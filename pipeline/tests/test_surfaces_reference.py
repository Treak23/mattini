"""Brief M3-06: the vectorised class grid equals the rule written out slowly, on random features.

The step finds each texel's class with integer interval arithmetic over whole rows. This file
computes the same classes the way SPEC §8 *The surfaces* words them, texel by texel with
`fractions.Fraction` and no shared code: a texel is on a line when the exact squared distance
from its centre to the nearest point of a segment is at most the square of half the width,
and inside a feature when an odd number of its edges satisfy (y1 > yc) != (y2 > yc) with xc
strictly left of the crossing. The random features are drawn on a 50 mm lattice, so that
texel centres fall exactly on lines' band edges, discs, polygon edges and vertices (ties) in
many of the cases; a tie handled the other way round differs from the reference somewhere.

Does NOT prove: that the reference is the rule (the shared fixture's pinned classes do:
test_surfaces_fixture.py), nor that the real data reads as this (the step's comparison with
config/surfaces.json does, on the owner's run).
"""

import random
from fractions import Fraction
from itertools import pairwise

import numpy as np
import pytest

from mattini import surfaces
from mattini.surfaces import STREAM_WIDTH_MM, WIDTH_MM, class_grid

E0, N1 = 2_700_000, 1_200_000  # the box's north-west corner, whole metres, in mm below
LATTICE = 50  # mm
WIDTHS = sorted(WIDTH_MM.items())


def _point(rng, width_mm: int, height_mm: int, reach_mm: int) -> list[int]:
    return [
        E0 + rng.randrange(-reach_mm, width_mm + reach_mm + 1, LATTICE),
        N1 - rng.randrange(-reach_mm, height_mm + reach_mm + 1, LATTICE),
    ]


def _random_features(seed: int, width_mm: int, height_mm: int) -> dict:
    rng = random.Random(seed)
    features = {"TLM_STRASSE": [], "TLM_BODENBEDECKUNG": [], "TLM_FLIESSGEWAESSER": []}
    reach = 1500
    for number in range(rng.randrange(2, 6)):
        parts = [
            [_point(rng, width_mm, height_mm, reach) for _ in range(rng.randrange(2, 5))]
            for _ in range(rng.randrange(1, 3))
        ]
        kind, _ = rng.choice(WIDTHS)
        features["TLM_STRASSE"].append(
            {
                "uuid": f"road-{number}",
                "attributes": {
                    "BELAGSART": rng.choice([100, 200, 200, 999997]),
                    "KUNSTBAUTE": rng.choice([100, 100, 200, 1000]),
                    "OBJEKTART": kind,
                },
                "geometry": {"type": "MultiLineString", "coordinates": parts},
            }
        )
    for number in range(rng.randrange(0, 3)):
        parts = [[_point(rng, width_mm, height_mm, reach) for _ in range(rng.randrange(2, 4))]]
        features["TLM_FLIESSGEWAESSER"].append(
            {
                "uuid": f"stream-{number}",
                "attributes": {"OBJEKTART": 4, "VERLAUF": rng.choice([100, 500, 400])},
                "geometry": {"type": "MultiLineString", "coordinates": parts},
            }
        )
    for number in range(rng.randrange(1, 4)):
        polygons = []
        for _ in range(rng.randrange(1, 3)):
            rings = []
            for _ in range(rng.randrange(1, 3)):
                ring = [_point(rng, width_mm, height_mm, reach) for _ in range(rng.randrange(3, 7))]
                rings.append([*ring, ring[0]])
            polygons.append(rings)
        features["TLM_BODENBEDECKUNG"].append(
            {
                "uuid": f"cover-{number}",
                "attributes": {"OBJEKTART": rng.choice([1, 2, 3, 4, 5, 10, 12])},
                "geometry": {"type": "MultiPolygon", "coordinates": polygons},
            }
        )
    return features


