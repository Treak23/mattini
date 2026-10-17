"""Pinning tests for brief M4-01: `python -m mattini download regio` (m4-design §1, SPEC §5).

Pinned decisions:

- *Layout.* Under the download root (`--out`, default data/raw): `swissaltiregio/<edition>/`
  (`2026-06`) with the 30 zips under swisstopo's names and a provenance.json with exactly the
  terrain's keys: {attribution, collection, dataset, edition, resolution_m, schema: 1,
  tiles: [{file, item, sha256, size_bytes, tile, url}] in the lock's tile order}, sorted
  keys, 2-space indent, UTF-8, LF, final newline, no times, no paths. The attribution is the
  datasets config's, the whole source text. The command prints the provenance path on
  stdout. A second run fetches nothing and writes the same bytes.
- *The lock first.* The lock's `swissaltiregio` entry must fit the configs (collection,
  edition, resolution, exactly the tiles the surroundings need), else the download is
  refused naming `python -m mattini lock regio` and no other command, before swisstopo is
  asked anything.
- *Checked before anything is fetched.* Every item's datetime must be in the edition, and
  every published file name and SHA-256 must be the lock's, before any request for a file
  and before anything on disk changes. A republished tile is refused naming the tile, both
  checksums, "nothing was fetched", `python -m mattini lock regio`, "then commit the lock"
  and design's step: config/surroundings.json, whose expected heights record the entry.
- *Files* download as the terrain's: to `<file>.part`, verified, renamed; a body that does
  not verify is fetched once more; a verified file already there is kept.

Run as the owner runs them, against the local stand-in (local_regio.py) through the real
urllib code; the lock is written here from design's expected entry, not by `lock regio`.

Likeliest wrong twins, each caught here: the comparison made lazily before each fetch (the
republished tile is the last); the edition not checked at download; a fit that ignores the
tile set; the republish refusal naming config/terrain.json; a provenance without the whole
attribution.

Does NOT prove: that the files hold what the surroundings step reads (brief M4-02), nor a
republish after today.
"""

import json

import pytest
from local_regio import REGIO, VILLAGE_TILES, LocalRegio, regio_name
from local_swisstopo import sha256

import mattini.__main__ as cli
from mattini import download, lock
from mattini.world import REPO

FOLDER = "swissaltiregio/2026-06"
LOCK_COMMAND = "python -m mattini lock regio"
OTHER_COMMANDS = ("lock terrain", "lock buildings", "lock photo", "lock surface", "lock tlm")


