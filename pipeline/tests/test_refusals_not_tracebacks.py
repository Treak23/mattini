"""Pinning tests for brief M3-01 (M2 V1-P-05): refusals, not tracebacks, on the command line.

Design's full replacement of the file brief M2-07 wrote (M2 R1 I-05; Hard Rule 2), which
it keeps whole, adding one case and the means to run it.

The review found `lock buildings` and `download buildings` ending in a Python traceback
(`KeyError: 'swissbuildings3d'`) when config/datasets.json lacks the dataset, and the sheet
grid's ValueError reaching the owner the same way for an area it cannot place. Here each
command runs as the owner runs it, in a process of its own, `python -m mattini`'s `main`
with only its inputs patched: a world, terrain, buildings or datasets config of the
test's own, the lock copied to a temporary folder, and fetchers that fail the test if
anything reaches for the network. Every run must end with exit status 1, a
`mattini: error:` line naming the file and no `Traceback`, and write nothing. The
terrain's twin (a datasets config without swissalti3d) is the same class of defect and
is checked the same way.

Pinned decision (brief M3-01, V1-P-05): a `swissalti3d` entry without `resolution_m` is a
refusal naming the datasets config and `resolution_m`, for each of the four commands that
read it (`lock terrain`, `download terrain`, `terrain`, and `manifest` over a built
terrain), which ended in `KeyError: 'resolution_m'`. The check lives in the datasets
config's loader, `load_datasets`, which refuses an entry without a positive number of
metres there (a DatasetsConfigError naming the file), and which brief M3-03 extends to its
new datasets. So that case hands the commands a datasets FILE (`datasets_file`), read by
the real loader and passed to `write_manifest` as its `datasets_path`, where the other
cases hand them the parsed config: a check in the loader is reached only that way.

Does NOT prove: that no other input ends in a traceback (these are the ones the review
found and their twins).
"""

import hashlib
import json
import shutil
import subprocess
import sys

import pytest

from mattini.datasets import DatasetsConfigError, load_datasets
from mattini.manifest import write_manifest
from mattini.terrain import TerrainError
from mattini.world import REPO

# Run in a process of its own: an uncaught exception prints a traceback on stderr there.
DRIVER = """
import functools, json, sys
from pathlib import Path
import mattini.__main__ as cli
from mattini import buildings, download, lock, terrain
from mattini.datasets import load_datasets
from mattini.world import load_world

spec = json.loads(sys.argv[1])

def no_network(*args):
    raise AssertionError("the test reached for the network")

download.urllib_fetch_json = no_network
download.urllib_fetch_file = no_network
lock.LOCK_PATH = Path(spec["lock_path"])
if spec["world"] is not None:
    cli.load_world = lambda: load_world(spec["world"])
if spec["terrain"] is not None:
    terrain.load_terrain_config = lambda: spec["terrain"]
if spec["buildings"] is not None:
    buildings.load_buildings_config = lambda: spec["buildings"]
if spec["datasets"] is not None:
    cli.load_datasets = lambda: spec["datasets"]
if spec["datasets_file"] is not None:  # read by the real loader, as config/datasets.json is
    cli.load_datasets = lambda: load_datasets(spec["datasets_file"])
    cli.write_manifest = functools.partial(cli.write_manifest, datasets_path=spec["datasets_file"])
sys.exit(cli.main(spec["argv"]))
"""

WORLD = json.loads((REPO / "config" / "world.json").read_text(encoding="utf-8"))
DATASETS = json.loads((REPO / "config" / "datasets.json").read_text(encoding="utf-8"))
TERRAIN = json.loads((REPO / "config" / "terrain.json").read_text(encoding="utf-8"))
BUILDINGS = json.loads((REPO / "config" / "buildings.json").read_text(encoding="utf-8"))
LOCK = (REPO / "config" / "datasets.lock.json").read_bytes()


