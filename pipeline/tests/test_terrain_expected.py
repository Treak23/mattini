"""Pinning tests for brief M2-01 (M1 R1 T-01 b): the terrain's expected SHA-256.

Pinned decisions (docs/SPEC.md §8, the expected SHA-256; lesson 38): each area of
config/terrain.json carries `expected_sha256`, an object from a spacing written as
swisstopo writes it ("0.5", "1", "2") to the SHA-256 of the heights file at that spacing,
64 lower-case hex digits; it must hold the configured spacing, and an area has exactly the
keys expected_sha256 and spacing_m. The village's three values were computed by design two
independent ways at M2 planning. `manifest` refuses a built terrain whose SHA-256 is not
the expected value for its spacing, naming `python -m mattini terrain`.

Does NOT prove: that `terrain` checks before writing (test_terrain_build_tiles.py does);
that the owner's machine computes these bytes.
"""

import json
import shutil
from pathlib import Path

import pytest

from mattini.manifest import write_manifest
from mattini.terrain import TerrainError, load_terrain_config

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "shared" / "terrain_fixture"
TERRAIN_COMMAND = "python -m mattini terrain"
VILLAGE = {
    "0.5": "b6334c1fdc992f0576bc59efd51484db2178cbe399ad46512a4bf510abb9411a",
    "1": "71bd4f174dfc3d07a3becace073c62bdf6b5cc010072a5e483a484210e8bc333",
    "2": "d6c1d558fee28c91472f2fea9c5db06d9b74480dd22f77554bf7037beec794ce",
}
FIXTURE_0_5 = "fd02c74441317dfb668f79011cb4bae7e76718648a992ec2f26417cca1f26ea2"
# design's record of what the village's values were computed for (brief M2-07's table)
VILLAGE_COMPUTED_FOR = {
    "inputs_sha256": "025f9045fef89c9e147c7dc80f081d6e65a73a3315380078b702b05386f6424d",
    "world_sha256": "d2607d1362f3c7ec26b7e00c38d873b36d29db83aa169eebf60e0dd6f299509b",
}


def test_the_committed_config_expects_design_s_village():
    config = load_terrain_config()
    assert config == {
        "schema": 1,
        "areas": {
            "village": {
                "computed_for": VILLAGE_COMPUTED_FOR,
                "expected_sha256": VILLAGE,
                "spacing_m": 0.5,
            }
        },
    }


def test_the_fixture_config_expects_the_fixture_s_heights():
    config = load_terrain_config(FIXTURE / "terrain.json")
    assert config["areas"]["fixture"]["expected_sha256"] == {"0.5": FIXTURE_0_5}


def _write_config(tmp_path, area: dict) -> Path:
    path = tmp_path / "terrain.json"
    path.write_text(json.dumps({"schema": 1, "areas": {"village": area}}), encoding="utf-8")
    return path


CF = {"computed_for": VILLAGE_COMPUTED_FOR}  # well formed, so each case below is its own fault


@pytest.mark.parametrize(
    ("area", "fault"),
    [
        ({**CF, "spacing_m": 0.5}, "exactly the keys"),
        ({**CF, "expected_sha256": {"1": VILLAGE["1"]}, "spacing_m": 0.5}, "configured spacing"),
        (
            {
                **CF,
                "expected_sha256": {"0.5": VILLAGE["0.5"], "0.25": VILLAGE["1"]},
                "spacing_m": 0.5,
            },
            "as swisstopo writes them",
        ),
        ({**CF, "expected_sha256": {"0.5": VILLAGE["0.5"].upper()}, "spacing_m": 0.5}, "64"),
        ({**CF, "expected_sha256": {"0.5": VILLAGE["0.5"][:63]}, "spacing_m": 0.5}, "64"),
        ({**CF, "expected_sha256": {"1.0": VILLAGE["1"]}, "spacing_m": 1.0}, "swisstopo"),
        ({**CF, "expected_sha256": [VILLAGE["0.5"]], "spacing_m": 0.5}, "an object"),
        (
            {**CF, "expected_sha256": {"0.5": VILLAGE["0.5"]}, "spacing_m": 0.5, "note": "x"},
            "exactly the keys",
        ),
    ],
    ids=[
        "missing",
        "not-the-configured-spacing",
        "unknown-spacing-key",
        "upper-case",
        "too-short",
        "spacing-written-1.0",
        "not-an-object",
        "extra-key",
    ],
)
def test_a_malformed_expected_value_is_refused_naming_the_file(tmp_path, area, fault):
    path = _write_config(tmp_path, area)
    with pytest.raises(TerrainError, match=str(path)) as refused:
        load_terrain_config(path)
    assert fault in str(refused.value)


@pytest.mark.parametrize(
    "computed_for",
    [
        None,
        "d2607d13",
        {"world_sha256": VILLAGE_COMPUTED_FOR["world_sha256"]},
        {**VILLAGE_COMPUTED_FOR, "tiles_sha256": "0" * 64},
        {**VILLAGE_COMPUTED_FOR, "world_sha256": VILLAGE_COMPUTED_FOR["world_sha256"].upper()},
        {**VILLAGE_COMPUTED_FOR, "inputs_sha256": VILLAGE_COMPUTED_FOR["inputs_sha256"][:63]},
        {**VILLAGE_COMPUTED_FOR, "inputs_sha256": None},
    ],
    ids=["missing", "not-an-object", "a-key-missing", "a-key-added", "upper-case", "short", "null"],
)
def test_a_malformed_computed_for_is_refused_naming_the_file(tmp_path, computed_for):
    """Brief M2-07: exactly {inputs_sha256, world_sha256}, 64 lower-case hex digits each."""
    area = {"expected_sha256": {"0.5": VILLAGE["0.5"]}, "spacing_m": 0.5}
    if computed_for is not None:
        area["computed_for"] = computed_for
    path = _write_config(tmp_path, area)
    with pytest.raises(TerrainError, match=str(path)) as refused:
        load_terrain_config(path)
    assert "computed_for" in str(refused.value) or "exactly the keys" in str(refused.value)


def test_a_config_at_another_spacing_is_accepted(tmp_path):
    path = _write_config(tmp_path, {**CF, "expected_sha256": dict(VILLAGE), "spacing_m": 2.0})
    assert load_terrain_config(path)["areas"]["village"]["spacing_m"] == 2.0


def test_manifest_refuses_a_terrain_that_is_not_the_expected_one(tmp_path):
    """A heights file that matches its own description but not design's value."""
    out = tmp_path / "generated"
    shutil.copytree(FIXTURE / "generated" / "terrain", out / "terrain")
    config = json.loads((FIXTURE / "terrain.json").read_text(encoding="utf-8"))
    config["areas"]["fixture"]["expected_sha256"]["0.5"] = "0" * 64
    wrong = tmp_path / "terrain.json"
    wrong.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(TerrainError, match=TERRAIN_COMMAND) as refusal:
        write_manifest(
            out,
            FIXTURE / "world.json",
            terrain_config_path=wrong,
            datasets_path=FIXTURE / "datasets.json",
            lock_path=FIXTURE / "datasets.lock.json",
        )
    assert FIXTURE_0_5 in str(refusal.value)
    assert not (out / "manifest.json").exists()
