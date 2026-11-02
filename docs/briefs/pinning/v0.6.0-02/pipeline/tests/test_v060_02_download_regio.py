"""Pinning tests for brief v0.6.0-02: `download regio` on 0.6.0's tree (design §1, §6).

Pinned decisions (docs/briefs/v0.6.0-02-download-regio.md, beside M4-01's own in
test_m4_01_download_regio.py):

- *The fit reads the surroundings config.* `lock.fit_problem(lock, datasets, world, area,
  "swissaltiregio")` asks for exactly the tiles `download.regio_tiles` gives with the
  `(margin_m, spacing_m)` that `download.surroundings_settings(area)` reads when it is called
  (brief v0.6.0-01 decision 3): the committed config's 30 for the village; a config with another
  margin, or another spacing, asks for other tiles, so the committed lock is refused naming
  `python -m mattini lock regio` and the tiles the area needs. At a margin of 20 km every
  spacing from 1 to 2000 m gives the same 30 tiles (the east edge lies on a tile edge), so the
  spacing case is 4000 m (measured: 36 tiles, the row N 1064 added, from `2595-1064` on;
  the session's ruling of 2026-11-02). A config the reader refuses ends `download regio` in one
  `mattini: error:` line naming the file, before swisstopo is asked anything, with nothing on
  disk.
- *The republish refusal, word for word:* the terrain's sentence for the tile, ending `then
  design recomputes the expected values in config/surroundings.json (docs/SPEC.md §8)`:
  `download.EXPECTED_CONFIG_NAMES["swissaltiregio"]` is `config/surroundings.json`.
- *A withdrawn item* (HTTP 404) is refused naming the tile and "cannot read the STAC item",
  before any file is fetched.
- *A cut transfer* (brief v0.5.0-10) cut twice is refused naming the tile, the URL, `cut at
  <n> of <size> bytes (after 2 attempts)` and the rerun advice, nothing kept under the file's
  name, no part left, and the rerun the message asks for completes. A whole body with another
  SHA-256 twice is refused `does not match the published`, without the rerun advice.
- *What the owner reads:* one `fetching <url>` line per fetch and then `30 tiles verified, 30
  fetches` on stderr, the provenance path alone on stdout; a second run prints `30 tiles
  verified, 0 fetches`.

Run as the owner runs them, against the local stand-in (local_regio.py, real urllib) through
`python -m mattini download regio`.

Likeliest wrong twins, each caught here: the fit's margin and spacing hard-coded (20000 and 50
fetch the right 30 tiles for the committed config, so only another config tells them apart: a
margin of 0, and a spacing of 4000 m that a spacing hard-coded or halved misses);
the fit's tiles taken from the lock itself; the refusal naming config/terrain.json (the
terrain's dict entry copied); the config read after the first STAC request; a count line in
sheets or files.

Does NOT prove: that the files hold what the surroundings step reads (brief v0.6.0-04); a real
cut of a real swisstopo transfer; a republish after today.
"""

import json

import pytest
from local_regio import VILLAGE_TILES, LocalRegio, regio_name

import mattini.__main__ as cli
from mattini import download, lock
from mattini.datasets import load_datasets
from mattini.world import REPO, load_world

FOLDER = "swissaltiregio/2026-06"
COMMITTED_CONFIG = REPO / "config" / "surroundings.json"
CUT = 100
HINT = "; a dropped connection heals on a rerun: run the command again"


@pytest.fixture
def regio(monkeypatch, tmp_path):
    """The stand-in of test_m4_01_download_regio.py, with a lock pinning what it publishes."""
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


def _config(tmp_path, change):
    """A copy of the committed config/surroundings.json with the village's settings changed."""
    data = json.loads(COMMITTED_CONFIG.read_text(encoding="utf-8"))
    change(data["areas"]["village"])
    path = tmp_path / "surroundings.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _download(site, capsys):
    code = cli.main(["download", "regio", "--out", str(site.out)])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _error(err):
    """The refusal: stderr from its `mattini: error:` line on (progress lines come first)."""
    assert "mattini: error: " in err, err
    return err[err.index("mattini: error: ") :].rstrip("\n")


def _gets(site, path):
    return [r for r in site.file_requests() if r[0] == "GET" and r[1] == path]


def test_the_fit_asks_for_the_tiles_of_the_committed_config(regio):
    world, datasets = load_world(), load_datasets()
    assert lock.fit_problem(regio.pinned, datasets, world, "village", "swissaltiregio") is None
    assert download.EXPECTED_CONFIG_NAMES["swissaltiregio"] == "config/surroundings.json"


def test_the_fit_follows_the_config_s_margin(regio, capsys, monkeypatch, tmp_path):
    monkeypatch.setattr(
        download, "SURROUNDINGS_PATH", _config(tmp_path, lambda v: v.update(margin_m=0))
    )
    world, datasets = load_world(), load_datasets()
    problem = lock.fit_problem(regio.pinned, datasets, world, "village", "swissaltiregio")
    assert problem is not None and "['2615-1094', '2625-1094']" in problem, problem
    assert "`python -m mattini lock regio`" in problem, problem

    code, out, err = _download(regio, capsys)
    assert (code, out) == (1, "")
    assert _error(err) == f"mattini: error: {problem}"
    assert regio.requests == []
    assert not (regio.out / FOLDER).exists()


