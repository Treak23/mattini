"""`build_buildings` and `python -m mattini buildings` (brief M2-04; docs/SPEC.md §8).

The step reads the sheets provenance.json lists, each checked against its provenance entry
and the lock and read from the very bytes hashed, applies the rule, compares every chunk
and the set of tiles with the buildings config before anything is written, then writes
the chunks and their description. Here the shared buildings fixture stands in for a sheet
the way its own lock says: sheet 1249-42 (the only sheet within 100 m of the fixture's
area) is the file source.json, whose bytes a stand-in reader turns into the eleven
features. So the step's output must be the fixture's files byte for byte, the description
included, which design computed two independent ways. A FileGDB that fiona writes cannot
stand in for the sheet here: GDAL regroups a MultiPolygon's rings by their orientation seen
from above when it reads one back (measured: two of the eleven buildings come back with
polygons of four rings, and the triangles of all eleven in another order), so the real
reader is exercised here only by a refusal it makes inside the step.

Does NOT prove: that swisstopo's own MultiPatch reads the same way (the real run, checked
against design's chunk hashes in config/buildings.json); that the owner's Windows PC reads
the same numbers (its GDAL is its wheel's; the step's own comparison says so if not).
"""

import copy
import json
import re
from pathlib import Path

import pytest
from computed_for import recorded
from synthetic_sheets import raw_folder, sheet_zip

import mattini.__main__ as cli
from mattini import buildings, lock, manifest, terrain
from mattini.buildings import (
    BuildingsError,
    build_buildings,
    check_buildings_config,
    load_buildings_config,
)
from mattini.datasets import load_datasets
from mattini.terrain import load_terrain_config
from mattini.world import load_world

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "shared" / "buildings_fixture"
GENERATED = FIXTURE / "generated"
SHEET = "1249-42"
BUILDINGS_COMMAND = "python -m mattini buildings"
DOWNLOAD_COMMAND = "python -m mattini download buildings"
LOCK_COMMAND = "python -m mattini lock buildings"


def _features(data: bytes) -> list[dict]:
    """The features source.json's bytes hold, as the reader hands them over."""
    source = json.loads(data.decode("utf-8"))
    return [
        {
            "uuid": f["uuid"],
            "objektart": f["objektart"],
            "triangles": [tuple(tuple(p) for p in t) for t in f["triangles"]],
        }
        for f in source["features"]
    ]


@pytest.fixture
def case(tmp_path, monkeypatch):
    """The fixture world and configs, a raw folder holding source.json as sheet 1249-42,
    and the stand-in reader, which records the bytes it was handed."""
    datasets = load_datasets(FIXTURE / "datasets.json")
    raw_root = tmp_path / "raw"
    source = (FIXTURE / "source.json").read_bytes()
    pinned = raw_folder(raw_root, datasets, {SHEET: source})
    handed = []

    def read_source(data: bytes, sheet: str) -> list[dict]:
        handed.append((sheet, data))
        return _features(data)

    monkeypatch.setattr(buildings, "read_sheet", read_source)
    # the raw folder names the sheet as the download does, where the fixture's lock names it
    # source.json: the same SHA-256, another entry, which the config records (M2-07)
    config = load_buildings_config(FIXTURE / "buildings.json")
    return {
        "tmp": tmp_path,
        "world": load_world(FIXTURE / "world.json"),
        "datasets": datasets,
        "lock": pinned,
        "buildings": recorded(config, FIXTURE / "world.json", pinned, "swissbuildings3d"),
        "terrain": load_terrain_config(FIXTURE / "terrain.json"),
        "raw": raw_root,
        "out": tmp_path / "generated",
        "sheet_dir": raw_root / "swissbuildings3d" / "2020",
        "source": source,
        "handed": handed,
    }


def _build(case, **changes):
    args = {key: case[key] for key in ("world", "datasets", "lock", "buildings", "terrain")}
    args.update(changes)
    return build_buildings(
        args["world"],
        args["datasets"],
        args["lock"],
        args["buildings"],
        args["terrain"],
        case["raw"],
        case["out"],
    )


