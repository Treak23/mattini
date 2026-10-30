"""Pinning tests for brief v0.5.0-01: the capture shadows' rule, on small grids built here.

Carried from brief M4-03's pin (docs/briefs/pinning/M4-03/) and re-pinned for release 0.5.0
(2026-10-29): only these docstrings changed, to name v0.5.0-01, v0.5.0-02 and the reader.

Pinned decisions (m4-design §3 and the brief's Decisions 1-6):
- The cells: 1 m, from the 0.5 m surface, each the largest of its 2 x 2 pixels, in float64
  (`cell_heights`); row 0 is the northern row, column 0 the western column.
- Cast shadow (`cast_shadow`): with A the grid azimuth and e the elevation, for k = 1 ... K the
  offset towards the sun is computed once per k, in cells: dx = k * sin(A) (east),
  dy = -(k * cos(A)) (south, rows grow southwards); i0 = floor(dx), fx = dx - i0, j0 =
  floor(dy), fy = dy - j0. The surface there is the bilinear value of the four cells (r + j0,
  c + i0), (r + j0, c + i0 + 1), (r + j0 + 1, c + i0), (r + j0 + 1, c + i0 + 1), evaluated as
  north = h00 * (1 - fx) + h01 * fx, south = h10 * (1 - fx) + h11 * fx, s = north * (1 - fy) +
  south * fy. A column (row) whose weight fx (fy) is 0 is not needed. A point whose needed
  cells are not all in the grid casts nothing (the grid is the cells' centres; nothing is
  clamped). The cell is in cast shadow when s > (h + k * tan(e)) + threshold_m, for any k.
  K = ceil((max - min) / tan(e)) over the cells (`march_steps`).
- Own shadow (`own_shadow`): gx = dh/dE and gy = dh/dN by central differences over the two
  neighbours divided by 2, one-sided (not halved) on the grid's edges; with the sun's unit
  vector (cos e sin A, cos e cos A, sin e) = (ux, uy, uz), the cell is in its own shadow when
  ((-gx) * ux - gy * uy) + uz <= 0.
- The mask (`capture_mask`, at 0.5 m; the ruling of 2026-10-17 on m4-design §3): the march
  stays on the 1 m cells; each 1 m cell in cast or own shadow becomes its 2 x 2 cells of 0.5 m
  (row 2r and 2r + 1, column 2c and 2c + 1), and then the inset (`inset`) runs on the 0.5 m
  grid: a 0.5 m cell in shadow stays 255 only when its four neighbours inside the grid are in
  shadow too; every other cell is 0; uint8, twice the 1 m grid's rows and columns.
The oracle below is written here from those words, cell by cell in Python floats, and it
marches until the point leaves the grid instead of to K, so a K too small fails it too.

Does NOT prove: the real village's mask (config/shadows.json, the step's own comparison);
that the mask lies on the photo's shadows; the game's reading (M4-06's reader, re-cut in 0.5.0).
"""

import math

import numpy as np
import pytest

from mattini.shadows import (
    capture_mask,
    cast_shadow,
    cell_heights,
    inset,
    march_steps,
    own_shadow,
)

SUN_AZ, SUN_EL, THRESHOLD = 184.67, 50.1, 0.05  # config/shadows.json's sun (the brief)


# ------------------------------------------------------------------- the oracle


def _oracle_cast(h, r, c, az, el, threshold):
    rows, columns = len(h), len(h[0])
    sin_a, cos_a = math.sin(math.radians(az)), math.cos(math.radians(az))
    tan_e = math.tan(math.radians(el))
    k = 0
    while True:
        k += 1
        dx = k * sin_a
        dy = -(k * cos_a)
        i0, j0 = math.floor(dx), math.floor(dy)
        fx, fy = dx - i0, dy - j0
        ca, ra = c + i0, r + j0
        cb = ca + 1 if fx > 0 else ca
        rb = ra + 1 if fy > 0 else ra
        far = max(abs(dx), abs(dy))
        if far > rows + columns:  # every later point is outside the grid too
            return False
        if ca < 0 or ra < 0 or cb > columns - 1 or rb > rows - 1:
            continue
        north = h[ra][ca] * (1.0 - fx) + h[ra][cb] * fx
        south = h[rb][ca] * (1.0 - fx) + h[rb][cb] * fx
        s = north * (1.0 - fy) + south * fy
        if s > (h[r][c] + k * tan_e) + threshold:
            return True