def _run(
    tmp_path, argv, *, world=None, terrain=None, buildings=None, datasets=None, datasets_file=None
):
    lock_path = tmp_path / "config" / "datasets.lock.json"
    lock_path.parent.mkdir(exist_ok=True)
    lock_path.write_bytes(LOCK)
    spec = {
        "argv": argv,
        "lock_path": str(lock_path),
        "world": str(world) if world else None,
        "terrain": terrain,
        "buildings": buildings,
        "datasets": datasets,
        "datasets_file": str(datasets_file) if datasets_file else None,
    }
    done = subprocess.run(  # the exit status is checked by _refused
        [sys.executable, "-c", DRIVER, json.dumps(spec)],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        timeout=120,
        check=False,
    )
    assert lock_path.read_bytes() == LOCK  # a refusal writes no lock
    return done


def _refused(done, *parts):
    assert "Traceback" not in done.stderr, done.stderr
    assert done.returncode == 1, (done.returncode, done.stderr)
    assert done.stdout == ""
    assert done.stderr.startswith("mattini: error: "), done.stderr
    for part in parts:
        assert part in done.stderr, (part, done.stderr)


def _without(name):
    return {key: value for key, value in DATASETS["datasets"].items() if key != name}


@pytest.mark.parametrize(
    ("argv", "dataset"),
    [
        (["lock", "buildings"], "swissbuildings3d"),
        (["download", "buildings", "--out", "raw"], "swissbuildings3d"),
        (["lock", "terrain"], "swissalti3d"),
        (["download", "terrain", "--out", "raw"], "swissalti3d"),
    ],
    ids=["lock-buildings", "download-buildings", "lock-terrain", "download-terrain"],
)
def test_a_datasets_config_without_the_dataset_is_a_refusal(tmp_path, argv, dataset):
    done = _run(tmp_path, argv, datasets=_without(dataset))
    _refused(done, "config/datasets.json", f"has no {dataset!r} dataset")
    assert not (tmp_path / "raw").exists()


def test_the_terrain_step_without_swissalti3d_is_a_refusal(tmp_path):
    """The terrain's twin reaches the step as well: refused before any tile is looked for."""
    done = _run(
        tmp_path,
        ["terrain", "--raw", "raw", "--out", "generated"],
        datasets=_without("swissalti3d"),
    )
    _refused(done, "config/datasets.json", "has no 'swissalti3d' dataset")
    assert not (tmp_path / "generated").exists()


def test_manifest_over_a_built_terrain_without_swissalti3d_is_a_refusal(tmp_path):
    """A built terrain, then a datasets config without swissalti3d: `manifest` refuses it,
    naming the dataset and the rebuild, where it used to end in a KeyError."""
    fixture = REPO / "tests" / "shared" / "terrain_fixture"
    out = tmp_path / "generated"
    shutil.copytree(fixture / "generated" / "terrain", out / "terrain")
    data = json.loads((fixture / "datasets.json").read_text(encoding="utf-8"))
    del data["datasets"]["swissalti3d"]
    datasets = tmp_path / "datasets.json"
    datasets.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(TerrainError) as refused:
        write_manifest(
            out,
            fixture / "world.json",
            terrain_config_path=fixture / "terrain.json",
            datasets_path=datasets,
            lock_path=fixture / "datasets.lock.json",
        )
    message = str(refused.value)
    for part in ("has no 'swissalti3d' dataset", "`python -m mattini terrain`"):
        assert part in message, (part, message)
    assert not (out / "manifest.json").exists()


