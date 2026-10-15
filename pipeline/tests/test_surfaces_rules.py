"""Brief M3-06: the surfaces rule's cases one at a time, and `class_grid`'s refusals.

The shared fixture pins the rule on one designed area; these are the cases a reader of
SPEC §8 *The surfaces* looks for by name, each on a box small enough to read. Roofed
bridges (KUNSTBAUTE 300 and 400) are decided by design in the brief and appear in no pinned
test, so they are here. The streams' width is an ASSUMED 2 m, a labelled placeholder: the
test pins the number the step uses, not a fact about any stream.

Does NOT prove: the rule on the real file (the step's comparison with config/surfaces.json
does); the order in which the pinned fixture's tie-breaks are decided (the reference
comparison in test_surfaces_reference.py draws them at random).
"""

import numpy as np
import pytest

from mattini import surfaces
from mattini.surfaces import SurfacesError, class_grid

E0, N1 = 2_700_000_000, 1_200_000_000  # mm
BOX = (2_700_000.0, 2_700_004.0, 1_199_996.0, 1_200_000.0)  # 4 m × 4 m: 8 × 8 texels at 0.5 m


def _empty() -> dict:
    return {"TLM_STRASSE": [], "TLM_BODENBEDECKUNG": [], "TLM_FLIESSGEWAESSER": []}


def _line(layer: str, attributes: dict, *points, uuid: str = "x") -> dict:
    """A one-part line through `points` given in metres east of the box's west edge and
    below its north edge, as the reader hands it over."""
    coordinates = [[[E0 + round(e * 1000), N1 - round(s * 1000)] for e, s in points]]
    geometry = {"type": "MultiLineString", "coordinates": coordinates}
    return {"uuid": uuid, "attributes": attributes, "geometry": geometry}


def _polygon(attributes: dict, *rings, uuid: str = "x") -> dict:
    rows = [[[E0 + round(e * 1000), N1 - round(s * 1000)] for e, s in ring] for ring in rings]
    geometry = {"type": "MultiPolygon", "coordinates": [rows]}
    return {"uuid": uuid, "attributes": attributes, "geometry": geometry}


def _street(belag=100, bau=100, kind=10, *points) -> dict:
    attributes = {"BELAGSART": belag, "KUNSTBAUTE": bau, "OBJEKTART": kind}
    return _line("TLM_STRASSE", attributes, *(points or ((0, 2), (4, 2))))


def _square(kind: int, a: float, b: float, c: float, d: float, uuid: str = "x") -> dict:
    ring = [(a, b), (c, b), (c, d), (a, d), (a, b)]
    return _polygon({"OBJEKTART": kind}, ring, uuid=uuid)


def _grid(**layers) -> np.ndarray:
    features = _empty()
    for layer, found in layers.items():
        features[layer] = found
    return class_grid(features, BOX, 0.5)


@pytest.mark.parametrize("bau", [300, 400, 700, 1000, 1100, 1200, 1400])
def test_a_roofed_or_underground_road_is_not_drawn(bau):
    assert not _grid(TLM_STRASSE=[_street(100, bau)]).any()


@pytest.mark.parametrize("bau", [100, 200, 900, 999998])
def test_a_road_on_the_ground_or_a_bridge_or_stairs_is_drawn(bau):
    grid = _grid(TLM_STRASSE=[_street(100, bau, 16)])
    assert set(np.unique(grid)) == {0, 4}


def test_the_covered_bridges_are_named_in_the_rule():
    """300 Bruecke mit Galerie and 400 Gedeckte Bruecke: design's decision in the brief."""
    assert {300, 400} <= surfaces.NOT_DRAWN
    assert 200 not in surfaces.NOT_DRAWN, "an open bridge is on the photo's ground"


@pytest.mark.parametrize("belag", [100, 200])
def test_the_surface_gives_the_class_not_the_kind_of_road(belag):
    code = 4 if belag == 100 else 3
    street = _grid(TLM_STRASSE=[_street(belag, 100, 10)])  # 4 m wide: covers the whole box
    assert set(np.unique(street)) == {code}
    way = _grid(TLM_STRASSE=[_street(belag, 100, 16)])  # 1 m wide
    assert set(np.unique(way)) == {0, code}


@pytest.mark.parametrize("kind", [0, 7, 12, 13, 14, 19, 21, 22, 23, 24, 99])
def test_a_kind_without_a_width_is_not_drawn(kind):
    assert not _grid(TLM_STRASSE=[_street(100, 100, kind)]).any()


@pytest.mark.parametrize("belag", [0, 99, 300, 999997, 999998])
def test_an_unknown_surface_is_not_drawn(belag):
    assert not _grid(TLM_STRASSE=[_street(belag, 100, 10)]).any()


