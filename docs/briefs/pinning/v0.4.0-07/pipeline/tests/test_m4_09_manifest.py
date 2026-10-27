"""Pinning tests for brief v0.4.0-07 (brief M4-09 cut to the sky): the manifest's `sky` block.

Pinned decisions (m4-design §4; brief M4-09 decisions 2 and 3, the sky only; brief v0.4.0-07):
the manifest's top level is exactly `buildings`, `photo`, `roofs`, `schema`, `sky`,
`surfaces`, `terrain`, `trees`, `world` and `world_sha256` (ten keys: M3-13's nine and `sky`;
no `surroundings` or `shadows` key until their steps exist); `schema` stays 1; the `sky` block
is the description `python -m mattini sky` wrote, `sky/<area>.json` for config/sky.json's area,
verbatim, or null when that step has not been run in the folder (brief M3-13's rule for every
block): never computed by `manifest` from the config, never left out, never an empty object;
the text is `json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False)` and a final
LF, in UTF-8.

The seven M2 and M3 fixtures' committed manifests are their previous text plus one line,
`  "sky": null,` (between `schema` and `surfaces`), nothing else: design's copies, made two
ways (that text edit, and the pin author's throwaway `write_manifest`; identical). Their SHA-256
before the line (PREVIOUS: M3-13's, the surfaces fixture's from brief v0.4.0-01) and after it
(test_manifest_m3.py) are both pinned, so a fixture rewritten by the code under test fails
even where a bytes comparison would follow it (lesson 33).

The shadows and surroundings fixtures hold a sky config (`sky.json`) and its description
(`generated/sky/fixture.json`, design data; test_m4_09_sky_step.py): a folder holding only that
description, with the fixture's world and sky config, gives a manifest whose `sky` block is
the description and every other block null, at the SHA-256 pinned here (SKY_FIXTURES, made two
ways: assembled by hand from the description and the world, and the throwaway). The
surroundings fixture's own committed `generated/manifest.json` (twelve keys, M4-07's, read by
no test) is not this brief's and stays as it is.

Does NOT prove: that the game reads the sky block (brief v0.4.0-08); that the real village's
manifest is design's (the release gate, against the plan's pair).
"""

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from mattini.manifest import write_manifest

REPO = Path(__file__).resolve().parents[2]
SHARED = REPO / "tests" / "shared"
TOP_LEVEL = {
    "buildings",
    "photo",
    "roofs",
    "schema",
    "sky",
    "surfaces",
    "terrain",
    "trees",
    "world",
    "world_sha256",
}
BLOCKS = sorted(TOP_LEVEL - {"schema", "world", "world_sha256"})
SKY_LINE = '  "sky": null,'
# Each M2 and M3 fixture's committed manifest before this brief (nine keys).
PREVIOUS = {
    "terrain_fixture": "1a7e6ba22265c5c3bbb83b8d250dfaf31b41fb77a5d945011c51b289eef86c43",
    "terrain_fixture_nw": "25f595d251e264111b8ed6374b9e7acc36c149c99bcf42af0fd49c2a4f16ae07",
    "buildings_fixture": "83357e6c490233e916a8d6af4baabaf8244a8710bf3758f5e876baa01228ed4a",
    "photo_fixture": "e7fd45d45d4f3feb2b9a4f24d0ab6080ea7afc57e1d96b270eefc499f754b39f",
    "roofs_fixture": "588fee50d5cbe55a6cfb90fe36c1d9831a4742eb8a7e5c67031c221695325489",
    "surfaces_fixture": "58ebd442501261b40b342f1b0fabc0886909f4ae48844fd6095403ec49762be4",
    "trees_fixture": "669db5fb6300423b64c41aefc3919e0b86c0363a17b5fe29d9c8adec0b8ebef8",
}
# A folder holding only the fixture's sky description: the manifest's SHA-256 and size.
SKY_FIXTURES = {
    "shadows_fixture": ("0286b7251a22a5c80590ba9407225afe3870f416cb99d68b58620cf42da618cd", 888),
    "surroundings_fixture": (
        "83e3937c6c240db8c25665e38fc9ddb299be358c7ac29e9215aecd0eceb372ff",
        889,
    ),
}


