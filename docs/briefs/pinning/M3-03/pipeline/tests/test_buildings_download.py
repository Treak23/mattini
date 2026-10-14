"""Pinning tests for brief M2-03: the buildings' lock entry and download.

Pinned decisions (docs/SPEC.md §5, §8 the buildings; brief M2-03): the lock holds one
entry per dataset; `swissbuildings3d` is exactly {collection, edition, sheets}, each
sheet {file, sha256}, written from the STAC items only, and writing it keeps every other
entry. `download buildings` compares every published file name and SHA-256 with the lock
before anything on disk changes; a file downloads to `.part`, is verified, then renamed,
with one retry; a file already there and matching is not fetched again; `provenance.json`
is removed before the first change and written at the end, deterministic. Errors name the
sheet. Nothing reaches the network here: a fake STAC API serves six sheets.

Does NOT prove: that the live STAC API still serves these items (the network test and
the builder's real run do); anything about the zips' contents (M2-04).
"""

import hashlib
import json

import pytest

from mattini.datasets import load_datasets
from mattini.download import DownloadError, download_buildings
from mattini.lock import LockError, buildings_entry, load_lock, validate_lock, with_entry
from mattini.world import load_world

STAC = "https://data.geo.admin.ch/api/stac/v1/collections/ch.swisstopo.swissbuildings3d_3_0/items/"
SHEETS = ["1328-33", "1328-34", "1348-11", "1348-12", "1348-13", "1348-14"]


class FakeBuildingsStac:
    """One item per sheet, holding a DWG and a GDB zip; the GDB zip is the one to fetch."""

    def __init__(self, edition="2020", sheets=SHEETS):
        self.items, self.files = {}, {}
        self.json_fetches, self.file_fetches = [], []
        for sheet in sheets:
            self.publish(sheet, f"synthetic gdb zip for {sheet}".encode(), edition)

    def publish(self, sheet, body, edition="2020"):
        item_id = f"swissbuildings3d_3_0_{edition}_{sheet}"
        gdb = f"{item_id}_2056_5728.gdb.zip"
        dwg = f"{item_id}_2056_5728.dwg.zip"
        self.files[f"https://files.example/{gdb}"] = body
        self.files[f"https://files.example/{dwg}"] = b"the dwg must not be fetched"
        self.items[STAC + item_id] = {
            "id": item_id,
            "assets": {
                dwg: {
                    "href": f"https://files.example/{dwg}",
                    "file:checksum": "1220" + "11" * 32,
                },
                gdb: {
                    "href": f"https://files.example/{gdb}",
                    "file:checksum": "1220" + hashlib.sha256(body).hexdigest().upper(),
                },
            },
        }

    def sha256(self, sheet):
        return hashlib.sha256(f"synthetic gdb zip for {sheet}".encode()).hexdigest()

    def fetch_json(self, url):
        self.json_fetches.append(url)
        if url not in self.items:
            raise OSError(f"HTTP Error 404: Not Found: {url}")
        return self.items[url]

    def fetch_file(self, url, dest):
        self.file_fetches.append(url)
        dest.write_bytes(self.files[url])


def _entry(fake):
    return buildings_entry(load_world(), load_datasets(), fake.fetch_json, area="village")


def _lock(fake):
    return with_entry(load_lock(), "swissbuildings3d", _entry(fake))


def _download(fake, out_root, lock):
    return download_buildings(
        load_world(),
        load_datasets(),
        out_root,
        fake.fetch_json,
        fake.fetch_file,
        lock=lock,
        area="village",
    )


MEASURED = {  # sheet: SHA-256 of the 2020 GDB zip, read from STAC and the files, 2026-09-25
    "1328-33": "72b2502856d315b9f265f8279a9491cfa3f45065a42cc492824fd9731d7c4292",
    "1328-34": "0af21388ab8e665665ed61218fce7d9a276d260319ab77661ab652d039f5d4a9",
    "1348-11": "14d4aea6a24ab8ae5fd9f287f07ffbac93a28bcab342f06a3e1a841aa5233ab4",
    "1348-12": "d7fd32c439a633bae9d87cd94c1b793cdd64152be529344c5220b49fd50250b0",
    "1348-13": "d886a6baa4697631e49fd2281a3f011bbe034b01ea79708c9d46b9dca9730a16",
    "1348-14": "32c47a7da978832ba56c3e2709d692bf96dc1e386016c80dfda09f9f093db1e2",
}


def test_the_committed_lock_pins_the_six_measured_sheets():
    entry = load_lock()["datasets"]["swissbuildings3d"]
    assert entry == {
        "collection": "ch.swisstopo.swissbuildings3d_3_0",
        "edition": "2020",
        "sheets": {
            sheet: {"file": f"swissbuildings3d_3_0_2020_{sheet}_2056_5728.gdb.zip", "sha256": sha}
            for sheet, sha in MEASURED.items()
        },
    }


