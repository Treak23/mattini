"""A scalar oracle for the roof colour rule, written apart from `mattini.roofs` (brief M3-05).

The vectorised rule is checked against this: plain Python integers in units of 0.1 mm, the
buildings step's selection (the bounding-box centre in the area, the west and south edges
in), the orientation by the signed volume (an exact integer divergence sum), the roof test
by the integer normal, every pixel centre of the building's roofs' bounding box tested
against each roof triangle by its three integer edge functions, and the lower median from a
sorted list. Slow, and meant to be: it shares no line of the code under test but the
buildings fixture's world.

`oracle(features, rasters)` gives uuid -> (roof, roof_pixels) for the selected buildings of
the buildings fixture's area; a building without roof pixels is (None, 0).
"""

from pathlib import Path

from mattini.world import load_world

REPO = Path(__file__).resolve().parents[2]
WORLD = REPO / "tests" / "shared" / "buildings_fixture" / "world.json"
AREA = "fixture"
UNITS = 10000  # 0.1 mm per metre


def _units(value: float) -> int:
    return round(value * UNITS)


def inside_or_on(plan, e: int, n: int) -> bool:
    """Whether the point (e, n) is inside or on the counter-clockwise triangle `plan`."""
    for (pe, pn), (qe, qn) in ((plan[0], plan[1]), (plan[1], plan[2]), (plan[2], plan[0])):
        if (qe - pe) * (n - pn) - (qn - pn) * (e - pe) < 0:
            return False
    return True


def oracle(features, rasters) -> dict[str, tuple]:
    """uuid -> (roof, roof_pixels) for the selected buildings, in plain Python integers."""
    world = load_world(WORLD)
    e_min, e_max, n_min, n_max = world.area(AREA)
    result = {}
    for feature in features:
        points = [tuple(round(v * 1000) for v in p[:2]) for t in feature["triangles"] for p in t]
        centre_e = (min(p[0] for p in points) + max(p[0] for p in points)) / 2000
        centre_n = (min(p[1] for p in points) + max(p[1] for p in points)) / 2000
        if not (e_min <= centre_e < e_max and n_min <= centre_n < n_max):
            continue
        triangles = [
            tuple((_units(e), _units(n), _units(h)) for e, n, h in t) for t in feature["triangles"]
        ]
        # signed volume by the divergence theorem on the first vertex's differences (integers)
        origin = triangles[0][0]
        volume = 0
        for a, b, c in triangles:
            ra, rb, rc = [tuple(p[k] - origin[k] for k in range(3)) for p in (a, b, c)]
            volume += (
                ra[0] * (rb[1] * rc[2] - rb[2] * rc[1])
                + ra[1] * (rb[2] * rc[0] - rb[0] * rc[2])
                + ra[2] * (rb[0] * rc[1] - rb[1] * rc[0])
            )
        if volume < 0:
            triangles = [(a, c, b) for a, b, c in triangles]
        plans = []
        for a, b, c in triangles:
            u = [b[k] - a[k] for k in range(3)]
            v = [c[k] - a[k] for k in range(3)]
            nrm = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
            if nrm[2] > 0 and 4 * nrm[2] ** 2 >= nrm[0] ** 2 + nrm[1] ** 2 + nrm[2] ** 2:
                plans.append(((a[0], a[1]), (b[0], b[1]), (c[0], c[1])))
        values = []
        corners = [point for plan in plans for point in plan]
        if corners:  # only the pixels that can be inside: the roofs' bounding box, a pixel wider
            low_e, high_e = min(c[0] for c in corners) - 1000, max(c[0] for c in corners) + 1000
            low_n, high_n = min(c[1] for c in corners) - 1000, max(c[1] for c in corners) + 1000
            for west_dm, north_dm, pixels in rasters:
                rows, columns = pixels.shape[:2]
                for j in range(rows):
                    n = north_dm * 1000 - 500 - 1000 * j
                    if n > high_n:
                        continue
                    if n < low_n:
                        break
                    for i in range(columns):
                        e = west_dm * 1000 + 500 + 1000 * i
                        if low_e <= e <= high_e and any(inside_or_on(p, e, n) for p in plans):
                            values.append(tuple(int(x) for x in pixels[j, i]))
        if not values:
            result[feature["uuid"]] = (None, 0)
            continue
        colour = ""
        for channel in range(3):
            ordered = sorted(v[channel] for v in values)
            colour += f"{ordered[(len(ordered) - 1) // 2]:02x}"
        result[feature["uuid"]] = (colour, len(values))
    return result
