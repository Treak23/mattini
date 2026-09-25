"""Pinning tests for brief M2-01 (M1 R1 T-01 a, T-03): a terrain built from 2 x 2 tiles.

Pinned decisions (docs/SPEC.md §8, the terrain grid; docs/history/ARCS.md §M1, the
carry-over table): the terrain step places every tile where its id says and cuts the
outer tiles at the area's edges. Four synthetic 0.5 m tiles (2623-1095, 2624-1095,
2623-1096, 2624-1096) are written from a formula, and an area E 2'623'250-2'624'750 /
N 1'095'500-1'096'500 cuts all four. Built at 2 m and at 0.5 m, the heights file has the
exact SHA-256 design computed two independent ways at M2 planning: the pipeline's own
build and an exact area-overlap implementation, identical bits. A swapped tile, a flipped
or shifted tile, or a wrong cut changes these bytes (the formula makes every pixel's
height depend on its global position and its tile). The description `terrain/village.json`
has exactly the bytes rendered here from the inputs, so no date, host name or path can
enter it (T-03, lesson 33).

Does NOT prove: that the owner's machine computes the same bytes (the step's own check
against config/terrain.json says so on the real village); that anything renders.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from mattini.datasets import load_datasets
from mattini.terrain import TerrainError, build_terrain
from mattini.world import load_world

REPO = Path(__file__).resolve().parents[2]
WEST_KM, NORTH_KM = 2623, 1097  # the 2 x 2 km block's north-west corner, in km
TILES = ["2623-1095", "2623-1096", "2624-1095", "2624-1096"]  # the pipeline's order
BOX = {"e_min": 2623250.0, "e_max": 2624750.0, "n_min": 1095500.0, "n_max": 1096500.0}
# Design data (M2 planning, 2026-09-25): the pipeline's build and an independent exact
# area-overlap implementation give these bits.
EXPECTED = {
    2.0: ("42756c1c286a23856045b40b458d38f312104f84a1fbba0ae17de497ff325617", 751, 501),
    0.5: ("c3bbb0f0af19e06217c2fe3020fb35b2ad722ca8027311efbd4b347f9720deaa", 3001, 2001),
}


def tile_heights(tile_e_km: int, tile_n_km: int) -> np.ndarray:
    """The 2000 x 2000 float32 heights of a tile, rows north to south.

    Every term is an integer or a multiple of 2**-13 below 2**11, so the float64 sum is
    exact in any order and the cast to float32 does not round.
    """
    i0 = (NORTH_KM - 1 - tile_n_km) * 2000  # global row of the tile's northern pixel row
    j0 = (tile_e_km - WEST_KM) * 2000  # global column of the tile's western pixel column
    gi = np.arange(i0, i0 + 2000, dtype=np.int64)[:, None]
    gj = np.arange(j0, j0 + 2000, dtype=np.int64)[None, :]
    tile_constant = 10.0 * (tile_e_km - WEST_KM) + 20.0 * (NORTH_KM - 1 - tile_n_km)
    heights = (1550.0 + tile_constant) + gj / 16.0 - gi / 32.0 + ((gi * gj) % 8191) / 8192.0
    return heights.astype(np.float32)


def _name(tile: str) -> str:
    return f"swissalti3d_2024_{tile}_0.5_2056_5728.tif"


def _write_tile(path: Path, tile: str) -> None:
    e_km, n_km = (int(v) for v in tile.split("-"))
    data = tile_heights(e_km, n_km)
    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "width": 2000,
        "height": 2000,
        "count": 1,
        "crs": "EPSG:2056",
        "transform": from_origin(e_km * 1000.0, (n_km + 1) * 1000.0, 0.5, 0.5),
        "nodata": -9999.0,
    }
    with rasterio.open(path, "w", **profile) as ds:
        ds.write(data, 1)


@pytest.fixture(scope="module")
def four_tiles(tmp_path_factory):
    """The world, provenance and lock for the 2 x 2 block, written once for the module."""
    root = tmp_path_factory.mktemp("four_tiles")
    world = json.loads((REPO / "config" / "world.json").read_text(encoding="utf-8"))
    world["areas"] = {"village": dict(BOX)}
    world_path = root / "world.json"
    world_path.write_text(json.dumps(world, indent=2) + "\n", encoding="utf-8")
    raw_dir = root / "raw" / "swissalti3d" / "2024"
    raw_dir.mkdir(parents=True)
    entries, locked = [], {}
    for tile in TILES:
        path = raw_dir / _name(tile)
        _write_tile(path, tile)
        sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        entries.append(
            {
                "file": path.name,
                "item": f"swissalti3d_2024_{tile}",
                "sha256": sha256,
                "size_bytes": path.stat().st_size,
                "tile": tile,
                "url": f"https://data.geo.admin.ch/ch.swisstopo.swissalti3d/{path.name}",
            }
        )
        locked[tile] = {"file": path.name, "sha256": sha256}
    provenance = {
        "attribution": "© swisstopo",
        "collection": "ch.swisstopo.swissalti3d",
        "dataset": "swissalti3d",
        "edition": "2024",
        "resolution_m": 0.5,
        "schema": 1,
        "tiles": entries,
    }
    (raw_dir / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    lock = {
        "schema": 1,
        "datasets": {
            "swissalti3d": {
                "collection": "ch.swisstopo.swissalti3d",
                "edition": "2024",
                "resolution_m": 0.5,
                "tiles": locked,
            }
        },
    }
    return {
        "root": root,
        "world": load_world(world_path),
        "world_sha256": hashlib.sha256(world_path.read_bytes()).hexdigest(),
        "lock": lock,
        "raw_root": root / "raw",
        "tile_sha256": {tile: locked[tile]["sha256"] for tile in TILES},
    }


def _config(spacing: float, sha256: str) -> dict:
    return {
        "schema": 1,
        "areas": {
            "village": {"expected_sha256": {format(spacing, "g"): sha256}, "spacing_m": spacing}
        },
    }


def _expected_description(case: dict, spacing: float) -> bytes:
    sha256, columns, rows = EXPECTED[spacing]
    block = {
        "area": "village",
        "columns": columns,
        "file": "terrain/village.f32",
        "format": "float32-le",
        "lv95_box": {
            "e_max": BOX["e_max"],
            "e_min": BOX["e_min"],
            "n_max": BOX["n_max"],
            "n_min": BOX["n_min"],
        },
        "rows": rows,
        "sha256": sha256,
        "source": {
            "attribution": "© swisstopo",
            "collection": "ch.swisstopo.swissalti3d",
            "dataset": "swissalti3d",
            "edition": "2024",
            "resolution_m": 0.5,
            "tiles": [{"sha256": case["tile_sha256"][tile], "tile": tile} for tile in TILES],
        },
        "spacing_m": spacing,
        "world_sha256": case["world_sha256"],
    }
    text = json.dumps(block, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    return text.encode("utf-8")


@pytest.mark.parametrize("spacing", sorted(EXPECTED))
def test_four_tiles_build_to_design_s_bytes(four_tiles, spacing, tmp_path):
    sha256, columns, rows = EXPECTED[spacing]
    out = tmp_path / "generated"
    block = build_terrain(
        four_tiles["world"],
        load_datasets(),
        four_tiles["lock"],
        _config(spacing, sha256),
        four_tiles["raw_root"],
        out,
    )
    heights = (out / "terrain" / "village.f32").read_bytes()
    assert len(heights) == columns * rows * 4
    assert hashlib.sha256(heights).hexdigest() == sha256
    assert (block["columns"], block["rows"]) == (columns, rows)
    assert (out / "terrain" / "village.json").read_bytes() == _expected_description(
        four_tiles, spacing
    )


def test_the_cut_corners_hold_the_designed_heights(four_tiles, tmp_path):
    """Spot checks by hand at 2 m: the 4 x 4 pixels around a vertex, clipped at the edges."""
    sha256 = EXPECTED[2.0][0]
    out = tmp_path / "generated"
    build_terrain(
        four_tiles["world"],
        load_datasets(),
        four_tiles["lock"],
        _config(2.0, sha256),
        four_tiles["raw_root"],
        out,
    )
    heights = np.fromfile(out / "terrain" / "village.f32", dtype="<f4").reshape(501, 751)
    block = np.concatenate(
        [
            np.concatenate([tile_heights(2623, 1096), tile_heights(2624, 1096)], axis=1),
            np.concatenate([tile_heights(2623, 1095), tile_heights(2624, 1095)], axis=1),
        ],
        axis=0,
    ).astype(np.float64)
    # the area's north-west corner is global pixel row 1000, column 500
    r0, c0 = 1000, 500
    # the north-west vertex: its window's inner 2 x 2 pixels only
    assert heights[0, 0] == np.float32(block[r0 : r0 + 2, c0 : c0 + 2].mean())
    # an interior vertex on the tiles' shared corner (E 2'624'000, N 1'096'000)
    row, col = 250, 375
    i, j = r0 + 4 * row, c0 + 4 * col
    assert heights[row, col] == np.float32(block[i - 2 : i + 2, j - 2 : j + 2].mean())
    # the south-east vertex
    i, j = r0 + 4 * 500, c0 + 4 * 750
    assert heights[500, 750] == np.float32(block[i - 2 : i, j - 2 : j].mean())


def test_a_wrong_expected_value_is_refused_before_anything_is_written(four_tiles, tmp_path):
    out = tmp_path / "generated"
    wrong = "0" * 64
    with pytest.raises(TerrainError) as refusal:
        build_terrain(
            four_tiles["world"],
            load_datasets(),
            four_tiles["lock"],
            _config(2.0, wrong),
            four_tiles["raw_root"],
            out,
        )
    message = str(refusal.value)
    assert EXPECTED[2.0][0] in message and wrong in message
    assert not (out / "terrain" / "village.f32").exists()
    assert not (out / "terrain" / "village.json").exists()
