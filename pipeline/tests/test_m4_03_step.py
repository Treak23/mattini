"""Pinning tests for brief v0.5.0-01: the capture shadows step from swissSURFACE3D tiles to its files.

Carried from brief M4-03's pin (docs/briefs/pinning/M4-03/) and re-pinned for release 0.5.0
(2026-10-29): only these docstrings changed, to name v0.5.0-01, v0.5.0-02 and the reader.

The shared fixture's surface (tests/shared/shadows_fixture/dsm.f32, 0.5 m, 96 x 64 pixels) is
written here into the four 1 km GeoTIFF tiles its area touches (the area crosses the tiles'
corner at E 2651000, N 1150000 off its centre), with a provenance.json and a lock as `download
surface` and `lock surface` leave them; the tiles' bytes come from this machine's GDAL, so the
lock entry and `computed_for.inputs_sha256` are computed here (canonical JSON, lesson 41), and
the expected pixels and PNG are the fixture config's.

Pinned decisions (m4-design §3; the brief's Decisions):
- The step writes `shadows/<area>.png.import` (exactly `[remap]\\n\\nimporter="keep"\\n`, brain.md
  H24), then `shadows/<area>.png`, then `shadows/<area>.json`, each through `<name>.part` and a
  rename; after a write no `*.part` is left in `shadows/` (another folder's is kept).
- The checks come in this order: the config, the world (axes, area, `computed_for.world_sha256`),
  the lock's fit (`python -m mattini lock surface`), `computed_for.inputs_sha256` against the
  lock's `swisssurface3d` entry, provenance.json, then each tile's SHA-256 before it is read.
  A `computed_for` difference is refused as a design change, naming both SHA-256s (lesson 41).
- A missing download is refused naming `python -m mattini download surface`, before anything is
  created under the output folder and before any progress line.
- The mask's SHA-256 is compared with `expected_pixels_sha256`, then the PNG's (encoded once)
  with `expected_png_sha256`, both before anything is written (lesson 38); the PNG's refusal
  names zlib and `zlib.ZLIB_RUNTIME_VERSION` (brain.md H27, brief M3-R1-fix-6).
- `built_shadows_block` returns the description of what is built, None when nothing is, and
  refuses built files that are not design's naming `python -m mattini shadows`.

Does NOT prove: the real village (the brief's real run against config/shadows.json); the
command line and the manifest (brief v0.5.0-02); the game's reading (M4-06's reader, re-cut in 0.5.0).
"""

import copy
import hashlib
import json
import os
import shutil
import zlib
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from mattini import shadows
from mattini.shadows import ShadowsError, build_shadows, built_shadows_block
from mattini.world import load_world

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "shared" / "shadows_fixture"
GENERATED = FIXTURE / "generated" / "shadows"
BOX = (2650986.0, 2651018.0, 1149978.0, 1150026.0)
TILES = {"2650-1149": "2022", "2650-1150": "2021", "2651-1149": "2021", "2651-1150": "2022"}
KEEP = b'[remap]\n\nimporter="keep"\n'
DOWNLOAD = "python -m mattini download surface"
LOCK = "python -m mattini lock surface"
REBUILD = "python -m mattini shadows"
COLLECTION = "ch.swisstopo.swisssurface3d-raster"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value) -> str:
    return _sha(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    )


def _file(tile: str) -> str:
    return f"swisssurface3d-raster_{TILES[tile]}_{tile}_0.5_2056_5728.tif"


def _tile_bytes(tile: str) -> bytes:
    """The 2000 x 2000 tile, 1600 m beside the area, the fixture's pixels inside it."""
    e_km, n_km = (int(v) for v in tile.split("-"))
    west, north = e_km * 1000.0, (n_km + 1) * 1000.0
    values = np.full((2000, 2000), np.float32(1600.0))
    dsm = np.fromfile(FIXTURE / "dsm.f32", dtype="<f4").reshape(96, 64)
    e_min, _, _, n_max = BOX
    for r in range(96):
        for c in range(64):
            e, n = e_min + 0.5 * c, n_max - 0.5 * r  # the pixel's north-west corner
            i, j = round((north - n) / 0.5), round((e - west) / 0.5)
            if 0 <= i < 2000 and 0 <= j < 2000:
                values[i, j] = dsm[r, c]
    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "width": 2000,
        "height": 2000,
        "count": 1,
        "crs": "EPSG:2056",
        "transform": from_origin(west, north, 0.5, 0.5),
        "nodata": -9999.0,
        "compress": "deflate",
    }
    with rasterio.MemoryFile() as memory:
        with memory.open(**profile) as ds:
            ds.write(values, 1)
        return memory.read()


@pytest.fixture(scope="module")
def tiles() -> dict[str, bytes]:
    return {tile: _tile_bytes(tile) for tile in TILES}


