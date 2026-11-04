"""Pinning test for brief v0.6.0-05, opt-in (`pytest -m network`): swisstopo still publishes the lock.

Reads the live STAC item of a sample of the cells the committed lock records for the far photo
(every 37th of the 1806 in order, so pinned and absent cells both, and the first and the last
pinned tile) and asks the file host for one file (HEAD): a pinned cell's item must exist with
its datetime in the pinned edition and the 2 m asset's name and SHA-256 the lock's; an absent
cell's item must answer 404; the file host's `x-amz-meta-sha256` must be the lock's. The whole
1806 are read by `lock farphoto` and by every `download farphoto` (about 75 s and 30 s).

Does NOT prove: anything when it is not run (the standard gate deselects it); the cells it
does not read.
"""

import json
import urllib.error

import pytest

from mattini import download
from mattini.lock import load_lock
from mattini.world import REPO

pytestmark = pytest.mark.network


def test_a_sample_of_the_live_items_publishes_what_the_lock_records():
    entry = load_lock()["datasets"]["swissimage_far"]
    edition = json.loads((REPO / "config" / "datasets.json").read_text(encoding="utf-8"))[
        "datasets"
    ]["swissimage_far"]["edition"]
    cells = sorted([*entry["tiles"], *entry["absent"]])
    sample = sorted({*cells[::37], next(iter(entry["tiles"])), list(entry["tiles"])[-1]})
    href = sha = None
    for cell in sample:
        item_id = f"swissimage-dop10_{edition}_{cell}"
        url = download.STAC_ITEM.format(collection=entry["collection"], item_id=item_id)
        if cell in entry["absent"]:
            with pytest.raises(urllib.error.HTTPError) as answer:
                download.urllib_fetch_json(url)
            assert answer.value.code == 404, cell
            continue
        item = download.urllib_fetch_json(url)
        assert item["id"] == item_id
        assert item["properties"]["datetime"].startswith(edition + "-"), cell
        (name,) = [key for key in item["assets"] if key.endswith("_2_2056.tif")]
        checksum = item["assets"][name]["file:checksum"]
        pinned = entry["tiles"][cell]
        assert (name, download.parse_multihash_sha256(checksum)) == (
            pinned["file"],
            pinned["sha256"],
        ), cell
        href, sha = item["assets"][name]["href"], pinned["sha256"]
    size, host_sha256 = download.urllib_head(href)
    assert size > 50_000 and host_sha256.lower() == sha
