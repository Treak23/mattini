"""Brief M3-03's own tests of the new commands as the owner runs them.

Pinned decisions (docs/SPEC.md §5, brief M3-03 decisions 1, 2, 5 and 6):

- A Ctrl-C ends any command with one line `mattini: interrupted: `python -m mattini <command>`
  did not finish; run it again`, exit status 130 and no traceback; for `download tlm` the line
  adds that the part is kept and the next run resumes it. (The real signal, sent to a real
  download, is the builder's live run; here the interrupt is raised from the command.)
- A command that needs one `edition` refuses a config that lists `editions`, and the other
  way round, naming config/datasets.json: a refusal, never a traceback, and before any request.
- `lock surface` reads the item of every year in `editions` for every tile (12 items for the
  village); `download surface` reads only the item of the edition the lock pins (6), and the
  photo's and the TLM's commands read their own item(s) only; no lock command asks the file
  host for anything.
- A lock without the dataset's entry, or one that does not fit, ends the download with the
  dataset's own `lock <x>` command before a single request.

test_download_photo_surface_tlm.py and test_lock_photo_surface_tlm.py pin the outcomes; these
pin what the commands ask for and how they end.

Does NOT prove: that a signal reaches a real process (the live run), or the Windows console's
Ctrl-C.
"""

import json
import re
import shutil

import pytest
from local_swisstopo import VILLAGE_TILES, LocalSwisstopo

import mattini.__main__ as cli
from mattini import download, lock
from mattini.datasets import load_datasets
from mattini.world import REPO

COMMITTED_LOCK = REPO / "config" / "datasets.lock.json"


@pytest.fixture
def swisstopo(monkeypatch, tmp_path):
    """The stand-in wired into the command line, and a lock pinning what it publishes."""
    for name in ("http_proxy", "HTTP_PROXY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("no_proxy", "127.0.0.1")
    site = LocalSwisstopo()
    monkeypatch.setattr(download, "STAC_ITEM", site.stac_item)
    site.lock_path = tmp_path / "config" / "datasets.lock.json"
    site.lock_path.parent.mkdir()
    pinned = json.loads(COMMITTED_LOCK.read_bytes())
    pinned["datasets"].update(site.expected_entries())
    site.lock_path.write_text(json.dumps(pinned, indent=2, sort_keys=True), encoding="utf-8")
    monkeypatch.setattr(lock, "LOCK_PATH", site.lock_path)
    site.out = tmp_path / "raw"
    yield site
    site.close()


def _run(capsys, *argv):
    try:
        code = cli.main(list(argv))
    except KeyboardInterrupt:  # pytest would abort its whole run on one that escapes
        pytest.fail(f"a Ctrl-C escaped main() in {argv}")
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _items(site):
    """The STAC item ids requested, in order."""
    return [path.rsplit("/", 1)[1] for _, path, _ in site.requests if path.startswith("/api/stac/")]


# ---------------------------------------------------------------------- Ctrl-C


@pytest.mark.parametrize(
    ("argv", "command"),
    [
        (["lock", "terrain"], "python -m mattini lock terrain"),
        (["lock", "tlm"], "python -m mattini lock tlm"),
        (["download", "photo"], "python -m mattini download photo"),
        (["download", "surface"], "python -m mattini download surface"),
        (["terrain"], "python -m mattini terrain"),
        (["buildings"], "python -m mattini buildings"),
        (["manifest"], "python -m mattini manifest"),
    ],
    ids=[
        "lock-terrain",
        "lock-tlm",
        "download-photo",
        "download-surface",
        "terrain",
        "buildings",
        "manifest",
    ],
)
def test_a_ctrl_c_ends_one_line_with_status_130(monkeypatch, capsys, argv, command):
    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt

    for name in ("_lock", "_download", "_build_terrain", "_build_buildings", "write_manifest"):
        monkeypatch.setattr(cli, name, interrupted)
    code, out, err = _run(capsys, *argv)
    assert (code, out) == (130, "")
    assert err == f"mattini: interrupted: `{command}` did not finish; run it again\n", err


def test_a_ctrl_c_in_download_tlm_says_the_part_is_kept(monkeypatch, capsys):
    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "_download", interrupted)
    code, out, err = _run(capsys, "download", "tlm")
    assert (code, out) == (130, "")
    lines = err.splitlines()
    assert len(lines) == 1 and lines[0].startswith("mattini: interrupted: "), err
    assert "`python -m mattini download tlm` did not finish; run it again" in lines[0], err
    assert "part" in lines[0] and "resumes" in lines[0], err


# ---------------------------------------------------------------------- one edition or several


def _no_network(monkeypatch):
    def refused(url):
        raise AssertionError(f"the test reached for the network: {url}")

    monkeypatch.setattr(download, "urllib_fetch_json", refused)


def _datasets(change):
    datasets = load_datasets()
    change(datasets)
    return datasets


def _lists_editions(name):
    def change(datasets):
        datasets[name]["editions"] = [datasets[name].pop("edition")[:4]]

    return change


def _pins_one_edition(name):
    def change(datasets):
        datasets[name]["edition"] = datasets[name].pop("editions")[0]

    return change


