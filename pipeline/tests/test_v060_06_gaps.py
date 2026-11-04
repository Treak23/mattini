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

Does NOT prove: the village's values (the step's own comparison at the brief's real run and the
release gate); that these are the only gaps (the mutation prover looks for more).
"""

import copy
import hashlib
import json

import numpy as np
import pytest
from synthetic_farphoto import (
    FIXTURE,
    fixture_cells,
    fixture_datasets,
    fixture_photo,
    fixture_source,
    geotiff,
    raw_inputs,
    tile_pixels,
)

from mattini import farcolour
from mattini.farcolour import FarColourError, build_farcolour, built_farcolour_block
from mattini.surroundings import load_surroundings_config
from mattini.world import load_world

LOCK_FAR = "python -m mattini lock farphoto"
DOWNLOAD_REGIO = "python -m mattini download regio"
DOWNLOAD_FAR = "python -m mattini download farphoto"


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
