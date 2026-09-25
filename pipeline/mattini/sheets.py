"""The LK25 map-sheet grid swissBUILDINGS3D is cut by (brief M2-03; docs/SPEC.md §8, *Sheets*).

The LK25 sheet `1000 + 20 r + c` (c from 0 to 19, r from 0 to 49) covers
E 2'480'000 + 17'500 c to 2'480'000 + 17'500 (c + 1) and N 1'302'000 - 12'000 (r + 1) to
1'302'000 - 12'000 r. Its sixteenth `<sheet>-<q><s>` is quadrant q (1 north-west,
2 north-east, 3 south-west, 4 south-east; 8'750 m x 6'000 m), then sub-quadrant s of that
quadrant (the same order; 4'375 m x 3'000 m). swissBUILDINGS3D 3.0 publishes one item per
sixteenth. This is the map grid of the sheets, not the world's origin (which lives only in
config/world.json, Hard Rule 4).

What the grid covers (brief M2-07, M2 R1 I-06): the sheets 1000 to 1999 (rows 0 to 49),
E 2'480'000 to 2'830'000 and N 702'000 to 1'302'000. swisstopo numbers the sheets east of
E 2'830'000 outside this scheme (2180, 2240 and 2260, between E 2'830'000 and 2'834'375,
measured on the live collection by M2 R1), so the grid refuses ids of 2000 and above
rather than placing them 600 km away, and refuses a box within the margin of its east edge
rather than silently leaving those sheets out: design extends the grid when an area needs
them.

Which sheets an area needs follows from its box by this grid, never from a typed list:
`sheets_near(box)` is every sheet whose box lies within 100 m of it (buildings overhang
their sheet by up to about 12 m, measured at M2 planning), sorted as text. A malformed id
or one the grid does not place, a box not wholly inside the grid, and a box within the
margin of its east edge are ValueErrors naming them (Hard Rule 2).
"""

from __future__ import annotations

import math
import re

SHEET_ID = re.compile(r"[0-9]{4}-[1-4][1-4]")
DEFAULT_MARGIN_M = 100.0  # the buildings step's margin (SPEC §8)

_WEST = 2_480_000  # E of the grid's west edge (column 0)
_NORTH = 1_302_000  # N of the grid's north edge (row 0)
_SHEET_E, _SHEET_N = 17_500, 12_000  # one LK25 sheet
_PART_E, _PART_N = _SHEET_E // 4, _SHEET_N // 4  # one sixteenth: 4'375 m x 3'000 m
_FIRST, _LAST = 1000, 1999  # the sheet numbers the grid places (2xxx lie east of it)
_COLUMNS = 20  # sheets per row of the numbering
_ROWS = (_LAST - _FIRST) // _COLUMNS + 1  # 50: rows 0 to 49
_PART_COLUMNS, _PART_ROWS = 4 * _COLUMNS, 4 * _ROWS  # the grid in sixteenths
_EAST = _WEST + _SHEET_E * _COLUMNS  # E 2'830'000: no sheets east of it in this grid


def sheet_box(sheet: str) -> tuple[float, float, float, float]:
    """The LV95 box (e_min, e_max, n_min, n_max) of a sheet sixteenth, in whole metres.

    Only the sheets 1000 to 1999 are placed; any other number is a ValueError, never a box.
    """
    row, column = _part_index(sheet)
    return _part_box(row, column)


