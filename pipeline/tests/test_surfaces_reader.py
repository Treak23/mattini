"""Brief M3-06: what `read_tlm` decides, exactly, and what it needs fiona for.

`read_tlm` (also the trees step's reader, brief M3-07) hands over the features whose 2-D
geometry meets the closed box, decided in whole millimetres with integer arithmetic: GDAL's
rectangle filter is only a pre-filter. The pinned reader test shows it on the shared
fixture; here the same decision is compared with a slow exact one (`fractions`) on random
segments, rings and boxes, and the cases a millimetre apart go through a real FileGDB: a
line 1 mm outside the box is not read, one touching it is, a diagonal through a corner is,
the same diagonal 1 mm away is not. fiona is imported inside `read_tlm` only.

Does NOT prove: that swisstopo's own file reads the same way (the real-data gate in the
brief's Findings does).
"""

import json
import subprocess
import sys
from fractions import Fraction
from itertools import pairwise
from types import SimpleNamespace

import numpy as np
import pytest
from synthetic_tlm import zipped_tlm

from mattini.surfaces import SurfacesError, _feature, _meets, read_tlm

LAYERS = {
    "TLM_BODENBEDECKUNG": ("OBJEKTART",),
    "TLM_FLIESSGEWAESSER": ("OBJEKTART", "VERLAUF"),
    "TLM_STRASSE": ("BELAGSART", "KUNSTBAUTE", "OBJEKTART"),
}
E0, N0 = 2_700_000_000, 1_200_000_000  # mm: the box's south-west corner
BOX = (2_700_000.0, 2_700_010.0, 1_200_000.0, 1_200_010.0)


# ------------------------------------------------------------------ fiona is imported late


def test_importing_the_module_does_not_import_fiona_and_reading_does(tmp_path):
    path = zipped_tlm(tmp_path, {"TLM_STRASSE": []})
    program = (
        "import sys\n"
        "def loaded(): return [m for m in sys.modules if m == 'fiona' or m.startswith('fiona.')]\n"
        "import mattini.surfaces as s\n"
        "before = loaded()\n"
        f"s.read_tlm({str(path)!r}, {{'TLM_STRASSE': ('OBJEKTART',)}}, (0.0, 1.0, 0.0, 1.0))\n"
        "print(__import__('json').dumps([before, bool(loaded())]))\n"
    )
    done = subprocess.run(  # the exit status is checked below
        [sys.executable, "-c", program], capture_output=True, text=True, timeout=120, check=False
    )
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout.splitlines()[-1]) == [[], True]


# ------------------------------------------------------- the exact decision vs a slow one


def _segment_meets(a, b, rect) -> bool:
    """Liang-Barsky with exact fractions: does the segment a-b touch the closed rectangle?"""
    (xmin, xmax, ymin, ymax), (ax, ay), (bx, by) = rect, a, b
    dx, dy = bx - ax, by - ay
    low, high = Fraction(0), Fraction(1)
    for p, q in ((-dx, ax - xmin), (dx, xmax - ax), (-dy, ay - ymin), (dy, ymax - ay)):
        if p == 0:
            if q < 0:
                return False
            continue
        r = Fraction(q, p)
        if p < 0:
            if r > high:
                return False
            low = max(low, r)
        else:
            if r < low:
                return False
            high = min(high, r)
    return low <= high


def _inside(point, rings) -> bool:
    xc, yc = point
    odd = False
    for ring in rings:
        for (x1, y1), (x2, y2) in pairwise(ring):
            if (y1 > yc) != (y2 > yc):
                odd ^= xc < x1 + Fraction(yc - y1, y2 - y1) * (x2 - x1)
    return odd


def _reference(parts, rect, polygon) -> bool:
    for part in parts:
        pairs = list(pairwise(part)) or [(part[0], part[0])]
        if any(_segment_meets(a, b, rect) for a, b in pairs):
            return True
    return polygon and _inside((rect[0], rect[2]), parts)


