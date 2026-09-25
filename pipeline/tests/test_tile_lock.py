"""Pinning tests for brief M1-01: the tile checksum lock (D7; docs/SPEC.md §5).

Pinned decisions: the repository pins the SHA-256 of every tile the pipeline uses in
`config/datasets.lock.json`, written only by `python -m mattini lock terrain` from the
checksums swisstopo publishes, and committed. `download terrain` refuses a published
checksum that differs from the lock, naming the tile, both values and the command that
adopts the new tile, and fetches nothing for it: adopting a republished tile is a
deliberate change like a new edition (Hard Rule 5). A lock for another edition,
resolution or tile list is refused too. The committed lock holds the six 2024 tiles
measured by brief M0-04 and re-read from the live STAC items at M1 planning.
"""

import hashlib
import json
import re

import pytest
from fake_swisstopo import VILLAGE_TILES, FakeSwisstopo

from mattini.datasets import load_datasets
from mattini.download import DownloadError, download_terrain
from mattini.lock import LOCK_PATH, LockError, build_lock, load_lock, write_lock
from mattini.world import REPO, load_world

MEASURED = {  # tile: (file, SHA-256); M0-04 Findings 4, re-read 2026-09-25
    "2623-1095": "a6ea488ecbb54b97100f22d867c38b8cd1efc37b68d61f175c98e53fb2c810ca",
    "2623-1096": "0e251928c93b53107618d576cf11a52299352d08532f50e3f764c635e72cc581",
    "2623-1097": "294bb2c6420f191dbf15d5104d130d982117528ce3fe3b271548a1e008d6ac24",
    "2624-1095": "57f12bcf71d823f32a3186667f8d7dbbfac80e2335454fd4d505dd17ce6e08aa",
    "2624-1096": "cdc98b65fccf96f1eeb2ba65009bf12cd41716d8bd2ba18260f4a072a8921f59",
    "2624-1097": "b6a322f4039431ba0805a4a4a19ae2b2603a2a0d0701a4cb280bb42ec09e032e",
}


def _lock_for(fake):
    return build_lock(load_world(), load_datasets(), fake.fetch_json)


def _download(fake, out_root, lock):
    return download_terrain(
        load_world(),
        load_datasets(),
        out_root,
        fetch_json=fake.fetch_json,
        fetch_file=fake.fetch_file,
        lock=lock,
    )


def test_the_committed_lock_pins_the_six_measured_tiles():
    assert LOCK_PATH == REPO / "config" / "datasets.lock.json"
    alti = load_lock()["datasets"]["swissalti3d"]
    assert alti["collection"] == "ch.swisstopo.swissalti3d"
    assert alti["edition"] == "2024"
    assert alti["resolution_m"] == 0.5
    assert sorted(alti["tiles"]) == VILLAGE_TILES
    for tile, sha256 in MEASURED.items():
        entry = alti["tiles"][tile]
        assert entry == {
            "file": f"swissalti3d_2024_{tile}_0.5_2056_5728.tif",
            "sha256": sha256,
        }


def test_build_lock_records_the_published_checksums():
    fake = FakeSwisstopo()
    lock = _lock_for(fake)
    assert lock == {
        "schema": 1,
        "datasets": {
            "swissalti3d": {
                "collection": "ch.swisstopo.swissalti3d",
                "edition": "2024",
                "resolution_m": 0.5,
                "tiles": {
                    tile: {
                        "file": f"swissalti3d_2024_{tile}_0.5_2056_5728.tif",
                        "sha256": fake.sha256(tile),
                    }
                    for tile in VILLAGE_TILES
                },
            }
        },
    }
    assert fake.file_fetches == []  # locking reads the STAC items only


def test_write_lock_is_deterministic_json(tmp_path):
    lock = _lock_for(FakeSwisstopo())
    first = write_lock(lock, tmp_path / "a.json").read_bytes()
    second = write_lock(lock, tmp_path / "b.json").read_bytes()
    assert first == second
    assert first == (json.dumps(lock, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()
    assert load_lock(tmp_path / "a.json") == lock
    assert hashlib.sha256(first).hexdigest() == (
        "392a322165554433dbf4e57682d7f841ee4077512075d378aa70d9acc8a5949f"
    )


def test_a_republished_tile_is_refused_and_not_fetched(tmp_path):
    fake = FakeSwisstopo()
    lock = _lock_for(fake)
    fake.republish("2624-1096")
    published = hashlib.sha256(b"republished terrain bytes for 2624-1096").hexdigest()
    with pytest.raises(DownloadError) as refused:
        _download(fake, tmp_path, lock)
    message = str(refused.value)
    assert "2624-1096" in message
    assert fake.sha256("2624-1096") in message and published in message
    assert "python -m mattini lock terrain" in message
    assert not any("2624-1096" in url for url in fake.file_fetches)


def test_a_lock_for_another_edition_resolution_or_tile_list_is_refused(tmp_path):
    fake = FakeSwisstopo()
    for why, change in {
        "edition": lambda alti: alti.update(edition="2019"),
        "resolution": lambda alti: alti.update(resolution_m=2.0),
        "a missing tile": lambda alti: alti["tiles"].pop("2623-1097"),
    }.items():
        lock = _lock_for(fake)
        change(lock["datasets"]["swissalti3d"])
        with pytest.raises(DownloadError, match="lock"):
            _download(fake, tmp_path / why, lock)


def test_the_lock_is_checked_before_any_file_is_fetched(tmp_path):
    fake = FakeSwisstopo()
    lock = _lock_for(fake)
    fake.republish("2624-1097")  # the last tile in order
    with pytest.raises(DownloadError, match="2624-1097"):
        _download(fake, tmp_path, lock)
    assert fake.file_fetches == []


@pytest.mark.parametrize(
    "text",
    [
        "not json",
        '{"schema": 2, "datasets": {}}',
        '{"schema": 1}',
        (
            '{"schema": 1, "datasets": {"swissalti3d": {"collection": "ch.swisstopo.swissalti3d",'
            ' "edition": "2024", "resolution_m": 0.5, "tiles": {"2623-1095": {"file": "x.tif",'
            ' "sha256": "abc"}}}}}'
        ),
    ],
    ids=["not-json", "unknown-schema", "no-datasets", "short-sha256"],
)
def test_a_malformed_lock_is_refused_with_the_file_named(tmp_path, text):
    path = tmp_path / "datasets.lock.json"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(LockError, match=re.escape(str(path))):
        load_lock(path)
