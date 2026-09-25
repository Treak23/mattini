"""Download failures are visible and leave nothing looking valid (brief M0-04; Hard Rule 2).

Beyond the pinned tests: the one retry, fetch errors, malformed STAC items, unsafe asset
names and a damaged file already on disk. In every failure the error names the tile and the
URL, no `.part` file is left behind and no `provenance.json` is written.
"""

import hashlib
import http.client
import math
import re
from pathlib import Path

import pytest

from mattini.datasets import load_datasets
from mattini.download import DownloadError, download_terrain
from mattini.lock import build_lock
from mattini.world import load_world

TILES = ["2623-1095", "2623-1096", "2623-1097", "2624-1095", "2624-1096", "2624-1097"]
STAC_ITEMS = "https://data.geo.admin.ch/api/stac/v1/collections/ch.swisstopo.swissalti3d/items/"
TILE = "2623-1096"
ITEM_URL = STAC_ITEMS + f"swissalti3d_2024_{TILE}"
NAME = f"swissalti3d_2024_{TILE}_0.5_2056_5728.tif"
FILE_URL = f"https://files.example/{NAME}"


class Server:
    """Fake STAC API and file host; `script` holds per-URL outcomes consumed in order."""

    def __init__(self):
        self.items, self.files, self.script, self.fetches = {}, {}, {}, []
        for tile in TILES:
            item_id = f"swissalti3d_2024_{tile}"
            name = f"{item_id}_0.5_2056_5728.tif"
            body = f"terrain bytes of {tile}".encode()
            self.files[f"https://files.example/{name}"] = body
            self.items[STAC_ITEMS + item_id] = {
                "id": item_id,
                "assets": {
                    name: {
                        "href": f"https://files.example/{name}",
                        "file:checksum": "1220" + hashlib.sha256(body).hexdigest(),
                    }
                },
            }

    def fetch_json(self, url):
        return self.items[url]

    def fetch_file(self, url, dest):
        self.fetches.append(url)
        queue = self.script.get(url)
        outcome = queue.pop(0) if queue else self.files[url]
        if isinstance(outcome, BaseException):
            Path(dest).write_bytes(b"half a file")
            raise outcome
        Path(dest).write_bytes(outcome)


def _lock():
    """The tile lock for what an untouched server publishes at the pinned config (M1-01)."""
    return build_lock(load_world(), load_datasets(), Server().fetch_json, area="village")


def _run(server, out_root, datasets=None):
    return download_terrain(
        load_world(),
        datasets or load_datasets(),
        out_root,
        fetch_json=server.fetch_json,
        fetch_file=server.fetch_file,
        lock=_lock(),
        area="village",
    )


def _out(tmp_path):
    return tmp_path / "swissalti3d" / "2024"


def _assert_nothing_looks_valid(tmp_path):
    out = _out(tmp_path)
    assert not (out / NAME).exists()
    assert not (out / "provenance.json").exists()
    assert sorted(p.name for p in tmp_path.rglob("*.part")) == []


def test_one_corrupt_fetch_is_retried_once(tmp_path):
    server = Server()
    server.script[FILE_URL] = [b"corrupted in transit"]
    entries = _run(server, tmp_path)
    assert server.fetches.count(FILE_URL) == 2
    assert (_out(tmp_path) / NAME).read_bytes() == server.files[FILE_URL]
    assert [e["tile"] for e in entries] == TILES


def test_two_corrupt_fetches_fail_naming_tile_and_url(tmp_path):
    server = Server()
    server.script[FILE_URL] = [b"corrupted", b"corrupted again"]
    with pytest.raises(DownloadError) as caught:
        _run(server, tmp_path)
    message = str(caught.value)
    assert TILE in message and FILE_URL in message and "does not match" in message
    assert server.fetches.count(FILE_URL) == 2  # one retry, no more
    _assert_nothing_looks_valid(tmp_path)


@pytest.mark.parametrize(
    "error",
    [
        ConnectionResetError("connection reset by peer"),
        TimeoutError("timed out"),
        http.client.IncompleteRead(b"half", 100),
    ],
)
def test_a_failed_fetch_is_retried_then_reported(tmp_path, error):
    server = Server()
    server.script[FILE_URL] = [error]
    _run(server, tmp_path)
    assert server.fetches.count(FILE_URL) == 2
    assert (_out(tmp_path) / NAME).read_bytes() == server.files[FILE_URL]

    other = tmp_path / "again"
    server.script[FILE_URL] = [error, error]
    with pytest.raises(DownloadError, match=re.escape(TILE)) as caught:
        _run(server, other)
    assert FILE_URL in str(caught.value) and "fetch failed" in str(caught.value)
    _assert_nothing_looks_valid(other)


