"""What a test config's expected values were computed for (brief M2-07; SPEC §8).

Each area of a terrain or buildings config records `computed_for`: the SHA-256 of the
world config's bytes and of the lock's entry for its dataset rendered canonically
(`json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`, UTF-8).
A test that makes its own world or lock records them here, the way design records them
for the committed configs. Computed here, not with the pipeline's `lock.entry_sha256`, so
a canonical form the pipeline got wrong would not agree with itself (lesson 34).

`recorded(config, world, lock, dataset)` is a copy of a config whose areas record that
world and lock: "design computed these values for these inputs". A test that changes an
input and records the change is testing what comes after the check; one that changes an
input without recording it is testing the check.
"""

import copy
import hashlib
import json
from pathlib import Path


def _world_bytes(world) -> bytes:
    """`world` as bytes: a World (its file), a path, or the bytes themselves."""
    if isinstance(world, bytes):
        return world
    return Path(getattr(world, "path", world)).read_bytes()


def computed_for(world, lock: dict, dataset: str) -> dict:
    """`computed_for` for the world config `world` and the lock's entry for `dataset`."""
    entry = json.dumps(
        lock["datasets"][dataset], sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return {
        "inputs_sha256": hashlib.sha256(entry).hexdigest(),
        "world_sha256": hashlib.sha256(_world_bytes(world)).hexdigest(),
    }


def recorded(config: dict, world, lock: dict, dataset: str) -> dict:
    """A copy of `config` whose every area records `computed_for(world, lock, dataset)`."""
    config = copy.deepcopy(config)
    for area in config["areas"].values():
        area["computed_for"] = computed_for(world, lock, dataset)
    return config
