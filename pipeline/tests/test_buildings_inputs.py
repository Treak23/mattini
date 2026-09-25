"""The buildings' lock entry and download on the command line, and their refusals (M2-03).

The pinning tests (test_buildings_download.py) call the library. These run the commands
the owner runs, `python -m mattini lock buildings|terrain` and `download buildings`, with
the fetchers and the lock's path patched to a fake STAC API serving both collections: the
six village tiles (fake_swisstopo) and the six village sheets. They check what the brief
states and the pinning tests leave out: `lock <dataset>` writes that entry only and keeps
the other byte for byte; a lock it cannot read is refused before swisstopo is asked
anything; the download's lock checks (edition, collection, a missing sheet, a SHA-256
changed by one digit) come before anything on disk changes, naming the sheet and `python
-m mattini lock buildings`; a damaged file on disk is replaced; a dropped fetch is
retried once; `validate_lock` refuses an unknown dataset and accepts a lock that holds
only the buildings (M2-04's fixture).

Does NOT prove: that the live STAC API serves these items (the network test and the
builder's real run do); anything about the zips' contents (M2-04).
"""

import copy
import hashlib
import json

import pytest
from fake_swisstopo import FakeSwisstopo

import mattini.__main__ as cli
from mattini import download, lock
from mattini.world import REPO

BUILDINGS_STAC = (
    "https://data.geo.admin.ch/api/stac/v1/collections/ch.swisstopo.swissbuildings3d_3_0/items/"
)
SHEETS = ["1328-33", "1328-34", "1348-11", "1348-12", "1348-13", "1348-14"]
LOCK_BUILDINGS = "`python -m mattini lock buildings`"


def _name(sheet):
    return f"swissbuildings3d_3_0_2020_{sheet}_2056_5728.gdb.zip"


class FakeStac:
    """Both collections; a missing item is a 404 (an OSError), as urllib raises it."""

    def __init__(self):
        terrain = FakeSwisstopo()
        self.items, self.files = dict(terrain.items), dict(terrain.files)
        self.json_fetches, self.file_fetches = [], []
        self.drop_once = set()  # file URLs whose next fetch drops the connection
        for sheet in SHEETS:
            self.publish(sheet, f"sheet bytes of {sheet}".encode() * 100)

    def publish(self, sheet, body):
        item_id = f"swissbuildings3d_3_0_2020_{sheet}"
        gdb, dwg = _name(sheet), f"{item_id}_2056_5728.dwg.zip"
        self.files[f"https://files.example/{gdb}"] = body
        self.files[f"https://files.example/{dwg}"] = b"the dwg must not be fetched"
        self.items[BUILDINGS_STAC + item_id] = {
            "id": item_id,
            "assets": {
                dwg: {"href": f"https://files.example/{dwg}", "file:checksum": "1220" + "22" * 32},
                gdb: {
                    "href": f"https://files.example/{gdb}",
                    "file:checksum": "1220" + hashlib.sha256(body).hexdigest(),
                },
            },
        }

    def body(self, sheet):
        return self.files[f"https://files.example/{_name(sheet)}"]

    def fetch_json(self, url):
        self.json_fetches.append(url)
        if url not in self.items:
            raise OSError(f"HTTP Error 404: Not Found: {url}")
        return copy.deepcopy(self.items[url])

    def fetch_file(self, url, dest):
        self.file_fetches.append(url)
        if url in self.drop_once:
            self.drop_once.discard(url)
            dest.write_bytes(b"half a file")
            raise ConnectionResetError("the network dropped")
        dest.write_bytes(self.files[url])


@pytest.fixture
def stac(tmp_path, monkeypatch):
    """The fake wired into the command line; the lock lives in tmp_path, not yet written."""
    fake = FakeStac()
    fake.lock_path = tmp_path / "config" / "datasets.lock.json"
    fake.lock_path.parent.mkdir()
    fake.raw = tmp_path / "raw"
    fake.folder = fake.raw / "swissbuildings3d" / "2020"
    monkeypatch.setattr(download, "urllib_fetch_json", fake.fetch_json)
    monkeypatch.setattr(download, "urllib_fetch_file", fake.fetch_file)
    monkeypatch.setattr(lock, "LOCK_PATH", fake.lock_path)
    return fake


def _run(capsys, *argv):
    code = cli.main(list(argv))
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _locked(stac):
    return json.loads(stac.lock_path.read_bytes())["datasets"]


def _snapshot(folder):
    return {p.name: p.read_bytes() for p in sorted(folder.iterdir())}


