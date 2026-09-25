"""Pinning tests for brief M2-03: the LK25 map-sheet grid swissBUILDINGS3D is cut by.

Pinned decisions (docs/SPEC.md §8, the buildings, *Sheets*): the LK25 sheet
1000 + 20 r + c covers E 2'480'000 + 17'500 c to + 17'500, N 1'302'000 - 12'000 (r + 1) to
1'302'000 - 12'000 r; its sixteenth <sheet>-<q><s> is quadrant q (1 north-west,
2 north-east, 3 south-west, 4 south-east; 8'750 m x 6'000 m), then sub-quadrant s of it
(same order; 4'375 m x 3'000 m). Design checked the grid at M2 planning against the STAC
items' bounding boxes and the buildings' own extents (1348-11's data spans
E 2'620'030-2'624'386, N 1'094'988-1'097'821). The buildings step uses every sheet within
100 m of the area, touching included, sorted as text; for the village that is six sheets.

The margin exists because swisstopo files a building by its own rule, not by the grid: three
of the 2'134 buildings in the village's six sheets have their bounding-box centre up to
3.6 m outside their own sheet (measured at M2 planning), so the step reads the neighbours
and selects buildings by the area, never by their sheet.

Does NOT prove: that swisstopo cuts every edition by this grid (measured for the 2020
edition only: every one of the 34 sheets around Zermatt within 7 mm of its STAC bbox).
"""

import pytest
from mattini.sheets import SHEET_ID, sheet_box, sheets_near

VILLAGE = (2623000.0, 2625000.0, 1095000.0, 1098000.0)  # e_min, e_max, n_min, n_max


@pytest.mark.parametrize(
    ("sheet", "box"),
    [
        ("1348-11", (2620000.0, 2624375.0, 1095000.0, 1098000.0)),
        ("1348-12", (2624375.0, 2628750.0, 1095000.0, 1098000.0)),
        ("1348-13", (2620000.0, 2624375.0, 1092000.0, 1095000.0)),
        ("1348-14", (2624375.0, 2628750.0, 1092000.0, 1095000.0)),
        ("1348-22", (2633125.0, 2637500.0, 1095000.0, 1098000.0)),
        ("1348-41", (2628750.0, 2633125.0, 1089000.0, 1092000.0)),
        ("1328-33", (2620000.0, 2624375.0, 1098000.0, 1101000.0)),
        ("1328-34", (2624375.0, 2628750.0, 1098000.0, 1101000.0)),
        ("1166-44", (2598125.0, 2602500.0, 1194000.0, 1197000.0)),
        ("1011-11", (2672500.0, 2676875.0, 1299000.0, 1302000.0)),
    ],
)
def test_sheet_boxes_follow_the_grid(sheet, box):
    assert sheet_box(sheet) == box
    assert all(isinstance(v, float) for v in sheet_box(sheet))


def test_the_sixteen_parts_of_a_sheet_tile_it_exactly():
    parts = [sheet_box(f"1348-{q}{s}") for q in range(1, 5) for s in range(1, 5)]
    area = sum((e1 - e0) * (n1 - n0) for e0, e1, n0, n1 in parts)
    assert area == 17500.0 * 12000.0
    assert min(p[0] for p in parts) == 2620000.0 and max(p[1] for p in parts) == 2637500.0
    assert min(p[2] for p in parts) == 1086000.0 and max(p[3] for p in parts) == 1098000.0
    assert len(set(parts)) == 16


def test_the_village_needs_six_sheets():
    assert sheets_near(VILLAGE) == [
        "1328-33",
        "1328-34",
        "1348-11",
        "1348-12",
        "1348-13",
        "1348-14",
    ]


def test_without_a_margin_only_the_sheets_the_area_touches():
    # the village's box ends exactly on N 1'095'000 and N 1'098'000: touching counts
    assert sheets_near(VILLAGE, margin_m=0.0) == sheets_near(VILLAGE)
    inner = (2623000.0, 2625000.0, 1095500.0, 1097500.0)
    assert sheets_near(inner, margin_m=0.0) == ["1348-11", "1348-12"]


def test_the_margin_is_inclusive_to_the_metre():
    # 1328-33 starts at N 1'098'000: a box ending 100 m south of it is within the margin,
    # one ending 100.5 m south is not
    near = (2621000.0, 2622000.0, 1096000.0, 1097900.0)
    far = (2621000.0, 2622000.0, 1096000.0, 1097899.5)
    assert "1328-33" in sheets_near(near)
    assert "1328-33" not in sheets_near(far)
    assert sheets_near(far) == ["1348-11"]


@pytest.mark.parametrize(
    "bad", ["1348-1", "1348-51", "1348-10", "134-11", "1348_11", "1348-11 ", "", "13480-11"]
)
def test_a_malformed_sheet_id_is_refused(bad):
    assert not SHEET_ID.fullmatch(bad)
    with pytest.raises(ValueError, match="sheet"):
        sheet_box(bad)
