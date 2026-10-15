"""Pinning tests for brief M3-04: the photo built from 2 x 2 real-size SWISSIMAGE tiles.

Pinned decisions (m3-design §2, the photo): `build_photo` reads the tiles provenance.json
lists, each checked against the lock, and places every tile where its id says: a GeoTIFF
in EPSG:2056 of 10000 x 10000 pixels in 3 uint8 bands with the transform exactly
(0.1, 0, E0, 0, -0.1, N0 + 1000), else refused naming the tile. Texel (r, c) is the
k x k block of source pixels counted from the area's north-west corner (not from a tile's
corner), its value per channel round-half-to-even of the exact sum / k². Four synthetic
tiles (2623-1095, 2623-1096, 2624-1095, 2624-1096) are written from a formula as sparse
GeoTIFFs (only the blocks around the area hold pixels; the rest is never written, reads
as 0, and costs nothing on disk), and the area E 2'623'990.5-2'624'010.5 /
N 1'095'990.5-1'096'006.5 cuts all four, its north-west corner an odd number of
decimetres from the tiles' edges, so texels straddle both tile boundaries at 0.2 and 1 m.
Built at 0.2 m and at 1 m, the raw grid and the JPEG have the SHA-256s design computed
two independent ways (this test's formula evaluated in pure Python with Fraction and
round(), and a throwaway build through the GeoTIFFs; identical bytes). A swapped, flipped
or shifted tile, a grid counted from a tile's corner, a wrong cut or another rounding
changes these bytes (the formula depends on the global position and on the tile).

The expected values are compared in a fixed order before anything is written: the pixels
first ("this machine or this code computes other pixels than design's"), then the JPEG
("the pixels are design's; this machine's JPEG encoder writes other bytes", naming the
Pillow and libjpeg-turbo versions), each naming both SHA-256s; nothing is written on a
refusal. A build writes exactly `photo/<area>.jpg`, `photo/<area>.jpg.import` (Godot's
keep file, exactly `[remap]`, an empty line and `importer="keep"`) and `photo/<area>.json`.

Costs (measured 2026-10-14): the four sparse tiles are written in about 0.1 s and hold
77 to 94 KB each; a full read of one decodes 300 MB in about 1.1 s, a windowed read of the
area's part about 0.02 s.

Does NOT prove: that swisstopo's JPEG-compressed tiles decode to the same pixels on the
owner's machine (the step's own comparison with config/photo.json says so on the real
village); that anything renders.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import PIL
import PIL.features
import pytest
import rasterio
from computed_for import computed_for
from rasterio.transform import Affine
from rasterio.windows import Window

from mattini.photo import PhotoError, build_photo
from mattini.world import load_world

REPO = Path(__file__).resolve().parents[2]
WEST_KM, NORTH_KM = 2623, 1097  # the 2 x 2 km block's north-west corner, in km
TILES = ["2623-1095", "2623-1096", "2624-1095", "2624-1096"]  # the pipeline's order
BOX = {"e_min": 2623990.5, "e_max": 2624010.5, "n_min": 1095990.5, "n_max": 1096006.5}
DATASETS = {
    "swissimage": {
        "attribution": "© swisstopo",
        "collection": "ch.swisstopo.swissimage-dop10",
        "edition": "2023",
        "resolution_m": 0.1,
    }
}
MARGIN = 64  # source pixels written around the area's part of each tile
# Design data (M3 planning, 2026-10-14): (pixels_sha256, jpeg sha256, columns, rows)
EXPECTED = {
    0.2: (
        "773eb89d0d148a4cb6f0372962ac89a5d68405cdfcef509352692cd0518c089d",
        "8d3a7256fa23e3febf70dc10d2022ffd79fb60379218868927e6383fab39de19",
        100,
        80,
    ),
    1.0: (
        "3ad58ce1190fdb66a5af3b6eff347151a8f2fdabd19fa6d241e337ddb3b08621",
        "ea9b5c84350709d1241a278b75abf19694b1b60a8db60fea6478abdc0767345e",
        20,
        16,
    ),
}
KEEP_IMPORT = b'[remap]\n\nimporter="keep"\n'  # Godot keeps the JPEG as it is
MACHINE = "this machine or this code computes other pixels than design's"
ENCODER = "the pixels are design's; this machine's JPEG encoder writes other bytes"


def tile_pixels(tile: str, top: int, left: int, height: int, width: int) -> np.ndarray:
    """The (3, height, width) uint8 pixels of `tile` from its row `top`, column `left`.

    gi, gj count 0.1 m pixels from the block's north-west corner (E 2'623'000,
    N 1'097'000); t is 50 per km east and 90 per km south of that corner's tile.
    """
    e_km, n_km = (int(v) for v in tile.split("-"))
    t = 50 * (e_km - WEST_KM) + 90 * (NORTH_KM - 1 - n_km)
    gi = np.arange(top, top + height, dtype=np.int64)[:, None] + (NORTH_KM - 1 - n_km) * 10000
    gj = np.arange(left, left + width, dtype=np.int64)[None, :] + (e_km - WEST_KM) * 10000
    red = (3 * gi + 5 * gj + (gi * gj) % 7 + t) % 256
    green = (7 * gi + 2 * gj + (gi + 2 * gj) % 5 + 2 * t) % 256
    blue = (gi * gi + 3 * gj * gj + 3 * t) % 256
    return np.stack([red, green, blue]).astype(np.uint8)


def _window(tile: str) -> tuple[int, int, int, int]:
    """(top, left, height, width) in tile pixels: the area's part of the tile and MARGIN."""
    e_km, n_km = (int(v) for v in tile.split("-"))
    west, north = e_km * 1000.0, (n_km + 1) * 1000.0
    top = max(0, round((north - BOX["n_max"]) * 10) - MARGIN)
    bottom = min(10000, round((north - BOX["n_min"]) * 10) + MARGIN)
    left = max(0, round((BOX["e_min"] - west) * 10) - MARGIN)
    right = min(10000, round((BOX["e_max"] - west) * 10) + MARGIN)
    return top, left, bottom - top, right - left


