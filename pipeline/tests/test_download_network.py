"""Against the real swisstopo servers: opt-in with `pytest -m network` (M0-04, M1-01, M2-03, M3-03).

Excluded from the default run and the gate (pipeline/pyproject.toml). They check the fake
servers' assumptions against the live STAC API: the pinned edition's items exist for all
six village tiles with exactly one GeoTIFF asset at the pinned resolution and a SHA-256
multihash; each of the five entries of the committed lock, the terrain's, the buildings',
the photo's, the surface model's and the TLM's, equals what swisstopo publishes today (it
fails when a tile, a sheet or the TLM was republished); the six village sheets' items hold
one `.gdb.zip` asset each; the file host answers a HEAD for the TLM with the lock's size
class and checksum; and a real download of the small 2 m files verifies end to end against
a lock written for them. The TLM file itself (2.88 GB) is not fetched here: the builder's
live run of `download tlm` is brief M3-03's gate.
"""

import pytest

from mattini import download, lock
from mattini.datasets import load_datasets
from mattini.world import load_world

pytestmark = pytest.mark.network


def test_pinned_items_publish_one_asset_with_a_sha256_each():
    alti = load_datasets()["swissalti3d"]
    suffix = f"_{download._resolution_tag(alti['resolution_m'])}_2056_5728.tif"
    for tile in download.area_tiles(load_world(), "village"):
        item_id = f"swissalti3d_{alti['edition']}_{tile}"
        url = download.STAC_ITEM.format(collection=alti["collection"], item_id=item_id)
        name, href, sha256 = download._published_asset(
            download.urllib_fetch_json, url, item_id, tile, "village", suffix
        )
        assert name == f"{item_id}{suffix}"
        assert href.startswith("https://data.geo.admin.ch/") and href.endswith(name)
        assert len(sha256) == 64


def test_the_committed_lock_is_what_swisstopo_publishes():
    world, datasets, fetch = load_world(), load_datasets(), download.urllib_fetch_json
    committed = lock.load_lock()["datasets"]
    assert set(committed) == {
        "swissalti3d",
        "swissbuildings3d",
        "swissimage",
        "swisssurface3d",
        "swisstlm3d",
    }
    assert committed["swissalti3d"] == lock.terrain_entry(world, datasets, fetch, area="village")
    assert committed["swissbuildings3d"] == lock.buildings_entry(
        world, datasets, fetch, area="village"
    )
    assert committed["swissimage"] == lock.photo_entry(world, datasets, fetch, area="village")
    assert committed["swisssurface3d"] == lock.surface_entry(world, datasets, fetch, area="village")
    assert committed["swisstlm3d"] == lock.tlm_entry(datasets, fetch)


def test_the_file_host_agrees_with_the_lock_about_the_tlm():
    """A HEAD, no body: the host's checksum header is the lock's (case aside) and the file has
    a size (brief M3-03, decision 6). The host sends no Accept-Ranges but answers Range."""
    entry = lock.load_lock()["datasets"]["swisstlm3d"]
    published = download.published_tlm(load_datasets(), download.urllib_fetch_json)
    assert published.name == entry["file"]
    size, host_sha256 = download.urllib_head(published.href)
    assert size is not None and size > 2_000_000_000
    assert host_sha256 is None or host_sha256.lower() == entry["sha256"]


def test_the_village_sheets_publish_one_gdb_zip_each():
    sheets = download.published_sheets(
        load_world(), load_datasets(), download.urllib_fetch_json, area="village"
    )
    assert [s.sheet for s in sheets] == download.area_sheets(load_world(), "village")
    for sheet in sheets:
        assert sheet.name == f"{sheet.item_id}_2056_5728.gdb.zip"
        assert sheet.href.startswith("https://data.geo.admin.ch/") and sheet.href.endswith(
            sheet.name
        )


def test_a_real_download_of_the_2m_tiles_verifies(tmp_path):
    datasets = load_datasets()
    datasets["swissalti3d"] = dict(datasets["swissalti3d"], resolution_m=2.0)
    entries = download.download_terrain(
        load_world(),
        datasets,
        tmp_path,
        download.urllib_fetch_json,
        download.urllib_fetch_file,
        lock=lock.build_lock(load_world(), datasets, download.urllib_fetch_json, area="village"),
        area="village",
    )
    assert [e["file"].endswith("_2_2056_5728.tif") for e in entries] == [True] * 6
    assert all(e["size_bytes"] > 0 for e in entries)
