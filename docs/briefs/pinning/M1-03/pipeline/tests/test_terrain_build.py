"""Pinning tests for brief M1-03: the terrain step reads only what provenance and the lock vouch for.

Pinned decisions (docs/history/ARCS.md §M0, D7 and D9; docs/SPEC.md §8): the step reads the
tile list only from provenance.json, and refuses a provenance.json whose edition,
resolution or tiles differ from what the config asks for, naming `download terrain`;
stray files in the folder are not read. Every tile's SHA-256 must equal the lock's. Every
tile must lie where its id says (EPSG:2056, 2000 x 2000 pixels of 0.5 m, its 1 km square)
and hold no nodata or non-finite value in the area; each refusal names the tile. The test
world is one tile (2623-1096) at 2 m spacing, so the step runs in about a second.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from mattini.datasets import load_datasets
from mattini.terrain import TerrainError, build_terrain
from mattini.world import load_world

REPO = Path(__file__).resolve().parents[2]
TILE = "2623-1096"
NAME = f"swissalti3d_2024_{TILE}_0.5_2056_5728.tif"
DOWNLOAD_COMMAND = "python -m mattini download terrain"


def _heights():
    rows, cols = np.mgrid[0:2000, 0:2000]
    return (1600.0 + 0.0625 * cols - 0.03125 * rows + 0.5 * ((rows + cols) % 2)).astype(np.float32)


def _write_tile(path, data, west=2623000.0, north=1097000.0, crs="EPSG:2056"):
    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "width": data.shape[1],
        "height": data.shape[0],
        "count": 1,
        "crs": crs,
        "transform": from_origin(west, north, 0.5, 0.5),
        "nodata": -9999.0,
    }
    with rasterio.open(path, "w", **profile) as ds:
        ds.write(data, 1)


@pytest.fixture
def one_tile(tmp_path):
    """A world whose village is tile 2623-1096, its provenance, lock and terrain config."""
    world = json.loads((REPO / "config" / "world.json").read_text(encoding="utf-8"))
    world["areas"]["village"] = {
        "e_min": 2623000.0,
        "e_max": 2624000.0,
        "n_min": 1096000.0,
        "n_max": 1097000.0,
    }
    world_path = tmp_path / "world.json"
    world_path.write_text(json.dumps(world, indent=2), encoding="utf-8")
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
        "tiles": [
            {
                "file": NAME,
                "item": f"swissalti3d_2024_{TILE}",
                "sha256": sha256,
                "size_bytes": (raw_dir / NAME).stat().st_size,
                "tile": TILE,
                "url": f"https://data.geo.admin.ch/ch.swisstopo.swissalti3d/{NAME}",
            }
        ],
    }
    (raw_dir / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
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
    return {
        "world": load_world(world_path),
        "world_sha256": hashlib.sha256(world_path.read_bytes()).hexdigest(),
        "lock": lock,
        "terrain_config": {"schema": 1, "areas": {"village": {"spacing_m": 2.0}}},
        "raw_root": tmp_path / "raw",
        "raw_dir": raw_dir,
        "out": tmp_path / "generated",
    }


def _build(case):
    return build_terrain(
        case["world"],
        load_datasets(),
        case["lock"],
        case["terrain_config"],
        case["raw_root"],
        case["out"],
    )


def _edit_provenance(case, change):
    path = case["raw_dir"] / "provenance.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_one_tile_builds_the_designed_grid(one_tile):
    block = _build(one_tile)
    heights_path = one_tile["out"] / "terrain" / "village.f32"
    assert block["area"] == "village"
    assert (block["columns"], block["rows"], block["spacing_m"]) == (501, 501, 2.0)
    assert block["lv95_box"] == {
        "e_max": 2624000.0,
        "e_min": 2623000.0,
        "n_max": 1097000.0,
        "n_min": 1096000.0,
    }
    assert block["file"] == "terrain/village.f32"
    assert block["format"] == "float32-le"
    assert block["sha256"] == hashlib.sha256(heights_path.read_bytes()).hexdigest()
    assert block["world_sha256"] == one_tile["world_sha256"]
    assert block["source"]["attribution"] == "© swisstopo"
    assert block["source"]["tiles"] == [
        {
            "sha256": one_tile["lock"]["datasets"]["swissalti3d"]["tiles"][TILE]["sha256"],
            "tile": TILE,
        }
    ]
    heights = np.fromfile(heights_path, dtype="<f4").reshape(501, 501)
    source = _heights().astype(np.float64)
    # interior vertex (row 100, column 200): the 4 x 4 pixels around LV95 (e_min + 400, n_max - 200)
    assert heights[100, 200] == np.float32(source[398:402, 798:802].mean())
    # north-west corner: the 2 x 2 pixels inside the area
    assert heights[0, 0] == np.float32(source[0:2, 0:2].mean())
    assert json.loads((one_tile["out"] / "terrain" / "village.json").read_text("utf-8")) == block


def test_a_stray_tif_in_the_folder_is_not_read(one_tile):
    _write_tile(
        one_tile["raw_dir"] / "swissalti3d_2024_2623-1095_0.5_2056_5728.tif",
        np.full((2000, 2000), -9999.0, dtype=np.float32),
        north=1096000.0,
    )
    _build(one_tile)  # the stray tile is all nodata; reading it would refuse


@pytest.mark.parametrize(
    "change",
    [
        lambda p: p.update(edition="2019"),
        lambda p: p.update(resolution_m=2.0),
        lambda p: p["tiles"].clear(),
        lambda p: p["tiles"][0].update(tile="2623-1095"),
    ],
    ids=["edition", "resolution", "no-tiles", "another-tile"],
)
def test_provenance_that_does_not_match_the_config_is_refused(one_tile, change):
    _edit_provenance(one_tile, change)
    with pytest.raises(TerrainError, match=DOWNLOAD_COMMAND):
        _build(one_tile)
    assert not (one_tile["out"] / "terrain" / "village.f32").exists()


def test_missing_provenance_names_the_download(one_tile):
    (one_tile["raw_dir"] / "provenance.json").unlink()
    with pytest.raises(TerrainError, match=DOWNLOAD_COMMAND):
        _build(one_tile)


def test_a_tile_that_differs_from_the_lock_is_refused(one_tile):
    _write_tile(one_tile["raw_dir"] / NAME, _heights() + np.float32(0.25))
    with pytest.raises(TerrainError, match=TILE):
        _build(one_tile)


@pytest.mark.parametrize(
    "tile_kwargs",
    [{"west": 2624000.0}, {"north": 1098000.0}, {"crs": "EPSG:21781"}],
    ids=["a-km-east", "a-km-north", "lv03"],
)
def test_a_tile_that_is_not_where_its_id_says_is_refused(one_tile, tile_kwargs):
    path = one_tile["raw_dir"] / NAME
    _write_tile(path, _heights(), **tile_kwargs)
    _relock(one_tile)
    with pytest.raises(TerrainError, match=TILE):
        _build(one_tile)


@pytest.mark.parametrize("bad", [-9999.0, np.nan])
def test_nodata_in_the_area_is_refused(one_tile, bad):
    data = _heights()
    data[1234, 567] = bad
    _write_tile(one_tile["raw_dir"] / NAME, data)
    _relock(one_tile)
    with pytest.raises(TerrainError, match=TILE):
        _build(one_tile)


def _relock(case):
    """Make provenance and lock vouch for the rewritten tile, so only its content is wrong."""
    path = case["raw_dir"] / NAME
    sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    case["lock"]["datasets"]["swissalti3d"]["tiles"][TILE]["sha256"] = sha256
    _edit_provenance(
        case, lambda p: p["tiles"][0].update(sha256=sha256, size_bytes=path.stat().st_size)
    )


def test_the_output_does_not_depend_on_where_it_is_written(one_tile, tmp_path):
    first = _build(one_tile)
    moved = dict(one_tile, out=tmp_path / "elsewhere")
    assert _build(moved) == first
    for rel in ("terrain/village.f32", "terrain/village.json"):
        assert (one_tile["out"] / rel).read_bytes() == (moved["out"] / rel).read_bytes()
    assert str(tmp_path).encode() not in (moved["out"] / "terrain/village.json").read_bytes()