def test_the_fit_follows_the_config_s_spacing(regio, capsys, monkeypatch, tmp_path):
    monkeypatch.setattr(
        download, "SURROUNDINGS_PATH", _config(tmp_path, lambda v: v.update(spacing_m=4000))
    )
    world, datasets = load_world(), load_datasets()
    problem = lock.fit_problem(regio.pinned, datasets, world, "village", "swissaltiregio")
    assert problem is not None and "2595-1064" in problem and "2645-1064" in problem, problem
    assert "`python -m mattini lock regio`" in problem, problem

    code, out, err = _download(regio, capsys)
    assert (code, out) == (1, "")
    assert _error(err) == f"mattini: error: {problem}"
    assert regio.requests == []
    assert not (regio.out / FOLDER).exists()


def test_a_config_the_reader_refuses_ends_download_regio_before_any_request(
    regio, capsys, monkeypatch, tmp_path
):
    path = _config(tmp_path, lambda v: v.update(spacing_m=50.5))
    monkeypatch.setattr(download, "SURROUNDINGS_PATH", path)
    code, out, err = _download(regio, capsys)
    assert (code, out) == (1, "")
    assert err.startswith("mattini: error: ") and str(path) in err and "spacing_m" in err, err
    assert "Traceback" not in err and err.count("\n") == 1, err
    assert regio.requests == []
    assert not regio.out.exists()


def test_the_republish_refusal_names_design_s_step_word_for_word(regio, capsys):
    tile = VILLAGE_TILES[-1]
    name = regio_name(tile)
    old = regio.regio_entry()["tiles"][tile]["sha256"]
    regio.publish_regio(tile, b"republished bytes")
    new = regio.regio_entry()["tiles"][tile]["sha256"]
    code, out, err = _download(regio, capsys)
    assert (code, out) == (1, "")
    assert _error(err) == (
        f"mattini: error: tile {tile} of area 'village': swisstopo now publishes {name} with "
        f"SHA-256 {new}, the tile lock pins {name} with SHA-256 {old}; nothing was fetched. A "
        f"republished tile is adopted only on purpose: `python -m mattini lock regio`, then "
        f"commit the lock, then design recomputes the expected values in "
        f"config/surroundings.json (docs/SPEC.md §8)"
    )
    assert regio.file_requests() == []


def test_a_withdrawn_item_is_refused_before_any_file_is_fetched(regio, capsys):
    tile = VILLAGE_TILES[12]
    regio.withdraw_regio(tile)
    code, out, err = _download(regio, capsys)
    assert (code, out) == (1, "")
    error = _error(err)
    assert f"tile {tile} of area 'village'" in error and "cannot read the STAC item" in error
    assert regio.file_requests() == []
    assert not (regio.out / FOLDER).exists()


def test_a_transfer_cut_twice_says_so_and_a_rerun_heals_it(regio, capsys):
    tile = VILLAGE_TILES[5]
    name = regio_name(tile)
    path = regio.file_path(name)
    size = len(regio.bodies[name])
    regio.script[path] = [("cut", CUT), ("cut", CUT)]
    code, out, err = _download(regio, capsys)
    assert (code, out) == (1, ""), err
    assert _error(err) == (
        f"mattini: error: tile {tile} of area 'village': {regio.base + path}: fetch failed: "
        f"cut at {CUT} of {size} bytes (after 2 attempts){HINT}"
    )
    assert len(_gets(regio, path)) == 2
    folder = regio.out / FOLDER
    assert not (folder / name).exists() and not (folder / "provenance.json").exists()
    assert list(regio.out.rglob("*.part")) == []

    code, out, err = _download(regio, capsys)  # the rerun the message asks for
    assert (code, out) == (0, f"{folder / 'provenance.json'}\n"), err
    assert (folder / name).read_bytes() == regio.bodies[name]


def test_a_whole_body_with_another_sha256_is_refused_without_the_rerun_advice(regio, capsys):
    tile = VILLAGE_TILES[5]
    path = regio.file_path(regio_name(tile))
    body, content_type, host_sha256 = regio.routes[path]
    regio.routes[path] = (bytes(b ^ 0x20 for b in body), content_type, host_sha256)
    code, _, err = _download(regio, capsys)
    message = _error(err)
    assert code == 1
    assert len(_gets(regio, path)) == 2
    assert f"tile {tile} of area 'village'" in message, message
    assert "does not match the published" in message and "cut at" not in message, message
    assert message.endswith("(after 2 attempts)") and "rerun" not in message, message
    assert not (regio.out / FOLDER / "provenance.json").exists()


def test_the_run_says_what_it_fetched(regio, capsys):
    code, out, err = _download(regio, capsys)
    folder = regio.out / FOLDER
    assert (code, out) == (0, f"{folder / 'provenance.json'}\n"), err
    lines = err.splitlines()
    urls = [regio.base + regio.file_path(regio_name(tile)) for tile in VILLAGE_TILES]
    assert lines == [f"fetching {url}" for url in urls] + ["30 tiles verified, 30 fetches"]

    code, out, err = _download(regio, capsys)
    assert (code, out) == (0, f"{folder / 'provenance.json'}\n"), err
    assert err.splitlines() == ["30 tiles verified, 0 fetches"]
