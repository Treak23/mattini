"""Pinning tests for brief M3-07: the masks shown both ways, a lone tree, and the two refusals.

Pinned decisions (m3-design §5, the trees): the footprint mask F takes every building of
the sheets whose bounding box meets the area, selected by the buildings step or not, and
every TLM_GEBAEUDE_FOOTPRINT polygon (even-odd over all its rings) but those of OBJEKTART 16
(Unterirdisches Gebaeude: no roof above ground); the rock mask R takes
TLM_BODENBEDECKUNG of OBJEKTART 1, 2, 3 and 4 only. Each case below takes one input away
from the shared fixture and sees the tree the input had removed come back (or, for the
courtyard's hole and the underground building read as an ordinary one, go): the fixture
test shows the other way. A tree alone in its area has no nearest tree: d is infinite, so its
crown radius is clamp(height / 4, 1.0, 6.0), not 6.0. Refused: a canopy height v
that is not a whole multiple of 2^-13 m (the exact integer rule holds for heights from
1024 to 4096 m only), naming the pixel's LV95 centre; a world config whose axes are not
the owner's (x = +e, y = +h, z = -n), since the trees stand on the terrain grid, which
supports no other (SPEC §8).

Does NOT prove: that swisstopo's files hold what the readers hand over (the real run).
"""

import copy
import json
import struct
from pathlib import Path

import numpy as np
import pytest

from mattini.trees import TreesError, build_tree_chunks
from mattini.world import load_world

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "shared" / "trees_fixture"
SIZE = 96


def _inputs() -> dict:
    tlm = json.loads((FIXTURE / "tlm.json").read_text("utf-8"))
    return {
        "dsm": np.fromfile(FIXTURE / "dsm.f32", dtype="<f4").reshape(SIZE, SIZE),
        "dtm": np.fromfile(FIXTURE / "dtm.f32", dtype="<f4").reshape(SIZE, SIZE),
        "buildings": json.loads((FIXTURE / "buildings.json").read_text("utf-8"))["features"],
        "footprints": tlm["TLM_GEBAEUDE_FOOTPRINT"],
        "land_cover": tlm["TLM_BODENBEDECKUNG"],
    }


def _trees_at(inputs: dict, world=None) -> set[tuple[float, float]]:
    """The (x, z) of every tree the rule gives for `inputs`."""
    world = world or load_world(FIXTURE / "world.json")
    chunks = build_tree_chunks(
        inputs["dsm"],
        inputs["dtm"],
        inputs["buildings"],
        inputs["footprints"],
        inputs["land_cover"],
        world,
        "fixture",
    )
    return {
        struct.unpack_from("<5f", c["data"], k)[0:3:2]
        for c in chunks
        for k in range(0, len(c["data"]), 20)
    }


def _xz(i: int, j: int) -> tuple[float, float]:
    east, north = 2650976.25 + 0.5 * j, 1150023.75 - 0.5 * i
    return (float(np.float32(east - 2650012.0)), float(np.float32(-(north - 1149988.0))))


def _without(key: str, uuid: str):
    def change(inputs: dict) -> None:
        kept = [f for f in inputs[key] if f["uuid"] != uuid]
        assert len(kept) == len(inputs[key]) - 1, uuid
        inputs[key] = kept

    return change


def _underground_as_a_building(inputs: dict) -> None:
    for feature in inputs["footprints"]:
        if feature["objektart"] == 16:
            feature["objektart"] = 0


def _exterior_only(inputs: dict) -> None:
    for feature in inputs["footprints"]:
        feature["polygons"] = [polygon[:1] for polygon in feature["polygons"]]