def _refused(case, match, **changes):
    with pytest.raises(BuildingsError, match=match) as refusal:
        _build(case, **changes)
    assert not case["out"].exists(), "a refusal must write nothing"
    return str(refusal.value)


def test_the_fixture_sheet_builds_the_fixture_s_files(case):
    messages = []
    block = build_buildings(
        case["world"],
        case["datasets"],
        case["lock"],
        case["buildings"],
        case["terrain"],
        case["raw"],
        case["out"],
        progress=messages.append,
    )
    assert case["handed"] == [(SHEET, case["source"])]  # the bytes hashed are the bytes read
    assert sorted(p.name for p in (case["out"] / "buildings").iterdir()) == sorted(
        p.name for p in (GENERATED / "buildings").iterdir()
    )
    for path in sorted((GENERATED / "buildings").iterdir()):
        assert (case["out"] / "buildings" / path.name).read_bytes() == path.read_bytes(), path
    assert block == json.loads((GENERATED / "buildings" / "fixture.json").read_bytes())
    assert f"sheet {SHEET}: 11 features read, 8 selected" in messages
    assert "8 buildings in 3 chunks: 71 vertices, 110 triangles, 2172 bytes" in messages


def test_a_second_run_writes_the_same_bytes(case):
    _build(case)
    first = {p.name: p.read_bytes() for p in (case["out"] / "buildings").iterdir()}
    _build(case)
    second = {p.name: p.read_bytes() for p in (case["out"] / "buildings").iterdir()}
    assert first == second


def test_a_build_removes_the_chunks_an_earlier_build_left(case):
    """M2 R1 G-06, the pipeline half: chunk files the new description does not list go.

    An earlier build's chunks in `buildings/` (here a village tile and a tile of the
    fixture's own area the new build does not fill), a stray file that is not a chunk and
    a chunk-like name that is not `*.bin`: the build removes the two chunks, keeps the rest
    and the description, and says how many it removed. Harm: every file in
    assets/generated/ ships in an export, so an earlier build's chunks grow the .pck (M2 R1
    measured 1 MiB of 5.2 MiB left under GitHub's limit) though the game never reads them.
    """
    buildings_dir = case["out"] / "buildings"
    buildings_dir.mkdir(parents=True)
    stale = {"2622-1095.bin": b"\0" * 1024, "2651-1149.bin": b"\1" * 24}
    kept = {"notes.txt": b"not a chunk", "2622-1095.bin.part": b"an interrupted write"}
    for name, data in {**stale, **kept}.items():
        (buildings_dir / name).write_bytes(data)

    def build():
        messages = []
        block = build_buildings(
            case["world"],
            case["datasets"],
            case["lock"],
            case["buildings"],
            case["terrain"],
            case["raw"],
            case["out"],
            progress=messages.append,
        )
        return block, [m for m in messages if m.startswith("removed ")]

    block, removed = build()
    listed = sorted(Path(chunk["file"]).name for chunk in block["chunks"])
    assert listed == ["2650-1149.bin", "2650-1150.bin", "2651-1150.bin"]
    after = sorted([*listed, "fixture.json", *kept])
    assert sorted(p.name for p in buildings_dir.iterdir()) == after
    for name, data in kept.items():
        assert (buildings_dir / name).read_bytes() == data
    for path in sorted((GENERATED / "buildings").iterdir()):
        assert (buildings_dir / path.name).read_bytes() == path.read_bytes(), path
    where = f"of an earlier build that fixture.json does not list from {buildings_dir}"
    assert removed == [f"removed 2 chunk files {where}"]

    _, removed = build()  # nothing left to remove, and it says so
    assert removed == [f"removed 0 chunk files {where}"]
    assert sorted(p.name for p in buildings_dir.iterdir()) == after


