"""The LK25 sheet grid beyond the pinned cases (brief M2-03; docs/SPEC.md §8 *Sheets*).

The pinning tests (test_sheets.py) check ten sheets' boxes, the village's six sheets and
the margin at 100 m to the half metre. These check the rest of the contract the brief
states: every id the grid places round-trips through its box, the distance is the
shortest one between the boxes (so a sheet across a corner counts by the diagonal), and a
malformed box, a box not wholly inside the grid and a bad margin are ValueErrors naming
them (Hard Rule 2).

What the grid covers (brief M2-07, M2 R1 I-06): the sheets 1000 to 1999, 20 columns by 50
rows, E 2'480'000 to 2'830'000 and N 702'000 to 1'302'000. swisstopo numbers the sheets
east of E 2'830'000 outside this scheme (2180, 2240 and 2260, measured by M2 R1 on the live
collection), so ids of 2000 and above are refused rather than placed 600 km away, and a
box within the margin of E 2'830'000 is refused rather than given a sheet list without
them. West, north and south of the grid lie no LK25 sheets.

Does NOT prove: that swisstopo cuts any edition by this grid (test_sheets.py's note; the
real run of `lock buildings` read the six village items the grid names); that no other
swisstopo sheet lies outside it (M2 R1 compared the 6'724 items of the collection then).
"""

import math

import pytest

from mattini.sheets import SHEET_ID, sheet_box, sheets_near

GRID = (2480000.0, 2830000.0, 702000.0, 1302000.0)  # the grid's extent, 1000-11 to 1999-44
EAST = 2830000.0  # the grid's east edge: swisstopo's 2xxx sheets lie beyond it


def _inside(box, by=1.0):
    e_min, e_max, n_min, n_max = box
    return (e_min + by, e_max - by, n_min + by, n_max - by)


def test_every_swiss_sheet_id_round_trips_through_its_box():
    # sheets 1000 to 1399 cover Switzerland and more (rows 0 to 19), all sixteen parts each
    for number in range(1000, 1400):
        for q in range(1, 5):
            for s in range(1, 5):
                sheet = f"{number}-{q}{s}"
                box = sheet_box(sheet)
                assert (box[1] - box[0], box[3] - box[2]) == (4375.0, 3000.0), sheet
                assert sheets_near(_inside(box), margin_m=0.0) == [sheet]


def test_a_sheet_s_neighbours_are_the_eight_around_it():
    # 1348-11 is the north-west corner of sheet 1348: its neighbours are 1327-44 (north-west,
    # the last part of sheet 1327), 1328-33 and 1328-34 (north), 1347-22 and 1347-24 (west),
    # 1348-12, 1348-13 and 1348-14; its own box with no margin touches all eight
    assert sheet_box("1347-22") == (2615625.0, 2620000.0, 1095000.0, 1098000.0)
    assert sheet_box("1327-44") == (2615625.0, 2620000.0, 1098000.0, 1101000.0)
    assert sheets_near(sheet_box("1348-11"), margin_m=0.0) == [
        "1327-44",
        "1328-33",
        "1328-34",
        "1347-22",
        "1347-24",
        "1348-11",
        "1348-12",
        "1348-13",
        "1348-14",
    ]


def test_the_distance_across_a_corner_is_the_diagonal():
    # 1328-34's south-west corner is (2624375, 1098000); a box ending 70 m west and 70 m
    # south of it is 99.0 m away by the diagonal, one ending 71 m from both is 100.4 m
    assert math.hypot(70.0, 70.0) < 100.0 < math.hypot(71.0, 71.0)
    near = (2623000.0, 2624305.0, 1096000.0, 1097930.0)
    far = (2623000.0, 2624304.0, 1096000.0, 1097929.0)
    assert "1328-34" in sheets_near(near)
    assert "1328-34" not in sheets_near(far)
    assert "1328-33" in sheets_near(far)  # straight north: 71 m


def test_the_grid_s_corners_name_only_sheets_that_exist():
    assert sheet_box("1000-11") == (2480000.0, 2484375.0, 1299000.0, 1302000.0)
    assert sheet_box("1019-22") == (2825625.0, 2830000.0, 1299000.0, 1302000.0)
    assert sheet_box("1980-33") == (2480000.0, 2484375.0, 702000.0, 705000.0)
    assert sheet_box("1999-44") == (2825625.0, 2830000.0, 702000.0, 705000.0)
    assert sheets_near(sheet_box("1000-11")) == ["1000-11", "1000-12", "1000-13", "1000-14"]
    assert sheets_near(sheet_box("1980-33")) == ["1980-31", "1980-32", "1980-33", "1980-34"]
    every = [f"{n}-{q}{s}" for n in range(1000, 2000) for q in range(1, 5) for s in range(1, 5)]
    short_of_the_east_edge = (GRID[0], EAST - 0.5, GRID[2], GRID[3])
    assert sheets_near(short_of_the_east_edge, margin_m=0.0) == every  # 16'000, each once


