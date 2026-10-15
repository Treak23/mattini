"""The photo grid's rule at its edges, and the photo config's refusals (brief M3-04).

`photo_grid`: texel (r, c) is the k × k block of 0.1 m pixels, per channel the exact integer
sum / k² rounded half to even, k = 2, 5, 10. The sums below are chosen at the ties (a half
rounds to the even neighbour: 0.5 → 0, 1.5 → 2, 2.5 → 2, 3.5 → 4), one either side of
them, and at the extremes (a block of 255s, a block of 0s), in every channel at once with a
different sum in each, so round-half-up, floor, truncation, a mean taken in 8 bits and a
channel mixed with its neighbour all change a named case. A block is k rows and k columns
counted from the north-west corner: a box whose sides are not whole cells, off the 0.1 m
grid by more than 1e-6 m, empty or not finite is refused naming the box, as is a mosaic
that is not the box's size in 8-bit RGB. The function does not change its input.

`check_photo_config`: refusals beyond the pinned list name the file.

Does NOT prove: the placement of the grid in the world (the fixture and the four-tile
build do); the JPEG.
"""

import numpy as np
import pytest

from mattini.photo import PhotoError, check_photo_config, load_photo_config, photo_grid

CELL_BOXES = {0.2: (0.0, 0.2, 0.0, 0.2), 0.5: (0.0, 0.5, 0.0, 0.5), 1.0: (0.0, 1.0, 0.0, 1.0)}


def _block(k: int, sums: tuple[int, int, int]) -> np.ndarray:
    """A k × k block of pixels whose channel sums are `sums`, spread unevenly so that a
    block read row-wise or column-wise as a different shape would not give the same sum."""
    out = np.zeros((k, k, 3), dtype=np.uint8)
    for channel, total in enumerate(sums):
        flat = np.zeros(k * k, dtype=np.int64)
        for i in range(total):
            flat[i % (k * k)] += 1
        out[:, :, channel] = flat.reshape(k, k)
    assert [int(out[:, :, c].sum()) for c in range(3)] == list(sums)
    return out


# (cell, sums per channel) -> expected texel; ties go to even
CASES = [
    (0.2, (0, 1, 2), (0, 0, 0)),  # 0, 0.25, 0.5 -> 0 (a half goes down to the even 0)
    (0.2, (3, 4, 5), (1, 1, 1)),  # 0.75, 1, 1.25 -> 1
    (0.2, (6, 7, 10), (2, 2, 2)),  # 1.5 -> 2, 1.75, 2.5 -> 2
    (0.2, (14, 18, 1020), (4, 4, 255)),  # 3.5 -> 4, 4.5 -> 4, 255
    (0.5, (62, 63, 12), (2, 3, 0)),  # 2.48, 2.52, 0.48: no ties at k = 5
    (0.5, (12, 13, 6375), (0, 1, 255)),  # 0.48 -> 0, 0.52 -> 1
    (1.0, (49, 50, 51), (0, 0, 1)),  # 0.49, 0.5 -> 0, 0.51 -> 1
    (1.0, (150, 250, 350), (2, 2, 4)),  # 1.5 -> 2, 2.5 -> 2, 3.5 -> 4
    (1.0, (149, 151, 25500), (1, 2, 255)),
]


@pytest.mark.parametrize(("cell", "sums", "expected"), CASES)
def test_the_block_means_round_half_to_even(cell, sums, expected):
    k = round(cell / 0.1)
    mosaic = _block(k, sums)
    grid = photo_grid(mosaic, CELL_BOXES[cell], cell)
    assert grid.shape == (1, 1, 3) and grid.dtype == np.uint8
    assert grid[0, 0].tolist() == list(expected)


def test_a_texel_is_the_block_counted_from_the_north_west_corner():
    """A 2 × 3-texel box at 0.2 m: each texel takes its own 2 × 2 block, rows north to
    south, columns west to east."""
    sums = [[(1, 2, 3), (5, 6, 7), (9, 10, 11)], [(13, 14, 15), (17, 18, 19), (21, 22, 23)]]
    mosaic = np.zeros((4, 6, 3), dtype=np.uint8)
    for r in range(2):
        for c in range(3):
            mosaic[2 * r : 2 * r + 2, 2 * c : 2 * c + 2] = _block(2, sums[r][c])
    grid = photo_grid(mosaic, (0.0, 0.6, 0.0, 0.4), 0.2)
    for r in range(2):
        for c in range(3):
            wanted = [round(s / 4) for s in sums[r][c]]  # Python's round is half to even too
            assert grid[r, c].tolist() == wanted, (r, c)


def test_the_input_is_not_changed_and_may_be_read_only():
    mosaic = np.arange(2 * 4 * 3, dtype=np.uint8).reshape(2, 4, 3)
    mosaic.flags.writeable = False
    before = mosaic.tobytes()
    photo_grid(mosaic, (0.0, 0.4, 0.0, 0.2), 0.2)
    assert mosaic.tobytes() == before


