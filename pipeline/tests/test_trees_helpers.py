"""Brief M3-07: the rule's parts against slow exact versions written from the definition.

The step finds tops, triangles' texels, margins, neighbours and the smoothing with array
arithmetic over whole rows; each is compared here with the definition in SPEC §8 *The trees*,
pixel by pixel in plain Python (fractions where a rational is involved), on random inputs
built to tie: equal S values, vertices and edges on texel centres, trees in a band
narrower than the search's. Then `build_tree_chunks`'s refusals.

Does NOT prove: that the definition is the rule (the shared fixture's pinned bytes and the
real village's chunks do); that real data holds no case the random ones do not reach.
"""

import json
import random
import struct
from pathlib import Path

import numpy as np
import pytest

from mattini import trees
from mattini.surfaces import _Frame
from mattini.trees import (
    MIN_TOP,
    WINDOW_M,
    TreesError,
    _grown,
    _inputs_sha256,
    _nearest,
    _smooth,
    _tops,
    _triangle_spans,
    _triangles,
    build_tree_chunks,
    check_trees_config,
)
from mattini.world import load_world

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "shared" / "trees_fixture"
SIZE = 96
E0, N1 = 2_700_000_000, 1_200_000_000  # a frame's north-west corner in mm


# ------------------------------------------------------------------------- the neighbours


@pytest.mark.parametrize("seed", range(8))
def test_the_nearest_tree_is_found_exactly_whatever_the_band(seed, monkeypatch):
    """Narrow first bands (2 rows) make the search widen again and again; the answer is the
    brute-force one for every tree, -1 for a tree alone."""
    rng = random.Random(seed)
    monkeypatch.setattr(trees, "NEIGHBOUR_ROWS", rng.choice([1, 2, 3, 16]))
    cells = {(rng.randrange(0, 300), rng.randrange(0, 40)) for _ in range(rng.randrange(2, 60))}
    cells |= {(rng.randrange(0, 30), rng.randrange(0, 40)) for _ in range(rng.randrange(0, 30))}
    ordered = sorted(cells)  # raster order, as the tops come
    ti = np.array([i for i, _ in ordered])
    tj = np.array([j for _, j in ordered])
    expected = [
        min(((i - a) ** 2 + (j - b) ** 2 for a, b in ordered if (a, b) != (i, j)), default=-1)
        for i, j in ordered
    ]
    assert _nearest(ti, tj).tolist() == expected


def test_a_lone_tree_has_no_neighbour_and_two_trees_see_each_other():
    assert _nearest(np.array([5]), np.array([7])).tolist() == [-1]
    assert _nearest(np.array([], dtype=int), np.array([], dtype=int)).tolist() == []
    assert _nearest(np.array([0, 3]), np.array([0, 4])).tolist() == [25, 25]


# ------------------------------------------------------------------------ the triangles


def _inside_or_on(p, a, b, c) -> bool:
    """Exact: p in the closed triangle abc (not degenerate), by the three orientations."""
    signs = [
        (q[0] - o[0]) * (p[1] - o[1]) - (q[1] - o[1]) * (p[0] - o[0])
        for o, q in ((a, b), (b, c), (c, a))
    ]
    return all(s >= 0 for s in signs) or all(s <= 0 for s in signs)


@pytest.mark.parametrize("seed", range(12))
def test_the_texels_of_a_triangle_are_those_inside_or_on_it(seed):
    rng = random.Random(seed)
    frame = _Frame((E0 / 1000, E0 / 1000 + 5, N1 / 1000 - 4, N1 / 1000), 0.5)  # 10 × 8 texels
    lattice = rng.choice([250, 50, 1])
    triangles = []
    while len(triangles) < 6:
        pts = [
            (rng.randrange(-1500, 6500, lattice), rng.randrange(-5500, 1500, lattice))
            for _ in range(3)
        ]
        (ax, ay), (bx, by), (cx, cy) = pts
        if (bx - ax) * (cy - ay) - (by - ay) * (cx - ax) != 0:
            triangles.append(pts)
    plan = np.array(triangles, dtype=np.int64)
    rows, firsts, ends = _triangle_spans(frame, plan)
    got = np.zeros((frame.rows, frame.columns), dtype=bool)
    for r, a, b in zip(rows, firsts, ends, strict=True):
        got[r, a:b] = True
    expected = np.zeros_like(got)
    for r in range(frame.rows):
        for c in range(frame.columns):
            centre = (250 + 500 * c, -250 - 500 * r)
            expected[r, c] = any(_inside_or_on(centre, *t) for t in triangles)
    assert np.array_equal(got, expected)


