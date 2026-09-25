"""Against the real swisstopo servers: opt-in with `pytest -m network` (briefs M0-04, M1-01).

Excluded from the default run and the gate (pipeline/pyproject.toml). They check the fake
servers' assumptions against the live STAC API: the pinned edition's items exist for all
six village tiles with exactly one GeoTIFF asset at the pinned resolution and a SHA-256
multihash; the committed tile lock equals what swisstopo publishes today (it fails when a
tile was republished); and a real download of the small 2 m files verifies end to end
against a lock written for them.
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
    published = lock.build_lock(
        load_world(), load_datasets(), download.urllib_fetch_json, area="village"
    )
    assert published == lock.load_lock()


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
