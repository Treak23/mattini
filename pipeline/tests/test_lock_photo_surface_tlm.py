"""Pinning tests for brief M3-03: `lock photo`, `lock surface` and `lock tlm` (docs/SPEC.md §5).

Pinned decisions: each command writes its dataset's entry of config/datasets.lock.json from
the STAC items only (no request for a file, not even a HEAD) and keeps every other entry as
it was; the file stays sorted, 2-space indented, UTF-8, LF, with a final newline. The
entries, exact key sets (lesson 33):

- `swissimage`: {collection, edition, resolution_m, tiles: {<tile>: {file, sha256}}}, item
  `swissimage-dop10_<edition>_<tile>`, the one asset ending `_0.1_2056.tif`;
- `swisssurface3d`: {collection, resolution_m, tiles: {<tile>: {edition, file, sha256}}}: for
  every tile, the item `swisssurface3d-raster_<year>_<tile>` of every year in `editions` is
  read; exactly one must exist (HTTP 404 = absent; any other failure is a refusal, never an
  absence), the asset ending `_0.5_2056_5728.tif`. A tile in no edition or in two is
  refused naming the tile and the years found ("found none", "found ['2021', '2022']"),
  and nothing is written;
- `swisstlm3d`: {collection, edition, file, sha256}, item `swisstlm3d_<edition>`, the one
  asset ending `_2056_5728.gdb.zip`.

swisstopo publishes `file:checksum` in upper-case hex; the lock stores lower-case. The
commands run as the owner runs them, `python -m mattini lock <x>`, against a local HTTP
stand-in (local_swisstopo.py) through the real urllib code: only `download.STAC_ITEM` and
`lock.LOCK_PATH` are patched.

Likeliest wrong twins, each caught here: `lock <x>` writing a lock of its own entry alone;
the first asset or any `.zip` taken for the TLM (the GeoPackage comes first); the surface's
edition put at the entry's top level, or the first edition that answers taken without
reading the others (a tile in two editions); a server error read as "absent"; the
checksum stored as published.

Does NOT prove: that the live STAC API serves these items today (the network tests and
test_measured_photo_surface_tlm.py do).
"""

import json
import shutil

import pytest
from local_swisstopo import SURFACE, TLM, TLM_FILE, TLM_ITEM, LocalSwisstopo

import mattini.__main__ as cli
from mattini import download, lock
from mattini.world import REPO

COMMITTED_LOCK = REPO / "config" / "datasets.lock.json"


@pytest.fixture
def swisstopo(monkeypatch, tmp_path):
    """The stand-in wired into the command line; the lock is a copy of the committed one."""
    for name in ("http_proxy", "HTTP_PROXY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("no_proxy", "127.0.0.1")
    site = LocalSwisstopo()
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
    """The refusal: stderr from its `mattini: error:` line on (progress lines come first)."""
    assert "mattini: error: " in err, err
    return err[err.index("mattini: error: ") :]


def _text(lock_data):
    return (json.dumps(lock_data, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def test_each_command_writes_its_exact_entry_and_keeps_every_other(swisstopo, capsys):
    item = json.loads(swisstopo.routes[swisstopo.item_path(TLM, TLM_ITEM)][0])
    published = item["assets"][TLM_FILE]["file:checksum"]
    assert published == published.upper() and published != published.lower()  # as live

    expected = json.loads(COMMITTED_LOCK.read_bytes())
    for command, dataset in (
        ("photo", "swissimage"),
        ("surface", "swisssurface3d"),
        ("tlm", "swisstlm3d"),
    ):
        code, out, err = _run(capsys, "lock", command)
        assert (code, out) == (0, f"{swisstopo.lock_path}\n"), err
        expected["datasets"][dataset] = swisstopo.expected_entries()[dataset]
        assert swisstopo.lock_path.read_bytes() == _text(expected), command
    assert set(expected["datasets"]) == {
        "swissalti3d",
        "swissbuildings3d",
        "swissimage",
        "swisssurface3d",
        "swisstlm3d",
    }
    assert swisstopo.file_requests() == []  # STAC only: no file, no HEAD


@pytest.mark.parametrize("case", ["none", "two"])
def test_lock_surface_refuses_a_tile_in_no_edition_or_in_two(swisstopo, capsys, case):
    if case == "none":
        tile, found = "2623-1097", "found none"
        swisstopo.withdraw_surface(tile, "2021")
    else:
        tile, found = "2624-1096", "found ['2021', '2022']"
        swisstopo.publish_surface(tile, "2022", b"a second edition of the tile")
    before = swisstopo.lock_path.read_bytes()
    code, out, err = _run(capsys, "lock", "surface")
    assert (code, out) == (1, "")
    assert _error(err).startswith(f"mattini: error: tile {tile} of area 'village': "), err
    assert found in _error(err), err
    assert swisstopo.lock_path.read_bytes() == before
    assert swisstopo.file_requests() == []


def test_a_server_error_is_not_an_absent_edition(swisstopo, capsys):
    """2623-1096 is published in 2021 only; its 2022 item answers 500, not 404."""
    path = swisstopo.item_path(SURFACE, "swisssurface3d-raster_2022_2623-1096")
    swisstopo.script[path] = [("status", 500)] * 10
    before = swisstopo.lock_path.read_bytes()
    code, out, err = _run(capsys, "lock", "surface")
    assert (code, out) == (1, "")
    error = _error(err)
    assert error.startswith("mattini: error: tile 2623-1096 of area 'village': "), err
    assert "cannot read the STAC item" in error and "500" in error, err
    assert swisstopo.lock_path.read_bytes() == before
