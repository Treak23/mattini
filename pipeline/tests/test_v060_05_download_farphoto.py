"""Pinning tests for brief v0.6.0-05: `python -m mattini download farphoto` (design §2, SPEC §5).

Pinned decisions (the flow of `download regio`, brief v0.6.0-02, for the far photo):

- First `lock.fit_problem` (collection, edition, resolution; the tiles and the absent cells
  together exactly the area's cells), naming `python -m mattini lock farphoto` and no other
  command, before swisstopo is asked anything; a config the reader refuses ends the command in
  one `mattini: error:` line naming the file, before any request, nothing on disk.
- Then every cell's item, all before any request for a file and before anything on disk
  changes: a pinned tile's published name and SHA-256 must be the lock's (the terrain's
  republish sentence, word for word, ending `then design recomputes the expected values in
  config/surroundings.json (docs/SPEC.md §8)`); a cell the lock records as absent must still
  answer 404 (**a new item is refused**, naming the tile, its file, "nothing was fetched",
  `python -m mattini lock farphoto`, "then commit the lock" and config/surroundings.json); a
  pinned tile whose item answers 404 is refused the same way (**a vanished item**); an item
  of another edition is refused naming the tile and its datetime. Without these the colour
  step would read a coverage the expected values were not computed for.
- Then the files: `<file>.part`, verified, renamed, one retry, a verified file kept (the shared
  `_fetch_verified`: a transfer cut once heals); `FARPHOTO_WORKERS` (8) fetches at once.
- `swissimage_far/2023/provenance.json`: the terrain's keys and `absent`, {absent,
  attribution, collection, dataset, edition, resolution_m, schema: 1, tiles: [{file, item,
  sha256, size_bytes, tile, url}] in the lock's order}, sorted keys, 2-space indent, UTF-8, LF,
  a final newline, no times, no paths; removed before the first change on disk.
- What the owner reads: one `fetching <url>` line per fetch (in the order the fetches start,
  which is not fixed), then `<n> tiles verified, <f> fetches, <a> cells without an item` on
  stderr, the provenance path alone on stdout; a second run fetches nothing.

Run as the owner runs them, against the local stand-in (local_farphoto.py, real urllib, the
`margin_m` 1000 box: 20 cells, 17 with an item) through `python -m mattini download farphoto`;
re-cut by brief v0.6.0-07: the config comes from `surroundings.load_surroundings_config`, its one
reader, patched on its module (no longer `download.SURROUNDINGS_PATH`).

Likeliest wrong twins, each caught here: the absent cells not read again at download (a new
item adopted silently by the next lock); the vanished item taken for an absent cell; the lock
compared lazily while fetching; the fetches one at a time; the provenance without `absent`;
the folder without the edition; the refusal naming the photo's configs.

Does NOT prove: that the files hold what the colour step reads (brief v0.6.0-06); a real cut of
a real transfer; a republish after today.
"""

import json
import threading

import pytest
from local_farphoto import ABSENT, LocalFarphoto, cells_of, far_name

import mattini.__main__ as cli
from mattini import download, lock, surroundings
from mattini.world import REPO

FOLDER = "swissimage_far/2023"
COMMITTED_CONFIG = REPO / "config" / "surroundings.json"
LOCK_COMMAND = "python -m mattini lock farphoto"
STEP = "then design recomputes the expected values in config/surroundings.json (docs/SPEC.md §8)"
PRESENT = [cell for cell in cells_of(1000) if cell not in ABSENT]


def _use_config(monkeypatch, path):
    """The command line's surroundings config: `surroundings.load_surroundings_config`, its one
    reader (brief v0.6.0-07), replaced on its module by one that reads `path` with the real
    reader; a refusal is the reader's own, naming `path`."""
    real = surroundings.load_surroundings_config
    monkeypatch.setattr(surroundings, "load_surroundings_config", lambda *a, **k: real(path))


def _config(tmp_path, **settings):
    data = json.loads(COMMITTED_CONFIG.read_text(encoding="utf-8"))
    data["areas"]["village"].update(settings)
    path = tmp_path / "surroundings.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


