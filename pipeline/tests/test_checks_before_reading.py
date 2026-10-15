"""Pinning tests for brief M3-01 (M2 V1-P-03): a step's world and inputs checks come first.

Pinned decisions (docs/SPEC.md §8, the expected output; brief M2-07): the terrain step
reads no tile, and the buildings step no map sheet, before its world check
(`computed_for.world_sha256`) and its inputs check (`computed_for.inputs_sha256`) have
passed. Every file a step opens is recorded here (builtins.open and io.open, which
pathlib's read_bytes and write_bytes use), and a refusal by either check leaves no input
file opened but provenance.json. The positive controls show that the recorder sees an
input read once both checks pass, so an empty record is a finding, not a blind spot.

Harm prevented: the review's V1-P-03. The earlier tests asserted only that a refusal wrote
nothing, so the checks moved after the reading (the 96 MB mosaic of six tiles built, then
refused) passed them, while a test docstring said "refused before the tile is read".

Does NOT prove: that no read happens through another door than Python's open (os.open,
GDAL opening a path itself); the step reads its inputs as bytes through open today.
"""

import builtins
import hashlib
import io
import json
import os
import shutil
from pathlib import Path

import pytest
from one_tile import AREA, canonical_sha256, one_tile_case, relay, write_tile, write_world

from mattini.buildings import BuildingsError, build_buildings, load_buildings_config
from mattini.datasets import load_datasets
from mattini.terrain import TerrainError, build_terrain
from mattini.world import REPO, load_world

BUILDINGS_FIXTURE = REPO / "tests" / "shared" / "buildings_fixture"
SHEET = "1249-42"
MACHINE = "this machine or this code"


@pytest.fixture
def opened(monkeypatch):
    """Every path opened through builtins.open or io.open while the test runs."""
    paths = []
    real_open = io.open

    def recording_open(file, *args, **kwargs):
        if isinstance(file, str | bytes | os.PathLike):
            paths.append(Path(os.fsdecode(file)).resolve())
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", recording_open)
    monkeypatch.setattr(io, "open", recording_open)
    return paths


def _inputs_read(paths, raw_root) -> list[str]:
    """The files under the raw folder that were opened, provenance.json aside."""
    root = Path(raw_root).resolve()
    return [p.name for p in paths if p.is_relative_to(root) and p.name != "provenance.json"]


# ---------------------------------------------------------------------- the terrain


def _build_terrain(case, world_path=None):
    return build_terrain(
        load_world(world_path or case["world_path"]),
        case["datasets"],
        case["lock"],
        case["config"],
        case["raw_root"],
        case["out"],
    )


def test_once_both_checks_pass_the_tile_is_read_and_seen(tmp_path, opened):
    """Positive control: the recorder sees the step read its tile."""
    case = one_tile_case(tmp_path)
    opened.clear()  # the test's own writing and hashing of the tile does not count
    block = _build_terrain(case)
    assert block["area"] == AREA
    assert _inputs_read(opened, case["raw_root"]) == [case["tile_path"].name]


def test_a_changed_world_is_refused_before_any_tile_is_read(tmp_path, opened):
    case = one_tile_case(tmp_path)
    moved = write_world(tmp_path / "moved", lambda d: d["origin_lv95"].update(e=2600000.0))
    opened.clear()
    with pytest.raises(TerrainError) as refused:
        _build_terrain(case, moved)
    assert "config/world.json now has" in str(refused.value)
    assert _inputs_read(opened, case["raw_root"]) == []
    assert not case["out"].exists()


def test_republished_and_relocked_inputs_are_refused_before_any_tile_is_read(tmp_path, opened):
    """The tile rewritten 0.25 m higher, the lock and provenance.json pinning it, the
    terrain config not recomputed: refused by the inputs check, and no tile opened."""
    case = one_tile_case(tmp_path)
    relay(case, write_tile(case["tile_path"], 1600.25))
    recorded = case["config"]["areas"][AREA]["computed_for"]["inputs_sha256"]
    assert canonical_sha256(case["lock"]["datasets"]["swissalti3d"]) != recorded
    opened.clear()
    with pytest.raises(TerrainError) as refused:
        _build_terrain(case)
    message = str(refused.value)
    assert "datasets.lock.json" in message and MACHINE not in message
    assert _inputs_read(opened, case["raw_root"]) == []
    assert not case["out"].exists()


