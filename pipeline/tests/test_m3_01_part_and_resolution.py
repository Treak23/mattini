"""Brief M3-01's own tests beyond its pinned ones: `.part` leftovers and `resolution_m`.

`*.part` (decision 5; test_part_leftovers.py pins the two steps' success): a refusal removes
nothing, a `.part` that is a directory is left alone and does not stop the build, the
terrain step says how many it removed, `write_terrain` (the step's writer) cleans too, and
the files a build wrote are never taken for leftovers.

`resolution_m` (decision 4; test_refusals_not_tracebacks.py pins the four commands): the
loader's rule at its edges. A positive int or float is accepted; zero, negatives, NaN and
infinity, a string, a boolean and a list are refused, naming the file and the dataset; a
dataset that is not read at a resolution (swissBUILDINGS3D) needs none.

Does NOT prove: that the export leaves `*.part` out (the presets' exclude_filter, M3-08).
"""

import json
from pathlib import Path

import numpy as np
import pytest
from one_tile import AREA, BOX, HEIGHTS_SHA256, one_tile_case, write_world

from mattini.datasets import DatasetsConfigError, load_datasets
from mattini.terrain import TerrainError, build_terrain, write_terrain
from mattini.world import REPO, load_world

CUT_SHORT = b"a write cut short"


def _build(case, world_path=None, progress=None):
    return build_terrain(
        load_world(world_path or case["world_path"]),
        case["datasets"],
        case["lock"],
        case["config"],
        case["raw_root"],
        case["out"],
        progress=progress,
    )


# ---------------------------------------------------------------------- *.part


def test_a_refused_terrain_build_keeps_the_part_files(tmp_path):
    case = one_tile_case(tmp_path)
    terrain_dir = case["out"] / "terrain"
    terrain_dir.mkdir(parents=True)
    (terrain_dir / f"{AREA}.f32.part").write_bytes(CUT_SHORT)
    moved = write_world(tmp_path / "moved", lambda d: d["origin_lv95"].update(e=2600000.0))
    with pytest.raises(TerrainError, match="config/world.json now has"):
        _build(case, moved)
    assert [p.name for p in terrain_dir.iterdir()] == [f"{AREA}.f32.part"]


def test_the_terrain_step_says_how_many_part_files_it_removed(tmp_path):
    case = one_tile_case(tmp_path)
    terrain_dir = case["out"] / "terrain"
    terrain_dir.mkdir(parents=True)
    for name in ("elsewhere.f32.part", "elsewhere.json.part"):  # not the step's own names
        (terrain_dir / name).write_bytes(CUT_SHORT)
    said = []
    _build(case, progress=said.append)
    removed = [line for line in said if line.startswith("removed ")]
    assert removed == ["removed 2 .part files left in terrain/"]
    assert said.index(removed[0]) > max(
        i for i, line in enumerate(said) if line.startswith("wrote")
    )

    said.clear()
    _build(case, progress=said.append)  # nothing to remove, and no line about it
    assert [line for line in said if line.startswith("removed ")] == []


def test_a_part_that_is_a_directory_is_left_alone_and_the_build_goes_on(tmp_path):
    case = one_tile_case(tmp_path)
    stray = case["out"] / "terrain" / "stray.part"
    (stray / "inside").mkdir(parents=True)
    (stray / "inside" / "kept.txt").write_bytes(CUT_SHORT)
    _build(case)
    assert (stray / "inside" / "kept.txt").read_bytes() == CUT_SHORT
    assert (case["out"] / "terrain" / f"{AREA}.f32").is_file()


def test_write_terrain_removes_part_files_too_and_keeps_what_it_wrote(tmp_path):
    """The writer is public: a caller that writes through it gets a clean folder as well."""
    terrain_dir = tmp_path / "terrain"
    terrain_dir.mkdir()
    (terrain_dir / f"{AREA}.f32.part").write_bytes(CUT_SHORT)
    heights = np.full((3, 3), 600.0, dtype=np.float32)
    box = (BOX["e_min"], BOX["e_max"], BOX["n_min"], BOX["n_max"])
    block = write_terrain(tmp_path, AREA, heights, box, 2.0, "0" * 64, {})
    assert block["sha256"] == HEIGHTS_SHA256
    assert sorted(p.name for p in terrain_dir.iterdir()) == [f"{AREA}.f32", f"{AREA}.json"]


# ---------------------------------------------------------------------- resolution_m


def _datasets_file(tmp_path: Path, dataset: str, change) -> Path:
    data = json.loads((REPO / "config" / "datasets.json").read_text(encoding="utf-8"))
    change(data["datasets"][dataset])
    path = tmp_path / "datasets.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


@pytest.mark.parametrize("value", [0.5, 1, 2, 0.0001, 1e9], ids=str)
def test_a_positive_number_of_metres_is_accepted(tmp_path, value):
    path = _datasets_file(tmp_path, "swissalti3d", lambda d: d.update(resolution_m=value))
    assert load_datasets(path)["swissalti3d"]["resolution_m"] == value


@pytest.mark.parametrize(
    "value",
    [0, -1, -0.5, float("nan"), float("inf"), float("-inf"), "0.5", True, False, [0.5], None, {}],
    ids=[
        "zero",
        "-1",
        "-0.5",
        "nan",
        "inf",
        "-inf",
        "string",
        "true",
        "false",
        "list",
        "null",
        "{}",
    ],
)
def test_anything_else_is_refused_naming_the_file_and_the_dataset(tmp_path, value):
    path = _datasets_file(tmp_path, "swissalti3d", lambda d: d.update(resolution_m=value))
    with pytest.raises(DatasetsConfigError) as refused:
        load_datasets(path)
    message = str(refused.value)
    for part in (str(path), "'swissalti3d'", "resolution_m", "positive number of metres"):
        assert part in message, (part, message)


def test_swissbuildings3d_needs_no_resolution(tmp_path):
    path = _datasets_file(tmp_path, "swissbuildings3d", lambda d: d.pop("resolution_m", None))
    assert "resolution_m" not in load_datasets(path)["swissbuildings3d"]
