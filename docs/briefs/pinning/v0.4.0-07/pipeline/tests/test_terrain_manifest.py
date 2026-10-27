"""Pinning tests for brief M1-03: the manifest's `terrain` block (docs/SPEC.md §8).

Pinned decisions: the manifest's top level is exactly schema, terrain, world and
world_sha256 (since M2-04 also buildings, since M3-13 also photo, roofs, surfaces and trees,
since v0.4.0-07 also sky, all null here: none is built); `terrain` is null until a terrain has been built, and otherwise the
description the terrain step wrote next to the heights file, copied verbatim. `manifest`
refuses a built terrain that no longer matches: another world config (its heights are
H - height_offset_m, so a changed offset would shift the world vertically, Hard Rule 4),
another spacing, another edition or resolution, or a heights file whose SHA-256 differs;
each refusal names `python -m mattini terrain`. The gate runs `manifest` in containers
with no terrain built, where `terrain` is null. Since M2-01 the fixture carries its own
tile lock, which the manifest reads (M1 R1 T-04), and its terrain config the expected
SHA-256 (T-01).
"""

import hashlib
import json
import re
import shutil
from pathlib import Path

import pytest
from computed_for import recorded

from mattini.manifest import write_manifest
from mattini.terrain import TerrainError, load_terrain_config

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "shared" / "terrain_fixture"
GENERATED = FIXTURE / "generated"
TERRAIN_COMMAND = "python -m mattini terrain"
LOCK_COMMAND = "python -m mattini lock terrain"
# v0.4.0-07: the M3-13 bytes (cf4b939c…) with `  "sky": null,` added (M3-13: the M2-04
# bytes, ba8383ff…, with `  "photo": null,`, `  "roofs": null,`, `  "surfaces": null,` and
# `  "trees": null,` added; M2-04: the M1-03 bytes with `  "buildings": null,` added)
MANIFEST_WITHOUT_TERRAIN_SHA256 = "d8c11ede88065d3e2eb5ed2f78f5219cf32cb5a0367b21d370e983154ee2ec21"


def _fixture_out(tmp_path) -> Path:
    out = tmp_path / "generated"
    shutil.copytree(GENERATED / "terrain", out / "terrain")
    return out


def _write(out, world=FIXTURE / "world.json", terrain=FIXTURE / "terrain.json"):
    return write_manifest(
        out,
        world,
        terrain_config_path=terrain,
        datasets_path=FIXTURE / "datasets.json",
        lock_path=FIXTURE / "datasets.lock.json",
    )


def _copy_with(tmp_path, name, change):
    data = json.loads((FIXTURE / name).read_text(encoding="utf-8"))
    change(data)
    path = tmp_path / name
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def test_without_a_built_terrain_the_block_is_null(tmp_path):
    raw = _write(tmp_path / "empty").read_bytes()
    manifest = json.loads(raw)
    assert set(manifest) == {
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
    assert manifest["terrain"] is None
    assert hashlib.sha256(raw).hexdigest() == MANIFEST_WITHOUT_TERRAIN_SHA256


def test_the_real_config_without_terrain_gives_a_null_block(tmp_path):
    manifest = json.loads(write_manifest(tmp_path).read_bytes())
    assert set(manifest) == {
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
    assert manifest["terrain"] is None


def test_a_built_terrain_is_copied_verbatim(tmp_path):
    manifest = json.loads(_write(_fixture_out(tmp_path)).read_bytes())
    sidecar = json.loads((GENERATED / "terrain" / "fixture.json").read_text(encoding="utf-8"))
    assert manifest["terrain"] == sidecar
    assert manifest["terrain"]["world_sha256"] == manifest["world_sha256"]


def test_terrain_built_for_another_world_is_refused(tmp_path):
    """Design has recomputed for the changed world (the config records it, M2-07): the old
    terrain is refused, naming `terrain`. Without design's step the refusal names design's
    (test_computed_for_terrain.py)."""
    world = _copy_with(tmp_path, "world.json", lambda d: d.update(height_offset_m=900.0))
    lock = json.loads((FIXTURE / "datasets.lock.json").read_text(encoding="utf-8"))
    config = recorded(
        json.loads((FIXTURE / "terrain.json").read_text(encoding="utf-8")),
        world,
        lock,
        "swissalti3d",
    )
    terrain = tmp_path / "adopted-terrain.json"
    terrain.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(TerrainError, match=TERRAIN_COMMAND) as refused:
        _write(_fixture_out(tmp_path), world=world, terrain=terrain)
    assert "built for the world config" in str(refused.value)


def test_terrain_built_at_another_spacing_is_refused(tmp_path):
    def one_metre(d):  # the config must still expect a value at its spacing
        d["areas"]["fixture"].update(spacing_m=1.0, expected_sha256={"1": "0" * 64})

    terrain = _copy_with(tmp_path, "terrain.json", one_metre)
    with pytest.raises(TerrainError, match=TERRAIN_COMMAND):
        _write(_fixture_out(tmp_path), terrain=terrain)


def test_a_datasets_config_with_another_edition_is_refused_naming_the_lock(tmp_path):
    """The lock no longer fits the datasets config (M3-01): `lock terrain` is the command
    that helps. The block's own edition is edited in test_terrain_manifest_source.py."""
    datasets = _copy_with(
        tmp_path, "datasets.json", lambda d: d["datasets"]["swissalti3d"].update(edition="2019")
    )
    with pytest.raises(TerrainError, match=LOCK_COMMAND):
        write_manifest(
            _fixture_out(tmp_path),
            FIXTURE / "world.json",
            terrain_config_path=FIXTURE / "terrain.json",
            datasets_path=datasets,
            lock_path=FIXTURE / "datasets.lock.json",
        )


@pytest.mark.parametrize("damage", ["changed", "missing", "short"])
def test_a_heights_file_that_does_not_match_is_refused(tmp_path, damage):
    out = _fixture_out(tmp_path)
    heights = out / "terrain" / "fixture.f32"
    if damage == "changed":
        data = bytearray(heights.read_bytes())
        data[100] ^= 1
        heights.write_bytes(bytes(data))
    elif damage == "missing":
        heights.unlink()
    else:
        heights.write_bytes(heights.read_bytes()[:-4])
    with pytest.raises(TerrainError, match=TERRAIN_COMMAND):
        _write(out)
    assert not (out / "manifest.json").exists()


def test_the_committed_terrain_config_is_the_owners_choice():
    config = load_terrain_config()
    assert list(config["areas"]) == ["village"]
    assert config["areas"]["village"]["spacing_m"] == 0.5  # the owner, 2026-09-25 (SPEC §7)


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d["areas"]["village"].update(spacing_m=0.25),
        lambda d: d["areas"].update(backdrop=dict(d["areas"]["village"], spacing_m=2.0)),
        lambda d: d["areas"].clear(),
        lambda d: d.update(schema=2),
    ],
    ids=["spacing", "second-area", "no-area", "schema"],
)
def test_a_bad_terrain_config_is_refused_with_the_file_named(tmp_path, change):
    data = json.loads((REPO / "config" / "terrain.json").read_text(encoding="utf-8"))
    change(data)
    path = tmp_path / "terrain.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(TerrainError, match=re.escape(str(path))):
        load_terrain_config(path)
