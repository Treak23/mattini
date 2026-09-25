"""Pinning tests for brief M2-07 (M2 R1 P-02, I-01): what an expected value was computed for.

Pinned decisions (docs/SPEC.md §8, the expected output): each area of config/terrain.json
and config/buildings.json records `computed_for`, the SHA-256 of config/world.json's bytes
and of the lock's entry for its dataset rendered canonically (sorted keys, no spaces,
UTF-8). A step or `manifest` compares both with the world config and the lock before it
compares any output. A difference is refused as a design change that design recomputes,
never blamed on this machine or this code. The committed configs and the fixtures' configs
record design's values, and those values are what the files and locks hold today.

Does NOT prove: that the expected values themselves are right (design's two
implementations and the steps' own comparison do).
"""

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from mattini.buildings import BuildingsError
from mattini.manifest import write_manifest
from mattini.terrain import TerrainError

REPO = Path(__file__).resolve().parents[2]
TERRAIN_FIXTURE = REPO / "tests" / "shared" / "terrain_fixture"
BUILDINGS_FIXTURE = REPO / "tests" / "shared" / "buildings_fixture"


def _canonical(entry: dict) -> bytes:
    return json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.mark.parametrize(
    ("config", "area", "world", "lock", "dataset"),
    [
        (
            "config/terrain.json",
            "village",
            "config/world.json",
            "config/datasets.lock.json",
            "swissalti3d",
        ),
        (
            "config/buildings.json",
            "village",
            "config/world.json",
            "config/datasets.lock.json",
            "swissbuildings3d",
        ),
        (
            "tests/shared/terrain_fixture/terrain.json",
            "fixture",
            "tests/shared/terrain_fixture/world.json",
            "tests/shared/terrain_fixture/datasets.lock.json",
            "swissalti3d",
        ),
        (
            "tests/shared/terrain_fixture_nw/terrain.json",
            "fixture_nw",
            "tests/shared/terrain_fixture_nw/world.json",
            "tests/shared/terrain_fixture_nw/datasets.lock.json",
            "swissalti3d",
        ),
        (
            "tests/shared/buildings_fixture/buildings.json",
            "fixture",
            "tests/shared/buildings_fixture/world.json",
            "tests/shared/buildings_fixture/datasets.lock.json",
            "swissbuildings3d",
        ),
    ],
)
def test_each_config_records_the_world_and_inputs_it_was_computed_for(
    config, area, world, lock, dataset
):
    recorded = json.loads((REPO / config).read_text(encoding="utf-8"))["areas"][area]
    entry = json.loads((REPO / lock).read_text(encoding="utf-8"))["datasets"][dataset]
    assert recorded["computed_for"] == {
        "inputs_sha256": _sha(_canonical(entry)),
        "world_sha256": _sha((REPO / world).read_bytes()),
    }


def _terrain_case(tmp_path, change) -> dict:
    out = tmp_path / "generated"
    shutil.copytree(TERRAIN_FIXTURE / "generated" / "terrain", out / "terrain")
    config = json.loads((TERRAIN_FIXTURE / "terrain.json").read_text(encoding="utf-8"))
    change(config["areas"]["fixture"]["computed_for"])
    path = tmp_path / "terrain.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return {"out": out, "config": path}


@pytest.mark.parametrize(
    ("key", "needle"),
    [("world_sha256", "config/world.json"), ("inputs_sha256", "datasets.lock.json")],
)
def test_manifest_names_a_changed_world_or_input_as_design_s_step(tmp_path, key, needle):
    case = _terrain_case(tmp_path, lambda cf: cf.update({key: "0" * 64}))
    with pytest.raises(TerrainError) as refusal:
        write_manifest(
            case["out"],
            TERRAIN_FIXTURE / "world.json",
            terrain_config_path=case["config"],
            datasets_path=TERRAIN_FIXTURE / "datasets.json",
            lock_path=TERRAIN_FIXTURE / "datasets.lock.json",
        )
    message = str(refusal.value)
    assert needle in message and "design recomputes" in message
    assert "this machine or this code" not in message
    assert not (case["out"] / "manifest.json").exists()


@pytest.mark.parametrize(
    ("key", "needle"),
    [("world_sha256", "config/world.json"), ("inputs_sha256", "datasets.lock.json")],
)
def test_the_buildings_manifest_names_them_too(tmp_path, key, needle):
    out = tmp_path / "generated"
    shutil.copytree(BUILDINGS_FIXTURE / "generated" / "buildings", out / "buildings")
    config = json.loads((BUILDINGS_FIXTURE / "buildings.json").read_text(encoding="utf-8"))
    config["areas"]["fixture"]["computed_for"][key] = "0" * 64
    path = tmp_path / "buildings.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(BuildingsError) as refusal:
        write_manifest(
            out,
            BUILDINGS_FIXTURE / "world.json",
            terrain_config_path=BUILDINGS_FIXTURE / "terrain.json",
            datasets_path=BUILDINGS_FIXTURE / "datasets.json",
            lock_path=BUILDINGS_FIXTURE / "datasets.lock.json",
            buildings_config_path=path,
        )
    message = str(refusal.value)
    assert needle in message and "design recomputes" in message
    assert "this machine or this code" not in message
