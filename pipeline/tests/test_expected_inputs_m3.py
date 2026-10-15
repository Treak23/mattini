"""Pinning tests for brief M3-03: the new steps' expected values fit the committed lock.

Pinned decisions (docs/SPEC.md §8, the expected output, and its rule for a step with several
datasets): each step config design committed with the M3 plan records `computed_for`, the
SHA-256 of config/world.json's bytes and, for its inputs, the SHA-256 of the lock entry it
reads rendered canonically (sorted keys, no spaces, UTF-8): photo swissimage, surfaces
swisstlm3d. A step that reads several datasets records the SHA-256 of {dataset: entry} over
exactly those datasets, rendered the same way: roofs swissbuildings3d and swissimage; trees
swissalti3d, swissbuildings3d, swisssurface3d and swisstlm3d. The lock this brief writes and
commits must give those values. This is the seam between lane A's lock and the steps of
lanes C and D (briefs M3-04 to M3-07), whose own tests do not read the committed lock: it
gains these entries in the same wave.

Does NOT prove: that the expected values themselves are right (design's two
implementations and the steps' own comparisons do).
"""

import hashlib
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def _canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.mark.parametrize(
    ("config", "datasets"),
    [
        ("config/photo.json", ["swissimage"]),
        ("config/surfaces.json", ["swisstlm3d"]),
        ("config/roofs.json", ["swissbuildings3d", "swissimage"]),
        (
            "config/trees.json",
            ["swissalti3d", "swissbuildings3d", "swisssurface3d", "swisstlm3d"],
        ),
    ],
)
def test_each_step_config_was_computed_for_the_committed_lock(config, datasets):
    areas = json.loads((REPO / config).read_text(encoding="utf-8"))["areas"]
    assert list(areas) == ["village"], config
    entries = json.loads((REPO / "config" / "datasets.lock.json").read_text(encoding="utf-8"))[
        "datasets"
    ]
    if len(datasets) == 1:
        inputs = _canonical(entries[datasets[0]])
    else:
        inputs = _canonical({name: entries[name] for name in datasets})
    assert areas["village"]["computed_for"] == {
        "inputs_sha256": _sha(inputs),
        "world_sha256": _sha((REPO / "config" / "world.json").read_bytes()),
    }, config


def test_a_step_with_several_datasets_hashes_them_together_not_one_by_one():
    entries = json.loads((REPO / "config" / "datasets.lock.json").read_text(encoding="utf-8"))[
        "datasets"
    ]
    roofs = json.loads((REPO / "config" / "roofs.json").read_text(encoding="utf-8"))
    recorded = roofs["areas"]["village"]["computed_for"]["inputs_sha256"]
    for name in ("swissbuildings3d", "swissimage"):
        assert recorded != _sha(_canonical(entries[name])), name