def test_a_refused_build_removes_nothing(case):
    """The removal comes after writing: a build refused before it leaves every file."""
    buildings_dir = case["out"] / "buildings"
    buildings_dir.mkdir(parents=True)
    (buildings_dir / "2622-1095.bin").write_bytes(b"\0" * 1024)
    config = _expecting(case, lambda e: e.update({"2650-1150": "0" * 64}))
    with pytest.raises(BuildingsError, match="2650-1150"):
        _build(case, buildings=config)
    assert sorted(p.name for p in buildings_dir.iterdir()) == ["2622-1095.bin"]


def test_the_manifest_after_the_step_is_the_fixture_s(case):
    _build(case)
    path = manifest.write_manifest(
        case["out"],
        FIXTURE / "world.json",
        terrain_config_path=FIXTURE / "terrain.json",
        datasets_path=FIXTURE / "datasets.json",
        lock_path=FIXTURE / "datasets.lock.json",
        buildings_config_path=FIXTURE / "buildings.json",
    )
    assert path.read_bytes() == (GENERATED / "manifest.json").read_bytes()


# ------------------------------------------------------------------ the expected chunks


def _expecting(case, change):
    config = copy.deepcopy(case["buildings"])
    change(config["areas"]["fixture"]["expected_sha256"])
    return config


@pytest.mark.parametrize(
    ("change", "tile"),
    [
        (lambda e: e.update({"2650-1150": "0" * 64}), "2650-1150"),
        (lambda e: e.update({"2651-1149": "1" * 64}), "2651-1149"),
        (lambda e: e.pop("2651-1150"), "2651-1150"),
    ],
    ids=["another-sha256", "a-tile-not-built", "a-tile-not-expected"],
)
def test_chunks_that_are_not_the_expected_ones_are_refused_before_writing(case, change, tile):
    config = _expecting(case, change)
    message = _refused(case, tile, buildings=config)
    assert "config/buildings.json" in message and "two independent ways" in message
    built = json.loads((GENERATED / "buildings" / "fixture.json").read_text("utf-8"))
    built = {c["tile"]: c["sha256"] for c in built["chunks"]}
    expected = config["areas"]["fixture"]["expected_sha256"]
    for value in (built.get(tile), expected.get(tile)):
        if value is not None:
            assert value in message  # both values are named where there are two


def test_a_buildings_config_for_another_area_is_refused(case):
    config = {"schema": 1, "areas": {"village": case["buildings"]["areas"]["fixture"]}}
    _refused(case, "'village'", buildings=config)


# ------------------------------------------------------------------ the inputs


def _edit_provenance(case, change):
    path = case["sheet_dir"] / "provenance.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(json.dumps(data), encoding="utf-8")


@pytest.mark.parametrize(
    "change",
    [
        lambda p: p.update(edition="2019"),
        lambda p: p.update(collection="ch.swisstopo.swissbuildings3d_2"),
        lambda p: p.update(dataset="swissalti3d"),
        lambda p: p["sheets"].append(dict(p["sheets"][0], sheet="1249-41")),
        lambda p: p.update(sheets=[]),
        lambda p: p["sheets"][0].update(file="../elsewhere.zip"),
    ],
    ids=["edition", "collection", "dataset", "another-sheet", "no-sheet", "path"],
)
def test_a_provenance_that_does_not_match_the_config_is_refused(case, change):
    _edit_provenance(case, change)
    _refused(case, DOWNLOAD_COMMAND)


def test_without_a_download_the_step_names_the_download(case):
    (case["sheet_dir"] / "provenance.json").unlink()
    _refused(case, DOWNLOAD_COMMAND)


