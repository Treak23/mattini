"""Brief M3-13's own tests of the checks `manifest` makes itself before a new block's own.

Pinned decisions (brief M3-13, decision 3; SPEC §8): for a built photo, roofs, surfaces or
trees block, `manifest` checks, in this order and in the step's error class, whatever the
step's own block function checks: `computed_for.world_sha256` against the world config, the
lock's fit for every dataset the step reads in sorted order (`lock.fit_problem`'s text,
whole), `computed_for.inputs_sha256` against the lock's entries, and, for the roofs, that
buildings are built (naming `python -m mattini buildings`); and only then calls the step's
`built_<step>_block`. test_manifest_lock_fit_m3.py pins the same refusals through the
command line, where the block functions repeat the checks and give the same words; here
those functions are stand-ins that fail the test when they are reached, so only a check
`manifest` made itself can pass, and a check dropped from `manifest` shows.

Harm prevented: `manifest` that leaves the order of its refusals to each step's own block
function, so that one step's wave-1 order (or a later change to it) decides what the owner is
told first, and a roofs block accepted for buildings nobody built.

Does NOT prove: that the block functions check what they should (the steps' own tests).
"""

import copy
import json

import pytest

from mattini import manifest as manifest_module
from mattini.datasets import load_datasets
from mattini.lock import fit_problem, load_lock, write_lock
from mattini.manifest import build_manifest, write_manifest
from mattini.photo import PhotoError
from mattini.roofs import RoofsError
from mattini.surfaces import SurfacesError
from mattini.terrain import configured_area, load_terrain_config
from mattini.trees import TreesError
from mattini.world import REPO, load_world

WORLD_PATH = REPO / "config" / "world.json"
COMMITTED = load_lock(REPO / "config" / "datasets.lock.json")
DATASETS = load_datasets()
WORLD = load_world()
AREA = configured_area(load_terrain_config())
ERROR = {"photo": PhotoError, "roofs": RoofsError, "surfaces": SurfacesError, "trees": TreesError}
DATASETS_OF = {
    "photo": ["swissimage"],
    "roofs": ["swissbuildings3d", "swissimage"],
    "surfaces": ["swisstlm3d"],
    "trees": ["swissalti3d", "swissbuildings3d", "swisssurface3d", "swisstlm3d"],
}
COMMAND = {
    "swissalti3d": "python -m mattini lock terrain",
    "swissbuildings3d": "python -m mattini lock buildings",
    "swissimage": "python -m mattini lock photo",
    "swisssurface3d": "python -m mattini lock surface",
    "swisstlm3d": "python -m mattini lock tlm",
}
SENTINEL = {"area": AREA, "stand-in": "returned by the step's block function"}


def _fail_if_reached(step):
    def block(*args, **kwargs):
        raise AssertionError(f"manifest reached {step}'s own block check")

    return block


@pytest.fixture
def blocks(monkeypatch):
    """The four block functions replaced by stand-ins that fail the test when they are reached."""
    for step in ERROR:
        monkeypatch.setattr(manifest_module, f"built_{step}_block", _fail_if_reached(step))


def _out(tmp_path, step):
    out = tmp_path / "generated"
    (out / step).mkdir(parents=True, exist_ok=True)
    (out / step / f"{AREA}.json").write_text("{}\n", encoding="utf-8")
    return out


def _lock_file(tmp_path, change=None):
    lock = copy.deepcopy(COMMITTED)
    if change:
        change(lock["datasets"])
    return write_lock(lock, tmp_path / "datasets.lock.json")


def _another_world(tmp_path):
    data = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
    data["origin_lv95"]["e"] += 1.0
    path = tmp_path / "moved-world.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _other_file(entry):
    if "sha256" in entry:
        entry["sha256"] = "ab" * 32
    else:
        parts = entry.get("tiles") or entry["sheets"]
        parts[min(parts)]["sha256"] = "ab" * 32


def _build(tmp_path, step, *, world=WORLD_PATH, lock=None):
    lock_path = lock or _lock_file(tmp_path)
    return build_manifest(world, _out(tmp_path, step), lock_path=lock_path)


@pytest.mark.parametrize("step", sorted(ERROR))
def test_a_changed_world_is_refused_first_naming_design(tmp_path, blocks, step):
    lock = _lock_file(tmp_path, lambda d: d.pop(DATASETS_OF[step][0]))  # the lock does not fit
    with pytest.raises(ERROR[step]) as refused:
        _build(tmp_path, step, world=_another_world(tmp_path), lock=lock)
    message = str(refused.value)
    assert "config/world.json" in message and "design recomputes" in message
    assert "python -m mattini" not in message


def _does_not_fit(entry):
    """Another collection: the entry no longer fits the datasets config, whatever it pins."""
    entry["collection"] = "ch.swisstopo.somewhere-else"


