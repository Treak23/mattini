"""Pinning tests for brief M3-07: the pipeline reproduces the shared trees fixture.

Pinned decisions (m3-design §5, the trees): the rule, on the area's 0.5 m pixels, from the
DSM and DTM mosaics, the buildings as the buildings step's reader hands them over and the
TLM polygons as trees.py takes them ({uuid, objektart, polygons}); the chunk files
`trees/<tile>.bin`, 20 bytes per tree (x, y, z, height_m, crown_radius_m as little-endian
float32), trees in raster order of their top pixels, no chunk for a tile without a tree;
the description `trees/<area>.json` with exactly its keys, its `parameters` and the four
datasets' sources. A top is dropped when its chm is above 40 m or below 3 m or its DTM slope
is 60 degrees or more; the crown radius is min(d / 2, height / 4), clamped to 1.0-6.0 m, in
64-bit and then rounded once to float32, d the distance to the nearest other kept tree of the
area (infinite when there is none), height the chm at the top. The fixture
(tests/shared/trees_fixture/, its cases and trees named in tests/shared/trees_vectors.json)
holds 35 crafted cases in a synthetic world: plateau ties, the outer ring, the building
margin's exact radius, buildings the buildings step does not select, TLM footprints with a
hole, without a swissBUILDINGS3D twin and underground (OBJEKTART 16, not a footprint), rock
edges through pixel centres, the window's boundary, a pit, a pole, a gap in a crown, the
height, low and slope drops, crown radii decided by d / 2, by height / 4, clamped to 1.0 and to
6.0, nearest neighbours across chunks. Design computed its expected files two independent
ways (identical bytes) and ran 54 likely wrong implementations on it: 53 change its bytes.

Does NOT prove: that the reader turns swisstopo's files into these inputs (the real run
against config/trees.json does); that the game draws the trees (M3-11).
"""

import hashlib
import json
import math
import struct
from pathlib import Path

import numpy as np
import pytest

from mattini.trees import build_tree_chunks, write_trees
from mattini.world import load_world

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "shared" / "trees_fixture"
GENERATED = FIXTURE / "generated"
VECTORS = json.loads((REPO / "tests" / "shared" / "trees_vectors.json").read_text("utf-8"))
SIZE = 96  # pixels per side
BOX = (2650976.0, 2651024.0, 1149976.0, 1150024.0)


def _raster(name: str) -> np.ndarray:
    return np.fromfile(FIXTURE / name, dtype="<f4").reshape(SIZE, SIZE)


def _inputs() -> tuple:
    buildings = json.loads((FIXTURE / "buildings.json").read_text("utf-8"))["features"]
    tlm = json.loads((FIXTURE / "tlm.json").read_text("utf-8"))
    return (
        _raster("dsm.f32"),
        _raster("dtm.f32"),
        buildings,
        tlm["TLM_GEBAEUDE_FOOTPRINT"],
        tlm["TLM_BODENBEDECKUNG"],
    )


def _chunks() -> list[dict]:
    world = load_world(FIXTURE / "world.json")
    return build_tree_chunks(*_inputs(), world, "fixture")


def _block() -> dict:
    return json.loads((GENERATED / "trees" / "fixture.json").read_text("utf-8"))


def _records(data: bytes) -> list[tuple[float, ...]]:
    assert len(data) % 20 == 0
    return [struct.unpack_from("<5f", data, offset) for offset in range(0, len(data), 20)]


def _local_xz(pixel: list[int]) -> tuple[float, float]:
    """The local x, z of a pixel's centre, by hand for the fixture world (owner's axes)."""
    i, j = pixel
    east, north = 2650976.25 + 0.5 * j, 1150023.75 - 0.5 * i
    return (
        float(np.float32(east - 2650012.0)),
        float(np.float32(-(north - 1149988.0))),
    )


def test_the_chunks_are_the_fixture_s_bytes():
    chunks = _chunks()
    entries = _block()["chunks"]
    assert [c["tile"] for c in chunks] == [e["tile"] for e in entries]
    assert [c["tile"] for c in chunks] == ["2650-1149", "2650-1150", "2651-1150"], (
        "2651-1149 holds crowns but no kept tree, so no chunk"
    )
    for chunk, entry in zip(chunks, entries, strict=True):
        assert chunk["trees"] == entry["trees"] == VECTORS["chunks"][entry["tile"]]
        assert chunk["data"] == (GENERATED / entry["file"]).read_bytes(), entry["tile"]
        assert hashlib.sha256(chunk["data"]).hexdigest() == entry["sha256"]


