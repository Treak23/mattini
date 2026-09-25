"""One home for the area the pipeline serves (brief M2-01; M1 R1 T-06).

`lock terrain`, `download terrain` and `terrain` all serve the one area config/terrain.json
names; `download.area_tiles(world, area)` lists its tiles and the download's refusals name
it. The review's proof, turned round: a world with a second area, `valley`, one tile east
of the village, and a terrain config naming `valley`. Before M2-01 the download fetched
the village and `terrain` refused, pointing at the download, in a loop. Here the three
commands run in order on the command line against a fake swisstopo serving a synthetic
GeoTIFF for the valley's tile, and the manifest ends up holding the valley's terrain.

Does NOT prove: anything about M5's larger area (not designed yet); a real download.
"""

import json

import numpy as np
import pytest
import rasterio
from fake_swisstopo import VILLAGE_TILES, FakeSwisstopo
from rasterio.transform import from_origin
from window_mean import expected_sha256

import mattini.__main__ as cli
from mattini import download, lock, manifest, terrain
from mattini.datasets import load_datasets
from mattini.world import REPO, load_world

VALLEY_TILE = "2625-1096"
VALLEY = {"e_min": 2625000.0, "e_max": 2626000.0, "n_min": 1096000.0, "n_max": 1097000.0}
LOCK_COMMAND = "python -m mattini lock terrain"


def _heights():
    rows, cols = np.mgrid[0:2000, 0:2000]
    return (1700.0 + 0.0625 * cols - 0.03125 * rows).astype(np.float32)


def _geotiff(path) -> bytes:
    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "width": 2000,
        "height": 2000,
        "count": 1,
        "crs": "EPSG:2056",
        "transform": from_origin(VALLEY["e_min"], VALLEY["n_max"], 0.5, 0.5),
        "nodata": -9999.0,
    }
    with rasterio.open(path, "w", **profile) as ds:
        ds.write(_heights(), 1)
    return path.read_bytes()


@pytest.fixture
def valley(tmp_path, monkeypatch):
    """A world with the village and the valley, a terrain config naming the valley, a fake
    swisstopo publishing all seven tiles (the valley's as a real GeoTIFF), and the command
    line wired to them."""
    world = json.loads((REPO / "config" / "world.json").read_text(encoding="utf-8"))
    world["areas"]["valley"] = dict(VALLEY)
    world_path = tmp_path / "world.json"
    world_path.write_text(json.dumps(world, indent=2), encoding="utf-8")
    config = {
        "schema": 1,
        "areas": {
            "valley": {"expected_sha256": {"2": expected_sha256(_heights(), 2.0)}, "spacing_m": 2.0}
        },
    }
    config_path = tmp_path / "terrain.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    lock_path = tmp_path / "datasets.lock.json"

    fake = FakeSwisstopo(tiles=VILLAGE_TILES + [VALLEY_TILE])
    fake._publish(VALLEY_TILE, _geotiff(tmp_path / "valley.tif"))
    load_terrain_config = terrain.load_terrain_config
    monkeypatch.setattr(download, "urllib_fetch_json", fake.fetch_json)
    monkeypatch.setattr(download, "urllib_fetch_file", fake.fetch_file)
    monkeypatch.setattr(lock, "LOCK_PATH", lock_path)
    monkeypatch.setattr(cli, "load_world", lambda: load_world(world_path))
    monkeypatch.setattr(terrain, "load_terrain_config", lambda: load_terrain_config(config_path))
    monkeypatch.setattr(
        cli,
        "write_manifest",
        lambda out: manifest.write_manifest(
            out, world_path, terrain_config_path=config_path, lock_path=lock_path
        ),
    )
    return {"tmp": tmp_path, "fake": fake, "lock_path": lock_path, "world_path": world_path}


def test_area_tiles_lists_the_named_area_s_tiles(valley):
    world = load_world(valley["world_path"])
    assert download.area_tiles(world, "valley") == [VALLEY_TILE]
    assert download.area_tiles(world, "village") == VILLAGE_TILES


def test_lock_download_and_terrain_serve_the_configured_area(valley, capsys):
    raw, out = valley["tmp"] / "raw", valley["tmp"] / "generated"
    assert cli.main(["lock", "terrain"]) == 0
    locked = lock.load_lock(valley["lock_path"])["datasets"]["swissalti3d"]["tiles"]
    assert list(locked) == [VALLEY_TILE]

    assert cli.main(["download", "terrain", "--out", str(raw)]) == 0
    assert [url.rsplit("/", 1)[1] for url in valley["fake"].file_fetches] == [
        f"swissalti3d_2024_{VALLEY_TILE}_0.5_2056_5728.tif"
    ]
    provenance = json.loads((raw / "swissalti3d" / "2024" / "provenance.json").read_bytes())
    assert [entry["tile"] for entry in provenance["tiles"]] == [VALLEY_TILE]

    assert cli.main(["terrain", "--raw", str(raw), "--out", str(out)]) == 0
    capsys.readouterr()
    block = json.loads((out / "manifest.json").read_bytes())["terrain"]
    assert block["area"] == "valley" and block["file"] == "terrain/valley.f32"
    assert block["source"]["tiles"] == [
        {"sha256": locked[VALLEY_TILE]["sha256"], "tile": VALLEY_TILE}
    ]


def test_a_lock_for_another_area_is_refused_naming_the_area(valley, capsys):
    village = FakeSwisstopo()
    pinned = lock.build_lock(load_world(), load_datasets(), village.fetch_json, area="village")
    lock.write_lock(pinned, valley["lock_path"])
    assert cli.main(["download", "terrain", "--out", str(valley["tmp"] / "raw")]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "'valley'" in captured.err and VALLEY_TILE in captured.err
    assert f"`{LOCK_COMMAND}`" in captured.err
    assert valley["fake"].file_fetches == []


@pytest.mark.parametrize("broken", ["stac-item", "file"])
def test_a_tile_refusal_names_the_tile_and_the_area(valley, capsys, broken):
    assert cli.main(["lock", "terrain"]) == 0
    fake, item_id = valley["fake"], f"swissalti3d_2024_{VALLEY_TILE}"
    if broken == "stac-item":  # an item that is not the one asked for
        fake.items[next(url for url in fake.items if url.endswith(item_id))] = {"id": "other"}
    else:
        fake.broken_files.add(next(url for url in fake.files if f"{item_id}_0.5_" in url))
    assert cli.main(["download", "terrain", "--out", str(valley["tmp"] / "raw")]) == 1
    captured = capsys.readouterr()
    assert f"mattini: error: tile {VALLEY_TILE} of area 'valley': " in captured.err


def test_the_pipeline_code_names_no_area():
    """Text only (lesson 5): no area name is written into pipeline/mattini/ (M2-01).

    The behaviour is the command-line test above; this census keeps the next area-specific
    shortcut from coming back as a default.
    """
    offenders = [
        f"{path.relative_to(REPO)}:{number}"
        for path in sorted((REPO / "pipeline" / "mattini").rglob("*.py"))
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if "village" in line.lower()
    ]
    assert offenders == []
