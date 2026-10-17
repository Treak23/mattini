"""Pinning tests for brief M4-07: the surroundings fixture's manifest, the game tests' input.

Pinned decisions (brief M4-07; docs/SPEC.md §8, *The manifest*): design wrote
tests/shared/surroundings_fixture/generated/manifest.json with the plan, in the shape brief
M4-09's `write_manifest` will write: the top level is exactly M3's keys plus `shadows`, `sky`
and `surroundings`; `surroundings` is the step's description generated/surroundings/fixture.json
verbatim; `world` is the fixture's world.json and `world_sha256` the SHA-256 of its bytes; every
other block is null; the text is `json.dumps(manifest, indent=2, sort_keys=True,
ensure_ascii=False)` and a final LF, in UTF-8. Its SHA-256 is pinned here too, so a fixture
rewritten by the code under test fails even where the comparison would follow it (lesson 33).

Does NOT prove: that `write_manifest` writes this (brief M4-09, which may rewrite the fixture's
other blocks in its own shape: the game reads only `world`, `world_sha256` and
`surroundings`); that the game reads it (test_m4_07_surroundings_grid.gd).
"""

import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "shared" / "surroundings_fixture"
MANIFEST = FIXTURE / "generated" / "manifest.json"
MANIFEST_SHA256 = "a42c5a91e2f17e8e2d0608653b7d46cedf8102aff1e12b1c1dfe35516b2638d4"
TOP_LEVEL = {
    "buildings",
    "photo",
    "roofs",
    "schema",
    "shadows",
    "sky",
    "surfaces",
    "surroundings",
    "terrain",
    "trees",
    "world",
    "world_sha256",
}


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_the_manifest_is_design_s_bytes():
    assert hashlib.sha256(MANIFEST.read_bytes()).hexdigest() == MANIFEST_SHA256


def test_the_text_is_the_manifest_writer_s_format():
    manifest = _manifest()
    text = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    assert MANIFEST.read_bytes() == text.encode("utf-8")


def test_its_blocks_are_the_fixture_s_files():
    manifest = _manifest()
    assert set(manifest) == TOP_LEVEL
    assert manifest["schema"] == 1
    description = FIXTURE / "generated" / "surroundings" / "fixture.json"
    assert manifest["surroundings"] == json.loads(description.read_text(encoding="utf-8"))
    raw = (FIXTURE / "world.json").read_bytes()
    assert manifest["world"] == json.loads(raw)
    assert manifest["world_sha256"] == hashlib.sha256(raw).hexdigest()
    assert manifest["surroundings"]["world_sha256"] == manifest["world_sha256"]
    for block in sorted(TOP_LEVEL - {"schema", "surroundings", "world", "world_sha256"}):
        assert manifest[block] is None, block
