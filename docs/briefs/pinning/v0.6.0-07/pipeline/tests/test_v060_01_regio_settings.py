"""Pinning tests for brief v0.6.0-01: `lock regio` takes the margin and spacing from the config;
re-cut by brief v0.6.0-07 onto the config's one reader.

Pinned decisions (brief M4-01 decision 4, carried over; design §1 of 0.6.0; brief v0.6.0-07
decision 5, which moved brief v0.6.0-01's small reader in download.py onto
`surroundings.load_surroundings_config`):

- config/surroundings.json is read by `surroundings.load_surroundings_config` alone; for the
  village it holds `margin_m` 20000 and `spacing_m` 50 since 0.6.0's design data.
  `download.surroundings_settings` and `download.SURROUNDINGS_PATH` are gone.
- `python -m mattini lock regio` pins the tiles `download.regio_tiles` gives for the area
  config/terrain.json names with those two numbers, exactly: a config with another margin
  locks other tiles. The command line reads the config through the module
  (`surroundings.load_surroundings_config`, looked up when it runs, so the tests replace it
  there). A config the reader refuses ends the command in one `mattini: error:` line naming
  the file, before swisstopo is asked anything, and the lock is left as it was. The reader's
  own refusals are brief v0.6.0-04's (test_m4_02_surroundings_config.py).

Likeliest wrong twins, each caught here: the margin and spacing hard-coded (20000 and 50 lock
the same 30 tiles as 20000 and 100, so only another margin tells them apart); a second reader
left in download.py; the config read after the first STAC request.

Does NOT prove: that the surroundings step reads the same two numbers (brief v0.6.0-04 and
test_v060_07_one_home.py).
"""

import json
import shutil

import pytest
from local_regio import LocalRegio

import mattini.__main__ as cli
from mattini import download, lock, surroundings
from mattini.world import REPO

COMMITTED_LOCK = REPO / "config" / "datasets.lock.json"
COMMITTED_CONFIG = REPO / "config" / "surroundings.json"


def _config(tmp_path, change=None):
    """A copy of the committed config/surroundings.json with the village's settings changed."""
    path = tmp_path / "surroundings.json"
    data = json.loads(COMMITTED_CONFIG.read_text(encoding="utf-8"))
    if change is not None:
        change(data)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _use_config(monkeypatch, path):
    """The command line's surroundings config: `surroundings.load_surroundings_config`, its one
    reader (brief v0.6.0-07), replaced on its module by one that reads `path` with the real
    reader; a refusal is the reader's own, naming `path`."""
    real = surroundings.load_surroundings_config
    monkeypatch.setattr(surroundings, "load_surroundings_config", lambda *a, **k: real(path))


@pytest.fixture
def regio(monkeypatch, tmp_path):
    """The stand-in of test_m4_01_lock_regio.py: STAC_ITEM and LOCK_PATH patched, a lock copy."""
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


def test_the_committed_config_gives_the_village_50_m_and_20_km():
    village = surroundings.load_surroundings_config(COMMITTED_CONFIG)["areas"]["village"]
    assert (village["margin_m"], village["spacing_m"]) == (20000, 50)
    village = surroundings.load_surroundings_config()["areas"]["village"]
    assert (village["margin_m"], village["spacing_m"]) == (20000, 50)


def test_download_py_keeps_no_reader_of_its_own():
    assert not hasattr(download, "surroundings_settings")
    assert not hasattr(download, "SURROUNDINGS_PATH")


def test_lock_regio_locks_the_tiles_of_the_config_s_margin(regio, capsys, monkeypatch, tmp_path):
    def narrow(data):
        data["areas"]["village"]["margin_m"] = 0

    _use_config(monkeypatch, _config(tmp_path, narrow))
    code, out, err = _run(capsys, "lock", "regio")
    assert (code, out) == (0, f"{regio.lock_path}\n"), err
    locked = json.loads(regio.lock_path.read_bytes())["datasets"]["swissaltiregio"]
    assert list(locked["tiles"]) == ["2615-1094", "2625-1094"]  # the area box alone
    assert regio.file_requests() == []


def test_lock_regio_refuses_a_bad_config_before_swisstopo_is_asked(
    regio, capsys, monkeypatch, tmp_path
):
    before = regio.lock_path.read_bytes()
    path = _config(tmp_path, lambda d: d["areas"]["village"].update(spacing_m=50.5))
    _use_config(monkeypatch, path)
    code, out, err = _run(capsys, "lock", "regio")
    assert (code, out) == (1, "")
    assert err.startswith("mattini: error: ") and str(path) in err and "spacing_m" in err, err
    assert "Traceback" not in err and err.count("\n") == 1, err
    assert regio.requests == []
    assert regio.lock_path.read_bytes() == before
