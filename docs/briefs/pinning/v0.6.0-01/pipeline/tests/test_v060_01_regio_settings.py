"""Pinning tests for brief v0.6.0-01: `lock regio` takes the margin and spacing from the config.

Pinned decisions (brief M4-01 decision 4, carried over; design §1 of 0.6.0):

- `download.surroundings_settings(area, path=None)` reads config/surroundings.json (the file at
  `download.SURROUNDINGS_PATH` when `path` is None, looked up when it is called) and returns
  the area's `(margin_m, spacing_m)`: for the village (20000, 50) since 0.6.0's design data.
- Each is a whole number of metres, a JSON integer (not a float, a text or a boolean),
  `margin_m` 0 or more and `spacing_m` 1 or more. A file that cannot be read, is not JSON,
  has no such area, or holds anything else is a DownloadError whose text names the file, and
  the area or the key at fault.
- `python -m mattini lock regio` pins the tiles `download.regio_tiles` gives for the area
  config/terrain.json names with those two numbers, exactly: a config with another margin
  locks other tiles. A config it cannot read ends the command in one `mattini: error:` line
  naming the file, before swisstopo is asked anything, and the lock is left as it was.

Likeliest wrong twins, each caught here: the margin and spacing hard-coded (20000 and 50 lock
the same 30 tiles as 20000 and 100, so only another margin tells them apart); a float or a
boolean accepted as a whole number; the path bound when the module loads (a test that points
the reader elsewhere would read the committed file); a refusal that names no file.

Does NOT prove: that the surroundings step reads the same two numbers (brief v0.6.0-04); the
one home of the reader (brief v0.6.0-07 may move it).
"""

import json
import shutil

import pytest
from local_regio import LocalRegio

import mattini.__main__ as cli
from mattini import download, lock
from mattini.world import REPO

COMMITTED_LOCK = REPO / "config" / "datasets.lock.json"
COMMITTED_CONFIG = REPO / "config" / "surroundings.json"


def _config(tmp_path, change=None, *, text=None):
    """A copy of the committed config/surroundings.json with the village's settings changed."""
    path = tmp_path / "surroundings.json"
    if text is not None:
        path.write_bytes(text)
        return path
    data = json.loads(COMMITTED_CONFIG.read_text(encoding="utf-8"))
    if change is not None:
        change(data)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


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
    assert download.surroundings_settings("village") == (20000, 50)
    assert download.surroundings_settings("village", COMMITTED_CONFIG) == (20000, 50)
    assert download.SURROUNDINGS_PATH == COMMITTED_CONFIG


def test_the_reader_reads_the_path_it_is_given_or_the_module_s_when_called(monkeypatch, tmp_path):
    def narrow(data):
        data["areas"]["village"].update(margin_m=0, spacing_m=100)

    path = _config(tmp_path, narrow)
    assert download.surroundings_settings("village", path) == (0, 100)
    assert download.surroundings_settings("village", str(path)) == (0, 100)
    monkeypatch.setattr(download, "SURROUNDINGS_PATH", path)
    assert download.surroundings_settings("village") == (0, 100)


def test_lock_regio_locks_the_tiles_of_the_config_s_margin(regio, capsys, monkeypatch, tmp_path):
    def narrow(data):
        data["areas"]["village"]["margin_m"] = 0

    monkeypatch.setattr(download, "SURROUNDINGS_PATH", _config(tmp_path, narrow))
    code, out, err = _run(capsys, "lock", "regio")
    assert (code, out) == (0, f"{regio.lock_path}\n"), err
    locked = json.loads(regio.lock_path.read_bytes())["datasets"]["swissaltiregio"]
    assert list(locked["tiles"]) == ["2615-1094", "2625-1094"]  # the area box alone
    assert regio.file_requests() == []


@pytest.mark.parametrize(
    ("change", "named"),
    [
        (lambda d: d["areas"].pop("village"), "'village'"),
        (lambda d: d.pop("areas"), "'village'"),
        (lambda d: d["areas"].update(village=[20000, 50]), "'village'"),
        (lambda d: d["areas"]["village"].pop("margin_m"), "margin_m"),
        (lambda d: d["areas"]["village"].pop("spacing_m"), "spacing_m"),
        (lambda d: d["areas"]["village"].update(margin_m=20000.0), "margin_m"),
        (lambda d: d["areas"]["village"].update(margin_m="20000"), "margin_m"),
        (lambda d: d["areas"]["village"].update(margin_m=None), "margin_m"),
        (lambda d: d["areas"]["village"].update(margin_m=-1), "margin_m"),
        (lambda d: d["areas"]["village"].update(spacing_m=50.0), "spacing_m"),
        (lambda d: d["areas"]["village"].update(spacing_m=True), "spacing_m"),
        (lambda d: d["areas"]["village"].update(spacing_m=0), "spacing_m"),
        (lambda d: d["areas"]["village"].update(spacing_m=-50), "spacing_m"),
    ],
)
def test_a_config_without_two_whole_numbers_is_refused_naming_the_file(tmp_path, change, named):
    path = _config(tmp_path, change)
    with pytest.raises(download.DownloadError) as refusal:
        download.surroundings_settings("village", path)
    assert str(path) in str(refusal.value) and named in str(refusal.value), str(refusal.value)


def test_a_margin_of_zero_is_a_whole_number(tmp_path):
    path = _config(tmp_path, lambda d: d["areas"]["village"].update(margin_m=0, spacing_m=1))
    assert download.surroundings_settings("village", path) == (0, 1)


@pytest.mark.parametrize("text", [b"{not json", b"\xff\xfe", b""])
def test_a_file_that_is_not_json_is_refused_naming_it(tmp_path, text):
    path = _config(tmp_path, text=text)
    with pytest.raises(download.DownloadError) as refusal:
        download.surroundings_settings("village", path)
    assert str(path) in str(refusal.value), str(refusal.value)


def test_a_missing_file_is_refused_naming_it(tmp_path):
    path = tmp_path / "nowhere" / "surroundings.json"
    with pytest.raises(download.DownloadError) as refusal:
        download.surroundings_settings("village", path)
    assert str(path) in str(refusal.value), str(refusal.value)


def test_lock_regio_refuses_a_bad_config_before_swisstopo_is_asked(
    regio, capsys, monkeypatch, tmp_path
):
    before = regio.lock_path.read_bytes()
    path = _config(tmp_path, lambda d: d["areas"]["village"].update(spacing_m=50.5))
    monkeypatch.setattr(download, "SURROUNDINGS_PATH", path)
    code, out, err = _run(capsys, "lock", "regio")
    assert (code, out) == (1, "")
    assert err.startswith("mattini: error: ") and str(path) in err and "spacing_m" in err, err
    assert "Traceback" not in err and err.count("\n") == 1, err
    assert regio.requests == []
    assert regio.lock_path.read_bytes() == before