class Case:
    def __init__(self, root: Path, tiles: dict[str, bytes]):
        self.root = root
        self.raw = root / "raw"
        self.out = root / "out"
        self.world_path = root / "world.json"
        shutil.copyfile(FIXTURE / "world.json", self.world_path)
        self.datasets = json.loads((FIXTURE / "datasets.json").read_text("utf-8"))["datasets"]
        entry = {
            "collection": COLLECTION,
            "resolution_m": 0.5,
            "tiles": {
                t: {"edition": TILES[t], "file": _file(t), "sha256": _sha(data)}
                for t, data in tiles.items()
            },
        }
        self.lock = {"schema": 1, "datasets": {"swisssurface3d": entry}}
        self.config = json.loads((FIXTURE / "shadows.json").read_text("utf-8"))
        self.config["areas"]["fixture"]["computed_for"]["inputs_sha256"] = _canonical(entry)
        folder = self.raw / "swisssurface3d" / "2021-2022"
        folder.mkdir(parents=True)
        items = []
        for tile, data in tiles.items():
            (folder / _file(tile)).write_bytes(data)
            items.append(
                {
                    "edition": TILES[tile],
                    "file": _file(tile),
                    "item": f"swisssurface3d-raster_{TILES[tile]}_{tile}",
                    "sha256": _sha(data),
                    "size_bytes": len(data),
                    "tile": tile,
                    "url": f"https://data.geo.admin.ch/{COLLECTION}/{_file(tile)}",
                }
            )
        provenance = {
            "attribution": "© swisstopo",
            "collection": COLLECTION,
            "dataset": "swisssurface3d",
            "editions": ["2021", "2022"],
            "resolution_m": 0.5,
            "schema": 1,
            "tiles": items,
        }
        (folder / "provenance.json").write_text(json.dumps(provenance, indent=2), "utf-8")
        self.folder = folder
        self.said: list[str] = []

    def build(self, **changes):
        return build_shadows(
            load_world(self.world_path),
            changes.get("datasets", self.datasets),
            changes.get("lock", self.lock),
            changes.get("config", self.config),
            changes.get("raw", self.raw),
            self.out,
            progress=self.said.append,
        )

    def block(self):
        return built_shadows_block(
            self.out,
            self.config,
            load_world(self.world_path),
            _sha(self.world_path.read_bytes()),
            self.datasets,
            self.lock,
        )


@pytest.fixture
def case(tmp_path, tiles) -> Case:
    return Case(tmp_path, tiles)


def _expected_description(case: Case) -> dict:
    block = json.loads((GENERATED / "fixture.json").read_text("utf-8"))
    block["source"]["entry_sha256"] = _canonical(case.lock["datasets"]["swisssurface3d"])
    return block


def _nothing_written(case: Case) -> bool:
    return not case.out.exists() or not any(case.out.rglob("*"))


# ------------------------------------------------------------------- what it writes