def _name(tile: str) -> str:
    return f"swissimage-dop10_2023_{tile}_0.1_2056.tif"


def write_tile(path: Path, tile: str, **change) -> None:
    """A sparse 10000 x 10000 RGB GeoTIFF of `tile` holding pixels only around the area.

    `change` overrides profile entries (a refusal case: another size, CRS, transform...).
    """
    e_km, n_km = (int(v) for v in tile.split("-"))
    profile = {
        "driver": "GTiff",
        "dtype": "uint8",
        "width": 10000,
        "height": 10000,
        "count": 3,
        "crs": "EPSG:2056",
        "transform": Affine(0.1, 0.0, e_km * 1000.0, 0.0, -0.1, (n_km + 1) * 1000.0),
        "tiled": True,
        "blockxsize": 256,
        "blockysize": 256,
        "compress": "deflate",
        "sparse_ok": True,
    }
    profile.update(change)
    top, left, height, width = _window(tile)
    data = tile_pixels(tile, top, left, height, width)
    with rasterio.open(path, "w", **profile) as ds:
        extra = np.zeros((max(0, ds.count - 3), height, width), dtype=np.uint8)
        ds.write(np.concatenate([data, extra])[: ds.count], window=Window(left, top, width, height))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _inputs(root: Path, changed: dict | None = None) -> dict:
    """World, provenance and lock for the four tiles under `root`; `changed` maps a tile to
    profile overrides for that tile."""
    world = json.loads((REPO / "config" / "world.json").read_text(encoding="utf-8"))
    world["areas"] = {"village": dict(BOX)}
    world_path = root / "world.json"
    world_path.write_text(json.dumps(world, indent=2) + "\n", encoding="utf-8")
    raw_dir = root / "raw" / "swissimage" / "2023"
    raw_dir.mkdir(parents=True)
    entries, locked = [], {}
    for tile in TILES:
        path = raw_dir / _name(tile)
        write_tile(path, tile, **(changed or {}).get(tile, {}))
        sha256 = _sha(path)
        entries.append(
            {
                "file": path.name,
                "item": f"swissimage-dop10_2023_{tile}",
                "sha256": sha256,
                "size_bytes": path.stat().st_size,
                "tile": tile,
                "url": (
                    "https://data.geo.admin.ch/ch.swisstopo.swissimage-dop10/"
                    f"swissimage-dop10_2023_{tile}/{path.name}"
                ),
            }
        )
        locked[tile] = {"file": path.name, "sha256": sha256}
    provenance = {
        "attribution": "© swisstopo",
        "collection": "ch.swisstopo.swissimage-dop10",
        "dataset": "swissimage",
        "edition": "2023",
        "resolution_m": 0.1,
        "schema": 1,
        "tiles": entries,
    }
    (raw_dir / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    lock = {
        "schema": 1,
        "datasets": {
            "swissimage": {
                "collection": "ch.swisstopo.swissimage-dop10",
                "edition": "2023",
                "resolution_m": 0.1,
                "tiles": locked,
            }
        },
    }
    return {
        "world": load_world(world_path),
        "world_sha256": _sha(world_path),
        "lock": lock,
        "raw_root": root / "raw",
        "tile_sha256": {tile: locked[tile]["sha256"] for tile in TILES},
        "computed_for": computed_for(world_path, lock, "swissimage"),
    }


@pytest.fixture(scope="module")
def four_tiles(tmp_path_factory):
    return _inputs(tmp_path_factory.mktemp("four_tiles"))


def _config(cell: float, pixels: str, jpeg: str, computed: dict) -> dict:
    key = format(cell, "g")
    return {
        "schema": 1,
        "areas": {
            "village": {
                "cell_m": cell,
                "computed_for": computed,
                "expected_pixels_sha256": {key: pixels},
                "expected_sha256": {key: jpeg},
            }
        },
    }


def _expected_description(case: dict, cell: float) -> bytes:
    pixels, jpeg, columns, rows = EXPECTED[cell]
    block = {
        "area": "village",
        "cell_m": cell,
        "columns": columns,
        "file": "photo/village.jpg",
        "format": "jpeg",
        "jpeg": {"quality": 92, "subsampling": "4:2:0"},
        "lv95_box": {key: BOX[key] for key in ("e_max", "e_min", "n_max", "n_min")},
        "pixels_sha256": pixels,
        "rows": rows,
        "sha256": jpeg,
        "source": {
            "attribution": "© swisstopo",
            "collection": "ch.swisstopo.swissimage-dop10",
            "dataset": "swissimage",
            "edition": "2023",
            "resolution_m": 0.1,
            "tiles": [{"sha256": case["tile_sha256"][tile], "tile": tile} for tile in TILES],
        },
        "world_sha256": case["world_sha256"],
    }
    return (json.dumps(block, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def _build(case: dict, config: dict, out: Path) -> dict:
    return build_photo(case["world"], DATASETS, case["lock"], config, case["raw_root"], out)


@pytest.mark.parametrize("cell", sorted(EXPECTED))
def test_four_tiles_build_to_design_s_bytes(four_tiles, cell, tmp_path):
    pixels, jpeg, columns, rows = EXPECTED[cell]
    out = tmp_path / "generated"
    block = _build(four_tiles, _config(cell, pixels, jpeg, four_tiles["computed_for"]), out)
    data = (out / "photo" / "village.jpg").read_bytes()
    assert hashlib.sha256(data).hexdigest() == jpeg
    assert (block["columns"], block["rows"], block["pixels_sha256"]) == (columns, rows, pixels)
    assert (out / "photo" / "village.json").read_bytes() == _expected_description(four_tiles, cell)
    assert (out / "photo" / "village.jpg.import").read_bytes() == KEEP_IMPORT
    assert sorted(p.name for p in (out / "photo").iterdir()) == [
        "village.jpg",
        "village.jpg.import",
        "village.json",
    ]


def _refused(case: dict, config: dict, out: Path) -> str:
    with pytest.raises(PhotoError) as refusal:
        _build(case, config, out)
    for name in ("village.jpg", "village.jpg.import", "village.json"):
        assert not (out / "photo" / name).exists(), name
    return str(refusal.value)


def test_other_pixels_are_refused_first_naming_both_values(four_tiles, tmp_path):
    pixels = EXPECTED[0.2][0]
    wrong_pixels, wrong_jpeg = "0" * 64, "1" * 64
    config = _config(0.2, wrong_pixels, wrong_jpeg, four_tiles["computed_for"])
    message = _refused(four_tiles, config, tmp_path / "generated")
    assert MACHINE in message
    assert pixels in message and wrong_pixels in message
    assert ENCODER not in message and wrong_jpeg not in message


def test_design_s_pixels_with_another_jpeg_name_the_encoder(four_tiles, tmp_path):
    pixels, jpeg, _, _ = EXPECTED[0.2]
    wrong_jpeg = "1" * 64
    config = _config(0.2, pixels, wrong_jpeg, four_tiles["computed_for"])
    message = _refused(four_tiles, config, tmp_path / "generated")
    assert ENCODER in message and MACHINE not in message
    assert jpeg in message and wrong_jpeg in message
    assert f"Pillow {PIL.__version__}" in message
    assert f"libjpeg-turbo {PIL.features.version('libjpeg_turbo')}" in message


@pytest.mark.parametrize(
    "change",
    [
        {"width": 9999},
        {"count": 4},
        {"crs": "EPSG:21781"},
        {"transform": Affine(0.1, 0.0, 2624000.1, 0.0, -0.1, 1096000.0)},
        {"transform": Affine(0.1, 0.0, 2624000.0, 0.0, -0.2, 1096000.0)},
    ],
    ids=["9999-wide", "4-bands", "lv03-crs", "shifted-0.1-m", "0.2-m-rows"],
)
def test_a_tile_that_is_not_where_its_id_says_is_refused_naming_it(tmp_path, change):
    case = _inputs(tmp_path, changed={"2624-1095": change})
    pixels, jpeg, _, _ = EXPECTED[0.2]
    message = _refused(case, _config(0.2, pixels, jpeg, case["computed_for"]), tmp_path / "gen")
    assert "2624-1095" in message
    for tile in ("2623-1095", "2623-1096", "2624-1096"):
        assert tile not in message
