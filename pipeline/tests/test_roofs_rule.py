"""The roof colour rule, beyond the pinned fixture (brief M3-05; SPEC §8 *Roof colours*).

Four things the fixture does not fix by itself:

- Exact arithmetic where 64 bits run out. A roof triangle's test squares the components of
  its normal, which reach 10^29 in units of 0.1 mm for a triangle a few hundred metres wide;
  a wrong 64-bit version passes every house and fails there.
- Exact counts at a pixel centre on an edge or a vertex, in a case worked out by hand: a right
  triangle of 11 × 11 pixel centres (66 inside or on, 36 strictly inside), a roof of three
  triangles that share edges (each pixel once for the building: 66, not 70), and an edge
  moved 1 mm inward, which takes the 10 centres on it out.
- The vectorised rule against a scalar oracle written separately, in plain Python integers
  with sorted lists: the fixture's buildings moved and turned at random (so that edges cross
  pixel centres at all angles), under noise pixels cut into windows at random.
- The photo's rasters: any order or cutting of the same pixels gives the same colours; an
  overlap is refused (a pixel in two rasters would count twice); a raster that is not RGB
  8-bit is refused; no photo at all gives no colour and no refusal.

Does NOT prove: that the oracle and the code are not wrong the same way (the fixture, which
design derived twice, and the real village's `expected_sha256` are the other checks); that
the colours look right.
"""

import json
import math
import random
from itertools import pairwise
from pathlib import Path

import numpy as np
import pytest
from roofs_oracle import oracle

from mattini.buildings import BuildingsError
from mattini.roofs import RoofsError, _lower_median, _roof_triangle, build_roof_chunks
from mattini.world import load_world

REPO = Path(__file__).resolve().parents[2]
SHARED = REPO / "tests" / "shared"
WORLD = SHARED / "buildings_fixture" / "world.json"
AREA = "fixture"
WEST_DM, NORTH_DM = 26509000, 11500000  # E 2650900.0, N 1150000.0: the area's north-west


def _fixture_features() -> list[dict]:
    source = json.loads((SHARED / "roofs_fixture" / "source.json").read_text(encoding="utf-8"))
    return [
        {
            "uuid": f["uuid"],
            "objektart": f["objektart"],
            "triangles": [tuple(tuple(p) for p in t) for t in f["triangles"]],
        }
        for f in source["features"]
    ]


def _chunks(features, rasters):
    return build_roof_chunks(features, load_world(WORLD), AREA, iter(rasters))


def _by_uuid(chunks) -> dict[str, tuple]:
    return {b["uuid"]: (b["roof"], b["roof_pixels"]) for c in chunks for b in c["buildings"]}


# --------------------------------------------------------------------------- the triangle


