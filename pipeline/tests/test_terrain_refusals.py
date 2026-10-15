"""The terrain step's refusals beyond the pinned tests (brief M1-03; Hard Rules 2 and 4).

A rotated world, an area whose north-west corner is off the vertex lattice, a source that
is not 0.5 m, a lock or provenance that disagree, a tile that is not what its id says, and
a manifest whose terrain description no longer fits: each is a TerrainError naming what is
wrong and the command that fixes it, and nothing is written. The test world is one tile
(its id and corner are read from the world config's own origin) at 2 m spacing; since
M2-01 its terrain config expects the SHA-256 an independent reference computes from the
tile's own heights (window_mean.py), and the manifest over the shared fixture reads the
fixture's own tile lock. Since M2-07 the config records the test world and lock as what
its value was computed for (computed_for.py); a test that changes the lock and means to
reach a later check records the change (`_adopt`).
"""

import hashlib
import json
import math
import re
import shutil

import numpy as np
import pytest
import rasterio
from computed_for import recorded
from rasterio.transform import from_origin
from window_mean import expected_sha256

from mattini.datasets import load_datasets
from mattini.manifest import write_manifest
from mattini.terrain import TerrainError, build_terrain, load_terrain_config, resample
from mattini.world import REPO, load_world

WORLD = json.loads((REPO / "config" / "world.json").read_text(encoding="utf-8"))
WEST, SOUTH = WORLD["origin_lv95"]["e"], WORLD["origin_lv95"]["n"]
TILE = f"{math.floor(WEST / 1000)}-{math.floor(SOUTH / 1000)}"
NAME = f"swissalti3d_2024_{TILE}_0.5_2056_5728.tif"
FIXTURE = REPO / "tests" / "shared" / "terrain_fixture"
TERRAIN_COMMAND = "python -m mattini terrain"
DOWNLOAD_COMMAND = "python -m mattini download terrain"
LOCK_COMMAND = "python -m mattini lock terrain"


def _heights():
    rows, cols = np.mgrid[0:2000, 0:2000]
    return (1600.0 + 0.0625 * cols - 0.03125 * rows).astype(np.float32)


# The heights' SHA-256 at 2 m, from the tile's own heights (the area is the whole tile)
HEIGHTS_SHA256 = expected_sha256(_heights(), 2.0)


def _config(world, lock, area="village"):
    """The terrain config, recording `world` and `lock` as what its value was computed for."""
    config = {
        "schema": 1,
        "areas": {area: {"expected_sha256": {"2": HEIGHTS_SHA256}, "spacing_m": 2.0}},
    }
    return recorded(config, world, lock, "swissalti3d")


def _write_tile(path, data, west=WEST, north=SOUTH + 1000.0, size=0.5):
    profile = {
        "driver": "GTiff",
        "dtype": str(data.dtype),
        "width": data.shape[1],
        "height": data.shape[0],
        "count": 1,
        "crs": "EPSG:2056",
        "transform": from_origin(west, north, size, size),
        "nodata": -9999.0,
    }
    with rasterio.open(path, "w", **profile) as ds:
        ds.write(data, 1)


def _world(tmp_path, change=lambda d: None):
    data = json.loads(json.dumps(WORLD))
    data["areas"]["village"] = {
        "e_min": WEST,
        "e_max": WEST + 1000.0,
        "n_min": SOUTH,
        "n_max": SOUTH + 1000.0,
    }
    change(data)
    path = tmp_path / "world.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return load_world(path)


@pytest.fixture
def case(tmp_path):
    raw_dir = tmp_path / "raw" / "swissalti3d" / "2024"
    raw_dir.mkdir(parents=True)
    _write_tile(raw_dir / NAME, _heights())
    sha256 = hashlib.sha256((raw_dir / NAME).read_bytes()).hexdigest()
    provenance = {
        "attribution": "© swisstopo",
        "collection": "ch.swisstopo.swissalti3d",
        "dataset": "swissalti3d",
        "edition": "2024",
        "resolution_m": 0.5,
        "schema": 1,
        "tiles": [{"file": NAME, "sha256": sha256, "tile": TILE}],
    }
    (raw_dir / "provenance.json").write_text(json.dumps(provenance), encoding="utf-8")
    lock = {
        "schema": 1,
        "datasets": {
            "swissalti3d": {
                "collection": "ch.swisstopo.swissalti3d",
                "edition": "2024",
                "resolution_m": 0.5,
                "tiles": {TILE: {"file": NAME, "sha256": sha256}},
            }
        },
    }
    world = _world(tmp_path)
    return {
        "tmp": tmp_path,
        "world": world,
        "datasets": load_datasets(),
        "lock": lock,
        "config": _config(world, lock),
        "raw_dir": raw_dir,
        "out": tmp_path / "generated",
    }


