"""The transforms beyond the pinned vectors: round trips, the height offset, 64-bit maths.

The height-offset test pins the reading this brief took (a Findings item of M0-02):
`height_offset_m` is the vertical part of the origin, subtracted like the easting and
northing, so y = H - height_offset_m. The shipped config's offset is 0.0, where every
reading agrees.
"""

import json
import random
from pathlib import Path

import pytest

from mattini.world import load_world

REPO = Path(__file__).resolve().parents[2]
CONFIG = REPO / "config" / "world.json"
VECTORS = json.loads((REPO / "tests" / "shared" / "world_vectors.json").read_text("utf-8"))


def test_height_offset_is_subtracted_from_heights(tmp_path):
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    data["height_offset_m"] = 1000.0
    path = tmp_path / "world.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    world = load_world(path)
    assert world.height_offset == 1000.0
    assert world.to_local(world.origin_e + 3.0, world.origin_n + 4.0, 1600.0) == (3.0, 600.0, -4.0)
    assert world.to_lv95(3.0, 600.0, -4.0) == (world.origin_e + 3.0, world.origin_n + 4.0, 1600.0)


@pytest.mark.parametrize("vec", VECTORS["vectors"], ids=lambda v: v["name"])
def test_shared_vectors_round_trip_exactly(vec):
    world = load_world()
    assert world.to_lv95(*world.to_local(*vec["lv95"])) == tuple(vec["lv95"])


def test_random_points_round_trip_within_a_micrometre():
    world = load_world()
    rng = random.Random(20260924)
    for _ in range(1000):
        point = (
            world.origin_e + rng.uniform(-30000.0, 30000.0),
            world.origin_n + rng.uniform(-30000.0, 30000.0),
            rng.uniform(-500.0, 5000.0),
        )
        assert world.to_lv95(*world.to_local(*point)) == pytest.approx(point, abs=1e-6)


def test_the_32_bit_trap_point_keeps_its_centimetres():
    """The origin is subtracted in 64-bit: the trap vector's fractions survive."""
    trap = next(v for v in VECTORS["vectors"] if "32-bit trap" in v["name"])
    x, y, z = load_world().to_local(*trap["lv95"])
    assert abs(x - 825.13) < 1e-6 and abs(z + 489.77) < 1e-6 and abs(y - 1606.37) < 1e-9
