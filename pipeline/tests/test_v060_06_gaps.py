"""Gap tests for brief v0.6.0-06: what the pinned tests leave open (decision 17), found by the
builder's own reading of the step against its rules.

- A four-band tile and a 16-bit tile are each refused by their own check, naming what is wrong
  (the pins only ask for the tile and `download farphoto`).
- The band of a negative height is the floor of its quotient, not its truncation: no sample of
  the fixture lies below 0 m, so the band rule is run on a few pixels by hand.
- A filled pixel's band takes the nearest band below that has a covered pixel before any above, even
  where a band above is nearer; the fixture's empty bands cannot tell that from "the nearest, ties
  below".
- A band's totals are 64-bit: 300 pixels of 255 are 76'500, above what 16 bits hold.
- When both downloads are missing, swissALTIRegio's is refused first.
- A grid with no covered pixel is refused (there is no colour to fill with).
- A tile the box only meets is cut at the box's edge; the village's box lies on the km grid, so the
  fixture never cuts one.
- A lock's swissimage_far entry that lists an absent cell twice, or pins a tile as more than a file
  name and a SHA-256, is refused naming `lock farphoto`; a description beside a config without a
  colour block is refused naming the config.

The batch gate's mutation prover then named more vacuous guards; each class is closed here, not
only its instance (lesson 9):

- Orientation and the band height: the fixture is square (30 x 30) and its bands are 100 m, so no
  pin could tell rows from columns or notice `band_m` ignored. A box of 30 columns x 25 rows (the
  world config's area 1 km x 500 m, grown by the same 1000 m) is built end to end from the
  fixture's own tiles and samples, at three band heights, against pixels computed here by a plain
  twin of design §2's rule; the built block's check holds that description and refuses a swapped
  one. The cell's refusal for a box corner it does not divide.
- The inputs: a swissALTIRegio zip of other bytes than the lock pins (the samples still parse)
  is refused; with both locks unfit swissALTIRegio's is named, with a far tile and a zip both
  damaged the far tile's; every key of the far provenance.json (collection, resolution, the
  tiles' order, a tile's file name and SHA-256 each alone, a list that is no list of objects, a
  file that is no object, no JSON, unreadable) is refused naming `download farphoto`.
- The world: a world config that changed after it was read, and an area the world config does not
  hold, are each a FarColourError naming the world config.
- The built block: every key of the description is held to its value and, where JSON writes the
  same number two ways (100 and 100.0), to its type; a config the shared reader refuses and a lock
  that cannot be read are FarColourErrors, not the shared code's SurroundingsError.
- What the step says and leaves alone: its progress lines name every file, count and value; only
  the `.part` files of `surroundings/` are removed, never a directory or a file elsewhere.

The second mutation prover's run closes more classes (the end of the file):

- A tile's size is its width, its height and its band count, each held on its own (the pins had a
  tile of the wrong width only); the three expected values are compared pixels, then fraction,
  then JPEG, each adjacent pair with both wrong; a far tile and a swissALTIRegio zip are decoded
  from the very bytes that were hashed, tried by changing the file between the read and the
  decode; a sample that is not on a pixel's centre is no pixel's sample, whatever the shared
  parser refuses; the description is written sorted, indented and in UTF-8, and the far dataset's
  reader refuses a datasets config that is no object, both tried on the helper itself (the
  step's own call sites cannot reach either); a description whose JPEG is not the one the config
  expects is refused by the key the description is held to (the JPEG's own comparison with the
  description was the second of three that implied one another).
- The config's colour settings: a bool, a float, a text or null is no whole number for any of the
  four, the filled fraction is a float from 0.0 to 1.0, both ends included, a hash is 64 lower-case
  hex digits as text, and the block is exactly its eight keys.
- No claim before its check: a refused comparison, a fill or an encoding or a write that stops
  leaves the progress before the line that says it held or happened, and the file being read is
  named before it is read; a file of other bytes fails the lock's SHA-256 before it is decoded.
- The order of the checks that the brief fixes (decision 6): the colour block before the axes,
  the axes before the area, the area and the lattice before the datasets config; a config with
  no area or two is a FarColourError before its area is read; a provenance that lists a tile the
  lock does not pin is a different list, not a lookup that fails.
- Every value in its role (the class of the first round's row/column test): each refusal that
  names two values or more (built and expected, listed and pinned, found and asked for) is held to
  its whole text, so that a swap of two values cannot pass; the tile refusals to their prefix
  (tile, then file); a non-square pixel and a tile without a CRS to their own words.

Does NOT prove: the village's values (the step's own comparison at the brief's real run and the
release gate); that these are the only gaps (the mutation prover looks for more).
"""

import copy
import hashlib
import io
import json
import struct
from decimal import Decimal

import numpy as np
import pytest
import rasterio
from PIL import Image
from synthetic_farphoto import (
    FIXTURE,
    far_name,
    fixture_cells,
    fixture_datasets,
    fixture_photo,
    fixture_source,
    geotiff,
    raw_inputs,
    tile_pixels,
)
from synthetic_regio import xyz_zip, zip_name

from mattini import farcolour
from mattini.farcolour import FarColourError, build_farcolour, built_farcolour_block
from mattini.lock import shape_problem
from mattini.photo import KEEP_IMPORT, encode_jpeg, jpeg_encoder
from mattini.surroundings import (
    SurroundingsError,
    check_surroundings_config,
    load_surroundings_config,
)
from mattini.world import load_world

LOCK_REGIO = "python -m mattini lock regio"
LOCK_FAR = "python -m mattini lock farphoto"
DOWNLOAD_REGIO = "python -m mattini download regio"
DOWNLOAD_FAR = "python -m mattini download farphoto"
STEP_COMMAND = "python -m mattini farcolour"
FILES = ["fixture_colour.jpg", "fixture_colour.jpg.import", "fixture_colour.json"]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _world():
    return load_world(FIXTURE / "world.json")


def _config():
    return load_surroundings_config(FIXTURE / "surroundings.json")


def _lock():
    return json.loads((FIXTURE / "datasets.lock.json").read_text(encoding="utf-8"))