def test_an_unexpected_error_propagates_and_leaves_no_part_file(tmp_path):
    server = Server()
    server.script[FILE_URL] = [RuntimeError("a bug in the fetcher")]
    with pytest.raises(RuntimeError, match="a bug in the fetcher"):
        _run(server, tmp_path)
    assert server.fetches.count(FILE_URL) == 1  # only fetch errors are retried
    _assert_nothing_looks_valid(tmp_path)


def test_a_damaged_file_on_disk_is_fetched_again(tmp_path):
    server = Server()
    _run(server, tmp_path)
    (_out(tmp_path) / NAME).write_bytes(b"damaged on disk")
    server.fetches.clear()
    _run(server, tmp_path)
    assert server.fetches == [FILE_URL]
    assert (_out(tmp_path) / NAME).read_bytes() == server.files[FILE_URL]


def test_a_damaged_file_that_cannot_be_refetched_is_removed(tmp_path):
    server = Server()
    _run(server, tmp_path)
    (_out(tmp_path) / NAME).write_bytes(b"damaged on disk")
    (_out(tmp_path) / "provenance.json").unlink()
    server.script[FILE_URL] = [b"corrupted", b"corrupted"]
    with pytest.raises(DownloadError, match=re.escape(TILE)):
        _run(server, tmp_path)
    _assert_nothing_looks_valid(tmp_path)


def _drop_assets(item):
    del item["assets"]


def _two_matches(item):
    (asset,) = item["assets"].values()
    item["assets"]["copy_of_" + NAME] = dict(asset)


def _rename_asset(new_name):
    def mutate(item):
        item["assets"] = {new_name: item["assets"][NAME]}

    return mutate


def _set_asset(key, value):
    def mutate(item):
        item["assets"][NAME][key] = value

    return mutate


@pytest.mark.parametrize(
    ("mutate", "complaint"),
    [
        (lambda item: item.update(id="swissalti3d_2019_2623-1096"), "expected the STAC item"),
        (_drop_assets, "no assets"),
        (_rename_asset(f"swissalti3d_2024_{TILE}_2_2056_5728.tif"), "exactly one asset"),
        (_rename_asset(f"swissalti3d_2024_{TILE}_0.5_2056_5728.xyz.zip"), "exactly one asset"),
        (_two_matches, "exactly one asset"),
        (_rename_asset("../../escape_0.5_2056_5728.tif"), "not a plain file name"),
        (_rename_asset(".hidden_0.5_2056_5728.tif"), "not a plain file name"),
        (_set_asset("href", ""), "no href"),
        (_set_asset("file:checksum", "1340" + "ab" * 64), "SHA-256 multihash"),
        (_set_asset("file:checksum", None), "SHA-256 multihash"),
        (_set_asset("file:checksum", "1220" + "ab" * 32 + "00"), "SHA-256 multihash"),
    ],
)
def test_a_malformed_stac_item_is_refused_before_any_fetch(tmp_path, mutate, complaint):
    server = Server()
    mutate(server.items[ITEM_URL])
    with pytest.raises(DownloadError, match=re.escape(complaint)) as caught:
        _run(server, tmp_path)
    assert TILE in str(caught.value) and ITEM_URL in str(caught.value)
    assert all(TILE not in url for url in server.fetches)
    assert sorted(p.name for p in tmp_path.rglob("escape*")) == []
    _assert_nothing_looks_valid(tmp_path)


@pytest.mark.parametrize(
    "error", [OSError("HTTP Error 404: Not Found"), ValueError("Expecting value: line 1")]
)
def test_an_unreadable_stac_item_is_a_download_error(tmp_path, error):
    server = Server()

    def fetch_json(url):
        if url == ITEM_URL:
            raise error
        return server.items[url]

    with pytest.raises(DownloadError, match="cannot read the STAC item") as caught:
        download_terrain(
            load_world(),
            load_datasets(),
            tmp_path,
            fetch_json,
            server.fetch_file,
            lock=_lock(),
            area="village",
        )
    assert TILE in str(caught.value) and ITEM_URL in str(caught.value)
    _assert_nothing_looks_valid(tmp_path)


@pytest.mark.parametrize("resolution", [0, -0.5, math.inf, math.nan, "0.5", True, None])
def test_a_resolution_that_is_not_a_positive_number_is_refused(tmp_path, resolution):
    datasets = load_datasets()
    datasets["swissalti3d"] = dict(datasets["swissalti3d"], resolution_m=resolution)
    server = Server()
    with pytest.raises(DownloadError, match="resolution_m"):
        _run(server, tmp_path, datasets)
    assert server.fetches == []