def _distance2_to_segment(p, a, b) -> Fraction:
    """The exact squared distance from p to the closest point of the segment a-b."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    length2 = dx * dx + dy * dy
    if length2 == 0:
        return Fraction((p[0] - a[0]) ** 2 + (p[1] - a[1]) ** 2)
    t = Fraction((p[0] - a[0]) * dx + (p[1] - a[1]) * dy, length2)
    t = min(Fraction(1), max(Fraction(0), t))
    cx, cy = a[0] + t * dx, a[1] + t * dy
    return (p[0] - cx) ** 2 + (p[1] - cy) ** 2


def _inside(p, polygons) -> bool:
    """Even-odd over all the rings of a feature, by the half-open crossing rule."""
    xc, yc = p
    odd = False
    for rings in polygons:
        for ring in rings:
            for (x1, y1), (x2, y2) in pairwise(ring):
                if (y1 > yc) != (y2 > yc):
                    crossing = x1 + Fraction(yc - y1, y2 - y1) * (x2 - x1)
                    odd ^= xc < crossing
    return odd


def _reference(features: dict, box: tuple, cell_mm: int) -> np.ndarray:
    e_min, e_max, n_min, n_max = box
    columns, rows = (e_max - e_min) // cell_mm, (n_max - n_min) // cell_mm
    grid = np.zeros((rows, columns), dtype=np.uint8)

    def on_line(p, parts, radius_mm) -> bool:
        return any(
            _distance2_to_segment(p, a, b) <= radius_mm**2
            for part in parts
            for a, b in pairwise(part)
        )

    for r in range(rows):
        for c in range(columns):
            p = (e_min + cell_mm // 2 + c * cell_mm, n_max - cell_mm // 2 - r * cell_mm)
            best = 0
            for f in features["TLM_BODENBEDECKUNG"]:
                kind = f["attributes"]["OBJEKTART"]
                code = 1 if kind in (1, 2, 3, 4) else 2 if kind in (5, 10) else 0
                if code > best and _inside(p, f["geometry"]["coordinates"]):
                    best = code
            for f in features["TLM_FLIESSGEWAESSER"]:
                a = f["attributes"]
                if (
                    a["OBJEKTART"] == 4
                    and a["VERLAUF"] in (100, 500)
                    and best < 2
                    and on_line(p, f["geometry"]["coordinates"], STREAM_WIDTH_MM // 2)
                ):
                    best = 2
            for f in features["TLM_STRASSE"]:
                a = f["attributes"]
                code = {100: 4, 200: 3}.get(a["BELAGSART"], 0)
                if (
                    code > best
                    and a["KUNSTBAUTE"] not in (300, 400, 700, 1000, 1100, 1200, 1400)
                    and a["OBJEKTART"] in WIDTH_MM
                    and on_line(p, f["geometry"]["coordinates"], WIDTH_MM[a["OBJEKTART"]] // 2)
                ):
                    best = code
            grid[r, c] = best
    return grid


@pytest.mark.parametrize("seed", range(40))
@pytest.mark.parametrize("cell_m", [0.2, 0.5, 1.0])
def test_the_class_grid_equals_the_rule_written_out(seed, cell_m):
    cell_mm = round(cell_m * 1000)
    width_mm, height_mm = 12 * cell_mm * 2, 10 * cell_mm * 2  # 24 × 20 texels
    box_mm = (E0, E0 + width_mm, N1 - height_mm, N1)
    features = _random_features(seed * 7 + round(cell_m * 10), width_mm, height_mm)
    expected = _reference(features, box_mm, cell_mm)
    box = tuple(v / 1000 for v in box_mm)
    assert np.array_equal(class_grid(features, box, cell_m), expected)


def test_the_random_cases_draw_every_class_and_many_ties():
    """The reference cases are not vacuous: all five classes occur, and the lattice puts
    texel centres exactly on band edges (a centre at exactly half a width from a line)."""
    seen = np.zeros(5, dtype=int)
    exact = 0
    for seed in range(40):
        features = _random_features(seed * 7 + 5, 12_000, 10_000)
        grid = class_grid(
            features, (E0 / 1000, (E0 + 12_000) / 1000, (N1 - 10_000) / 1000, N1 / 1000), 0.5
        )
        seen += np.bincount(grid.ravel(), minlength=5)
        for f in features["TLM_STRASSE"]:
            radius = WIDTH_MM[f["attributes"]["OBJEKTART"]] // 2
            for part in f["geometry"]["coordinates"]:
                for a, b in pairwise(part):
                    for r in range(20):
                        for c in range(24):
                            p = (E0 + 250 + c * 500, N1 - 250 - r * 500)
                            exact += _distance2_to_segment(p, a, b) == radius**2
    assert (seen > 0).all(), seen
    assert exact >= 20, exact


def test_the_module_keeps_the_widths_design_pinned():
    """The width table is the rule's data (SPEC §8): a mutation of it fails this and the
    fixture's pinned classes alike."""
    assert surfaces.WIDTH_MM == {
        8: 10000,
        9: 6000,
        10: 4000,
        11: 3000,
        15: 2000,
        16: 1000,
        17: 1000,
        18: 2000,
        20: 8000,
    }
    assert surfaces.STREAM_WIDTH_MM == 2000
    assert surfaces.NOT_DRAWN == {300, 400, 700, 1000, 1100, 1200, 1400}