def _arrays(parts) -> list[np.ndarray]:
    return [np.array([[E0 + x, N0 + y] for x, y in part], dtype=np.int64) for part in parts]


@pytest.mark.parametrize("seed", range(6))
def test_the_integer_decision_is_the_exact_one_for_lines(seed):
    rng = np.random.default_rng(seed)
    box = (E0 + 2, E0 + 5, N0 + 1, N0 + 4)
    rect = (2, 5, 1, 4)
    hits = 0
    for _ in range(400):
        count = int(rng.integers(1, 4))
        parts = [
            [tuple(int(v) for v in rng.integers(-3, 10, size=2)) for _ in range(count + 1)]
            for _ in range(int(rng.integers(1, 3)))
        ]
        expected = _reference(parts, rect, polygon=False)
        hits += expected
        assert _meets(_arrays(parts), box, polygon=False) == expected, parts
    assert 40 < hits < 360, "the cases are neither all hits nor all misses"


@pytest.mark.parametrize("seed", range(6))
def test_the_integer_decision_is_the_exact_one_for_polygons(seed):
    rng = np.random.default_rng(100 + seed)
    box = (E0 + 3, E0 + 6, N0 + 3, N0 + 5)
    rect = (3, 6, 3, 5)
    hits = inside = 0
    for _ in range(400):
        rings = []
        for _ in range(int(rng.integers(1, 3))):
            ring = [tuple(int(v) for v in rng.integers(-2, 12, size=2)) for _ in range(3)]
            rings.append([*ring, ring[0]])
        expected = _reference(rings, rect, polygon=True)
        hits += expected
        inside += expected and not any(
            _segment_meets(a, b, rect) for ring in rings for a, b in pairwise(ring)
        )
        assert _meets(_arrays(rings), box, polygon=True) == expected, rings
    assert 40 < hits < 360, "the cases are neither all hits nor all misses"
    assert inside >= 5, "some polygons hold the box without a boundary touching it"


def test_a_point_a_segment_of_length_zero_and_a_corner_touch():
    box = (E0, E0 + 4, N0, N0 + 4)
    assert _meets(_arrays([[(4, 4)]]), box, polygon=False), "the corner itself"
    assert not _meets(_arrays([[(5, 4)]]), box, polygon=False)
    assert _meets(_arrays([[(-1, 9), (9, -1)]]), box, polygon=False), "through the corner"
    assert not _meets(_arrays([[(0, 9), (9, 0)]]), box, polygon=False), "1 mm beyond the corner"


# ---------------------------------------------------- a real FileGDB, a millimetre apart


def _line(uuid: str, *points: tuple[int, int]) -> dict:
    """A road through `points` (mm from the box's south-west corner)."""
    attributes = {"BELAGSART": 100, "KUNSTBAUTE": 100, "OBJEKTART": 10}
    coordinates = [[[E0 + x, N0 + y] for x, y in points]]
    geometry = {"type": "MultiLineString", "coordinates": coordinates}
    return {"uuid": uuid, "attributes": attributes, "geometry": geometry}


def _polygon(uuid: str, *rings) -> dict:
    coordinates = [[[[E0 + x, N0 + y] for x, y in ring] for ring in rings]]
    return {
        "uuid": uuid,
        "attributes": {"OBJEKTART": 1},
        "geometry": {"type": "MultiPolygon", "coordinates": coordinates},
    }


def _read(tmp_path, roads=(), covers=()) -> dict:
    path = zipped_tlm(
        tmp_path,
        {
            "TLM_STRASSE": list(roads),
            "TLM_BODENBEDECKUNG": list(covers),
            "TLM_FLIESSGEWAESSER": [],
        },
    )
    found = read_tlm(path, LAYERS, BOX)
    return {layer: [f["uuid"] for f in features] for layer, features in found.items()}


