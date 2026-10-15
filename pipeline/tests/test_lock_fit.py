"""Pinning tests for brief M3-01 (M2 V1-P-01, V1-P-02, V1-P-07): one rule for the lock's fit.

Pinned decisions (docs/SPEC.md §5, the lock; §8, the expected output; brief M3-01): a
dataset's lock entry fits when it is for the datasets config's collection and edition
(`swissalti3d`: and resolution_m) and pins exactly the area's tiles (`swissalti3d`) or map
sheets (`swissbuildings3d`): none missing and none beside them. `download <x>`, the step
and `manifest` apply that one rule, and refuse a lock that does not fit naming
`python -m mattini lock <x>` and no other command. `manifest` checks the fit where the
step does: after the world (`computed_for.world_sha256`), before the inputs
(`computed_for.inputs_sha256`) and before any check of the built block itself. So for the
same configs and lock the step and `manifest` name the same command, which this file
asserts case by case. The built block here is a stand-in that any check of the block would
refuse, naming the rebuild: only a fit checked first names the lock.

Harm prevented: a hand-edited or stale lock answered with "design recomputes" or "rebuild"
(the review's three refusals before the one that helps), and `download terrain` reporting
success for a lock that `terrain` and `manifest` then refuse (I-04's terrain twin).

The committed configs serve as the inputs (the village: six tiles, six sheets); no tile or
sheet file exists, since a lock that does not fit is refused before any is read.

Does NOT prove: that the committed lock is swisstopo's (test_tile_lock.py and the network
test); anything about the files a fitting lock vouches for.
"""

import json
import re

import pytest
from fake_swisstopo import FakeSwisstopo

from mattini import lock as lock_module
from mattini.buildings import BuildingsError, build_buildings, load_buildings_config
from mattini.datasets import load_datasets
from mattini.download import DownloadError, area_sheets, area_tiles, download_terrain
from mattini.manifest import write_manifest
from mattini.terrain import TerrainError, build_terrain, load_terrain_config
from mattini.world import REPO, load_world

CONFIG = REPO / "config"
WORLD = CONFIG / "world.json"
DATASETS = CONFIG / "datasets.json"
TERRAIN_CONFIG = CONFIG / "terrain.json"
BUILDINGS_CONFIG = CONFIG / "buildings.json"
LOCK = CONFIG / "datasets.lock.json"
LOCK_TERRAIN = "python -m mattini lock terrain"
LOCK_BUILDINGS = "python -m mattini lock buildings"
COMMAND = re.compile(
    r"python -m mattini (?:(?:lock|download) )?(?:terrain|buildings)|python -m mattini manifest"
)
DESIGN = "design's step"  # what a refusal names when it says "design recomputes"


def _named(message: str) -> set[str]:
    """The commands a refusal names, and design's step when it names that."""
    named = set(COMMAND.findall(message))
    if "design recomputes" in message:
        named.add(DESIGN)
    return named


def _area() -> str:
    ((area, _),) = load_terrain_config(TERRAIN_CONFIG)["areas"].items()
    return area


def _committed_lock() -> dict:
    return json.loads(LOCK.read_text(encoding="utf-8"))


def _moved_world(folder):
    """The committed world with its origin moved 1 m east: a changed world for design."""
    data = json.loads(WORLD.read_text(encoding="utf-8"))
    data["origin_lv95"]["e"] += 1.0
    path = folder / "moved" / "world.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _provenance(raw_root, dataset: str, entry: dict, unit: str, ids: list[str]) -> None:
    """provenance.json as the download leaves it for `ids`, from the committed lock's
    entry; the files themselves are absent (a step reads them only after its checks)."""
    datasets = load_datasets(DATASETS)
    folder = raw_root / dataset / datasets[dataset]["edition"]
    folder.mkdir(parents=True)
    key = "tile" if unit == "tiles" else "sheet"
    data = {
        "attribution": datasets[dataset]["attribution"],
        "collection": datasets[dataset]["collection"],
        "dataset": dataset,
        "edition": datasets[dataset]["edition"],
        "schema": 1,
        unit: [
            {"file": entry[unit][part]["file"], "sha256": entry[unit][part]["sha256"], key: part}
            for part in ids
        ],
    }
    if dataset == "swissalti3d":
        data["resolution_m"] = datasets[dataset]["resolution_m"]
    (folder / "provenance.json").write_text(json.dumps(data, indent=2), encoding="utf-8")


def _stand_in_block(out, folder: str) -> None:
    """A built block that no check of a block accepts: `{}` as `<folder>/<area>.json`."""
    (out / folder).mkdir(parents=True)
    (out / folder / f"{_area()}.json").write_text("{}\n", encoding="utf-8")


