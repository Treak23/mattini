"""Pinning test for brief M4-01: config/surroundings.json fits the committed lock and world.

The seam between lanes A and B of wave 1 (lesson 3): design committed config/surroundings.json
(brief M4-02's expected heights) with the plan, recording `computed_for` over the
`swissaltiregio` lock entry it was computed from; that entry enters the committed lock only
here (`lock regio`). M4-02's tests read no committed lock. This test is where the two meet:
`computed_for.world_sha256` is the SHA-256 of config/world.json's bytes and
`computed_for.inputs_sha256` the canonical SHA-256 of the committed lock's entry (SPEC §8),
computed here without the pipeline's helper so a wrong canonical form would not agree with
itself (lesson 34).

Does NOT prove: that the expected heights are right (design's two implementations and the
step's own comparison on the real tiles do).
"""

import hashlib
import json

from mattini.world import REPO

LOCK = json.loads((REPO / "config" / "datasets.lock.json").read_text(encoding="utf-8"))
CONFIG = json.loads((REPO / "config" / "surroundings.json").read_text(encoding="utf-8"))


def test_the_surroundings_config_was_computed_for_the_committed_entry_and_world():
    ((area, settings),) = CONFIG["areas"].items()
    entry = LOCK["datasets"]["swissaltiregio"]
    canonical = json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    world = (REPO / "config" / "world.json").read_bytes()
    assert settings["computed_for"] == {
        "inputs_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "world_sha256": hashlib.sha256(world).hexdigest(),
    }, area