@pytest.mark.parametrize(
    "argv",
    [
        ["lock", "terrain"],
        ["download", "terrain", "--out", "raw"],
        ["terrain", "--raw", "raw", "--out", "generated"],
        ["manifest", "--out", "generated"],
    ],
    ids=["lock-terrain", "download-terrain", "terrain", "manifest"],
)
def test_a_swissalti3d_entry_without_resolution_m_is_a_refusal(tmp_path, argv):
    """V1-P-05: each of the four ended in `KeyError: 'resolution_m'`. The datasets file is
    config/datasets.json without that one key; `manifest` has a terrain to check (a stand-in
    description, which it must not reach)."""
    data = json.loads(json.dumps(DATASETS))
    del data["datasets"]["swissalti3d"]["resolution_m"]
    datasets_file = tmp_path / "config" / "datasets.json"
    datasets_file.parent.mkdir(exist_ok=True)
    datasets_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    ((area, _),) = TERRAIN["areas"].items()
    (tmp_path / "generated" / "terrain").mkdir(parents=True)
    (tmp_path / "generated" / "terrain" / f"{area}.json").write_text("{}\n", encoding="utf-8")
    done = _run(tmp_path, argv, datasets_file=datasets_file)
    _refused(done, "datasets.json", "resolution_m")
    assert not (tmp_path / "raw").exists()
    assert sorted(p.name for p in (tmp_path / "generated").iterdir()) == ["terrain"]


@pytest.mark.parametrize(
    "value",
    [None, "0.5", 0, -0.5, True],
    ids=["missing", "a-string", "zero", "negative", "a-boolean"],
)
def test_the_datasets_loader_refuses_swissalti3d_without_a_resolution(tmp_path, value):
    data = json.loads(json.dumps(DATASETS))
    if value is None:
        del data["datasets"]["swissalti3d"]["resolution_m"]
    else:
        data["datasets"]["swissalti3d"]["resolution_m"] = value
    path = tmp_path / "datasets.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    with pytest.raises(DatasetsConfigError) as refused:
        load_datasets(path)
    message = str(refused.value)
    for part in (str(path), "swissalti3d", "resolution_m"):
        assert part in message, (part, message)


EAST_EDGE = (2829000.0, 2829950.0, 1167500.0, 1168500.0)  # the review's box, 50 m from it


def _world_with(tmp_path, box):
    """The committed world plus an area `edge` of `box`, at <tmp>/config/world.json."""
    data = json.loads(json.dumps(WORLD))
    data["areas"]["edge"] = dict(zip(("e_min", "e_max", "n_min", "n_max"), box, strict=True))
    path = tmp_path / "config" / "world.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _named_edge(config, world=None):
    """`config` (terrain or buildings) with its one area renamed `edge`; with `world`, its
    values recorded as computed for that world (so the step reaches the grid)."""
    ((_, settings),) = json.loads(json.dumps(config))["areas"].items()
    if world is not None:
        settings["computed_for"]["world_sha256"] = hashlib.sha256(world.read_bytes()).hexdigest()
    return {"schema": 1, "areas": {"edge": settings}}


@pytest.mark.parametrize(
    ("box", "complaint"),
    [
        (EAST_EDGE, "no sheets east of E 2'830'000 in mattini's grid: design extends it"),
        ((2600000.0, 2601000.0, 600000.0, 601000.0), "not wholly inside the LK25 sheet grid"),
    ],
    ids=["within-the-margin-of-the-east-edge", "south-of-the-grid"],
)
@pytest.mark.parametrize(
    "argv",
    [["lock", "buildings"], ["download", "buildings", "--out", "raw"]],
    ids=["lock", "download"],
)
def test_an_area_the_sheet_grid_cannot_place_is_a_refusal(tmp_path, box, complaint, argv):
    world = _world_with(tmp_path, box)
    done = _run(tmp_path, argv, world=world, terrain=_named_edge(TERRAIN))
    _refused(done, "area 'edge'", "config/world.json", complaint)
    assert not (tmp_path / "raw").exists()


def test_the_buildings_step_refuses_such_an_area_too(tmp_path):
    """The step asks the grid for the area's sheets as well, once the world check passes."""
    world = _world_with(tmp_path, EAST_EDGE)
    done = _run(
        tmp_path,
        ["buildings", "--raw", "raw", "--out", "generated"],
        world=world,
        terrain=_named_edge(TERRAIN, world),
        buildings=_named_edge(BUILDINGS, world),
    )
    _refused(done, "area 'edge'", "config/world.json", "no sheets east of E 2'830'000")
    assert not (tmp_path / "generated").exists()