@pytest.fixture
def regio(monkeypatch, tmp_path):
    """The stand-in wired into the command line, and a lock pinning what it publishes."""
    for name in ("http_proxy", "HTTP_PROXY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("no_proxy", "127.0.0.1")
    site = LocalRegio()
    monkeypatch.setattr(download, "STAC_ITEM", site.stac_item)
    site.lock_path = tmp_path / "config" / "datasets.lock.json"
    site.lock_path.parent.mkdir()
    site.pinned = json.loads((REPO / "config" / "datasets.lock.json").read_bytes())
    site.pinned["datasets"]["swissaltiregio"] = site.regio_entry()
    site.lock_path.write_text(json.dumps(site.pinned, indent=2, sort_keys=True), "utf-8")
    monkeypatch.setattr(lock, "LOCK_PATH", site.lock_path)
    site.out = tmp_path / "raw"
    yield site
    site.close()


def _run(capsys, *argv):
    code = cli.main(list(argv))
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _error(err):
    assert "mattini: error: " in err, err
    return err[err.index("mattini: error: ") :]


def _download(site, capsys):
    return _run(capsys, "download", "regio", "--out", str(site.out))


def _attribution():
    datasets = json.loads((REPO / "config" / "datasets.json").read_text(encoding="utf-8"))
    return datasets["datasets"]["swissaltiregio"]["attribution"]


def _provenance(site):
    tiles = []
    for tile in VILLAGE_TILES:
        name = regio_name(tile)
        tiles.append(
            {
                "file": name,
                "item": f"swissaltiregio_{tile}",
                "sha256": sha256(site.bodies[name]),
                "size_bytes": len(site.bodies[name]),
                "tile": tile,
                "url": site.base + site.file_path(name),
            }
        )
    return {
        "attribution": _attribution(),
        "collection": REGIO,
        "dataset": "swissaltiregio",
        "edition": "2026-06",
        "resolution_m": 10,
        "schema": 1,
        "tiles": tiles,
    }


def _bytes(data):
    return (json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def _write_lock(site, entry):
    site.pinned["datasets"]["swissaltiregio"] = entry
    site.lock_path.write_text(json.dumps(site.pinned, indent=2, sort_keys=True), "utf-8")


def test_download_fetches_verifies_and_records(regio, capsys):
    code, out, err = _download(regio, capsys)
    folder = regio.out / FOLDER
    assert (code, out) == (0, f"{folder / 'provenance.json'}\n"), err
    assert (folder / "provenance.json").read_bytes() == _bytes(_provenance(regio))
    names = sorted(p.name for p in folder.iterdir())
    assert names == sorted([regio_name(t) for t in VILLAGE_TILES] + ["provenance.json"])
    for tile in VILLAGE_TILES:
        assert (folder / regio_name(tile)).read_bytes() == regio.bodies[regio_name(tile)]
    assert [m for m, _, _ in regio.file_requests()] == ["GET"] * 30

    before = len(regio.requests)
    code, _, err = _download(regio, capsys)
    assert code == 0, err
    assert [r for r in regio.requests[before:] if not r[1].startswith("/api/stac/")] == []
    assert (folder / "provenance.json").read_bytes() == _bytes(_provenance(regio))


def test_a_republished_tile_is_refused_before_anything_is_fetched(regio, capsys):
    last = VILLAGE_TILES[-1]
    old = sha256(regio.bodies[regio_name(last)])
    regio.publish_regio(last, b"republished bytes")
    code, out, err = _download(regio, capsys)
    assert (code, out) == (1, "")
    error = _error(err)
    assert last in error and old in error and sha256(b"republished bytes") in error, error
    assert "nothing was fetched" in error and f"`{LOCK_COMMAND}`" in error, error
    assert "then commit the lock" in error and "config/surroundings.json" in error, error
    assert "config/terrain.json" not in error, error
    assert regio.file_requests() == []
    assert not (regio.out / FOLDER).exists()


def test_an_item_of_another_edition_is_refused_before_anything_is_fetched(regio, capsys):
    tile = VILLAGE_TILES[-1]
    regio.publish_regio(tile, regio.bodies[regio_name(tile)], datetime="2027-05-01T00:00:00Z")
    code, out, err = _download(regio, capsys)
    assert (code, out) == (1, "")
    error = _error(err)
    assert tile in error and "2027-05-01T00:00:00Z" in error and "2026-06" in error, error
    assert regio.file_requests() == []
    assert not (regio.out / FOLDER).exists()


def test_a_republish_after_a_download_changes_nothing_on_disk(regio, capsys):
    assert _download(regio, capsys)[0] == 0
    folder = regio.out / FOLDER
    before = {p.name: p.read_bytes() for p in folder.iterdir()}
    regio.publish_regio(VILLAGE_TILES[0], b"republished bytes")
    assert _download(regio, capsys)[0] == 1
    assert {p.name: p.read_bytes() for p in folder.iterdir()} == before


@pytest.mark.parametrize(
    "case",
    ["no-entry", "a-tile-missing", "a-tile-too-many", "edition", "resolution", "collection"],
)
def test_a_lock_that_does_not_fit_is_refused_naming_lock_regio(regio, capsys, case):
    entry = regio.regio_entry()
    if case == "no-entry":
        del regio.pinned["datasets"]["swissaltiregio"]
        regio.lock_path.write_text(json.dumps(regio.pinned, indent=2, sort_keys=True), "utf-8")
    else:
        if case == "a-tile-missing":
            del entry["tiles"]["2645-1114"]
        elif case == "a-tile-too-many":
            entry["tiles"]["2655-1114"] = {"file": regio_name("2655-1114"), "sha256": "0" * 64}
        elif case == "edition":
            entry["edition"] = "2025-06"
        elif case == "resolution":
            entry["resolution_m"] = 2
        else:
            entry["collection"] = "ch.swisstopo.swissalti3d"
        _write_lock(regio, entry)
    code, out, err = _download(regio, capsys)
    assert (code, out) == (1, "")
    error = _error(err)
    assert f"`{LOCK_COMMAND}`" in error, error
    assert not any(other in error for other in OTHER_COMMANDS), error
    assert "download" not in error.replace("python -m mattini lock regio", ""), error
    assert regio.requests == []  # refused before swisstopo is asked anything
    assert not (regio.out / FOLDER).exists()


def test_a_body_that_does_not_verify_is_fetched_once_more_through_a_part_file(regio, capsys):
    tile = VILLAGE_TILES[3]
    path = regio.file_path(regio_name(tile))
    regio.script[path] = [("cut", 100)]  # the first transfer ends short, without an error
    code, _, err = _download(regio, capsys)
    assert code == 0, err
    folder = regio.out / FOLDER
    assert (folder / regio_name(tile)).read_bytes() == regio.bodies[regio_name(tile)]
    assert [r for r in regio.file_requests() if r[1] == path] == [("GET", path, None)] * 2
    assert not list(folder.glob("*.part"))


def test_a_damaged_file_on_disk_is_fetched_again(regio, capsys):
    assert _download(regio, capsys)[0] == 0
    folder = regio.out / FOLDER
    damaged = folder / regio_name(VILLAGE_TILES[7])
    damaged.write_bytes(b"damaged")
    before = len(regio.requests)
    code, _, err = _download(regio, capsys)
    assert code == 0, err
    fetched = [r[1] for r in regio.requests[before:] if not r[1].startswith("/api/stac/")]
    assert fetched == [regio.file_path(damaged.name)]
    assert damaged.read_bytes() == regio.bodies[damaged.name]
    assert (folder / "provenance.json").read_bytes() == _bytes(_provenance(regio))
