"""Pinning tests for brief M3-01 (M2 V1-P-06, its pipeline half): no `*.part` after a step.

Pinned decisions (docs/SPEC.md §8, the files; brief M3-01): every file a step writes goes
through `<name>.part` and a rename, so a run cut between the two leaves the `.part`
behind, and the export shipped it (measured in 0.2.0's `.pck` by the M2 review). After a
build that succeeds, the terrain step leaves no `*.part` in `<out>/terrain/` and the
buildings step none in `<out>/buildings/`, whoever wrote them; each step cleans its own
folder only, so a `.part` in the other step's folder is kept. The built files themselves
are the ones expected (design's values: the one-tile world's, the shared buildings
fixture's), so the cleaning removed nothing it should not.

Does NOT prove: that the export leaves `*.part` out (the presets' exclude_filter, brief
M3-08); what a refused build does with them (a refusal writes and removes nothing).
"""

import hashlib
import json
import shutil

from one_tile import AREA, HEIGHTS_SHA256, one_tile_case

from mattini import buildings
from mattini.buildings import build_buildings, load_buildings_config
from mattini.datasets import load_datasets
from mattini.terrain import build_terrain
from mattini.world import REPO, load_world

BUILDINGS_FIXTURE = REPO / "tests" / "shared" / "buildings_fixture"
SHEET = "1249-42"
CUT_SHORT = b"a write cut short"


def test_the_terrain_step_removes_part_files_from_its_folder(tmp_path):
    case = one_tile_case(tmp_path)
    terrain_dir, other_dir = case["out"] / "terrain", case["out"] / "buildings"
    terrain_dir.mkdir(parents=True)
    other_dir.mkdir()
    for name in (f"{AREA}.f32.part", f"{AREA}.json.part", "another_area.f32.part"):
        (terrain_dir / name).write_bytes(CUT_SHORT)
    (other_dir / "2601-1199.bin.part").write_bytes(CUT_SHORT)

    build_terrain(
        load_world(case["world_path"]),
        case["datasets"],
        case["lock"],
        case["config"],
        case["raw_root"],
        case["out"],
    )
    assert sorted(p.name for p in terrain_dir.glob("*.part")) == []
    heights = (terrain_dir / f"{AREA}.f32").read_bytes()
    assert hashlib.sha256(heights).hexdigest() == HEIGHTS_SHA256
    assert json.loads((terrain_dir / f"{AREA}.json").read_bytes())["sha256"] == HEIGHTS_SHA256
    assert (other_dir / "2601-1199.bin.part").read_bytes() == CUT_SHORT  # not its folder


def _features(data: bytes) -> list[dict]:
    """The features the fixture's source.json holds, as the reader hands them over."""
    return [
        {
            "uuid": f["uuid"],
            "objektart": f["objektart"],
            "triangles": [tuple(tuple(p) for p in t) for t in f["triangles"]],
        }
        for f in json.loads(data.decode("utf-8"))["features"]
    ]


def test_the_buildings_step_removes_part_files_from_its_folder(tmp_path, monkeypatch):
    """The shared buildings fixture's source.json stands in for sheet 1249-42, as the
    fixture's own lock names it, and a stand-in reader parses it (test_buildings_step.py)."""
    monkeypatch.setattr(buildings, "read_sheet", lambda data, sheet: _features(data))
    datasets = load_datasets(BUILDINGS_FIXTURE / "datasets.json")
    pinned = json.loads((BUILDINGS_FIXTURE / "datasets.lock.json").read_text(encoding="utf-8"))
    entry = pinned["datasets"]["swissbuildings3d"]["sheets"][SHEET]
    raw = tmp_path / "raw" / "swissbuildings3d" / datasets["swissbuildings3d"]["edition"]
    raw.mkdir(parents=True)
    shutil.copy(BUILDINGS_FIXTURE / "source.json", raw / entry["file"])
    provenance = {
        "attribution": datasets["swissbuildings3d"]["attribution"],
        "collection": datasets["swissbuildings3d"]["collection"],
        "dataset": "swissbuildings3d",
        "edition": datasets["swissbuildings3d"]["edition"],
        "schema": 1,
        "sheets": [{"file": entry["file"], "sha256": entry["sha256"], "sheet": SHEET}],
    }
    (raw / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    out = tmp_path / "generated"
    buildings_dir, other_dir = out / "buildings", out / "terrain"
    buildings_dir.mkdir(parents=True)
    other_dir.mkdir()
    for name in ("2650-1150.bin.part", "fixture.json.part", "2999-1999.bin.part"):
        (buildings_dir / name).write_bytes(CUT_SHORT)
    (other_dir / "fixture.f32.part").write_bytes(CUT_SHORT)

    build_buildings(
        load_world(BUILDINGS_FIXTURE / "world.json"),
        datasets,
        pinned,
        load_buildings_config(BUILDINGS_FIXTURE / "buildings.json"),
        json.loads((BUILDINGS_FIXTURE / "terrain.json").read_text(encoding="utf-8")),
        tmp_path / "raw",
        out,
    )
    assert sorted(p.name for p in buildings_dir.glob("*.part")) == []
    generated = BUILDINGS_FIXTURE / "generated" / "buildings"
    assert sorted(p.name for p in buildings_dir.iterdir()) == sorted(
        p.name for p in generated.iterdir()
    )
    for path in generated.iterdir():
        assert (buildings_dir / path.name).read_bytes() == path.read_bytes(), path.name
    assert (other_dir / "fixture.f32.part").read_bytes() == CUT_SHORT  # not its folder