def test_the_step_writes_the_fixture_s_files(case):
    block = case.build()
    folder = case.out / "shadows"
    assert sorted(p.name for p in folder.iterdir()) == [
        "fixture.json",
        "fixture.png",
        "fixture.png.import",
    ]
    assert (folder / "fixture.png").read_bytes() == (GENERATED / "fixture.png").read_bytes()
    assert (folder / "fixture.png.import").read_bytes() == KEEP
    expected = _expected_description(case)
    assert block == expected
    text = json.dumps(expected, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    assert (folder / "fixture.json").read_bytes() == text.encode("utf-8")
    assert case.said, "the step reports its progress"


def test_the_files_are_written_in_order_each_through_a_part_rename(case, monkeypatch):
    renames = []
    real = os.replace

    def recording(src, dst):
        renames.append((Path(src).name, Path(dst).name))
        return real(src, dst)

    monkeypatch.setattr(shadows.os, "replace", recording)
    folder = case.out / "shadows"
    folder.mkdir(parents=True)
    (folder / "fixture.png.part").write_bytes(b"a write cut short")
    (folder / "old.json.part").write_bytes(b"a write cut short")
    other = case.out / "surfaces"
    other.mkdir()
    (other / "fixture.png.part").write_bytes(b"not this step's")
    case.build()
    assert renames == [
        ("fixture.png.import.part", "fixture.png.import"),
        ("fixture.png.part", "fixture.png"),
        ("fixture.json.part", "fixture.json"),
    ]
    assert list(folder.glob("*.part")) == []
    assert (other / "fixture.png.part").read_bytes() == b"not this step's"


# ------------------------------------------------------------------- refusals


def test_a_missing_download_names_download_surface_before_anything(case, tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(ShadowsError, match=DOWNLOAD):
        case.build(raw=empty)
    assert not case.out.exists(), "not even the output folder"
    assert case.said == [], "no progress line before the refusal"


def test_a_missing_tile_names_download_surface_and_writes_nothing(case):
    (case.folder / _file("2651-1150")).unlink()
    with pytest.raises(ShadowsError, match=DOWNLOAD):
        case.build()
    assert _nothing_written(case)


def test_a_tile_that_is_not_the_locked_one_is_refused_by_its_sha256_before_it_is_read(case):
    """Bytes that are no GeoTIFF: a step that read them first would fail on the format."""
    (case.folder / _file("2650-1150")).write_bytes(b"not a GeoTIFF")
    with pytest.raises(ShadowsError, match=DOWNLOAD) as caught:
        case.build()
    text = str(caught.value)
    assert "2650-1150" in text and "SHA-256" in text, text
    assert _nothing_written(case)


def test_another_mask_is_refused_before_anything_is_written(case):
    config = copy.deepcopy(case.config)
    expected = config["areas"]["fixture"]["expected_pixels_sha256"]
    config["areas"]["fixture"]["expected_pixels_sha256"] = "0" * 64
    with pytest.raises(ShadowsError) as caught:
        case.build(config=config)
    text = str(caught.value)
    assert "0" * 64 in text and expected in text and "config/shadows.json" in text, text
    assert _nothing_written(case)


def test_another_png_is_refused_naming_zlib_before_anything_is_written(case, monkeypatch):
    original = zlib.compress  # shadows.zlib is this module: patch with a closure over it
    monkeypatch.setattr(shadows.zlib, "compress", lambda data, level=-1: original(data, 0))
    with pytest.raises(ShadowsError) as caught:
        case.build()
    text = str(caught.value)
    assert "zlib" in text and zlib.ZLIB_RUNTIME_VERSION in text, text
    assert "expected_png_sha256" in text, text
    assert _nothing_written(case)


def test_another_world_is_refused_as_a_design_change_before_any_input(case, tmp_path):
    recorded = case.config["areas"]["fixture"]["computed_for"]["world_sha256"]
    case.world_path.write_bytes(case.world_path.read_bytes() + b"\n")
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(ShadowsError) as caught:
        case.build(raw=empty)  # the world comes before the download
    text = str(caught.value)
    assert recorded in text and _sha(case.world_path.read_bytes()) in text, text
    assert "design" in text and DOWNLOAD not in text and "this machine" not in text, text
    assert not case.out.exists()


def test_other_inputs_are_refused_as_a_design_change_before_any_input(case, tmp_path):
    config = copy.deepcopy(case.config)
    config["areas"]["fixture"]["computed_for"]["inputs_sha256"] = "1" * 64
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(ShadowsError) as caught:
        case.build(config=config, raw=empty)
    text = str(caught.value)
    current = _canonical(case.lock["datasets"]["swisssurface3d"])
    assert "1" * 64 in text and current in text and "design" in text, text
    assert DOWNLOAD not in text and "this machine" not in text, text
    assert not case.out.exists()


def test_a_lock_without_the_surface_entry_names_lock_surface(case):
    lock = {"schema": 1, "datasets": {}}
    with pytest.raises(ShadowsError, match=LOCK):
        case.build(lock=lock)
    other = copy.deepcopy(case.lock)
    del other["datasets"]["swisssurface3d"]["tiles"]["2651-1150"]
    with pytest.raises(ShadowsError, match=LOCK):
        case.build(lock=other)
    assert _nothing_written(case)


def test_other_axes_are_refused(case):
    data = json.loads(case.world_path.read_text("utf-8"))
    data["axes"] = {"x": "+n", "y": "+h", "z": "+e"}
    case.world_path.write_text(json.dumps(data, indent=2), "utf-8")
    with pytest.raises(ShadowsError, match="axes"):
        case.build()
    assert _nothing_written(case)


# ------------------------------------------------------------------- the built block


def test_the_built_block_is_the_description_or_none(case):
    assert case.block() is None
    written = case.build()
    assert case.block() == written == _expected_description(case)


@pytest.mark.parametrize(
    "damage",
    ["png", "import", "description", "missing png"],
)
def test_built_files_that_are_not_design_s_are_refused_naming_the_step(case, damage):
    case.build()
    folder = case.out / "shadows"
    if damage == "png":
        mask = np.zeros((96, 64), dtype=np.uint8)
        (folder / "fixture.png").write_bytes(shadows.png_mask(mask))
    elif damage == "import":
        (folder / "fixture.png.import").write_bytes(b'[remap]\n\nimporter="texture"\n')
    elif damage == "description":
        block = json.loads((folder / "fixture.json").read_text("utf-8"))
        block["rows"] = 47
        (folder / "fixture.json").write_text(json.dumps(block), "utf-8")
    else:
        (folder / "fixture.png").unlink()
    with pytest.raises(ShadowsError, match=REBUILD):
        case.block()
