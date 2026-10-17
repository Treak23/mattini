"""Pinning tests for brief M4-01: `python -m mattini lock regio` (m4-design §1, SPEC §5).

Pinned decisions:

- The lock's `swissaltiregio` entry is exactly {collection, edition, resolution_m,
  tiles: {<tile>: {file, sha256}}}, written only by `python -m mattini lock regio` from the
  STAC items (no request to the file host, not even a HEAD), replacing its own entry and
  keeping every other; the file stays sorted, 2-space indented, UTF-8, LF, final newline.
- The tiles are the 10 km items `swissaltiregio_<E km>-<N km>` whose square meets the
  samples the surroundings need (`download.regio_tiles`, test_m4_01_regio_tiles.py), for
  the area config/terrain.json names and the `margin_m` and `spacing_m` config/surroundings.json
  gives it: the village's 30. The asset is the one whose key ends `_2056_5728.xyz.zip`.
- The item ids carry no edition (measured): an item whose `properties.datetime` is not in the
  pinned edition (`2026-06-01T00:00:00Z` is in `2026-06`) is refused naming the tile, its
  datetime and the edition, and nothing is written. A tile with no item is refused, "cannot
  read the STAC item".
- `file:checksum` comes in upper-case hex; the lock stores lower-case.
- A malformed lock is refused naming `python -m mattini lock regio` among the lock commands.

Run as the owner runs them, against the local stand-in (local_regio.py) through the real
urllib code; only `download.STAC_ITEM` and `lock.LOCK_PATH` are patched.

Likeliest wrong twins, each caught here: the lock written with the regio entry alone; the
tiles of the area box without the margin, or of the box without its half-spacing border
(the village's east column 2645 is needed only through it), or a ring too many; the edition
not checked against the items (they would lock a new edition under the old name); the
checksum stored as published.

Does NOT prove: that the live STAC API serves these items today
(test_m4_01_measured_regio.py and the network test do).
"""

import json
import shutil

import pytest
from local_regio import RING_TILES, VILLAGE_TILES, LocalRegio

import mattini.__main__ as cli
from mattini import download, lock
from mattini.world import REPO

COMMITTED_LOCK = REPO / "config" / "datasets.lock.json"
LOCK_COMMAND = "python -m mattini lock regio"


@pytest.fixture
def regio(monkeypatch, tmp_path):
    """The stand-in wired into the command line; the lock is a copy of the committed one."""
    for name in ("http_proxy", "HTTP_PROXY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("no_proxy", "127.0.0.1")
    site = LocalRegio()
    monkeypatch.setattr(download, "STAC_ITEM", site.stac_item)
    site.lock_path = tmp_path / "config" / "datasets.lock.json"
    site.lock_path.parent.mkdir()
    shutil.copyfile(COMMITTED_LOCK, site.lock_path)
    monkeypatch.setattr(lock, "LOCK_PATH", site.lock_path)
    yield site
    site.close()


def _run(capsys, *argv):
    code = cli.main(list(argv))
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _error(err):
    assert "mattini: error: " in err, err
    return err[err.index("mattini: error: ") :]


def _text(lock_data):
    return (json.dumps(lock_data, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def _item_requests(site):
    return [path for _, path, _ in site.requests if path.startswith("/api/stac/")]


def test_lock_regio_writes_its_exact_entry_and_keeps_every_other(regio, capsys):
    expected = json.loads(COMMITTED_LOCK.read_bytes())
    expected["datasets"].pop("swissaltiregio", None)  # a lock regio already wrote, replaced
    expected["datasets"]["swissaltiregio"] = regio.regio_entry()
    code, out, err = _run(capsys, "lock", "regio")
    assert (code, out) == (0, f"{regio.lock_path}\n"), err
    assert regio.lock_path.read_bytes() == _text(expected)
    entry = expected["datasets"]["swissaltiregio"]
    assert list(entry["tiles"]) == sorted(VILLAGE_TILES) and len(VILLAGE_TILES) == 30
    assert all(t["sha256"] == t["sha256"].lower() for t in entry["tiles"].values())
    assert regio.file_requests() == []  # STAC only: no file, no HEAD
    asked = {path.rsplit("/", 1)[1] for path in _item_requests(regio)}
    assert not asked & {f"swissaltiregio_{tile}" for tile in RING_TILES}


def test_a_second_run_writes_the_same_bytes(regio, capsys):
    assert _run(capsys, "lock", "regio")[0] == 0
    first = regio.lock_path.read_bytes()
    assert _run(capsys, "lock", "regio")[0] == 0
    assert regio.lock_path.read_bytes() == first


@pytest.mark.parametrize(
    "datetime", ["2027-05-01T00:00:00Z", "2026-07-01T00:00:00Z", "2025-06-01T00:00:00Z"]
)
def test_an_item_of_another_edition_is_refused_and_nothing_is_written(regio, capsys, datetime):
    before = regio.lock_path.read_bytes()
    regio.publish_regio("2625-1094", b"a newer edition of the tile", datetime=datetime)
    code, out, err = _run(capsys, "lock", "regio")
    assert (code, out) == (1, "")
    error = _error(err)
    assert "2625-1094" in error and datetime in error and "2026-06" in error, error
    assert regio.lock_path.read_bytes() == before
    assert regio.file_requests() == []


def test_a_tile_without_an_item_is_refused_and_nothing_is_written(regio, capsys):
    before = regio.lock_path.read_bytes()
    regio.withdraw_regio("2645-1114")
    code, out, err = _run(capsys, "lock", "regio")
    assert (code, out) == (1, "")
    error = _error(err)
    assert "2645-1114" in error and "cannot read the STAC item" in error, error
    assert regio.lock_path.read_bytes() == before


def test_a_malformed_regio_entry_is_refused_naming_lock_regio(tmp_path):
    data = json.loads(COMMITTED_LOCK.read_bytes())
    data["datasets"]["swissaltiregio"] = {
        "collection": "ch.swisstopo.swissaltiregio",
        "edition": "2026-06",
        "tiles": {"2625-1094": {"file": "a.xyz.zip", "sha256": "0" * 64}},
    }  # no resolution_m
    path = tmp_path / "datasets.lock.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(lock.LockError) as refusal:
        lock.load_lock(path)
    assert "swissaltiregio" in str(refusal.value) and f"`{LOCK_COMMAND}`" in str(refusal.value)


def test_a_well_formed_regio_entry_is_accepted(tmp_path):
    data = json.loads(COMMITTED_LOCK.read_bytes())
    data["datasets"]["swissaltiregio"] = {
        "collection": "ch.swisstopo.swissaltiregio",
        "edition": "2026-06",
        "resolution_m": 10,
        "tiles": {
            "2625-1094": {
                "file": "swissaltiregio_2625-1094_2056_5728.xyz.zip",
                "sha256": "f01770a3e8eff0c6e5ecbfab54136fb56a449770c9d8f4004cebe4cbaa84ea41",
            }
        },
    }
    path = tmp_path / "datasets.lock.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert lock.load_lock(path) == data
