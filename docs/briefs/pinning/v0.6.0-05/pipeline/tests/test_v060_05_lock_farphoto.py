"""Pinning tests for brief v0.6.0-05: `python -m mattini lock farphoto` (design §2, SPEC §5).

Pinned decisions:

- The lock's `swissimage_far` entry is exactly {absent, collection, edition, resolution_m,
  tiles: {<tile>: {file, sha256}}}: `tiles` every cell of the surroundings box
  (`download.area_farphoto_cells`, test_v060_05_farphoto_cells.py) whose item
  `swissimage-dop10_<edition>_<cell>` exists, with the one asset ending `_2_2056.tif` (the
  10 cm asset of the same item is not it); `absent` every other cell, a sorted list of
  distinct tile ids, none of them in `tiles`. A cell is absent only when its item answers
  HTTP 404; any other failure to read it is "cannot read the STAC item" naming the tile, and
  nothing is written.
- Written only by `python -m mattini lock farphoto`, from the STAC items only (no request to
  the file host, not even a HEAD), replacing its own entry and keeping every other; the file
  stays sorted, 2-space indented, UTF-8, LF, final newline; a second run writes the same bytes.
- Every item's `properties.datetime` must lie in the pinned edition (it starts with
  `<edition>-`); else it is refused naming the tile, its datetime and the edition, and
  nothing is written.
- `file:checksum` comes in upper-case hex; the lock stores lower-case.
- The reads run in parallel, `download.FARPHOTO_WORKERS` (8) at once (the session's decision:
  1806 items, about 75 s live instead of 22 minutes), each cell asked once; the entry's order
  does not depend on the order the answers arrive in.
- The config the cells come from is read before swisstopo is asked anything: a config the
  reader refuses ends `lock farphoto` in one `mattini: error:` line naming the file, with no
  request and the lock unchanged.
- `lock.validate_lock` knows the entry; a malformed one is refused naming the file and
  `python -m mattini lock farphoto` among the seven lock commands.
- `lock.fit_problem(lock, datasets, world, area, "swissimage_far")`: the entry is for the
  config's collection, edition and resolution, and its tiles and its absent cells together
  are exactly the area's cells, none in both; else the refusal names the area and `python -m
  mattini lock farphoto` and no other command.

Run as the owner runs them, against the local stand-in (local_farphoto.py) through the real
urllib code; `download.STAC_ITEM`, `download.SURROUNDINGS_PATH` (a copy of the committed
config with `margin_m` 1000: 20 cells, 3 absent) and `lock.LOCK_PATH` are patched.

Likeliest wrong twins, each caught here: the 10 cm asset locked (the photo's suffix); a server
error taken for an absent cell; the absent cells not recorded (a new item would be adopted
silently); the edition not checked; the lock written with this entry alone; the reads one at
a time; the checksum stored as published.

Does NOT prove: that the live STAC API serves these items today (test_v060_05_measured_farphoto.py
and the network test do).
"""

import copy
import json
import shutil
import threading

import pytest
from local_farphoto import ABSENT, LocalFarphoto, cells_of, far_name
from local_swisstopo import PHOTO

import mattini.__main__ as cli
from mattini import download, lock
from mattini.datasets import load_datasets
from mattini.world import REPO, load_world

COMMITTED_LOCK = REPO / "config" / "datasets.lock.json"
COMMITTED_CONFIG = REPO / "config" / "surroundings.json"
LOCK_COMMAND = "python -m mattini lock farphoto"


def _config(tmp_path, **settings):
    data = json.loads(COMMITTED_CONFIG.read_text(encoding="utf-8"))
    data["areas"]["village"].update(settings)
    path = tmp_path / "surroundings.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