def _adopt(case):
    """Record the case's lock in its terrain config, as design does when it adopts inputs.

    Since M2-07 a lock entry the config was not computed for is refused before any tile is
    read; a test of what comes after that check changes the lock and adopts it.
    """
    case["config"] = recorded(case["config"], case["world"], case["lock"], "swissalti3d")


def _build(case, **changes):
    case = dict(case, **changes)
    return build_terrain(
        case["world"],
        case["datasets"],
        case["lock"],
        case["config"],
        case["tmp"] / "raw",
        case["out"],
    )


def _refused(case, pattern, **changes):
    with pytest.raises(TerrainError, match=pattern) as refused:
        _build(case, **changes)
    assert not case["out"].exists()  # nothing written
    return str(refused.value)


def test_a_rotated_world_is_refused(case, tmp_path):
    rotated = _world(tmp_path, lambda d: d.update(axes={"x": "+n", "y": "+h", "z": "+e"}))
    _refused(case, re.escape("x = +e, y = +h, z = -n"), world=rotated)


def test_an_area_off_the_vertex_lattice_is_refused(case, tmp_path):
    def shift(d):  # still on the 0.5 m source grid and inside the tile, 1 m off the 2 m lattice
        d["areas"]["village"].update(e_min=WEST + 1.0, n_max=SOUTH + 999.0)

    message = _refused(case, "vertex lattice", world=_world(tmp_path, shift))
    assert "village" in message


def test_an_area_the_world_does_not_have_is_refused(case):
    config = _config(case["world"], case["lock"], "backdrop")
    _refused(case, "no area named 'backdrop'", config=config)


def test_a_source_resolution_other_than_half_a_metre_is_refused(case):
    datasets = json.loads(json.dumps(case["datasets"]))
    datasets["swissalti3d"]["resolution_m"] = 2.0
    _refused(case, "resolution_m", datasets=datasets)


@pytest.mark.parametrize(
    ("change", "pattern"),
    [
        (lambda a: a.update(edition="2019"), "edition"),
        (lambda a: a.update(resolution_m=2.0), "resolution_m"),
        (lambda a: a["tiles"].clear(), TILE),
    ],
    ids=["edition", "resolution", "no-tile"],
)
def test_a_lock_for_other_inputs_is_refused_naming_the_lock_command(case, change, pattern):
    change(case["lock"]["datasets"]["swissalti3d"])
    message = _refused(case, pattern)
    assert LOCK_COMMAND in message


def test_provenance_that_differs_from_the_lock_is_refused(case):
    """The lock adopted (design recorded it), the download not run again since."""
    case["lock"]["datasets"]["swissalti3d"]["tiles"][TILE]["sha256"] = "ab" * 32
    _adopt(case)
    message = _refused(case, TILE)
    assert "ab" * 32 in message and DOWNLOAD_COMMAND in message


def test_a_missing_tile_file_is_refused_naming_the_download(case):
    (case["raw_dir"] / NAME).unlink()
    message = _refused(case, TILE)
    assert DOWNLOAD_COMMAND in message


def test_a_provenance_file_name_that_is_not_plain_is_refused(case):
    path = case["raw_dir"] / "provenance.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["tiles"][0]["file"] = "../" + NAME
    path.write_text(json.dumps(data), encoding="utf-8")
    _refused(case, DOWNLOAD_COMMAND)


@pytest.mark.parametrize(
    "tile",
    [
        {"size": 1.0, "data": np.zeros((1000, 1000), dtype=np.float32)},
        {"data": np.zeros((2000, 2000), dtype=np.float64)},
        {"data": np.zeros((1999, 2000), dtype=np.float32)},
    ],
    ids=["1m-pixels", "float64", "short"],
)
def test_a_tile_of_another_shape_is_refused(case, tile):
    data = tile.pop("data")
    path = case["raw_dir"] / NAME
    _write_tile(path, data, **tile)
    sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    case["lock"]["datasets"]["swissalti3d"]["tiles"][TILE]["sha256"] = sha256
    provenance = case["raw_dir"] / "provenance.json"
    data = json.loads(provenance.read_text(encoding="utf-8"))
    data["tiles"][0]["sha256"] = sha256
    provenance.write_text(json.dumps(data), encoding="utf-8")
    _adopt(case)
    _refused(case, TILE)