def test_the_entry_holds_the_six_sheets_published_checksums():
    fake = FakeBuildingsStac()
    assert _entry(fake) == {
        "collection": "ch.swisstopo.swissbuildings3d_3_0",
        "edition": "2020",
        "sheets": {
            sheet: {
                "file": f"swissbuildings3d_3_0_2020_{sheet}_2056_5728.gdb.zip",
                "sha256": fake.sha256(sheet),
            }
            for sheet in SHEETS
        },
    }
    assert fake.file_fetches == []  # the lock reads STAC only


def test_writing_one_entry_keeps_the_others():
    fake = FakeBuildingsStac()
    before = load_lock()
    lock = _lock(fake)
    assert set(lock["datasets"]) == set(before["datasets"]) | {"swissbuildings3d"}
    for name in set(before["datasets"]) - {"swissbuildings3d"}:  # M3-03: five datasets now
        assert lock["datasets"][name] == before["datasets"][name], name
    validate_lock(lock, "test")
    assert with_entry(None, "swissbuildings3d", _entry(fake)) == {
        "schema": 1,
        "datasets": {"swissbuildings3d": _entry(fake)},
    }


@pytest.mark.parametrize(
    "change",
    [
        lambda e: e.update(resolution_m=0.5),
        lambda e: e.update(tiles=e.pop("sheets")),
        lambda e: e["sheets"].update({"1348-5": {"file": "x.gdb.zip", "sha256": "0" * 64}}),
        lambda e: e["sheets"]["1348-11"].update(sha256="A" * 64),
    ],
    ids=["extra-key", "tiles-not-sheets", "bad-sheet-id", "upper-case-sha"],
)
def test_a_malformed_buildings_entry_is_refused(change):
    lock = _lock(FakeBuildingsStac())
    change(lock["datasets"]["swissbuildings3d"])
    with pytest.raises(LockError):
        validate_lock(lock, "test")


def test_download_fetches_verifies_and_records(tmp_path):
    fake = FakeBuildingsStac()
    entries = _download(fake, tmp_path, _lock(fake))
    folder = tmp_path / "swissbuildings3d" / "2020"
    assert [e["sheet"] for e in entries] == SHEETS
    assert len(fake.file_fetches) == 6
    assert not any(url.endswith(".dwg.zip") for url in fake.file_fetches)
    for sheet in SHEETS:
        name = f"swissbuildings3d_3_0_2020_{sheet}_2056_5728.gdb.zip"
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == fake.sha256(sheet)
    assert not list(folder.glob("*.part"))
    provenance = (folder / "provenance.json").read_bytes()
    assert provenance.endswith(b"\n") and b"\r" not in provenance
    data = json.loads(provenance)
    assert data == {
        "attribution": "© swisstopo",
        "collection": "ch.swisstopo.swissbuildings3d_3_0",
        "dataset": "swissbuildings3d",
        "edition": "2020",
        "schema": 1,
        "sheets": entries,
    }
    for entry in entries:
        assert set(entry) == {"file", "item", "sha256", "sheet", "size_bytes", "url"}
    assert (
        provenance
        == (json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()
    )


def test_a_second_run_fetches_nothing_and_writes_the_same_provenance(tmp_path):
    fake = FakeBuildingsStac()
    lock = _lock(fake)
    _download(fake, tmp_path, lock)
    first = (tmp_path / "swissbuildings3d" / "2020" / "provenance.json").read_bytes()
    fake.file_fetches.clear()
    _download(fake, tmp_path, lock)
    assert fake.file_fetches == []
    assert (tmp_path / "swissbuildings3d" / "2020" / "provenance.json").read_bytes() == first


def test_a_republished_sheet_is_refused_before_anything_changes(tmp_path):
    fake = FakeBuildingsStac()
    lock = _lock(fake)
    _download(fake, tmp_path, lock)
    folder = tmp_path / "swissbuildings3d" / "2020"
    before = {p.name: p.read_bytes() for p in folder.iterdir()}
    fake.publish("1348-12", b"republished")
    fake.file_fetches.clear()
    with pytest.raises(DownloadError, match="1348-12"):
        _download(fake, tmp_path, lock)
    assert fake.file_fetches == []
    assert {p.name: p.read_bytes() for p in folder.iterdir()} == before


def test_a_missing_sheet_item_is_refused_naming_it(tmp_path):
    fake = FakeBuildingsStac(sheets=[s for s in SHEETS if s != "1328-33"])
    full = FakeBuildingsStac()
    with pytest.raises(DownloadError, match="1328-33"):
        _download(fake, tmp_path, _lock(full))
    assert fake.file_fetches == []


def test_a_damaged_download_is_not_kept(tmp_path):
    fake = FakeBuildingsStac()
    lock = _lock(fake)
    url = next(u for u in fake.files if "1348-11" in u and u.endswith(".gdb.zip"))
    fake.files[url] = b"damaged in transit"
    with pytest.raises(DownloadError, match="1348-11"):
        _download(fake, tmp_path, lock)
    folder = tmp_path / "swissbuildings3d" / "2020"
    assert not (folder / "swissbuildings3d_3_0_2020_1348-11_2056_5728.gdb.zip").exists()
    assert not (folder / "provenance.json").exists()
    assert not list(folder.glob("*.part"))
