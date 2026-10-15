"""The photo is built in strips of texel rows, and the checked tile reader (brief M3-04).

`build_photo` works in strips of `STRIP_M` metres of whole texel rows, each reading only its
windows of the verified tiles (module docstring of `mattini.photo`): the bytes must be those
of one mosaic of the whole area whatever the strip height, including strips that end inside
a tile, across a tile boundary, at one texel row and past the area's end. The area of the
four synthetic tiles is cut by both tile boundaries with its north-west corner an odd number
of decimetres from the tiles' edges, so a strip counted from a tile's corner, a window off
by one row or column, or a strip that does not start on a texel boundary changes the bytes.

`read_tiles` hands the roofs step the tiles as rasters, one at a time: each in the order the
area lists them, with its west and north edges in decimetres, 10000 × 10000 pixels of RGB,
the pixels the GeoTIFF holds; a tile whose bytes are not the SHA-256 vouched for is refused
naming it and the download command.

Does NOT prove: the memory of the real run (measured in brief M3-04's Findings, which is
the gate); that the reader decodes swisstopo's JPEG-compressed tiles (the real run does).
"""

from pathlib import Path

import numpy as np
import pytest
from test_photo_build_tiles import (
    DATASETS,
    EXPECTED,
    TILES,
    _build,
    _config,
    _inputs,
    _window,
    tile_pixels,
)

from mattini import photo
from mattini.photo import PhotoError, PhotoTile, photo_tiles, read_tiles


@pytest.fixture(scope="module")
def case(tmp_path_factory):
    return _inputs(tmp_path_factory.mktemp("strip_tiles"))


@pytest.mark.parametrize("cell", sorted(EXPECTED))
@pytest.mark.parametrize("strip_m", [0.1, 1.0, 2.0, 7.0, 10.0, 1000.0], ids=lambda m: f"{m}m")
def test_every_strip_height_gives_design_s_bytes(case, cell, strip_m, tmp_path, monkeypatch):
    monkeypatch.setattr(photo, "STRIP_M", strip_m)
    pixels, jpeg, columns, rows = EXPECTED[cell]
    block = _build(case, _config(cell, pixels, jpeg, case["computed_for"]), tmp_path / "out")
    assert (block["columns"], block["rows"]) == (columns, rows)
    assert block["pixels_sha256"] == pixels and block["sha256"] == jpeg


def test_the_tiles_come_as_rasters_in_the_area_s_order(case):
    listed = photo_tiles(case["raw_root"], DATASETS["swissimage"], case["lock"], TILES)
    assert [t.tile for t in listed] == TILES
    seen = []
    for tile, (west_dm, north_dm, pixels) in zip(TILES, read_tiles(listed), strict=True):
        e_km, n_km = (int(v) for v in tile.split("-"))
        assert (west_dm, north_dm) == (e_km * 10000, (n_km + 1) * 10000), tile
        assert pixels.shape == (10000, 10000, 3) and pixels.dtype == np.uint8, tile
        top, left, height, width = _window(tile)
        written = tile_pixels(tile, top, left, height, width).transpose(1, 2, 0)
        assert np.array_equal(pixels[top : top + height, left : left + width], written), tile
        seen.append(tile)
    assert seen == TILES


def test_the_reader_says_which_tile_it_reads(case):
    listed = photo_tiles(case["raw_root"], DATASETS["swissimage"], case["lock"], TILES)
    said = []
    tiles = read_tiles(listed, progress=said.append)
    next(tiles)  # one tile is read per step: the others are not touched yet
    tiles.close()
    assert len(said) == 1 and str(listed[0].path) in said[0]


def test_a_tile_that_is_not_the_bytes_vouched_for_is_refused_naming_it(case):
    listed = photo_tiles(case["raw_root"], DATASETS["swissimage"], case["lock"], TILES)
    wrong = PhotoTile(listed[1].tile, listed[1].path, "4" * 64)
    with pytest.raises(PhotoError) as refusal:
        for _ in read_tiles([listed[0], wrong]):
            pass
    message = str(refusal.value)
    assert wrong.tile in message and "python -m mattini download photo" in message
    assert wrong.sha256 in message and listed[1].sha256 in message  # the pinned and the actual


def test_photo_tiles_reads_nothing_but_provenance(case, monkeypatch):
    real = Path.read_bytes

    def read_bytes(self):
        assert self.suffix != ".tif", f"photo_tiles read {self}"
        return real(self)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    listed = photo_tiles(case["raw_root"], DATASETS["swissimage"], case["lock"], TILES)
    assert [t.tile for t in listed] == TILES