@pytest.mark.parametrize(
    ("change", "pixels", "appears"),
    [
        # the roof of a building whose bounding-box centre lies north of the area
        (_without("buildings", "{7EE50000-0000-4000-8000-000000000002}"), [(2, 40)], True),
        # the roof of the selected building
        (_without("buildings", "{7EE50000-0000-4000-8000-000000000003}"), [(78, 78)], True),
        # the tiny building: the crown whose top was exactly 2.0 m from its corner
        (_without("buildings", "{7EE50000-0000-4000-8000-000000000001}"), [(26, 30)], True),
        # the roof of a building only TLM holds (OBJEKTART 10, Im Bau)
        (_without("footprints", "{7EE5F000-0000-4000-8000-000000000002}"), [(56, 74)], True),
        # the Fels rectangle: the crowns on its west and south edges
        (
            _without("land_cover", "{7EE5B000-0000-4000-8000-000000000001}"),
            [(28, 58), (34, 64)],
            True,
        ),
        # the Felsbloecke locker polygon (OBJEKTART 4)
        (_without("land_cover", "{7EE5B000-0000-4000-8000-000000000003}"), [(84, 60)], True),
        # the courtyard's hole filled: its tree goes
        (_exterior_only, [(60, 13)], False),
        # the underground building (OBJEKTART 16) read as an ordinary one: its crown goes
        (_underground_as_a_building, [(68, 40)], False),
    ],
    ids=[
        "unselected building",
        "selected building",
        "tiny building",
        "TLM-only footprint",
        "Fels",
        "Felsbloecke locker",
        "courtyard without its hole",
        "underground building as a building",
    ],
)
def test_each_mask_input_decides_its_trees(change, pixels, appears):
    before = _trees_at(_inputs())
    inputs = copy.deepcopy(_inputs())
    change(inputs)
    after = _trees_at(inputs)
    for i, j in pixels:
        assert (_xz(i, j) in before) is not appears, (i, j)
        assert (_xz(i, j) in after) is appears, (i, j)


def test_a_tree_alone_takes_a_quarter_of_its_height():
    inputs = _inputs()
    lone = inputs["dtm"].copy()
    window = (slice(38, 47), slice(26, 35))  # the 18 m crown at (42, 30) and nothing else
    lone[window] = inputs["dsm"][window]
    inputs["dsm"] = lone
    world = load_world(FIXTURE / "world.json")
    chunks = build_tree_chunks(
        inputs["dsm"],
        inputs["dtm"],
        inputs["buildings"],
        inputs["footprints"],
        inputs["land_cover"],
        world,
        "fixture",
    )
    assert [(c["tile"], c["trees"]) for c in chunks] == [("2650-1150", 1)]
    x, _, z, height, radius = struct.unpack("<5f", chunks[0]["data"])
    assert (x, z) == _xz(42, 30)
    assert (height, radius) == (18.0, 4.5), "clamp(18 / 4, 1, 6): no nearest tree, d infinite"


def test_a_canopy_height_off_the_2_13_grid_is_refused():
    inputs = _inputs()
    # below 1024 m a float32 has bits finer than 2^-13 m: v = 10 + 2^-14 m here, at a pixel
    # 10 m and more from every footprint, so no margin can hide it
    inputs["dtm"] = inputs["dtm"].copy()
    inputs["dsm"] = inputs["dsm"].copy()
    inputs["dtm"][90, 50] = np.float32(1000.0)
    inputs["dsm"][90, 50] = np.float32(1010.0 + 2.0**-14)
    assert float(inputs["dsm"][90, 50]) - 1000.0 == 10.0 + 2.0**-14
    with pytest.raises(TreesError) as refusal:
        _trees_at(inputs)
    message = str(refusal.value)
    assert "2651001.25" in message and "1149978.75" in message, message


def test_only_the_owner_s_axes(tmp_path):
    data = json.loads((FIXTURE / "world.json").read_text("utf-8"))
    data["axes"] = {"x": "+n", "y": "+h", "z": "+e"}  # a proper rotation, not the owner's
    path = tmp_path / "world.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(TreesError, match="axes"):
        _trees_at(_inputs(), load_world(path))