def test_a_vertex_on_a_centre_and_an_edge_through_centres_are_inside():
    frame = _Frame((E0 / 1000, E0 / 1000 + 2, N1 / 1000 - 2, N1 / 1000), 0.5)  # 4 × 4 texels
    # a right triangle whose legs run through the centres of column 0 and row 0
    plan = np.array([[[250, -250], [1250, -250], [250, -1250]]], dtype=np.int64)
    rows, firsts, ends = _triangle_spans(frame, plan)
    got = {(int(r), c) for r, a, b in zip(rows, firsts, ends, strict=True) for c in range(a, b)}
    assert got == {(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (2, 0)}, "the hypotenuse's centres too"


def _building(uuid: str, triangles: list, sheet: str | None = None) -> dict:
    feature = {"uuid": uuid, "objektart": "x", "triangles": triangles}
    return dict(feature, sheet=sheet) if sheet else feature


def test_only_buildings_meeting_the_area_and_non_degenerate_triangles_count():
    frame = _Frame((2_700_000.0, 2_700_010.0, 1_199_990.0, 1_200_000.0), 0.5)
    roof = [(2_700_002.0, 1_199_998.0, 1500.0), (2_700_006.0, 1_199_998.0, 1500.0)]
    roof.append((2_700_002.0, 1_199_994.0, 1500.0))
    wall = [(2_700_002.0, 1_199_998.0, 1500.0), (2_700_006.0, 1_199_998.0, 1500.0)]
    wall.append((2_700_006.0, 1_199_998.0, 1510.0))  # vertical: a segment in plan
    far = [(2_700_100.0, 1_199_998.0, 1500.0), (2_700_104.0, 1_199_998.0, 1500.0)]
    far.append((2_700_100.0, 1_199_994.0, 1500.0))
    plan = _triangles(
        frame,
        [_building("a", [tuple(roof), tuple(wall)]), _building("b", [tuple(far)], sheet="1-2")],
    )
    assert plan.shape == (1, 3, 2), "the wall is degenerate in plan, the far building is outside"
    assert plan[0].tolist() == [[2000, -2000], [6000, -2000], [2000, -6000]]
    assert _triangles(frame, []).shape == (0, 3, 2)


# --------------------------------------------------------------------------- the margin


@pytest.mark.parametrize("seed", range(5))
def test_the_margin_is_the_disc_of_radius_4_over_the_area_s_pixels_only(seed):
    rng = np.random.default_rng(seed)
    mask = rng.random((20, 25)) < 0.04
    grown = _grown(mask)
    expected = np.zeros_like(mask)
    for i, j in np.argwhere(mask):
        for a in range(max(0, i - 4), min(20, i + 5)):
            for b in range(max(0, j - 4), min(25, j + 5)):
                if (a - i) ** 2 + (b - j) ** 2 <= 16:
                    expected[a, b] = True
    assert np.array_equal(grown, expected)
    assert grown[mask].all(), "the pixels themselves are in B"


def test_the_margin_is_a_disc_not_a_square():
    mask = np.zeros((11, 11), dtype=bool)
    mask[5, 5] = True
    grown = _grown(mask)
    assert grown[5, 9] and grown[9, 5], "4 pixels along an axis: 16, in"
    assert grown[8, 7] and grown[7, 8], "(3, 2): 13, in"
    assert not grown[8, 8], "(3, 3): 18, out"
    assert not grown[9, 6] and not grown[6, 9], "(4, 1): 17, out"
    assert not grown[9, 9]
    assert int(grown.sum()) == 49, "the square would hold 81"


# ------------------------------------------------------------------------- the smoothing


def test_the_smoothing_is_the_binomial_5x5_with_zeros_outside():
    rng = np.random.default_rng(3)
    canopy = rng.integers(0, 50_000, size=(9, 11)).astype(np.int64)
    out = np.zeros_like(canopy)
    _smooth(canopy, out)
    weights = np.array([1, 4, 6, 4, 1], dtype=np.int64)
    padded = np.pad(canopy, 2)
    expected = np.zeros_like(canopy)
    for i in range(9):
        for j in range(11):
            window = padded[i : i + 5, j : j + 5]
            expected[i, j] = int((np.outer(weights, weights) * window).sum())
    assert np.array_equal(out, expected)
    assert weights.sum() ** 2 == 256


def test_a_single_pixel_spreads_as_the_kernel_and_the_edge_loses_what_falls_outside():
    canopy = np.zeros((7, 7), dtype=np.int64)
    canopy[0, 0] = 256
    out = np.zeros_like(canopy)
    _smooth(canopy, out)
    assert out[0, 0] == 256 * 36 and out[0, 2] == 256 * 6 and out[2, 2] == 256
    assert out.sum() == 256 * (6 + 4 + 1) ** 2, "only the quarter inside the area is kept"


# --------------------------------------------------------------------------------- tops


def _brute_tops(interior: np.ndarray, excluded: np.ndarray) -> list[tuple[int, int]]:
    """The tops by the definition: S >= 3 m, not on the outer ring, not excluded, and no
    other pixel of the window dominates it."""
    rows, columns = interior.shape
    found = []
    for i in range(1, rows - 1):
        for j in range(1, columns - 1):
            s = int(interior[i, j])
            if s < MIN_TOP or excluded[i, j]:
                continue
            rho = 3 + s // WINDOW_M
            top = True
            for a in range(max(0, i - rho), min(rows, i + rho + 1)):
                for b in range(max(0, j - rho), min(columns, j + rho + 1)):
                    if (a, b) == (i, j) or (a - i) ** 2 + (b - j) ** 2 > rho * rho:
                        continue
                    q = int(interior[a, b])
                    if q > s or (q == s and (a, b) < (i, j)):
                        top = False
            if top:
                found.append((i, j))
    return found


@pytest.mark.parametrize("seed", range(10))
def test_the_tops_are_the_windows_maxima_with_ties_to_the_first_in_raster_order(seed):
    rng = np.random.default_rng(seed)
    metres = rng.choice([0, 0, 1, 3, 3, 3, 4, 4, 11, 11, 25], size=(24, 30))
    interior = metres.astype(np.int64) * (1 << 21)
    excluded = rng.random((24, 30)) < 0.05
    reach = 3 + int(interior.max()) // WINDOW_M
    padded = np.full((24 + 2 * reach, 30 + 2 * reach), -1, dtype=np.int64)
    padded[reach:-reach, reach:-reach] = interior
    ti, tj, value = _tops(padded, reach, 24, 30, excluded)
    assert list(zip(ti.tolist(), tj.tolist(), strict=True)) == _brute_tops(interior, excluded)
    assert value.tolist() == [int(interior[i, j]) for i, j in zip(ti, tj, strict=True)]
    assert len(ti) > 0


def test_the_window_is_the_candidate_s_own_and_grows_with_its_height():
    """A 12 m crown has a window of 4 pixels, so a 13 m crown 4 pixels away hides it; two 5 m
    crowns also 4 pixels apart have windows of 3 and do not see each other."""
    interior = np.zeros((9, 40), dtype=np.int64)
    interior[4, 5] = 12 * (1 << 21)
    interior[4, 9] = 13 * (1 << 21)
    interior[4, 20] = 5 * (1 << 21)
    interior[4, 24] = 5 * (1 << 21)
    reach = 4
    padded = np.full((9 + 2 * reach, 40 + 2 * reach), -1, dtype=np.int64)
    padded[reach:-reach, reach:-reach] = interior
    ti, tj, _ = _tops(padded, reach, 9, 40, np.zeros((9, 40), dtype=bool))
    assert list(zip(ti.tolist(), tj.tolist(), strict=True)) == [(4, 9), (4, 20), (4, 24)]


def test_a_pixel_on_the_outer_ring_is_never_a_top():
    interior = np.zeros((5, 5), dtype=np.int64)
    interior[0, 2] = interior[4, 2] = interior[2, 0] = interior[2, 4] = 9 * (1 << 21)
    padded = np.full((11, 11), -1, dtype=np.int64)
    padded[3:-3, 3:-3] = interior
    ti, _, _ = _tops(padded, 3, 5, 5, np.zeros((5, 5), dtype=bool))
    assert len(ti) == 0


# ------------------------------------------------------------------- the rule's refusals


def _inputs() -> dict:
    tlm = json.loads((FIXTURE / "tlm.json").read_text("utf-8"))
    return {
        "dsm": np.fromfile(FIXTURE / "dsm.f32", dtype="<f4").reshape(SIZE, SIZE),
        "dtm": np.fromfile(FIXTURE / "dtm.f32", dtype="<f4").reshape(SIZE, SIZE),
        "buildings": json.loads((FIXTURE / "buildings.json").read_text("utf-8"))["features"],
        "footprints": tlm["TLM_GEBAEUDE_FOOTPRINT"],
        "land_cover": tlm["TLM_BODENBEDECKUNG"],
    }


def _run(inputs: dict, area: str = "fixture"):
    world = load_world(FIXTURE / "world.json")
    return build_tree_chunks(
        inputs["dsm"],
        inputs["dtm"],
        inputs["buildings"],
        inputs["footprints"],
        inputs["land_cover"],
        world,
        area,
    )


def test_the_fixture_runs_clean_as_a_control():
    assert [c["tile"] for c in _run(_inputs())] == ["2650-1149", "2650-1150", "2651-1150"]


@pytest.mark.parametrize(
    ("change", "pattern"),
    [
        (lambda i: i.update(dsm=i["dsm"].astype(np.float64)), "32-bit floats"),
        (lambda i: i.update(dtm=i["dtm"].ravel()), "two-dimensional"),
        (lambda i: i.update(dsm=i["dsm"][:, :-1].copy()), "needs 96 × 96"),
        (lambda i: i["dtm"].__setitem__((3, 4), np.float32("nan")), "not a height"),
        (lambda i: i["dsm"].__setitem__((7, 7), np.float32("inf")), "not a height"),
        (lambda i: i["buildings"][0].update(triangles=[[1, 2, 3]]), "three .E, N, H. points"),
        (lambda i: i["buildings"][0].update(triangles=[]), "three .E, N, H. points"),
        (lambda i: i["buildings"][0].update(triangles="x"), "three .E, N, H. points"),
        (
            lambda i: i["buildings"][0]["triangles"][0][0].__setitem__(0, 2650989.2504),
            r"building .*1 mm grid",
        ),
        (
            lambda i: i["buildings"][0]["triangles"][0][0].__setitem__(0, 9.0e9),
            "537 km",
        ),
        (lambda i: i["footprints"][0].pop("polygons"), "needs a UUID and polygons"),
        (lambda i: i["footprints"][0].update(uuid=5), "needs a UUID and polygons"),
        (lambda i: i["footprints"][0]["polygons"][0][0].pop(), "not closed"),
        (
            lambda i: i["land_cover"][0]["polygons"][0][0][0].__setitem__(1, 1150006.7504),
            r"TLM_BODENBEDECKUNG .*1 mm grid",
        ),
    ],
)
def test_inputs_that_are_not_what_the_rule_reads_are_refused(change, pattern):
    inputs = _inputs()
    inputs["dsm"], inputs["dtm"] = inputs["dsm"].copy(), inputs["dtm"].copy()
    change(inputs)
    with pytest.raises(TreesError, match=pattern):
        _run(inputs)


def test_an_area_the_world_does_not_have_is_refused():
    with pytest.raises(TreesError, match="no area named 'elsewhere'"):
        _run(_inputs(), "elsewhere")


def test_no_trees_gives_no_chunks():
    inputs = _inputs()
    inputs["dsm"] = inputs["dtm"].copy()
    assert _run(inputs) == []


# ------------------------------------------------------------------------- the config


def test_the_fixture_lock_hashes_to_the_inputs_the_fixture_config_records():
    """`_inputs_sha256` over the lock's four entries is design's value for the fixture."""
    lock = json.loads((FIXTURE / "datasets.lock.json").read_text("utf-8"))["datasets"]
    config = json.loads((FIXTURE / "trees.json").read_text("utf-8"))
    recorded = config["areas"]["fixture"]["computed_for"]["inputs_sha256"]
    assert _inputs_sha256(lock) == recorded
    reversed_entries = {name: lock[name] for name in sorted(lock, reverse=True)}
    assert _inputs_sha256(reversed_entries) == recorded, "the order the entries come in is not it"
    changed = json.loads(json.dumps(lock))
    changed["swisstlm3d"]["sha256"] = "0" * 64
    assert _inputs_sha256(changed) != recorded


@pytest.mark.parametrize(
    ("change", "pattern"),
    [
        (lambda a: a.update(expected_sha256={}), "non-empty"),
        (lambda a: a.update(expected_sha256=[]), "non-empty"),
        (lambda a: a["expected_sha256"].update({"2623-1095": "A" * 64}), "lower-case"),
        (lambda a: a["expected_sha256"].update({"x": "0" * 64}), "tile id"),
        (
            lambda a: a.update(computed_for={"inputs_sha256": "0" * 64, "world_sha256": "z" * 64}),
            "computed_for",
        ),
    ],
)
def test_more_malformed_trees_configs_are_refused_naming_where(change, pattern):
    area = {
        "computed_for": {"inputs_sha256": "1" * 64, "world_sha256": "2" * 64},
        "expected_sha256": {"2623-1095": "3" * 64},
    }
    check_trees_config({"schema": 1, "areas": {"village": area}})
    change(area)
    with pytest.raises(TreesError, match=pattern) as refusal:
        check_trees_config({"schema": 1, "areas": {"village": area}}, "config/trees.json")
    assert str(refusal.value).startswith("config/trees.json: ")


# ------------------------------------------------------------- a narrow crown, by hand


def _pole(height_m: float) -> list[dict]:
    """The chunks for flat ground with one single-pixel pole of `height_m`, no buildings."""
    dtm = np.full((SIZE, SIZE), 1500.0, dtype=np.float32)
    dsm = dtm.copy()
    dsm[48, 48] += np.float32(height_m)
    world = load_world(FIXTURE / "world.json")
    return build_tree_chunks(dsm, dtm, [], [], [], world, "fixture")


@pytest.mark.parametrize(
    ("height_m", "trees"),
    [
        (18.0, 0),  # S = 36/256 * 18 = 2.53 m
        (21.25, 0),  # S = 2.988 m: just below 3 m
        (21.5, 1),  # S = 3.023 m
        (40.0, 1),  # chm exactly 40 m is kept ("above 40 m" is dropped)
        (40.125, 0),  # above 40 m: a cliff
    ],
)
def test_a_single_pixel_needs_36_over_256_of_its_height_to_reach_3_m(height_m, trees):
    """S at the pole is 36/256 of its height (the kernel's centre weight): 3 m needs 21.33 m."""
    chunks = _pole(height_m)
    assert sum(c["trees"] for c in chunks) == trees
    if trees:
        _, _, _, height, radius = struct.unpack("<5f", chunks[0]["data"])
        assert height == height_m and radius == min(6.0, max(1.0, height_m / 4))