@pytest.mark.parametrize(
    ("box", "cell", "shape", "message"),
    [
        ((0.0, 0.25, 0.0, 0.2), 0.2, (2, 2, 3), "e_max"),  # off the 0.1 m grid
        ((0.0, 0.2, 0.0000015, 0.2), 0.2, (2, 2, 3), "n_min"),  # 1.5 µm off
        ((0.0, 0.3, 0.0, 0.2), 0.2, (2, 3, 3), "whole number of 0.2 m cells"),
        ((0.0, 1.0, 0.0, 0.7), 1.0, (7, 10, 3), "whole number of 1 m cells"),
        ((0.0, 0.0, 0.0, 0.2), 0.2, (2, 0, 3), "empty"),
        ((0.2, 0.0, 0.0, 0.2), 0.2, (2, 0, 3), "empty"),
        ((0.0, 0.2, 0.0, float("nan")), 0.2, (2, 2, 3), "n_max"),
        ((0.0, 0.2, 0.0, float("inf")), 0.2, (2, 2, 3), "n_max"),
        ((0.0, 0.2, 0.0, 0.2), 0.25, (2, 2, 3), "cell_m"),
        ((0.0, 0.2, 0.0, 0.2), 0.1, (1, 1, 3), "cell_m"),
        ((0.0, 0.2, 0.0, 0.2), True, (2, 2, 3), "cell_m"),
        ((0.0, 0.4, 0.0, 0.2), 0.2, (2, 2, 3), "the box needs 4 × 2"),  # wrong mosaic size
        ((0.0, 0.2, 0.0, 0.2), 0.2, (2, 2, 4), "bands"),  # RGBA
    ],
)
def test_a_box_or_mosaic_that_does_not_fit_is_refused(box, cell, shape, message):
    mosaic = np.zeros(shape, dtype=np.uint8)
    with pytest.raises(PhotoError, match=message):
        photo_grid(mosaic, box, cell)


@pytest.mark.parametrize("bad", [np.zeros((2, 2, 3), dtype=np.float32), np.zeros((2, 2), np.uint8)])
def test_a_mosaic_that_is_not_8_bit_rgb_is_refused(bad):
    with pytest.raises(PhotoError, match="three-dimensional array of 8-bit"):
        photo_grid(bad, (0.0, 0.2, 0.0, 0.2), 0.2)


def test_a_box_off_the_grid_by_less_than_a_micrometre_is_the_grid():
    """Floats that stand for a decimetre (the world config is written in decimal) pass."""
    mosaic = np.zeros((2, 2, 3), dtype=np.uint8)
    assert photo_grid(mosaic, (0.0, 0.2 + 5e-7, 0.0, 0.2), 0.2).shape == (1, 1, 3)


VILLAGE = {
    "cell_m": 0.2,
    "computed_for": {"inputs_sha256": "a" * 64, "world_sha256": "b" * 64},
    "expected_pixels_sha256": {"0.2": "c" * 64},
    "expected_sha256": {"0.2": "d" * 64},
}


def _config(**change) -> dict:
    area = {**VILLAGE, **change}
    return {"schema": 1, "areas": {"village": area}}


def test_a_config_with_only_the_configured_cell_s_values_is_accepted():
    check_photo_config(_config())
    for cell in (1, 1.0):  # an integer 1 stands for 1.0
        check_photo_config(
            _config(
                cell_m=cell, expected_pixels_sha256={"1": "c" * 64}, expected_sha256={"1": "d" * 64}
            )
        )


@pytest.mark.parametrize(
    "config",
    [
        [],
        {"schema": 1},
        {"schema": 2, "areas": {"village": VILLAGE}},
        {"schema": True, "areas": {"village": VILLAGE}},
        {"schema": 1, "areas": {}},
        {"schema": 1, "areas": {"village": VILLAGE, "other": VILLAGE}},
        {"schema": 1, "areas": {"Village": VILLAGE}},
        {"schema": 1, "areas": {"village": []}},
        _config(cell_m="0.2"),
        _config(cell_m=True),
        _config(cell_m=None),
        _config(expected_sha256=[]),
        _config(expected_pixels_sha256={"0.2": 5}),
        _config(expected_pixels_sha256={"0.2": "c" * 63}),
        _config(expected_sha256={"1": "d" * 64}),
        _config(expected_pixels_sha256={"0.2": "c" * 64, "2": "c" * 64}),
        _config(computed_for={"inputs_sha256": "a" * 64}),
        _config(computed_for={"inputs_sha256": "a" * 64, "world_sha256": "B" * 64}),
    ],
    ids=lambda c: None,
)
def test_a_malformed_config_is_refused_naming_where(config):
    with pytest.raises(PhotoError, match="the photo config"):
        check_photo_config(config)


def test_a_config_file_that_cannot_be_read_or_parsed_names_it(tmp_path):
    missing = tmp_path / "missing.json"
    with pytest.raises(PhotoError, match=str(missing)):
        load_photo_config(missing)
    broken = tmp_path / "broken.json"
    broken.write_text("{", encoding="utf-8")
    with pytest.raises(PhotoError, match=str(broken)):
        load_photo_config(broken)
    binary = tmp_path / "binary.json"
    binary.write_bytes(b"\xff\xfe")
    with pytest.raises(PhotoError, match=str(binary)):
        load_photo_config(binary)
