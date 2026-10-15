"""Brief M3-03's own tests of the lock's three new entries and `fit_problem`'s rows for them.

Pinned decisions (docs/SPEC.md §5, brief M3-03 decisions 3 and 5): the lock holds five
entries with exact key sets: `swissimage` {collection, edition, resolution_m, tiles:
{<tile>: {file, sha256}}}, `swisssurface3d` {collection, resolution_m, tiles: {<tile>:
{edition, file, sha256}}} and `swisstlm3d` {collection, edition, file, sha256}. A malformed
lock is a LockError naming the file and all five lock commands. `fit_problem` (M3-01's one
rule) gets a row each: the photo as the terrain, the surface model with every tile's edition
one of the config's `editions`, the TLM national (no area in its refusal), each naming its own
`lock <x>` command and no other.

test_lock_photo_surface_tlm.py pins what the commands write; test_m3_01_fit_problem.py the
rule for the first two datasets. These pin the rest, branch by branch, on the committed
configs and lock (the village: six tiles).

Does NOT prove: that the committed lock is swisstopo's (test_download_network.py does).
"""

import copy
import json

import pytest

from mattini.datasets import load_datasets
from mattini.download import DownloadError, area_tiles
from mattini.lock import LOCK_COMMANDS, LockError, fit_problem, validate_lock, write_lock
from mattini.terrain import configured_area, load_terrain_config
from mattini.world import REPO, load_world

WORLD = load_world()
DATASETS = load_datasets()
AREA = configured_area(load_terrain_config())
COMMITTED = json.loads((REPO / "config" / "datasets.lock.json").read_text(encoding="utf-8"))
TILES = area_tiles(WORLD, AREA)
COMMAND = {
    "swissimage": "python -m mattini lock photo",
    "swisssurface3d": "python -m mattini lock surface",
    "swisstlm3d": "python -m mattini lock tlm",
}
NEW = sorted(COMMAND)


def _problem(dataset, change=None, lock=None):
    lock = copy.deepcopy(COMMITTED) if lock is None else lock
    if change is not None:
        change(lock["datasets"][dataset])
    return fit_problem(lock, DATASETS, WORLD, AREA, dataset)


# ---------------------------------------------------------------------- fit_problem


@pytest.mark.parametrize("dataset", NEW)
def test_the_committed_lock_fits_the_committed_configs(dataset):
    assert _problem(dataset) is None


def test_the_tlm_needs_neither_a_world_nor_an_area():
    assert fit_problem(COMMITTED, DATASETS, None, None, "swisstlm3d") is None
    message = fit_problem({"schema": 1, "datasets": {}}, DATASETS, None, None, "swisstlm3d")
    assert "has no 'swisstlm3d' entry" in message and "area" not in message, message


@pytest.mark.parametrize("dataset", ["swissimage", "swisssurface3d"])
def test_an_extra_or_a_missing_tile_is_refused_for_the_photo_and_the_surface(dataset):
    east, north = TILES[-1].split("-")
    extra = f"{int(east) + 1}-{north}"

    def add(entry):
        entry["tiles"][extra] = dict(entry["tiles"][TILES[-1]])

    message = _problem(dataset, add)
    assert extra in message and f"the area needs exactly {TILES}" in message, message
    assert COMMAND[dataset] in message and repr(AREA) in message, message

    message = _problem(dataset, lambda entry: entry["tiles"].pop(TILES[2]))
    assert f"pins no checksum for the tiles {[TILES[2]]} of the area" in message, message


@pytest.mark.parametrize(
    ("dataset", "key", "found"),
    [
        ("swissimage", "collection", "elsewhere"),
        ("swissimage", "edition", "2019"),
        ("swissimage", "resolution_m", 0.2),
        ("swisssurface3d", "collection", "elsewhere"),
        ("swisssurface3d", "resolution_m", 1.0),
        ("swisstlm3d", "collection", "elsewhere"),
        ("swisstlm3d", "edition", "2025-08"),
    ],
)
def test_another_collection_edition_or_resolution_is_refused(dataset, key, found):
    message = _problem(dataset, lambda entry: entry.update({key: found}))
    assert f"is for {dataset} {key} {found!r}, the config pins {DATASETS[dataset][key]!r}" in (
        message
    ), message
    assert COMMAND[dataset] in message, message


def test_a_surface_tile_in_an_edition_the_config_does_not_list_is_refused():
    def change(entry):
        entry["tiles"][TILES[3]]["edition"] = "2019"

    message = _problem("swisssurface3d", change)
    assert f"pins {TILES[3]} in edition '2019'" in message, message
    assert "['2021', '2022']" in message and COMMAND["swisssurface3d"] in message, message


def test_every_surface_tile_s_own_edition_is_accepted():
    """Positive control: the village's tile 2623-1095 is in 2022 and the rest in 2021."""
    editions = {
        tile: e["edition"] for tile, e in COMMITTED["datasets"]["swisssurface3d"]["tiles"].items()
    }
    assert set(editions.values()) == {"2021", "2022"}
    assert _problem("swisssurface3d") is None


