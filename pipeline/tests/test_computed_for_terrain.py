"""The terrain step and `manifest` refuse expected values computed for another world or
other inputs, naming design's step (brief M2-07; M2 R1 P-02, I-01; SPEC §8).

The pinned tests (test_expected_inputs.py) change the recorded `computed_for`. These change
what the owner changes: config/world.json (its origin moved 1 km, its height offset
changed) and the lock (a tile republished, then locked and downloaded, as the download's
own refusal instructs). The one-tile world of test_terrain_refusals.py stands in for the
village; its terrain config records the world and lock it was computed for.

Harm prevented (the review's proof, P-02 and I-01): the owner edits the world config or
adopts a republished tile; `terrain` then says his machine or the code is wrong and
`manifest` names `python -m mattini terrain`, which cannot succeed. Nothing wrong is
written either way; what was wrong was the stated cause and the missing step.

Does NOT prove: anything about a real republish by swisstopo (none exists to try; the
tile is synthetic); that design's recomputed values would be right.
"""

import hashlib
import json

import numpy as np
import pytest
from computed_for import recorded
from test_terrain_refusals import NAME, TILE, _heights, _write_tile, case  # noqa: F401

from mattini import lock
from mattini.manifest import write_manifest
from mattini.terrain import TerrainError, build_terrain
from mattini.world import load_world

TERRAIN_COMMAND = "python -m mattini terrain"
MACHINE = "this machine or this code"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_sha(entry: dict) -> str:
    text = json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return _sha(text.encode("utf-8"))


def _changed_world(case, change):  # noqa: F811 (a case, not the fixture)
    """The case's world config changed by `change`, in a folder of its own."""
    data = json.loads(case["world"].path.read_text(encoding="utf-8"))
    change(data)
    path = case["tmp"] / "changed" / "world.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return load_world(path)


def _shift_origin(data):
    data["origin_lv95"]["e"] += 1000.0
    data["origin_lv95"]["n"] += 1000.0


def _build(case, world=None):  # noqa: F811 (a case, not the fixture)
    return build_terrain(
        world or case["world"],
        case["datasets"],
        case["lock"],
        case["config"],
        case["tmp"] / "raw",
        case["out"],
    )


def _republish_and_relock(case):  # noqa: F811 (a case, not the fixture)
    """The tile rewritten 0.25 m higher, the lock and provenance.json pinning it: what
    `lock terrain` and `download terrain` leave after a republish. The config is not
    touched: design has not recomputed."""
    path = case["raw_dir"] / NAME
    _write_tile(path, _heights() + np.float32(0.25))
    sha256 = _sha(path.read_bytes())
    case["lock"]["datasets"]["swissalti3d"]["tiles"][TILE]["sha256"] = sha256
    provenance = case["raw_dir"] / "provenance.json"
    data = json.loads(provenance.read_text(encoding="utf-8"))
    data["tiles"][0]["sha256"] = sha256
    provenance.write_text(json.dumps(data), encoding="utf-8")


def _world_message_parts(case, world):  # noqa: F811 (a case, not the fixture)
    recorded_sha = case["config"]["areas"]["village"]["computed_for"]["world_sha256"]
    return (
        "area 'village'",
        "config/terrain.json",
        f"computed for the world config with SHA-256 {recorded_sha}",
        f"config/world.json now has {_sha(world.path.read_bytes())}",
        "A changed world is a design change: design recomputes the expected values",
        "docs/SPEC.md §8",
    )


@pytest.mark.parametrize(
    "change",
    [_shift_origin, lambda d: d.update(height_offset_m=1000.0)],
    ids=["origin-moved-1-km", "height-offset"],
)
def test_the_step_names_a_changed_world_as_design_s_step(case, change):  # noqa: F811
    """The shifted-origin test (brief M2-07's mutation): refused before any tile is read.

    Moving the origin changes no height, so without the check the step would build; a new
    height offset changes every height, so without it the step blamed the machine (P-02).
    """
    world = _changed_world(case, change)
    with pytest.raises(TerrainError) as refused:
        _build(case, world)
    message = str(refused.value)
    for part in _world_message_parts(case, world):
        assert part in message, (part, message)
    assert MACHINE not in message and "datasets.lock.json" not in message
    assert not case["out"].exists()


