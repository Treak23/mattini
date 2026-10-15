"""Brief M3-07: the trees step's checks come in their order, and what it writes is what it checked.

A small synthetic world, `probe` (E 2601100-2601140, N 1199100-1199140, one tile), with real
GeoTIFF tiles for the surface and terrain models, the lock, provenance.json and the configs laid
out as `lock`, `download` and design leave them. Only the two FileGDB readers are stand-ins
(`read_sheet` and `read_tlm`, whose readers have their own tests); the zips they would read are
plain bytes whose SHA-256 the step checks. Three crowns stand in it: one that is a tree, one
under a building's roof (the mask removes it) and one on rock (removed by the rock mask).
Pinned decisions (the brief, SPEC §8): a missing download is refused naming its command, the
first missing in sorted dataset order, before anything is created and before any progress line;
the world, the lock's fit and the inputs `computed_for` are checked before any provenance.json
is read; the TLM zip's size before it is hashed; every chunk is compared with
config/trees.json before anything is written.

Does NOT prove: the rule (the shared fixture's tests and the real village do); the FileGDB
readers on swisstopo's files; the command line and the manifest wiring (brief M3-13).
"""

import hashlib
import json
import os
import shutil
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from mattini import trees
from mattini.download import area_sheets
from mattini.trees import (
    TreesError,
    build_tree_chunks,
    build_trees,
    built_trees_block,
    write_trees,
)
from mattini.world import load_world

AREA = "probe"
TILE = "2601-1199"
WEST, NORTH = 2601000.0, 1200000.0  # the tile's corners: E of its west edge, N of its north edge
BOX = (2601100.0, 2601140.0, 1199100.0, 1199140.0)
EDITIONS = ["2021", "2022"]
DATASETS = ("swissalti3d", "swissbuildings3d", "swisssurface3d", "swisstlm3d")
FILES = {
    "swissalti3d": "swissalti3d_2024_2601-1199_0.5_2056_5728.tif",
    "swisssurface3d": "swisssurface3d-raster_2021_2601-1199_0.5_2056_5728.tif",
    "swisstlm3d": "swisstlm3d_2026-02_2056_5728.gdb.zip",
}
DOWNLOAD = {
    "swissalti3d": "python -m mattini download terrain",
    "swissbuildings3d": "python -m mattini download buildings",
    "swisssurface3d": "python -m mattini download surface",
    "swisstlm3d": "python -m mattini download tlm",
}
LOCK = {
    "swissalti3d": "python -m mattini lock terrain",
    "swissbuildings3d": "python -m mattini lock buildings",
    "swisssurface3d": "python -m mattini lock surface",
    "swisstlm3d": "python -m mattini lock tlm",
}
REBUILD = "python -m mattini trees"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _tile(values: np.ndarray, **overrides) -> bytes:
    """A 2000 × 2000 GeoTIFF of the tile 2601-1199, written as swisstopo writes its tiles."""
    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "width": values.shape[1],
        "height": values.shape[0],
        "count": 1,
        "crs": "EPSG:2056",
        "transform": from_origin(WEST, NORTH, 0.5, 0.5),
        "nodata": -9999.0,
        "compress": "deflate",
    }
    profile.update(overrides)
    with rasterio.MemoryFile() as memory:
        with memory.open(**profile) as ds:
            ds.write(values.astype(profile["dtype"]), 1)
        return memory.read()


def _models() -> tuple[np.ndarray, np.ndarray]:
    """DTM: 1600 m everywhere. DSM: three 9 × 9 crowns of 12 m, at the area's pixels (30, 40),
    (2, 4) and (60, 10): a free one, one under the building's roof, one on the rock."""
    dtm = np.full((2000, 2000), 1600.0, dtype=np.float32)
    dsm = dtm.copy()
    for i, j in ((30, 40), (2, 4), (60, 10)):
        dsm[1720 + i : 1729 + i, 200 + j : 209 + j] += 12.0
    return dsm, dtm


def _roof() -> dict:
    corners = [(2601098.0, 1199132.0), (2601110.0, 1199132.0), (2601110.0, 1199145.0)]
    other = [(2601098.0, 1199132.0), (2601110.0, 1199145.0), (2601098.0, 1199145.0)]
    triangles = [tuple((e, n, 1612.0) for e, n in corner) for corner in (corners, other)]
    return {"uuid": "{ROOF}", "objektart": "Gebaeude Einzelhaus", "triangles": triangles}


def _rock() -> dict:
    """A reader-form TLM_BODENBEDECKUNG polygon (whole mm) around the third crown: E 2601105 to
    2601110, N 1199104 to 1199112."""
    ring = [(2601105000, 1199104000), (2601110000, 1199104000), (2601110000, 1199112000)]
    ring += [(2601105000, 1199112000), (2601105000, 1199104000)]
    geometry = {"type": "MultiPolygon", "coordinates": [[[list(p) for p in ring]]]}
    return {"uuid": "{ROCK}", "attributes": {"OBJEKTART": 1}, "geometry": geometry}


