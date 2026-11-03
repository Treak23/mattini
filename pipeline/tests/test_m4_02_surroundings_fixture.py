"""Pinning tests for brief v0.6.0-04 (brief M4-02 re-scoped by design §1): the shared
surroundings fixture is what it says, and the step gives its vectors (lessons 34, 42).

Re-cut from M4-02's pinned file of the same name for 0.6.0: the height is the MEAN of the
square's samples in whole centimetres (design §1), no longer the largest; the fixture's world,
tiles, lock and grid are M4-02's (design data committed with M4), its config is schema 2 and its
heights, description, committed manifest and vectors are re-cut (the pin author, two ways:
the throwaway step and plain Python in Fractions from source.json; identical bytes).

The fixture (tests/shared/surroundings_fixture/, surroundings_vectors.json; their `about`)
is a synthetic world with a non-zero height offset and nine synthetic swissALTIRegio tiles at
a 1000 m cell, grown by 3000 m at 3000 m spacing: 6 columns × 7 rows, nine samples a square,
samples on the squares' west, east, south and north edges (as the village's 10 m samples at
50 m spacing, design §0). The game's reader (brief v0.6.0-08) reads the same
`generated/surroundings/` folder, so the fixture must tell the right code from its likeliest
wrong twins: a flipped row or column order, swapped axes, a missing cut, a cut that takes the
area's edge, a vertex placed at a cell centre, a square closed on the wrong side, the largest
sample for the mean (M4-02's rule), the mean rounded to whole centimetres, no height offset.
Each is shown here to change the bytes.

Pinned rules (design §1):
- vertex (row r, column c) is LV95 (e_min + c·s, n_max − r·s) of the surroundings box, rows
  north to south, columns west to east; local x = E − origin E, z = −(N − origin N);
- its height is the mean of the samples whose position lies in [E − s/2, E + s/2) ×
  [N − s/2, N + s/2): their heights in whole centimetres summed as integers, divided once in
  float64 by 100 × their count, minus `height_offset_m` in float64, rounded once to float32;
- a vertex strictly inside the area box is NaN, the quiet NaN 0x7FC00000 (bytes 00 00 c0 7f);
  a vertex on the area's edge keeps its height;
- the file is little-endian float32, no header.

Does NOT prove: that the game reads the file (brief v0.6.0-08 reads this folder); that the
fixture's nine samples a square stand for the village's 25 (the real run's SHA-256 does).
"""

import hashlib
import json
import struct
from fractions import Fraction

import numpy as np
from computed_for import computed_for
from synthetic_regio import FIXTURE, fixture_source, points_of, raw_regio

from mattini.surroundings import build_surroundings, load_surroundings_config
from mattini.world import REPO, load_world

VECTORS = json.loads((REPO / "tests" / "shared" / "surroundings_vectors.json").read_text("utf-8"))
GENERATED = FIXTURE / "generated" / "surroundings"
NAN = bytes.fromhex("0000c07f")
FIXTURE_F32 = "5758119c921825ee96c8f57e524e470807010661277d6f5ce19693e72dc3bb6d"
MAX_RULE_F32 = "f07106285a79517adca87e6d712f73e42ade869f306b36c4519f11f811526c6d"  # M4-02's


def _grid() -> np.ndarray:
    data = (GENERATED / "fixture.f32").read_bytes()
    return np.frombuffer(data, dtype="<f4").reshape(VECTORS["rows"], VECTORS["columns"])


def _cents(text: str) -> int:
    """A height text in whole centimetres, written out without float (`-3.05` -> -305)."""
    whole, _, frac = text.lstrip("-").partition(".")
    assert whole.isdigit() and len(frac) <= 2 and (frac == "" or frac.isdigit()), text
    cents = int(whole) * 100 + int(frac.ljust(2, "0") or "0")
    return -cents if text.startswith("-") else cents


def _samples() -> dict:
    out = {}
    for tile in fixture_source()["tiles"].values():
        for x, y, z in points_of(tile["text"]):
            assert (x, y) not in out
            out[(x, y)] = _cents(z)
    return out


def _mine(samples: dict, e, n, s) -> list[int]:
    return [
        z
        for (x, y), z in samples.items()
        if e - Fraction(s, 2) <= x < e + Fraction(s, 2)
        and n - Fraction(s, 2) <= y < n + Fraction(s, 2)
    ]


def _height(cents: list[int], offset) -> np.float32:
    """The rule: one exact quotient, the offset, one rounding to float32."""
    return np.float32(float(Fraction(sum(cents), 100 * len(cents)) - Fraction(offset)))


def test_the_fixture_s_zips_are_what_its_lock_pins(tmp_path):
    _, lock = raw_regio(tmp_path)
    committed = json.loads((FIXTURE / "datasets.lock.json").read_text(encoding="utf-8"))
    assert lock == committed