# ---------------------------------------------------------------------- the buildings


def _buildings_case(tmp_path) -> dict:
    """The shared buildings fixture's configs and lock, and a raw folder holding its
    source.json as sheet 1249-42, as the fixture's own lock names it."""
    datasets = load_datasets(BUILDINGS_FIXTURE / "datasets.json")
    pinned = json.loads((BUILDINGS_FIXTURE / "datasets.lock.json").read_text(encoding="utf-8"))
    entry = pinned["datasets"]["swissbuildings3d"]["sheets"][SHEET]
    raw_root = tmp_path / "raw"
    folder = raw_root / "swissbuildings3d" / datasets["swissbuildings3d"]["edition"]
    folder.mkdir(parents=True)
    shutil.copy(BUILDINGS_FIXTURE / "source.json", folder / entry["file"])
    provenance = {
        "attribution": datasets["swissbuildings3d"]["attribution"],
        "collection": datasets["swissbuildings3d"]["collection"],
        "dataset": "swissbuildings3d",
        "edition": datasets["swissbuildings3d"]["edition"],
        "schema": 1,
        "sheets": [{"file": entry["file"], "sha256": entry["sha256"], "sheet": SHEET}],
    }
    (folder / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    return {
        "tmp": tmp_path,
        "world_path": BUILDINGS_FIXTURE / "world.json",
        "datasets": datasets,
        "lock": pinned,
        "raw_root": raw_root,
        "sheet_path": folder / entry["file"],
        "out": tmp_path / "generated",
    }


def _build_buildings(case, world_path=None):
    return build_buildings(
        load_world(world_path or case["world_path"]),
        case["datasets"],
        case["lock"],
        load_buildings_config(BUILDINGS_FIXTURE / "buildings.json"),
        json.loads((BUILDINGS_FIXTURE / "terrain.json").read_text(encoding="utf-8")),
        case["raw_root"],
        case["out"],
    )


def test_once_both_checks_pass_the_sheet_is_read_and_seen(tmp_path, opened):
    """Positive control: the step reads its sheet (whose JSON bytes the real reader then
    refuses as no zip: what matters is that the recorder saw the read)."""
    case = _buildings_case(tmp_path)
    opened.clear()
    with pytest.raises(BuildingsError, match="not a zip"):
        _build_buildings(case)
    assert _inputs_read(opened, case["raw_root"]) == [case["sheet_path"].name]


def test_a_changed_world_is_refused_before_any_sheet_is_read(tmp_path, opened):
    case = _buildings_case(tmp_path)
    data = json.loads(Path(case["world_path"]).read_text(encoding="utf-8"))
    data["origin_lv95"]["e"] += 1000.0
    moved = tmp_path / "moved" / "world.json"
    moved.parent.mkdir()
    moved.write_text(json.dumps(data, indent=2), encoding="utf-8")
    opened.clear()
    with pytest.raises(BuildingsError) as refused:
        _build_buildings(case, moved)
    assert "config/world.json now has" in str(refused.value)
    assert _inputs_read(opened, case["raw_root"]) == []
    assert not case["out"].exists()


def test_republished_and_relocked_sheets_are_refused_before_any_sheet_is_read(tmp_path, opened):
    case = _buildings_case(tmp_path)
    case["sheet_path"].write_bytes(case["sheet_path"].read_bytes() + b"\n")
    sha256 = hashlib.sha256(case["sheet_path"].read_bytes()).hexdigest()
    case["lock"]["datasets"]["swissbuildings3d"]["sheets"][SHEET]["sha256"] = sha256
    provenance = case["sheet_path"].parent / "provenance.json"
    data = json.loads(provenance.read_text(encoding="utf-8"))
    data["sheets"][0]["sha256"] = sha256
    provenance.write_text(json.dumps(data, indent=2), encoding="utf-8")
    opened.clear()
    with pytest.raises(BuildingsError) as refused:
        _build_buildings(case)
    message = str(refused.value)
    assert "datasets.lock.json" in message and MACHINE not in message
    assert _inputs_read(opened, case["raw_root"]) == []
    assert not case["out"].exists()