def test_a_roof_triangle_at_the_slope_limit_in_numbers_beyond_64_bits():
    """H = s·E over a 2 km triangle: n = (−s·L², 0, L²), roof exactly when s² <= 3. The squares
    are 10^29 and overflow int64, which wraps them to something else."""
    length = 20_000_000  # 2 km in units of 0.1 mm
    for s_num, s_den, roof in (
        (17, 10, True),
        (173, 100, True),
        (174, 100, False),
        (18, 10, False),
    ):
        a, b, c = (0, 0, 0), (length, 0, length * s_num // s_den), (0, length, 0)
        # (a, b, c) is counter-clockwise in plan: n_H = L² > 0
        assert (_roof_triangle(a, b, c) is not None) == roof, (s_num, s_den)
    assert 17 * 17 < 300 and 174 * 174 > 30000 * 1  # the cases straddle s² = 3


@pytest.mark.parametrize(
    ("triangle", "roof"),
    [
        (((0, 0, 0), (1000, 0, 0), (0, 1000, 0)), True),  # flat, wound counter-clockwise
        (((0, 0, 0), (0, 1000, 0), (1000, 0, 0)), False),  # the floor of it: facing down
        (((0, 0, 0), (1000, 0, 0), (1000, 0, 1000)), False),  # a vertical wall: n_H = 0
        (((0, 0, 0), (1000, 0, 600), (0, 1000, 0)), True),  # n = (−600000, 0, 1000000)
        (((0, 0, 0), (1000, 0, 1900), (0, 1000, 0)), False),  # steeper than 60 degrees
        (((0, 0, 0), (1000, 0, 1732), (0, 1000, 0)), True),  # tan 1.732 < the root of 3
        (((0, 0, 0), (1000, 0, 1733), (0, 1000, 0)), False),  # tan 1.733 > the root of 3
        (((0, 0, 0), (1000, 1000, 0), (2000, 2000, 0)), False),  # no area
    ],
)
def test_the_roof_triangle_rule(triangle, roof):
    found = _roof_triangle(*triangle)
    assert (found is not None) == roof
    if roof:
        assert found == tuple((p[0], p[1]) for p in triangle)  # its plan projection


# --------------------------------------------------------------------------- worked counts


def _pixel(i: int, j: int) -> tuple[float, float]:
    """The (E, N) of the centre of pixel (row j, column i) of the raster at E 2650900.0,
    N 1150000.0, in metres on the 1 mm grid."""
    return (
        round(2650900.0 + 0.05 + 0.1 * i, 3),
        round(1150000.0 - 0.05 - 0.1 * j, 3),
    )


def _raster() -> np.ndarray:
    """200 × 200 pixels, every pixel a different colour: R = i, G = j, B = (i + j) % 251."""
    rows, columns = np.mgrid[0:200, 0:200]
    return np.stack([columns, rows, (rows + columns) % 251], axis=-1).astype(np.uint8)


def _pyramid(corners, apex_pixel, height, floor=1500.0) -> list[dict]:
    """A closed flat pyramid: the floor triangle on the three corner pixels' centres (pixel
    (i, j) of `corners`), the apex above pixel `apex_pixel`, as one feature."""
    (a, b, c) = [_pixel(i, j) + (floor,) for i, j in corners]
    apex = _pixel(*apex_pixel) + (floor + height,)
    triangles = [(a, b, c), (b, a, apex), (c, b, apex), (a, c, apex)]
    return [
        {"uuid": "{00000000-0000-4000-8000-000000000001}", "objektart": "x", "triangles": triangles}
    ]


def _expected_lattice(corners_ok: set) -> tuple[str, int]:
    """The lower median and the count of the pixels in `corners_ok` (a set of (i, j)),
    written out by hand: sorted per channel, the element at (n − 1) // 2."""
    values = [(i, j, (i + j) % 251) for i, j in corners_ok]
    colour = ""
    for channel in range(3):
        ordered = sorted(v[channel] for v in values)
        colour += f"{ordered[(len(ordered) - 1) // 2]:02x}"
    return colour, len(values)


RIGHT_TRIANGLE = {(100 + di, 100 + dj) for di in range(11) for dj in range(11 - di)}  # 66


def test_a_right_triangle_roof_counts_its_boundary_once_per_pixel():
    features = _pyramid([(100, 100), (110, 100), (100, 110)], (103, 103), 0.3)
    got = _by_uuid(_chunks(features, [(WEST_DM, NORTH_DM, _raster())]))
    assert got == {features[0]["uuid"]: _expected_lattice(RIGHT_TRIANGLE)}
    assert len(RIGHT_TRIANGLE) == 66  # 11 + 10 + ... + 1: the lattice points with i + j <= 10


def _moved_vertex(features: list[dict], pixel: tuple[int, int], de: float) -> list[dict]:
    """The features with every vertex over the centre of `pixel` moved `de` metres east."""
    at = _pixel(*pixel)
    return [
        {
            **feature,
            "triangles": [
                tuple((e + de, n, h) if (e, n) == at else (e, n, h) for e, n, h in triangle)
                for triangle in feature["triangles"]
            ],
        }
        for feature in features
    ]


def test_an_edge_moved_one_millimetre_inward_takes_its_ten_centres_out():
    """The vertex at pixel (110, 100) moves 1 mm west: the hypotenuse's centres, (di, 10 − di)
    for di = 1 … 10, are outside the roof (the vertex's own among them)."""
    features = _moved_vertex(
        _pyramid([(100, 100), (110, 100), (100, 110)], (103, 103), 0.3), (110, 100), -0.001
    )
    inside = {(i, j) for i, j in RIGHT_TRIANGLE if not (i - 100 >= 1 and i - 100 + j - 100 == 10)}
    got = _by_uuid(_chunks(features, [(WEST_DM, NORTH_DM, _raster())]))
    assert got == {features[0]["uuid"]: _expected_lattice(inside)}
    assert len(inside) == 56


def test_an_edge_moved_one_millimetre_outward_changes_nothing():
    features = _moved_vertex(
        _pyramid([(100, 100), (110, 100), (100, 110)], (103, 103), 0.3), (110, 100), 0.001
    )
    got = _by_uuid(_chunks(features, [(WEST_DM, NORTH_DM, _raster())]))
    assert got == {features[0]["uuid"]: _expected_lattice(RIGHT_TRIANGLE)}


def test_a_solid_turned_upside_down_has_its_old_floor_as_its_roof():
    """The apex below the floor: the buildings step reverses the solid by its signed volume,
    so the floor now faces up and is the one roof triangle (its pixels the same 66), and the
    three faces to the apex face down."""
    features = _pyramid([(100, 100), (110, 100), (100, 110)], (103, 103), -0.3)
    got = _by_uuid(_chunks(features, [(WEST_DM, NORTH_DM, _raster())]))
    assert got == {features[0]["uuid"]: _expected_lattice(RIGHT_TRIANGLE)}


# --------------------------------------------------------------------------- the oracle


def _moved(features, seed: int) -> list[dict]:
    """The features turned by a random angle about (2651000, 1150000) and moved by a random
    vector, snapped back to the storage grid (E and N to 1 mm, H to 0.1 mm)."""
    rng = random.Random(seed)
    angle = rng.uniform(0.02, 0.9)
    shift_e, shift_n = rng.uniform(-3, 3), rng.uniform(-3, 3)
    cos, sin = math.cos(angle), math.sin(angle)
    moved = []
    for feature in features:
        triangles = []
        for triangle in feature["triangles"]:
            points = []
            for e, n, h in triangle:
                de, dn = e - 2651000.0, n - 1150000.0
                points.append(
                    (
                        round(2651000.0 + cos * de - sin * dn + shift_e, 3),
                        round(1150000.0 + sin * de + cos * dn + shift_n, 3),
                        round(h, 4),
                    )
                )
            triangles.append(tuple(points))
        moved.append({**feature, "triangles": triangles})
    return moved


def _windows(seed: int) -> list[tuple[int, int, np.ndarray]]:
    """Noise pixels over the 200 m × 100 m area, cut into non-overlapping windows at random
    lines (their pixels are the same whatever the cutting)."""
    rng = random.Random(seed * 7 + 1)
    noise = np.random.RandomState(seed).randint(0, 256, size=(1000, 2000, 3)).astype(np.uint8)
    cuts_c = sorted({0, 2000} | {rng.randrange(100, 1900) for _ in range(rng.randrange(1, 4))})
    cuts_r = sorted({0, 1000} | {rng.randrange(100, 900) for _ in range(rng.randrange(1, 3))})
    windows = []
    for r0, r1 in pairwise(cuts_r):
        for c0, c1 in pairwise(cuts_c):
            windows.append((WEST_DM + c0, NORTH_DM - r0, noise[r0:r1, c0:c1]))
    rng.shuffle(windows)
    return windows


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_the_rule_equals_a_scalar_oracle_on_turned_buildings(seed):
    features = _moved(_fixture_features(), seed)
    windows = _windows(seed)
    got = _by_uuid(_chunks(features, windows))
    wanted = oracle(features, windows)
    assert got == wanted
    assert sum(1 for roof, _ in wanted.values() if roof is not None) >= 6, "a real test"


def test_any_cutting_and_order_of_the_same_pixels_gives_the_same_colours():
    features = _fixture_features()
    noise = np.random.RandomState(5).randint(0, 256, size=(1000, 2000, 3)).astype(np.uint8)
    whole = [(WEST_DM, NORTH_DM, noise)]
    cut = [
        (WEST_DM + 700, NORTH_DM, noise[:, 700:]),
        (WEST_DM, NORTH_DM, noise[:, :700]),
    ]
    cut_both = [
        (WEST_DM, NORTH_DM - 400, noise[400:, :1200]),
        (WEST_DM + 1200, NORTH_DM, noise[:, 1200:]),
        (WEST_DM, NORTH_DM, noise[:400, :1200]),
    ]
    reference = _by_uuid(_chunks(features, whole))
    assert any(count for _, count in reference.values())
    assert _by_uuid(_chunks(features, cut)) == reference
    assert _by_uuid(_chunks(features, cut_both)) == reference
    assert _by_uuid(_chunks(features, reversed(cut_both))) == reference


# --------------------------------------------------------------------------- the rasters


def test_no_photo_gives_no_colour_and_no_refusal():
    chunks = _chunks(_fixture_features(), [])
    assert all(b["roof"] is None and b["roof_pixels"] == 0 for c in chunks for b in c["buildings"])
    assert sum(len(c["buildings"]) for c in chunks) > 0


def test_a_raster_far_from_every_building_gives_no_colour():
    far = np.full((50, 50, 3), 7, dtype=np.uint8)
    chunks = _chunks(_fixture_features(), [(WEST_DM - 10000, NORTH_DM + 10000, far)])
    assert all(b["roof"] is None for c in chunks for b in c["buildings"])


def test_the_rasters_are_consumed_once_one_at_a_time():
    rasters = _windows(4)
    taken = []

    def photo():
        for raster in rasters:
            taken.append(raster[0])
            yield raster

    build_roof_chunks(_fixture_features(), load_world(WORLD), AREA, photo())
    assert taken == [r[0] for r in rasters]


@pytest.mark.parametrize(
    "second",
    [
        (WEST_DM + 50, NORTH_DM, np.zeros((40, 40, 3), np.uint8)),  # a corner inside the first
        (WEST_DM, NORTH_DM - 50, np.zeros((10, 100, 3), np.uint8)),  # a strip inside it
        (WEST_DM - 99, NORTH_DM + 99, np.zeros((100, 100, 3), np.uint8)),  # one pixel shared
        (WEST_DM, NORTH_DM, np.zeros((100, 100, 3), np.uint8)),  # the same place
    ],
    ids=["corner", "strip", "one-pixel", "same"],
)
def test_overlapping_rasters_are_refused(second):
    first = (WEST_DM, NORTH_DM, np.zeros((100, 100, 3), np.uint8))
    with pytest.raises(RoofsError, match="overlap"):
        _chunks(_fixture_features(), [first, second])


def test_rasters_that_only_touch_are_accepted():
    first = (WEST_DM, NORTH_DM, np.zeros((100, 100, 3), np.uint8))
    east = (WEST_DM + 100, NORTH_DM, np.zeros((100, 100, 3), np.uint8))
    south = (WEST_DM, NORTH_DM - 100, np.zeros((100, 100, 3), np.uint8))
    _chunks(_fixture_features(), [first, east, south])


@pytest.mark.parametrize(
    "raster",
    [
        (WEST_DM, NORTH_DM),
        (WEST_DM, NORTH_DM, np.zeros((10, 10), np.uint8)),
        (WEST_DM, NORTH_DM, np.zeros((10, 10, 4), np.uint8)),
        (WEST_DM, NORTH_DM, np.zeros((10, 10, 3), np.float32)),
        (WEST_DM, NORTH_DM, [[0, 0, 0]]),
        (WEST_DM + 0.5, NORTH_DM, np.zeros((10, 10, 3), np.uint8)),
        (WEST_DM, None, np.zeros((10, 10, 3), np.uint8)),
    ],
    ids=["two-items", "grey", "rgba", "float", "list", "half-decimetre", "no-north"],
)
def test_a_raster_that_is_not_8_bit_rgb_at_whole_decimetres_is_refused(raster):
    with pytest.raises(RoofsError):
        _chunks(_fixture_features(), [raster])


# --------------------------------------------------------------------------- the median


@pytest.mark.parametrize("seed", range(6))
def test_the_histogram_median_is_the_lower_median_of_the_sorted_values(seed):
    rng = np.random.RandomState(seed)
    for size in (1, 2, 3, 4, 5, 6, 7, 100, 101):
        values = (
            rng.choice([0, 1, 7, 8, 128, 254, 255], size=(size, 3))
            if seed % 2
            else (rng.randint(0, 256, size=(size, 3)))
        )
        counts = np.stack([np.bincount(values[:, c], minlength=256) for c in range(3)])
        expected = "".join(
            f"{sorted(values[:, c].tolist())[(size - 1) // 2]:02x}" for c in range(3)
        )
        assert _lower_median(counts, size) == expected, (seed, size)


def test_no_pixel_is_no_colour_never_an_empty_string():
    assert _lower_median(np.zeros((3, 256), dtype=np.int64), 0) is None
    chunks = _chunks(_fixture_features(), [])
    assert {b["roof"] for c in chunks for b in c["buildings"]} == {None}


def test_two_pixels_give_the_lower_of_them_per_channel():
    counts = np.zeros((3, 256), dtype=np.int64)
    for channel, (low, high) in enumerate(((10, 200), (255, 0), (5, 5))):
        counts[channel, low] += 1
        counts[channel, high] += 1
    assert _lower_median(counts, 2) == "0a0005"


# --------------------------------------------------------------------------- the selection


def _box(uuid: str, e: float, n: float, height: float = 1500.0) -> dict:
    """A closed 2 × 2 m box with a flat roof, its centre at (e, n)."""
    a = [(e - 1, n - 1), (e + 1, n - 1), (e + 1, n + 1), (e - 1, n + 1)]
    low, high = [(x, y, height) for x, y in a], [(x, y, height + 3) for x, y in a]
    quads = [
        (low[0], low[3], low[2], low[1]),  # the floor, facing down
        (high[0], high[1], high[2], high[3]),  # the roof
        (low[0], low[1], high[1], high[0]),
        (low[1], low[2], high[2], high[1]),
        (low[2], low[3], high[3], high[2]),
        (low[3], low[0], high[0], high[3]),
    ]
    triangles = []
    for p, q, r, s in quads:
        triangles += [(p, q, r), (p, r, s)]
    return {"uuid": uuid, "objektart": "x", "triangles": triangles}


def test_the_selection_is_the_buildings_steps_edges_in_and_out():
    """The bounding-box centre decides, the west and south edges of the area in, the east and
    north edges out (the area is E 2650900 … 2651100, N 1149950 … 1150050)."""
    centres = {
        "west": (2650900.0, 1150000.0, True),
        "south": (2651000.0, 1149950.0, True),
        "east": (2651100.0, 1150000.0, False),
        "north": (2651000.0, 1150050.0, False),
        "inside": (2651000.0, 1150000.0, True),
        "outside": (2651200.0, 1150000.0, False),
    }
    features = [
        _box(f"{{{number:08d}-0000-4000-8000-000000000000}}", e, n)
        for number, (e, n, _) in enumerate(centres.values())
    ]
    got = _by_uuid(_chunks(features, []))
    wanted = {
        f"{{{number:08d}-0000-4000-8000-000000000000}}"
        for number, (_, _, selected) in enumerate(centres.values())
        if selected
    }
    assert set(got) == wanted


def test_a_uuid_selected_twice_is_the_buildings_refusal():
    twin = _box("{00000000-0000-4000-8000-000000000001}", 2651000.0, 1150000.0)
    with pytest.raises(BuildingsError, match="selected 2 times"):
        _chunks([twin, dict(twin, sheet="1249-42")], [])


def test_a_solid_that_is_not_closed_is_the_buildings_refusal():
    broken = _box("{00000000-0000-4000-8000-000000000002}", 2651000.0, 1150000.0)
    broken["triangles"] = broken["triangles"][:-1]
    with pytest.raises(BuildingsError, match="not a closed"):
        _chunks([broken], [])


def test_the_chunks_are_by_tile_and_their_buildings_by_uuid_as_text():
    """Upper case sorts before lower case (the text order, not the hexadecimal's)."""
    features = [
        _box("{BBBBBBBB-0000-4000-8000-000000000000}", 2650950.0, 1150000.0),  # 2650-1150
        _box("{aaaaaaaa-0000-4000-8000-000000000000}", 2650960.0, 1150000.0),  # 2650-1150
        _box("{AAAAAAAA-0000-4000-8000-000000000000}", 2650970.0, 1150000.0),  # 2650-1150
        _box("{CCCCCCCC-0000-4000-8000-000000000000}", 2651050.0, 1150000.0),  # 2651-1150
        _box("{DDDDDDDD-0000-4000-8000-000000000000}", 2651050.0, 1149990.0),  # 2651-1149
    ]
    chunks = _chunks(features, [])
    assert [(c["tile"], [b["uuid"][1:5] for b in c["buildings"]]) for c in chunks] == [
        ("2650-1150", ["AAAA", "BBBB", "aaaa"]),
        ("2651-1149", ["DDDD"]),
        ("2651-1150", ["CCCC"]),
    ]
