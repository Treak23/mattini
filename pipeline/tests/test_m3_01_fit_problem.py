"""Brief M3-01's own tests of `lock.fit_problem`, the one rule for the lock's fit.

Pinned decisions (brief M3-01, decision 1): `fit_problem(lock, datasets, world, area,
dataset)` is None when the lock's entry for `dataset` is for the datasets config's
collection and edition (`swissalti3d`: and resolution_m) and pins exactly the area's
tiles or map sheets; otherwise it is the refusal text, which names the area and
`python -m mattini lock <x>` for that dataset alone. test_lock_fit.py pins what the
download, the step and `manifest` make of it; these pin the rule itself, branch by branch,
on the committed configs (the village: six tiles, six sheets).

A dataset without a rule is a ValueError, and a datasets config without the dataset is a
DownloadError naming config/datasets.json: neither is a lock problem.

Does NOT prove: that the committed lock is swisstopo's (the network tests do); the rule
for the datasets M3-03 adds.
"""

import copy
import json

import pytest

from mattini.datasets import load_datasets
from mattini.download import DownloadError, area_sheets, area_tiles
from mattini.lock import fit_problem
from mattini.terrain import configured_area, load_terrain_config
from mattini.world import REPO, load_world

LOCK_TERRAIN = "python -m mattini lock terrain"
LOCK_BUILDINGS = "python -m mattini lock buildings"
WORLD = load_world()
DATASETS = load_datasets()
AREA = configured_area(load_terrain_config())
COMMITTED = json.loads((REPO / "config" / "datasets.lock.json").read_text(encoding="utf-8"))
TILES, SHEETS = area_tiles(WORLD, AREA), area_sheets(WORLD, AREA)
KINDS = {
    "swissalti3d": ("tiles", TILES, LOCK_TERRAIN),
    "swissbuildings3d": ("sheets", SHEETS, LOCK_BUILDINGS),
}
BOTH = pytest.mark.parametrize("dataset", sorted(KINDS))


def _problem(dataset: str, change=None, lock=None) -> str | None:
    lock = copy.deepcopy(COMMITTED) if lock is None else lock
    if change is not None:
        change(lock["datasets"][dataset])
    return fit_problem(lock, DATASETS, WORLD, AREA, dataset)


@BOTH
def test_the_committed_lock_fits_the_committed_configs(dataset):
    assert _problem(dataset) is None


@BOTH
def test_an_entry_beside_the_dataset_s_changes_nothing(dataset):
    """The other dataset's entry is not this dataset's business."""
    other = next(name for name in KINDS if name != dataset)
    lock = copy.deepcopy(COMMITTED)
    del lock["datasets"][other]
    assert fit_problem(lock, DATASETS, WORLD, AREA, dataset) is None


@BOTH
def test_an_extra_tile_or_sheet_is_refused_naming_it_and_what_the_area_needs(dataset):
    files, needed, command = KINDS[dataset]
    east, north = needed[-1].split("-")
    extra = f"{int(east) + 1}-{north}"

    def add(entry):
        entry[files][extra] = dict(entry[files][needed[-1]])

    message = _problem(dataset, add)
    assert extra in message and f"the area needs exactly {needed}" in message, message
    assert repr(AREA) in message and f"`{command}`" in message, message


@BOTH
def test_a_missing_tile_or_sheet_is_refused_naming_it(dataset):
    files, needed, command = KINDS[dataset]
    gone = needed[len(needed) // 2]
    message = _problem(dataset, lambda entry: entry[files].pop(gone))
    assert f"pins no checksum for the {files} {[gone]} of the area" in message, message
    assert repr(AREA) in message and f"`{command}`" in message, message


@BOTH
def test_a_missing_one_is_named_before_an_extra_one(dataset):
    files, needed, _ = KINDS[dataset]

    def swap(entry):
        entry[files].pop(needed[0])
        entry[files]["2999-1999"] = {"file": "x.tif", "sha256": "ab" * 32}

    message = _problem(dataset, swap)
    assert "pins no checksum" in message and needed[0] in message, message


@BOTH
@pytest.mark.parametrize("key", ["collection", "edition"])
def test_another_collection_or_edition_is_refused_naming_both_values(dataset, key):
    _, _, command = KINDS[dataset]
    message = _problem(dataset, lambda entry: entry.update({key: "elsewhere"}))
    configured = DATASETS[dataset][key]
    assert f"{dataset} {key} 'elsewhere', the config pins {configured!r}" in message, message
    assert f"`{command}`" in message, message


def test_another_resolution_is_refused_for_swissalti3d_alone():
    message = _problem("swissalti3d", lambda entry: entry.update(resolution_m=2.0))
    assert "resolution_m 2.0, the config pins 0.5" in message, message


@BOTH
def test_no_entry_is_refused(dataset):
    _, _, command = KINDS[dataset]
    lock = copy.deepcopy(COMMITTED)
    del lock["datasets"][dataset]
    message = fit_problem(lock, DATASETS, WORLD, AREA, dataset)
    assert f"has no {dataset!r} entry" in message and f"`{command}`" in message, message


@BOTH
@pytest.mark.parametrize(
    "lock",
    ["a string", None, {}, {"datasets": []}, {"datasets": {"swissalti3d": "x"}}],
    ids=["string", "none", "empty", "datasets-a-list", "entry-a-string"],
)
def test_a_lock_that_is_not_a_lock_is_a_refusal_not_a_traceback(dataset, lock):
    message = fit_problem(lock, DATASETS, WORLD, AREA, dataset)
    assert f"has no {dataset!r} entry" in message, message


@BOTH
def test_an_entry_without_its_files_is_refused(dataset):
    files, _, _ = KINDS[dataset]
    message = _problem(dataset, lambda entry: entry.update({files: "none"}))
    assert f"has no {files}" in message, message


@BOTH
def test_the_refusal_names_one_lock_command_and_no_other(dataset):
    _, _, command = KINDS[dataset]
    other = LOCK_BUILDINGS if command == LOCK_TERRAIN else LOCK_TERRAIN
    message = _problem(dataset, lambda entry: entry.update(edition="elsewhere"))
    assert command in message and other not in message, message
    for forbidden in ("python -m mattini download", "python -m mattini manifest", "design"):
        assert forbidden not in message, (forbidden, message)


def test_a_datasets_config_without_the_dataset_is_a_download_error_naming_the_file():
    datasets = {k: v for k, v in DATASETS.items() if k != "swissalti3d"}
    with pytest.raises(DownloadError, match=r"config/datasets\.json has no 'swissalti3d'"):
        fit_problem(COMMITTED, datasets, WORLD, AREA, "swissalti3d")


def test_a_dataset_without_a_rule_is_refused_by_name():
    with pytest.raises(ValueError, match="no fit rule for dataset 'swissimage'"):
        fit_problem(COMMITTED, DATASETS, WORLD, AREA, "swissimage")