@pytest.mark.parametrize(
    ("kind", "width_m"), sorted((k, w / 1000) for k, w in surfaces.WIDTH_MM.items())
)
def test_a_road_is_as_wide_as_its_kind(kind, width_m):
    """A horizontal road through the middle of a tall box: its rows are width / 0.5 m."""
    box = (2_700_000.0, 2_700_004.0, 1_199_976.0, 1_200_000.0)  # 24 m tall: 48 rows
    features = _empty()
    features["TLM_STRASSE"] = [_street(100, 100, kind, (0, 12.25), (4, 12.25))]
    grid = class_grid(features, box, 0.5)
    rows = np.flatnonzero(grid.any(axis=1))
    # the line runs through a texel row's centre: that row and width/2 either side, the
    # outermost ones exactly on the edge (a tie, drawn)
    assert len(rows) == int(width_m / 0.5) + 1
    assert (grid[rows] == 4).all()


def test_priority_road_over_path_over_water_over_rock():
    """Rock over the whole box, a pond over its north-west 3 m, a path and a road side by side
    along the north edge (1 m wide: rows 0 and 1; the road's columns 0-2, the path's 0-4)."""
    rock = _square(1, 0, 0, 4, 4, uuid="rock")
    pond = _square(10, 0, 0, 3, 3, uuid="pond")
    path = _street(200, 100, 16, (0, 0.5), (2, 0.5))
    road = _street(100, 100, 16, (0, 0.5), (1, 0.5))
    grid = _grid(TLM_BODENBEDECKUNG=[rock, pond], TLM_STRASSE=[path, road])
    assert grid[0, 0] == 4 and grid[1, 2] == 4, "road over path, water and rock"
    assert grid[0, 3] == 3 and grid[1, 4] == 3, "path over water and rock"
    assert grid[0, 5] == 2 and grid[2, 0] == 2 and grid[5, 5] == 2, "water over rock"
    assert grid[0, 6] == 1 and grid[6, 6] == 1 and grid[7, 7] == 1, "rock where nothing is above"
    only_land = _grid(TLM_BODENBEDECKUNG=[rock, pond])
    assert only_land[0, 0] == 2 and only_land[6, 6] == 1


def test_the_priority_does_not_depend_on_the_order_features_are_given():
    rock = _square(1, 0, 0, 4, 4, uuid="rock")
    pond = _square(5, 1, 1, 3, 3, uuid="pond")
    one = _grid(TLM_BODENBEDECKUNG=[rock, pond])
    other = _grid(TLM_BODENBEDECKUNG=[pond, rock])
    assert np.array_equal(one, other)
    assert one[4, 4] == 2 and one[0, 0] == 1


def test_a_stream_is_two_metres_wide_by_assumption():
    """The width is a placeholder (TLM gives none): 1.0 m either side, a centre exactly 1.0 m
    from the line is water and one at 1.5 m is not."""
    assert surfaces.STREAM_WIDTH_MM == 2000
    stream = _line("TLM_FLIESSGEWAESSER", {"OBJEKTART": 4, "VERLAUF": 100}, (0, 1.75), (4, 1.75))
    grid = _grid(TLM_FLIESSGEWAESSER=[stream])  # row 3's centre is 1.75 m below the north edge
    assert grid.any(axis=1).tolist() == [False, True, True, True, True, True, False, False]
    assert (grid[1:6] == 2).all()


@pytest.mark.parametrize(
    ("attributes", "drawn"),
    [
        ({"OBJEKTART": 4, "VERLAUF": 100}, True),
        ({"OBJEKTART": 4, "VERLAUF": 500}, True),
        ({"OBJEKTART": 4, "VERLAUF": 200}, False),  # underground
        ({"OBJEKTART": 4, "VERLAUF": 400}, False),  # on a bridge
        ({"OBJEKTART": 0, "VERLAUF": 100}, False),  # a Bisse or Suone
        ({"OBJEKTART": 7, "VERLAUF": 100}, False),  # a Trockenrinne
    ],
)
def test_which_watercourses_are_drawn(attributes, drawn):
    stream = _line("TLM_FLIESSGEWAESSER", attributes, (0, 2), (4, 2))
    assert _grid(TLM_FLIESSGEWAESSER=[stream]).any() == drawn


@pytest.mark.parametrize(
    ("kind", "code"),
    [(1, 1), (2, 1), (3, 1), (4, 1), (5, 2), (10, 2), (0, 0), (6, 0), (7, 0), (11, 0), (12, 0)],
)
def test_the_land_cover_kinds(kind, code):
    grid = _grid(TLM_BODENBEDECKUNG=[_square(kind, -1, -1, 5, 5)])
    assert set(np.unique(grid)) == {code}


