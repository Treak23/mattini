"""Refusals, not tracebacks, on the command line (brief M2-07, M2 R1 I-05; Hard Rule 2).

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

Does NOT prove: that no other input ends in a traceback (these are the ones the review
found and their twins).
"""

import hashlib
import json
import shutil
import subprocess
import sys

import pytest

from mattini.manifest import write_manifest
from mattini.terrain import TerrainError
from mattini.world import REPO

# Run in a process of its own: an uncaught exception prints a traceback on stderr there.
DRIVER = """
import json, sys
from pathlib import Path
import mattini.__main__ as cli
from mattini import buildings, download, lock, terrain
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
sys.exit(cli.main(spec["argv"]))
"""

WORLD = json.loads((REPO / "config" / "world.json").read_text(encoding="utf-8"))
DATASETS = json.loads((REPO / "config" / "datasets.json").read_text(encoding="utf-8"))
TERRAIN = json.loads((REPO / "config" / "terrain.json").read_text(encoding="utf-8"))
BUILDINGS = json.loads((REPO / "config" / "buildings.json").read_text(encoding="utf-8"))
LOCK = (REPO / "config" / "datasets.lock.json").read_bytes()


def _run(tmp_path, argv, *, world=None, terrain=None, buildings=None, datasets=None):
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
