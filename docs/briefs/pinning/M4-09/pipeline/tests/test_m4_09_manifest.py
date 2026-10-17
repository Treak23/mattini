"""Pinning tests for brief M4-09: the manifest's M4 shape, reproduced from every fixture.

Pinned decisions (m4-design §2, §3, §4; brief M4-09): the manifest's top level is exactly
`buildings`, `photo`, `roofs`, `schema`, `shadows`, `sky`, `surfaces`, `surroundings`,
`terrain`, `trees`, `world` and `world_sha256`; `schema` stays 1; each block is the
description its step wrote, verbatim, or null when that step has not been run in the
folder (brief M3-13's rule, now for the three new blocks too: the `sky` block is the
description `python -m mattini sky` writes, `sky/<area>.json`); the text is
`json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False)` and a final LF, in
UTF-8.

Every shared fixture's committed `generated/manifest.json` is what `write_manifest` writes
from that fixture's committed generated files and configs, byte for byte. The seven M2 and M3
fixtures' manifests are design's pinned copies (docs/briefs/pinning/M4-09/tests/shared/),
each the M3-13 file plus three lines, `"shadows": null`, `"sky": null` and
`"surroundings": null`, made two ways (that text edit, and design's throwaway
`write_manifest`; identical). The surroundings and shadows fixtures gain a manifest of their
own (new, design's, made the same two ways: the dict assembled by hand from the description,
the world and the sky config, and the throwaway), each with its fixture's sky block
(`generated/sky/fixture.json`, from the fixture's `sky.json`).

Each fixture's manifest also carries its SHA-256 here, so a fixture rewritten by the code
under test fails even where the bytes comparison would follow it (lesson 33).

Does NOT prove: that the game reads the new blocks (briefs M4-06, M4-07, M4-10); that the
real village's blocks are design's (the real run of this brief's gates, against
config/*.json).
"""

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from mattini.manifest import write_manifest

REPO = Path(__file__).resolve().parents[2]
SHARED = REPO / "tests" / "shared"
BUILDINGS_FIXTURE = SHARED / "buildings_fixture"
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
BLOCKS = sorted(TOP_LEVEL - {"schema", "world", "world_sha256"})
NEW = ("shadows", "sky", "surroundings")

# Each fixture: the configs write_manifest reads from it (a config a fixture does not hold is
# the committed one, for a step not run there), which blocks are built, and the SHA-256 of its
# committed manifest.
FIXTURES = {
    "terrain_fixture": {
        "world": "world.json",
        "configs": {"terrain_config_path": "terrain.json"},
        "built": ["terrain"],
        "sha256": "7da6238dc7cad625ecab5039be762c7d9518b001f7c5ab5524597fca27f36cd1",
    },
    "terrain_fixture_nw": {
        "world": "world.json",
        "configs": {"terrain_config_path": "terrain.json"},
        "built": ["terrain"],
        "sha256": "d5b2566d7467cc9278bf6ab720869f288432e9947fea18ffbdd51b9a7a46ff97",
    },
    "buildings_fixture": {
        "world": "world.json",
        "configs": {
            "terrain_config_path": "terrain.json",
            "buildings_config_path": "buildings.json",
        },
        "built": ["buildings"],
        "sha256": "e21c525b8d8c714fd92feec7e8945730a015e62879ded0f54ee697dccaa6e442",
    },
    "photo_fixture": {
        "world": "world.json",
        "configs": {"photo_config_path": "photo.json"},
        "built": ["photo"],
        "sha256": "72a550df79c733392eabbad4dfca3602b4d6e68fc3d73cb2bf78883f0414c1a7",
    },
    "roofs_fixture": {
        # the buildings fixture's world and area (its photo.json describes the synthetic
        # photo's windows: it is not a photo config)
        "world": BUILDINGS_FIXTURE / "world.json",
        "configs": {
            "terrain_config_path": BUILDINGS_FIXTURE / "terrain.json",
            "buildings_config_path": "buildings.json",
            "roofs_config_path": "roofs.json",
        },
        "built": ["buildings", "roofs"],
        "sha256": "396e5b2b70165992d709762bfac7ae9412131df2de7aa14cf0e3a5f7550a3ee6",
    },
    "surfaces_fixture": {
        "world": "world.json",
        "configs": {"surfaces_config_path": "surfaces.json"},
        "built": ["surfaces"],
        "sha256": "06636734c5096612c0be5440aa35ded12480dfc080c5bd30ffb52015ba9a0a85",
    },
    "trees_fixture": {
        "world": "world.json",
        "configs": {"terrain_config_path": "terrain.json", "trees_config_path": "trees.json"},
        "built": ["trees"],
        "sha256": "8bd7a99d986ab30aa98c2eaa8956108d7295ef6d2936ec682526f5ad99a8ff5b",
    },
    "surroundings_fixture": {
        "world": "world.json",
        "configs": {"surroundings_config_path": "surroundings.json", "sky_config_path": "sky.json"},
        "built": ["sky", "surroundings"],
        "sha256": "8fa084a51747793d40c9126b093851f4fd779062de06b731248629ffb7f181e1",
    },
    "shadows_fixture": {
        "world": "world.json",
        "configs": {"shadows_config_path": "shadows.json", "sky_config_path": "sky.json"},
        "built": ["shadows", "sky"],
        "sha256": "d4bceb8f9c77daf4cd5efa2355b4b4d90df555c98bb04c476bfc854483108993",
    },
}


