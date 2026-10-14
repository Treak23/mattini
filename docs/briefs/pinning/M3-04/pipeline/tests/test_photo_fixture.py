"""Pinning tests for brief M3-04: the pipeline reproduces the shared photo fixture.

Pinned decisions (m3-design §2, the photo): the grid over the area at cell_m, one of
0.2, 0.5 and 1 m (k = 2, 5 or 10 source pixels of 0.1 m): texel (r, c), r from north, c
from west, is the k x k block of source pixels whose indices from the area's north-west
corner are rows r·k ... r·k + k - 1 and columns c·k ... c·k + k - 1; per channel its value
is round-half-to-even of the exact integer sum / k². The raw grid: rows north to south,
columns west to east, R, G, B interleaved, uint8; `pixels_sha256` is its SHA-256. The JPEG
is Pillow's `Image.frombuffer("RGB", (columns, rows), raw, "raw", "RGB", 0, 1).save(f,
"JPEG", quality=92, subsampling=2, optimize=False, progressive=False)`. The description
`photo/<area>.json` has exactly the keys area, cell_m, columns, file, format, jpeg,
lv95_box, pixels_sha256, rows, sha256, source and world_sha256, written with sorted keys,
2-space indent, UTF-8, LF and a final newline, after the JPEG; beside the JPEG the step
writes `photo/<area>.jpg.import` holding exactly `[remap]`, an empty line and
`importer="keep"` (25 bytes, LF), so Godot keeps the file as it is instead of importing
it as a texture (measured: without it the village's first import takes 43.6 s, peaks at
5.2 GiB and an export ships a 170 MB texture instead of the JPEG). All three go through a
`.part` rename; the description does not list the `.import` file (it is Godot's, not
data). `built_photo_block` reads the description back for the manifest.

The fixture (tests/shared/photo_fixture/, its design in tests/shared/photo_vectors.json)
is a synthetic world whose 16 m x 8 m area is 80 x 40 texels at 0.2 m: 8 x 8-texel
blocks of distinct greys and one coloured 16 x 16-texel corner, so that the game can check
placement through the lossy JPEG. Each texel's 2 x 2 source pixels sum, per channel, to
4L + d with d in -2..2 and L even: round-half-up gives L + 1 where d = 2, floor gives
L - 1 where d < 0, a grid counted one pixel off mixes texels, and BGR order changes the
coloured corner; at 1 m a quarter of the sums are ties (S mod 100 = 50). Design computed
the expected bytes two independent ways at M3 planning (numpy block sums with integer
rounding, and a pure-Python loop with Fraction and round(); identical at every cell; the
JPEGs with Pillow 12.3.0, libjpeg-turbo 3.1.4.1). The pipeline must reproduce `generated/
photo/` byte for byte; the game reads the same JPEG (brief M3-09): the seam (lesson 3).

Does NOT prove: that the tiles are read and placed (test_photo_build_tiles.py); that the
owner's machine computes the village's bytes (the step's own check against
config/photo.json); that anything renders.
"""

import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
import pytest
from computed_for import computed_for

from mattini.datasets import load_datasets
from mattini.photo import (
    PhotoError,
    built_photo_block,
    encode_jpeg,
    load_photo_config,
    photo_grid,
    write_photo,
)
from mattini.world import load_world

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "shared" / "photo_fixture"
GENERATED = FIXTURE / "generated"
VECTORS = json.loads((REPO / "tests" / "shared" / "photo_vectors.json").read_text("utf-8"))
BOX = (2610412.5, 2610428.5, 1170207.0, 1170215.0)  # e_min, e_max, n_min, n_max
CELLS = {0.2: (80, 40), 0.5: (32, 16), 1.0: (16, 8)}  # columns, rows
PHOTO_COMMAND = "python -m mattini photo"
BLOCK_KEYS = {
    "area",
    "cell_m",
    "columns",
    "file",
    "format",
    "jpeg",
    "lv95_box",
    "pixels_sha256",
    "rows",
    "sha256",
    "source",
    "world_sha256",
}


def _source() -> np.ndarray:
    meta = json.loads((FIXTURE / "source.json").read_text(encoding="utf-8"))
    raw = (FIXTURE / "source.u8").read_bytes()
    return np.frombuffer(raw, dtype=np.uint8).reshape(meta["rows"], meta["columns"], 3)


def _config() -> dict:
    return load_photo_config(FIXTURE / "photo.json")


def _block() -> dict:
    return json.loads((GENERATED / "photo" / "fixture.json").read_text(encoding="utf-8"))


def _lock() -> dict:
    return json.loads((FIXTURE / "datasets.lock.json").read_text(encoding="utf-8"))


def _designed_texels() -> np.ndarray:
    """The 0.2 m grid as photo_vectors.json states it: each 8 x 8 block's grey, or the
    coloured corner's colour."""
    blocks = VECTORS["blocks"]
    size = blocks["texels"]
    texels = np.zeros((40, 80, 3), dtype=np.uint8)
    for by, row in enumerate(blocks["levels"]):
        for bx, level in enumerate(row):
            rgb = blocks["colour_mcu"]["rgb"] if level is None else [level] * 3
            texels[by * size : (by + 1) * size, bx * size : (bx + 1) * size] = rgb
    return texels


