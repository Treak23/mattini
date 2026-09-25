"""Pinning tests for brief M1-03: the resampling rule at every allowed spacing, and refusals.

Pinned decisions (docs/SPEC.md §8, the terrain grid): spacings 0.5, 1 and 2 m on 0.5 m
source pixels; a vertex at every spacing from the area's north-west corner, edges
included; its height is the area-weighted mean of the pixels under the spacing-wide
square centred on it, clipped to the area, minus height_offset_m, in 64-bit, rounded once
to 32-bit. The reference below computes that definition with exact fractions; resample
must match it bit for bit. Anything else is refused with TerrainError, never a plausible
grid: a non-finite height would become 0 m in Terrain3D (brain.md H11), invented ground.

"Rounded once" holds on SPEC §8's condition: the height offset subtracts exactly in
64-bit, as every offset tested here does (0, 1000 and -12.25 m) and every offset in use.
Then the mean and the difference are exact, and both resample and the reference round
once, to 32-bit. An offset with many binary fraction digits (such as 2**-14 + 2**-45)
would round the subtraction as well, in resample and in the reference alike, so this
test does not cover it (M1 R1 T-08); a non-zero offset is a design change (SPEC §6).
"""

from fractions import Fraction

import numpy as np
import pytest

from mattini.terrain import SPACINGS, TerrainError, resample

SOURCE_M = Fraction(1, 2)


def _reference(mosaic, box, spacing, offset):
    """The rule, by its definition: exact overlap areas and an exact mean, then `float()`
    and `np.float32()`. That is one rounding, to 32-bit, while the mean minus the offset is
    a 64-bit number (the offset subtracts exactly, SPEC §8); otherwise `float()` rounds
    first."""
    e_min, e_max, n_min, n_max = (Fraction(v) for v in box)
    s = Fraction(spacing)
    rows = int((n_max - n_min) / s) + 1
    cols = int((e_max - e_min) / s) + 1
    out = np.empty((rows, cols), dtype=np.float32)
    for r in range(rows):
        for c in range(cols):
            e_v, n_v = e_min + c * s, n_max - r * s
            e0, e1 = max(e_v - s / 2, e_min), min(e_v + s / 2, e_max)
            n0, n1 = max(n_v - s / 2, n_min), min(n_v + s / 2, n_max)
            total = area = Fraction(0)
            # only the pixels near the vertex can overlap its square
            i_lo, i_hi = max(0, int((n_max - n1) / SOURCE_M) - 1), int((n_max - n0) / SOURCE_M) + 1
            j_lo, j_hi = max(0, int((e0 - e_min) / SOURCE_M) - 1), int((e1 - e_min) / SOURCE_M) + 1
            for i in range(i_lo, min(i_hi, mosaic.shape[0])):
                on = min(n1, n_max - i * SOURCE_M) - max(n0, n_max - (i + 1) * SOURCE_M)
                if on <= 0:
                    continue
                for j in range(j_lo, min(j_hi, mosaic.shape[1])):
                    oe = min(e1, e_min + (j + 1) * SOURCE_M) - max(e0, e_min + j * SOURCE_M)
                    if oe > 0:
                        total += on * oe * Fraction(float(mosaic[i, j]))
                        area += on * oe
            out[r, c] = np.float32(float(total / area - Fraction(offset)))
    return out


def _mosaic(rows, cols, seed):
    rng = np.random.default_rng(seed)
    return (1500.0 + rng.random((rows, cols)) * 900.0).astype(np.float32)


def test_the_allowed_spacings():
    assert tuple(SPACINGS) == (0.5, 1.0, 2.0)


@pytest.mark.parametrize("spacing", [0.5, 1.0, 2.0])
@pytest.mark.parametrize("offset", [0.0, 1000.0, -12.25])
def test_resample_matches_the_rule_bit_for_bit(spacing, offset):
    box = (2623004.0, 2623012.0, 1096002.0, 1096008.0)  # 8 m by 6 m: 16 by 12 pixels
    mosaic = _mosaic(12, 16, seed=int(spacing * 4) + 10 * int(abs(offset)))
    got = resample(mosaic, box, spacing, offset)
    want = _reference(mosaic, box, spacing, offset)
    assert got.dtype == np.float32
    assert got.shape == want.shape
    assert got.tobytes() == want.tobytes()


def test_the_grid_shape_follows_the_box_and_spacing():
    box = (2623000.0, 2623004.0, 1096000.0, 1096002.0)  # 4 m by 2 m
    mosaic = _mosaic(4, 8, seed=1)
    assert resample(mosaic, box, 0.5, 0.0).shape == (5, 9)
    assert resample(mosaic, box, 1.0, 0.0).shape == (3, 5)
    assert resample(mosaic, box, 2.0, 0.0).shape == (2, 3)


def test_rows_run_north_to_south_and_columns_west_to_east():
    box = (2623000.0, 2623002.0, 1096000.0, 1096002.0)
    mosaic = np.zeros((4, 4), dtype=np.float32)
    mosaic[0, :] = 100.0  # the northernmost pixel row
    mosaic[:, 3] += 10.0  # the easternmost pixel column
    heights = resample(mosaic, box, 1.0, 0.0)
    assert heights[0, 0] == 100.0  # north-west vertex: one pixel row, one column
    assert heights[2, 0] == 0.0  # south-west vertex
    assert heights[0, 2] == 110.0  # north-east vertex
    assert heights[2, 2] == 10.0  # south-east vertex


@pytest.mark.parametrize("spacing", [0.25, 1.5, 4.0, 0.0, -1.0])
def test_other_spacings_are_refused(spacing):
    with pytest.raises(TerrainError):
        resample(_mosaic(4, 4, seed=2), (2623000.0, 2623002.0, 1096000.0, 1096002.0), spacing, 0.0)


def test_a_mosaic_that_does_not_fit_the_box_is_refused():
    with pytest.raises(TerrainError):
        resample(_mosaic(4, 5, seed=3), (2623000.0, 2623002.0, 1096000.0, 1096002.0), 1.0, 0.0)


def test_a_box_off_the_source_grid_is_refused():
    with pytest.raises(TerrainError):
        resample(_mosaic(4, 4, seed=4), (2623000.25, 2623002.25, 1096000.0, 1096002.0), 1.0, 0.0)


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_a_non_finite_source_height_is_refused(bad):
    mosaic = _mosaic(4, 4, seed=5)
    mosaic[2, 1] = bad
    with pytest.raises(TerrainError):
        resample(mosaic, (2623000.0, 2623002.0, 1096000.0, 1096002.0), 1.0, 0.0)
