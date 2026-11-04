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

Does NOT prove: the village's values (the step's own comparison at the brief's real run and the
release gate); that these are the only gaps (the mutation prover looks for more).
"""

import copy
import hashlib
import io
import json
from decimal import Decimal

import numpy as np
import pytest
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
from mattini.photo import encode_jpeg
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


def test_a_grid_without_a_covered_pixel_is_refused(tmp_path):
    source = fixture_source()
    source["absent"] = fixture_cells(source)
    root, lock = raw_inputs(tmp_path / "raw", source=source)
    assert lock["datasets"]["swissimage_far"]["tiles"] == {}
    with pytest.raises(FarColourError) as refusal:
        build_farcolour(_world(), fixture_datasets(), lock, _recorded(lock), root, tmp_path / "out")
    assert "no pixel is covered" in str(refusal.value), str(refusal.value)
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
def test_a_far_lock_entry_that_is_not_exactly_formed_is_refused_naming_lock_farphoto(
    tmp_path, case
):
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
    assert LOCK_FAR in text and "python -m mattini lock regio" not in text, text
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
        ("a-pin-no-object", lambda e, lock: e["tiles"].update({"2615-1094": "abc"}), ["2615-1094"]),
        (
            "a-pin-file-unsafe",
            lambda e, lock: e["tiles"]["2615-1094"].update(file="../x.tif"),
            ["2615-1094"],
        ),
        (
            "a-pin-sha256-short",
            lambda e, lock: e["tiles"]["2615-1094"].update(sha256="ab"),
            ["2615-1094"],
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