def test_a_mosaic_that_is_not_32_bit_is_refused():
    box = (WEST, WEST + 2.0, SOUTH, SOUTH + 2.0)
    with pytest.raises(TerrainError, match="32-bit"):
        resample(np.zeros((4, 4), dtype=np.float64), box, 1.0, 0.0)


def test_the_terrain_step_writes_the_same_bytes_twice(case, tmp_path):
    first = _build(case)
    before = {p.name: p.read_bytes() for p in (case["out"] / "terrain").iterdir()}
    assert _build(case) == first
    assert {p.name: p.read_bytes() for p in (case["out"] / "terrain").iterdir()} == before
    assert sorted(before) == ["village.f32", "village.json"]  # no .part left behind


# The manifest's checks of a built terrain, beyond the pinned ones.


def _fixture_out(tmp_path):
    out = tmp_path / "generated"
    shutil.copytree(FIXTURE / "generated" / "terrain", out / "terrain")
    return out


def _manifest(out, datasets=FIXTURE / "datasets.json"):
    return write_manifest(
        out,
        FIXTURE / "world.json",
        terrain_config_path=FIXTURE / "terrain.json",
        datasets_path=datasets,
        lock_path=FIXTURE / "datasets.lock.json",
    )


def _edit_block(out, change):
    path = out / "terrain" / "fixture.json"
    block = json.loads(path.read_text(encoding="utf-8"))
    change(block)
    path.write_text(json.dumps(block), encoding="utf-8")


@pytest.mark.parametrize(
    "change",
    [
        lambda b: b.update(file="../terrain/fixture.f32"),
        lambda b: b.update(area="village"),
        lambda b: b.update(format="float64-le"),
        lambda b: b.pop("lv95_box"),
        lambda b: b.update(rows=b["rows"] + 1),
        lambda b: b.update(sha256="00" * 32),
    ],
    ids=["file-elsewhere", "another-area", "format", "a-key-missing", "rows", "sha256"],
)
def test_a_description_that_does_not_fit_is_refused(tmp_path, change):
    out = _fixture_out(tmp_path)
    _edit_block(out, change)
    with pytest.raises(TerrainError, match=TERRAIN_COMMAND):
        _manifest(out)
    assert not (out / "manifest.json").exists()


def test_a_description_that_is_not_json_is_refused(tmp_path):
    out = _fixture_out(tmp_path)
    (out / "terrain" / "fixture.json").write_text("{", encoding="utf-8")
    with pytest.raises(TerrainError, match=TERRAIN_COMMAND):
        _manifest(out)


def test_a_datasets_config_with_another_resolution_is_refused_naming_the_lock(tmp_path):
    """The lock no longer fits the datasets config (M3-01): `lock terrain` is the command
    that helps. The block's own resolution is edited in test_terrain_manifest_source.py."""
    datasets = json.loads((FIXTURE / "datasets.json").read_text(encoding="utf-8"))
    datasets["datasets"]["swissalti3d"]["resolution_m"] = 2.0
    path = tmp_path / "datasets.json"
    path.write_text(json.dumps(datasets), encoding="utf-8")
    with pytest.raises(TerrainError, match=LOCK_COMMAND):
        _manifest(_fixture_out(tmp_path), datasets=path)


def test_a_heights_file_without_its_description_is_no_terrain(tmp_path):
    out = _fixture_out(tmp_path)
    (out / "terrain" / "fixture.json").unlink()
    assert json.loads(_manifest(out).read_bytes())["terrain"] is None


@pytest.mark.parametrize("name", ["../village", "Village", "village.f32", ""])
def test_an_area_name_that_is_not_a_plain_file_name_is_refused(tmp_path, name):
    path = tmp_path / "terrain.json"
    area = {"expected_sha256": {"0.5": "0" * 64}, "spacing_m": 0.5}
    path.write_text(json.dumps({"schema": 1, "areas": {name: area}}), "utf-8")
    with pytest.raises(TerrainError, match=re.escape(str(path))) as refused:
        load_terrain_config(path)
    assert "area name" in str(refused.value)
