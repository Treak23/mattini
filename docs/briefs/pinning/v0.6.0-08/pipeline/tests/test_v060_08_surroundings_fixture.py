"""Pinning tests for brief v0.6.0-08: the surroundings fixture's manifest block, the game's input.

Pinned decisions (design §2, §3; brief v0.6.0-08 decision 1, the block's shape, which brief
v0.6.0-07's `write_manifest` writes for the village):
- the manifest's `surroundings` block holds exactly 20 keys: the heights' description the
  surroundings step writes (`generated/surroundings/fixture.json`, verbatim: area, columns,
  cut_box, file, format, lv95_box, rows, sha256, source, spacing_m, world_sha256) and the colour's
  nine: colour_cell_m, colour_columns, colour_file, colour_format ("jpeg"),
  colour_pixels_sha256, colour_rows, colour_sha256, colour_source {attribution, collection,
  dataset ("swissimage_far"), edition} and filled_fraction;
- the colour covers the heights' own lv95_box: colour_columns × colour_cell_m is its width,
  colour_rows × colour_cell_m its depth; image row 0 is the north edge;
- colour_sha256 is the JPEG file's SHA-256, colour_pixels_sha256 that of its decoded RGB bytes
  (row-major, north to south), as the photo's block has them.

The fixture's colour (`generated/surroundings/fixture_colour.jpg`, design data of this brief) is
a synthetic placeholder, labelled as one in its attribution (Hard Rule 2): 15 × 18 pixels of
1000 m, pixel (c, r) designed as RGB (60 + 9c + 2r, 90 + 5r, 150 − 4c + 3r), so a flip or a swap
of the axes changes every pixel but the few on a symmetry line, encoded with photo.py's
`encode_jpeg` (Pillow, baseline, 4:2:0, quality 92); made two ways (plain Pillow in the pin
author's script, and `encode_jpeg` here; identical bytes). Its filled_fraction 0.2 is a designed
value (no pixel of it was filled by the far colour step's rule). The manifest's SHA-256 is pinned
here too, so a fixture rewritten by the code under test fails even where the comparison would
follow it (lesson 33).

GAME-ONLY DESIGN DATA (the release session's ruling of 2026-11-02): this JPEG and the colour keys
of this manifest's block are hand-made for the game's reader and loader, pinned here by SHA-256;
no pipeline step reproduces them (`write_manifest` over this folder gives a null block, brief
v0.6.0-07). The far colour step is proved by its own fixture, tests/shared/farcolour_fixture/
(brief v0.6.0-06).

Does NOT prove: that `write_manifest` writes this block (brief v0.6.0-07); that the far colour
step makes such a JPEG (brief v0.6.0-06); that the game reads it (the GUT tests of brief
v0.6.0-08); a JPEG difference between encoders (photo.py's `jpeg_encoder` names it).
"""

import hashlib
import io
import json

import numpy as np
from PIL import Image

from mattini.photo import encode_jpeg
from mattini.world import REPO

FIXTURE = REPO / "tests" / "shared" / "surroundings_fixture"
MANIFEST = FIXTURE / "generated" / "manifest.json"
DESCRIPTION = FIXTURE / "generated" / "surroundings" / "fixture.json"
COLOUR = FIXTURE / "generated" / "surroundings" / "fixture_colour.jpg"
MANIFEST_SHA256 = "c75b7bd7ee0b98249b6cb1f8bdb2cf570da075ac1c48a291de3d71241b11f557"
COLOUR_SHA256 = "c1d7cf77c72e23a70f650dce87e9027020353ff2cca63cfacdcebdcc64797781"
COLOUR_KEYS = {
    "colour_cell_m",
    "colour_columns",
    "colour_file",
    "colour_format",
    "colour_pixels_sha256",
    "colour_rows",
    "colour_sha256",
    "colour_source",
    "filled_fraction",
}
HEIGHT_KEYS = {
    "area",
    "columns",
    "cut_box",
    "file",
    "format",
    "lv95_box",
    "rows",
    "sha256",
    "source",
    "spacing_m",
    "world_sha256",
}
COLUMNS, ROWS = 15, 18


def _block() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))["surroundings"]


def _designed_pixels() -> np.ndarray:
    r, c = np.mgrid[0:ROWS, 0:COLUMNS]
    return np.stack([60 + 9 * c + 2 * r, 90 + 5 * r, 150 - 4 * c + 3 * r], axis=-1).astype(np.uint8)


def test_the_manifest_is_design_s_bytes():
    raw = MANIFEST.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == MANIFEST_SHA256
    manifest = json.loads(raw)
    text = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    assert text.encode("utf-8") == raw


def test_the_block_is_the_heights_description_and_the_colour_s_keys():
    block = _block()
    description = json.loads(DESCRIPTION.read_text(encoding="utf-8"))
    assert set(description) == HEIGHT_KEYS
    assert set(block) == HEIGHT_KEYS | COLOUR_KEYS
    assert len(block) == 20
    assert {key: block[key] for key in HEIGHT_KEYS} == description
    assert block["colour_format"] == "jpeg"
    assert block["colour_file"] == "surroundings/fixture_colour.jpg"
    assert set(block["colour_source"]) == {
        "attribution",
        "collection",
        "dataset",
        "edition",
    }
    assert block["colour_source"]["dataset"] == "swissimage_far"
    assert "synthetic" in block["colour_source"]["attribution"]
    assert isinstance(block["filled_fraction"], float) and 0.0 <= block["filled_fraction"] <= 1.0


def test_the_colour_covers_the_heights_box():
    block = _block()
    box = block["lv95_box"]
    assert (block["colour_columns"], block["colour_rows"]) == (COLUMNS, ROWS)
    assert block["colour_columns"] * block["colour_cell_m"] == box["e_max"] - box["e_min"]
    assert block["colour_rows"] * block["colour_cell_m"] == box["n_max"] - box["n_min"]
    # Not the heights' own count: a reader that sizes the texture by columns and rows fails.
    assert (block["colour_columns"], block["colour_rows"]) != (
        block["columns"],
        block["rows"],
    )


def test_the_colour_is_photo_py_s_jpeg_of_the_designed_pixels():
    data = COLOUR.read_bytes()
    assert hashlib.sha256(data).hexdigest() == COLOUR_SHA256
    assert encode_jpeg(_designed_pixels()) == data
    block = _block()
    assert block["colour_sha256"] == COLOUR_SHA256
    with Image.open(io.BytesIO(data)) as image:
        assert image.format == "JPEG" and image.mode == "RGB"
        assert image.size == (COLUMNS, ROWS)
        decoded = image.tobytes()
    assert hashlib.sha256(decoded).hexdigest() == block["colour_pixels_sha256"]


def test_the_designed_pixels_tell_a_flip_from_the_right_order():
    pixels = _designed_pixels()
    assert not np.array_equal(pixels, pixels[::-1])  # north-south
    assert not np.array_equal(pixels, pixels[:, ::-1])  # east-west
    assert tuple(pixels[0, 0]) == (60, 90, 150)  # the north-west corner
    assert tuple(pixels[ROWS - 1, COLUMNS - 1]) == (
        60 + 126 + 34,
        90 + 85,
        150 - 56 + 51,
    )