@pytest.mark.parametrize("cell", sorted(CELLS))
def test_the_grid_has_design_s_pixels_at_every_cell(cell):
    pixels = photo_grid(_source(), BOX, cell)
    columns, rows = CELLS[cell]
    assert pixels.dtype == np.uint8 and pixels.shape == (rows, columns, 3)
    expected = _config()["areas"]["fixture"]["expected_pixels_sha256"][format(cell, "g")]
    assert hashlib.sha256(pixels.tobytes()).hexdigest() == expected


def test_the_0_2_m_grid_is_the_designed_blocks():
    pixels = photo_grid(_source(), BOX, 0.2)
    assert pixels.tobytes() == _designed_texels().tobytes()
    assert hashlib.sha256(pixels.tobytes()).hexdigest() == _block()["pixels_sha256"]
    for point in VECTORS["points"]:
        column, row = point["texel"]
        assert pixels[row, column].tolist() == point["rgb"], point["name"]


@pytest.mark.parametrize("cell", sorted(CELLS))
def test_the_jpeg_is_design_s_bytes_at_every_cell(cell):
    data = encode_jpeg(photo_grid(_source(), BOX, cell))
    expected = _config()["areas"]["fixture"]["expected_sha256"][format(cell, "g")]
    assert hashlib.sha256(data).hexdigest() == expected
    if cell == 0.2:
        assert data == (GENERATED / "photo" / "fixture.jpg").read_bytes()


def test_write_photo_writes_the_fixture_files(tmp_path):
    block = _block()
    assert set(block) == BLOCK_KEYS
    assert block["jpeg"] == {"quality": 92, "subsampling": "4:2:0"}
    assert set(block["source"]) == {
        "attribution",
        "collection",
        "dataset",
        "edition",
        "resolution_m",
        "tiles",
    }
    assert all(type(v) is float for v in block["lv95_box"].values())
    written = write_photo(
        tmp_path,
        "fixture",
        photo_grid(_source(), BOX, 0.2),
        BOX,
        0.2,
        block["world_sha256"],
        block["source"],
    )
    assert written == block
    assert sorted(p.name for p in (tmp_path / "photo").iterdir()) == [
        "fixture.jpg",
        "fixture.jpg.import",
        "fixture.json",
    ]
    for rel in ("photo/fixture.jpg", "photo/fixture.jpg.import", "photo/fixture.json"):
        assert (tmp_path / rel).read_bytes() == (GENERATED / rel).read_bytes(), rel


def test_godot_keeps_the_jpeg_as_it_is():
    """The `.import` beside the JPEG: exactly these bytes, and the description, which is
    data, does not name it."""
    keep = b'[remap]\n\nimporter="keep"\n'
    assert (GENERATED / "photo" / "fixture.jpg.import").read_bytes() == keep
    assert ".import" not in (GENERATED / "photo" / "fixture.json").read_text(encoding="utf-8")


def test_the_fixture_records_what_it_was_computed_for():
    world_path = FIXTURE / "world.json"
    block = _block()
    assert block["world_sha256"] == hashlib.sha256(world_path.read_bytes()).hexdigest()
    lock = _lock()
    source_sha256 = hashlib.sha256((FIXTURE / "source.u8").read_bytes()).hexdigest()
    assert lock["datasets"]["swissimage"]["tiles"] == {
        "2610-1170": {"file": "source.u8", "sha256": source_sha256}
    }
    assert block["source"]["tiles"] == [{"sha256": source_sha256, "tile": "2610-1170"}]
    area = _config()["areas"]["fixture"]
    assert area["computed_for"] == computed_for(world_path, lock, "swissimage")
    assert area["expected_pixels_sha256"]["0.2"] == block["pixels_sha256"]
    assert area["expected_sha256"]["0.2"] == block["sha256"]


def _built(out: Path) -> dict | None:
    world_path = FIXTURE / "world.json"
    return built_photo_block(
        out,
        _config(),
        load_world(world_path),
        hashlib.sha256(world_path.read_bytes()).hexdigest(),
        load_datasets(FIXTURE / "datasets.json"),
        _lock(),
    )


def test_built_photo_block_reads_the_fixture_back(tmp_path):
    assert _built(GENERATED) == _block()
    assert _built(tmp_path) is None  # nothing built there


def test_built_photo_block_refuses_a_jpeg_that_is_not_the_described_one(tmp_path):
    shutil.copytree(GENERATED / "photo", tmp_path / "photo")
    jpeg = tmp_path / "photo" / "fixture.jpg"
    data = bytearray(jpeg.read_bytes())
    data[400] ^= 1
    jpeg.write_bytes(bytes(data))
    with pytest.raises(PhotoError, match=PHOTO_COMMAND):
        _built(tmp_path)