@pytest.fixture
def far(monkeypatch, tmp_path):
    """The stand-in wired into the command line; the lock is a copy of the committed one."""
    for name in ("http_proxy", "HTTP_PROXY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("no_proxy", "127.0.0.1")
    site = LocalFarphoto()
    monkeypatch.setattr(download, "STAC_ITEM", site.stac_item)
    monkeypatch.setattr(download, "SURROUNDINGS_PATH", _config(tmp_path, margin_m=1000))
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


def test_lock_farphoto_writes_its_exact_entry_and_keeps_every_other(far, capsys):
    expected = json.loads(COMMITTED_LOCK.read_bytes())
    expected["datasets"].pop("swissimage_far", None)  # a lock farphoto already wrote, replaced
    expected["datasets"]["swissimage_far"] = far.far_entry()
    code, out, err = _run(capsys, "lock", "farphoto")
    assert (code, out) == (0, f"{far.lock_path}\n"), err
    assert far.lock_path.read_bytes() == _text(expected)
    entry = expected["datasets"]["swissimage_far"]
    assert entry["absent"] == list(ABSENT) and len(entry["tiles"]) == 17
    assert list(entry["tiles"]) == [c for c in cells_of(1000) if c not in ABSENT]
    assert all(t["file"].endswith("_2_2056.tif") for t in entry["tiles"].values())
    assert all(t["sha256"] == t["sha256"].lower() for t in entry["tiles"].values())
    assert far.file_requests() == []  # STAC only: no file, no HEAD
    asked = sorted(path.rsplit("_", 1)[1] for path in _item_requests(far))
    assert asked == sorted(cells_of(1000))  # every cell once, no other


def test_a_second_run_writes_the_same_bytes(far, capsys):
    assert _run(capsys, "lock", "farphoto")[0] == 0
    first = far.lock_path.read_bytes()
    assert _run(capsys, "lock", "farphoto")[0] == 0
    assert far.lock_path.read_bytes() == first


def test_a_new_item_and_a_vanished_one_change_the_entry(far, capsys):
    far.publish_far("2625-1094", b"a new 2 m tile in a cell that had none")
    far.withdraw_far("2622-1098")
    code, _, err = _run(capsys, "lock", "farphoto")
    assert code == 0, err
    entry = json.loads(far.lock_path.read_bytes())["datasets"]["swissimage_far"]
    assert entry["absent"] == ["2622-1098", "2624-1094", "2625-1095"]
    assert "2625-1094" in entry["tiles"] and "2622-1098" not in entry["tiles"]
    assert entry == far.far_entry()


@pytest.mark.parametrize(
    "datetime", ["2024-01-01T00:00:00Z", "2020-01-01T00:00:00Z", "2022-12-31T23:59:59Z"]
)
def test_an_item_of_another_edition_is_refused_and_nothing_is_written(far, capsys, datetime):
    before = far.lock_path.read_bytes()
    far.publish_far("2623-1098", b"another flight", datetime=datetime)
    code, out, err = _run(capsys, "lock", "farphoto")
    assert (code, out) == (1, "")
    error = _error(err)
    assert "2623-1098" in error and datetime in error and "'2023'" in error, error
    assert far.lock_path.read_bytes() == before
    assert far.file_requests() == []


@pytest.mark.parametrize("status", [500, 403, 503])
def test_a_server_error_is_not_an_absent_cell(far, capsys, status):
    before = far.lock_path.read_bytes()
    far.script[far.item_path(PHOTO, "swissimage-dop10_2023_2622-1094")] = [("status", status)]
    code, out, err = _run(capsys, "lock", "farphoto")
    assert (code, out) == (1, "")
    error = _error(err)
    assert "2622-1094" in error and "cannot read the STAC item" in error, error
    assert far.lock_path.read_bytes() == before


def test_the_reads_run_eight_at_once(far, capsys, monkeypatch):
    assert download.FARPHOTO_WORKERS == 8
    gate, calls, count = threading.Barrier(8, timeout=10), [], threading.Lock()
    real = download.urllib_fetch_json

    def fetch_json(url):
        with count:
            calls.append(url)
            first = len(calls) <= 8
        if first:
            gate.wait()  # BrokenBarrierError unless eight reads are under way together
        return real(url)

    monkeypatch.setattr(download, "urllib_fetch_json", fetch_json)
    code, _, err = _run(capsys, "lock", "farphoto")
    assert code == 0, err
    assert sorted(calls) == sorted(set(calls)) and len(calls) == 20
    entry = json.loads(far.lock_path.read_bytes())["datasets"]["swissimage_far"]
    assert entry == far.far_entry()


def test_lock_farphoto_takes_the_config_s_margin(far, capsys, monkeypatch, tmp_path):
    monkeypatch.setattr(download, "SURROUNDINGS_PATH", _config(tmp_path, margin_m=0))
    code, _, err = _run(capsys, "lock", "farphoto")
    assert code == 0, err
    entry = json.loads(far.lock_path.read_bytes())["datasets"]["swissimage_far"]
    assert entry["absent"] == [] and list(entry["tiles"]) == cells_of(0)


def test_lock_farphoto_refuses_a_bad_config_before_any_request(far, capsys, monkeypatch, tmp_path):
    before = far.lock_path.read_bytes()
    path = _config(tmp_path, margin_m=1000.0)
    monkeypatch.setattr(download, "SURROUNDINGS_PATH", path)
    code, out, err = _run(capsys, "lock", "farphoto")
    assert (code, out) == (1, "")
    assert err.startswith("mattini: error: ") and str(path) in err and "margin_m" in err, err
    assert "Traceback" not in err and err.count("\n") == 1, err
    assert far.requests == []
    assert far.lock_path.read_bytes() == before


# ------------------------------------------------------------------------ the lock's shape


def _entry():
    return {
        "absent": ["2624-1094", "2625-1094"],
        "collection": "ch.swisstopo.swissimage-dop10",
        "edition": "2023",
        "resolution_m": 2,
        "tiles": {
            "2603-1088": {
                "file": "swissimage-dop10_2023_2603-1088_2_2056.tif",
                "sha256": "826dc2299fe0957c70daf31f9612bdad76c2a0c308a49ff4766343493a371013",
            }
        },
    }


def _load(tmp_path, entry):
    data = json.loads(COMMITTED_LOCK.read_bytes())
    data["datasets"]["swissimage_far"] = entry
    path = tmp_path / "datasets.lock.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path, data


def test_a_well_formed_entry_is_accepted(tmp_path):
    path, data = _load(tmp_path, _entry())
    assert lock.load_lock(path) == data
    path, data = _load(tmp_path, dict(_entry(), absent=[]))
    assert lock.load_lock(path) == data


@pytest.mark.parametrize(
    "change, complaint",
    [
        (lambda e: e.pop("absent"), "exactly the keys"),
        (lambda e: e.pop("resolution_m"), "exactly the keys"),
        (lambda e: e.update(absent="2624-1094"), "absent"),
        (lambda e: e.update(absent=["2625-1094", "2624-1094"]), "absent"),
        (lambda e: e.update(absent=["2624-1094", "2624-1094"]), "absent"),
        (lambda e: e.update(absent=["2624-1094", "x-1"]), "absent"),
        (lambda e: e.update(absent=["2624-1094", 2625]), "absent"),
        (lambda e: e.update(absent=["2603-1088", "2624-1094"]), "2603-1088"),
        (lambda e: e["tiles"]["2603-1088"].update(sha256="AB" * 32), "lower-case"),
    ],
)
def test_a_malformed_entry_is_refused_naming_lock_farphoto(tmp_path, change, complaint):
    entry = _entry()
    change(entry)
    path, _ = _load(tmp_path, entry)
    with pytest.raises(lock.LockError) as refusal:
        lock.load_lock(path)
    message = str(refusal.value)
    assert "swissimage_far" in message and complaint in message, message
    assert f"`{LOCK_COMMAND}`" in message, message
    assert download.LOCK_COMMAND_OF["swissimage_far"] == LOCK_COMMAND


# ------------------------------------------------------------------------------- the fit


def _fit_lock():
    data = json.loads(COMMITTED_LOCK.read_bytes())
    cells = download.farphoto_cells(load_world(), "village", margin_m=1000)
    data["datasets"]["swissimage_far"] = {
        "absent": list(ABSENT),
        "collection": "ch.swisstopo.swissimage-dop10",
        "edition": "2023",
        "resolution_m": 2,
        "tiles": {
            cell: {"file": far_name(cell), "sha256": "0" * 64}
            for cell in cells
            if cell not in ABSENT
        },
    }
    return data


def _fit(data):
    return lock.fit_problem(data, load_datasets(), load_world(), "village", "swissimage_far")


def _far(data):
    return data["datasets"]["swissimage_far"]


@pytest.mark.parametrize(
    "change, words",
    [
        (
            lambda d: d["datasets"].pop("swissimage_far"),
            "has no 'swissimage_far' entry",
        ),
        (lambda d: _far(d).update(collection="ch.swisstopo.x"), "collection"),
        (lambda d: _far(d).update(edition="2020"), "edition"),
        (lambda d: _far(d).update(resolution_m=0.1), "resolution_m"),
        (lambda d: _far(d)["tiles"].pop("2622-1094"), "2622-1094"),
        (lambda d: _far(d)["absent"].remove("2625-1095"), "2625-1095"),
        (lambda d: _far(d)["absent"].append("2626-1094"), "2626-1094"),
        (
            lambda d: _far(d)["tiles"].update({"2621-1094": {"file": "f.tif", "sha256": "0" * 64}}),
            "2621-1094",
        ),
        (lambda d: _far(d)["absent"].append("2622-1094"), "2622-1094"),
        (lambda d: _far(d).pop("absent"), "absent"),
    ],
)
def test_a_lock_that_does_not_fit_is_refused_naming_lock_farphoto(
    monkeypatch, tmp_path, change, words
):
    monkeypatch.setattr(download, "SURROUNDINGS_PATH", _config(tmp_path, margin_m=1000))
    data = _fit_lock()
    assert _fit(data) is None
    broken = copy.deepcopy(data)
    change(broken)
    problem = _fit(broken)
    assert problem is not None and words in problem, problem
    assert "(area 'village')" in problem and f"`{LOCK_COMMAND}`" in problem, problem
    others = [c for c in lock.LOCK_COMMANDS if c != LOCK_COMMAND]
    assert not any(c in problem for c in others), problem


def test_the_fit_follows_the_config_s_margin(monkeypatch, tmp_path):
    monkeypatch.setattr(download, "SURROUNDINGS_PATH", _config(tmp_path, margin_m=1000))
    data = _fit_lock()
    assert _fit(data) is None
    monkeypatch.setattr(download, "SURROUNDINGS_PATH", _config(tmp_path, margin_m=0))
    problem = _fit(data)
    assert problem is not None and f"`{LOCK_COMMAND}`" in problem, problem
    assert download.EXPECTED_CONFIG_NAMES["swissimage_far"] == "config/surroundings.json"
