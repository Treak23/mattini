"""Pinning tests for briefs M1-03 and M2-01: the pipeline reproduces the shared terrain fixture.

Pinned decisions (docs/SPEC.md §8, the terrain grid): a vertex every spacing_m from the
area's north-west corner, the edges included; each vertex's height is the area-weighted
mean of the 0.5 m source pixels under the spacing-wide square centred on it, clipped to
the area, minus height_offset_m, computed in 64-bit and rounded once to 32-bit; the file is
little-endian float32, rows north to south (+z), columns west to east (+x), no header; the
description is written next to it and copied into the manifest's `terrain` block. The
expected bytes under tests/shared/terrain_fixture/generated/ were computed by design two
independent ways (see tests/shared/terrain_vectors.json); the game's tests load the same
bytes (brief M1-04), so this is the seam between the two halves (lesson 3). Since M2-01
the fixture's source is pinned in its own `datasets.lock.json` as the tile it lies in
(2601-1199), so the manifest's source check (M1 R1 T-04) applies to it too.
"""

import hashlib
import json
from pathlib import Path

import numpy as np

from mattini.manifest import write_manifest
from mattini.terrain import resample, write_terrain

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "shared" / "terrain_fixture"
GENERATED = FIXTURE / "generated"
VECTORS = json.loads((REPO / "tests" / "shared" / "terrain_vectors.json").read_text("utf-8"))
BOX = (2601015.0, 2601035.0, 1199978.0, 1199989.5)  # e_min, e_max, n_min, n_max


def _source() -> np.ndarray:
    src = VECTORS["source"]
    return np.fromfile(FIXTURE / "source.f32", dtype="<f4").reshape(src["rows"], src["columns"])


def _expected_heights() -> np.ndarray:
    grid = VECTORS["grid"]
    raw = (GENERATED / "terrain" / "fixture.f32").read_bytes()
    return np.frombuffer(raw, dtype="<f4").reshape(grid["rows"], grid["columns"])


def _block() -> dict:
    return json.loads((GENERATED / "terrain" / "fixture.json").read_text(encoding="utf-8"))


def test_resample_gives_the_fixture_bit_for_bit():
    heights = resample(_source(), BOX, 0.5, 1000.0)
    assert heights.dtype == np.float32
    assert heights.shape == (VECTORS["grid"]["rows"], VECTORS["grid"]["columns"])
    assert heights.tobytes() == _expected_heights().astype("<f4").tobytes()


def test_the_named_vertices_have_the_designed_heights():
    heights = resample(_source(), BOX, 0.5, 1000.0)
    for v in VECTORS["vertices"]:
        assert float(heights[v["row"], v["column"]]) == v["y"], v["name"]


def test_write_terrain_writes_the_fixture_files(tmp_path):
    block = _block()
    written = write_terrain(
        tmp_path,
        "fixture",
        resample(_source(), BOX, 0.5, 1000.0),
        BOX,
        0.5,
        block["world_sha256"],
        block["source"],
    )
    assert written == block
    for rel in ("terrain/fixture.f32", "terrain/fixture.json"):
        assert (tmp_path / rel).read_bytes() == (GENERATED / rel).read_bytes(), rel


def test_the_manifest_carries_the_fixture_block_verbatim(tmp_path):
    block = _block()
    write_terrain(
        tmp_path,
        "fixture",
        resample(_source(), BOX, 0.5, 1000.0),
        BOX,
        0.5,
        block["world_sha256"],
        block["source"],
    )
    path = write_manifest(
        tmp_path,
        FIXTURE / "world.json",
        terrain_config_path=FIXTURE / "terrain.json",
        datasets_path=FIXTURE / "datasets.json",
        lock_path=FIXTURE / "datasets.lock.json",
    )
    assert path.read_bytes() == (GENERATED / "manifest.json").read_bytes()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == (
        hashlib.sha256((GENERATED / "manifest.json").read_bytes()).hexdigest()
    )
