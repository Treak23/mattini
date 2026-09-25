"""Pinning tests for brief M2-04: the pipeline reproduces the shared buildings fixture.

Pinned decisions (docs/SPEC.md §8, the buildings): the fixture
(tests/shared/buildings_fixture/, its outcomes in tests/shared/buildings_vectors.json) is a
synthetic world with eleven buildings as the reader hands them over. They include:
- a negative solid that must be reversed and a positive one that must not;
- centres exactly on the area's west, east and north edges and on a tile's row boundary;
- a building whose vertex mean and first vertex lie in another tile than its
  bounding-box centre, which a 32-bit centre would also misplace;
- two buildings in one chunk whose UUID order reverses their reading order.

Design computed the expected files two independent ways at M2 planning (identical
bytes). The pipeline must reproduce `generated/` byte for byte; the game's building tests
read the same bytes (brief M2-05): the seam (lesson 3).

Does NOT prove: that the reader turns swisstopo's files into these features
(test_buildings_read.py and the real run); that the game draws them (M2-05).
"""

import hashlib
import json
from pathlib import Path

from mattini.buildings import build_chunks, load_buildings_config, write_buildings
from mattini.manifest import write_manifest
from mattini.world import load_world

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "shared" / "buildings_fixture"
GENERATED = FIXTURE / "generated"
VECTORS = json.loads((REPO / "tests" / "shared" / "buildings_vectors.json").read_text("utf-8"))
BOX = (2650900.0, 2651100.0, 1149950.0, 1150050.0)


def _source() -> dict:
    return json.loads((FIXTURE / "source.json").read_text(encoding="utf-8"))


def _features() -> list[dict]:
    return [
        {
            "uuid": f["uuid"],
            "objektart": f["objektart"],
            "triangles": [tuple(tuple(p) for p in t) for t in f["triangles"]],
        }
        for f in _source()["features"]
    ]


def _block() -> dict:
    return json.loads((GENERATED / "buildings" / "fixture.json").read_text(encoding="utf-8"))


def _chunks():
    return build_chunks(_features(), load_world(FIXTURE / "world.json"), "fixture")


def test_the_chunks_hold_the_designed_buildings():
    chunks = _chunks()
    expected = VECTORS["expected"]["chunks"]
    assert [c["tile"] for c in chunks] == [e["tile"] for e in expected]
    assert [c["buildings"] for c in chunks] == [len(e["buildings"]) for e in expected]
    for chunk, entry in zip(chunks, _block()["chunks"], strict=True):
        assert chunk["tile"] == entry["tile"]
        assert (chunk["vertices"], chunk["triangles"]) == (entry["vertices"], entry["triangles"])
        assert chunk["data"] == (GENERATED / entry["file"]).read_bytes(), entry["tile"]
        assert hashlib.sha256(chunk["data"]).hexdigest() == entry["sha256"]


def test_the_config_expects_the_fixture_s_chunks():
    config = load_buildings_config(FIXTURE / "buildings.json")
    expected = {c["tile"]: c["sha256"] for c in _block()["chunks"]}
    assert config["areas"]["fixture"]["expected_sha256"] == expected


def test_write_buildings_and_manifest_write_the_fixture_files(tmp_path):
    block = _block()
    source = _source()
    assert block["source"]["sheets"] == [
        {
            "sha256": hashlib.sha256((FIXTURE / "source.json").read_bytes()).hexdigest(),
            "sheet": source["sheet"],
        }
    ]
    written = write_buildings(
        tmp_path, "fixture", _chunks(), BOX, block["world_sha256"], block["source"]
    )
    assert written == block
    assert (tmp_path / "buildings" / "fixture.json").read_bytes() == (
        GENERATED / "buildings" / "fixture.json"
    ).read_bytes()
    for entry in block["chunks"]:
        assert (tmp_path / entry["file"]).read_bytes() == (GENERATED / entry["file"]).read_bytes()
    path = write_manifest(
        tmp_path,
        FIXTURE / "world.json",
        terrain_config_path=FIXTURE / "terrain.json",
        datasets_path=FIXTURE / "datasets.json",
        lock_path=FIXTURE / "datasets.lock.json",
        buildings_config_path=FIXTURE / "buildings.json",
    )
    assert path.read_bytes() == (GENERATED / "manifest.json").read_bytes()
    manifest = json.loads(path.read_bytes())
    assert set(manifest) == {"buildings", "schema", "terrain", "world", "world_sha256"}
    assert manifest["terrain"] is None
    assert manifest["buildings"] == block
