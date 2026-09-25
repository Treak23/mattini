"""The buildings step and `manifest` refuse expected chunks computed for another world or
other inputs, naming design's step (brief M2-07; M2 R1 P-02, I-01; SPEC §8).

The pinned tests (test_expected_inputs.py) change the recorded `computed_for`. These change
what the owner changes: config/world.json (the review's proof: its origin moved 1 km) and
the lock (a sheet republished with one building moved, then locked and downloaded). The
shared buildings fixture stands in for the village, as in test_buildings_step.py.

Harm prevented (the review's proof, P-02 and I-01): after a world change or an adopted
republish, `buildings` said "this machine or this code produces other buildings than the
design's" and `manifest` named `python -m mattini buildings`, which cannot succeed.

Does NOT prove: anything about a real republish by swisstopo (none exists to try); that
design's recomputed values would be right.
"""

import copy
import hashlib
import json
import shutil

import pytest
from synthetic_sheets import raw_folder
from test_buildings_step import FIXTURE, GENERATED, SHEET, _features, case  # noqa: F401

from mattini.buildings import BuildingsError, build_buildings
from mattini.lock import write_lock
from mattini.manifest import write_manifest
from mattini.world import load_world

BUILDINGS_COMMAND = "python -m mattini buildings"
MACHINE = "this machine or this code"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_sha(entry: dict) -> str:
    text = json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return _sha(text.encode("utf-8"))


def _shifted_world(folder):
    """The fixture's world with its origin moved 1 km east and north (the review's proof)."""
    data = json.loads((FIXTURE / "world.json").read_text(encoding="utf-8"))
    data["origin_lv95"]["e"] += 1000.0
    data["origin_lv95"]["n"] += 1000.0
    path = folder / "shifted" / "world.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return load_world(path)


def _build(case, world=None, lock=None):  # noqa: F811 (a case, not the fixture)
    return build_buildings(
        world or case["world"],
        case["datasets"],
        lock or case["lock"],
        case["buildings"],
        case["terrain"],
        case["raw"],
        case["out"],
    )


def _republish_and_relock(case) -> dict:  # noqa: F811 (a case, not the fixture)
    """Sheet 1249-42 republished with its first building 1 m higher, laid out and pinned as
    `lock buildings` and `download buildings` leave it; returns the new lock. The buildings
    config is not touched: design has not recomputed."""
    features = copy.deepcopy(_features(case["source"]))
    features[0]["triangles"] = [
        tuple((e, n, h + 1.0) for e, n, h in triangle) for triangle in features[0]["triangles"]
    ]
    data = json.dumps({"sheet": SHEET, "features": features}).encode("utf-8")
    return raw_folder(case["raw"], case["datasets"], {SHEET: data})


def test_the_step_names_a_shifted_origin_as_design_s_step(case):  # noqa: F811
    """The shifted-origin test (brief M2-07's mutation), the review's P-02 proof.

    Without the check, the chunks built for the moved origin differ from design's and the
    step blamed the machine or the code.
    """
    world = _shifted_world(case["tmp"])
    recorded_sha = case["buildings"]["areas"]["fixture"]["computed_for"]["world_sha256"]
    with pytest.raises(BuildingsError) as refused:
        _build(case, world=world)
    message = str(refused.value)
    for part in (
        "area 'fixture'",
        "config/buildings.json",
        f"computed for the world config with SHA-256 {recorded_sha}",
        f"config/world.json now has {_sha(world.path.read_bytes())}",
        "A changed world is a design change: design recomputes the expected values",
        "docs/SPEC.md §8",
    ):
        assert part in message, (part, message)
    assert MACHINE not in message and "datasets.lock.json" not in message
    assert case["handed"] == []  # refused before any sheet is read
    assert not case["out"].exists()


def test_the_step_names_republished_and_relocked_inputs_as_design_s_step(case):  # noqa: F811
    """The republished-and-relocked test (brief M2-07's mutation), the review's I-01 proof.

    Without the check, every input is vouched for and the chunks differ from design's: the
    step blamed the machine or the code.
    """
    recorded_sha = case["buildings"]["areas"]["fixture"]["computed_for"]["inputs_sha256"]
    pinned = _republish_and_relock(case)
    current = _canonical_sha(pinned["datasets"]["swissbuildings3d"])
    assert current != recorded_sha
    with pytest.raises(BuildingsError) as refused:
        _build(case, lock=pinned)
    message = str(refused.value)
    for part in (
        "area 'fixture'",
        "config/buildings.json",
        f"computed from the swissbuildings3d lock entry with SHA-256 {recorded_sha}",
        f"config/datasets.lock.json's entry now has {current}",
        "(a new edition or an adopted republished file)",
        "Adopting new inputs is a design change: design recomputes the expected values",
        "docs/SPEC.md §5, §8",
    ):
        assert part in message, (part, message)
    assert MACHINE not in message and "config/world.json" not in message
    assert case["handed"] == []  # refused before any sheet is read
    assert not case["out"].exists()


def test_a_shifted_origin_is_named_before_changed_inputs(case):  # noqa: F811
    pinned = _republish_and_relock(case)
    with pytest.raises(BuildingsError) as refused:
        _build(case, world=_shifted_world(case["tmp"]), lock=pinned)
    assert "config/world.json now has" in str(refused.value)
    assert "datasets.lock.json" not in str(refused.value)


# The manifest over the fixture's built block, then the owner's change, no `buildings` run.


def _out(tmp_path):
    out = tmp_path / "generated"
    shutil.copytree(GENERATED / "buildings", out / "buildings")
    return out


def _manifest(out, world=FIXTURE / "world.json", lock=FIXTURE / "datasets.lock.json"):
    return write_manifest(
        out,
        world,
        terrain_config_path=FIXTURE / "terrain.json",
        datasets_path=FIXTURE / "datasets.json",
        lock_path=lock,
        buildings_config_path=FIXTURE / "buildings.json",
    )


def test_manifest_names_a_shifted_origin_as_design_s_step(tmp_path):
    """P-02's dead end: the old refusal named `buildings`, which then refused too."""
    out = _out(tmp_path)
    world = _shifted_world(tmp_path)
    with pytest.raises(BuildingsError) as refused:
        _manifest(out, world=world.path)
    message = str(refused.value)
    for part in (
        f"config/world.json now has {_sha(world.path.read_bytes())}",
        "config/buildings.json",
        "design recomputes",
    ):
        assert part in message, (part, message)
    assert BUILDINGS_COMMAND not in message and MACHINE not in message
    assert not (out / "manifest.json").exists()


def test_manifest_names_a_relocked_input_as_design_s_step(tmp_path):
    """I-01's dead end: a sheet re-pinned by `lock buildings`, the old block kept."""
    out = _out(tmp_path)
    data = json.loads((FIXTURE / "datasets.lock.json").read_text(encoding="utf-8"))
    entry = data["datasets"]["swissbuildings3d"]
    entry["sheets"][SHEET]["sha256"] = _sha(b"1249-42 republished")
    lock = write_lock(data, tmp_path / "datasets.lock.json")
    with pytest.raises(BuildingsError) as refused:
        _manifest(out, lock=lock)
    message = str(refused.value)
    for part in (_canonical_sha(entry), "datasets.lock.json", "design recomputes"):
        assert part in message, (part, message)
    assert BUILDINGS_COMMAND not in message
    assert not (out / "manifest.json").exists()
