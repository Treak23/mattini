"""Pinning tests for brief M3-07: built_trees_block, the check of a built trees block.

Pinned decisions (m3-design §5 and its conventions; lesson 41): `built_trees_block(out_dir,
trees_config, terrain_config, world, world_sha256, datasets, lock)` returns the description
`trees/<area>.json` built in `out_dir` once it is shown to match (the area is the terrain
config's), or None when none is built; the manifest will copy it as its `trees` block (a
later brief wires it). First it compares the trees config's `computed_for` with the world
config and the four lock entries: a difference names design's step ("design recomputes"),
never this machine or this code. Then a built block that no longer matches is refused naming
`python -m mattini trees`, among others a chunk file whose bytes changed.

Does NOT prove: the other refusals (exact key sets, box, source, sizes), which the brief's
own tests cover.
"""

import copy
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from mattini.trees import TreesError, built_trees_block
from mattini.world import load_world

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "shared" / "trees_fixture"


def _json(name: str) -> dict:
    return json.loads((FIXTURE / name).read_text("utf-8"))


def _check(out_dir: Path, trees_config: dict | None = None):
    world_path = FIXTURE / "world.json"
    return built_trees_block(
        out_dir,
        trees_config or _json("trees.json"),
        _json("terrain.json"),
        load_world(world_path),
        hashlib.sha256(world_path.read_bytes()).hexdigest(),
        _json("datasets.json")["datasets"],
        _json("datasets.lock.json"),
    )


def _copy(tmp_path: Path) -> Path:
    out = tmp_path / "generated"
    shutil.copytree(FIXTURE / "generated" / "trees", out / "trees")
    return out


def test_the_fixture_s_built_block_is_accepted():
    block = _check(FIXTURE / "generated")
    assert block == json.loads(
        (FIXTURE / "generated" / "trees" / "fixture.json").read_text("utf-8")
    )


def test_nothing_built_gives_none(tmp_path):
    assert _check(tmp_path) is None


def test_a_changed_chunk_file_is_refused_naming_the_command(tmp_path):
    out = _copy(tmp_path)
    chunk = out / "trees" / "2651-1150.bin"
    data = bytearray(chunk.read_bytes())
    data[7] ^= 1  # same size, other bytes
    chunk.write_bytes(bytes(data))
    with pytest.raises(TreesError) as refusal:
        _check(out)
    message = str(refusal.value)
    assert "python -m mattini trees" in message and "2651-1150" in message, message


@pytest.mark.parametrize(
    ("key", "needle"),
    [("world_sha256", "config/world.json"), ("inputs_sha256", "datasets.lock.json")],
)
def test_a_changed_world_or_input_names_design_s_step(tmp_path, key, needle):
    config = copy.deepcopy(_json("trees.json"))
    config["areas"]["fixture"]["computed_for"][key] = "0" * 64
    with pytest.raises(TreesError) as refusal:
        _check(_copy(tmp_path), config)
    message = str(refusal.value)
    assert needle in message and "design recomputes" in message, message
    assert "this machine or this code" not in message
