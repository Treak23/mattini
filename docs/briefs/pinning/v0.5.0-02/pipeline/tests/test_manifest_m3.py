"""Pinning tests for brief M3-13: the manifest's M3 shape, reproduced from every fixture.

Pinned decisions (docs/SPEC.md §8, *The manifest*; brief M3-13): the manifest's top level
is exactly `buildings`, `photo`, `roofs`, `schema`, `surfaces`, `terrain`, `trees`, `world`
and `world_sha256`, since brief v0.4.0-07 `sky` and since brief v0.5.0-02 `shadows` (both null
in every fixture here: neither step has run in them; their manifests gained the one line
`  "sky": null,`, then the one line `  "shadows": null,`, test_m4_09_manifest.py); `schema`
stays 1; each block is the description its step wrote,
verbatim, or null when that step has not been run in the folder; the text is
`json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False)` and a final LF, in
UTF-8. Every shared fixture's committed `generated/manifest.json` is what `write_manifest`
writes from that fixture's committed generated files and configs, byte for byte: the
photo, roofs, surfaces and trees fixtures (design wrote them in this shape with the plan)
and the three M2 fixtures, whose manifests design rewrote in this shape for M3-13 (the
pinned copies under docs/briefs/pinning/M3-13/tests/shared/, made two ways: the M2
manifest with the four null blocks added, and design's throwaway; identical). Roof colours
need the buildings they colour: built roofs without built buildings are refused, naming
`python -m mattini buildings`, and nothing is written.

Each fixture's manifest also carries its SHA-256 here, so a fixture rewritten by the code
under test fails even where the bytes comparison would follow it (lesson 33).

Does NOT prove: that the game reads the new blocks (M3-09 to M3-12 and M3-14); that the
real village's blocks are design's (the real run, against config/*.json).
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
    "terrain",
    "trees",
    "world",
    "world_sha256",
}
BLOCKS = sorted(TOP_LEVEL - {"schema", "world", "world_sha256"})

# Each fixture: the configs write_manifest reads from it (a config a fixture does not hold
# is the committed one, for a step not run there), which blocks are built, and the SHA-256
# of its committed manifest.
FIXTURES = {
    "terrain_fixture": {
        "world": "world.json",
        "configs": {"terrain_config_path": "terrain.json"},
        "built": ["terrain"],
        "sha256": "3d5d9e353dec37c32a0e0f3aaef90871e5eebcad6f4ee6ffcc03594e44e24fab",
    },
    "terrain_fixture_nw": {
        "world": "world.json",
        "configs": {"terrain_config_path": "terrain.json"},
        "built": ["terrain"],
        "sha256": "fd2481dffa88ebbc7be198fabc8758a7d7fb6c6a1502fb88c7d6aae91597ca84",
    },
    "buildings_fixture": {
        "world": "world.json",
        "configs": {
            "terrain_config_path": "terrain.json",
            "buildings_config_path": "buildings.json",
        },
        "built": ["buildings"],
        "sha256": "5814d95c2af053eb1955b2762599fbacbe9aabe61859c03e7ebcf925ed67770d",
    },
    "photo_fixture": {
        "world": "world.json",
        "configs": {"photo_config_path": "photo.json"},
        "built": ["photo"],
        "sha256": "252c92a7bc858aa0169cb6eaccc199719f86a46b36c54f6dd4c04cda92ac611f",
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
        "sha256": "f65abc0b7fc685fa53005bd1e37cc92fb57d24e2ab30a04ba209a18bcb47bea7",
    },
    "surfaces_fixture": {
        "world": "world.json",
        "configs": {"surfaces_config_path": "surfaces.json"},
        "built": ["surfaces"],
        "sha256": "1df51af7602407115ddba5c990c6e02ca8aaabae902fe8f8de40fe12fb8843e5",  # v0.5.0-02
    },
    "trees_fixture": {
        "world": "world.json",
        "configs": {"terrain_config_path": "terrain.json", "trees_config_path": "trees.json"},
        "built": ["trees"],
        "sha256": "c9066f6d68ce27cc71c5db1ccb649ea5fa829c1f6d7968fb6b1e75b4dc885645",
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


def test_with_nothing_built_every_block_is_null(tmp_path):
    """The committed configs (the village's), a world of another area, an empty folder:
    every step not run gives null, none is left out, none is an empty object."""
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


def test_roof_colours_without_buildings_are_refused(tmp_path):
    """The roofs fixture's roofs, its buildings left out: refused, naming the buildings."""
    out = _generated(tmp_path, "roofs_fixture", leave_out=("buildings",))
    assert not (out / "buildings").exists() and (out / "roofs" / "fixture.json").exists()
    world, configs = _paths("roofs_fixture")
    with pytest.raises(ValueError) as refused:
        write_manifest(out, world, **configs)
    assert "python -m mattini buildings" in str(refused.value)
    assert not (out / "manifest.json").exists(), "a refusal writes nothing"