def test_every_named_tree_is_in_its_chunk_at_its_index():
    by_tile = {c["tile"]: _records(c["data"]) for c in _chunks()}
    assert sum(len(r) for r in by_tile.values()) == len(VECTORS["trees"])
    for tree in VECTORS["trees"]:
        record = by_tile[tree["tile"]][tree["index"]]
        expected = (*tree["local"], tree["height_m"], tree["crown_radius_m"])
        assert record == expected, tree["name"]
        # the file's x, z are the pixel centre's, through the world config (64-bit, then f32)
        assert (record[0], record[2]) == _local_xz(tree["pixel"]), tree["name"]


CROWN_CASES = [c for c in VECTORS["cases"] if c["outcome"] in ("tree", "none", "dropped")]


@pytest.mark.parametrize("case", CROWN_CASES, ids=lambda c: c["case"])
def test_each_case_has_its_outcome(case):
    """A tree at the case's pixel exactly when the case says so (tree / none / dropped)."""
    at = {(r[0], r[2]) for c in _chunks() for r in _records(c["data"])}
    has_tree = _local_xz(case["pixel"]) in at
    assert has_tree == (case["outcome"] == "tree"), case["why"]


def test_the_crown_radius_rule():
    """Every tree's radius by hand from the vectors, and each of its four regimes occurs."""
    trees = VECTORS["trees"]
    seen = set()
    for tree in trees:
        e, n = tree["lv95"][0], tree["lv95"][1]
        d = min(
            math.sqrt((o["lv95"][0] - e) ** 2 + (o["lv95"][1] - n) ** 2)
            for o in trees
            if o is not tree
        )
        quarter = tree["height_m"] / 4
        bound = min(d / 2, quarter)
        radius = float(np.float32(min(max(bound, 1.0), 6.0)))
        assert radius == tree["crown_radius_m"], tree["name"]
        seen.add("d/2" if d / 2 <= quarter else "h/4")
        seen.add("clamped to 1.0" if bound < 1.0 else "clamped to 6.0" if bound > 6.0 else "free")
    assert seen == {"d/2", "h/4", "clamped to 1.0", "clamped to 6.0", "free"}


def test_write_trees_writes_the_fixture_description(tmp_path):
    block = _block()
    world_sha256 = hashlib.sha256((FIXTURE / "world.json").read_bytes()).hexdigest()
    assert block["world_sha256"] == world_sha256
    written = write_trees(tmp_path, "fixture", _chunks(), BOX, world_sha256, block["source"])
    assert written == block
    assert (tmp_path / "trees" / "fixture.json").read_bytes() == (
        GENERATED / "trees" / "fixture.json"
    ).read_bytes()
    for entry in block["chunks"]:
        assert (tmp_path / entry["file"]).read_bytes() == (GENERATED / entry["file"]).read_bytes()
    assert sorted(p.name for p in (tmp_path / "trees").iterdir()) == [
        "2650-1149.bin",
        "2650-1150.bin",
        "2651-1150.bin",
        "fixture.json",
    ]


def test_the_description_s_key_sets():
    block = _block()
    assert set(block) == {
        "area",
        "chunks",
        "format",
        "lv95_box",
        "parameters",
        "source",
        "world_sha256",
    }
    assert block["format"] == "trees-f32x5-le"
    assert block["parameters"] == {
        "building_margin_m": 2.0,
        "crown_radius": (
            "min(d / 2, height / 4), clamped to 1.0-6.0 m; d to the nearest other tree, "
            "infinite when none"
        ),
        "max_height_m": 40.0,
        "max_slope_deg": 60.0,
        "min_height_m": 3.0,
        "smoothing": "binomial-5x5",
        "window": "3 + floor(h / 10 m) pixels",
    }
    assert all(set(e) == {"file", "sha256", "tile", "trees"} for e in block["chunks"])
    source = block["source"]
    assert set(source) == {"swissalti3d", "swissbuildings3d", "swisssurface3d", "swisstlm3d"}
    keys = {
        "swissalti3d": {"attribution", "collection", "dataset", "edition", "resolution_m", "tiles"},
        "swissbuildings3d": {"attribution", "collection", "dataset", "edition", "sheets"},
        "swisssurface3d": {
            "attribution",
            "collection",
            "dataset",
            "editions",
            "resolution_m",
            "tiles",
        },
        "swisstlm3d": {"attribution", "collection", "dataset", "edition", "file", "sha256"},
    }
    for dataset, wanted in keys.items():
        assert set(source[dataset]) == wanted, dataset
        assert source[dataset]["dataset"] == dataset
    assert all(set(t) == {"edition", "sha256", "tile"} for t in source["swisssurface3d"]["tiles"])