def test_a_sheet_whose_bytes_changed_is_refused(case):
    (entry,) = json.loads((case["sheet_dir"] / "provenance.json").read_bytes())["sheets"]
    path = case["sheet_dir"] / entry["file"]
    data = bytearray(path.read_bytes())
    data[len(data) // 2] ^= 1
    path.write_bytes(bytes(data))
    message = _refused(case, DOWNLOAD_COMMAND)
    assert SHEET in message and entry["sha256"] in message


def test_a_missing_sheet_file_is_refused(case):
    (entry,) = json.loads((case["sheet_dir"] / "provenance.json").read_bytes())["sheets"]
    (case["sheet_dir"] / entry["file"]).unlink()
    _refused(case, DOWNLOAD_COMMAND)


def _locked(case, change):
    pinned = copy.deepcopy(case["lock"])
    change(pinned["datasets"]["swissbuildings3d"])
    return pinned


def _adopting(case, pinned):
    """The case's buildings config recording `pinned` (design adopted it, M2-07): a lock the
    config was not computed for is refused before any sheet is read."""
    return recorded(case["buildings"], case["world"], pinned, "swissbuildings3d")


@pytest.mark.parametrize(
    ("change", "command"),
    [
        (lambda e: e["sheets"][SHEET].update(sha256="ab" * 32), DOWNLOAD_COMMAND),
        (lambda e: e["sheets"][SHEET].update(file="other.gdb.zip"), DOWNLOAD_COMMAND),
        (lambda e: e.update(edition="2019"), LOCK_COMMAND),
        (lambda e: e["sheets"].update({"1249-41": e["sheets"][SHEET]}), LOCK_COMMAND),
        (lambda e: e["sheets"].clear(), LOCK_COMMAND),
    ],
    ids=["sha256", "file", "edition", "another-sheet", "no-sheet"],
)
def test_a_lock_that_does_not_pin_the_downloaded_sheets_is_refused(case, change, command):
    """The lock changed and adopted by design; the download not run again since."""
    pinned = _locked(case, change)
    _refused(case, command, lock=pinned, buildings=_adopting(case, pinned))


def test_a_lock_without_buildings_is_refused(case):
    _refused(case, LOCK_COMMAND, lock={"schema": 1, "datasets": {}})


def test_a_datasets_config_without_buildings_is_refused(case):
    datasets = {k: v for k, v in case["datasets"].items() if k != "swissbuildings3d"}
    _refused(case, "swissbuildings3d", datasets=datasets)


def test_a_refusal_of_the_rule_names_the_sheet_and_the_uuid(case):
    features = _features(case["source"])
    features[0]["triangles"] = features[0]["triangles"][1:]  # an open solid, inside the area
    data = json.dumps({"features": features}).encode("utf-8")
    pinned = raw_folder(case["raw"], case["datasets"], {SHEET: data})
    config = _adopting(case, pinned)
    message = _refused(case, re.escape(features[0]["uuid"]), lock=pinned, buildings=config)
    assert f"sheet {SHEET}" in message and "closed" in message


def test_a_refusal_of_the_real_reader_names_the_sheet_and_the_uuid(case, monkeypatch):
    monkeypatch.undo()  # the real reader, on a FileGDB fiona writes
    a, b, c, d = (
        (2650950.0, 1150000.0, 1500.0),
        (2650960.0, 1150000.0, 1500.0),
        (2650960.0, 1150010.0, 1500.0),
        (2650950.0, 1150010.0, 1500.0),
    )
    triangle = {"uuid": "{GOOD}", "objektart": "Gebaeude Einzelhaus", "triangles": [(a, b, c)]}
    quad = dict(triangle, uuid="{QUAD}", triangles=[(a, b, c, d)])
    data = sheet_zip(case["tmp"], [triangle, quad])
    pinned = raw_folder(case["raw"], case["datasets"], {SHEET: data})
    where = re.escape(f"sheet {SHEET}, UUID {{QUAD}}")
    message = _refused(case, where, lock=pinned, buildings=_adopting(case, pinned))
    assert "points" in message


# ------------------------------------------------------------------ the config


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d.update(schema=2),
        lambda d: d["areas"].update(backdrop=d["areas"]["village"]),
        lambda d: d["areas"].clear(),
        lambda d: d["areas"]["village"].update(spacing_m=0.5),
        lambda d: d["areas"]["village"]["expected_sha256"].update({"2623": "0" * 64}),
        lambda d: d["areas"]["village"]["expected_sha256"].update({"1-2": "A" * 64}),
        lambda d: d["areas"]["village"]["expected_sha256"].update({"1-2": "0" * 63}),
        lambda d: d.update(extra=1),
        lambda d: d["areas"]["village"].pop("computed_for"),
        lambda d: d["areas"]["village"].update(computed_for=["0" * 64, "0" * 64]),
        lambda d: d["areas"]["village"]["computed_for"].pop("inputs_sha256"),
        lambda d: d["areas"]["village"]["computed_for"].update(tiles_sha256="0" * 64),
        lambda d: d["areas"]["village"]["computed_for"].update(world_sha256="A" * 64),
        lambda d: d["areas"]["village"]["computed_for"].update(inputs_sha256="0" * 65),
    ],
    ids=[
        "schema",
        "two-areas",
        "no-area",
        "extra-key",
        "tile-id",
        "upper-case",
        "short",
        "top",
        "no-computed-for",
        "computed-for-not-an-object",
        "computed-for-key-missing",
        "computed-for-key-added",
        "computed-for-upper-case",
        "computed-for-long",
    ],
)
def test_a_bad_buildings_config_is_refused_naming_the_file(tmp_path, change):
    data = json.loads((REPO / "config" / "buildings.json").read_text(encoding="utf-8"))
    change(data)
    path = tmp_path / "buildings.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(BuildingsError) as refusal:
        load_buildings_config(path)
    assert str(path) in str(refusal.value)