@pytest.mark.parametrize("sheet", ["2000-11", "2180-13", "2240-11", "2260-11", "9999-44"])
def test_ids_of_2000_and_above_are_refused_not_placed(sheet):
    """M2 R1 I-06: sheet_box('2240-11') was E 2'480'000, N 555'000, 600 km from its data."""
    assert SHEET_ID.fullmatch(sheet)
    with pytest.raises(ValueError, match="not an LK25 sheet mattini's grid places") as refused:
        sheet_box(sheet)
    assert repr(sheet) in str(refused.value) and "1000 to 1999" in str(refused.value)


@pytest.mark.parametrize(
    ("box", "margin"),
    [
        ((2829000.0, 2829950.0, 1167500.0, 1168500.0), 100.0),  # the review's: 2240-11 50 m east
        ((2825000.0, 2829900.0, 1167500.0, 1168500.0), 100.0),  # 100 m: the margin is inclusive
        ((2825000.0, 2830000.0, 1167500.0, 1168500.0), 100.0),  # on the edge
        ((2825000.0, 2830000.0, 1167500.0, 1168500.0), 0.0),  # touching counts with no margin
        ((2825625.0, 2830000.0, 702000.0, 705000.0), 100.0),  # the grid's south-east sheet
    ],
)
def test_a_box_within_the_margin_of_the_east_edge_is_refused(box, margin):
    """The sheets east of E 2'830'000 are not in the grid; a box that would need them is
    refused rather than given a sheet list silently without them (M2 R1 I-06)."""
    with pytest.raises(ValueError, match="no sheets east of E 2'830'000") as refused:
        sheets_near(box, margin_m=margin)
    assert repr(box) in str(refused.value) and "design extends it" in str(refused.value)


def test_a_box_just_beyond_the_margin_of_the_east_edge_gets_its_sheets():
    """Half a metre more than the margin from the edge: the column-19 sheets, as before.

    1239 is row 11, column 19; its sixteenths 21 (E 2'821'250-2'825'625) and 22
    (E 2'825'625-2'830'000), both N 1'167'000-1'170'000, hold the box.
    """
    box = (2825000.0, 2829899.5, 1167500.0, 1168500.0)
    assert sheets_near(box) == ["1239-21", "1239-22"]
    touching = (2825000.0, EAST - 0.5, 1167500.0, 1168500.0)
    assert sheets_near(touching, margin_m=0.0) == ["1239-21", "1239-22"]


@pytest.mark.parametrize(
    "box",
    [
        (2479999.0, 2481000.0, 1100000.0, 1101000.0),  # west of the grid
        (2600000.0, 2601000.0, 1301500.0, 1302001.0),  # north of it
        (2829000.0, 2830001.0, 1100000.0, 1101000.0),  # east of column 19
        (2600000.0, 2601000.0, 701999.0, 703000.0),  # south of row 49
        (2400000.0, 2401000.0, 1100000.0, 1101000.0),  # wholly outside
    ],
)
def test_a_box_not_wholly_inside_the_grid_is_refused_naming_it(box):
    with pytest.raises(ValueError, match="LK25 sheet grid") as refused:
        sheets_near(box)
    assert repr(box) in str(refused.value)


@pytest.mark.parametrize(
    "box",
    [
        (2623000.0, 2625000.0, 1095000.0),
        (2623000.0, 2625000.0, 1095000.0, 1098000.0, 0.0),
        (2623000.0, 2625000.0, 1095000.0, math.nan),
        (2623000.0, math.inf, 1095000.0, 1098000.0),
        (2623000.0, 2625000.0, True, 1098000.0),
        ("2623000", 2625000.0, 1095000.0, 1098000.0),
        (2625000.0, 2623000.0, 1095000.0, 1098000.0),  # e_min > e_max
        (2623000.0, 2625000.0, 1098000.0, 1098000.0),  # empty
        None,
    ],
)
def test_a_malformed_box_is_refused_naming_it(box):
    with pytest.raises(ValueError, match="box") as refused:
        sheets_near(box)
    assert repr(box) in str(refused.value)


@pytest.mark.parametrize("margin", [-1.0, -0.0001, math.nan, math.inf, "100", None, True])
def test_a_bad_margin_is_refused_naming_it(margin):
    with pytest.raises(ValueError, match="margin") as refused:
        sheets_near((2623000.0, 2625000.0, 1095000.0, 1098000.0), margin_m=margin)
    assert repr(margin) in str(refused.value)


@pytest.mark.parametrize("sheet", ["0999-11", "0000-44"])
def test_a_sheet_number_below_the_grid_is_refused_naming_it(sheet):
    assert SHEET_ID.fullmatch(sheet)
    with pytest.raises(ValueError, match="outside the LK25 grid") as refused:
        sheet_box(sheet)
    assert sheet in str(refused.value)


@pytest.mark.parametrize("sheet", [None, 1348, b"1348-11", ["1348-11"]])
def test_a_sheet_id_that_is_not_text_is_refused(sheet):
    with pytest.raises(ValueError, match="sheet"):
        sheet_box(sheet)
