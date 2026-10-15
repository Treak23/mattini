"""Brief M3-01's own tests of the order of checks in the two steps and in `manifest`.

Pinned decisions (brief M3-01, decision 1): a step checks the world, then the lock's fit
(`lock.fit_problem`), then the inputs (`computed_for.inputs_sha256`), and only then reads
provenance.json, the tiles or sheets, or the block. test_lock_fit.py pins that the step and
`manifest` name the same command for the same configs; test_checks_before_reading.py pins
that no tile or sheet is opened before the world and inputs checks. These add what neither
does, in the situation the owner is in after editing a config and before downloading again:

- no download has completed in the folder the changed config asks for (no provenance.json
  at all), and the step still names `lock <x>`, or design's step, not `download <x>`;
- `manifest` over a built block whose datasets config lacks the dataset names the rebuild,
  never a KeyError (the fit is skipped there: there is no config to fit).

Harm prevented: a changed datasets config or an adopted lock answered with "no download has
completed here", a command that cannot help until the lock is right.

Does NOT prove: the order inside the checks the block itself gets (test_terrain_refusals.py
and test_buildings_step.py).
"""

import json
import shutil

import pytest
from one_tile import ALTI, TILE, one_tile_case

from mattini.buildings import BuildingsError, build_buildings, load_buildings_config
from mattini.datasets import load_datasets
from mattini.manifest import write_manifest
from mattini.terrain import TerrainError, build_terrain
from mattini.world import REPO, load_world

BUILDINGS_FIXTURE = REPO / "tests" / "shared" / "buildings_fixture"
SHEET = "1249-42"
NO_DOWNLOAD = "no download has completed here"