@pytest.mark.parametrize(
    ("argv", "name", "change", "needs"),
    [
        (["lock", "terrain"], "swissalti3d", _lists_editions("swissalti3d"), "one pinned edition"),
        (["lock", "photo"], "swissimage", _lists_editions("swissimage"), "one pinned edition"),
        (["lock", "tlm"], "swisstlm3d", _lists_editions("swisstlm3d"), "one pinned edition"),
        (
            ["lock", "buildings"],
            "swissbuildings3d",
            _lists_editions("swissbuildings3d"),
            "one pinned",
        ),
        (
            ["lock", "surface"],
            "swisssurface3d",
            _pins_one_edition("swisssurface3d"),
            "a list of editions",
        ),
    ],
    ids=["terrain", "photo", "tlm", "buildings", "surface"],
)
def test_the_wrong_kind_of_edition_is_a_refusal_before_any_request(
    monkeypatch, capsys, tmp_path, argv, name, change, needs
):
    _no_network(monkeypatch)
    monkeypatch.setattr(lock, "LOCK_PATH", tmp_path / "datasets.lock.json")
    monkeypatch.setattr(cli, "load_datasets", lambda: _datasets(change))
    code, out, err = _run(capsys, *argv)
    assert (code, out) == (1, "")
    assert err.startswith(f"mattini: error: config/datasets.json: dataset '{name}' "), err
    assert needs in err and "Traceback" not in err, err
    assert not (tmp_path / "datasets.lock.json").exists()


def test_raw_folder_is_the_edition_or_the_editions_joined():
    datasets = load_datasets()
    assert [download.raw_folder(datasets, name) for name in sorted(datasets)] == [
        "2024",  # swissalti3d
        "2020",  # swissbuildings3d
        "2023",  # swissimage
        "2021-2022",  # swisssurface3d
        "2026-02",  # swisstlm3d
    ]


# ---------------------------------------------------------------------- what is asked for


def test_lock_surface_reads_both_years_of_every_tile_and_no_file(swisstopo, capsys):
    shutil.copyfile(COMMITTED_LOCK, swisstopo.lock_path)
    swisstopo.requests.clear()
    code, _, err = _run(capsys, "lock", "surface")
    assert code == 0, err
    items = _items(swisstopo)
    wanted = [f"swisssurface3d-raster_{y}_{t}" for t in VILLAGE_TILES for y in ("2021", "2022")]
    assert items == wanted
    assert swisstopo.file_requests() == []


def test_download_surface_reads_only_the_items_the_lock_pins(swisstopo, capsys):
    swisstopo.publish_surface("2624-1096", "2022", b"an edition published after the lock")
    swisstopo.requests.clear()
    code, _, err = _run(capsys, "download", "surface", "--out", str(swisstopo.out))
    assert code == 0, err
    items = _items(swisstopo)
    assert items == [
        f"swisssurface3d-raster_{'2022' if tile == '2623-1095' else '2021'}_{tile}"
        for tile in VILLAGE_TILES
    ]
    assert not any(re.search(r"2022_2624-1096$", item) for item in items)


def test_download_photo_and_tlm_read_their_own_items_only(swisstopo, capsys):
    swisstopo.requests.clear()
    assert _run(capsys, "download", "photo", "--out", str(swisstopo.out))[0] == 0
    assert _items(swisstopo) == [f"swissimage-dop10_2023_{tile}" for tile in VILLAGE_TILES]
    swisstopo.requests.clear()
    assert _run(capsys, "download", "tlm", "--out", str(swisstopo.out))[0] == 0
    assert _items(swisstopo) == ["swisstlm3d_2026-02"]


@pytest.mark.parametrize(
    ("command", "dataset", "lock_command"),
    [
        ("photo", "swissimage", "python -m mattini lock photo"),
        ("surface", "swisssurface3d", "python -m mattini lock surface"),
        ("tlm", "swisstlm3d", "python -m mattini lock tlm"),
    ],
)
@pytest.mark.parametrize("damage", ["missing", "edition"])
def test_a_lock_that_does_not_fit_ends_the_download_before_any_request(
    swisstopo, capsys, command, dataset, lock_command, damage
):
    pinned = json.loads(swisstopo.lock_path.read_bytes())
    if damage == "missing":
        del pinned["datasets"][dataset]
    elif dataset == "swisssurface3d":
        pinned["datasets"][dataset]["tiles"]["2624-1096"]["edition"] = "2019"
    else:
        pinned["datasets"][dataset]["collection"] = "ch.swisstopo.elsewhere"
    swisstopo.lock_path.write_text(json.dumps(pinned, indent=2, sort_keys=True), encoding="utf-8")
    swisstopo.requests.clear()
    code, out, err = _run(capsys, "download", command, "--out", str(swisstopo.out))
    assert (code, out) == (1, "")
    assert err.startswith("mattini: error: "), err
    assert f"`{lock_command}`" in err, err
    assert swisstopo.requests == [] and not swisstopo.out.exists()
    if dataset == "swisstlm3d":
        assert err.startswith("mattini: error: swisstlm3d 2026-02: "), err