@pytest.mark.parametrize("dataset", NEW)
def test_each_refusal_names_its_own_lock_command_and_no_other(dataset):
    message = _problem(dataset, lambda entry: entry.update(collection="elsewhere"))
    others = [c for c in LOCK_COMMANDS if c != COMMAND[dataset]]
    assert COMMAND[dataset] in message
    assert not any(other in message for other in others), message
    for forbidden in ("python -m mattini download", "python -m mattini manifest", "design"):
        assert forbidden not in message, (forbidden, message)


def test_a_datasets_config_without_the_new_dataset_is_a_download_error():
    for dataset in NEW:
        datasets = {k: v for k, v in DATASETS.items() if k != dataset}
        with pytest.raises(DownloadError, match=rf"config/datasets\.json has no '{dataset}'"):
            fit_problem(COMMITTED, datasets, WORLD, AREA, dataset)


@pytest.mark.parametrize(
    ("dataset", "wrong"),
    [
        ("swissalti3d", "editions"),
        ("swissbuildings3d", "editions"),
        ("swissimage", "editions"),
        ("swisstlm3d", "editions"),
        ("swisssurface3d", "edition"),
    ],
)
def test_the_wrong_kind_of_edition_in_the_config_is_a_refusal_not_a_key_error(dataset, wrong):
    datasets = copy.deepcopy(DATASETS)
    if wrong == "editions":
        datasets[dataset]["editions"] = [datasets[dataset].pop("edition")[:4]]
    else:
        datasets[dataset]["edition"] = datasets[dataset].pop("editions")[0]
    with pytest.raises(DownloadError, match=rf"config/datasets\.json: dataset '{dataset}' "):
        fit_problem(COMMITTED, datasets, WORLD, AREA, dataset)


# ---------------------------------------------------------------------- the lock's shapes


def _invalid(change, tmp_path=None):
    lock = copy.deepcopy(COMMITTED)
    change(lock["datasets"])
    with pytest.raises(LockError) as refused:
        validate_lock(lock, "lock.json")
    return str(refused.value)


def test_the_committed_lock_is_valid_and_written_back_byte_for_byte(tmp_path):
    validate_lock(COMMITTED, "lock.json")
    written = write_lock(COMMITTED, tmp_path / "datasets.lock.json")
    assert written.read_bytes() == (REPO / "config" / "datasets.lock.json").read_bytes()


@pytest.mark.parametrize(
    ("change", "complaint"),
    [
        (lambda d: d["swissimage"].update(extra=1), "exactly the keys"),
        (lambda d: d["swissimage"].pop("resolution_m"), "exactly the keys"),
        (lambda d: d["swissimage"].update(sheets=d["swissimage"].pop("tiles")), "exactly the keys"),
        (lambda d: d["swissimage"].update(resolution_m=0), "resolution_m"),
        (lambda d: d["swissimage"].update(resolution_m=True), "resolution_m"),
        (lambda d: d["swissimage"]["tiles"].clear(), "tiles must be a non-empty object"),
        (lambda d: d["swissimage"]["tiles"].update({"x": {}}), "a tile id is"),
        (
            lambda d: d["swissimage"]["tiles"]["2623-1095"].update(edition="2023"),
            "exactly the keys",
        ),
        (
            lambda d: d["swissimage"]["tiles"]["2623-1095"].update(sha256="AB" * 32),
            "lower-case hex",
        ),
        (lambda d: d["swisssurface3d"].update(edition="2021"), "exactly the keys"),
        (lambda d: d["swisssurface3d"]["tiles"]["2623-1095"].pop("edition"), "exactly the keys"),
        (lambda d: d["swisssurface3d"]["tiles"]["2623-1095"].update(edition="latest"), "edition"),
        (lambda d: d["swisssurface3d"]["tiles"]["2623-1095"].update(edition=2022), "edition"),
        (lambda d: d["swisssurface3d"]["tiles"]["2623-1095"].update(file="../x.tif"), "plain file"),
        (lambda d: d["swisstlm3d"].update(tiles={}), "exactly the keys"),
        (lambda d: d["swisstlm3d"].pop("file"), "exactly the keys"),
        (lambda d: d["swisstlm3d"].update(file="a/b.zip"), "plain file name"),
        (lambda d: d["swisstlm3d"].update(file="x.zip", sha256="12"), "64 lower-case hex"),
        (lambda d: d["swisstlm3d"].update(sha256=d["swisstlm3d"]["sha256"].upper()), "lower-case"),
        (lambda d: d["swisstlm3d"].update(edition=""), "edition must be a non-empty string"),
        (lambda d: d.update(swissnothing=d["swisstlm3d"]), "unknown dataset 'swissnothing'"),
    ],
)
def test_a_malformed_entry_is_refused_naming_the_file_and_all_five_commands(change, complaint):
    message = _invalid(change)
    assert message.startswith("lock.json: ") and complaint in message, message
    for command in LOCK_COMMANDS:
        assert f"`{command}`" in message, (command, message)
    assert len(LOCK_COMMANDS) == 5


def test_the_five_commands_are_the_five_lock_datasets():
    assert sorted(LOCK_COMMANDS) == sorted(
        f"python -m mattini lock {name}"
        for name in ("terrain", "buildings", "photo", "surface", "tlm")
    )