def test_the_fixture_config_was_computed_for_the_fixture_s_world_and_lock():
    config = load_surroundings_config(FIXTURE / "surroundings.json")
    lock = json.loads((FIXTURE / "datasets.lock.json").read_text(encoding="utf-8"))
    world = load_world(FIXTURE / "world.json")
    assert config["schema"] == 2
    assert config["areas"]["fixture"]["computed_for"] == computed_for(world, lock, "swissaltiregio")
    assert config["areas"]["fixture"]["expected_sha256"] == FIXTURE_F32 == VECTORS["sha256"]


def test_the_world_is_asymmetric_with_a_height_offset():
    world = json.loads((FIXTURE / "world.json").read_text(encoding="utf-8"))
    assert world["height_offset_m"] == VECTORS["height_offset_m"] == 1250.25
    area = world["areas"]["fixture"]
    assert area == VECTORS["cut_box"]
    assert area["e_max"] - area["e_min"] != area["n_max"] - area["n_min"]
    assert (VECTORS["columns"], VECTORS["rows"]) == (6, 7)


def test_every_source_height_is_whole_centimetres_as_swisstopo_writes_them():
    for tile in fixture_source()["tiles"].values():
        for _, _, z in points_of(tile["text"]):
            frac = z.partition(".")[2]
            assert len(frac) <= 2 and not frac.endswith("0"), z


def test_the_generated_files_are_the_vectors():
    grid = _grid()
    data = (GENERATED / "fixture.f32").read_bytes()
    assert hashlib.sha256(data).hexdigest() == VECTORS["sha256"] == FIXTURE_F32
    assert len(data) == 6 * 7 * 4
    block = json.loads((GENERATED / "fixture.json").read_text(encoding="utf-8"))
    assert block["sha256"] == VECTORS["sha256"]
    assert block["lv95_box"] == VECTORS["lv95_box"] and block["cut_box"] == VECTORS["cut_box"]
    assert block["spacing_m"] == VECTORS["spacing_m"] == 3000
    world = load_world(FIXTURE / "world.json")
    samples = _samples()
    for vertex in VECTORS["vertices"]:
        r, c = vertex["row"], vertex["column"]
        e = VECTORS["lv95_box"]["e_min"] + c * VECTORS["spacing_m"]
        n = VECTORS["lv95_box"]["n_max"] - r * VECTORS["spacing_m"]
        assert (vertex["e"], vertex["n"]) == (e, n)
        x, _, z = world.to_local(e, n, 0.0)
        assert (vertex["local_x"], vertex["local_z"]) == (x, z)
        mine = _mine(samples, Fraction(e), Fraction(n), VECTORS["spacing_m"])
        assert (vertex["samples"], vertex["sum_cm"]) == (len(mine), sum(mine)) == (9, sum(mine))
        cell = data[(r * 6 + c) * 4 : (r * 6 + c) * 4 + 4]
        if vertex["local_y"] is None:
            assert cell == NAN, (r, c)
        else:
            assert struct.unpack("<f", cell)[0] == vertex["local_y"], (r, c)
            assert _height(mine, VECTORS["height_offset_m"]) == np.float32(vertex["local_y"])
    assert int(np.isnan(grid).sum()) == VECTORS["nan_count"] == 6


def test_every_vertex_is_the_mean_of_its_half_open_square_or_the_cut():
    """The rule written out with exact fractions, against every one of the 42 vertices."""
    samples = _samples()
    grid = _grid()
    box, cut, s = VECTORS["lv95_box"], VECTORS["cut_box"], VECTORS["spacing_m"]
    for r in range(VECTORS["rows"]):
        for c in range(VECTORS["columns"]):
            e = Fraction(box["e_min"]) + c * s
            n = Fraction(box["n_max"]) - r * s
            if cut["e_min"] < e < cut["e_max"] and cut["n_min"] < n < cut["n_max"]:
                assert grid[r, c].tobytes() == NAN, (r, c)
                continue
            mine = _mine(samples, e, n, s)
            assert len(mine) == 9, (r, c)
            assert grid[r, c].tobytes() == _height(mine, VECTORS["height_offset_m"]).tobytes()