def test_lines_a_millimetre_outside_are_not_read_and_touching_ones_are(tmp_path):
    ten = 10_000
    read = _read(
        tmp_path,
        roads=[
            _line("{A-east-outside}", (ten + 1, -5000), (ten + 1, 15000)),
            _line("{B-east-touching}", (ten, -5000), (ten, 15000)),
            _line("{C-south-outside}", (-5000, -1), (15000, -1)),
            _line("{D-south-touching}", (-5000, 0), (15000, 0)),
            _line("{E-corner-diagonal}", (ten - 1000, ten + 1000), (ten + 1000, ten - 1000)),
            _line("{F-corner-diagonal-1mm-out}", (ten - 999, ten + 1000), (ten + 1001, ten - 1000)),
            _line("{G-inside}", (3000, 3000), (4000, 4000)),
            _line("{H-crossing}", (-3000, 5000), (13000, 5000)),
            _line("{I-bounding-box-only}", (-2000, 12000), (12000, 22000)),
        ],
    )
    assert read["TLM_STRASSE"] == [
        "{B-east-touching}",
        "{D-south-touching}",
        "{E-corner-diagonal}",
        "{G-inside}",
        "{H-crossing}",
    ]


def test_polygons_are_read_when_they_touch_or_hold_the_box_and_not_a_millimetre_short(tmp_path):
    def square(a, b, c, d):
        return [(a, b), (c, b), (c, d), (a, d), (a, b)]

    ten = 10_000
    read = _read(
        tmp_path,
        covers=[
            _polygon("{A-touching-an-edge}", square(ten, 2000, ten + 5000, 8000)),
            _polygon("{B-a-millimetre-short}", square(ten + 1, 2000, ten + 5000, 8000)),
            _polygon("{C-holds-the-box}", square(-5000, -5000, 15000, 15000)),
            _polygon(
                "{D-in-a-hole}",
                square(-5000, -5000, 15000, 15000),
                square(-1, -1, ten + 1, ten + 1),
            ),
            _polygon(
                "{E-hole-touching-the-box}",
                square(-5000, -5000, 15000, 15000),
                square(1, 1, 9000, 9000),
            ),
        ],
    )
    assert read["TLM_BODENBEDECKUNG"] == [
        "{A-touching-an-edge}",
        "{C-holds-the-box}",
        "{E-hole-touching-the-box}",
    ]


def test_a_uuid_twice_in_a_layer_is_refused(tmp_path):
    road = _line("{TWICE}", (1000, 1000), (2000, 2000))
    other = _line("{TWICE}", (3000, 3000), (4000, 4000))
    path = zipped_tlm(tmp_path, {"TLM_STRASSE": [road, other]})
    with pytest.raises(SurfacesError, match="UUID twice"):
        read_tlm(path, {"TLM_STRASSE": LAYERS["TLM_STRASSE"]}, BOX)


def test_a_file_that_is_not_there_or_not_a_zip_is_refused_naming_it(tmp_path):
    with pytest.raises(SurfacesError, match="absent.gdb.zip"):
        read_tlm(tmp_path / "absent.gdb.zip", LAYERS, BOX)
    bad = tmp_path / "bad.gdb.zip"
    bad.write_bytes(b"not a zip")
    with pytest.raises(SurfacesError, match="bad.gdb.zip"):
        read_tlm(bad, LAYERS, BOX)


# ------------------------------------------------- a feature as fiona hands it over


def _fiona_feature(properties, kind, coordinates):
    geometry = None if kind is None else SimpleNamespace(type=kind, coordinates=coordinates)
    return SimpleNamespace(properties=properties, geometry=geometry)


BOX_MM = (E0, E0 + 10_000, N0, N0 + 10_000)
ROAD = ("BELAGSART", "OBJEKTART")


def _metres(*points):
    return [(E0 / 1000 + x / 1000, N0 / 1000 + y / 1000, 1500.0) for x, y in points]