def _oracle_own(h, r, c, az, el):
    rows, columns = len(h), len(h[0])
    a, e = math.radians(az), math.radians(el)
    ux, uy, uz = math.cos(e) * math.sin(a), math.cos(e) * math.cos(a), math.sin(e)
    if c == 0:
        gx = h[r][1] - h[r][0]
    elif c == columns - 1:
        gx = h[r][c] - h[r][c - 1]
    else:
        gx = (h[r][c + 1] - h[r][c - 1]) / 2
    if r == 0:
        gy = h[0][c] - h[1][c]
    elif r == rows - 1:
        gy = h[r - 1][c] - h[r][c]
    else:
        gy = (h[r - 1][c] - h[r + 1][c]) / 2
    return ((-gx) * ux - gy * uy) + uz <= 0


def _oracle_mask(surface, az, el, threshold):
    rows, columns = surface.shape[0] // 2, surface.shape[1] // 2
    h = [
        [
            max(float(surface[2 * r + i, 2 * c + j]) for i in (0, 1) for j in (0, 1))
            for c in range(columns)
        ]
        for r in range(rows)
    ]
    shadow = [
        [
            _oracle_cast(h, r, c, az, el, threshold) or _oracle_own(h, r, c, az, el)
            for c in range(columns)
        ]
        for r in range(rows)
    ]
    fine = [[shadow[r // 2][c // 2] for c in range(2 * columns)] for r in range(2 * rows)]
    out = np.zeros((2 * rows, 2 * columns), dtype=np.uint8)
    for r in range(2 * rows):
        for c in range(2 * columns):
            near = [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]
            inside = [(i, j) for i, j in near if 0 <= i < 2 * rows and 0 <= j < 2 * columns]
            if fine[r][c] and all(fine[i][j] for i, j in inside):
                out[r, c] = 255
    return out


def _fine(cells: np.ndarray) -> np.ndarray:
    """Each 1 m cell as its 2 x 2 cells of 0.5 m."""
    return np.repeat(np.repeat(cells, 2, axis=0), 2, axis=1)


def _random_surface(seed: int, rows: int, columns: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    surface = 1600.0 + rng.random((2 * rows, 2 * columns)) * 2.5
    for _ in range(4):  # a few towers and walls of a few metres to 15 m
        i, j = rng.integers(0, 2 * rows - 3), rng.integers(0, 2 * columns - 3)
        surface[i : i + rng.integers(1, 4), j : j + rng.integers(1, 6)] += rng.random() * 15
    return surface.astype(np.float32)


SUNS = [
    (184.67, 50.1, 0.05),
    (175.33, 50.1, 0.05),
    (4.67, 50.1, 0.05),
    (95.0, 30.0, 0.05),
    (271.3, 20.0, 0.0),
    (45.0, 50.1, 0.05),
    (135.0, 65.0, 0.05),
    (225.0, 40.0, 0.05),
    (315.0, 50.1, 0.0),
    (180.0, 50.1, 0.05),
    (90.0, 50.1, 0.05),
]


@pytest.mark.parametrize("seed", range(6))
@pytest.mark.parametrize("sun", SUNS, ids=lambda s: f"az{s[0]}-el{s[1]}-t{s[2]}")
def test_the_mask_is_the_rule_written_out_cell_by_cell(seed, sun):
    surface = _random_surface(seed, 9 + seed, 13 - seed)
    expected = _oracle_mask(surface, *sun)
    found = capture_mask(surface, *sun)
    assert found.dtype == np.uint8 and found.shape == expected.shape
    assert np.array_equal(found, expected), np.argwhere(found != expected)[:5].tolist()


@pytest.mark.parametrize("sun", SUNS, ids=lambda s: f"az{s[0]}-el{s[1]}-t{s[2]}")
def test_the_random_cases_hold_cast_own_and_kept_shadow(sun):
    """The comparison above is not vacuous: under every sun its cases hold cells in cast
    shadow, cells in their own shadow only, cells the inset keeps and cells it removes."""
    cast = own_only = kept = removed = 0
    for seed in range(6):
        surface = _random_surface(seed, 9 + seed, 13 - seed)
        h = cell_heights(surface)
        c = cast_shadow(h, sun[0], sun[1], sun[2])
        o = own_shadow(h, sun[0], sun[1])
        m = capture_mask(surface, *sun)
        cast += int(c.sum())
        own_only += int((o & ~c).sum())
        kept += int((m == 255).sum())
        removed += int((_fine(c | o) & (m == 0)).sum())
    assert min(cast, own_only, kept, removed) > 0, (cast, own_only, kept, removed)


# ------------------------------------------------------------------- the cells


def test_a_cell_is_the_largest_of_its_four_pixels_in_float64():
    surface = np.arange(16, dtype=np.float32).reshape(4, 4) + np.float32(1600.25)
    cells = cell_heights(surface)
    assert cells.dtype == np.float64
    assert cells.tolist() == [[1605.25, 1607.25], [1613.25, 1615.25]]
    for i in range(4):
        for j in range(4):
            spiked = np.full((4, 4), np.float32(1600.0))
            spiked[i, j] = np.float32(1612.5)
            expected = np.full((2, 2), 1600.0)
            expected[i // 2, j // 2] = 1612.5
            assert np.array_equal(cell_heights(spiked), expected), (i, j)


def test_a_wall_half_a_metre_thick_casts_its_full_height():
    """One 0.5 m pixel row 6 m high (a wall): its 1 m cell takes 6 m and casts the 1 m rows 11
    to 14, which the 0.5 m inset keeps from 0.5 m row 23 to 28. A mean of the four pixels (3 m)
    keeps 0.5 m rows 27 and 28 only; a minimum or the north-west pixel casts nothing."""
    surface = np.full((40, 16), np.float32(1600.0))
    surface[31, :] += np.float32(6.0)  # the southern half of 1 m row 15
    mask = capture_mask(surface, SUN_AZ, SUN_EL, THRESHOLD)
    assert mask.shape == (40, 16)
    assert (mask[23:29, 3:] == 255).all()
    assert (mask[:23] == 0).all() and (mask[29:] == 0).all() and (mask[:, :2] == 0).all()


# ------------------------------------------------------------------- cast shadow


def _tower() -> np.ndarray:
    h = np.full((30, 20), 1600.0)
    h[20:25, 5:10] += 12.0
    return h


def test_the_flight_s_sun_casts_north_and_its_shadow_leans_east():
    """The sun stands south, 4.67 deg west of grid south: shadows fall north, leaning east."""
    cast = cast_shadow(_tower(), SUN_AZ, SUN_EL, THRESHOLD)
    assert cast[11:20, 6:10].all() and cast[15:20, 5].all()
    assert not cast[11:15, 5].any(), "the far end leans east: its western column is lit"
    assert not cast[25:].any(), "nothing south of the tower"
    assert not cast[:11].any(), "12 m casts 10 m at most"
    assert cast[:, 10:].sum() == 0 and cast[:, :5].sum() == 0


def test_a_mirrored_or_opposite_sun_casts_elsewhere():
    mirrored = cast_shadow(_tower(), 360.0 - SUN_AZ, SUN_EL, THRESHOLD)
    assert mirrored[11:15, 5:9].all() and not mirrored[11:15, 9].any(), "leans west"
    opposite = cast_shadow(_tower(), SUN_AZ - 180.0, SUN_EL, THRESHOLD)
    assert opposite[25:].any() and not opposite[:20].any(), "falls south"
    assert not np.array_equal(mirrored, cast_shadow(_tower(), SUN_AZ, SUN_EL, THRESHOLD))


def _wall(height: float) -> np.ndarray:
    h = np.full((12, 8), 1600.0)
    h[6, :] += height
    return h


def test_the_threshold_keeps_a_low_wall_from_casting():
    """North of a wall the sample at k = 1 is 0.99668 of the wall's height: a 1.23 m wall
    reaches 1.2259 m against tan(50.1 deg) = 1.1965 m, so it casts only without the 5 cm."""
    assert not cast_shadow(_wall(1.23), SUN_AZ, SUN_EL, THRESHOLD)[5].any()
    assert cast_shadow(_wall(1.23), SUN_AZ, SUN_EL, 0.0)[5, 1:].all()
    assert cast_shadow(_wall(1.27), SUN_AZ, SUN_EL, THRESHOLD)[5, 1:].all()


def test_a_point_outside_the_grid_casts_nothing():
    """The western cell's sample at k = 1 lies 0.08 m west of the first column's centre:
    outside the grid, so it casts nothing (no clamping to the edge)."""
    cast = cast_shadow(_wall(1.27), SUN_AZ, SUN_EL, THRESHOLD)
    assert not cast[5, 0]
    south_edge = np.full((6, 6), 1600.0)
    south_edge[5, :] += 20.0  # the last row: a cell's sun lies beyond it after one metre
    assert cast_shadow(south_edge, SUN_AZ, SUN_EL, THRESHOLD)[4, 1:].all()
    beyond = np.full((6, 6), 1600.0)  # the same wall just outside the grid casts nothing
    assert not cast_shadow(beyond, SUN_AZ, SUN_EL, THRESHOLD).any()


def test_march_steps_is_the_height_range_over_tan_e():
    h = _tower()
    assert march_steps(h, SUN_EL) == math.ceil(12.0 / math.tan(math.radians(SUN_EL))) == 11
    assert march_steps(np.full((3, 3), 1600.0), SUN_EL) == 0
    assert march_steps(_wall(1.27), 20.0) == math.ceil(1.27 / math.tan(math.radians(20.0)))


def test_a_long_shadow_reaches_as_far_as_the_rule_says():
    """A 30 m mast at a low sun (20 deg) casts 82 m: the march goes that far."""
    h = np.full((100, 6), 1600.0)
    h[95:98, 1:5] += 30.0
    cast = cast_shadow(h, 180.0, 20.0, THRESHOLD)
    tan_e = math.tan(math.radians(20.0))
    reach = [r for r in range(95) if cast[r, 2]]
    assert reach and min(reach) == 95 - math.floor((30.0 - THRESHOLD) / tan_e)


# ------------------------------------------------------------------- own shadow


def _ramp(rows: int, columns: int, slope_south: float) -> np.ndarray:
    """A plane rising `slope_south` metres per metre towards the south."""
    return (
        1600.0 + slope_south * np.arange(rows, dtype=np.float64)[:, None] + np.zeros((1, columns))
    )


def test_a_slope_steeper_than_the_sun_facing_away_is_in_its_own_shadow():
    """Falling north at 1.25 (51.3 deg): dot = 0.7672 - 0.6393 * 1.25 < 0; at 1.15 it is lit.
    A slope facing the sun (rising north) is lit however steep."""
    assert own_shadow(_ramp(6, 5, 1.25), SUN_AZ, SUN_EL).all()
    assert not own_shadow(_ramp(6, 5, 1.15), SUN_AZ, SUN_EL).any()
    assert not own_shadow(_ramp(6, 5, -3.0), SUN_AZ, SUN_EL).any()
    assert own_shadow(_ramp(6, 5, -1.25), SUN_AZ - 180.0, SUN_EL).all()


def test_the_normal_is_one_sided_at_the_edges_and_central_inside():
    """A 1.25 m step at the grid's first and last rows: one-sided there (1.25, shadow), the
    next row's central difference halves it (0.625, lit)."""
    h = np.full((6, 4), 1601.25)
    h[0, :] = 1600.0
    h[5, :] = 1602.5
    own = own_shadow(h, SUN_AZ, SUN_EL)
    assert own[0].all() and own[5].all()
    assert not own[1:5].any()
    east = np.full((4, 6), 1600.0)
    east[:, 1:] += 1.25  # a sun in the east (90 deg): the western edge column faces away
    east[:, 5] += 1.25
    own = own_shadow(east, 90.0, SUN_EL)
    assert own[:, 0].all() and own[:, 5].all() and not own[:, 1:5].any()


# ------------------------------------------------------------------- the inset


def test_the_inset_keeps_a_shadow_cell_only_inside_the_shadow():
    shadow = np.zeros((5, 5), dtype=bool)
    shadow[1:4, 1:4] = True
    mask = inset(shadow)
    assert mask.dtype == np.uint8
    assert np.argwhere(mask == 255).tolist() == [[2, 2]]
    assert set(np.unique(mask).tolist()) == {0, 255}


def test_the_inset_ignores_neighbours_outside_the_grid():
    shadow = np.zeros((5, 5), dtype=bool)
    shadow[0:3, 0:3] = True
    assert np.argwhere(inset(shadow) == 255).tolist() == [[0, 0], [0, 1], [1, 0], [1, 1]]
    assert (inset(np.ones((3, 4), dtype=bool)) == 255).all()
    assert (inset(np.zeros((3, 4), dtype=bool)) == 0).all()


def test_the_mask_is_the_1_m_shadow_at_0_5_m_then_the_inset():
    surface = _random_surface(11, 12, 10)
    h = cell_heights(surface)
    shadow = cast_shadow(h, SUN_AZ, SUN_EL, THRESHOLD) | own_shadow(h, SUN_AZ, SUN_EL)
    mask = capture_mask(surface, SUN_AZ, SUN_EL, THRESHOLD)
    assert mask.shape == (24, 20) == surface.shape
    assert np.array_equal(mask, inset(_fine(shadow)))
    assert not np.array_equal(mask, _fine(inset(shadow))), "the inset runs at 0.5 m, not at 1 m"


def test_the_inset_at_0_5_m_removes_half_a_metre():
    """A shadow 3 x 3 m (1 m cells) keeps 2 x 2 m at 0.5 m: half a metre off every side."""
    h = np.zeros((7, 7), dtype=bool)
    h[2:5, 2:5] = True
    mask = inset(_fine(h))
    assert np.argwhere(mask == 255).min(axis=0).tolist() == [5, 5]
    assert np.argwhere(mask == 255).max(axis=0).tolist() == [8, 8]