def test_the_named_edge_cases_hold():
    samples = _samples()
    by_place = {(v["row"], v["column"]): v for v in VECTORS["vertices"]}
    s = VECTORS["spacing_m"]
    # (0, 0) takes the samples on its west and south edges, not those on its east and north
    v = by_place[(0, 0)]
    e, n = v["e"], v["n"]
    own = {(x, y) for x in (e - 1500, e - 500, e + 500) for y in (n - 1500, n - 500, n + 500)}
    assert v["sum_cm"] == sum(samples[p] for p in own)
    east = sum(samples[(e + 1500, y)] for y in (n - 1500, n - 500, n + 500))
    west = sum(samples[(e - 1500, y)] for y in (n - 1500, n - 500, n + 500))
    assert east != west  # a square closed on the east would give another sum
    north = sum(samples[(x, n + 1500)] for x in (e - 1500, e - 500, e + 500))
    south = sum(samples[(x, n - 1500)] for x in (e - 1500, e - 500, e + 500))
    assert north != south
    # (0, 1)'s west edge is (0, 0)'s east edge: each sample belongs to exactly one square
    left, right = by_place[(0, 0)], by_place[(0, 1)]
    assert right["e"] - s / 2 == left["e"] + s / 2
    assert sum(samples[(right["e"] - 1500, y)] for y in (n - 1500, n - 500, n + 500)) == east
    # (6, 5)'s south edge is its own; the north edge is row 5's
    v = by_place[(6, 5)]
    xs = (v["e"] - 1500, v["e"] - 500, v["e"] + 500)
    assert sum(samples[(x, v["n"] - 1500)] for x in xs) != sum(
        samples[(x, v["n"] + 1500)] for x in xs
    )
    # the cut hides the highest sample of all
    assert max(samples.values()) == 444444
    assert by_place[(2, 2)]["local_y"] is None and by_place[(2, 2)]["sum_cm"] > 0


def test_the_likeliest_wrong_twins_give_other_bytes():
    grid = _grid()
    data = grid.astype("<f4").tobytes()
    assert np.flipud(grid).astype("<f4").tobytes() != data  # rows south to north
    assert np.fliplr(grid).astype("<f4").tobytes() != data  # columns east to west
    assert grid.T.shape != grid.shape  # swapped axes cannot even keep the shape
    samples = _samples()
    box, cut, s = VECTORS["lv95_box"], VECTORS["cut_box"], VECTORS["spacing_m"]
    offset = VECTORS["height_offset_m"]

    def twin(
        closed_east=False,
        closed_north=False,
        largest=False,
        centre=False,
        whole_cm=False,
        no_offset=False,
        no_cut=False,
        edge_cut=False,
    ):
        out = grid.copy()
        for r in range(7):
            for c in range(6):
                e = box["e_min"] + c * s
                n = box["n_max"] - r * s
                if edge_cut:
                    inside = cut["e_min"] <= e <= cut["e_max"] and cut["n_min"] <= n <= cut["n_max"]
                else:
                    inside = cut["e_min"] < e < cut["e_max"] and cut["n_min"] < n < cut["n_max"]
                if inside and not no_cut:
                    out[r, c] = np.frombuffer(NAN, "<f4")[0]
                    continue
                e += s / 2 if centre else 0
                n -= s / 2 if centre else 0
                mine = [
                    z
                    for (x, y), z in samples.items()
                    if (e - s / 2 < x <= e + s / 2 if closed_east else e - s / 2 <= x < e + s / 2)
                    and (n - s / 2 < y <= n + s / 2 if closed_north else n - s / 2 <= y < n + s / 2)
                ]
                if not mine:
                    continue
                if largest:
                    value = Fraction(max(mine), 100)
                elif whole_cm:
                    value = Fraction(sum(mine) // len(mine), 100)
                else:
                    value = Fraction(sum(mine), 100 * len(mine))
                value -= 0 if no_offset else Fraction(offset)
                out[r, c] = np.float32(float(value))
        return out.astype("<f4").tobytes()

    kinds = (
        "closed_east",
        "closed_north",
        "largest",
        "centre",
        "whole_cm",
        "no_offset",
        "no_cut",
        "edge_cut",
    )
    for kind in kinds:
        assert twin(**{kind: True}) != data, kind
    assert hashlib.sha256(twin(largest=True)).hexdigest() == MAX_RULE_F32  # M4-02's file
    assert twin() == data  # the twin machinery itself reproduces the rule


def test_the_committed_manifest_carries_the_description():
    """The fixture's own generated/manifest.json (M4-07's form, design data; brief v0.6.0-07
    writes the manifest's block): its `surroundings` block is the re-cut description, so no
    committed file still holds M4-02's heights' SHA-256."""
    manifest = json.loads((FIXTURE / "generated" / "manifest.json").read_text(encoding="utf-8"))
    block = json.loads((GENERATED / "fixture.json").read_text(encoding="utf-8"))
    assert manifest["surroundings"] == block
    assert MAX_RULE_F32 not in (FIXTURE / "generated" / "manifest.json").read_text("utf-8")


def test_the_step_writes_the_fixture_s_files(tmp_path):
    raw, lock = raw_regio(tmp_path / "raw")
    world = load_world(FIXTURE / "world.json")
    datasets = json.loads((FIXTURE / "datasets.json").read_text(encoding="utf-8"))["datasets"]
    config = load_surroundings_config(FIXTURE / "surroundings.json")
    out = tmp_path / "out"
    build_surroundings(world, datasets, lock, config, raw, out)
    for name in ("fixture.f32", "fixture.json"):
        assert (out / "surroundings" / name).read_bytes() == (GENERATED / name).read_bytes()
