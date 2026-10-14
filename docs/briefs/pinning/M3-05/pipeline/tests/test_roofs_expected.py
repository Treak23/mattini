"""Pinning tests for brief M3-05: the village's expected roof colours and what they hold for.

Pinned decisions (m3-design.md §3 and its conventions; lessons 38 and 41): config/roofs.json
is exactly {"schema": 1, "areas": {<area>: {"computed_for": {inputs_sha256, world_sha256},
"expected_sha256": <SHA-256 of roofs/<area>.json>}}}, its one area the terrain config's.
The roofs step reads two datasets, so `inputs_sha256` is the SHA-256 of
json.dumps({"swissbuildings3d": <lock entry>, "swissimage": <lock entry>}, sort_keys=True,
separators=(",", ":"), ensure_ascii=False) in UTF-8, over exactly those two entries of
config/datasets.lock.json; `world_sha256` is the SHA-256 of config/world.json's bytes. The
village's roofs/village.json was computed by design two independent ways (identical bytes,
290'006 bytes): 1'486 buildings, every one with a roof colour, 30'392'135 roof pixels. The
step compares the SHA-256 of the bytes it would write with `expected_sha256` before writing
anything, after comparing `computed_for` with the world config and the lock. The fit of
`computed_for` with the committed lock is pinned by brief M3-03, which writes the lock's
swissimage entry in the same wave; this file reads no committed lock.

Does NOT prove: that this machine computes those bytes (the step's own comparison does, at
the close's real run); that the colours look right (the owner's eyes).
"""

import hashlib
import json
from pathlib import Path

import pytest

from mattini.roofs import RoofsError, check_roofs_config, load_roofs_config

REPO = Path(__file__).resolve().parents[2]
VILLAGE_ROOFS = "8d9664b643173eaee7d1980438600c7bcb7dd8d1921346466ec72b716c480db5"
# design's record of what the village's value was computed for (m3-design.md §1's tiles)
VILLAGE_COMPUTED_FOR = {
    "inputs_sha256": "e66bee6eefdf491cbcf1dcca8ca87632d0779802f777b1caedc4a09009ca9a48",
    "world_sha256": "d2607d1362f3c7ec26b7e00c38d873b36d29db83aa169eebf60e0dd6f299509b",
}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_the_committed_config_expects_design_s_village():
    config = load_roofs_config(REPO / "config" / "roofs.json")
    assert config == {
        "schema": 1,
        "areas": {
            "village": {
                "computed_for": VILLAGE_COMPUTED_FOR,
                "expected_sha256": VILLAGE_ROOFS,
            }
        },
    }
    terrain = json.loads((REPO / "config" / "terrain.json").read_text(encoding="utf-8"))
    assert list(config["areas"]) == list(terrain["areas"]), "the one area is the terrain's"


def test_computed_for_is_this_world():
    assert VILLAGE_COMPUTED_FOR["world_sha256"] == _sha(
        (REPO / "config" / "world.json").read_bytes()
    )
    # The inputs: config/datasets.lock.json gains its swissimage entry in this wave (brief
    # M3-03, lane A), so its fit with VILLAGE_COMPUTED_FOR is pinned by that brief, not here.


AREA = {"computed_for": VILLAGE_COMPUTED_FOR, "expected_sha256": VILLAGE_ROOFS}


@pytest.mark.parametrize(
    "broken",
    [
        {"schema": 1, "areas": {}},
        {"schema": 1, "areas": {"village": AREA, "other": AREA}},
        {"schema": 1, "areas": {"village": {"expected_sha256": VILLAGE_ROOFS}}},
        {"schema": 1, "areas": {"village": {**AREA, "spacing_m": 0.5}}},
        {"schema": 1, "areas": {"village": {**AREA, "expected_sha256": {"0.2": VILLAGE_ROOFS}}}},
        {"schema": 1, "areas": {"village": {**AREA, "computed_for": {"world_sha256": "0" * 64}}}},
        {"schema": 2, "areas": {"village": AREA}},
    ],
)
def test_a_config_that_is_not_exactly_its_shape_is_refused(broken):
    check_roofs_config({"schema": 1, "areas": {"village": AREA}})
    with pytest.raises(RoofsError):
        check_roofs_config(broken)