def test_a_hole_is_outside_and_overlapping_features_are_or_ed_not_xor_ed():
    outer = [(0, 0), (4, 0), (4, 4), (0, 4), (0, 0)]
    hole = [(1, 1), (3, 1), (3, 3), (1, 3), (1, 1)]
    ring = _polygon({"OBJEKTART": 1}, outer, hole, uuid="ring")
    assert _grid(TLM_BODENBEDECKUNG=[ring])[3, 3] == 0
    assert _grid(TLM_BODENBEDECKUNG=[ring])[0, 0] == 1
    twice = _grid(TLM_BODENBEDECKUNG=[_square(1, 0, 0, 3, 3, "a"), _square(1, 0, 0, 3, 3, "b")])
    assert (twice[:6, :6] == 1).all(), "two identical rocks are rock, not a hole"


def test_the_polygon_edges_are_half_open_west_and_south_in_east_and_north_out():
    # a rectangle whose edges pass exactly through texel centres (0.25 m, 1.25 m, ...)
    grid = _grid(TLM_BODENBEDECKUNG=[_square(1, 0.25, 0.25, 1.25, 1.25)])
    columns = np.flatnonzero(grid.any(axis=0)).tolist()
    rows = np.flatnonzero(grid.any(axis=1)).tolist()
    assert columns == [0, 1], "west edge in, east edge out"
    # in N, the south edge (N = N1 - 1.25) is in and the north edge (N = N1 - 0.25) is out
    assert rows == [1, 2]


def test_features_outside_the_box_draw_nothing_and_a_cover_of_the_whole_box_is_all_rock():
    far = _street(100, 100, 10, (40, 2), (50, 2))
    assert not _grid(TLM_STRASSE=[far]).any()
    assert (_grid(TLM_BODENBEDECKUNG=[_square(2, -50, -50, 50, 50)]) == 1).all()


def test_long_diagonal_roads_and_every_way_a_line_can_run():
    for points in (
        ((-10, -10), (14, 14)),
        ((14, -10), (-10, 14)),
        ((2, -9), (2, 13)),
        ((-5, 3), (9, 3)),
    ):
        grid = _grid(TLM_STRASSE=[_street(100, 100, 11, *points)])
        assert grid.any() and (grid != 4).sum() > 0 and set(np.unique(grid)) == {0, 4}


def test_small_windows_give_the_same_classes(monkeypatch):
    """The step handles segment-row pairs and texel rows in windows; the windows' size must
    not change a class (a window boundary through a road, a polygon, a stream)."""
    street = _street(100, 100, 8, (-1, -1), (5, 5))
    river = _square(5, 0.5, 0.5, 3.5, 3.5)
    stream = _line("TLM_FLIESSGEWAESSER", {"OBJEKTART": 4, "VERLAUF": 100}, (0, 3), (4, 2))
    layers = {
        "TLM_STRASSE": [street],
        "TLM_BODENBEDECKUNG": [river],
        "TLM_FLIESSGEWAESSER": [stream],
    }
    whole = _grid(**layers)
    monkeypatch.setattr(surfaces, "PAIRS", 3)
    monkeypatch.setattr(surfaces, "BAND_CELLS", 1)
    assert np.array_equal(_grid(**layers), whole)


# ------------------------------------------------------------------------------ refusals


def test_features_must_come_as_the_three_layers():
    with pytest.raises(SurfacesError, match="layers"):
        class_grid({"TLM_STRASSE": []}, BOX, 0.5)
    with pytest.raises(SurfacesError, match="layers"):
        class_grid({**_empty(), "TLM_EISENBAHN": []}, BOX, 0.5)


def _broken(change) -> dict:
    features = _empty()
    features["TLM_STRASSE"] = [_street(100, 100, 10)]
    features["TLM_BODENBEDECKUNG"] = [_square(1, 0, 0, 2, 2)]
    change(features)
    return features