def _sky_only(tmp_path, name: str) -> Path:
    """A folder holding only the fixture's committed `sky/` (its description)."""
    out = tmp_path / "generated"
    shutil.copytree(SHARED / name / "generated" / "sky", out / "sky")
    return out


@pytest.mark.parametrize("name", sorted(PREVIOUS))
def test_an_m3_fixture_s_manifest_is_its_previous_text_with_one_null_line(name):
    """The seven earlier fixtures change by exactly the one line, nothing else (their blocks,
    world and world_sha256 stay byte for byte)."""
    raw = (SHARED / name / "generated" / "manifest.json").read_bytes()
    lines = raw.decode("utf-8").split("\n")
    assert lines.count(SKY_LINE) == 1, name
    at = lines.index(SKY_LINE)
    assert lines[at - 1] == '  "schema": 1,' and lines[at + 1].startswith('  "surfaces": '), name
    previous = "\n".join(lines[:at] + lines[at + 1 :]).encode("utf-8")
    assert hashlib.sha256(previous).hexdigest() == PREVIOUS[name], name
    manifest = json.loads(raw)
    assert set(manifest) == TOP_LEVEL and manifest["sky"] is None


def test_with_nothing_built_every_block_is_null(tmp_path):
    """The committed configs (the village's), a world of another area, an empty folder:
    every step not run gives null (the sky too: `python -m mattini sky` has not run in the
    folder, so the block is never computed from config/sky.json), none is left out, none is
    an empty object."""
    world = SHARED / "terrain_fixture" / "world.json"
    raw = write_manifest(tmp_path / "empty", world).read_bytes()
    manifest = json.loads(raw)
    assert set(manifest) == TOP_LEVEL
    assert manifest["schema"] == 1
    assert {key: manifest[key] for key in BLOCKS} == dict.fromkeys(BLOCKS)
    for key in BLOCKS:
        assert f'  "{key}": null,\n'.encode() in raw, key
    assert manifest["world"] == json.loads(world.read_bytes())
    assert manifest["world_sha256"] == hashlib.sha256(world.read_bytes()).hexdigest()


def test_the_village_s_sky_is_null_until_its_step_has_run(tmp_path):
    """The committed world and configs, an empty folder: config/sky.json holds this world's
    values, and still the block is null (the step's rule, not the config's)."""
    manifest = json.loads(write_manifest(tmp_path / "empty").read_bytes())
    assert set(manifest) == TOP_LEVEL and manifest["sky"] is None


@pytest.mark.parametrize("name", sorted(SKY_FIXTURES))
def test_a_sky_fixture_s_description_is_the_sky_block_verbatim(tmp_path, name):
    fixture = SHARED / name
    path = write_manifest(
        _sky_only(tmp_path, name), fixture / "world.json", sky_config_path=fixture / "sky.json"
    )
    raw = path.read_bytes()
    assert (hashlib.sha256(raw).hexdigest(), len(raw)) == SKY_FIXTURES[name], name
    manifest = json.loads(raw)
    assert set(manifest) == TOP_LEVEL
    description = (fixture / "generated" / "sky" / "fixture.json").read_bytes()
    assert manifest["sky"] == json.loads(description)
    assert [key for key in BLOCKS if manifest[key] is not None] == ["sky"]
    text = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    assert raw == text.encode("utf-8")


@pytest.mark.parametrize("name", sorted(SKY_FIXTURES))
def test_without_its_description_the_sky_block_is_null_and_the_rest_stays(tmp_path, name):
    """The same folder with `sky/` left out: the sky block is null, every other byte of the
    manifest is the one with it but that block's lines."""
    fixture = SHARED / name
    with_sky = json.loads(
        write_manifest(
            _sky_only(tmp_path / "a", name),
            fixture / "world.json",
            sky_config_path=fixture / "sky.json",
        ).read_bytes()
    )
    without = json.loads(
        write_manifest(
            tmp_path / "b", fixture / "world.json", sky_config_path=fixture / "sky.json"
        ).read_bytes()
    )
    assert without["sky"] is None
    with_sky["sky"] = None
    assert without == with_sky