def _world_file(path: Path, **changes) -> Path:
    data = {
        "schema": 1,
        "crs": {"horizontal": "EPSG:2056", "vertical": "EPSG:5728"},
        "origin_lv95": {"e": 2601000.0, "n": 1199000.0},
        "height_offset_m": 1000.0,
        "axes": {"x": "+e", "y": "+h", "z": "-n"},
        "areas": {AREA: dict(zip(("e_min", "e_max", "n_min", "n_max"), BOX, strict=True))},
    }
    data.update(changes)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _provenance(folder: Path, name: str, dataset: dict, parts: list[dict], **top) -> None:
    body = {
        "attribution": "© swisstopo",
        "collection": dataset["collection"],
        "dataset": name,
        "schema": 1,
        **top,
    }
    key = "sheets" if name == "swissbuildings3d" else "tiles"
    if name != "swisstlm3d":
        body[key] = parts
    (folder / "provenance.json").write_text(json.dumps(body, indent=2), encoding="utf-8")


def _case(tmp_path: Path, *, dsm_bytes: bytes | None = None, dtm_bytes: bytes | None = None):
    """The whole input of a build: world, datasets, lock, configs, a raw root, the stand-in
    readers' results. `dsm_bytes` and `dtm_bytes` replace a tile file (the lock and
    provenance.json follow them)."""
    world = load_world(_world_file(tmp_path / "world.json"))
    dsm, dtm = _models()
    files = {
        "swisssurface3d": dsm_bytes or _tile(dsm),
        "swissalti3d": dtm_bytes or _tile(dtm),
        "swisstlm3d": b"stand-in for the 2.88 GB zip",
    }
    sheets = area_sheets(world, AREA)
    sheet_names = {s: f"swissbuildings3d_3_0_2020_{s}_2056_5728.gdb.zip" for s in sheets}
    sheet_bytes = {s: f"stand-in for sheet {s}".encode() for s in sheets}
    datasets = {
        "swissalti3d": {
            "collection": "ch.swisstopo.swissalti3d",
            "edition": "2024",
            "resolution_m": 0.5,
            "attribution": "© swisstopo",
        },
        "swissbuildings3d": {
            "collection": "ch.swisstopo.swissbuildings3d_3_0",
            "edition": "2020",
            "attribution": "© swisstopo",
        },
        "swisssurface3d": {
            "collection": "ch.swisstopo.swisssurface3d-raster",
            "editions": EDITIONS,
            "resolution_m": 0.5,
            "attribution": "© swisstopo",
        },
        "swisstlm3d": {
            "collection": "ch.swisstopo.swisstlm3d",
            "edition": "2026-02",
            "attribution": "© swisstopo",
        },
    }
    lock = {
        "schema": 1,
        "datasets": {
            "swissalti3d": {
                "collection": "ch.swisstopo.swissalti3d",
                "edition": "2024",
                "resolution_m": 0.5,
                "tiles": {
                    TILE: {"file": FILES["swissalti3d"], "sha256": _sha(files["swissalti3d"])}
                },
            },
            "swissbuildings3d": {
                "collection": "ch.swisstopo.swissbuildings3d_3_0",
                "edition": "2020",
                "sheets": {
                    s: {"file": sheet_names[s], "sha256": _sha(sheet_bytes[s])} for s in sheets
                },
            },
            "swisssurface3d": {
                "collection": "ch.swisstopo.swisssurface3d-raster",
                "resolution_m": 0.5,
                "tiles": {
                    TILE: {
                        "edition": "2021",
                        "file": FILES["swisssurface3d"],
                        "sha256": _sha(files["swisssurface3d"]),
                    }
                },
            },
            "swisstlm3d": {
                "collection": "ch.swisstopo.swisstlm3d",
                "edition": "2026-02",
                "file": FILES["swisstlm3d"],
                "sha256": _sha(files["swisstlm3d"]),
            },
        },
    }
    raw = tmp_path / "raw"
    folders = {
        "swissalti3d": raw / "swissalti3d" / "2024",
        "swissbuildings3d": raw / "swissbuildings3d" / "2020",
        "swisssurface3d": raw / "swisssurface3d" / "2021-2022",
        "swisstlm3d": raw / "swisstlm3d" / "2026-02",
    }
    for folder in folders.values():
        folder.mkdir(parents=True)
    for name in ("swissalti3d", "swisssurface3d", "swisstlm3d"):
        (folders[name] / FILES[name]).write_bytes(files[name])
    for s in sheets:
        (folders["swissbuildings3d"] / sheet_names[s]).write_bytes(sheet_bytes[s])
    for name in ("swissalti3d", "swisssurface3d"):
        entry = {"file": FILES[name], "sha256": _sha(files[name]), "tile": TILE}
        if name == "swisssurface3d":
            entry["edition"] = "2021"
        extra = {"editions": EDITIONS} if name == "swisssurface3d" else {"edition": "2024"}
        _provenance(folders[name], name, datasets[name], [entry], resolution_m=0.5, **extra)
    _provenance(
        folders["swissbuildings3d"],
        "swissbuildings3d",
        datasets["swissbuildings3d"],
        [{"file": sheet_names[s], "sha256": _sha(sheet_bytes[s]), "sheet": s} for s in sheets],
        edition="2020",
    )
    _provenance(
        folders["swisstlm3d"],
        "swisstlm3d",
        datasets["swisstlm3d"],
        [],
        edition="2026-02",
        file=FILES["swisstlm3d"],
        sha256=_sha(files["swisstlm3d"]),
        size_bytes=len(files["swisstlm3d"]),
    )
    canonical = json.dumps(
        {name: lock["datasets"][name] for name in DATASETS},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    terrain_config = {
        "schema": 1,
        "areas": {
            AREA: {
                "computed_for": {"inputs_sha256": "a" * 64, "world_sha256": "b" * 64},
                "expected_sha256": {"0.5": "c" * 64},
                "spacing_m": 0.5,
            }
        },
    }
    case = SimpleNamespace(
        world=world,
        datasets=datasets,
        lock=lock,
        terrain_config=terrain_config,
        raw=raw,
        out=tmp_path / "out",
        folders=folders,
        sheets=sheets,
        sheet_names=sheet_names,
        canonical=canonical,
    )
    case.footprints, case.land_cover = [], [_rock_record()]
    case.buildings = [_roof()]
    area_dsm, area_dtm = dsm[1720:1800, 200:280], dtm[1720:1800, 200:280]
    expected = build_tree_chunks(
        area_dsm, area_dtm, case.buildings, case.footprints, case.land_cover, world, AREA
    )
    case.expected = {c["tile"]: _sha(c["data"]) for c in expected}
    case.chunks = expected
    case.config = {
        "schema": 1,
        "areas": {
            AREA: {
                "computed_for": {
                    "inputs_sha256": _sha(canonical.encode("utf-8")),
                    "world_sha256": _sha((tmp_path / "world.json").read_bytes()),
                },
                "expected_sha256": dict(case.expected),
            }
        },
    }
    return case


def _rock_record() -> dict:
    """The rock as `adapted` hands it to the rule: {uuid, objektart, polygons} in metres."""
    feature = _rock()
    return {
        "uuid": feature["uuid"],
        "objektart": 1,
        "polygons": [
            [[[e / 1000, n / 1000] for e, n in ring] for ring in polygon]
            for polygon in feature["geometry"]["coordinates"]
        ],
    }


@pytest.fixture(autouse=True)
def stand_in_readers(monkeypatch):
    """`read_sheet` gives the roof on every sheet; `read_tlm` the rock, no footprints. Both
    record what they were asked."""
    asked = SimpleNamespace(sheets=[], tlm=[])

    def read_sheet(data: bytes, sheet: str) -> list[dict]:
        asked.sheets.append(sheet)
        return [_roof()]

    def read_tlm(path, layers, box):
        asked.tlm.append((Path(path).name, dict(layers), tuple(box)))
        return {"TLM_GEBAEUDE_FOOTPRINT": [], "TLM_BODENBEDECKUNG": [_rock()]}

    monkeypatch.setattr(trees, "read_sheet", read_sheet)
    monkeypatch.setattr(trees, "read_tlm", read_tlm)
    return asked


def _build(case, **keywords):
    return build_trees(
        case.world,
        case.datasets,
        case.lock,
        case.config,
        case.terrain_config,
        case.raw,
        case.out,
        **keywords,
    )


# ------------------------------------------------------------------------ the happy path


def test_the_step_writes_the_one_free_tree_and_what_it_read(tmp_path, stand_in_readers):
    case = _case(tmp_path)
    block = _build(case)
    assert [(c["tile"], c["trees"]) for c in block["chunks"]] == [(TILE, 1)]
    assert [c["tile"] for c in case.chunks] == [TILE] and case.chunks[0]["trees"] == 1
    assert (case.out / "trees" / f"{TILE}.bin").read_bytes() == case.chunks[0]["data"]
    assert json.loads((case.out / "trees" / f"{AREA}.json").read_text()) == block
    assert stand_in_readers.sheets == case.sheets
    name, layers, box = stand_in_readers.tlm[0]
    assert name == FILES["swisstlm3d"] and box == BOX
    assert layers == {
        "TLM_GEBAEUDE_FOOTPRINT": ("OBJEKTART",),
        "TLM_BODENBEDECKUNG": ("OBJEKTART",),
    }
    assert set(block["source"]) == set(DATASETS)
    assert block["source"]["swisssurface3d"]["editions"] == EDITIONS
    assert block["source"]["swisssurface3d"]["tiles"][0]["edition"] == "2021"


def test_without_the_roof_and_the_rock_all_three_crowns_are_trees(tmp_path):
    """Control: the masks are what removes the two crowns."""
    case = _case(tmp_path)
    dsm, dtm = _models()
    chunks = build_tree_chunks(
        dsm[1720:1800, 200:280], dtm[1720:1800, 200:280], [], [], [], case.world, AREA
    )
    assert [(c["tile"], c["trees"]) for c in chunks] == [(TILE, 3)]


def test_the_built_block_is_accepted_and_two_builds_write_the_same_bytes(tmp_path):
    case = _case(tmp_path)
    first = _build(case)
    one = {p.name: p.read_bytes() for p in (case.out / "trees").iterdir()}
    shutil.rmtree(case.out)
    second = _build(case)
    two = {p.name: p.read_bytes() for p in (case.out / "trees").iterdir()}
    assert first == second and one == two
    again = _check(case)
    assert again == first


def _check(case, **overrides):
    args = {
        "trees_config": case.config,
        "terrain_config": case.terrain_config,
        "world": case.world,
        "world_sha256": _sha(case.world.path.read_bytes()),
        "datasets": case.datasets,
        "lock": case.lock,
    }
    args.update(overrides)
    return built_trees_block(
        case.out,
        args["trees_config"],
        args["terrain_config"],
        args["world"],
        args["world_sha256"],
        args["datasets"],
        args["lock"],
    )


def test_the_progress_lines_come_in_order(tmp_path):
    case = _case(tmp_path)
    said: list[str] = []
    _build(case, progress=said.append)
    starts = [
        "reading the 1 terrain and surface tiles",
        "reading the 1 building sheets",
        "reading the footprints and the land cover",
        "1 buildings meet the area",
        "masking",
        "smoothing",
        "finding the tops",
        "1 tops, 1 kept",
        "masks:",
        "1 trees in 1 chunks",
        "the 1 chunks have the SHA-256s config/trees.json expects",
        "wrote",
    ]
    assert len(said) == len(starts), said
    assert all(line.startswith(start) for line, start in zip(said, starts, strict=True)), said


# ------------------------------------------------------------- a missing download, first


@pytest.mark.parametrize("name", DATASETS)
def test_a_missing_download_is_refused_naming_its_command_before_anything_happens(tmp_path, name):
    case = _case(tmp_path)
    (case.folders[name] / "provenance.json").unlink()
    said: list[str] = []
    with pytest.raises(TreesError, match=DOWNLOAD[name]) as refusal:
        _build(case, progress=said.append)
    assert "no download has completed here" in str(refusal.value)
    assert said == [] and not case.out.exists()


def test_the_first_missing_download_in_sorted_dataset_order_is_the_one_named(tmp_path):
    case = _case(tmp_path)
    for name in ("swisstlm3d", "swisssurface3d", "swissbuildings3d"):
        (case.folders[name] / "provenance.json").unlink()
    with pytest.raises(TreesError, match=DOWNLOAD["swissbuildings3d"]):
        _build(case)
    shutil.rmtree(case.raw / "swissalti3d")
    with pytest.raises(TreesError, match=DOWNLOAD["swissalti3d"]):
        _build(case)
    shutil.rmtree(case.raw)
    with pytest.raises(TreesError, match=DOWNLOAD["swissalti3d"]):
        _build(case)
    assert not case.out.exists()


def test_a_file_a_provenance_lists_but_that_is_absent_names_the_download(tmp_path):
    case = _case(tmp_path)
    (case.folders["swissalti3d"] / FILES["swissalti3d"]).unlink()
    with pytest.raises(TreesError, match=DOWNLOAD["swissalti3d"]) as refusal:
        _build(case)
    assert TILE in str(refusal.value) and not case.out.exists()


# --------------------------------------------------------- the checks before the reading


def test_another_world_is_refused_before_a_provenance_is_read(tmp_path):
    case = _case(tmp_path)
    shutil.rmtree(case.raw)  # reading first would fail otherwise, naming a download
    case.config["areas"][AREA]["computed_for"]["world_sha256"] = "0" * 64
    with pytest.raises(TreesError, match=r"config/world\.json") as refusal:
        _build(case)
    assert "design recomputes" in str(refusal.value) and not case.out.exists()


@pytest.mark.parametrize("name", DATASETS)
@pytest.mark.parametrize("how", ["no entry", "another edition", "extra part", "bad checksum"])
def test_a_lock_that_does_not_fit_is_refused_naming_its_lock_command(tmp_path, name, how):
    case = _case(tmp_path)
    shutil.rmtree(case.raw)
    entry = case.lock["datasets"][name]
    parts = entry.get("tiles") or entry.get("sheets")
    if how == "no entry":
        del case.lock["datasets"][name]
    elif how == "another edition":
        if "edition" in entry:
            entry["edition"] = "1999-01"
        else:
            entry["resolution_m"] = 2.0
    elif how == "extra part":
        if parts is None:
            entry["tiles"] = {}
            entry["file"] = "../x"
        else:
            parts["9999-9999" if "tiles" in entry else "0000-00"] = dict(next(iter(parts.values())))
    else:
        if parts is None:
            entry["sha256"] = "XYZ"
        else:
            next(iter(parts.values()))["sha256"] = "not hex"
    with pytest.raises(TreesError, match=LOCK[name]) as refusal:
        _build(case)
    assert "design recomputes" not in str(refusal.value) and not case.out.exists()


def test_the_surface_tile_s_edition_must_be_one_the_config_lists(tmp_path):
    case = _case(tmp_path)
    case.lock["datasets"]["swisssurface3d"]["tiles"][TILE]["edition"] = "2019"
    with pytest.raises(TreesError, match=LOCK["swisssurface3d"]) as refusal:
        _build(case)
    assert "2019" in str(refusal.value)


def test_republished_inputs_that_fit_are_refused_by_the_inputs_check_naming_design(tmp_path):
    case = _case(tmp_path)
    shutil.rmtree(case.raw)
    case.lock["datasets"]["swisssurface3d"]["tiles"][TILE]["sha256"] = "1" * 64
    with pytest.raises(TreesError, match="design recomputes") as refusal:
        _build(case)
    message = str(refusal.value)
    assert "datasets.lock.json" in message and "this machine or this code" not in message
    assert not case.out.exists()


def test_the_trees_config_must_name_the_terrain_configs_area(tmp_path):
    case = _case(tmp_path)
    case.config["areas"] = {"elsewhere": case.config["areas"][AREA]}
    with pytest.raises(TreesError, match="config/terrain.json names 'probe'"):
        _build(case)


def test_a_datasets_config_without_a_dataset_is_refused_naming_the_config(tmp_path):
    case = _case(tmp_path)
    del case.datasets["swisstlm3d"]
    with pytest.raises(TreesError, match=r"config/datasets\.json has no 'swisstlm3d'"):
        _build(case)
    case.datasets["swisstlm3d"] = {"collection": "c", "edition": "2026-02"}
    with pytest.raises(TreesError, match="attribution"):
        _build(case)
    case.datasets["swisstlm3d"] = {"collection": "c", "edition": "2026-02", "attribution": "a"}
    case.datasets["swissalti3d"]["resolution_m"] = 2.0
    with pytest.raises(TreesError, match="resolution_m"):
        _build(case)


def test_other_axes_are_refused(tmp_path):
    case = _case(tmp_path)
    path = _world_file(tmp_path / "rotated.json", axes={"x": "+n", "y": "+h", "z": "+e"})
    case.world = load_world(path)
    with pytest.raises(TreesError, match="axes"):
        _build(case)
    assert not case.out.exists()


def test_an_area_that_is_not_whole_pixels_is_refused(tmp_path):
    case = _case(tmp_path)
    path = _world_file(tmp_path / "odd.json")
    data = json.loads(path.read_text())
    data["areas"][AREA]["e_max"] += 0.3
    path.write_text(json.dumps(data))
    case.world = load_world(path)
    with pytest.raises(TreesError, match="whole number of 0.5 m cells"):
        _build(case)


# ------------------------------------------------------------------- the provenance


@pytest.mark.parametrize(
    ("name", "change", "pattern"),
    [
        ("swissalti3d", {"edition": "2019"}, "edition"),
        ("swissalti3d", {"resolution_m": 2.0}, "resolution_m"),
        ("swissalti3d", {"dataset": "swissalti3d_x"}, "dataset"),
        ("swissalti3d", {"collection": "ch.other"}, "collection"),
        ("swissalti3d", {"tiles": []}, "lists the tiles"),
        ("swissalti3d", {"tiles": "x"}, "not a list"),
        ("swissbuildings3d", {"sheets": []}, "lists the sheets"),
        ("swissbuildings3d", {"edition": "2015"}, "edition"),
        ("swisssurface3d", {"editions": ["2021"]}, "editions"),
        ("swisssurface3d", {"resolution_m": 1.0}, "resolution_m"),
        ("swisstlm3d", {"edition": "2025-08"}, "edition"),
        ("swisstlm3d", {"sha256": "e" * 64}, "sha256"),
        ("swisstlm3d", {"file": "another.gdb.zip"}, "file"),
        ("swisstlm3d", {"size_bytes": 0}, "size_bytes"),
        ("swisstlm3d", {"size_bytes": True}, "size_bytes"),
    ],
)
def test_a_provenance_of_something_else_is_refused_naming_the_download(
    tmp_path, name, change, pattern
):
    case = _case(tmp_path)
    path = case.folders[name] / "provenance.json"
    path.write_text(json.dumps({**json.loads(path.read_text()), **change}), encoding="utf-8")
    with pytest.raises(TreesError, match=pattern) as refusal:
        _build(case)
    assert DOWNLOAD[name] in str(refusal.value) and not case.out.exists()


@pytest.mark.parametrize(
    ("name", "key", "value"),
    [
        ("swissalti3d", "file", "other.tif"),
        ("swissalti3d", "sha256", "f" * 64),
        ("swisssurface3d", "sha256", "f" * 64),
        ("swisssurface3d", "edition", "2022"),
        ("swissbuildings3d", "sha256", "f" * 64),
        ("swissalti3d", "file", "../up.tif"),
        ("swissalti3d", "sha256", None),
    ],
)
def test_an_entry_that_is_not_the_locked_file_is_refused_naming_the_download(
    tmp_path, name, key, value
):
    case = _case(tmp_path)
    path = case.folders[name] / "provenance.json"
    provenance = json.loads(path.read_text())
    provenance["sheets" if name == "swissbuildings3d" else "tiles"][0][key] = value
    path.write_text(json.dumps(provenance), encoding="utf-8")
    with pytest.raises(TreesError, match=DOWNLOAD[name]):
        _build(case)


def test_the_checksum_may_be_written_in_upper_case_in_a_provenance(tmp_path):
    case = _case(tmp_path)
    path = case.folders["swissalti3d"] / "provenance.json"
    provenance = json.loads(path.read_text())
    provenance["tiles"][0]["sha256"] = provenance["tiles"][0]["sha256"].upper()
    path.write_text(json.dumps(provenance), encoding="utf-8")
    assert _build(case)["chunks"][0]["trees"] == 1


# ------------------------------------------------------------------- the files read


@pytest.mark.parametrize("name", ["swissalti3d", "swisssurface3d"])
def test_a_tile_whose_bytes_are_not_the_locked_ones_is_refused(tmp_path, name):
    case = _case(tmp_path)
    path = case.folders[name] / FILES[name]
    path.write_bytes(path.read_bytes() + b"x")
    with pytest.raises(TreesError, match=DOWNLOAD[name]) as refusal:
        _build(case)
    assert TILE in str(refusal.value) and "has SHA-256" in str(refusal.value)
    assert not case.out.exists()


def test_a_sheet_whose_bytes_are_not_the_locked_ones_is_refused(tmp_path):
    case = _case(tmp_path)
    path = case.folders["swissbuildings3d"] / case.sheet_names[case.sheets[0]]
    path.write_bytes(b"another sheet")
    with pytest.raises(TreesError, match=DOWNLOAD["swissbuildings3d"]) as refusal:
        _build(case)
    assert case.sheets[0] in str(refusal.value)


def test_the_tlm_zip_s_size_is_compared_before_it_is_hashed(tmp_path, monkeypatch):
    case = _case(tmp_path)
    path = case.folders["swisstlm3d"] / "provenance.json"
    path.write_text(json.dumps({**json.loads(path.read_text()), "size_bytes": 5}), encoding="utf-8")

    def no_hashing(*args, **kwargs):
        raise AssertionError("the zip was hashed before its size was compared")

    monkeypatch.setattr(hashlib, "file_digest", no_hashing)
    with pytest.raises(TreesError, match=DOWNLOAD["swisstlm3d"]) as refusal:
        _build(case)
    assert "lists 5" in str(refusal.value)


def test_the_tlm_zip_must_be_the_locked_bytes_and_unchanged_by_the_read(tmp_path, monkeypatch):
    case = _case(tmp_path)
    zip_path = case.folders["swisstlm3d"] / FILES["swisstlm3d"]
    same_size = bytes(len(zip_path.read_bytes()))
    original = zip_path.read_bytes()
    zip_path.write_bytes(same_size)
    with pytest.raises(TreesError, match="has SHA-256") as refusal:
        _build(case)
    assert DOWNLOAD["swisstlm3d"] in str(refusal.value)
    zip_path.write_bytes(original)

    real = trees.read_tlm

    def read_then_touch(path, layers, box):
        found = real(path, layers, box)
        status = os.stat(path)
        os.utime(path, ns=(status.st_atime_ns, status.st_mtime_ns + 5_000_000_000))
        return found

    monkeypatch.setattr(trees, "read_tlm", read_then_touch)
    with pytest.raises(TreesError, match="changed while it was read"):
        _build(case)
    assert not case.out.exists()


@pytest.mark.parametrize(
    ("how", "pattern"),
    [
        ("crs", "CRS"),
        ("size", "pixels in 1 bands"),
        ("dtype", "float32"),
        ("transform", "top-left corner"),
        ("nodata", "not a height"),
        ("nan", "not a height"),
        ("garbage", "GeoTIFF"),
    ],
)
@pytest.mark.parametrize("name", ["swissalti3d", "swisssurface3d"])
def test_a_tile_of_another_shape_is_refused_naming_the_tile(tmp_path, name, how, pattern):
    dsm, dtm = _models()
    values = dsm if name == "swisssurface3d" else dtm
    if how == "crs":
        data = _tile(values, crs="EPSG:4326")
    elif how == "size":
        data = _tile(values[:1000, :1000])
    elif how == "dtype":
        data = _tile(values, dtype="float64")
    elif how == "transform":
        data = _tile(values, transform=from_origin(WEST + 0.5, NORTH, 0.5, 0.5))
    elif how == "nodata":
        values = values.copy()
        values[1750, 240] = -9999.0
        data = _tile(values)
    elif how == "nan":
        values = values.copy()
        values[1750, 240] = np.nan
        data = _tile(values, nodata=None)
    else:
        data = b"not a GeoTIFF"
    case = _case(tmp_path, **{"dsm_bytes" if name == "swisssurface3d" else "dtm_bytes": data})
    with pytest.raises(TreesError, match=pattern) as refusal:
        _build(case)
    assert TILE in str(refusal.value) and name in str(refusal.value) and not case.out.exists()


# ------------------------------------------------------------- compared, then written


def test_other_chunks_are_refused_before_anything_is_written(tmp_path):
    case = _case(tmp_path)
    case.config["areas"][AREA]["expected_sha256"][TILE] = "0" * 64
    with pytest.raises(TreesError) as refusal:
        _build(case)
    assert case.expected[TILE] in str(refusal.value) and "0" * 64 in str(refusal.value)
    assert "nothing was written" in str(refusal.value) and not case.out.exists()


@pytest.mark.parametrize("extra", ["a tile the config expects", "a tile the build has"])
def test_a_set_of_tiles_that_differs_is_refused(tmp_path, extra):
    case = _case(tmp_path)
    if extra == "a tile the config expects":
        case.config["areas"][AREA]["expected_sha256"]["2602-1199"] = "0" * 64
        pattern = "2602-1199.*no chunk"
    else:
        case.config["areas"][AREA]["expected_sha256"] = {"2602-1199": "0" * 64}
        pattern = f"{TILE}.*expects no chunk|2602-1199.*no chunk"
    with pytest.raises(TreesError, match=pattern):
        _build(case)
    assert not case.out.exists()


def test_a_write_removes_stale_chunks_and_part_files_from_its_folder_only(tmp_path):
    case = _case(tmp_path)
    folder, other = case.out / "trees", case.out / "terrain"
    folder.mkdir(parents=True)
    other.mkdir()
    for name in ("2599-1000.bin", "2599-1000.bin.part", "stale.json.part", "notes.txt"):
        (folder / name).write_bytes(b"old")
    (other / "probe.f32.part").write_bytes(b"old")
    said: list[str] = []
    _build(case, progress=said.append)
    assert sorted(p.name for p in folder.iterdir()) == [f"{TILE}.bin", "notes.txt", "probe.json"]
    assert (other / "probe.f32.part").read_bytes() == b"old"
    assert any("removed 1 stale chunk files and 2 .part files" in line for line in said)


def test_a_refused_build_leaves_the_folder_as_it_was(tmp_path):
    case = _case(tmp_path)
    folder = case.out / "trees"
    folder.mkdir(parents=True)
    (folder / "2599-1000.bin").write_bytes(b"old")
    case.config["areas"][AREA]["expected_sha256"][TILE] = "0" * 64
    with pytest.raises(TreesError):
        _build(case)
    assert [p.name for p in folder.iterdir()] == ["2599-1000.bin"]


def test_the_files_are_written_through_part_renames_chunks_first(tmp_path, monkeypatch):
    case = _case(tmp_path)
    moves = []
    real = os.replace
    monkeypatch.setattr(
        trees.os,
        "replace",
        lambda src, dst: (moves.append((Path(src).name, Path(dst).name)), real(src, dst))[1],
    )
    _build(case)
    assert moves == [(f"{TILE}.bin.part", f"{TILE}.bin"), (f"{AREA}.json.part", f"{AREA}.json")]


def test_write_trees_refuses_a_chunk_whose_bytes_are_not_its_trees(tmp_path):
    chunk = {"tile": TILE, "trees": 2, "data": b"x" * 20}
    with pytest.raises(TreesError, match="not 2 trees"):
        write_trees(tmp_path, AREA, [chunk], BOX, "0" * 64, {})
    with pytest.raises(TreesError, match="area name"):
        write_trees(tmp_path, "Probe", [], BOX, "0" * 64, {})
    assert not (tmp_path / "trees").exists()


# ------------------------------------------------------------------- the built block


def _edit(case, **changes) -> None:
    path = case.out / "trees" / f"{AREA}.json"
    block = json.loads(path.read_text())
    block.update(changes)
    path.write_text(json.dumps(block, indent=2, sort_keys=True) + "\n")


def test_nothing_built_gives_none_and_no_lock_is_read(tmp_path):
    case = _case(tmp_path)
    assert _check(case, lock=tmp_path / "no-lock.json") is None


@pytest.mark.parametrize(
    ("changes", "pattern"),
    [
        ({"extra": 1}, "exactly the keys"),
        ({"area": "elsewhere"}, "area is"),
        ({"format": "trees-f64"}, "format is"),
        ({"world_sha256": "0" * 64}, "world_sha256 is"),
        ({"parameters": {}}, "parameters is"),
        ({"source": {}}, "source is"),
        ({"lv95_box": {"e_max": 1, "e_min": 1, "n_max": 1, "n_min": 1}}, "lv95_box is"),
        ({"lv95_box": []}, "lv95_box is"),
        ({"chunks": "x"}, "list of entries"),
        ({"chunks": [{"tile": TILE}]}, "list of entries"),
        ({"chunks": []}, "it lists the chunks"),
    ],
)
def test_a_description_that_does_not_fit_is_refused_naming_the_rebuild(tmp_path, changes, pattern):
    case = _case(tmp_path)
    _build(case)
    _edit(case, **changes)
    with pytest.raises(TreesError, match=pattern) as refusal:
        _check(case)
    assert REBUILD in str(refusal.value) and f"{AREA}.json" in str(refusal.value)


def test_a_description_that_is_not_json_is_refused(tmp_path):
    case = _case(tmp_path)
    _build(case)
    (case.out / "trees" / f"{AREA}.json").write_text("{broken", encoding="utf-8")
    with pytest.raises(TreesError, match="not valid JSON"):
        _check(case)


def test_a_chunk_that_is_missing_short_or_changed_is_refused(tmp_path):
    case = _case(tmp_path)
    _build(case)
    chunk = case.out / "trees" / f"{TILE}.bin"
    original = chunk.read_bytes()
    chunk.write_bytes(original[:-4])
    with pytest.raises(TreesError, match="20 bytes|need 20") as refusal:
        _check(case)
    assert REBUILD in str(refusal.value)
    flipped = bytearray(original)
    flipped[3] ^= 1
    chunk.write_bytes(bytes(flipped))
    with pytest.raises(TreesError, match="has SHA-256") as refusal:
        _check(case)
    assert TILE in str(refusal.value) and REBUILD in str(refusal.value)
    chunk.unlink()
    with pytest.raises(TreesError, match="cannot be read"):
        _check(case)


def test_a_chunk_that_is_not_the_configs_expected_one_is_refused(tmp_path):
    case = _case(tmp_path)
    _build(case)
    case.config["areas"][AREA]["expected_sha256"][TILE] = "5" * 64
    with pytest.raises(TreesError, match="expects 5555") as refusal:
        _check(case)
    assert REBUILD in str(refusal.value)


def test_a_source_that_is_not_what_the_lock_pins_is_refused(tmp_path):
    case = _case(tmp_path)
    _build(case)
    case.lock["datasets"]["swissalti3d"]["tiles"][TILE]["sha256"] = "7" * 64
    case.config["areas"][AREA]["computed_for"]["inputs_sha256"] = _sha(
        json.dumps(
            {n: case.lock["datasets"][n] for n in DATASETS},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
    )
    with pytest.raises(TreesError, match="source is"):
        _check(case)


def test_the_built_check_names_design_for_a_world_or_inputs_it_was_not_computed_for(tmp_path):
    case = _case(tmp_path)
    _build(case)
    with pytest.raises(TreesError, match="design recomputes") as refusal:
        _check(case, world_sha256="1" * 64)
    assert REBUILD not in str(refusal.value)
    case.lock["datasets"]["swisstlm3d"]["sha256"] = "3" * 64
    with pytest.raises(TreesError, match="design recomputes") as refusal:
        _check(case)
    assert REBUILD not in str(refusal.value)


@pytest.mark.parametrize("name", DATASETS)
def test_the_built_check_refuses_a_lock_that_does_not_fit_naming_its_lock_command(tmp_path, name):
    case = _case(tmp_path)
    _build(case)
    del case.lock["datasets"][name]
    with pytest.raises(TreesError, match=LOCK[name]):
        _check(case)


def test_the_lock_may_be_given_as_a_path_and_an_unreadable_one_is_refused(tmp_path):
    case = _case(tmp_path)
    block = _build(case)
    path = tmp_path / "lock.json"
    path.write_text(json.dumps(case.lock), encoding="utf-8")
    assert _check(case, lock=path) == block
    assert _check(case, lock=str(path)) == block
    with pytest.raises(TreesError, match="cannot read the lock"):
        _check(case, lock=tmp_path / "absent.json")
    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(TreesError, match="not valid JSON"):
        _check(case, lock=path)


def test_a_world_without_the_configured_area_is_refused_by_the_built_check(tmp_path):
    case = _case(tmp_path)
    _build(case)
    path = _world_file(tmp_path / "other.json")
    data = json.loads(path.read_text())
    data["areas"] = {"elsewhere": data["areas"][AREA]}
    path.write_text(json.dumps(data), encoding="utf-8")
    config = json.loads(json.dumps(case.config))
    config["areas"][AREA]["computed_for"]["world_sha256"] = _sha(path.read_bytes())
    with pytest.raises(TreesError, match="no area 'probe'"):
        _check(
            case, trees_config=config, world=load_world(path), world_sha256=_sha(path.read_bytes())
        )
