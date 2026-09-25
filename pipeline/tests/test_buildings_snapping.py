"""The snapping, where it changes the outcome (brief M2-04; docs/SPEC.md §8 *Snapping*).

The pinned noise test moves every reading of a corner by the same last bit, which the
float32 rounding absorbs anyway: a build that checked the grid but kept the raw values
passed it (measured at M2-04, lesson 34). These tests use noise that only the snapping
removes: one reading of a corner off by a nanometre, which must still weld with the
others; and a building whose bounding-box centre lies exactly on the area's west edge
once snapped, one nanometre west of it as read. On the real village the snapping moves
2'120'072 of 2'259'594 coordinates by at most 1.9e-9 m, and without it six float32
values of one chunk come out one step off (measured, Findings).

Does NOT prove: that the owner's Windows PC reads the same noise (its GDAL is its wheel's;
the step's comparison with config/buildings.json says so if the chunks differ).
"""

from test_buildings_rules import FIXTURE_WORLD, _tetra

from mattini.buildings import build_chunks
from mattini.world import load_world

NANOMETRE = 1e-9  # two 64-bit steps at E 2.65e6: far inside the 1e-6 m tolerance


def _with_noise(building: dict, triangle: int, corner: int, de: float) -> dict:
    """`building` with one reading of one corner moved east by `de` metres."""
    triangles = [tuple(t) for t in building["triangles"]]
    points = list(triangles[triangle])
    e, n, h = points[corner]
    points[corner] = (e + de, n, h)
    triangles[triangle] = tuple(points)
    return dict(building, triangles=triangles)


def test_one_noisy_reading_of_a_corner_still_welds():
    world = load_world(FIXTURE_WORLD)
    clean = _tetra("{A}")
    noisy = _with_noise(clean, 1, 0, -NANOMETRE)  # corner O as the second triangle reads it
    assert noisy["triangles"][1][0] != clean["triangles"][0][0]  # the data shows the noise
    assert build_chunks([noisy], world, "fixture") == build_chunks([clean], world, "fixture")


def test_noise_does_not_move_a_centre_off_the_west_edge():
    world = load_world(FIXTURE_WORLD)
    west = 2650900.0  # the fixture area's e_min
    clean = _tetra("{W}", e=west - 1.5, n=1149990.0)  # E 2650898.5 to 2650901.5
    noisy = dict(
        clean,
        triangles=[
            tuple((e - NANOMETRE if e == west - 1.5 else e, n, h) for e, n, h in t)
            for t in clean["triangles"]
        ],
    )
    es = [p[0] for t in noisy["triangles"] for p in t]
    assert (min(es) + max(es)) / 2 < west  # unsnapped, the centre is west of the area
    (chunk,) = build_chunks([noisy], world, "fixture")
    assert chunk == build_chunks([clean], world, "fixture")[0]