def _paths(name: str) -> tuple[Path, dict]:
    fixture = SHARED / name
    spec = FIXTURES[name]
    configs = {key: fixture / value for key, value in spec["configs"].items()}
    configs["datasets_path"] = fixture / "datasets.json"
    configs["lock_path"] = fixture / "datasets.lock.json"
    return fixture / spec["world"], configs


def _generated(tmp_path, name: str, *, leave_out: tuple[str, ...] = ()) -> Path:
    """A copy of the fixture's committed generated files, without its manifest."""
    out = tmp_path / "generated"
    shutil.copytree(
        SHARED / name / "generated",
        out,
        ignore=shutil.ignore_patterns("manifest.json", *leave_out),
    )
    return out


@pytest.mark.parametrize("name", sorted(FIXTURES))
def test_each_fixture_s_manifest_is_what_write_manifest_writes(tmp_path, name):
    committed = (SHARED / name / "generated" / "manifest.json").read_bytes()
    assert hashlib.sha256(committed).hexdigest() == FIXTURES[name]["sha256"], name
    world, configs = _paths(name)
    path = write_manifest(_generated(tmp_path, name), world, **configs)
    assert path.read_bytes() == committed
    manifest = json.loads(committed)
    assert set(manifest) == TOP_LEVEL
    assert [key for key in BLOCKS if manifest[key] is not None] == FIXTURES[name]["built"]
    text = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    assert committed == text.encode("utf-8")
    for key in FIXTURES[name]["built"]:  # each block is its description, verbatim
        description = SHARED / name / "generated" / key / f"{manifest[key]['area']}.json"
        assert manifest[key] == json.loads(description.read_bytes()), key


@pytest.mark.parametrize(
    "name", sorted(set(FIXTURES) - {"surroundings_fixture", "shadows_fixture"})
)
def test_an_m3_fixture_s_manifest_is_its_m3_13_text_with_three_null_lines(name):
    """The seven earlier fixtures change by exactly three lines each, nothing else (their
    blocks, world and world_sha256 stay byte for byte)."""
    lines = (SHARED / name / "generated" / "manifest.json").read_text("utf-8").splitlines()
    for key in NEW:
        assert f'  "{key}": null,' in lines, key
    kept = [line for line in lines if line not in {f'  "{key}": null,' for key in NEW}]
    m3 = json.loads("\n".join(kept))
    assert set(m3) == TOP_LEVEL - set(NEW)
    assert json.dumps(m3, indent=2, sort_keys=True, ensure_ascii=False).splitlines() == kept


def test_with_nothing_built_every_block_is_null(tmp_path):
    """The committed configs (the village's), a world of another area, an empty folder:
    every step not run gives null (the sky too: `python -m mattini sky` has not run), none is
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


@pytest.mark.parametrize(
    ("name", "block"),
    [
        ("surroundings_fixture", "surroundings"),
        ("surroundings_fixture", "sky"),
        ("shadows_fixture", "shadows"),
        ("shadows_fixture", "sky"),
    ],
)
def test_a_new_block_whose_step_has_not_run_is_null_and_the_rest_stays(tmp_path, name, block):
    """Its description left out of the folder: that block is null, every other byte of the
    manifest is the committed one's but that block's lines."""
    world, configs = _paths(name)
    out = _generated(tmp_path, name, leave_out=(block,))
    manifest = json.loads(write_manifest(out, world, **configs).read_bytes())
    committed = json.loads((SHARED / name / "generated" / "manifest.json").read_bytes())
    assert manifest[block] is None
    committed[block] = None
    assert manifest == committed