def _edit_lock(stac, change):
    data = json.loads(stac.lock_path.read_bytes())
    change(data["datasets"])
    stac.lock_path.write_text(json.dumps(data), encoding="utf-8")


def test_lock_buildings_adds_its_entry_and_keeps_the_terrain_s(stac, capsys):
    assert _run(capsys, "lock", "terrain")[0] == 0
    terrain_only = stac.lock_path.read_bytes()
    stac.json_fetches.clear()

    code, out, err = _run(capsys, "lock", "buildings")
    assert (code, out, err) == (0, f"{stac.lock_path}\n", "")
    datasets = _locked(stac)
    assert datasets["swissalti3d"] == json.loads(terrain_only)["datasets"]["swissalti3d"]
    assert datasets["swissbuildings3d"] == {
        "collection": "ch.swisstopo.swissbuildings3d_3_0",
        "edition": "2020",
        "sheets": {
            sheet: {"file": _name(sheet), "sha256": hashlib.sha256(stac.body(sheet)).hexdigest()}
            for sheet in SHEETS
        },
    }
    assert [url.rsplit("_", 1)[1] for url in stac.json_fetches] == SHEETS
    assert stac.file_fetches == []  # the lock reads the STAC items only

    # and `lock terrain` now keeps the buildings: the file comes back byte for byte
    both = stac.lock_path.read_bytes()
    assert _run(capsys, "lock", "terrain")[0] == 0
    assert stac.lock_path.read_bytes() == both
    assert both == (json.dumps(json.loads(both), indent=2, sort_keys=True) + "\n").encode()


def test_lock_buildings_without_a_lock_writes_its_entry_alone(stac, capsys):
    assert _run(capsys, "lock", "buildings")[0] == 0
    assert list(_locked(stac)) == ["swissbuildings3d"]


@pytest.mark.parametrize("dataset", ["terrain", "buildings"])
@pytest.mark.parametrize("text", ["", "{", '{"schema": 1, "datasets": {"swissalti3d": {}}}'])
def test_the_lock_command_refuses_a_lock_it_cannot_read(stac, capsys, dataset, text):
    stac.lock_path.write_text(text, encoding="utf-8")
    code, out, err = _run(capsys, "lock", dataset)
    assert (code, out) == (1, "")
    assert err.startswith(f"mattini: error: {stac.lock_path}: ")
    assert "keeps the others" in err and "restore" in err
    assert stac.lock_path.read_text(encoding="utf-8") == text  # never replaced
    assert stac.json_fetches == []  # refused before swisstopo is asked anything


def test_lock_buildings_names_a_missing_sheet_and_writes_nothing(stac, capsys):
    assert _run(capsys, "lock", "terrain")[0] == 0
    before = stac.lock_path.read_bytes()
    missing = BUILDINGS_STAC + "swissbuildings3d_3_0_2020_1348-13"
    del stac.items[missing]
    code, out, err = _run(capsys, "lock", "buildings")
    assert (code, out) == (1, "")
    assert "mattini: error: sheet 1348-13 of area 'village'" in err and missing in err
    assert stac.lock_path.read_bytes() == before


def test_download_buildings_then_a_rerun_fetches_nothing(stac, capsys):
    assert _run(capsys, "lock", "buildings")[0] == 0
    code, out, err = _run(capsys, "download", "buildings", "--out", str(stac.raw))
    assert (code, out) == (0, f"{stac.folder / 'provenance.json'}\n")
    assert err.count("fetching ") == 6 and "6 sheets verified, 6 fetches" in err
    first = _snapshot(stac.folder)
    assert sorted(first) == sorted([_name(s) for s in SHEETS] + ["provenance.json"])

    code, out, err = _run(capsys, "download", "buildings", "--out", str(stac.raw))
    assert code == 0 and "fetching " not in err and "6 sheets verified, 0 fetches" in err
    assert _snapshot(stac.folder) == first


