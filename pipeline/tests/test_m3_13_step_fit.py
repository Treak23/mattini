"""Brief M3-13's own tests: each of the four steps refuses a lock that does not fit with
`lock.fit_problem`'s text, and no step keeps a fit rule of its own.

Pinned decisions (brief M3-13; SPEC §8): the photo, roofs, surfaces and trees steps ask
`lock.fit_problem` whether the lock's entry of each dataset they read fits the datasets
config and the area, in sorted order, and refuse with its text, whole and unchanged, in
their own error class, in `build_<step>` and in `built_<step>_block alike. The text names
`python -m mattini lock <x>` for the dataset that does not fit and no other command. A lock
that fits but is not well-formed (an entry with another key, a file name that is not plain,
a checksum that is not 64 lower-case hex digits) is refused with `lock.shape_problem`'s text,
after the fit.

The committed configs and lock are the village's (the real run's inputs), the downloads an
empty folder, the built block a stand-in `{}`: everything the lock's check precedes (the
download, the block) would refuse differently, so only a check made first can say this text.

Harm prevented: a step that keeps its own copy of the fit rule beside `fit_problem`, which
refuses with other words than `manifest` does, or accepts what `manifest` refuses (the review's
"refusals before the one that helps", M2 V1-P-01, for the four new steps).

Does NOT prove: the checks after the lock's (the steps' own tests), nor that the committed lock
is swisstopo's.
"""

import copy
import hashlib

import pytest

from mattini.datasets import load_datasets
from mattini.lock import fit_problem, load_lock, shape_problem
from mattini.photo import PhotoError, build_photo, built_photo_block, load_photo_config
from mattini.roofs import RoofsError, build_roofs, built_roofs_block, load_roofs_config
from mattini.surfaces import (
    SurfacesError,
    build_surfaces,
    built_surfaces_block,
    load_surfaces_config,
)
from mattini.terrain import configured_area, load_terrain_config
from mattini.trees import TreesError, build_trees, built_trees_block, load_trees_config
from mattini.world import REPO, load_world

WORLD = load_world()
DATASETS = load_datasets()
COMMITTED = load_lock(REPO / "config" / "datasets.lock.json")
TERRAIN_CONFIG = load_terrain_config()
AREA = configured_area(TERRAIN_CONFIG)
WORLD_SHA256 = hashlib.sha256((REPO / "config" / "world.json").read_bytes()).hexdigest()
DROP = "drop"  # the change that removes the dataset's entry
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


def _extra_tile(entry):
    first, second = max(entry["tiles"]).split("-")
    entry["tiles"][f"{int(first) + 1}-{second}"] = copy.deepcopy(
        entry["tiles"][max(entry["tiles"])]
    )


def _missing_part(entry):
    parts = entry.get("tiles") or entry["sheets"]
    del parts[min(parts)]


def _collection(entry):
    entry["collection"] = "ch.swisstopo.somewhere-else"


def _resolution(entry):
    entry["resolution_m"] = 0.25


def _edition(entry):
    entry["edition"] = "1999-01"


def _surface_edition(entry):
    entry["tiles"][min(entry["tiles"])]["edition"] = "2019"


def _changes(dataset):
    """Every way the rule names that the committed entry of `dataset` can fail to fit."""
    entry = COMMITTED["datasets"][dataset]
    yield "no-entry", DROP
    yield "collection", _collection
    if "edition" in entry:
        yield "edition", _edition
    if "resolution_m" in entry:
        yield "resolution", _resolution
    if "tiles" in entry:
        yield "extra-tile", _extra_tile
        yield "missing-tile", _missing_part
    if "sheets" in entry:
        yield "missing-sheet", _missing_part
    if dataset == "swisssurface3d":
        yield "edition-not-accepted", _surface_edition


# (step, dataset, change, id): every dataset each step reads, in every way the rule names
CASES = [
    (step, dataset, change, case)
    for step, names in DATASETS_OF.items()
    for dataset in names
    for case, change in _changes(dataset)
]
# (step, change to a well-formed fitting entry that is not well-formed, what the text says)
MALFORMED = [
    ("photo", "swissimage", lambda e: e.update(note="x"), "exactly the keys"),
    (
        "roofs",
        "swissbuildings3d",
        lambda e: next(iter(e["sheets"].values())).update(file="../x"),
        "plain file name",
    ),
    ("surfaces", "swisstlm3d", lambda e: e.update(sha256="AB" * 32), "lower-case hex"),
    (
        "trees",
        "swissalti3d",
        lambda e: next(iter(e["tiles"].values())).pop("sha256"),
        "exactly the keys",
    ),
]


