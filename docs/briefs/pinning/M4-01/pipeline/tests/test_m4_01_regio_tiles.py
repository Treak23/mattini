"""Pinning tests for brief M4-01: which swissALTIRegio tiles an area's surroundings need.

Pinned decisions (m4-design §1, §2; measured on the live STAC API, 2026-10-17):

- swissALTIRegio is published in 10 km tiles whose south-west corners lie at E = 5 km + 10 km·i
  and N = 4 km + 10 km·j (all 2'365 items); a tile is named by that corner in whole
  kilometres, four digits each: `2615-1084`, and `2385-0974` in the south-west.
- The surroundings box is the area's box grown by `margin_m` on every side (m4-design §2). A
  vertex every `spacing_m` takes its height from the samples in the half-open square
  [E − s/2, E + s/2) × [N − s/2, N + s/2), so the samples needed are those in
  [e_min − s/2, e_max + s/2) × [n_min − s/2, n_max + s/2) of the surroundings box.
  `download.regio_tiles(world, area, *, margin_m, spacing_m)` gives every tile whose square
  [E0, E0 + 10 km) × [N0, N0 + 10 km) meets that region, east outer and north inner, sorted:
  the order of the lock, the download and provenance.json.
- The village (margin 20 km, spacing 100 m; box E 2'603'000–2'645'000, N 1'075'000–1'118'000)
  needs 6 × 5 = 30 tiles. Its east edge lies on a tile edge: the column 2645 is needed for the
  half square east of the last vertices (its samples E 2'645'005 … 2'645'045).

Likeliest wrong twins: the area box without the margin; the box without the half-spacing
border (30 → 25 tiles: the column 2645 lost, the east edge's heights silently from half
squares); tiles counted from 0 km instead of the measured lattice; ids not zero-padded;
north outer.

Does NOT prove: that swisstopo keeps this tiling (the lock's STAC read refuses a missing
item; the step refuses a sample outside its tile, brief M4-02).
"""

import json

import pytest

from mattini import download
from mattini.world import REPO, load_world

VILLAGE = [
    f"{e}-{n}" for e in (2595, 2605, 2615, 2625, 2635, 2645) for n in (1074, 1084, 1094, 1104, 1114)
]


def _world(tmp_path, box):
    data = json.loads((REPO / "config" / "world.json").read_text(encoding="utf-8"))
    data["areas"] = {"here": dict(zip(("e_min", "e_max", "n_min", "n_max"), box, strict=True))}
    path = tmp_path / "world.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return load_world(path)


def test_the_village_needs_the_thirty_measured_tiles():
    world = load_world()
    tiles = download.regio_tiles(world, "village", margin_m=20000, spacing_m=100)
    assert tiles == VILLAGE


def test_the_area_box_alone_is_not_the_surroundings():
    world = load_world()
    # the area alone: its east edge E 2'625'000 is a tile edge, so two tiles
    assert download.regio_tiles(world, "village", margin_m=0, spacing_m=100) == [
        "2615-1094",
        "2625-1094",
    ]


@pytest.mark.parametrize(
    ("box", "spacing", "tiles"),
    [
        # east edge on a tile edge: the half square east of it reaches the next column
        ((2_606_000.0, 2_615_000.0, 1_095_000.0, 1_096_000.0), 100, ["2605-1094", "2615-1094"]),
        # 50 m inside the tile edge: half of 100 m is 50 m, and the square is half-open
        ((2_606_000.0, 2_614_950.0, 1_095_000.0, 1_096_000.0), 100, ["2605-1094"]),
        # west edge 50 m east of a tile edge: the half square starts on it, the west tile is out
        ((2_615_050.0, 2_616_000.0, 1_095_000.0, 1_096_000.0), 100, ["2615-1094"]),
        # 40 m east of it: the half square reaches 10 m into the west tile
        ((2_615_040.0, 2_616_000.0, 1_095_000.0, 1_096_000.0), 100, ["2605-1094", "2615-1094"]),
        # south edge on a tile edge, the same rule on the other axis
        ((2_606_000.0, 2_607_000.0, 1_094_000.0, 1_095_000.0), 100, ["2605-1084", "2605-1094"]),
        # north edge 50 m south of a tile edge: the half square ends on it
        ((2_606_000.0, 2_607_000.0, 1_095_000.0, 1_103_950.0), 100, ["2605-1094"]),
        ((2_606_000.0, 2_607_000.0, 1_095_000.0, 1_103_960.0), 100, ["2605-1094", "2605-1104"]),
    ],
)
def test_a_tile_is_needed_when_its_square_meets_the_samples_of_the_vertices(
    tmp_path, box, spacing, tiles
):
    world = _world(tmp_path, box)
    assert download.regio_tiles(world, "here", margin_m=0, spacing_m=spacing) == tiles


def test_tile_ids_are_four_digits_each_and_east_is_outer(tmp_path):
    world = _world(tmp_path, (2_486_000.0, 2_487_000.0, 983_000.0, 985_000.0))
    assert download.regio_tiles(world, "here", margin_m=1000, spacing_m=100) == [
        "2475-0974",
        "2475-0984",
        "2485-0974",
        "2485-0984",
    ]
