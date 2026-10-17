"""Pinning tests for brief M4-02: the shared surroundings fixture is what it says, and the step
gives its vectors (m4-design §2; lessons 34, 42).

The fixture (tests/shared/surroundings_fixture/, surroundings_vectors.json; their `about`)
is a synthetic world with a non-zero height offset and nine synthetic swissALTIRegio tiles at
a 1000 m cell, grown by 3000 m at 3000 m spacing: 6 columns × 7 rows. The game's reader (a
later brief) reads the same `generated/surroundings/` folder, so the fixture must tell the
right code from its likeliest wrong twins: a flipped row or column order, swapped axes, a
missing cut, a cut that takes the area's edge, a vertex placed at a cell centre, a square
closed on the wrong side, a mean for the maximum. Each is shown here to change the bytes.

Pinned rules (m4-design §2):
- vertex (row r, column c) is LV95 (e_min + c·s, n_max − r·s) of the surroundings box, rows
  north to south, columns west to east; local x = E − origin E, z = −(N − origin N);
- its height is the largest sample whose position lies in [E − s/2, E + s/2) ×
  [N − s/2, N + s/2), minus `height_offset_m`, rounded once to float32;
- a vertex strictly inside the area box is NaN, the quiet NaN 0x7FC00000 (bytes 00 00 c0 7f);
  a vertex on the area's edge keeps its height;
- the file is little-endian float32, no header.

Does NOT prove: that the game reads the file (its reader, a later brief, reads this folder).
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


def _grid() -> np.ndarray:
    data = (GENERATED / "fixture.f32").read_bytes()
    return np.frombuffer(data, dtype="<f4").reshape(VECTORS["rows"], VECTORS["columns"])


def _samples() -> dict:
    out = {}
    for tile in fixture_source()["tiles"].values():
        for x, y, z in points_of(tile["text"]):
            assert (x, y) not in out
            out[(x, y)] = Fraction(z)
    return out


def test_the_fixture_s_zips_are_what_its_lock_pins(tmp_path):
    _, lock = raw_regio(tmp_path)
    committed = json.loads((FIXTURE / "datasets.lock.json").read_text(encoding="utf-8"))
    assert lock == committed


def test_the_fixture_config_was_computed_for_the_fixture_s_world_and_lock():
    config = load_surroundings_config(FIXTURE / "surroundings.json")
    lock = json.loads((FIXTURE / "datasets.lock.json").read_text(encoding="utf-8"))
    world = load_world(FIXTURE / "world.json")
    assert config["areas"]["fixture"]["computed_for"] == computed_for(world, lock, "swissaltiregio")


def test_the_world_is_asymmetric_with_a_height_offset():
    world = json.loads((FIXTURE / "world.json").read_text(encoding="utf-8"))
    assert world["height_offset_m"] == VECTORS["height_offset_m"] == 1250.25
    area = world["areas"]["fixture"]
    assert area == VECTORS["cut_box"]
    assert area["e_max"] - area["e_min"] != area["n_max"] - area["n_min"]
    assert (VECTORS["columns"], VECTORS["rows"]) == (6, 7)


def test_the_generated_files_are_the_vectors():
    grid = _grid()
    data = (GENERATED / "fixture.f32").read_bytes()
    assert hashlib.sha256(data).hexdigest() == VECTORS["sha256"]
    assert len(data) == 6 * 7 * 4
    block = json.loads((GENERATED / "fixture.json").read_text(encoding="utf-8"))
    assert block["sha256"] == VECTORS["sha256"]
    assert block["lv95_box"] == VECTORS["lv95_box"] and block["cut_box"] == VECTORS["cut_box"]
    world = load_world(FIXTURE / "world.json")
    for vertex in VECTORS["vertices"]:
        r, c = vertex["row"], vertex["column"]
        e = VECTORS["lv95_box"]["e_min"] + c * VECTORS["spacing_m"]
        n = VECTORS["lv95_box"]["n_max"] - r * VECTORS["spacing_m"]
        assert (vertex["e"], vertex["n"]) == (e, n)
        x, _, z = world.to_local(e, n, 0.0)
        assert (vertex["local_x"], vertex["local_z"]) == (x, z)
        cell = data[(r * 6 + c) * 4 : (r * 6 + c) * 4 + 4]
        if vertex["local_y"] is None:
            assert cell == NAN, (r, c)
        else:
            assert struct.unpack("<f", cell)[0] == vertex["local_y"], (r, c)
    assert int(np.isnan(grid).sum()) == VECTORS["nan_count"] == 6


def test_every_vertex_is_the_largest_sample_of_its_half_open_square_or_the_cut():
    """The rule written out with exact fractions, against every one of the 42 vertices."""
    samples = _samples()
    grid = _grid()
    box, cut, s = VECTORS["lv95_box"], VECTORS["cut_box"], VECTORS["spacing_m"]
    offset = Fraction(VECTORS["height_offset_m"])
    for r in range(VECTORS["rows"]):
        for c in range(VECTORS["columns"]):
            e = Fraction(box["e_min"]) + c * s
            n = Fraction(box["n_max"]) - r * s
            if cut["e_min"] < e < cut["e_max"] and cut["n_min"] < n < cut["n_max"]:
                assert grid[r, c].tobytes() == NAN, (r, c)
                continue
            mine = [
                z
                for (x, y), z in samples.items()
                if e - Fraction(s, 2) <= x < e + Fraction(s, 2)
                and n - Fraction(s, 2) <= y < n + Fraction(s, 2)
            ]
            assert len(mine) == 9, (r, c)
            wanted = np.float32(float(max(mine)) - float(offset))
            assert grid[r, c] == wanted, (r, c)


def test_the_named_edge_cases_hold():
    samples = _samples()
    by_place = {(v["row"], v["column"]): v for v in VECTORS["vertices"]}
    for (r, c), vertex in by_place.items():
        best = vertex["highest_sample"]
        if best is not None:
            assert samples[(best["e"], best["n"])] == Fraction(best["z"]), (r, c)
    # (0, 0)'s highest sample is on its west edge; higher ones lie on its east and north edges
    west = by_place[(0, 0)]["highest_sample"]
    assert west["e"] == by_place[(0, 0)]["e"] - 1500
    assert samples[(by_place[(0, 0)]["e"] + 1500, 1108500)] > Fraction(west["z"])
    assert samples[(2612500, by_place[(0, 0)]["n"] + 1500)] > Fraction(west["z"])
    # (6, 5)'s highest sample is on its south edge; a higher one lies on its north edge
    south = by_place[(6, 5)]["highest_sample"]
    assert south["n"] == by_place[(6, 5)]["n"] - 1500
    assert samples[(2628500, by_place[(6, 5)]["n"] + 1500)] > Fraction(south["z"])


def test_the_likeliest_wrong_twins_give_other_bytes():
    grid = _grid()
    data = grid.astype("<f4").tobytes()
    assert np.flipud(grid).astype("<f4").tobytes() != data  # rows south to north
    assert np.fliplr(grid).astype("<f4").tobytes() != data  # columns east to west
    assert grid.T.shape != grid.shape  # swapped axes cannot even keep the shape
    samples = _samples()
    box, s = VECTORS["lv95_box"], VECTORS["spacing_m"]
    offset = VECTORS["height_offset_m"]

    def twin(closed_east=False, closed_north=False, mean=False, centre=False):
        out = grid.copy()
        for r in range(7):
            for c in range(6):
                if np.isnan(grid[r, c]):
                    continue
                e = box["e_min"] + c * s + (s / 2 if centre else 0)
                n = box["n_max"] - r * s - (s / 2 if centre else 0)
                mine = [
                    z
                    for (x, y), z in samples.items()
                    if (e - s / 2 < x <= e + s / 2 if closed_east else e - s / 2 <= x < e + s / 2)
                    and (n - s / 2 < y <= n + s / 2 if closed_north else n - s / 2 <= y < n + s / 2)
                ]
                if not mine:
                    continue
                value = sum(mine) / len(mine) if mean else max(mine)
                out[r, c] = np.float32(float(value) - offset)
        return out.astype("<f4").tobytes()

    for kind in ("closed_east", "closed_north", "mean", "centre"):
        assert twin(**{kind: True}) != data, kind
    assert twin() == data  # the twin machinery itself reproduces the rule


def test_the_step_writes_the_fixture_s_files(tmp_path):
    raw, lock = raw_regio(tmp_path / "raw")
    world = load_world(FIXTURE / "world.json")
    datasets = json.loads((FIXTURE / "datasets.json").read_text(encoding="utf-8"))["datasets"]
    config = load_surroundings_config(FIXTURE / "surroundings.json")
    out = tmp_path / "out"
    build_surroundings(world, datasets, lock, config, raw, out)
    for name in ("fixture.f32", "fixture.json"):
        assert (out / "surroundings" / name).read_bytes() == (GENERATED / name).read_bytes()