def _recorded(lock):
    """The fixture's config whose colour records the fixture's world and both of `lock`'s entries."""
    config = _config()
    both = {name: lock["datasets"][name] for name in ("swissaltiregio", "swissimage_far")}
    text = json.dumps(both, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    config["areas"]["fixture"]["colour"]["computed_for"] = {
        "inputs_sha256": _sha(text.encode("utf-8")),
        "world_sha256": _sha((FIXTURE / "world.json").read_bytes()),
    }
    return config


# ------------------------------------------------------------------- the tiles


@pytest.mark.parametrize("case, word", [("four-bands", "4 bands"), ("16-bit", "uint16")])
def test_a_four_band_or_16_bit_tile_is_refused_by_its_own_check(tmp_path, case, word):
    source = fixture_source()
    pixels = tile_pixels(fixture_photo(source), source, "2615-1095")
    if case == "four-bands":
        body = geotiff(pixels[..., [0, 1, 2, 2]], 2_615_000.0, 1_096_000.0, 20)
    else:
        body = geotiff(pixels, 2_615_000.0, 1_096_000.0, 20, dtype_bits=16)
    root, lock = raw_inputs(tmp_path / "raw", bodies={"2615-1095": body})
    with pytest.raises(FarColourError) as refusal:
        build_farcolour(_world(), fixture_datasets(), lock, _recorded(lock), root, tmp_path / "out")
    text = str(refusal.value)
    assert "2615-1095" in text and word in text and DOWNLOAD_FAR in text, text
    assert not (tmp_path / "out").exists()


def test_a_tile_the_box_only_meets_is_cut_at_the_box_s_edge():
    pixels = np.zeros((4, 5, 3), np.uint8)
    covered = np.zeros((4, 5), bool)
    means = np.arange(27, dtype=np.uint8).reshape(3, 3, 3)
    farcolour._place(pixels, covered, means, -1, 3)  # one row above the grid, columns 3 to 5
    assert covered.sum() == 4 and covered[0:2, 3:5].all()
    assert (pixels[0:2, 3:5] == means[1:3, 0:2]).all()
    assert not pixels[2:].any() and not pixels[:, :3].any()
    farcolour._place(pixels, covered, means, 4, 0)  # wholly below the grid: nothing
    farcolour._place(pixels, covered, means, 0, -3)  # wholly west of it: nothing
    assert covered.sum() == 4


@pytest.mark.parametrize(
    "row, column",
    [
        (1, 2),  # inside
        (-1, 2),  # cut at the north edge
        (3, 2),  # cut at the south edge
        (1, -2),  # cut at the west edge
        (1, 5),  # cut at the east edge
        (-2, -2),  # a corner
        (3, 5),  # the opposite corner
        (4, 0),  # wholly south
        (-3, 0),  # wholly north
        (0, -3),  # wholly west
        (0, 7),  # wholly east
        (0, 9),  # wholly east, further off
        (0, 8),  # and one cell nearer, where a wrong test would slice a column of the tile
        (5, 0),  # wholly south, further off
        (-4, 0),  # wholly north, further off
        (0, -4),  # wholly west, further off
    ],
)
def test_a_tile_is_placed_and_cut_by_every_edge_of_a_grid_taller_than_wide_or_not(row, column):
    """A 4-row, 7-column grid (not square, so a row's limit is not a column's) against a model."""
    pixels = np.zeros((4, 7, 3), np.uint8)
    covered = np.zeros((4, 7), bool)
    means = np.arange(1, 28, dtype=np.uint8).reshape(3, 3, 3)
    want, want_covered = np.zeros_like(pixels), np.zeros_like(covered)
    for i in range(3):
        for j in range(3):
            if 0 <= row + i < 4 and 0 <= column + j < 7:
                want[row + i, column + j] = means[i, j]
                want_covered[row + i, column + j] = True
    farcolour._place(pixels, covered, means, row, column)
    assert (pixels == want).all() and (covered == want_covered).all()


# ------------------------------------------------------------------- the rule on a few pixels


def test_the_band_of_a_negative_height_is_floored():
    pixels = np.zeros((1, 3, 3), np.uint8)
    pixels[0, 0] = (10, 20, 30)  # covered, the sample -0.50 m: band -1
    pixels[0, 1] = (200, 100, 50)  # covered, +0.50 m: band 0
    covered = np.array([[True, True, False]])
    cents = np.array([[-50, 50, -9999]])  # filled, -99.99 m: band -1 (truncated it would be 0)
    farcolour._fill(pixels, covered, cents, 100)
    assert pixels[0, 2].tolist() == [10, 20, 30]


@pytest.mark.parametrize(
    "band, covered_bands, taken",
    [
        (5, [3, 7], 3),  # equally near: below
        (6, [3, 7], 3),  # a band above is nearer, and below still comes first
        (4, [3, 7], 3),
        (1, [3, 7], 3),  # none below: the nearest above
        (0, [3, 7], 3),
        (9, [3, 7], 7),
        (3, [3, 7], 3),  # a band with covered pixels is its own
        (-2, [-5, -1], -5),
    ],
)
def test_an_empty_band_takes_the_nearest_band_below_before_any_above(band, covered_bands, taken):
    assert farcolour._donor_band(band, covered_bands) == taken


def test_a_band_s_totals_are_64_bit():
    bands = np.zeros(300, np.int64)
    rgb = np.full((300, 3), 255, np.uint8)  # 76'500 per channel: more than 16 bits hold
    assert farcolour._band_means(bands, rgb)[0].tolist() == [255, 255, 255]
    rgb[:, 0] = 0
    rgb[:150, 0] = 1  # 150 over 300: an exact half rounds up
    assert farcolour._band_means(bands, rgb)[0].tolist() == [1, 255, 255]


def test_a_grid_without_a_covered_pixel_is_refused():
    """The fill's own refusal, called on its own: since brief v0.6.0-07 the step asks the lock's
    shape (`lock.shape_problem`) after the fits, so a lock that pins no far tile never reaches it
    (the next test)."""
    pixels = np.zeros((4, 4, 3), dtype=np.uint8)
    covered = np.zeros((4, 4), dtype=bool)
    cents = np.zeros((4, 4), dtype=np.int64)
    with pytest.raises(FarColourError) as refusal:
        farcolour._fill(pixels, covered, cents, 100)
    assert "no pixel is covered" in str(refusal.value), str(refusal.value)


def test_a_lock_that_pins_no_far_tile_is_refused_as_malformed_before_any_grid(tmp_path):
    source = fixture_source()
    source["absent"] = fixture_cells(source)
    root, lock = raw_inputs(tmp_path / "raw", source=source)
    assert lock["datasets"]["swissimage_far"]["tiles"] == {}
    with pytest.raises(FarColourError) as refusal:
        build_farcolour(_world(), fixture_datasets(), lock, _recorded(lock), root, tmp_path / "out")
    text = str(refusal.value)
    assert text == shape_problem(lock) and "tiles must be a non-empty object" in text, text
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize(
    "row, column",
    [(3, 17), (22, 6)],  # off the diagonal: the pinned (0, 0) and (29, 29) cannot tell a swap
)
def test_a_pixel_without_a_sample_is_refused_naming_its_row_and_column_apart(tmp_path, row, column):
    x, y = 2_615_050 + 100 * column, 1_096_950 - 100 * row
    source = fixture_source()
    tile = source["regio"]["tiles"]["2615-1094"]
    lines = tile["text"].split("\r\n")
    kept = [line for line in lines if not line.startswith(f"{x} {y} ")]
    assert len(kept) == len(lines) - 1
    tile["text"] = "\r\n".join(kept)
    root, lock = raw_inputs(tmp_path / "raw", source=source)
    with pytest.raises(FarColourError) as refusal:
        build_farcolour(_world(), fixture_datasets(), lock, _recorded(lock), root, tmp_path / "out")
    text = str(refusal.value)
    assert f"(row {row}, column {column}) at LV95 ({x}, {y})" in text, text
    assert DOWNLOAD_REGIO in text
    assert not (tmp_path / "out").exists()


# ------------------------------------------------------------------- the checks


def test_with_both_downloads_missing_swissaltiregio_s_is_refused_first(tmp_path):
    with pytest.raises(FarColourError) as refusal:
        build_farcolour(
            _world(),
            fixture_datasets(),
            _lock(),
            _config(),
            tmp_path / "raw",
            tmp_path / "out",
        )
    text = str(refusal.value)
    assert DOWNLOAD_REGIO in text and DOWNLOAD_FAR not in text, text


@pytest.mark.parametrize("case", ["an-absent-cell-twice", "a-pin-with-an-extra-key"])
def test_a_far_lock_entry_that_is_not_exactly_formed_is_refused_with_shape_problem_s_text(
    tmp_path, case
):
    """Re-cut by brief v0.6.0-07: the far entry's shape is the lock's (`lock.shape_problem`, asked
    once after both fits), whose text names the dataset and, as every step's does, all the lock
    commands, `lock farphoto` among them."""
    lock = _lock()
    entry = lock["datasets"]["swissimage_far"]
    if case == "an-absent-cell-twice":
        entry["absent"] = sorted([*entry["absent"], "2616-1094"])
    else:
        entry["tiles"]["2615-1094"]["size_bytes"] = 1
    with pytest.raises(FarColourError) as refusal:
        build_farcolour(
            _world(), fixture_datasets(), lock, _recorded(lock), tmp_path / "raw", tmp_path / "out"
        )
    text = str(refusal.value)
    assert text == shape_problem(lock), text
    assert "'swissimage_far'" in text and LOCK_FAR in text, text
    assert not (tmp_path / "out").exists()


def test_a_description_beside_a_config_without_a_colour_block_is_refused_naming_the_config(
    tmp_path,
):
    root, lock = raw_inputs(tmp_path / "raw")
    out = tmp_path / "out"
    build_farcolour(_world(), fixture_datasets(), lock, _recorded(lock), root, out)
    config = copy.deepcopy(_config())
    del config["areas"]["fixture"]["colour"]
    world_sha256 = _sha((FIXTURE / "world.json").read_bytes())
    with pytest.raises(FarColourError) as refusal:
        built_farcolour_block(out, config, _world(), world_sha256, fixture_datasets(), lock)
    text = str(refusal.value)
    assert "colour" in text and "config/surroundings.json" in text, text


# ------------------------------------------------------------------- the checks the pins leave open


def _built(tmp_path):
    """The fixture built once: (out, root, lock)."""
    root, lock = raw_inputs(tmp_path / "raw")
    out = tmp_path / "out"
    build_farcolour(_world(), fixture_datasets(), lock, _recorded(lock), root, out)
    return out, root, lock


def _world_sha256():
    return _sha((FIXTURE / "world.json").read_bytes())


def _flip_last_byte(path):
    data = bytearray(path.read_bytes())
    data[-1] ^= 1
    path.write_bytes(bytes(data))


def _fixture_world_at(path, areas=None, **top):
    """The fixture's world config written to `path` with `areas` and `top`'s keys replaced."""
    data = json.loads((FIXTURE / "world.json").read_text(encoding="utf-8"))
    data.update(top)
    if areas is not None:
        data["areas"] = areas
    raw = (json.dumps(data, indent=2, sort_keys=True) + "\n").encode("utf-8")
    path.write_bytes(raw)
    return load_world(path), _sha(raw)


def test_a_cell_that_does_not_divide_the_box_s_corners_is_refused_naming_it(tmp_path):
    """The cell is the datasets' resolution and 5 source pixels and divides the km, only the box
    does not: margin 500 m puts the box's west edge at 2'615'500 m, not a multiple of 1000 m."""
    config, datasets = _config(), fixture_datasets()
    config["areas"]["fixture"]["margin_m"] = 500
    config["areas"]["fixture"]["colour"]["cell_m"] = 1000
    datasets["swissaltiregio"]["resolution_m"] = 1000
    datasets["swissimage_far"]["resolution_m"] = 200
    with pytest.raises(FarColourError) as refusal:
        build_farcolour(_world(), datasets, _lock(), config, tmp_path / "raw", tmp_path / "out")
    text = str(refusal.value)
    assert "cell_m" in text and "[2615500, 2617500, 1094500, 1096500]" in text, text
    assert not (tmp_path / "out").exists()


# ------------------------------------------------------------------- the world


def test_a_world_config_that_changed_after_it_was_read_is_refused(tmp_path):
    world, _ = _fixture_world_at(tmp_path / "world.json")
    _fixture_world_at(tmp_path / "world.json", height_offset_m=1250.5)  # edited, not re-read
    with pytest.raises(FarColourError) as refusal:
        build_farcolour(
            world, fixture_datasets(), _lock(), _config(), tmp_path / "raw", tmp_path / "out"
        )
    text = str(refusal.value)
    assert str(tmp_path / "world.json") in text and "changed while the colour was built" in text
    assert not (tmp_path / "out").exists()


def test_an_area_the_world_config_does_not_hold_is_refused_naming_the_world(tmp_path):
    area = json.loads((FIXTURE / "world.json").read_text(encoding="utf-8"))["areas"]["fixture"]
    world, _ = _fixture_world_at(tmp_path / "world.json", areas={"other": area})
    with pytest.raises(FarColourError) as refusal:
        build_farcolour(
            world, fixture_datasets(), _lock(), _config(), tmp_path / "raw", tmp_path / "out"
        )
    text = str(refusal.value)
    assert str(tmp_path / "world.json") in text and "'fixture'" in text, text
    assert not (tmp_path / "out").exists()


# ------------------------------------------------------------------- the lock and the files, in order


def test_with_both_locks_unfit_swissaltiregio_s_is_named_first(tmp_path):
    lock = _lock()
    lock["datasets"]["swissaltiregio"]["edition"] = "2025-06"
    lock["datasets"]["swissimage_far"]["edition"] = "2020"
    with pytest.raises(FarColourError) as refusal:
        build_farcolour(
            _world(), fixture_datasets(), lock, _config(), tmp_path / "raw", tmp_path / "out"
        )
    text = str(refusal.value)
    assert LOCK_REGIO in text and LOCK_FAR not in text, text


def test_with_a_far_tile_and_a_regio_zip_both_damaged_the_far_tile_is_refused_first(tmp_path):
    root, lock = raw_inputs(tmp_path / "raw")
    _flip_last_byte(root / "swissimage_far" / "2023" / far_name("2615-1095", "2023", 20))
    _flip_last_byte(root / "swissaltiregio" / "2026-06" / zip_name("2615-1094"))
    with pytest.raises(FarColourError) as refusal:
        build_farcolour(_world(), fixture_datasets(), lock, _recorded(lock), root, tmp_path / "out")
    text = str(refusal.value)
    assert "2615-1095" in text and DOWNLOAD_FAR in text and DOWNLOAD_REGIO not in text, text
    assert not (tmp_path / "out").exists()


def test_a_regio_zip_of_other_bytes_than_the_lock_pins_is_refused_naming_it(tmp_path):
    """The same samples in another zip (deflated, the fixture's is stored): it parses, so only the
    SHA-256 against the lock can tell."""
    root, lock = raw_inputs(tmp_path / "raw")
    tile = fixture_source()["regio"]["tiles"]["2615-1094"]
    other = xyz_zip(tile["member"], tile["text"], deflated=True)
    path = root / "swissaltiregio" / "2026-06" / zip_name("2615-1094")
    pinned = lock["datasets"]["swissaltiregio"]["tiles"]["2615-1094"]["sha256"]
    assert _sha(other) != pinned and _sha(path.read_bytes()) == pinned
    path.write_bytes(other)
    with pytest.raises(FarColourError) as refusal:
        build_farcolour(_world(), fixture_datasets(), lock, _recorded(lock), root, tmp_path / "out")
    text = str(refusal.value)
    assert "2615-1094" in text and _sha(other) in text and pinned in text, text
    assert DOWNLOAD_REGIO in text and DOWNLOAD_FAR not in text, text
    assert not (tmp_path / "out").exists()


def _edit_far_provenance(root, edit):
    path = root / "swissimage_far" / "2023" / "provenance.json"
    provenance = json.loads(path.read_text(encoding="utf-8"))
    edit(provenance)
    path.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _set_tile(provenance, index, value):
    provenance["tiles"][index] = value


@pytest.mark.parametrize(
    "case, edit",
    [
        ("collection", lambda p: p.update(collection="ch.swisstopo.swissimage-dop10-2")),
        ("resolution_m", lambda p: p.update(resolution_m=2)),
        ("tiles-in-another-order", lambda p: p["tiles"].reverse()),
        ("a-tile-s-file-name", lambda p: p["tiles"][1].update(file="other.tif")),
        ("a-tile-s-sha256", lambda p: p["tiles"][1].update(sha256="1" * 64)),
        ("tiles-an-object", lambda p: p.update(tiles={})),
        ("tiles-none", lambda p: p.update(tiles=None)),
        ("a-tile-that-is-no-object", lambda p: _set_tile(p, 0, 1)),
    ],
)
def test_every_key_of_the_far_provenance_is_held_to_the_lock(tmp_path, case, edit):
    root, lock = raw_inputs(tmp_path / "raw")
    _edit_far_provenance(root, edit)
    with pytest.raises(FarColourError) as refusal:
        build_farcolour(_world(), fixture_datasets(), lock, _recorded(lock), root, tmp_path / "out")
    text = str(refusal.value)
    assert DOWNLOAD_FAR in text and DOWNLOAD_REGIO not in text, text
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("case", ["not-json", "not-utf-8", "not-an-object", "unreadable"])
def test_a_far_provenance_that_is_no_json_object_is_refused(tmp_path, case):
    root, lock = raw_inputs(tmp_path / "raw")
    path = root / "swissimage_far" / "2023" / "provenance.json"
    path.unlink()
    if case == "unreadable":
        path.mkdir()
    else:
        path.write_bytes({"not-json": b"{", "not-utf-8": b"\xff\xfe", "not-an-object": b"[]"}[case])
    with pytest.raises(FarColourError) as refusal:
        build_farcolour(_world(), fixture_datasets(), lock, _recorded(lock), root, tmp_path / "out")
    text = str(refusal.value)
    assert str(path) in text and DOWNLOAD_FAR in text, text
    assert not (tmp_path / "out").exists()


# ------------------------------------------------------------------- the built block's own checks


@pytest.mark.parametrize(
    "case, edit",
    [
        ("cell-written-as-an-int", lambda b: b.update(colour_cell_m=100)),
        ("columns-written-as-a-float", lambda b: b.update(colour_columns=30.0)),
        ("rows-written-as-a-float", lambda b: b.update(colour_rows=30.0)),
        ("rows-another", lambda b: b.update(colour_rows=31)),
        ("file-another", lambda b: b.update(colour_file="surroundings/other_colour.jpg")),
        ("format-another", lambda b: b.update(colour_format="png")),
        ("pixels-sha256-another", lambda b: b.update(colour_pixels_sha256="0" * 64)),
        ("jpeg-sha256-another", lambda b: b.update(colour_sha256="0" * 64)),
        ("a-key-missing", lambda b: b.pop("colour_rows")),
        ("source-with-an-extra-key", lambda b: b["colour_source"].update(extra=1)),
        ("source-without-a-key", lambda b: b["colour_source"].pop("attribution")),
        ("source-no-object", lambda b: b.update(colour_source=[])),
        ("source-null", lambda b: b.update(colour_source=None)),
        ("source-a-number", lambda b: b.update(colour_source=3)),
        ("source-attribution", lambda b: b["colour_source"].update(attribution="© nobody")),
        ("source-collection", lambda b: b["colour_source"].update(collection="ch.swisstopo.x")),
        ("source-dataset", lambda b: b["colour_source"].update(dataset="swissimage")),
    ],
)
def test_every_key_of_a_built_description_is_held_to_its_value_and_type(tmp_path, case, edit):
    out, _, lock = _built(tmp_path)
    path = out / "surroundings" / "fixture_colour.json"
    block = json.loads(path.read_text(encoding="utf-8"))
    edit(block)
    path.write_text(json.dumps(block, indent=2), encoding="utf-8")
    with pytest.raises(FarColourError) as refusal:
        built_farcolour_block(out, _config(), _world(), _world_sha256(), fixture_datasets(), lock)
    assert STEP_COMMAND in str(refusal.value), str(refusal.value)


@pytest.mark.parametrize(
    "raw", [b"{", b"\xff\xfe", b"[]", b"3"], ids=["json", "utf-8", "list", "int"]
)
def test_a_description_that_is_no_json_object_is_refused_naming_the_step(tmp_path, raw):
    out, _, lock = _built(tmp_path)
    (out / "surroundings" / "fixture_colour.json").write_bytes(raw)
    with pytest.raises(FarColourError) as refusal:
        built_farcolour_block(out, _config(), _world(), _world_sha256(), fixture_datasets(), lock)
    assert STEP_COMMAND in str(refusal.value), str(refusal.value)


def test_a_description_that_names_another_jpeg_is_refused_though_that_file_is_there(tmp_path):
    """The other file is the very JPEG and its .import: only the key's value can tell."""
    out, _, lock = _built(tmp_path)
    folder = out / "surroundings"
    (folder / "other_colour.jpg").write_bytes((folder / "fixture_colour.jpg").read_bytes())
    (folder / "other_colour.jpg.import").write_bytes(
        (folder / "fixture_colour.jpg.import").read_bytes()
    )
    path = folder / "fixture_colour.json"
    block = json.loads(path.read_text(encoding="utf-8"))
    block["colour_file"] = "surroundings/other_colour.jpg"
    path.write_text(json.dumps(block, indent=2), encoding="utf-8")
    with pytest.raises(FarColourError) as refusal:
        built_farcolour_block(out, _config(), _world(), _world_sha256(), fixture_datasets(), lock)
    text = str(refusal.value)
    assert "colour_file" in text and STEP_COMMAND in text, text


def test_a_filled_fraction_of_zero_written_as_an_int_is_refused(tmp_path):
    """JSON writes the number zero as 0 or 0.0; the description's is a float (the control)."""
    out, _, lock = _built(tmp_path)
    config = _config()
    config["areas"]["fixture"]["colour"]["expected_filled_fraction"] = 0.0
    path = out / "surroundings" / "fixture_colour.json"
    block = json.loads(path.read_text(encoding="utf-8"))
    block["filled_fraction"] = 0.0
    path.write_text(json.dumps(block, indent=2), encoding="utf-8")
    datasets = fixture_datasets()
    assert built_farcolour_block(out, config, _world(), _world_sha256(), datasets, lock) == block
    block["filled_fraction"] = 0
    path.write_text(json.dumps(block, indent=2), encoding="utf-8")
    with pytest.raises(FarColourError) as refusal:
        built_farcolour_block(out, config, _world(), _world_sha256(), datasets, lock)
    assert "filled_fraction" in str(refusal.value), str(refusal.value)


def test_a_config_the_shared_reader_refuses_is_a_far_colour_error_in_the_built_block(tmp_path):
    config = _config()
    config["areas"]["fixture"]["colour"]["band_m"] = 0
    with pytest.raises(FarColourError) as refusal:
        built_farcolour_block(
            tmp_path, config, _world(), _world_sha256(), fixture_datasets(), _lock()
        )
    assert not isinstance(refusal.value, SurroundingsError)
    assert "band_m" in str(refusal.value), str(refusal.value)


@pytest.mark.parametrize("case", ["missing", "not-json"])
def test_a_lock_that_cannot_be_read_is_a_far_colour_error_in_the_built_block(tmp_path, case):
    out, _, _ = _built(tmp_path)
    path = tmp_path / "datasets.lock.json"
    if case == "not-json":
        path.write_bytes(b"{")
    with pytest.raises(FarColourError) as refusal:
        built_farcolour_block(out, _config(), _world(), _world_sha256(), fixture_datasets(), path)
    assert not isinstance(refusal.value, SurroundingsError)
    assert str(path) in str(refusal.value), str(refusal.value)


# ------------------------------------------------------------------- what it says and leaves alone


def test_the_progress_lines_name_every_file_count_and_value(tmp_path):
    root, lock = raw_inputs(tmp_path / "raw")
    out = tmp_path / "out"
    lines = []
    block = build_farcolour(
        _world(), fixture_datasets(), lock, _recorded(lock), root, out, progress=lines.append
    )
    colour = _config()["areas"]["fixture"]["colour"]
    far = root / "swissimage_far" / "2023"
    regio = root / "swissaltiregio" / "2026-06"
    far_tiles = ("2615-1094", "2615-1095", "2615-1096", "2616-1095", "2616-1096", "2617-1096")
    regio_tiles = ("2605-1084", "2605-1094", "2615-1084", "2615-1094")
    expected = [
        *(f"reading {far / far_name(tile, '2023', 20)}" for tile in far_tiles),
        *(f"reading {regio / zip_name(tile)}" for tile in regio_tiles),
        "filling the 300 pixels without a photo by their altitude",
        "the pixels have the SHA-256 config/surroundings.json expects, "
        + colour["expected_pixels_sha256"],
        "encoding the JPEG",
        f"the JPEG has the SHA-256 config/surroundings.json expects, {colour['expected_sha256']}",
        f"wrote {out / block['colour_file']} (30 × 30 pixels)",
    ]
    assert lines == expected


@pytest.mark.parametrize("parts, words", [(1, "1 .part file left"), (2, "2 .part files left")])
def test_the_progress_counts_the_part_files_it_removed(tmp_path, parts, words):
    folder = tmp_path / "out" / "surroundings"
    folder.mkdir(parents=True)
    for number in range(parts):
        (folder / f"old{number}.json.part").write_bytes(b"a run cut short")
    root, lock = raw_inputs(tmp_path / "raw")
    lines = []
    build_farcolour(
        _world(),
        fixture_datasets(),
        lock,
        _recorded(lock),
        root,
        tmp_path / "out",
        progress=lines.append,
    )
    assert lines[-1] == f"removed {words} in surroundings/", lines[-1]
    assert lines[-2].startswith("wrote ")


def test_only_the_part_files_of_the_surroundings_folder_are_removed(tmp_path):
    out = tmp_path / "out"
    folder = out / "surroundings"
    (folder / "kept.part").mkdir(parents=True)
    (folder / "kept.part" / "inner.txt").write_bytes(b"a directory is no part file")
    (folder / "stale.json.part").write_bytes(b"a run cut short")
    (out / "stray.part").write_bytes(b"beside surroundings/, not in it")
    (out / "elsewhere").mkdir()
    (out / "elsewhere" / "other.part").write_bytes(b"in another folder")
    root, lock = raw_inputs(tmp_path / "raw")
    build_farcolour(_world(), fixture_datasets(), lock, _recorded(lock), root, out)
    assert not (folder / "stale.json.part").exists()
    assert (folder / "kept.part" / "inner.txt").read_bytes() == b"a directory is no part file"
    assert (out / "stray.part").read_bytes() == b"beside surroundings/, not in it"
    assert (out / "elsewhere" / "other.part").read_bytes() == b"in another folder"
    assert sorted(p.name for p in folder.iterdir()) == sorted([*FILES, "kept.part"])


# ------------------------------------------------------------------- a wide box, other bands


WIDE_AREA = {"e_max": 2_617_000.0, "e_min": 2_616_000.0, "n_max": 1_095_500.0, "n_min": 1_095_000.0}
WIDE_BOX = {"e_max": 2_618_000.0, "e_min": 2_615_000.0, "n_max": 1_096_500.0, "n_min": 1_094_000.0}
WIDE_COLUMNS, WIDE_ROWS = 30, 25


def _wide_twin(band_m: int) -> tuple[np.ndarray, int]:
    """design §2's colour of the wide box (30 columns x 25 rows from (2'615'000, 1'096'500)) and
    the count of its filled pixels, in plain numpy from source.json and photo.u8; no mattini code.

    The box's pixels are the fixture's source pixels from row 25 southwards (N 1'096'500), five a
    side; the fixture's three absent cells and its samples are those of the pixels' centres.
    """
    source = fixture_source()
    photo = fixture_photo(source).astype(np.int64)[25:]
    means = (photo.reshape(WIDE_ROWS, 5, WIDE_COLUMNS, 5, 3).sum(axis=(1, 3)) + 12) // 25
    found = {}
    for tile in source["regio"]["tiles"].values():
        for line in tile["text"].split("\r\n")[1:-1]:
            x, y, z = line.split(" ")
            found[int(x), int(y)] = int(Decimal(z) * 100)
    covered = np.zeros((WIDE_ROWS, WIDE_COLUMNS), bool)
    band = np.zeros((WIDE_ROWS, WIDE_COLUMNS), np.int64)
    for r in range(WIDE_ROWS):
        for c in range(WIDE_COLUMNS):
            x, y = 2_615_050 + 100 * c, 1_096_450 - 100 * r
            covered[r, c] = f"{x // 1000}-{y // 1000}" not in source["absent"]
            band[r, c] = found[x, y] // (100 * band_m)
    mean = {}
    for b in sorted(set(band[covered].tolist())):
        chosen = covered & (band == b)
        n = int(chosen.sum())
        mean[b] = (means[chosen].sum(axis=0) + n // 2) // n

    def donor(b: int) -> int:
        below = [other for other in mean if other < b]
        above = [other for other in mean if other > b]
        return b if b in mean else max(below) if below else min(above)

    pixels = np.where(covered[..., None], means, 0)
    for r in range(WIDE_ROWS):
        for c in range(WIDE_COLUMNS):
            if not covered[r, c]:
                pixels[r, c] = mean[donor(int(band[r, c]))]
    return pixels.astype(np.uint8), int((~covered).sum())


def _wide_build(tmp_path, band_m, progress=None):
    """The step on the wide box, its expected values the twin's: (block, out, config, world, ...)."""
    world, world_sha256 = _fixture_world_at(
        tmp_path / "wide_world.json", areas={"fixture": WIDE_AREA}
    )
    root, lock = raw_inputs(tmp_path / "raw")
    pixels, filled = _wide_twin(band_m)
    config = _recorded(lock)
    area = config["areas"]["fixture"]
    area["expected_lv95_box"] = dict(WIDE_BOX)
    area["expected_rows"] = 6  # the heights' 500 m spacing: 2500 m / 500 + 1
    area["colour"].update(
        band_m=band_m,
        expected_rows=WIDE_ROWS,
        expected_pixels_sha256=_sha(pixels.tobytes()),
        expected_sha256=_sha(encode_jpeg(pixels)),
        expected_filled_fraction=filled / (WIDE_ROWS * WIDE_COLUMNS),
    )
    area["colour"]["computed_for"]["world_sha256"] = world_sha256
    out = tmp_path / "out"
    block = build_farcolour(world, fixture_datasets(), lock, config, root, out, progress=progress)
    return block, out, config, world, world_sha256, lock


def test_the_wide_box_s_bands_are_told_apart_by_their_pixels():
    """Without this the next test could pass with `band_m` ignored."""
    shas = {band_m: _sha(_wide_twin(band_m)[0].tobytes()) for band_m in (50, 100, 250)}
    assert len(set(shas.values())) == 3, shas
    assert _wide_twin(100)[1] == 300


@pytest.mark.parametrize("band_m", [100, 50, 250])
def test_a_box_wider_than_tall_and_another_band_height_are_built_as_the_rule_says(tmp_path, band_m):
    lines = []
    block, out, config, _, _, _ = _wide_build(tmp_path, band_m, progress=lines.append)
    colour = config["areas"]["fixture"]["colour"]
    assert lines[-1] == f"wrote {out / block['colour_file']} (30 × 25 pixels)", lines[-1]
    filled = _wide_twin(band_m)[1]
    assert f"filling the {filled} pixels without a photo by their altitude" in lines
    assert (block["colour_columns"], block["colour_rows"]) == (WIDE_COLUMNS, WIDE_ROWS)
    assert block["colour_pixels_sha256"] == colour["expected_pixels_sha256"]
    assert block["colour_sha256"] == colour["expected_sha256"]
    assert block["filled_fraction"] == colour["expected_filled_fraction"]
    jpeg = (out / block["colour_file"]).read_bytes()
    assert _sha(jpeg) == colour["expected_sha256"]
    assert Image.open(io.BytesIO(jpeg)).size == (WIDE_COLUMNS, WIDE_ROWS)  # width x height
    described = json.loads((out / "surroundings" / "fixture_colour.json").read_text())
    assert described == block


def test_the_built_block_of_a_wide_box_holds_and_a_swapped_one_does_not(tmp_path):
    block, out, config, world, world_sha256, lock = _wide_build(tmp_path, 100)
    datasets = fixture_datasets()
    assert built_farcolour_block(out, config, world, world_sha256, datasets, lock) == block
    path = out / "surroundings" / "fixture_colour.json"
    for edit in (
        {"colour_columns": WIDE_ROWS, "colour_rows": WIDE_COLUMNS},  # swapped
        {"colour_columns": WIDE_ROWS},
        {"colour_rows": WIDE_COLUMNS},
    ):
        path.write_text(json.dumps({**block, **edit}, indent=2), encoding="utf-8")
        with pytest.raises(FarColourError) as refusal:
            built_farcolour_block(out, config, world, world_sha256, datasets, lock)
        assert STEP_COMMAND in str(refusal.value), edit


# ------------------------------------------------------------------- the datasets config and the lock's far entry


def _refused(tmp_path, *, datasets=None, lock=None):
    with pytest.raises(FarColourError) as refusal:
        build_farcolour(
            _world(),
            datasets or fixture_datasets(),
            lock or _lock(),
            _config(),
            tmp_path / "raw",
            tmp_path / "out",
        )
    assert not (tmp_path / "out").exists()
    return str(refusal.value)


@pytest.mark.parametrize(
    "case, edit, word",
    [
        ("no-dataset", lambda d: d.pop("swissimage_far"), "has no 'swissimage_far' dataset"),
        ("dataset-no-object", lambda d: d.update(swissimage_far=[]), "has no 'swissimage_far'"),
        ("no-attribution", lambda d: d["swissimage_far"].pop("attribution"), "attribution must"),
        (
            "collection-empty",
            lambda d: d["swissimage_far"].update(collection=""),
            "collection must",
        ),
        ("edition-a-number", lambda d: d["swissimage_far"].update(edition=2023), "edition must"),
        (
            "resolution-zero",
            lambda d: d["swissimage_far"].update(resolution_m=0),
            "resolution_m must",
        ),
        (
            "resolution-negative",
            lambda d: d["swissimage_far"].update(resolution_m=-2),
            "resolution_m must",
        ),
        (
            "resolution-a-float",
            lambda d: d["swissimage_far"].update(resolution_m=20.0),
            "resolution_m must",
        ),
        (
            "resolution-a-bool",
            lambda d: d["swissimage_far"].update(resolution_m=True),
            "resolution_m must",
        ),
        (
            "resolution-a-text",
            lambda d: d["swissimage_far"].update(resolution_m="20"),
            "resolution_m must",
        ),
    ],
)
def test_a_datasets_config_without_a_usable_far_dataset_is_refused_naming_it(
    tmp_path, case, edit, word
):
    datasets = fixture_datasets()
    edit(datasets)
    text = _refused(tmp_path, datasets=datasets)
    assert "config/datasets.json" in text and word in text, text


def test_a_far_resolution_of_one_metre_is_a_usable_dataset_and_only_the_cell_is_refused(tmp_path):
    datasets = fixture_datasets()
    datasets["swissimage_far"]["resolution_m"] = 1  # a whole number of metres: 5 m is not the cell
    text = _refused(tmp_path, datasets=datasets)
    assert "cell_m" in text and "must be a whole number" not in text, text


@pytest.mark.parametrize(
    "case, edit, words",
    [
        (
            "no-entry",
            lambda e, lock: lock["datasets"].pop("swissimage_far"),
            ["has no 'swissimage_far'"],
        ),
        ("no-tiles", lambda e, lock: e.pop("tiles"), ["has no tiles"]),
        ("tiles-a-list", lambda e, lock: e.update(tiles=[]), ["has no tiles"]),
        ("absent-a-text", lambda e, lock: e.update(absent="2617-1094"), ["no absent list"]),
        ("absent-with-a-number", lambda e, lock: e["absent"].append(7), ["no absent list"]),
        ("a-cell-in-neither", lambda e, lock: e["absent"].remove("2617-1094"), ["2617-1094"]),
        (
            "a-cell-in-both",
            lambda e, lock: e["absent"].append("2615-1094"),
            ["2615-1094", "both as pinned tiles and as absent"],
        ),
        (
            "a-cell-beyond-the-box",
            lambda e, lock: e["absent"].append("2618-1094"),
            ["2618-1094", "does not need"],
        ),
    ],
)
def test_a_far_lock_entry_that_does_not_fit_says_what_and_where(tmp_path, case, edit, words):
    lock = _lock()
    edit(lock["datasets"].get("swissimage_far"), lock)
    text = _refused(tmp_path, lock=lock)
    assert LOCK_FAR in text and "area 'fixture'" in text, text
    for word in words:
        assert word in text, text


@pytest.mark.parametrize(
    "case, edit",
    [
        ("a-pin-no-object", lambda e: e["tiles"].update({"2615-1094": "abc"})),
        ("a-pin-file-unsafe", lambda e: e["tiles"]["2615-1094"].update(file="../x.tif")),
        ("a-pin-sha256-short", lambda e: e["tiles"]["2615-1094"].update(sha256="ab")),
    ],
)
def test_a_far_pin_that_is_not_a_file_name_and_a_checksum_is_refused_by_the_lock_s_shape(
    tmp_path, case, edit
):
    """The three cases that brief v0.6.0-06's own pin check refused naming `lock farphoto` and the
    area are `lock.shape_problem`'s since brief v0.6.0-07: its text names the tile, the dataset
    and all the lock commands."""
    lock = _lock()
    edit(lock["datasets"]["swissimage_far"])
    text = _refused(tmp_path, lock=lock)
    assert text == shape_problem(lock), text
    assert "2615-1094" in text and "'swissimage_far'" in text and LOCK_FAR in text, text


def test_a_long_list_in_a_refusal_is_cut_after_its_first_six():
    assert farcolour._some(["a", "b"]) == "['a', 'b']"
    assert farcolour._some(list("abcdef")) == "['a', 'b', 'c', 'd', 'e', 'f']"
    assert farcolour._some(list("abcdefg")) == "['a', 'b', 'c', 'd', 'e', 'f'] and 1 more"
    assert farcolour._some(list("abcdefghij"), 3) == "['a', 'b', 'c'] and 7 more"


def test_a_far_provenance_that_lists_other_tiles_names_both_lists(tmp_path):
    root, lock = raw_inputs(tmp_path / "raw")
    _edit_far_provenance(root, lambda p: p["tiles"].pop(0))
    with pytest.raises(FarColourError) as refusal:
        build_farcolour(_world(), fixture_datasets(), lock, _recorded(lock), root, tmp_path / "out")
    text = str(refusal.value)
    listed, pinned = text.split("the lock pins")
    assert "'2615-1094'" not in listed and "'2615-1095'" in listed, text
    assert "'2615-1094'" in pinned, text


def test_a_description_that_cannot_be_read_is_refused_naming_the_step(tmp_path):
    out, _, lock = _built(tmp_path)
    path = out / "surroundings" / "fixture_colour.json"
    path.unlink()
    path.mkdir()  # there, and not a file
    with pytest.raises(FarColourError) as refusal:
        built_farcolour_block(out, _config(), _world(), _world_sha256(), fixture_datasets(), lock)
    text = str(refusal.value)
    assert STEP_COMMAND in text and "cannot read" in text, text


@pytest.mark.parametrize("key", ["band_m", "cell_m", "expected_columns", "expected_rows"])
def test_the_smallest_whole_number_is_a_valid_colour_setting(key):
    """The pinned config cases refuse 0 and below; 1 is the edge that stays valid."""
    config = _config()
    config["areas"]["fixture"]["colour"][key] = 1
    check_surroundings_config(config)
    config["areas"]["fixture"]["colour"][key] = 0
    with pytest.raises(SurroundingsError):
        check_surroundings_config(config)


# ------------------------------------------------------------------- the second prover's classes


@pytest.mark.parametrize(
    "columns, rows",
    [(50, 49), (50, 51), (49, 50), (51, 50), (49, 49), (51, 51)],
    ids=[
        "one-row-short",
        "one-row-long",
        "one-column-short",
        "one-column-long",
        "both-short",
        "both-long",
    ],
)
def test_a_tile_of_another_width_or_height_is_refused_naming_its_size(tmp_path, columns, rows):
    """The pinned case is a tile one column short; a tile's height is held on its own too."""
    source = fixture_source()
    pixels = tile_pixels(fixture_photo(source), source, "2615-1095")  # 50 x 50 at 20 m
    body = geotiff(np.resize(pixels, (rows, columns, 3)), 2_615_000.0, 1_096_000.0, 20)
    root, lock = raw_inputs(tmp_path / "raw", bodies={"2615-1095": body})
    with pytest.raises(FarColourError) as refusal:
        build_farcolour(_world(), fixture_datasets(), lock, _recorded(lock), root, tmp_path / "out")
    text = str(refusal.value)
    assert text == (
        f"tile 2615-1095: {_far_path(root)}: it is {columns} × {rows} pixels in 3 bands, "
        f"expected 50 × 50 in 3; `{DOWNLOAD_FAR}` fetches it again"
    ), text
    assert not (tmp_path / "out").exists()


PIXELS_WORDS = "the colour pixels built here"
FRACTION_WORDS = "the filled fraction built here"
JPEG_WORDS = "this machine's JPEG encoder"


@pytest.mark.parametrize(
    "wrong, named",
    [
        (("pixels", "fraction"), PIXELS_WORDS),
        (("fraction", "jpeg"), FRACTION_WORDS),
        (("pixels", "jpeg"), PIXELS_WORDS),
        (("pixels", "fraction", "jpeg"), PIXELS_WORDS),
        (("fraction",), FRACTION_WORDS),
        (("jpeg",), JPEG_WORDS),
    ],
    ids=[
        "pixels-and-fraction",
        "fraction-and-jpeg",
        "pixels-and-jpeg",
        "all-three",
        "fraction-alone",
        "jpeg-alone",
    ],
)
def test_the_expected_values_are_compared_pixels_then_fraction_then_jpeg(tmp_path, wrong, named):
    """Each adjacent pair wrong together is refused as the first of the two, by its own words."""
    root, lock = raw_inputs(tmp_path / "raw")
    config = _recorded(lock)
    colour = config["areas"]["fixture"]["colour"]
    if "pixels" in wrong:
        colour["expected_pixels_sha256"] = "ab" * 32
    if "fraction" in wrong:
        colour["expected_filled_fraction"] = 0.25
    if "jpeg" in wrong:
        colour["expected_sha256"] = "cd" * 32
    with pytest.raises(FarColourError) as refusal:
        build_farcolour(_world(), fixture_datasets(), lock, config, root, tmp_path / "out")
    text = str(refusal.value)
    assert named in text and "nothing was written" in text, text
    for other in {PIXELS_WORDS, FRACTION_WORDS, JPEG_WORDS} - {named}:
        assert other not in text, text
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("seam", ["_far_bytes", "regio_tile_bytes"])
def test_each_file_is_decoded_from_the_bytes_that_were_hashed_not_read_again(
    tmp_path, monkeypatch, seam
):
    """The file is replaced by a text that is no tile and no zip right after it is read: only a
    step that decodes the very bytes it hashed still builds design's colour."""
    root, lock = raw_inputs(tmp_path / "raw")
    real = getattr(farcolour, seam)

    def read_then_change(path, tile):
        data = real(path, tile)
        path.write_bytes(b"the file changed after it was read")
        return data

    monkeypatch.setattr(farcolour, seam, read_then_change)
    block = build_farcolour(
        _world(), fixture_datasets(), lock, _recorded(lock), root, tmp_path / "out"
    )
    assert block["colour_sha256"] == _config()["areas"]["fixture"]["colour"]["expected_sha256"]


@pytest.mark.parametrize("shift", [(1, 0), (0, 1)], ids=["one-metre-east", "one-metre-north"])
def test_a_sample_that_is_not_on_a_pixel_centre_is_no_pixel_s_sample(tmp_path, monkeypatch, shift):
    """The shared parser refuses such a point, so the step never sees one; with the parser made to
    return every point a metre off, no pixel has a sample, whatever the parser checked."""
    real = farcolour.regio_tile_samples

    def shifted(data, tile, path, resolution):
        x, y, centimetres = real(data, tile, path, resolution)
        return x + shift[0], y + shift[1], centimetres

    monkeypatch.setattr(farcolour, "regio_tile_samples", shifted)
    root, lock = raw_inputs(tmp_path / "raw")
    with pytest.raises(FarColourError) as refusal:
        build_farcolour(_world(), fixture_datasets(), lock, _recorded(lock), root, tmp_path / "out")
    text = str(refusal.value)
    assert "has no swissALTIRegio sample (900 such pixels)" in text, text
    assert not (tmp_path / "out").exists()


def test_the_description_is_written_sorted_indented_and_in_utf_8():
    """The description's own keys are already in order, so the step cannot tell sorting from
    its absence: the helper is tried on keys that are not."""
    data = {"b": 1, "a": {"d": [1, 2], "c": "© swisstopo"}}
    text = '{\n  "a": {\n    "c": "© swisstopo",\n    "d": [\n      1,\n      2\n    ]\n  },\n  "b": 1\n}\n'
    assert farcolour._json_bytes(data) == text.encode("utf-8")


@pytest.mark.parametrize("datasets", [None, [], "swissimage_far", 3], ids=repr)
def test_a_datasets_config_that_is_no_object_is_refused_by_the_far_reader_itself(datasets):
    """`_checked` reads swissALTIRegio's entry first, which refuses such a config in its own words;
    the far reader takes any object and must refuse it as it does a config without the dataset."""
    with pytest.raises(FarColourError) as refusal:
        farcolour._far_config(datasets, FarColourError)
    text = str(refusal.value)
    assert "config/datasets.json has no 'swissimage_far' dataset" in text, text


def test_a_built_block_whose_jpeg_is_not_the_one_the_config_expects_is_refused(tmp_path):
    """The description and the JPEG agree; only the config's expected SHA-256 is another."""
    out, _, lock = _built(tmp_path)
    config = _config()
    config["areas"]["fixture"]["colour"]["expected_sha256"] = "ab" * 32
    with pytest.raises(FarColourError) as refusal:
        built_farcolour_block(out, config, _world(), _world_sha256(), fixture_datasets(), lock)
    text = str(refusal.value)
    assert "colour_sha256" in text and "ab" * 32 in text and STEP_COMMAND in text, text


@pytest.mark.parametrize("key", ["band_m", "cell_m", "expected_columns", "expected_rows"])
@pytest.mark.parametrize("value", [True, False, 2.0, "2", None], ids=repr)
def test_no_colour_setting_is_a_whole_number_when_it_is_a_bool_a_float_a_text_or_null(key, value):
    config = _config()
    config["areas"]["fixture"]["colour"][key] = value
    with pytest.raises(SurroundingsError) as refusal:
        check_surroundings_config(config)
    assert f"colour {key} must be" in str(refusal.value), str(refusal.value)


@pytest.mark.parametrize(
    "value, valid",
    [
        (0.0, True),
        (0.5, True),
        (1.0, True),
        (-1e-9, False),
        (1.0 + 2**-52, False),
        (0, False),
        (1, False),
        (True, False),
        (float("nan"), False),
        (float("inf"), False),
        ("0.5", False),
        (None, False),
    ],
    ids=repr,
)
def test_the_expected_filled_fraction_is_a_float_from_0_to_1_both_ends_included(value, valid):
    config = _config()
    config["areas"]["fixture"]["colour"]["expected_filled_fraction"] = value
    if valid:
        check_surroundings_config(config)
        return
    with pytest.raises(SurroundingsError) as refusal:
        check_surroundings_config(config)
    assert str(refusal.value) == (
        "the surroundings config: area 'fixture': colour expected_filled_fraction must be a "
        f"float from 0 to 1, found {value!r}"
    )


@pytest.mark.parametrize("key", ["expected_pixels_sha256", "expected_sha256"])
@pytest.mark.parametrize("value", [None, 3, ["a" * 64], "A" * 64, "a" * 63, "a" * 65], ids=repr)
def test_a_colour_hash_that_is_not_64_lower_case_hex_text_is_refused_by_the_reader(key, value):
    """A number, null or list is refused in the same words as text of the wrong shape."""
    config = _config()
    config["areas"]["fixture"]["colour"][key] = value
    with pytest.raises(SurroundingsError) as refusal:
        check_surroundings_config(config)
    assert str(refusal.value) == (
        f"the surroundings config: area 'fixture': colour {key} must be a SHA-256 in 64 "
        f"lower-case hex characters, found {value!r}"
    )


def test_a_colour_block_s_computed_for_is_refused_as_the_colour_s_not_the_area_s():
    config = _config()
    config["areas"]["fixture"]["colour"]["computed_for"] = {}
    with pytest.raises(SurroundingsError) as refusal:
        check_surroundings_config(config)
    assert str(refusal.value) == (
        "the surroundings config: colour: area 'fixture': computed_for must have exactly the "
        "keys ['inputs_sha256', 'world_sha256']"
    )


@pytest.mark.parametrize("change", ["a-key-missing", "a-key-more", "not-an-object"])
def test_a_colour_block_that_is_not_exactly_the_eight_keys_is_refused_naming_them(change):
    config = _config()
    area = config["areas"]["fixture"]
    if change == "a-key-missing":
        del area["colour"]["band_m"]
    elif change == "a-key-more":
        area["colour"]["extra"] = 1
    else:
        area["colour"] = []
    with pytest.raises(SurroundingsError) as refusal:
        check_surroundings_config(config)
    keys = (
        "['band_m', 'cell_m', 'computed_for', 'expected_columns', 'expected_filled_fraction', "
        "'expected_pixels_sha256', 'expected_rows', 'expected_sha256']"
    )
    assert str(refusal.value) == (
        f"the surroundings config: area 'fixture': colour must have exactly the keys {keys}"
    )


def _far_path(root, tile="2615-1095"):
    return root / "swissimage_far" / "2023" / far_name(tile, "2023", 20)


def _regio_path(root, tile="2615-1094"):
    return root / "swissaltiregio" / "2026-06" / zip_name(tile)


def _fails(tmp_path, *, config=None, lock=None, root=None, world=None, datasets=None, **kwargs):
    """The step's refusal text for the fixture, its inputs made as given: (text, progress lines)."""
    if root is None:
        root, made = raw_inputs(tmp_path / "raw")
        lock = lock or made
    lines = []
    with pytest.raises(FarColourError) as refusal:
        build_farcolour(
            world or _world(),
            datasets or fixture_datasets(),
            lock,
            config or _recorded(lock),
            root,
            tmp_path / "out",
            progress=lines.append,
            **kwargs,
        )
    assert not (tmp_path / "out").exists()
    return str(refusal.value), lines


def test_a_tile_without_a_coordinate_system_is_refused_naming_it(tmp_path):
    """The GeoKeyDirectory (tag 34735) is the last entry of the IFD: renamed to a private tag, the
    file keeps its tie point and pixel size but no CRS."""
    source = fixture_source()
    pixels = tile_pixels(fixture_photo(source), source, "2615-1095")
    body = bytearray(geotiff(pixels, 2_615_000.0, 1_096_000.0, 20))
    (count,) = struct.unpack_from("<H", body, 8)
    renamed = 0
    for entry in range(count):
        if struct.unpack_from("<H", body, 10 + 12 * entry)[0] == 34735:
            struct.pack_into("<H", body, 10 + 12 * entry, 65000)
            renamed += 1
    assert renamed == 1
    root, lock = raw_inputs(tmp_path / "raw", bodies={"2615-1095": bytes(body)})
    text, _ = _fails(tmp_path, root=root, lock=lock, config=_recorded(lock))
    path = _far_path(root)
    assert text == (
        f"tile 2615-1095: {path}: its CRS is None, expected EPSG:2056; `{DOWNLOAD_FAR}` "
        f"fetches it again"
    ), text


def test_with_several_pixels_without_a_sample_the_first_in_reading_order_is_named(tmp_path):
    source = fixture_source()
    tile = source["regio"]["tiles"]["2615-1094"]
    gone = (
        f"{2_615_050 + 100 * 17} {1_096_950 - 100 * 3} ",
        f"{2_615_050 + 100 * 6} {1_096_950 - 100 * 22} ",
    )
    kept = [line for line in tile["text"].split("\r\n") if not line.startswith(gone)]
    assert len(kept) == len(tile["text"].split("\r\n")) - 2
    tile["text"] = "\r\n".join(kept)
    root, lock = raw_inputs(tmp_path / "raw", source=source)
    text, _ = _fails(tmp_path, root=root, lock=lock)
    assert text.startswith("pixel (row 3, column 17) at LV95 (2616750, 1096650) has no "), text
    assert "(2 such pixels)" in text and "row 22" not in text, text


def test_a_cell_that_does_not_divide_the_km_is_refused_naming_it(tmp_path):
    """2000 m divides every corner of this 6 km box but not the 1000 m tile: only that clause."""
    area = {"e_max": 2_618_000.0, "e_min": 2_616_000.0, "n_max": 1_096_000.0, "n_min": 1_094_000.0}
    world, _ = _fixture_world_at(tmp_path / "world.json", areas={"fixture": area})
    config, datasets = _config(), fixture_datasets()
    config["areas"]["fixture"]["margin_m"] = 2000
    config["areas"]["fixture"]["colour"]["cell_m"] = 2000
    datasets["swissaltiregio"]["resolution_m"] = 2000
    datasets["swissimage_far"]["resolution_m"] = 400
    text, _ = _fails(
        tmp_path, root=tmp_path / "raw", lock=_lock(), config=config, datasets=datasets, world=world
    )
    assert "colour cell_m 2000 must be" in text, text
    assert "[2614000, 2620000, 1092000, 1098000] and 1000:" in text, text


# ------------------------------------------------------------------- no claim before its check


def _expected_values_changed(config, **colour):
    config["areas"]["fixture"]["colour"].update(colour)
    return config


@pytest.mark.parametrize(
    "case, colour, last, never",
    [
        (
            "pixels",
            {"expected_pixels_sha256": "ab" * 32},
            "filling the 300 pixels without a photo by their altitude",
            ("the pixels have the SHA-256", "encoding the JPEG", "the JPEG has", "wrote "),
        ),
        (
            "fraction",
            {"expected_filled_fraction": 0.25},
            "the pixels have the SHA-256 config/surroundings.json expects, ",
            ("encoding the JPEG", "the JPEG has", "wrote "),
        ),
        (
            "jpeg",
            {"expected_sha256": "cd" * 32},
            "encoding the JPEG",
            ("the JPEG has", "wrote "),
        ),
    ],
)
def test_a_refused_comparison_leaves_the_progress_before_the_claim_that_it_held(
    tmp_path, case, colour, last, never
):
    root, lock = raw_inputs(tmp_path / "raw")
    config = _expected_values_changed(_recorded(lock), **colour)
    _, lines = _fails(tmp_path, root=root, lock=lock, config=config)
    assert lines[-1].startswith(last), lines
    for claim in never:
        assert not any(line.startswith(claim) for line in lines), (claim, lines)


def test_a_write_that_fails_leaves_the_progress_before_the_line_that_says_it_wrote(
    tmp_path, monkeypatch
):
    def cannot_write(*args):
        raise FarColourError("the disk is full")

    monkeypatch.setattr(farcolour, "_write_files", cannot_write)
    _, lines = _fails(tmp_path)
    assert lines[-1].startswith("the JPEG has the SHA-256 config/surroundings.json expects, ")
    assert not any(line.startswith("wrote ") for line in lines), lines


@pytest.mark.parametrize(
    "seam, last",
    [
        ("_fill", "filling the 300 pixels without a photo by their altitude"),
        ("encode_jpeg", "encoding the JPEG"),
    ],
)
def test_the_step_says_what_it_is_about_to_do_before_it_does_it(tmp_path, monkeypatch, seam, last):
    """A fill or an encoding that stops still leaves its own line as the last one."""

    def stops(*args, **kwargs):
        raise FarColourError("stopped here")

    monkeypatch.setattr(farcolour, seam, stops)
    text, lines = _fails(tmp_path)
    assert text == "stopped here" and lines[-1] == last, lines


@pytest.mark.parametrize("which", ["far", "regio"])
def test_the_file_being_read_is_named_before_it_is_read(tmp_path, which):
    """A file that cannot be read still leaves its own name as the last progress line."""
    root, lock = raw_inputs(tmp_path / "raw")
    path = _far_path(root, "2615-1094") if which == "far" else _regio_path(root, "2605-1084")
    path.unlink()
    path.mkdir()
    text, lines = _fails(tmp_path, root=root, lock=lock)
    assert lines[-1] == f"reading {path}", lines
    assert str(path) in text and "cannot read" in text, text


@pytest.mark.parametrize("which", ["far", "regio"])
def test_a_file_of_other_bytes_is_refused_by_its_checksum_before_it_is_decoded(tmp_path, which):
    """Bytes that are no GeoTIFF and no zip: the lock's SHA-256 is the first thing they fail."""
    root, lock = raw_inputs(tmp_path / "raw")
    path = _far_path(root) if which == "far" else _regio_path(root)
    garbage = b"neither a tile nor a zip"
    path.write_bytes(garbage)
    text, _ = _fails(tmp_path, root=root, lock=lock)
    sha = _sha(garbage)
    if which == "far":
        pinned = lock["datasets"]["swissimage_far"]["tiles"]["2615-1095"]["sha256"]
        assert text == (
            f"tile 2615-1095: {path}: it has SHA-256 {sha}, provenance.json and the lock pin "
            f"{pinned}; `{DOWNLOAD_FAR}` fetches it again"
        ), text
    else:
        pinned = lock["datasets"]["swissaltiregio"]["tiles"]["2615-1094"]["sha256"]
        assert text == (
            f"tile 2615-1094: {path} has SHA-256 {sha}, provenance.json and the lock pin "
            f"{pinned}; `{DOWNLOAD_REGIO}` fetches it again"
        ), text


# ------------------------------------------------------------------- the order of the checks


def _two_areas(config):
    config["areas"]["other"] = copy.deepcopy(config["areas"]["fixture"])
    return config


@pytest.mark.parametrize("areas", [0, 2], ids=["no-area", "two-areas"])
def test_a_config_without_exactly_one_area_is_a_far_colour_error_before_its_area_is_read(
    tmp_path, areas
):
    config = _config()
    config = _two_areas(config) if areas == 2 else {**config, "areas": {}}
    expected = "areas must hold exactly one area, found "
    with pytest.raises(FarColourError) as refusal:
        build_farcolour(
            _world(), fixture_datasets(), _lock(), config, tmp_path / "raw", tmp_path / "out"
        )
    assert expected in str(refusal.value), str(refusal.value)
    with pytest.raises(FarColourError) as refusal:
        built_farcolour_block(
            tmp_path, config, _world(), _world_sha256(), fixture_datasets(), _lock()
        )
    assert expected in str(refusal.value), str(refusal.value)


def test_the_colour_block_is_asked_for_before_the_axes_and_the_axes_before_the_area(tmp_path):
    """The brief's order (decision 6): a world with other axes and an area the config does not
    name, beside a config without a colour block, is refused as the config's first."""
    area = json.loads((FIXTURE / "world.json").read_text(encoding="utf-8"))["areas"]["fixture"]
    axes = {"x": "-e", "y": "+h", "z": "+n"}
    world, _ = _fixture_world_at(tmp_path / "world.json", areas={"other": area}, axes=axes)
    config = _config()
    del config["areas"]["fixture"]["colour"]
    text, _ = _fails(tmp_path, root=tmp_path / "raw", lock=_lock(), config=config, world=world)
    assert "holds no colour block" in text and str(world.path) not in text, text
    text, _ = _fails(tmp_path, root=tmp_path / "raw", lock=_lock(), world=world, config=_config())
    assert text == (
        f"{world.path}: the far colour supports only the axes x = +e, y = +h, z = -n"
    ), text


def test_the_area_on_the_lattice_is_checked_before_the_datasets_config(tmp_path):
    """Decision 6's order: the area and the box on the lattice, then the cell and the datasets."""
    area = {"e_max": 2_617_000.0, "e_min": 2_616_010.0, "n_max": 1_096_000.0, "n_min": 1_095_000.0}
    world, _ = _fixture_world_at(tmp_path / "world.json", areas={"fixture": area})
    datasets = fixture_datasets()
    del datasets["swissimage_far"]
    text, _ = _fails(
        tmp_path,
        root=tmp_path / "raw",
        lock=_lock(),
        config=_config(),
        datasets=datasets,
        world=world,
    )
    assert "e_min 2616010.0 is not a multiple of the 500 m spacing" in text, text


def test_an_area_the_world_config_does_not_hold_is_named_in_those_words(tmp_path):
    area = json.loads((FIXTURE / "world.json").read_text(encoding="utf-8"))["areas"]["fixture"]
    world, _ = _fixture_world_at(tmp_path / "world.json", areas={"other": area})
    text, _ = _fails(tmp_path, root=tmp_path / "raw", lock=_lock(), world=world, config=_config())
    assert text == (f"{world.path}: no area named 'fixture' for the surroundings config's area"), (
        text
    )


def test_a_far_provenance_that_lists_a_tile_the_lock_does_not_pin_is_refused_as_another_list(
    tmp_path,
):
    root, lock = raw_inputs(tmp_path / "raw")
    unknown = {"file": "x.tif", "sha256": "0" * 64, "tile": "9999-9999"}
    _edit_far_provenance(root, lambda p: p["tiles"].insert(0, unknown))
    text, _ = _fails(tmp_path, root=root, lock=lock)
    listed, pinned = text.split("the lock pins")
    assert "'9999-9999'" in listed and "'9999-9999'" not in pinned, text


# ------------------------------------------------------------------- every value in its role
#
# The pinned tests ask that a refusal names the values; these ask that it names each in the role
# it has: what was built and what was expected, what the download lists and what the lock pins.
# A refusal with the right words and the values swapped tells the owner the wrong thing.


def _colour_value(name):
    return _config()["areas"]["fixture"]["colour"][name]


def test_the_pixels_refusal_says_which_value_was_built_and_which_expected(tmp_path):
    root, lock = raw_inputs(tmp_path / "raw")
    config = _expected_values_changed(_recorded(lock), expected_pixels_sha256="ab" * 32)
    text, _ = _fails(tmp_path, root=root, lock=lock, config=config)
    decoder = f"rasterio {rasterio.__version__}, GDAL {rasterio.__gdal_version__}"
    assert farcolour._decoder() == decoder
    assert text == (
        f"area 'fixture': the colour pixels built here have SHA-256 "
        f"{_colour_value('expected_pixels_sha256')}, config/surroundings.json expects "
        f"{'ab' * 32}. Design computed the expected value two ways that share no code, so this "
        f"machine or this code computes other pixels than design's; the 2 m tiles are JPEG "
        f"inside the GeoTIFF, decoded here by {decoder}; nothing was written"
    ), text


def test_the_fraction_refusal_says_which_value_was_built_and_which_expected(tmp_path):
    root, lock = raw_inputs(tmp_path / "raw")
    config = _expected_values_changed(_recorded(lock), expected_filled_fraction=0.25)
    text, _ = _fails(tmp_path, root=root, lock=lock, config=config)
    assert text == (
        "area 'fixture': the filled fraction built here is 0.3333333333333333 (300 of 900 "
        "pixels), config/surroundings.json expects 0.25; nothing was written"
    ), text


def test_the_jpeg_refusal_says_which_value_was_built_and_which_expected(tmp_path):
    root, lock = raw_inputs(tmp_path / "raw")
    config = _expected_values_changed(_recorded(lock), expected_sha256="ef" * 32)
    text, _ = _fails(tmp_path, root=root, lock=lock, config=config)
    assert text == (
        f"area 'fixture': the pixels are design's; this machine's JPEG encoder writes other "
        f"bytes: {jpeg_encoder()}. The JPEG built here has SHA-256 "
        f"{_colour_value('expected_sha256')}, config/surroundings.json expects {'ef' * 32}; "
        f"nothing was written"
    ), text


def test_the_cell_refusal_says_each_resolution_and_the_box(tmp_path):
    config = _config()
    config["areas"]["fixture"]["colour"]["cell_m"] = 50
    text, _ = _fails(tmp_path, root=tmp_path / "raw", lock=_lock(), config=config)
    assert text == (
        "config/surroundings.json: area 'fixture': colour cell_m 50 must be swissaltiregio's "
        "resolution_m (100) and 5 times swissimage_far's resolution_m (20), and divide the box's "
        "corners [2615000, 2618000, 1094000, 1097000] and 1000: the samples lie on the pixel "
        "centres and a pixel is 5 × 5 source pixels"
    ), text


@pytest.mark.parametrize(
    "key, name, found", [("expected_columns", "columns", 31), ("expected_rows", "rows", 29)]
)
def test_the_box_refusal_says_the_count_it_built_and_the_count_design_has(
    tmp_path, key, name, found
):
    config = _config()
    config["areas"]["fixture"]["colour"][key] = found
    text, _ = _fails(tmp_path, root=tmp_path / "raw", lock=_lock(), config=config)
    assert text == (
        f"area 'fixture': the world config's area grown by the margin gives 30 {name} of the "
        f"colour at 100 m, config/surroundings.json's colour {key} is {found}. A changed area, "
        f"margin or cell is a design change: design recomputes the expected values "
        f"(docs/SPEC.md §8)"
    ), text


def test_the_inputs_refusal_says_the_recorded_and_the_current_entries(tmp_path):
    root, lock = raw_inputs(tmp_path / "raw")
    config = _recorded(lock)
    current = config["areas"]["fixture"]["colour"]["computed_for"]["inputs_sha256"]
    config["areas"]["fixture"]["colour"]["computed_for"]["inputs_sha256"] = "ab" * 32
    text, _ = _fails(tmp_path, root=root, lock=lock, config=config)
    assert text == (
        f"area 'fixture': the expected values in config/surroundings.json's colour were computed "
        f"from the swissaltiregio and swissimage_far lock entries with SHA-256 {'ab' * 32}; "
        f"config/datasets.lock.json's entries now have {current} (a new edition or an adopted "
        f"republished file). Adopting new inputs is a design change: design recomputes the "
        f"expected values (docs/SPEC.md §5, §8)"
    ), text


def test_a_world_that_is_not_design_s_is_refused_naming_the_area_first(tmp_path):
    config = _config()
    config["areas"]["fixture"]["colour"]["computed_for"]["world_sha256"] = "ab" * 32
    text, _ = _fails(tmp_path, root=tmp_path / "raw", lock=_lock(), config=config)
    assert text.startswith(
        "area 'fixture': the expected values in config/surroundings.json were computed for the "
        f"world config with SHA-256 {'ab' * 32}; "
    ), text
    assert _world_sha256() in text, text


def test_a_config_without_a_colour_block_says_its_file_then_its_area(tmp_path):
    config = _config()
    del config["areas"]["fixture"]["colour"]
    text, _ = _fails(tmp_path, root=tmp_path / "raw", lock=_lock(), config=config)
    assert text.startswith("config/surroundings.json: area 'fixture' holds no colour block"), text


@pytest.mark.parametrize(
    "case, edit, words",
    [
        (
            "text-missing",
            lambda d: d["swissimage_far"].pop("attribution"),
            "config/datasets.json: swissimage_far attribution must be a text, found None",
        ),
        (
            "resolution-a-float",
            lambda d: d["swissimage_far"].update(resolution_m=20.0),
            (
                "config/datasets.json: swissimage_far resolution_m must be a whole number of "
                "metres, found 20.0"
            ),
        ),
    ],
)
def test_the_far_dataset_refusals_say_the_file_the_dataset_the_key_and_what_was_found(
    tmp_path, case, edit, words
):
    datasets = fixture_datasets()
    edit(datasets)
    text, _ = _fails(
        tmp_path, root=tmp_path / "raw", lock=_lock(), config=_config(), datasets=datasets
    )
    assert text == words, text


@pytest.mark.parametrize(
    "case, edit, words",
    [
        (
            "collection",
            lambda p: p.update(collection="ch.swisstopo.swissimage-dop10-2"),
            lambda lock: (
                "it lists collection 'ch.swisstopo.swissimage-dop10-2', the config asks "
                f"for {fixture_datasets()['swissimage_far']['collection']!r}"
            ),
        ),
        (
            "resolution",
            lambda p: p.update(resolution_m=2),
            lambda lock: "it lists resolution_m 2, the config asks for 20",
        ),
        (
            "absent",
            lambda p: p.update(absent=["2617-1094"]),
            lambda lock: (
                "it lists the absent cells ['2617-1094'], the lock records "
                f"{lock['datasets']['swissimage_far']['absent']!r}"
            ),
        ),
        (
            "a-tile",
            lambda p: p["tiles"][1].update(file="other.tif", sha256="1" * 64),
            lambda lock: (
                "tile 2615-1095: it lists 'other.tif' with SHA-256 '" + "1" * 64 + "', the "
                "lock pins "
                f"{lock['datasets']['swissimage_far']['tiles']['2615-1095']['file']!r} with SHA-256 "
                f"{lock['datasets']['swissimage_far']['tiles']['2615-1095']['sha256']!r}"
            ),
        ),
    ],
)
def test_the_far_provenance_refusals_say_what_it_lists_and_what_the_config_or_lock_has(
    tmp_path, case, edit, words
):
    root, lock = raw_inputs(tmp_path / "raw")
    _edit_far_provenance(root, edit)
    text, _ = _fails(tmp_path, root=root, lock=lock)
    path = root / "swissimage_far" / "2023" / "provenance.json"
    assert text == f"{path}: {words(lock)}; `{DOWNLOAD_FAR}` downloads what it asks for", text


def _with_pixel_scale(body, x_m, y_m):
    """The GeoTIFF's ModelPixelScale (tag 33550) rewritten: pixels `x_m` wide and `y_m` high."""
    data = bytearray(body)
    (count,) = struct.unpack_from("<H", data, 8)
    for entry in range(count):
        tag, _, _, offset = struct.unpack_from("<HHII", data, 10 + 12 * entry)
        if tag == 33550:
            struct.pack_into("<dd", data, offset, float(x_m), float(y_m))
            return bytes(data)
    raise AssertionError("no ModelPixelScale in the tile")


def _odd_tile(case):
    """(the tile's bytes, what the refusal says is wrong with it) for tile 2615-1095."""
    source = fixture_source()
    pixels = tile_pixels(fixture_photo(source), source, "2615-1095")
    west, north = 2_615_000.0, 1_096_000.0
    return {
        "non-square-pixels": (
            _with_pixel_scale(geotiff(pixels, west, north, 20), 20, 10),
            (
                "its top-left corner is (2615000.0, 1096000.0) with 20.0 × 10.0 m pixels, its "
                "id says (2615000, 1096000) with 20 m pixels"
            ),
        ),
        "another-crs": (
            geotiff(pixels, west, north, 20, epsg=21781),
            "its CRS is EPSG:21781, expected EPSG:2056",
        ),
        "16-bit": (
            geotiff(pixels, west, north, 20, dtype_bits=16),
            "its pixels are ['uint16', 'uint16', 'uint16'], expected uint8",
        ),
        "shifted-east": (
            geotiff(pixels, west + 20, north, 20),
            (
                "its top-left corner is (2615020.0, 1096000.0) with 20.0 × 20.0 m pixels, its "
                "id says (2615000, 1096000) with 20 m pixels"
            ),
        ),
        "shifted-north": (
            geotiff(pixels, west, north + 20, 20),
            (
                "its top-left corner is (2615000.0, 1096020.0) with 20.0 × 20.0 m pixels, its "
                "id says (2615000, 1096000) with 20 m pixels"
            ),
        ),
        "other-pixel-size": (
            geotiff(pixels.repeat(2, 0).repeat(2, 1), west, north, 10),
            "it is 100 × 100 pixels in 3 bands, expected 50 × 50 in 3",
        ),
    }[case]


@pytest.mark.parametrize(
    "case",
    [
        "another-crs",
        "16-bit",
        "shifted-east",
        "shifted-north",
        "non-square-pixels",
        "other-pixel-size",
    ],
)
def test_a_tile_refusal_says_its_tile_then_its_file_then_what_is_wrong(tmp_path, case):
    body, wrong = _odd_tile(case)
    root, lock = raw_inputs(tmp_path / "raw", bodies={"2615-1095": body})
    text, _ = _fails(tmp_path, root=root, lock=lock)
    assert text == (
        f"tile 2615-1095: {_far_path(root)}: {wrong}; `{DOWNLOAD_FAR}` fetches it again"
    ), text


def test_a_tile_that_is_no_geotiff_and_a_tile_that_cannot_be_read_say_so_in_their_places(tmp_path):
    root, lock = raw_inputs(tmp_path / "raw", bodies={"2615-1095": b"not a GeoTIFF"})
    text, _ = _fails(tmp_path, root=root, lock=lock)
    path = _far_path(root)
    prefix, suffix = (
        f"tile 2615-1095: {path}: cannot read it as a GeoTIFF: ",
        f"; `{DOWNLOAD_FAR}` fetches it again",
    )
    assert text.startswith(prefix) and text.endswith(suffix), text
    root, lock = raw_inputs(tmp_path / "second")
    path = _far_path(root, "2615-1094")
    path.unlink()
    path.mkdir()
    text, _ = _fails(tmp_path / "second", root=root, lock=lock)
    prefix = f"tile 2615-1094: {path}: cannot read it: "
    assert text.startswith(prefix) and text.endswith(suffix), text


def _block_refusal(tmp_path, edit):
    out, _, lock = _built(tmp_path)
    path = out / "surroundings" / "fixture_colour.json"
    block = json.loads(path.read_text(encoding="utf-8"))
    edit(block, out)
    path.write_text(json.dumps(block, indent=2), encoding="utf-8")
    with pytest.raises(FarColourError) as refusal:
        built_farcolour_block(out, _config(), _world(), _world_sha256(), fixture_datasets(), lock)
    return str(refusal.value), path, out


def _flip_the_jpeg(block, out):
    _flip_last_byte(out / "surroundings" / "fixture_colour.jpg")


def _another_import(block, out):
    (out / "surroundings" / "fixture_colour.jpg.import").write_bytes(b"x")


@pytest.mark.parametrize(
    "case, edit, words",
    [
        (
            "format",
            lambda b, out: b.update(colour_format="png"),
            lambda out: "colour_format is 'png', expected 'jpeg'",
        ),
        (
            "cell",
            lambda b, out: b.update(colour_cell_m=50.0),
            lambda out: "it was built at 50.0 m, the config asks for 100 m",
        ),
        (
            "rows",
            lambda b, out: b.update(colour_rows=31),
            lambda out: "colour_rows is 31, the world config's area 'fixture' needs 30",
        ),
        (
            "columns",
            lambda b, out: b.update(colour_columns=29),
            lambda out: "colour_columns is 29, the world config's area 'fixture' needs 30",
        ),
        (
            "fraction",
            lambda b, out: b.update(filled_fraction=0.5),
            lambda out: (
                "filled_fraction is 0.5, config/surroundings.json expects 0.3333333333333333"
            ),
        ),
        (
            "source",
            lambda b, out: b["colour_source"].update(attribution="© nobody"),
            lambda out: (
                "its source's attribution is '© nobody', expected "
                f"{fixture_datasets()['swissimage_far']['attribution']!r}"
            ),
        ),
        (
            "jpeg",
            _flip_the_jpeg,
            lambda out: (
                f"{out / 'surroundings' / 'fixture_colour.jpg'} has SHA-256 "
                f"{_sha((out / 'surroundings' / 'fixture_colour.jpg').read_bytes())}, the description "
                f"pins {_colour_value('expected_sha256')}"
            ),
        ),
        (
            "import",
            _another_import,
            lambda out: (
                f"{out / 'surroundings' / 'fixture_colour.jpg'}.import is b'x', Godot "
                f"must keep the JPEG as it is: {KEEP_IMPORT!r}"
            ),
        ),
    ],
)
def test_the_built_block_refusals_say_what_was_found_and_what_is_expected(
    tmp_path, case, edit, words
):
    text, path, out = _block_refusal(tmp_path, edit)
    assert text == f"{path}: {words(out)}; `{STEP_COMMAND}` rebuilds the far colour", text