def _lock(dataset, change):
    lock = copy.deepcopy(COMMITTED)
    if change is DROP:
        del lock["datasets"][dataset]
    else:
        change(lock["datasets"][dataset])
    return lock


def _call(step, lock, tmp_path, *, built):
    """`build_<step>` over an empty download folder, or `built_<step>_block` over a stand-in
    description; the exception it raises."""
    raw, out = tmp_path / "raw", tmp_path / "out"
    raw.mkdir()
    if built:
        (out / step).mkdir(parents=True)
        (out / step / f"{AREA}.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(ERROR[step]) as refused:
        if step == "photo" and built:
            built_photo_block(out, load_photo_config(), WORLD, WORLD_SHA256, DATASETS, lock)
        elif step == "photo":
            build_photo(WORLD, DATASETS, lock, load_photo_config(), raw, out)
        elif step == "roofs" and built:
            built_roofs_block(
                out, load_roofs_config(), TERRAIN_CONFIG, WORLD, WORLD_SHA256, DATASETS, lock, {}
            )
        elif step == "roofs":
            build_roofs(WORLD, DATASETS, lock, load_roofs_config(), TERRAIN_CONFIG, raw, out)
        elif step == "surfaces" and built:
            built_surfaces_block(out, load_surfaces_config(), WORLD, WORLD_SHA256, DATASETS, lock)
        elif step == "surfaces":
            build_surfaces(WORLD, DATASETS, lock, load_surfaces_config(), raw, out)
        elif built:
            built_trees_block(
                out, load_trees_config(), TERRAIN_CONFIG, WORLD, WORLD_SHA256, DATASETS, lock
            )
        else:
            build_trees(WORLD, DATASETS, lock, load_trees_config(), TERRAIN_CONFIG, raw, out)
    if not built:
        assert not out.exists(), "a refusal writes nothing"
    return refused.value


@pytest.mark.parametrize("built", [False, True], ids=["build", "built-block"])
@pytest.mark.parametrize(
    ("step", "dataset", "change", "case"), CASES, ids=[f"{s}-{d}-{i}" for s, d, _, i in CASES]
)
def test_a_lock_that_does_not_fit_is_refused_with_fit_problem_s_text(
    tmp_path, step, dataset, change, case, built
):
    lock = _lock(dataset, change)
    wanted = fit_problem(lock, DATASETS, WORLD, AREA, dataset)
    assert wanted and COMMAND[dataset] in wanted  # the lock really does not fit
    refused = _call(step, lock, tmp_path, built=built)
    assert str(refused) == wanted  # the whole text, unchanged
    named = {c for c in COMMAND.values() if c in str(refused)}
    assert named == {COMMAND[dataset]}


@pytest.mark.parametrize("built", [False, True], ids=["build", "built-block"])
@pytest.mark.parametrize(
    ("step", "dataset", "change", "complaint"), MALFORMED, ids=[m[0] for m in MALFORMED]
)
def test_a_fitting_lock_that_is_not_well_formed_is_refused_with_shape_problem_s_text(
    tmp_path, step, dataset, change, complaint, built
):
    lock = _lock(dataset, change)
    for name in DATASETS_OF[step]:  # it fits: the rule asks nothing of keys, names or checksums
        assert fit_problem(lock, DATASETS, WORLD, AREA, name) is None, name
    wanted = shape_problem(lock)
    assert wanted and complaint in wanted
    assert str(_call(step, lock, tmp_path, built=built)) == wanted


@pytest.mark.parametrize("built", [False, True], ids=["build", "built-block"])
@pytest.mark.parametrize("step", sorted(ERROR))
def test_the_first_dataset_in_sorted_order_that_does_not_fit_is_the_one_named(
    tmp_path, step, built
):
    """A lock with no entry at all: the refusal is that of the step's first dataset, sorted."""
    names = DATASETS_OF[step]
    assert names == sorted(names)
    lock = {"schema": 1, "datasets": {}}
    refused = _call(step, lock, tmp_path, built=built)
    assert str(refused) == fit_problem(lock, DATASETS, WORLD, AREA, names[0])
    assert {c for c in COMMAND.values() if c in str(refused)} == {COMMAND[names[0]]}