def _east_neighbour(ids: list[str]) -> str:
    """An id east of the area's last one: a tile or sheet the area does not need."""
    first, second = ids[-1].split("-")
    return f"{int(first) + 1}-{second}"


# ---------------------------------------------------------------------- the terrain


def _terrain_lock_changes():
    tiles = area_tiles(load_world(WORLD), _area())

    def extra(entry):
        entry["tiles"][_east_neighbour(tiles)] = dict(entry["tiles"][tiles[-1]])

    def missing(entry):
        del entry["tiles"][tiles[len(tiles) // 2]]

    return [
        pytest.param(extra, id="an-extra-tile"),
        pytest.param(missing, id="a-missing-tile"),
        pytest.param(lambda entry: entry.update(edition="2019"), id="another-edition"),
        pytest.param(lambda entry: entry.update(resolution_m=2.0), id="another-resolution"),
        pytest.param(
            lambda entry: entry.update(collection="ch.swisstopo.swissalti3d_x"),
            id="another-collection",
        ),
    ]


def _terrain_refusals(tmp_path, change, *, world=WORLD, drop=False):
    """(the step's refusal, manifest's refusal) for the committed configs and a lock whose
    swissalti3d entry is changed by `change` (or dropped)."""
    committed = _committed_lock()
    area = _area()
    tiles = area_tiles(load_world(WORLD), area)
    raw_root = tmp_path / "raw"
    _provenance(raw_root, "swissalti3d", committed["datasets"]["swissalti3d"], "tiles", tiles)
    pinned = _committed_lock()
    if drop:
        del pinned["datasets"]["swissalti3d"]
    elif change is not None:
        change(pinned["datasets"]["swissalti3d"])
    lock_path = lock_module.write_lock(pinned, tmp_path / "datasets.lock.json")

    with pytest.raises(TerrainError) as step:
        build_terrain(
            load_world(world),
            load_datasets(DATASETS),
            pinned,
            load_terrain_config(TERRAIN_CONFIG),
            raw_root,
            tmp_path / "step-out",
        )
    assert not (tmp_path / "step-out").exists(), "a refusal writes nothing"

    out = tmp_path / "generated"
    _stand_in_block(out, "terrain")
    with pytest.raises(TerrainError) as manifest:
        write_manifest(
            out,
            world,
            terrain_config_path=TERRAIN_CONFIG,
            datasets_path=DATASETS,
            lock_path=lock_path,
            buildings_config_path=BUILDINGS_CONFIG,
        )
    assert not (out / "manifest.json").exists(), "a refusal writes nothing"
    return str(step.value), str(manifest.value)


@pytest.mark.parametrize("change", _terrain_lock_changes())
def test_terrain_and_manifest_name_lock_terrain_for_a_lock_that_does_not_fit(tmp_path, change):
    step, manifest = _terrain_refusals(tmp_path, change)
    assert _named(step) == {LOCK_TERRAIN}, step
    assert _named(manifest) == {LOCK_TERRAIN}, manifest


def test_a_lock_without_the_terrain_entry_names_lock_terrain_in_both(tmp_path):
    step, manifest = _terrain_refusals(tmp_path, None, drop=True)
    assert _named(step) == {LOCK_TERRAIN}, step
    assert _named(manifest) == {LOCK_TERRAIN}, manifest


def test_a_changed_world_is_named_first_by_both_as_the_step_does(tmp_path):
    """The world comes before the lock in the step; `manifest` keeps that order."""
    changes = _terrain_lock_changes()
    step, manifest = _terrain_refusals(tmp_path, changes[0].values[0], world=_moved_world(tmp_path))
    assert _named(step) == {DESIGN} and "config/world.json" in step, step
    assert _named(manifest) == {DESIGN} and "config/world.json" in manifest, manifest


def test_the_committed_terrain_lock_fits(tmp_path):
    """Positive control: the lock as committed passes the fit and the inputs check; the step
    then looks for its first tile, `manifest` checks the stand-in block."""
    step, manifest = _terrain_refusals(tmp_path, None)
    assert _named(step) == {"python -m mattini download terrain"}, step
    assert _named(manifest) == {"python -m mattini terrain"}, manifest


def test_download_terrain_refuses_a_lock_pinning_an_extra_tile(tmp_path):
    """I-04's terrain twin: the area's tiles exactly, before swisstopo is asked anything."""
    world, datasets, area = load_world(WORLD), load_datasets(DATASETS), _area()
    fake = FakeSwisstopo()
    pinned = lock_module.build_lock(world, datasets, fake.fetch_json, area=area)
    tiles = area_tiles(world, area)
    extra = _east_neighbour(tiles)
    pinned["datasets"]["swissalti3d"]["tiles"][extra] = {
        "file": f"swissalti3d_2024_{extra}_0.5_2056_5728.tif",
        "sha256": "ab" * 32,
    }
    lock_module.validate_lock(pinned, "test")  # a well-formed lock; only its tiles are wrong
    fake.json_fetches.clear()
    with pytest.raises(DownloadError) as refused:
        download_terrain(
            world, datasets, tmp_path, fake.fetch_json, fake.fetch_file, lock=pinned, area=area
        )
    message = str(refused.value)
    for part in (extra, str(tiles), repr(area)):
        assert part in message, (part, message)
    assert _named(message) == {LOCK_TERRAIN}, message
    assert fake.json_fetches == [] and fake.file_fetches == []
    assert list(tmp_path.iterdir()) == []


# ---------------------------------------------------------------------- the buildings


def _buildings_lock_changes():
    sheets = area_sheets(load_world(WORLD), _area())

    def extra(entry):
        entry["sheets"][_east_neighbour(sheets)] = dict(entry["sheets"][sheets[-1]])

    def missing(entry):
        del entry["sheets"][sheets[len(sheets) // 2]]

    return [
        pytest.param(extra, id="an-extra-sheet"),
        pytest.param(missing, id="a-missing-sheet"),
        pytest.param(lambda entry: entry.update(edition="2019"), id="another-edition"),
        pytest.param(
            lambda entry: entry.update(collection="ch.swisstopo.swissbuildings3d_2"),
            id="another-collection",
        ),
    ]


def _buildings_refusals(tmp_path, change, *, world=WORLD, drop=False):
    """(the step's refusal, manifest's refusal) for the committed configs and a lock whose
    swissbuildings3d entry is changed by `change` (or dropped)."""
    committed = _committed_lock()
    area = _area()
    sheets = area_sheets(load_world(WORLD), area)
    raw_root = tmp_path / "raw"
    entry = committed["datasets"]["swissbuildings3d"]
    _provenance(raw_root, "swissbuildings3d", entry, "sheets", sheets)
    pinned = _committed_lock()
    if drop:
        del pinned["datasets"]["swissbuildings3d"]
    elif change is not None:
        change(pinned["datasets"]["swissbuildings3d"])
    lock_path = lock_module.write_lock(pinned, tmp_path / "datasets.lock.json")

    with pytest.raises(BuildingsError) as step:
        build_buildings(
            load_world(world),
            load_datasets(DATASETS),
            pinned,
            load_buildings_config(BUILDINGS_CONFIG),
            load_terrain_config(TERRAIN_CONFIG),
            raw_root,
            tmp_path / "step-out",
        )
    assert not (tmp_path / "step-out").exists(), "a refusal writes nothing"

    out = tmp_path / "generated"
    _stand_in_block(out, "buildings")
    with pytest.raises(BuildingsError) as manifest:
        write_manifest(
            out,
            world,
            terrain_config_path=TERRAIN_CONFIG,
            datasets_path=DATASETS,
            lock_path=lock_path,
            buildings_config_path=BUILDINGS_CONFIG,
        )
    assert not (out / "manifest.json").exists(), "a refusal writes nothing"
    return str(step.value), str(manifest.value)


@pytest.mark.parametrize("change", _buildings_lock_changes())
def test_buildings_and_manifest_name_lock_buildings_for_a_lock_that_does_not_fit(tmp_path, change):
    step, manifest = _buildings_refusals(tmp_path, change)
    assert _named(step) == {LOCK_BUILDINGS}, step
    assert _named(manifest) == {LOCK_BUILDINGS}, manifest


def test_a_lock_without_the_buildings_entry_names_lock_buildings_in_both(tmp_path):
    step, manifest = _buildings_refusals(tmp_path, None, drop=True)
    assert _named(step) == {LOCK_BUILDINGS}, step
    assert _named(manifest) == {LOCK_BUILDINGS}, manifest


def test_a_changed_world_is_named_first_for_the_buildings_too(tmp_path):
    changes = _buildings_lock_changes()
    step, manifest = _buildings_refusals(
        tmp_path, changes[0].values[0], world=_moved_world(tmp_path)
    )
    assert _named(step) == {DESIGN} and "config/world.json" in step, step
    assert _named(manifest) == {DESIGN} and "config/world.json" in manifest, manifest


def test_the_committed_buildings_lock_fits(tmp_path):
    """Positive control: the step then looks for its first sheet, `manifest` checks the
    stand-in block."""
    step, manifest = _buildings_refusals(tmp_path, None)
    assert _named(step) == {"python -m mattini download buildings"}, step
    assert _named(manifest) == {"python -m mattini buildings"}, manifest
