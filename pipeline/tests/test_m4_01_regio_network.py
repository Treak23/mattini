"""Pinning test for brief M4-01, opt-in (`pytest -m network`): swisstopo still publishes the lock.

Reads the live STAC item of every tile the committed lock pins for swissALTIRegio and asks
the file host for one of them (HEAD): the published name and SHA-256 must be the lock's,
the item's datetime in the pinned edition, and the file host's `x-amz-meta-sha256` the lock's.
Measured on 2026-10-17 by M4-01's design rehearsal.

Does NOT prove: anything when it is not run (the standard gate deselects it).
"""

import json

import pytest

from mattini import download
from mattini.lock import load_lock
from mattini.world import REPO

pytestmark = pytest.mark.network


def test_the_live_items_publish_what_the_lock_pins():
    entry = load_lock()["datasets"]["swissaltiregio"]
    edition = json.loads((REPO / "config" / "datasets.json").read_text(encoding="utf-8"))[
        "datasets"
    ]["swissaltiregio"]["edition"]
    href = None
    for tile, pinned in entry["tiles"].items():
        item_id = f"swissaltiregio_{tile}"
        item = download.urllib_fetch_json(
            download.STAC_ITEM.format(collection=entry["collection"], item_id=item_id)
        )
        assert item["id"] == item_id
        assert item["properties"]["datetime"].startswith(edition + "-"), tile
        (name,) = [key for key in item["assets"] if key.endswith("_2056_5728.xyz.zip")]
        checksum = item["assets"][name]["file:checksum"]
        assert (name, download.parse_multihash_sha256(checksum)) == (
            pinned["file"],
            pinned["sha256"],
        ), tile
        href = item["assets"][name]["href"]
    size, host_sha256 = download.urllib_head(href)
    assert size > 1_000_000 and host_sha256.lower() == pinned["sha256"]