def test_the_step_names_republished_and_relocked_inputs_as_design_s_step(case):  # noqa: F811
    """The republished-and-relocked test (brief M2-07's mutation): I-01's proof.

    Every input vouched for by the lock and provenance.json, but not the one design
    computed the expected value from: refused before the tile is read, never blamed on the
    machine.
    """
    recorded_sha = case["config"]["areas"]["village"]["computed_for"]["inputs_sha256"]
    _republish_and_relock(case)
    current = _canonical_sha(case["lock"]["datasets"]["swissalti3d"])
    assert current != recorded_sha
    with pytest.raises(TerrainError) as refused:
        _build(case)
    message = str(refused.value)
    for part in (
        "area 'village'",
        "config/terrain.json",
        f"computed from the swissalti3d lock entry with SHA-256 {recorded_sha}",
        f"config/datasets.lock.json's entry now has {current}",
        "(a new edition or an adopted republished file)",
        "Adopting new inputs is a design change: design recomputes the expected values",
        "docs/SPEC.md §5, §8",
    ):
        assert part in message, (part, message)
    assert MACHINE not in message and "config/world.json" not in message
    assert not case["out"].exists()


def test_once_design_has_recorded_the_inputs_the_heights_decide(case):  # noqa: F811
    """After design's step (the config records the new lock), the old expected value is
    compared as before and its message stays as it was (the brief's decision)."""
    _republish_and_relock(case)
    case["config"] = recorded(case["config"], case["world"], case["lock"], "swissalti3d")
    with pytest.raises(TerrainError) as refused:
        _build(case)
    assert MACHINE in str(refused.value)  # the old expected value, the new heights
    assert not case["out"].exists()


def test_a_changed_world_is_named_before_changed_inputs(case):  # noqa: F811
    world = _changed_world(case, _shift_origin)
    _republish_and_relock(case)
    with pytest.raises(TerrainError) as refused:
        _build(case, world)
    assert "config/world.json now has" in str(refused.value)
    assert "datasets.lock.json" not in str(refused.value)


# The manifest over a terrain built for real, then the owner's change, no `terrain` run.


@pytest.fixture
def built(case):  # noqa: F811
    _build(case)
    paths = {
        "terrain": case["tmp"] / "terrain.json",
        "lock": case["tmp"] / "datasets.lock.json",
    }
    paths["terrain"].write_text(json.dumps(case["config"]), encoding="utf-8")
    lock.write_lock(case["lock"], paths["lock"])
    return dict(case, paths=paths)


def _manifest(built, world_path):
    return write_manifest(
        built["out"],
        world_path,
        terrain_config_path=built["paths"]["terrain"],
        lock_path=built["paths"]["lock"],
    )


def test_manifest_accepts_the_terrain_its_config_was_computed_for(built):
    """Positive control for the refusals below."""
    written = json.loads(_manifest(built, built["world"].path).read_bytes())
    assert written["terrain"]["area"] == "village"


@pytest.mark.parametrize(
    "change",
    [_shift_origin, lambda d: d.update(height_offset_m=1000.0)],
    ids=["origin-moved-1-km", "height-offset"],
)
def test_manifest_names_a_changed_world_as_design_s_step(built, change):
    """P-02's dead end: the old refusal said the terrain was built for another world and
    named `terrain`, which then refused as the step did before M2-07."""
    world = _changed_world(built, change)
    with pytest.raises(TerrainError) as refused:
        _manifest(built, world.path)
    message = str(refused.value)
    for part in _world_message_parts(built, world):
        assert part in message, (part, message)
    assert TERRAIN_COMMAND not in message
    assert not (built["out"] / "manifest.json").exists()


def test_manifest_names_a_relocked_input_as_design_s_step(built):
    """I-01's dead end: the tile republished, locked and downloaded; `manifest` used to name
    `terrain`, which could not help."""
    recorded_sha = built["config"]["areas"]["village"]["computed_for"]["inputs_sha256"]
    _republish_and_relock(built)
    lock.write_lock(built["lock"], built["paths"]["lock"])
    with pytest.raises(TerrainError) as refused:
        _manifest(built, built["world"].path)
    message = str(refused.value)
    current = _canonical_sha(built["lock"]["datasets"]["swissalti3d"])
    for part in (recorded_sha, current, "datasets.lock.json", "design recomputes"):
        assert part in message, (part, message)
    assert TERRAIN_COMMAND not in message
    assert not (built["out"] / "manifest.json").exists()
