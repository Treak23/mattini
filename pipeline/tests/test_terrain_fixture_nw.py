"""Pinning tests for brief M2-01: the pipeline reproduces the second shared terrain fixture.

Pinned decisions (docs/SPEC.md §8, the terrain grid and its shared fixtures): the second
fixture (tests/shared/terrain_fixture_nw/, its vectors in
tests/shared/terrain_vectors_nw.json) is a world whose grid lies north-west of its origin,
at 2 m, with a height offset of -12.25 m; design computed its expected output two
independent ways. The pipeline must reproduce `generated/` byte for byte, and the game's
loader tests read the same bytes back from Terrain3D (brief M2-02): the seam, as for the
first fixture (lesson 3). The fixture's source is pinned in its own `datasets.lock.json`
as the tile it lies in, so the manifest's source check (T-04) applies to it too.

Does NOT prove: that the game places it right (M2-02's test does); that it renders.
"""

import hashlib
import json
from pathlib import Path

import numpy as np

from mattini.manifest import write_manifest
from mattini.terrain import load_terrain_config, resample, write_terrain

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "shared" / "terrain_fixture_nw"
GENERATED = FIXTURE / "generated"
VECTORS = json.loads((REPO / "tests" / "shared" / "terrain_vectors_nw.json").read_text("utf-8"))
BOX = (2698964.0, 2698988.0, 1101008.0, 1101034.0)  # e_min, e_max, n_min, n_max
OFFSET = -12.25


def _source() -> np.ndarray:
    src = VECTORS["source"]
    return np.fromfile(FIXTURE / "source.f32", dtype="<f4").reshape(src["rows"], src["columns"])


def _block() -> dict:
    return json.loads((GENERATED / "terrain" / "fixture_nw.json").read_text(encoding="utf-8"))


def test_the_fixture_s_config_names_its_heights():
    config = load_terrain_config(FIXTURE / "terrain.json")
    area = config["areas"]["fixture_nw"]
    assert area["spacing_m"] == 2.0
    raw = (GENERATED / "terrain" / "fixture_nw.f32").read_bytes()
    assert area["expected_sha256"] == {"2": hashlib.sha256(raw).hexdigest()}


def test_resample_gives_the_fixture_bit_for_bit():
    heights = resample(_source(), BOX, 2.0, OFFSET)
    grid = VECTORS["grid"]
    assert heights.shape == (grid["rows"], grid["columns"])
    assert (
        heights.astype("<f4").tobytes() == (GENERATED / "terrain" / "fixture_nw.f32").read_bytes()
    )


def test_the_named_vertices_have_the_designed_heights():
    heights = resample(_source(), BOX, 2.0, OFFSET)
    for v in VECTORS["vertices"]:
        assert float(heights[v["row"], v["column"]]) == v["y"], v["name"]


def test_the_source_is_pinned_as_its_tile():
    lock = json.loads((FIXTURE / "datasets.lock.json").read_text(encoding="utf-8"))
    tiles = lock["datasets"]["swissalti3d"]["tiles"]
    assert list(tiles) == ["2698-1101"]
    assert (
        tiles["2698-1101"]["sha256"]
        == hashlib.sha256((FIXTURE / "source.f32").read_bytes()).hexdigest()
    )
    assert _block()["source"]["tiles"] == [
        {"sha256": tiles["2698-1101"]["sha256"], "tile": "2698-1101"}
    ]


def test_write_terrain_and_manifest_write_the_fixture_files(tmp_path):
    block = _block()
    written = write_terrain(
        tmp_path,
        "fixture_nw",
        resample(_source(), BOX, 2.0, OFFSET),
        BOX,
        2.0,
        block["world_sha256"],
        block["source"],
    )
    assert written == block
    for rel in ("terrain/fixture_nw.f32", "terrain/fixture_nw.json"):
        assert (tmp_path / rel).read_bytes() == (GENERATED / rel).read_bytes(), rel
    path = write_manifest(
        tmp_path,
        FIXTURE / "world.json",
        terrain_config_path=FIXTURE / "terrain.json",
        datasets_path=FIXTURE / "datasets.json",
        lock_path=FIXTURE / "datasets.lock.json",
    )
    assert path.read_bytes() == (GENERATED / "manifest.json").read_bytes()
