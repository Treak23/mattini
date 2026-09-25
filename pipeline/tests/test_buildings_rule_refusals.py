"""`build_chunks` refusals beyond the pinned rule tests (brief M2-04; docs/SPEC.md §8).

What the rule cannot place is refused naming the UUID, and the sheet when the feature says
which one it was read from: a coordinate that is not a number (snapping cannot measure its
distance to the grid), a feature with no triangle (it has no bounding box), a face that is
not three (E, N, H) points. Nothing is left out silently (Hard Rule 2).

Does NOT prove: that the reader ever hands such a feature over (it refuses most of them
itself, test_buildings_reader.py).
"""

import math

import pytest
from test_buildings_rules import FIXTURE_WORLD, _tetra

from mattini.buildings import BuildingsError, build_chunks
from mattini.world import load_world


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_a_coordinate_that_is_not_a_number_is_refused(value):
    building = _tetra("{NAN}")
    o, x, y = building["triangles"][0]
    building["triangles"][0] = (o, x, (y[0], y[1], value))
    with pytest.raises(BuildingsError, match=r"\{NAN\}"):
        build_chunks([building], load_world(FIXTURE_WORLD), "fixture")


def test_a_feature_without_triangles_is_refused():
    with pytest.raises(BuildingsError, match=r"\{NONE\}"):
        build_chunks(
            [{"uuid": "{NONE}", "objektart": "x", "triangles": []}],
            load_world(FIXTURE_WORLD),
            "fixture",
        )


def test_a_face_that_is_not_three_points_is_refused():
    building = _tetra("{FOUR}")
    o, x, y = building["triangles"][0]
    building["triangles"][0] = (o, x, y, o)
    with pytest.raises(BuildingsError, match=r"\{FOUR\}"):
        build_chunks([building], load_world(FIXTURE_WORLD), "fixture")


def test_a_refusal_names_the_sheet_the_feature_was_read_from():
    building = dict(_tetra("{BAD}"), sheet="1249-42")
    building["triangles"] = building["triangles"][:-1]  # open
    with pytest.raises(BuildingsError, match=r"sheet 1249-42, UUID \{BAD\}"):
        build_chunks([building], load_world(FIXTURE_WORLD), "fixture")


def test_a_building_outside_the_area_is_not_checked_as_a_solid():
    """Only the selected buildings go through the per-building steps (SPEC §8)."""
    outside = _tetra("{OUT}", e=2652000.0)
    outside["triangles"] = outside["triangles"][:-1]  # open, but not in the area
    chunks = build_chunks([_tetra("{IN}"), outside], load_world(FIXTURE_WORLD), "fixture")
    assert [c["buildings"] for c in chunks] == [1]
