"""Pinning tests for brief M3-07: the village's expected tree chunks and what they hold for.

Pinned decisions (m3-design.md §5 and its conventions; lessons 38 and 41): config/trees.json
is exactly {"schema": 1, "areas": {<area>: {"computed_for": {inputs_sha256, world_sha256},
"expected_sha256": {<tile>: <SHA-256 of trees/<tile>.bin>}}}}, its one area the terrain
config's, one entry per tile that has trees. The trees step reads four datasets, so
`inputs_sha256` is the SHA-256 of json.dumps({dataset: <lock entry>} over swissalti3d,
swissbuildings3d, swisssurface3d and swisstlm3d, sort_keys=True, separators=(",", ":"),
ensure_ascii=False) in UTF-8; `world_sha256` is the SHA-256 of config/world.json's bytes. The
village's six chunks were computed by design two independent ways (identical bytes): 34'412
trees, 688'240 bytes. The step compares every chunk and the set of tiles with
`expected_sha256` before writing anything, after comparing `computed_for` with the world
config and the lock. The fit of the village's `computed_for` with the committed lock is pinned
by brief M3-03, which writes the lock's swisssurface3d and swisstlm3d entries in the same
wave: this file reads no committed lock. The fixture's config records its own world and lock,
computed here independently of the pipeline's code (lesson 34).

Does NOT prove: that this machine computes those bytes (the step's own comparison does, at
the close's real run).
"""

import hashlib
import json
from pathlib import Path

import pytest

from mattini.trees import TreesError, check_trees_config, load_trees_config

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "shared" / "trees_fixture"
DATASETS = ("swissalti3d", "swissbuildings3d", "swisssurface3d", "swisstlm3d")
VILLAGE_CHUNKS = {
    "2623-1095": "69fc652cd1cb957d0aa0583c370278ae572d56b93b792328e73339cc2eae24fa",
    "2623-1096": "e4e0474920523973ffeb7b5805640df823ccd9a0f1dd4cc1d0c08951ee66846e",
    "2623-1097": "2ebf5a8147d238b6cbac77bf23b2dce0b62bb9a2058cc1798610a66c7fe4e1f6",
    "2624-1095": "89442014113296c26970640bc1ae09770a398c4b7e438fcd25e10c3ea7e2bc8e",
    "2624-1096": "d42745218831146a076fc8e77067d897cf5e1fd83fade8b1f271c08f5d0d95b6",
    "2624-1097": "765aac8e8f5b2bd365bc302f81510f9d483ec6af4ee16fafb171e761782a4271",
}
# design's record of what the village's values were computed for (m3-design.md §1's files)
VILLAGE_COMPUTED_FOR = {
    "inputs_sha256": "1eb7b79e450774e7aec8f15ebed4b8600c864de1f61d2813c49e967ad079164a",
    "world_sha256": "d2607d1362f3c7ec26b7e00c38d873b36d29db83aa169eebf60e0dd6f299509b",
}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_the_committed_config_expects_design_s_village():
    config = load_trees_config(REPO / "config" / "trees.json")
    assert config == {
        "schema": 1,
        "areas": {
            "village": {
                "computed_for": VILLAGE_COMPUTED_FOR,
                "expected_sha256": VILLAGE_CHUNKS,
            }
        },
    }
    terrain = json.loads((REPO / "config" / "terrain.json").read_text(encoding="utf-8"))
    assert list(config["areas"]) == list(terrain["areas"]), "the one area is the terrain's"


def test_computed_for_is_this_world():
    assert VILLAGE_COMPUTED_FOR["world_sha256"] == _sha(
        (REPO / "config" / "world.json").read_bytes()
    )
    # The inputs: config/datasets.lock.json gains its swisssurface3d and swisstlm3d entries in
    # this wave (brief M3-03, lane A), so their fit with VILLAGE_COMPUTED_FOR is pinned there.


def test_the_fixture_config_records_its_inputs_and_its_files():
    config = load_trees_config(FIXTURE / "trees.json")
    assert list(config["areas"]) == ["fixture"]
    settings = config["areas"]["fixture"]
    entries = json.loads((FIXTURE / "datasets.lock.json").read_text("utf-8"))["datasets"]
    four = {name: entries[name] for name in DATASETS}
    canonical = json.dumps(four, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert settings["computed_for"] == {
        "inputs_sha256": _sha(canonical.encode("utf-8")),
        "world_sha256": _sha((FIXTURE / "world.json").read_bytes()),
    }
    block = json.loads((FIXTURE / "generated" / "trees" / "fixture.json").read_text("utf-8"))
    files = {
        e["tile"]: _sha((FIXTURE / "generated" / e["file"]).read_bytes()) for e in block["chunks"]
    }
    assert settings["expected_sha256"] == files


AREA = {"computed_for": VILLAGE_COMPUTED_FOR, "expected_sha256": VILLAGE_CHUNKS}


@pytest.mark.parametrize(
    "broken",
    [
        {"schema": 1, "areas": {}},
        {"schema": 1, "areas": {"village": AREA, "other": AREA}},
        {"schema": 1, "areas": {"village": {"expected_sha256": VILLAGE_CHUNKS}}},
        {"schema": 1, "areas": {"village": {**AREA, "spacing_m": 0.5}}},
        {"schema": 1, "areas": {"village": {**AREA, "expected_sha256": {"2623_1095": "0" * 64}}}},
        {"schema": 1, "areas": {"village": {**AREA, "expected_sha256": {"2623-1095": "0"}}}},
        {"schema": 1, "areas": {"village": {**AREA, "computed_for": {"world_sha256": "0" * 64}}}},
        {"schema": 2, "areas": {"village": AREA}},
    ],
)
def test_a_config_that_is_not_exactly_its_shape_is_refused(broken):
    check_trees_config({"schema": 1, "areas": {"village": AREA}})
    with pytest.raises(TreesError):
        check_trees_config(broken)