@pytest.mark.parametrize(
    ("change", "complaint"),
    [
        (lambda d: d.pop("swissbuildings3d"), "has no 'swissbuildings3d' entry"),
        (lambda d: d["swissbuildings3d"].update(edition="2016"), "edition '2016'"),
        (
            lambda d: d["swissbuildings3d"].update(collection="ch.swisstopo.swissbuildings3d_2"),
            "collection 'ch.swisstopo.swissbuildings3d_2'",
        ),
        (lambda d: d["swissbuildings3d"]["sheets"].pop("1328-34"), "['1328-34']"),
    ],
    ids=["no-entry", "edition", "collection", "missing-sheet"],
)
def test_a_lock_that_does_not_fit_the_config_is_refused_before_anything(
    stac, capsys, change, complaint
):
    assert _run(capsys, "lock", "terrain")[0] == 0
    assert _run(capsys, "lock", "buildings")[0] == 0
    _edit_lock(stac, change)
    stac.json_fetches.clear()
    code, out, err = _run(capsys, "download", "buildings", "--out", str(stac.raw))
    assert (code, out) == (1, "")
    assert complaint in err and "'village'" in err and LOCK_BUILDINGS in err
    assert stac.json_fetches == [] and stac.file_fetches == []
    assert not stac.raw.exists()


def test_a_sheet_whose_lock_sha256_differs_by_one_digit_is_refused_before_anything(stac, capsys):
    """The brief's mutation, as a test: the lock changed by one digit, nothing on disk moves."""
    assert _run(capsys, "lock", "buildings")[0] == 0
    assert _run(capsys, "download", "buildings", "--out", str(stac.raw))[0] == 0
    before = _snapshot(stac.folder)
    published = hashlib.sha256(stac.body("1348-12")).hexdigest()
    changed = published[:-1] + ("0" if published[-1] != "0" else "1")
    _edit_lock(stac, lambda d: d["swissbuildings3d"]["sheets"]["1348-12"].update(sha256=changed))
    stac.file_fetches.clear()

    code, out, err = _run(capsys, "download", "buildings", "--out", str(stac.raw))
    assert (code, out) == (1, "")
    assert "mattini: error: sheet 1348-12 of area 'village'" in err
    assert published in err and changed in err and LOCK_BUILDINGS in err
    assert stac.file_fetches == []
    assert _snapshot(stac.folder) == before  # provenance.json and every file untouched


def test_a_damaged_file_on_disk_is_replaced_and_a_dropped_fetch_retried(stac, capsys):
    assert _run(capsys, "lock", "buildings")[0] == 0
    assert _run(capsys, "download", "buildings", "--out", str(stac.raw))[0] == 0
    first = _snapshot(stac.folder)
    (stac.folder / _name("1348-11")).write_bytes(b"damaged on disk")
    url = f"https://files.example/{_name('1348-11')}"
    stac.drop_once.add(url)
    stac.file_fetches.clear()

    code, _, err = _run(capsys, "download", "buildings", "--out", str(stac.raw))
    assert code == 0 and "6 sheets verified, 2 fetches" in err
    assert stac.file_fetches == [url, url]  # the drop, then the one retry
    assert _snapshot(stac.folder) == first
    assert not list(stac.folder.glob("*.part"))


def test_a_download_with_no_lock_names_both_lock_commands(stac, capsys):
    code, out, err = _run(capsys, "download", "buildings", "--out", str(stac.raw))
    assert (code, out) == (1, "")
    assert err.startswith(f"mattini: error: {stac.lock_path}: ")
    assert LOCK_BUILDINGS in err and "`python -m mattini lock terrain`" in err
    assert stac.json_fetches == [] and not stac.raw.exists()


def test_the_lock_refuses_an_unknown_dataset_and_accepts_the_buildings_alone(tmp_path):
    fixture = REPO / "tests" / "shared" / "buildings_fixture" / "datasets.lock.json"
    alone = lock.load_lock(fixture)
    assert list(alone["datasets"]) == ["swissbuildings3d"]
    unknown = lock.with_entry(alone, "swissnames3d", alone["datasets"]["swissbuildings3d"])
    with pytest.raises(lock.LockError, match="unknown dataset 'swissnames3d'"):
        lock.validate_lock(unknown, "test")
    with pytest.raises(lock.LockError, match="unknown dataset"):
        lock.write_lock(unknown, tmp_path / "lock.json")
    assert not (tmp_path / "lock.json").exists()


def test_with_entry_changes_neither_argument():
    fixture = REPO / "tests" / "shared" / "buildings_fixture" / "datasets.lock.json"
    alone = lock.load_lock(fixture)
    kept = copy.deepcopy(alone)
    entry = {"collection": "c", "edition": "2024", "resolution_m": 0.5, "tiles": {}}
    result = lock.with_entry(alone, "swissalti3d", entry)
    result["datasets"]["swissalti3d"]["tiles"]["x"] = 1
    result["datasets"]["swissbuildings3d"]["edition"] = "changed"
    assert alone == kept
    assert entry["tiles"] == {}