@pytest.mark.parametrize(
    ("change", "pattern"),
    [
        (lambda f: f["TLM_STRASSE"][0]["attributes"].pop("KUNSTBAUTE"), "attributes"),
        (lambda f: f["TLM_STRASSE"][0]["attributes"].update(KUNSTBAUTE=True), "integer"),
        (lambda f: f["TLM_STRASSE"][0]["attributes"].update(OBJEKTART=10.0), "integer"),
        (lambda f: f["TLM_STRASSE"][0].pop("uuid"), "UUID"),
        (lambda f: f["TLM_STRASSE"][0]["geometry"].update(type="MultiPolygon"), "MultiLineString"),
        (
            lambda f: f["TLM_STRASSE"][0]["geometry"].update(coordinates=[[[E0, N1]]]),
            "fewer than two",
        ),
        (
            lambda f: f["TLM_STRASSE"][0]["geometry"].update(coordinates=[[[1.5, 2], [3, 4]]]),
            "whole-mm",
        ),
        (
            lambda f: f["TLM_STRASSE"][0]["geometry"].update(coordinates=[[[1, 2, 3], [4, 5, 6]]]),
            "whole-mm",
        ),
        (
            lambda f: f["TLM_STRASSE"][0]["geometry"].update(coordinates=[[[E0, N1], [10**13, 0]]]),
            "537 km",
        ),
        (
            lambda f: f["TLM_BODENBEDECKUNG"][0]["geometry"].update(type="MultiLineString"),
            "MultiPolygon",
        ),
        (lambda f: f["TLM_BODENBEDECKUNG"][0]["geometry"]["coordinates"][0][0].pop(), "not closed"),
        (lambda f: f["TLM_BODENBEDECKUNG"][0]["geometry"]["coordinates"].clear(), "without rings"),
    ],
)
def test_a_malformed_feature_is_refused_naming_the_layer(change, pattern):
    with pytest.raises(SurfacesError, match=pattern) as refusal:
        class_grid(_broken(change), BOX, 0.5)
    assert "TLM_" in str(refusal.value)


@pytest.mark.parametrize(
    ("box", "cell_m", "pattern"),
    [
        ((2_700_000.0, 2_700_004.0, 1_199_996.0, 1_200_000.0), 0.3, "whole number"),
        ((2_700_000.0, 2_700_004.0, 1_199_996.0, 1_200_000.0), 0.001, "even number"),
        ((2_700_000.0, 2_700_004.0, 1_199_996.0, 1_200_000.0), 0, "even number"),
        ((2_700_000.0004, 2_700_004.0, 1_199_996.0, 1_200_000.0), 0.5, "1 mm grid"),
        ((2_700_004.0, 2_700_000.0, 1_199_996.0, 1_200_000.0), 0.5, "whole number"),
        ((2_700_000.0, 2_700_004.0, 1_199_996.0, float("nan")), 0.5, "finite"),
    ],
)
def test_a_box_that_is_not_whole_cells_is_refused(box, cell_m, pattern):
    with pytest.raises(SurfacesError, match=pattern):
        class_grid(_empty(), box, cell_m)


# ---------------------------------------------- the boundary is exact, below a millimetre


def _mm_road(*points: tuple[int, int], kind: int = 16) -> dict:
    """A road through `points` given in whole mm; kind 16 is 1 m wide, a radius of 500 mm."""
    attributes = {"BELAGSART": 100, "KUNSTBAUTE": 100, "OBJEKTART": kind}
    geometry = {"type": "MultiLineString", "coordinates": [[list(p) for p in points]]}
    return {"uuid": "x", "attributes": attributes, "geometry": geometry}


def _corner_texel(*roads) -> int:
    """The class of the north-west texel (centre 500 mm in from the corner) of a 2 × 2 m box
    at 1 m, given roads in whole mm."""
    features = _empty()
    features["TLM_STRASSE"] = list(roads)
    box = (2_700_000.0, 2_700_002.0, 1_199_998.0, 1_200_000.0)
    return int(class_grid(features, box, 1.0)[0, 0])


CENTRE = (E0 + 500, N1 - 500)


def test_a_centre_beyond_a_disc_by_one_square_millimetre_is_not_on_the_line():
    """|PA|² = 250001 mm² against r² = 250000: outside; exactly r² is a tie, drawn."""
    x, y = CENTRE
    assert _corner_texel(_mm_road((x + 500, y + 1), (x + 500, y + 1))) == 0
    assert _corner_texel(_mm_road((x + 500, y + 0), (x + 500, y + 0))) == 4
    assert _corner_texel(_mm_road((x - 300, y - 400), (x - 300, y - 400))) == 4, "3-4-5: a tie"
    assert _corner_texel(_mm_road((x - 300, y - 401), (x - 300, y - 401))) == 0


def test_a_centre_a_thousandth_of_a_millimetre_beyond_a_band_is_not_on_the_line():
    """A segment 1000 mm east and 1 mm north: len² = 1000001, r² len² = 250000250000, whose
    integer square root is 500000. A centre with cross = 500001 is 500.00075 mm from the line
    (outside), one with cross = 500000 is 499.99975 mm (inside). No lattice of tie-making
    coordinates reaches these, so the reference comparison does not."""
    x, y = CENTRE
    outside = _mm_road((x - 1, y + 500), (x + 999, y + 501))
    assert _corner_texel(outside) == 0, "perpendicular distance 500.00075 mm, feet inside"
    inside = _mm_road((x - 1000, y + 499), (x, y + 500))
    assert _corner_texel(inside) == 4, "perpendicular distance 499.99975 mm"
