"""Pinning tests for briefs v0.4.0-07 and v0.5.0-02 (brief M4-09 cut to the sky, then to the
shadows): the manifest's `sky` and `shadows` blocks.

Pinned decisions (m4-design §2, §3, §4; brief M4-09 decisions 2, 3 and 7, the sky and the
shadows only; briefs v0.4.0-07 and v0.5.0-02): the manifest's top level is exactly `buildings`,
`photo`, `roofs`, `schema`, `shadows`, `sky`, `surfaces`, `terrain`, `trees`, `world` and
`world_sha256` (eleven keys: M3-13's nine, `sky` and `shadows`; no `surroundings` key until the
far mountains' step exists); `schema` stays 1; the `sky` block is the description
`python -m mattini sky` wrote, `sky/<area>.json` for config/sky.json's area, and the `shadows`
block the description `python -m mattini shadows` wrote, `shadows/<area>.json` for
config/shadows.json's area, each verbatim, or null when that step has not been run in the
folder (brief M3-13's rule for every block): never computed by `manifest` from a config, never
left out, never an empty object; the text is `json.dumps(manifest, indent=2, sort_keys=True,
ensure_ascii=False)` and a final LF, in UTF-8.

The seven M2 and M3 fixtures' committed manifests are their 0.4.0 text (v0.4.0-07's, ten keys)
plus one line, `  "shadows": null,` (between `schema` and `sky`), nothing else: design's copies,
made two ways (that text edit, and the pin author's throwaway `write_manifest`; identical).
Their SHA-256 before the line (PREVIOUS: v0.4.0-07's) and after it (test_manifest_m3.py) are both
pinned, so a fixture rewritten by the code under test fails even where a bytes comparison would
follow it (lesson 33).

The shadows fixture (tests/shared/shadows_fixture/) holds a shadows config, a sky config, a lock
and their descriptions (`generated/shadows/`, `generated/sky/`, design data): its committed
`generated/manifest.json` (new, design's) is what `write_manifest` writes from them, byte for
byte, with the `shadows` and `sky` blocks built and every other block null; made three ways
(assembled by hand from the two descriptions and the world, the throwaway, and M4-09's pinned
file without its `surroundings` line; identical). A folder holding only a fixture's sky
description, with the fixture's world and sky config, gives a manifest whose `sky` block is the
description and every other block null, at the SHA-256 pinned here (SKY_FIXTURES, made two
ways). The surroundings fixture's own committed `generated/manifest.json` (twelve keys, M4-07's,
read by no test) is not these briefs' and stays as it is.

Does NOT prove: that the game reads the blocks (brief v0.4.0-08 the sky; the shadows' reader is
a later batch of 0.5.0); that the real village's manifest is design's (the release gate, against
the plan's pair).
"""

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from mattini.manifest import write_manifest

REPO = Path(__file__).resolve().parents[2]
SHARED = REPO / "tests" / "shared"
SHADOWS_FIXTURE = SHARED / "shadows_fixture"
TOP_LEVEL = {
    "buildings",
    "photo",
    "roofs",
    "schema",
    "shadows",
    "sky",
    "surfaces",
    "terrain",
    "trees",
    "world",
    "world_sha256",
}
BLOCKS = sorted(TOP_LEVEL - {"schema", "world", "world_sha256"})
SHADOWS_LINE = '  "shadows": null,'
# Each M2 and M3 fixture's committed manifest before brief v0.5.0-02 (v0.4.0-07's, ten keys).
PREVIOUS = {
    "terrain_fixture": "998371a52a2f2da3aa2c38c71bd0eaba3294292da188635a9405172ce69c6cad",
    "terrain_fixture_nw": "36972372212ef811dbe30e32fb3d9c2fed28ff8dfac45590abb822f3c5b498af",
    "buildings_fixture": "3079fc6dee98248484d707d78c70b3f89732a94f9b7881ee960181878c63ea16",
    "photo_fixture": "e5da20895a8d0ea13e381d39606beb823392a8db143516960fe00fc93023c5c3",
    "roofs_fixture": "235f82267a6117321b53afd03503230170b06190515a2e9b4b899b9b62c8e3d8",
    "surfaces_fixture": "5e4c63e28a0857fa22c9f39c184fd830fc32067e681655ab3c54b69d64cae278",
    "trees_fixture": "1ab1492704fbff77527264b2207c6db913607c039c54df745a62499abcfcc0c8",
}
# A folder holding only the fixture's sky description: the manifest's SHA-256 and size.
SKY_FIXTURES = {
    "shadows_fixture": ("ff90b955325b9d0b9d8597207928d6cfc038d680acc86cc3e377623930a7c546", 907),
    "surroundings_fixture": (
        "136685fd231e962488726bb96b7dc15d3e0c657c2ccc2d85e2ae9f7c6ebe61e4",
        908,
    ),
}
# The shadows fixture's committed manifest (new in brief v0.5.0-02): its SHA-256 and size.
SHADOWS_MANIFEST = ("0ffcf8984de34e783aa301d270de6af004dfbb2d0ba74bfd493f6cc90c2b90ea", 2077)