def _buildings_case(tmp_path) -> dict:
    """The shared buildings fixture's configs and lock, and a raw folder holding its
    source.json as sheet 1249-42 with the provenance.json `download buildings` leaves."""
    datasets = load_datasets(BUILDINGS_FIXTURE / "datasets.json")
    pinned = json.loads((BUILDINGS_FIXTURE / "datasets.lock.json").read_text(encoding="utf-8"))
    entry = pinned["datasets"]["swissbuildings3d"]["sheets"][SHEET]
    config = datasets["swissbuildings3d"]
    folder = tmp_path / "raw" / "swissbuildings3d" / config["edition"]
    folder.mkdir(parents=True)
    shutil.copy(BUILDINGS_FIXTURE / "source.json", folder / entry["file"])
    provenance = {
        "attribution": config["attribution"],
        "collection": config["collection"],
        "dataset": "swissbuildings3d",
        "edition": config["edition"],
        "schema": 1,
        "sheets": [{"file": entry["file"], "sha256": entry["sha256"], "sheet": SHEET}],
    }
    (folder / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    return {
        "world_path": BUILDINGS_FIXTURE / "world.json",
        "datasets": datasets,
        "lock": pinned,
        "raw_root": tmp_path / "raw",
        "provenance": folder / "provenance.json",
        "out": tmp_path / "generated",
    }


def _terrain(case, datasets=None, lock=None):
    return build_terrain(
        load_world(case["world_path"]),
        datasets or case["datasets"],
        lock or case["lock"],
        case["config"],
        case["raw_root"],
        case["out"],
    )


def _buildings(case, datasets=None, lock=None):
    return build_buildings(
        load_world(case["world_path"]),
        datasets or case["datasets"],
        lock or case["lock"],
        load_buildings_config(BUILDINGS_FIXTURE / "buildings.json"),
        json.loads((BUILDINGS_FIXTURE / "terrain.json").read_text(encoding="utf-8")),
        case["raw_root"],
        case["out"],
    )


# ---------------------------------------------------------------------- the terrain


def test_the_terrain_step_checks_the_fit_before_provenance(tmp_path):
    """Another edition in the datasets config: no folder for it, no provenance.json."""
    case = one_tile_case(tmp_path)
    datasets = {"swissalti3d": {**ALTI, "edition": "2019"}}
    with pytest.raises(TerrainError) as refused:
        _terrain(case, datasets)
    message = str(refused.value)
    assert "python -m mattini lock terrain" in message and NO_DOWNLOAD not in message, message
    assert "edition '2024', the config pins '2019'" in message, message
    assert not case["out"].exists()


def test_the_terrain_step_checks_the_inputs_before_provenance(tmp_path):
    """The lock re-pinned a tile, design's values not recomputed, the download not run."""
    case = one_tile_case(tmp_path)
    case["lock"]["datasets"]["swissalti3d"]["tiles"][TILE]["sha256"] = "ab" * 32
    (case["raw_dir"] / "provenance.json").unlink()
    with pytest.raises(TerrainError) as refused:
        _terrain(case)
    message = str(refused.value)
    assert "design recomputes" in message and NO_DOWNLOAD not in message, message
    assert not case["out"].exists()


def test_the_terrain_step_still_asks_for_the_download_once_the_lock_is_right(tmp_path):
    """Positive control: a fitting, adopted lock and no provenance.json reaches the download."""
    case = one_tile_case(tmp_path)
    (case["raw_dir"] / "provenance.json").unlink()
    with pytest.raises(TerrainError) as refused:
        _terrain(case)
    message = str(refused.value)
    assert NO_DOWNLOAD in message and "python -m mattini download terrain" in message, message


# ---------------------------------------------------------------------- the buildings


def test_the_buildings_step_checks_the_fit_before_provenance(tmp_path):
    case = _buildings_case(tmp_path)
    shutil.rmtree(case["raw_root"])
    datasets = json.loads(json.dumps(case["datasets"]))
    datasets["swissbuildings3d"]["edition"] = "2019"
    with pytest.raises(BuildingsError) as refused:
        _buildings(case, datasets)
    message = str(refused.value)
    assert "python -m mattini lock buildings" in message and NO_DOWNLOAD not in message, message
    assert not case["out"].exists()


def test_the_buildings_step_checks_the_inputs_before_provenance(tmp_path):
    case = _buildings_case(tmp_path)
    case["lock"]["datasets"]["swissbuildings3d"]["sheets"][SHEET]["sha256"] = "ab" * 32
    case["provenance"].unlink()
    with pytest.raises(BuildingsError) as refused:
        _buildings(case)
    message = str(refused.value)
    assert "design recomputes" in message and NO_DOWNLOAD not in message, message
    assert not case["out"].exists()


def test_the_buildings_step_still_asks_for_the_download_once_the_lock_is_right(tmp_path):
    case = _buildings_case(tmp_path)
    case["provenance"].unlink()
    with pytest.raises(BuildingsError) as refused:
        _buildings(case)
    message = str(refused.value)
    assert NO_DOWNLOAD in message and "python -m mattini download buildings" in message, message


def test_manifest_over_built_buildings_without_the_dataset_in_the_config_names_the_rebuild(
    tmp_path,
):
    """The fit has no config to compare with, and the later checks refuse it: a refusal
    naming the rebuild, where the lock's entry used to be looked up before that check."""
    out = tmp_path / "generated"
    shutil.copytree(BUILDINGS_FIXTURE / "generated" / "buildings", out / "buildings")
    data = json.loads((BUILDINGS_FIXTURE / "datasets.json").read_text(encoding="utf-8"))
    del data["datasets"]["swissbuildings3d"]
    datasets = tmp_path / "datasets.json"
    datasets.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(BuildingsError) as refused:
        write_manifest(
            out,
            BUILDINGS_FIXTURE / "world.json",
            terrain_config_path=BUILDINGS_FIXTURE / "terrain.json",
            datasets_path=datasets,
            lock_path=BUILDINGS_FIXTURE / "datasets.lock.json",
            buildings_config_path=BUILDINGS_FIXTURE / "buildings.json",
        )
    message = str(refused.value)
    for part in ("has no 'swissbuildings3d' dataset", "`python -m mattini buildings`"):
        assert part in message, (part, message)
    assert not (out / "manifest.json").exists()