def sheets_near(
    box: tuple[float, float, float, float], margin_m: float = DEFAULT_MARGIN_M
) -> list[str]:
    """Every sheet whose box is within `margin_m` of `box`, touching included, sorted as text.

    The distance is the shortest one between the two boxes (Euclidean; 0 where they touch
    or overlap). `box` is (e_min, e_max, n_min, n_max) in LV95 metres and must lie wholly
    inside the grid. West of it, north of it and south of it lie no LK25 sheets; east of
    E 2'830'000 lie sheets the grid does not place, so a box within `margin_m` of that edge
    (touching included) is a ValueError: it would need them.
    """
    e_min, e_max, n_min, n_max = _checked_box(box)
    if type(margin_m) not in (int, float) or not (math.isfinite(margin_m) and margin_m >= 0):
        raise ValueError(f"the margin around a box must be finite metres >= 0, found {margin_m!r}")
    if _EAST - e_max <= margin_m:
        raise ValueError(
            f"the box {box!r} is {_EAST - e_max:g} m from E 2'830'000, within the {margin_m:g} m "
            f"margin: no sheets east of E 2'830'000 in mattini's grid: design extends it"
        )
    # every sixteenth that can be within the margin, one more on each side, then the exact test
    first_column = max(0, math.floor((e_min - margin_m - _WEST) / _PART_E) - 1)
    last_column = min(_PART_COLUMNS - 1, math.floor((e_max + margin_m - _WEST) / _PART_E) + 1)
    first_row = max(0, math.floor((_NORTH - n_max - margin_m) / _PART_N) - 1)
    last_row = min(_PART_ROWS - 1, math.floor((_NORTH - n_min + margin_m) / _PART_N) + 1)
    near = []
    for row in range(first_row, last_row + 1):
        for column in range(first_column, last_column + 1):
            s_e_min, s_e_max, s_n_min, s_n_max = _part_box(row, column)
            gap_e = max(0.0, s_e_min - e_max, e_min - s_e_max)
            gap_n = max(0.0, s_n_min - n_max, n_min - s_n_max)
            if math.hypot(gap_e, gap_n) <= margin_m:
                near.append(_part_id(row, column))
    return sorted(near)


def _part_index(sheet: object) -> tuple[int, int]:
    """(row, column) of a sheet sixteenth in the grid of sixteenths, row 0 in the north."""
    if not isinstance(sheet, str) or not SHEET_ID.fullmatch(sheet):
        raise ValueError(
            f"not a sheet id: {sheet!r} (a sheet id is '<LK25 sheet>-<quadrant><sub-quadrant>', "
            f"four digits, a hyphen and two digits 1 to 4, like '1348-11')"
        )
    number, quadrant, part = int(sheet[:4]), int(sheet[5]), int(sheet[6])
    if number < _FIRST:
        raise ValueError(f"sheet {sheet!r} is outside the LK25 grid (sheets start at {_FIRST})")
    if number > _LAST:
        raise ValueError(
            f"sheet {sheet!r} is not an LK25 sheet mattini's grid places: it places the sheets "
            f"{_FIRST} to {_LAST}; the sheets swisstopo numbers from 2000 up (2180, 2240 and "
            f"2260 in its collection) lie east of E 2'830'000, outside this numbering"
        )
    row, column = divmod(number - _FIRST, _COLUMNS)
    q, s = quadrant - 1, part - 1
    return 4 * row + 2 * (q // 2) + s // 2, 4 * column + 2 * (q % 2) + s % 2


def _part_id(row: int, column: int) -> str:
    """The id of the sixteenth at (row, column); the inverse of `_part_index`."""
    number = _FIRST + _COLUMNS * (row // 4) + column // 4
    quadrant = 1 + 2 * ((row % 4) // 2) + (column % 4) // 2
    part = 1 + 2 * (row % 2) + column % 2
    return f"{number}-{quadrant}{part}"


def _part_box(row: int, column: int) -> tuple[float, float, float, float]:
    e_min = _WEST + _PART_E * column
    n_max = _NORTH - _PART_N * row
    return float(e_min), float(e_min + _PART_E), float(n_max - _PART_N), float(n_max)


def _checked_box(box: object) -> tuple[float, float, float, float]:
    """`box` as four floats once it is a finite, non-empty box wholly inside the grid."""
    if (
        not isinstance(box, tuple | list)
        or len(box) != 4
        or not all(type(v) in (int, float) and math.isfinite(v) for v in box)
    ):
        raise ValueError(
            f"a box is four finite numbers (e_min, e_max, n_min, n_max), found {box!r}"
        )
    e_min, e_max, n_min, n_max = (float(v) for v in box)
    if not (e_min < e_max and n_min < n_max):
        raise ValueError(f"the box {box!r} is empty: it needs e_min < e_max and n_min < n_max")
    grid = (
        float(_WEST),
        float(_WEST + _PART_E * _PART_COLUMNS),
        float(_NORTH - _PART_N * _PART_ROWS),
        float(_NORTH),
    )
    if not (grid[0] <= e_min and e_max <= grid[1] and grid[2] <= n_min and n_max <= grid[3]):
        raise ValueError(
            f"the box {box!r} is not wholly inside the LK25 sheet grid "
            f"(E {grid[0]:.0f} to {grid[1]:.0f}, N {grid[2]:.0f} to {grid[3]:.0f})"
        )
    return e_min, e_max, n_min, n_max