def test_a_single_line_or_polygon_is_handed_over_as_its_multi_form():
    props = {"UUID": "{X}", "BELAGSART": 100, "OBJEKTART": 10}
    line = _feature(
        _fiona_feature(props, "LineString", _metres((1000, 1000), (2000, 2000))), "L", ROAD, BOX_MM
    )
    assert line["geometry"] == {
        "type": "MultiLineString",
        "coordinates": [[[E0 + 1000, N0 + 1000], [E0 + 2000, N0 + 2000]]],
    }
    ring = _metres((1000, 1000), (3000, 1000), (3000, 3000), (1000, 1000))
    polygon = _feature(_fiona_feature(props, "Polygon", [ring]), "L", ROAD, BOX_MM)
    assert polygon["geometry"]["type"] == "MultiPolygon"
    assert polygon["geometry"]["coordinates"] == [
        [
            [
                [E0 + 1000, N0 + 1000],
                [E0 + 3000, N0 + 1000],
                [E0 + 3000, N0 + 3000],
                [E0 + 1000, N0 + 1000],
            ]
        ]
    ]
    assert all(type(v) is int for v in polygon["geometry"]["coordinates"][0][0][0])


@pytest.mark.parametrize(
    ("feature", "pattern"),
    [
        (_fiona_feature({"BELAGSART": 100, "OBJEKTART": 10}, "LineString", []), "without a UUID"),
        (
            _fiona_feature({"UUID": "", "BELAGSART": 100, "OBJEKTART": 10}, "LineString", []),
            "without a UUID",
        ),
        (
            _fiona_feature({"UUID": "{X}", "BELAGSART": None, "OBJEKTART": 10}, "LineString", []),
            "not an integer",
        ),
        (
            _fiona_feature({"UUID": "{X}", "BELAGSART": 100.5, "OBJEKTART": 10}, "LineString", []),
            "not an integer",
        ),
        (_fiona_feature({"UUID": "{X}", "BELAGSART": 100}, "LineString", []), "OBJEKTART"),
        (
            _fiona_feature({"UUID": "{X}", "BELAGSART": 100, "OBJEKTART": 10}, None, None),
            "no geometry",
        ),
        (
            _fiona_feature({"UUID": "{X}", "BELAGSART": 100, "OBJEKTART": 10}, "Point", (1.0, 2.0)),
            "neither a line",
        ),
        (
            _fiona_feature(
                {"UUID": "{X}", "BELAGSART": 100, "OBJEKTART": 10}, "MultiLineString", [[]]
            ),
            "empty part",
        ),
    ],
)
def test_a_feature_that_cannot_be_handed_over_is_refused_naming_the_layer(feature, pattern):
    with pytest.raises(SurfacesError, match=pattern) as refusal:
        _feature(feature, "TLM_STRASSE", ROAD, BOX_MM)
    assert "TLM_STRASSE" in str(refusal.value)


def test_a_vertex_off_the_grid_or_not_finite_is_refused_naming_the_layer_and_the_uuid():
    props = {"UUID": "{OFF}", "BELAGSART": 100, "OBJEKTART": 10}
    for bad in (0.0004, float("nan"), float("inf")):
        points = [
            (E0 / 1000 + 1.0 + bad, N0 / 1000 + 1.0, 0.0),
            (E0 / 1000 + 2.0, N0 / 1000 + 2.0, 0.0),
        ]
        with pytest.raises(SurfacesError, match=r"TLM_STRASSE \{OFF\}.*1 mm grid"):
            _feature(_fiona_feature(props, "LineString", points), "TLM_STRASSE", ROAD, BOX_MM)


def test_a_vertex_within_a_millionth_of_a_metre_of_the_grid_is_snapped():
    props = {"UUID": "{NEAR}", "BELAGSART": 100, "OBJEKTART": 10}
    points = [
        (E0 / 1000 + 1.0 + 4e-7, N0 / 1000 + 1.0, 0.0),
        (E0 / 1000 + 2.0, N0 / 1000 + 2.0 - 4e-7, 0.0),
    ]
    made = _feature(_fiona_feature(props, "LineString", points), "TLM_STRASSE", ROAD, BOX_MM)
    assert made["geometry"]["coordinates"] == [[[E0 + 1000, N0 + 1000], [E0 + 2000, N0 + 2000]]]