def test_the_committed_config_expects_the_village_s_six_chunks():
    config = load_buildings_config()
    check_buildings_config(config)
    (area,) = config["areas"]
    assert area == terrain.configured_area(load_terrain_config())
    assert len(config["areas"][area]["expected_sha256"]) == 6


# ------------------------------------------------------------------ the command line


def test_the_command_builds_then_writes_the_manifest(case, monkeypatch, capsys):
    lock_path = case["tmp"] / "datasets.lock.json"
    lock.write_lock(case["lock"], lock_path)
    config_path = case["tmp"] / "buildings.json"
    config_path.write_text(json.dumps(case["buildings"]), encoding="utf-8")
    monkeypatch.setattr(lock, "LOCK_PATH", lock_path)
    monkeypatch.setattr(cli, "load_world", lambda: case["world"])
    monkeypatch.setattr(cli, "load_datasets", lambda: case["datasets"])
    monkeypatch.setattr(terrain, "load_terrain_config", lambda: case["terrain"])
    monkeypatch.setattr(buildings, "load_buildings_config", lambda: case["buildings"])
    monkeypatch.setattr(
        cli,
        "write_manifest",
        lambda out: manifest.write_manifest(
            out,
            FIXTURE / "world.json",
            terrain_config_path=FIXTURE / "terrain.json",
            datasets_path=FIXTURE / "datasets.json",
            lock_path=lock_path,
            buildings_config_path=config_path,
        ),
    )
    out = case["out"]
    assert cli.main(["buildings", "--raw", str(case["raw"]), "--out", str(out)]) == 0
    captured = capsys.readouterr()
    assert captured.out == f"{out / 'manifest.json'}\n"
    assert f"sheet {SHEET}: 11 features read, 8 selected" in captured.err
    assert "8 buildings in 3 chunks" in captured.err
    assert "removed 0 chunk files of an earlier build" in captured.err
    written = json.loads((out / "manifest.json").read_bytes())
    assert written["buildings"] == json.loads((out / "buildings" / "fixture.json").read_bytes())


def test_the_command_without_a_download_fails_naming_the_download(tmp_path, capsys):
    out = tmp_path / "generated"
    assert cli.main(["buildings", "--raw", str(tmp_path / "raw"), "--out", str(out)]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("mattini: error: ")
    assert "provenance.json" in captured.err and f"`{DOWNLOAD_COMMAND}`" in captured.err
    assert not out.exists()