@pytest.mark.parametrize("step", sorted(ERROR))
def test_the_lock_s_fit_comes_before_the_inputs_and_is_fit_problem_s_text(tmp_path, blocks, step):
    """The first dataset's entry does not fit, and every entry also pins another file (the
    inputs differ): the fit is what the owner is told."""
    names = DATASETS_OF[step]

    def change(datasets):
        for name in names:
            _other_file(datasets[name])
        _does_not_fit(datasets[names[0]])

    pinned = copy.deepcopy(COMMITTED)
    change(pinned["datasets"])
    wanted = fit_problem(pinned, DATASETS, WORLD, AREA, names[0])
    assert wanted and COMMAND[names[0]] in wanted and "design" not in wanted
    with pytest.raises(ERROR[step]) as refused:
        _build(tmp_path, step, lock=_lock_file(tmp_path, change))
    assert str(refused.value) == wanted


@pytest.mark.parametrize("step", sorted(ERROR))
@pytest.mark.parametrize("position", ["first", "last"])
def test_every_dataset_the_step_reads_is_fitted_in_sorted_order(tmp_path, blocks, step, position):
    names = DATASETS_OF[step]
    name = names[0] if position == "first" else names[-1]
    lock = _lock_file(tmp_path, lambda d: d.pop(name))
    with pytest.raises(ERROR[step]) as refused:
        _build(tmp_path, step, lock=lock)
    assert COMMAND[name] in str(refused.value)
    assert {c for c in COMMAND.values() if c in str(refused.value)} == {COMMAND[name]}


@pytest.mark.parametrize("step", sorted(ERROR))
@pytest.mark.parametrize("position", ["first", "last"])
def test_a_fitting_lock_with_other_inputs_is_refused_naming_design(
    tmp_path, blocks, step, position
):
    names = DATASETS_OF[step]
    name = names[0] if position == "first" else names[-1]
    lock = _lock_file(tmp_path, lambda d: _other_file(d[name]))
    with pytest.raises(ERROR[step]) as refused:
        _build(tmp_path, step, lock=lock)
    message = str(refused.value)
    assert f"config/{step}.json" in message and "design recomputes" in message
    assert "python -m mattini" not in message


@pytest.mark.parametrize("step", sorted(ERROR))
def test_the_step_s_own_block_check_is_reached_only_after_the_three(tmp_path, monkeypatch, step):
    """The positive control: the committed world, lock and configs pass, the block function
    is called, and what it returns is the manifest's block (the roofs' with buildings built)."""
    seen = []

    def block(*args, **kwargs):
        seen.append(args)
        return SENTINEL

    if step == "roofs":
        monkeypatch.setattr(manifest_module, "built_buildings_block", lambda *a, **k: SENTINEL)
    monkeypatch.setattr(manifest_module, f"built_{step}_block", block)
    manifest = _build(tmp_path, step)
    assert manifest[step] == SENTINEL and len(seen) == 1
    others = {"buildings", "photo", "roofs", "surfaces", "terrain", "trees"} - {step}
    if step == "roofs":
        others -= {"buildings"}
    assert all(manifest[key] is None for key in others)


def test_roofs_without_buildings_are_refused_before_the_roofs_own_check(tmp_path, blocks):
    with pytest.raises(RoofsError) as refused:
        _build(tmp_path, "roofs")
    message = str(refused.value)
    assert "python -m mattini buildings" in message
    assert {c for c in COMMAND.values() if c in message} == set()


def test_roofs_are_refused_for_the_world_and_the_lock_before_the_missing_buildings(
    tmp_path, blocks
):
    with pytest.raises(RoofsError, match="design recomputes"):
        _build(tmp_path, "roofs", world=_another_world(tmp_path))
    with pytest.raises(RoofsError) as refused:
        _build(tmp_path, "roofs", lock=_lock_file(tmp_path, lambda d: d.pop("swissimage")))
    assert COMMAND["swissimage"] in str(refused.value)


@pytest.mark.parametrize(
    ("step", "keyword"),
    [
        ("photo", "photo_config_path"),
        ("roofs", "roofs_config_path"),
        ("surfaces", "surfaces_config_path"),
        ("trees", "trees_config_path"),
    ],
)
def test_every_step_config_is_checked_even_when_its_step_has_not_run(tmp_path, step, keyword):
    bad = tmp_path / f"{step}.json"
    bad.write_text("{}\n", encoding="utf-8")
    out = tmp_path / "generated"
    with pytest.raises(ERROR[step], match=str(bad)):
        write_manifest(out, WORLD_PATH, **{keyword: bad})
    assert not (out / "manifest.json").exists(), "a refusal writes nothing"