@pytest.fixture
def far(monkeypatch, tmp_path):
    """The stand-in with a lock pinning what it publishes over the 1000 m box."""
    for name in ("http_proxy", "HTTP_PROXY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("no_proxy", "127.0.0.1")
    site = LocalFarphoto()
    monkeypatch.setattr(download, "STAC_ITEM", site.stac_item)
    _use_config(monkeypatch, _config(tmp_path, margin_m=1000))
    site.lock_path = tmp_path / "config" / "datasets.lock.json"
    site.lock_path.parent.mkdir()
    site.pinned = json.loads((REPO / "config" / "datasets.lock.json").read_bytes())
    site.pinned["datasets"]["swissimage_far"] = site.far_entry()
    site.lock_path.write_text(json.dumps(site.pinned, indent=2, sort_keys=True), "utf-8")
    monkeypatch.setattr(lock, "LOCK_PATH", site.lock_path)
    site.out = tmp_path / "raw"
    yield site
    site.close()


def _download(site, capsys):
    code = cli.main(["download", "farphoto", "--out", str(site.out)])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _error(err):
    """The refusal: stderr from its `mattini: error:` line on (progress lines come first)."""
    assert "mattini: error: " in err, err
    return err[err.index("mattini: error: ") :].rstrip("\n")


def _gets(site, path):
    return [r for r in site.file_requests() if r[0] == "GET" and r[1] == path]


def _provenance(site):
    entry = site.far_entry()
    tiles = []
    for cell, pinned in entry["tiles"].items():
        item = f"swissimage-dop10_2023_{cell}"
        tiles.append(
            {
                "file": pinned["file"],
                "item": item,
                "sha256": pinned["sha256"],
                "size_bytes": len(site.bodies[pinned["file"]]),
                "tile": cell,
                "url": site.base + site.file_path(pinned["file"]),
            }
        )
    data = {
        "absent": entry["absent"],
        "attribution": "© swisstopo",
        "collection": "ch.swisstopo.swissimage-dop10",
        "dataset": "swissimage_far",
        "edition": "2023",
        "resolution_m": 2,
        "schema": 1,
        "tiles": tiles,
    }
    return (json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def test_download_fetches_verifies_and_records(far, capsys):
    code, out, err = _download(far, capsys)
    folder = far.out / FOLDER
    assert (code, out) == (0, f"{folder / 'provenance.json'}\n"), err
    assert sorted(p.name for p in folder.iterdir()) == sorted(
        [far_name(cell) for cell in PRESENT] + ["provenance.json"]
    )
    for cell in PRESENT:
        assert (folder / far_name(cell)).read_bytes() == far.bodies[far_name(cell)]
    assert (folder / "provenance.json").read_bytes() == _provenance(far)
    assert list(far.out.rglob("*.part")) == []
    decoys = [r for r in far.file_requests() if "_0.1_2056.tif" in r[1]]
    assert decoys == [] and all(r[0] == "GET" for r in far.file_requests())


def test_the_run_says_what_it_fetched(far, capsys):
    code, out, err = _download(far, capsys)
    folder = far.out / FOLDER
    assert (code, out) == (0, f"{folder / 'provenance.json'}\n"), err
    lines = err.splitlines()
    urls = [far.base + far.file_path(far_name(cell)) for cell in PRESENT]
    assert sorted(lines[:-1]) == sorted(f"fetching {url}" for url in urls)
    assert lines[-1] == "17 tiles verified, 17 fetches, 3 cells without an item"

    before = (folder / "provenance.json").read_bytes()
    code, out, err = _download(far, capsys)
    assert (code, out) == (0, f"{folder / 'provenance.json'}\n"), err
    assert err.splitlines() == ["17 tiles verified, 0 fetches, 3 cells without an item"]
    assert (folder / "provenance.json").read_bytes() == before


def test_a_new_item_in_an_absent_cell_is_refused_before_anything_is_fetched(far, capsys):
    far.publish_far("2625-1094", b"a new 2 m tile")
    code, out, err = _download(far, capsys)
    assert (code, out) == (1, "")
    error = _error(err)
    for words in (
        "2625-1094",
        far_name("2625-1094"),
        "nothing was fetched",
        f"`{LOCK_COMMAND}`, then commit the lock",
        STEP,
    ):
        assert words in error, (words, error)
    assert far.file_requests() == []
    assert not (far.out / FOLDER).exists()


def test_a_vanished_item_is_refused_before_anything_is_fetched(far, capsys):
    far.withdraw_far("2623-1098")
    code, out, err = _download(far, capsys)
    assert (code, out) == (1, "")
    error = _error(err)
    for words in (
        "tile 2623-1098 of area 'village'",
        far_name("2623-1098"),
        "nothing was fetched",
        f"`{LOCK_COMMAND}`, then commit the lock",
        STEP,
    ):
        assert words in error, (words, error)
    assert far.file_requests() == []
    assert not (far.out / FOLDER).exists()


def test_the_republish_refusal_names_design_s_step_word_for_word(far, capsys):
    cell = PRESENT[-1]
    name = far_name(cell)
    old = far.far_entry()["tiles"][cell]["sha256"]
    far.publish_far(cell, b"republished bytes")
    new = far.far_entry()["tiles"][cell]["sha256"]
    code, out, err = _download(far, capsys)
    assert (code, out) == (1, "")
    assert _error(err) == (
        f"mattini: error: tile {cell} of area 'village': swisstopo now publishes {name} with "
        f"SHA-256 {new}, the tile lock pins {name} with SHA-256 {old}; nothing was fetched. A "
        f"republished tile is adopted only on purpose: `{LOCK_COMMAND}`, then commit the "
        f"lock, {STEP}"
    )
    assert far.file_requests() == []


@pytest.mark.parametrize("datetime", ["2024-01-01T00:00:00Z", "2017-01-01T00:00:00Z"])
def test_an_item_of_another_edition_is_refused_before_anything_is_fetched(far, capsys, datetime):
    cell = PRESENT[3]
    far.publish_far(cell, far.bodies[far_name(cell)], datetime=datetime)
    code, out, err = _download(far, capsys)
    assert (code, out) == (1, "")
    error = _error(err)
    assert cell in error and datetime in error, error
    assert far.file_requests() == []


@pytest.mark.parametrize(
    "change, words",
    [
        (lambda e: e["tiles"].pop("2622-1094"), "2622-1094"),
        (lambda e: e["absent"].remove("2625-1095"), "2625-1095"),
        (lambda e: e.update(resolution_m=0.1), "resolution_m"),
        (lambda e: e.update(edition="2020"), "edition"),
    ],
)
def test_a_lock_that_does_not_fit_is_refused_naming_lock_farphoto(far, capsys, change, words):
    change(far.pinned["datasets"]["swissimage_far"])
    far.lock_path.write_text(json.dumps(far.pinned, indent=2, sort_keys=True), "utf-8")
    code, out, err = _download(far, capsys)
    assert (code, out) == (1, "")
    error = _error(err)
    assert words in error and f"`{LOCK_COMMAND}`" in error, error
    assert far.requests == []
    assert not far.out.exists()


def test_the_fit_follows_the_config_s_margin(far, capsys, monkeypatch, tmp_path):
    _use_config(monkeypatch, _config(tmp_path, margin_m=0))
    code, out, err = _download(far, capsys)
    assert (code, out) == (1, "")
    assert f"`{LOCK_COMMAND}`" in _error(err)
    assert far.requests == []


def test_a_config_the_reader_refuses_ends_download_farphoto_before_any_request(
    far, capsys, monkeypatch, tmp_path
):
    path = _config(tmp_path, margin_m="1000")
    _use_config(monkeypatch, path)
    code, out, err = _download(far, capsys)
    assert (code, out) == (1, "")
    assert err.startswith("mattini: error: ") and str(path) in err and "margin_m" in err, err
    assert "Traceback" not in err and err.count("\n") == 1, err
    assert far.requests == []
    assert not far.out.exists()


def test_a_cut_transfer_is_fetched_once_more_through_a_part_file(far, capsys):
    cell = PRESENT[5]
    path = far.file_path(far_name(cell))
    far.script[path] = [("cut", 50)]
    code, _, err = _download(far, capsys)
    assert code == 0, err
    assert len(_gets(far, path)) == 2
    folder = far.out / FOLDER
    assert (folder / far_name(cell)).read_bytes() == far.bodies[far_name(cell)]
    assert list(far.out.rglob("*.part")) == []


def test_a_damaged_file_on_disk_is_fetched_again_and_a_verified_one_kept(far, capsys):
    assert _download(far, capsys)[0] == 0
    folder = far.out / FOLDER
    damaged = folder / far_name(PRESENT[0])
    damaged.write_bytes(b"damaged")
    far.requests.clear()
    code, _, err = _download(far, capsys)
    assert code == 0, err
    assert [r[1] for r in far.file_requests()] == [far.file_path(far_name(PRESENT[0]))]
    assert damaged.read_bytes() == far.bodies[far_name(PRESENT[0])]
    assert (folder / "provenance.json").read_bytes() == _provenance(far)


def test_the_fetches_run_eight_at_once(far, capsys, monkeypatch):
    gate, calls, count = threading.Barrier(8, timeout=10), [], threading.Lock()
    real = download.urllib_fetch_file

    def fetch_file(url, dest):
        with count:
            calls.append(url)
            first = len(calls) <= 8
        if first:
            gate.wait()  # BrokenBarrierError unless eight fetches are under way together
        real(url, dest)

    monkeypatch.setattr(download, "urllib_fetch_file", fetch_file)
    code, _, err = _download(far, capsys)
    assert code == 0, err
    assert len(calls) == 17
    assert (far.out / FOLDER / "provenance.json").read_bytes() == _provenance(far)