def _sky_only(tmp_path, name: str) -> Path:
    """A folder holding only the fixture's committed `sky/` (its description)."""
    out = tmp_path / "generated"
    shutil.copytree(SHARED / name / "generated" / "sky", out / "sky")
    return out


def _shadows_fixture_generated(tmp_path, *, leave_out: tuple[str, ...] = ()) -> Path:
    """A copy of the shadows fixture's committed generated files, without its manifest."""
    out = tmp_path / "generated"
    shutil.copytree(
        SHADOWS_FIXTURE / "generated",
        out,
        ignore=shutil.ignore_patterns("manifest.json", *leave_out),
    )
    return out


def _shadows_fixture_manifest(out: Path) -> Path:
    """`write_manifest` with the shadows fixture's world, datasets config, lock, shadows config
    and sky config (every other config the committed one, for a step not run there)."""
    return write_manifest(
        out,
        SHADOWS_FIXTURE / "world.json",
        datasets_path=SHADOWS_FIXTURE / "datasets.json",
        lock_path=SHADOWS_FIXTURE / "datasets.lock.json",
        shadows_config_path=SHADOWS_FIXTURE / "shadows.json",
        sky_config_path=SHADOWS_FIXTURE / "sky.json",
    )


@pytest.mark.parametrize("name", sorted(PREVIOUS))
def test_an_m3_fixture_s_manifest_is_its_previous_text_with_one_null_line(name):
    """The seven earlier fixtures change by exactly the one line, nothing else (their blocks,
    the sky's null, world and world_sha256 stay byte for byte)."""
    raw = (SHARED / name / "generated" / "manifest.json").read_bytes()
    lines = raw.decode("utf-8").split("\n")
    assert lines.count(SHADOWS_LINE) == 1, name
    at = lines.index(SHADOWS_LINE)
    assert lines[at - 1] == '  "schema": 1,' and lines[at + 1] == '  "sky": null,', name
    previous = "\n".join(lines[:at] + lines[at + 1 :]).encode("utf-8")
    assert hashlib.sha256(previous).hexdigest() == PREVIOUS[name], name
    manifest = json.loads(raw)
    assert set(manifest) == TOP_LEVEL and manifest["shadows"] is None and manifest["sky"] is None


def test_with_nothing_built_every_block_is_null(tmp_path):
    """The committed configs (the village's), a world of another area, an empty folder:
    every step not run gives null (the sky and the shadows too: their steps have not run in
    the folder, so no block is computed from config/sky.json or config/shadows.json), none is
    left out, none is an empty object."""
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


def test_the_village_s_sky_and_shadows_are_null_until_their_steps_have_run(tmp_path):
    """The committed world and configs, an empty folder: config/sky.json and
    config/shadows.json hold this world's values, and still both blocks are null (the step's
    rule, not the config's)."""
    manifest = json.loads(write_manifest(tmp_path / "empty").read_bytes())
    assert set(manifest) == TOP_LEVEL and manifest["sky"] is None and manifest["shadows"] is None


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


def test_the_shadows_fixture_s_manifest_is_what_write_manifest_writes(tmp_path):
    """The shadows fixture's committed manifest: its SHA-256 and size pinned, then rewritten
    byte for byte from its generated files and configs; the shadows and sky blocks are their
    descriptions verbatim, every other block null."""
    committed = (SHADOWS_FIXTURE / "generated" / "manifest.json").read_bytes()
    assert (hashlib.sha256(committed).hexdigest(), len(committed)) == SHADOWS_MANIFEST
    path = _shadows_fixture_manifest(_shadows_fixture_generated(tmp_path))
    assert path.read_bytes() == committed
    manifest = json.loads(committed)
    assert set(manifest) == TOP_LEVEL
    assert [key for key in BLOCKS if manifest[key] is not None] == ["shadows", "sky"]
    for key in ("shadows", "sky"):  # each block is its description, verbatim
        description = SHADOWS_FIXTURE / "generated" / key / "fixture.json"
        assert manifest[key] == json.loads(description.read_bytes()), key
    text = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    assert committed == text.encode("utf-8")


@pytest.mark.parametrize("left_out", ["shadows", "sky"])
def test_a_block_whose_step_has_not_run_is_null_and_the_rest_stays(tmp_path, left_out):
    """The shadows fixture's generated files with one step's folder left out: that block is
    null, every other block is the committed manifest's."""
    out = _shadows_fixture_generated(tmp_path, leave_out=(left_out,))
    assert not (out / left_out).exists()
    manifest = json.loads(_shadows_fixture_manifest(out).read_bytes())
    committed = json.loads((SHADOWS_FIXTURE / "generated" / "manifest.json").read_bytes())
    assert manifest[left_out] is None and committed[left_out] is not None
    committed[left_out] = None
    assert manifest == committed
