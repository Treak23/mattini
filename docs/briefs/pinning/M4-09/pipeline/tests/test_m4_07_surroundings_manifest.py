"""Pinning tests for brief M4-07: the surroundings fixture's manifest, the game tests' input.

Since brief M4-09 (design's replacement of M4-07's file, 2026-10-17): the fixture's manifest is
the one `write_manifest` writes after the fixture's `sky` step, so `sky` is the fixture's
generated/sky/fixture.json and no longer null; only that block, this paragraph and the SHA-256
change.

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
MANIFEST_SHA256 = "8fa084a51747793d40c9126b093851f4fd779062de06b731248629ffb7f181e1"
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
    sky = FIXTURE / "generated" / "sky" / "fixture.json"
    assert manifest["sky"] == json.loads(sky.read_text(encoding="utf-8"))
    assert manifest["sky"]["world_sha256"] == manifest["world_sha256"]
    for block in sorted(TOP_LEVEL - {"schema", "sky", "surroundings", "world", "world_sha256"}):
        assert manifest[block] is None, block
