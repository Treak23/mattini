"""Brief M3-R1-fix-2: the trees tie the terrain to 0.5 m, and say so instead of floating.

Design's answer to M3 R1 P-01 (the owner's word, 2026-10-15, SPEC §13 row 37): a tree's base
height comes from the 0.5 m terrain grid (SPEC §8, trees, item 7), so a terrain config whose
`spacing_m` is not 0.5 is refused by the trees step and by the manifest's trees block, naming
config/terrain.json, instead of writing trees that float or sink on a 1 m or 2 m terrain (the
placement lens measured 3'542 of 34'412 trees more than 5 cm off at 1 m, 18'932 at 2 m).

Pinned decisions:
1. `build_trees` refuses a spacing other than 0.5 with a TreesError whose message names
   `config/terrain.json`, the spacing found and 0.5, before it reads the lock or any input and
   before it creates anything under `out_dir` (the call below passes an empty lock and a raw
   folder that does not exist; neither may be the reason for the refusal).
2. `built_trees_block` refuses the same spacing when trees are built (their description
   exists), with the same naming, and returns None when none are built: a terrain-only
   manifest at 1 m is not blocked by trees nobody built.
3. At 0.5 the spacing refusal does not fire (the twin: a check that refuses every spacing).

Does NOT prove: that the trees stand on the 0.5 m terrain (fix-1's scene test and the
placement lens's census do); the terrain step at 1 m or 2 m (its own tests).
"""

import copy
import hashlib
import json
from pathlib import Path

import pytest

from mattini.datasets import load_datasets
from mattini.terrain import load_terrain_config
from mattini.trees import TreesError, build_trees, built_trees_block, load_trees_config
from mattini.world import REPO, load_world

WORLD_SHA256 = hashlib.sha256((REPO / "config" / "world.json").read_bytes()).hexdigest()


def _terrain(spacing):
    config = copy.deepcopy(load_terrain_config())
    (area,) = config["areas"]
    config["areas"][area]["spacing_m"] = spacing
    return config


def _is_spacing_refusal(exc: TreesError, spacing) -> bool:
    text = str(exc)
    return "config/terrain.json" in text and "0.5" in text and format(spacing, "g") in text


@pytest.mark.parametrize("spacing", [1.0, 2.0])
def test_the_trees_step_refuses_a_terrain_that_is_not_half_a_metre(tmp_path, spacing):
    out = tmp_path / "out"
    seen = []
    with pytest.raises(TreesError) as caught:
        build_trees(
            load_world(),
            load_datasets(),
            {},
            load_trees_config(),
            _terrain(spacing),
            tmp_path / "no-raw-folder",
            out,
            progress=seen.append,
        )
    assert _is_spacing_refusal(caught.value, spacing), str(caught.value)
    assert not out.exists(), "nothing may be created before the refusal"
    assert seen == [], "no progress line before the refusal"


def test_at_half_a_metre_the_spacing_is_not_the_refusal(tmp_path):
    with pytest.raises(TreesError) as caught:  # the empty lock or the missing inputs refuse
        build_trees(
            load_world(),
            load_datasets(),
            {},
            load_trees_config(),
            _terrain(0.5),
            tmp_path / "no-raw-folder",
            tmp_path / "out",
        )
    assert "config/terrain.json" not in str(caught.value) or "spacing" not in str(caught.value)


def _write_description(out: Path, area: str) -> None:
    (out / "trees").mkdir(parents=True)
    (out / "trees" / f"{area}.json").write_text(json.dumps({"stand-in": True}))


@pytest.mark.parametrize("spacing", [1.0, 2.0])
def test_the_manifest_refuses_built_trees_on_a_terrain_that_is_not_half_a_metre(tmp_path, spacing):
    terrain = _terrain(spacing)
    (area,) = terrain["areas"]
    _write_description(tmp_path, area)
    world = load_world()
    with pytest.raises(TreesError) as caught:
        built_trees_block(
            tmp_path, load_trees_config(), terrain, world, WORLD_SHA256, load_datasets(), {}
        )
    assert _is_spacing_refusal(caught.value, spacing), str(caught.value)


@pytest.mark.parametrize("spacing", [1.0, 2.0])
def test_no_trees_built_is_no_refusal_at_any_spacing(tmp_path, spacing):
    world = load_world()
    block = built_trees_block(
        tmp_path, load_trees_config(), _terrain(spacing), world, WORLD_SHA256, load_datasets(), {}
    )
    assert block is None
