"""Guards of brief v0.6.0-05 the pinned tests leave open (decision 14; the batch gate's prover).

The pinned copies run `lock farphoto` and `download farphoto` against a stand-in in which at most
one cell fails at a time, and they bound the reads and fetches from below (a barrier of eight).
This file closes what they leave, by the class and not by the instance (lesson 9): the parallel
runner `download._in_parallel`, and two guards of the lock's entry and fit that a well-formed
lock never tests.

- *Which refusal is raised* (the prover's E3, decision 14). When several items fail, the one
  raised is the first in item order, whatever order the calls end in and whichever of the two
  refusal kinds it is (a DownloadError, or the OSError a file-system call raises inside a fetch):
  a later item that fails first must not be the one the owner reads. Held by the runner on its
  own, and through both commands with two cells published in another edition's datetime
  (2623-1098 and 2625-1098: the error names 2623-1098, the earlier cell, held back until the
  later one has failed).
- *Nothing is started after a refusal* (E2): once an item has failed, an item after it is not
  started, whichever kind the refusal is, so a refused run does not go on asking swisstopo for
  the rest of its 1806 items or 1220 files.
- *The OSError of a worker is a refusal in item order* (E24): removing it from what the runner
  catches lets the OSError of a later item overtake the DownloadError of an earlier one.
- *The upper bound of the concurrency* (E27): `FARPHOTO_WORKERS` is a width and not only a
  constant: no more than that many reads or fetches run at once, held for the runner with a
  width of three, for the STAC reads and for the file fetches (the pins hold the lower bound,
  and the constant). A pool wider than eight asks swisstopo for 64 files at once.
- *The fit is total* (E21): `lock.fit_problem` takes any lock object and answers with its
  refusal text; an `absent` that holds anything but tile ids (a number, a null, a list) is
  "has no absent list of tile ids", never a TypeError on the way to another refusal.
  `validate_lock` refuses the same lock, but the fit does not rely on it having run.
- *`absent` is sorted by the entry, not by luck* (E6): the cells are east outer and north inner,
  which for LV95's four-digit kilometres is also the sorted order, so a mutation that drops
  `sorted()` is equivalent for the village. The tile rule may move (brief v0.6.0-07) and take
  another order with it; the lock's entry must stay what `validate_lock` accepts, sorted and
  without repeats, whatever order the cells arrive in.
- *What the docstrings say the edition refusal names* (the review's F1, Hard Rule 2). The two
  docstrings that list the refusals of `download farphoto` promised that one of another edition
  names `lock farphoto` and config/surroundings.json; it names the cell, the datetime and the
  edition only (`_published_asset`, raised before the lock is looked at). Each docstring's
  clause about another edition says exactly what the refusal does: with a remedy if the error
  names one, without if it does not, so the words and the code move together.

The second fixer round (the prover's findings on the pinned gates; decision 14 again):

- *Only an HTTP 404 is an absent cell* (X12). The pins try three server errors on one cell of
  `lock farphoto`; here every other way an item can fail to be read (a refused, reset or
  timed-out connection, a server that hangs up, a cut or undecodable body, and the HTTP
  statuses 400 to 504 that a reverse proxy or a rate limit gives) is "cannot read the STAC
  item" naming the cell, for a pinned cell and for an absent one, under `lock farphoto` (the
  lock unchanged: a passing outage must never lock a cell as Italy) and under `download
  farphoto` (nothing fetched, nothing on disk).
- *The truncation of the fit's refusals* (X34): at most six cells are listed, then "and N more",
  at the boundary (six, seven) and at the 1794 a margin changed to 0 puts beside the lock.
- *The runner cancels what has not started* (decision 7's second half): a failure that is no
  refusal (a bug, a Ctrl-C) ends the run without starting the items still waiting.
- *The words of `--help`* (decision 8): the clauses for `farphoto` and `regio` say what each
  reads (the resolution, the cell size, the margin and whether a spacing, the config file).
- *Layers that cover one another* (X7, X33): `validate_lock` refuses an `absent` that is not a
  list; `fit_problem` refuses a files object that is not an object for every dataset, and
  never raises; `download farphoto` names a resolution no one can use before it asks the lock
  or swisstopo anything.
- *The live check's offline twin* (the network test is deselected by the gate, and the sample it
  reads leaves cells unread): the committed lock is replayed through the real code for all 1806
  cells with the real item URL form (`download.STAC_ITEM` not patched), and what the two live
  fetchers send (`Accept`, `User-Agent`, a timeout; HEAD's two headers) is held without a network.
- *The records follow the config*: with another collection, edition, resolution and credit in
  the datasets config, the lock's entry and provenance.json carry those, not the committed
  values; and the refusals of a new and of a vanished item name the file and the checksum.

Run as the owner runs the commands, against the local stand-in (local_farphoto.py, real urllib,
the `margin_m` 1000 box: 20 cells, 17 with an item), except the runner's own tests, which call
`download._in_parallel` with plain functions and events, the fit tests, which call
`lock.fit_problem` on the committed lock's entry, and the replay and fetcher tests, which hand
the code a fake item reader or `urlopen`. No sleep decides whether a correct run passes: the
holds in `Meter` only make a pool that is too wide overlap, the wait of 0.3 s only bounds how
long a correct run waits for a call that must not come, and the 0.5 s of the cancel test only keeps
both workers busy while the run is cancelled.

Does NOT prove: that a runner of another make (a pool that is not `ThreadPoolExecutor`) keeps
these properties; the order of the refusals when the calls that fail are not all started (the
skipped ones cannot fail); what the live swisstopo servers do under eight connections; that
the live API still publishes what the committed lock records (the network test, opt-in, reads a
sample; `lock farphoto` and `download farphoto` read every cell).
"""

import copy
import http.client
import io
import json
import re
import shutil
import threading
import time
import urllib.error
import urllib.request

import pytest
from local_farphoto import ABSENT, LocalFarphoto, cells_of, far_name
from local_swisstopo import PHOTO, photo_name, sha256

import mattini.__main__ as cli
from mattini import download, lock
from mattini.datasets import load_datasets
from mattini.world import REPO, load_world

COMMITTED_LOCK = REPO / "config" / "datasets.lock.json"
COMMITTED_CONFIG = REPO / "config" / "surroundings.json"
REFUSALS = (download.DownloadError, OSError)
PRESENT = [cell for cell in cells_of(1000) if cell not in ABSENT]
EARLY, LATE = "2623-1098", "2625-1098"  # cells 9 and 19 of the 20 of the 1000 m box
OTHER_EDITION = "2024-01-01T00:00:00Z"
REMEDY = re.compile(r"lock farphoto|surroundings\.json")


@pytest.fixture
def far(monkeypatch, tmp_path):
    """The stand-in wired into the commands, with a lock pinning what it publishes."""
    for name in ("http_proxy", "HTTP_PROXY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("no_proxy", "127.0.0.1")
    site = LocalFarphoto()
    data = json.loads(COMMITTED_CONFIG.read_text(encoding="utf-8"))
    data["areas"]["village"]["margin_m"] = 1000
    config = tmp_path / "surroundings.json"
    config.write_text(json.dumps(data, indent=2), encoding="utf-8")
    monkeypatch.setattr(download, "STAC_ITEM", site.stac_item)
    monkeypatch.setattr(download, "SURROUNDINGS_PATH", config)
    site.lock_path = tmp_path / "config" / "datasets.lock.json"
    site.lock_path.parent.mkdir()
    shutil.copyfile(COMMITTED_LOCK, site.lock_path)
    site.pinned = json.loads(site.lock_path.read_bytes())
    site.pinned["datasets"]["swissimage_far"] = site.far_entry()
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
    return err[err.index("mattini: error: ") :].rstrip("\n")


class Meter:
    """Wraps a one-argument call: counts the calls under way together, holds each a moment."""

    def __init__(self, call, hold_s=0.025):
        self.call, self.hold_s = call, hold_s
        self.active = self.peak = self.calls = 0
        self.guard = threading.Lock()

    def __call__(self, *args):
        with self.guard:
            self.active += 1
            self.calls += 1
            self.peak = max(self.peak, self.active)
        try:
            time.sleep(self.hold_s)  # long enough for every other worker to start meanwhile
            return self.call(*args)
        finally:
            with self.guard:
                self.active -= 1


# --- the runner on its own ------------------------------------------------------------------


@pytest.mark.parametrize("low", REFUSALS)
@pytest.mark.parametrize("high", REFUSALS)
def test_the_first_refusal_in_item_order_is_raised_though_a_later_one_fails_first(low, high):
    later_failed = threading.Event()

    def work(item):
        if item == 3:
            later_failed.set()
            raise high("item 3")
        if item == 1:
            assert later_failed.wait(timeout=10)  # item 1 is under way until item 3 has failed
            raise low("item 1")
        return item

    with pytest.raises(REFUSALS) as caught:
        download._in_parallel(work, list(range(6)), 4)
    assert type(caught.value) is low and str(caught.value) == "item 1"


@pytest.mark.parametrize("refusal", REFUSALS)
def test_an_item_after_a_refusal_is_not_started(refusal):
    started, later_started, first_failed = [], threading.Event(), threading.Event()

    def work(item):
        started.append(item)
        if item == 0:
            assert first_failed.wait(timeout=10)  # item 0 fails once item 1 is under way
            raise refusal("item 0")
        if item == 1:
            first_failed.set()
            later_started.wait(timeout=0.3)  # set by any item after the refusal: none may be
            return item
        later_started.set()
        return item

    with pytest.raises(REFUSALS):
        download._in_parallel(work, list(range(8)), 2)
    assert sorted(started) == [0, 1], started


def test_no_more_workers_than_asked_run_at_once():
    meter = Meter(lambda item: item, hold_s=0.02)
    assert download._in_parallel(meter, list(range(24)), 3) == list(range(24))
    assert meter.calls == 24 and meter.peak <= 3, meter.peak


# --- the far photo's reads and fetches ------------------------------------------------------


def test_the_stac_reads_never_run_more_than_eight_at_once(far):
    meter = Meter(download.urllib_fetch_json)
    assets, absent = download.published_farphoto(
        load_world(), load_datasets(), meter, area="village"
    )
    assert (len(assets), len(absent)) == (17, 3) and meter.calls == 20
    assert meter.peak <= 8, meter.peak


def test_the_file_fetches_never_run_more_than_eight_at_once(far):
    meter = Meter(download.urllib_fetch_file)
    entries = download.download_farphoto(
        load_world(),
        load_datasets(),
        far.out,
        download.urllib_fetch_json,
        meter,
        lock=far.pinned,
        area="village",
    )
    assert len(entries) == 17 and meter.calls == 17
    assert meter.peak <= 8, meter.peak


def _hold_early_cell_until_late_cell_is_read(monkeypatch):
    """Make the STAC read of EARLY wait until the read of LATE is over (the later cell fails first)."""
    real, late_read = download.urllib_fetch_json, threading.Event()

    def fetch_json(url):
        if url.endswith(f"swissimage-dop10_2023_{EARLY}"):
            late_read.wait(timeout=5)
        try:
            return real(url)
        finally:
            if url.endswith(f"swissimage-dop10_2023_{LATE}"):
                late_read.set()

    monkeypatch.setattr(download, "urllib_fetch_json", fetch_json)


@pytest.mark.parametrize("command", ["lock", "download"])
def test_two_cells_of_another_edition_name_the_first_in_cell_order(
    far, capsys, monkeypatch, command
):
    for cell in (EARLY, LATE):
        far.publish_far(cell, far.bodies[far_name(cell)], datetime=OTHER_EDITION)
    _hold_early_cell_until_late_cell_is_read(monkeypatch)
    argv = ["lock", "farphoto"] if command == "lock" else ["download", "farphoto"]
    argv += ["--out", str(far.out)] if command == "download" else []
    before = far.lock_path.read_bytes()
    code, out, err = _run(capsys, *argv)
    assert (code, out) == (1, "")
    error = _error(err)
    assert EARLY in error and OTHER_EDITION in error, error
    assert LATE not in error, error
    assert far.lock_path.read_bytes() == before
    assert far.file_requests() == []


# --- the lock's entry and fit -----------------------------------------------------------------


@pytest.mark.parametrize("junk", [5, None, ["2603-1075"], {"a": 1}])
def test_the_fit_refuses_an_absent_that_holds_other_than_tile_ids_and_never_raises(junk):
    entry = json.loads(COMMITTED_LOCK.read_bytes())["datasets"]["swissimage_far"]
    entry["absent"] = [*entry["absent"][:-1], junk]
    lock_data = {"schema": 1, "datasets": {"swissimage_far": entry}}
    problem = lock.fit_problem(
        lock_data, load_datasets(), load_world(), "village", "swissimage_far"
    )
    assert problem is not None
    assert "has no absent list of tile ids" in problem
    assert "village" in problem and "python -m mattini lock farphoto" in problem


def test_the_entry_s_absent_is_sorted_whatever_order_the_cells_come_in(far, monkeypatch, tmp_path):
    real = download.area_farphoto_cells
    monkeypatch.setattr(
        download, "area_farphoto_cells", lambda world, area: list(reversed(real(world, area)))
    )
    entry = lock.farphoto_entry(
        load_world(), load_datasets(), download.urllib_fetch_json, area="village"
    )
    assert entry["absent"] == sorted(ABSENT)
    assert sorted(entry["tiles"]) == sorted(PRESENT)
    whole = lock.with_entry(far.pinned, download.FARPHOTO, entry)
    lock.validate_lock(whole, tmp_path / "datasets.lock.json")


# --- what the docstrings say ----------------------------------------------------------------


def _clauses_about(doc, words):
    """The clauses (split at `;` and at a sentence's end) of a docstring that contain `words`."""
    return [c for c in re.split(r";|\.\s", " ".join(doc.split())) if words in c]


@pytest.mark.parametrize(
    "doc",
    [download.__doc__, download.download_farphoto.__doc__],
    ids=["module", "download_farphoto"],
)
def test_the_docstrings_say_what_the_edition_refusal_of_download_farphoto_names(far, capsys, doc):
    far.publish_far(PRESENT[3], far.bodies[far_name(PRESENT[3])], datetime=OTHER_EDITION)
    code, out, err = _run(capsys, "download", "farphoto", "--out", str(far.out))
    assert (code, out) == (1, "")
    error = _error(err)
    assert PRESENT[3] in error and OTHER_EDITION in error and "'2023'" in error, error
    clauses = _clauses_about(doc, "another edition")
    assert clauses, "the docstring no longer speaks of an item of another edition"
    for clause in clauses:
        assert bool(REMEDY.search(clause)) == bool(REMEDY.search(error)), (clause, error)


# === the second fixer round =====================================================================

LOCK_FARPHOTO = "python -m mattini lock farphoto"
COMMITTED = json.loads(COMMITTED_LOCK.read_bytes())
COMMITTED_ENTRY = COMMITTED["datasets"]["swissimage_far"]
COMMITTED_CELLS = sorted([*COMMITTED_ENTRY["tiles"], *COMMITTED_ENTRY["absent"]])


def _argv(command, far):
    if command == "lock":
        return ["lock", "farphoto"]
    return ["download", "farphoto", "--out", str(far.out)]


# --- only an HTTP 404 is an absent cell (X12) -----------------------------------------------


def _item_read_fails(monkeypatch, cell, failure):
    """Every read of the item of `cell` raises `failure()` before it reaches the stand-in."""
    real = download.urllib_fetch_json

    def fetch_json(url):
        if url.endswith(f"swissimage-dop10_2023_{cell}"):
            raise failure()
        return real(url)

    monkeypatch.setattr(download, "urllib_fetch_json", fetch_json)


FAILURES = {
    "connection-refused": lambda: urllib.error.URLError(
        ConnectionRefusedError(111, "Connection refused")
    ),
    "connection-reset": lambda: ConnectionResetError(104, "Connection reset by peer"),
    "hung-up": lambda: http.client.RemoteDisconnected(
        "Remote end closed connection without response"
    ),
    "timeout": lambda: TimeoutError("timed out"),
    "not-json": lambda: json.JSONDecodeError("Expecting value", "", 0),
    "not-utf-8": lambda: UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte"),
}


@pytest.mark.parametrize("command", ["lock", "download"])
@pytest.mark.parametrize("kind", ["pinned", "absent"])
@pytest.mark.parametrize("failure", FAILURES)
def test_an_item_that_cannot_be_reached_is_not_an_absent_cell(
    far, capsys, monkeypatch, failure, kind, command
):
    cell = PRESENT[5] if kind == "pinned" else ABSENT[0]
    _item_read_fails(monkeypatch, cell, FAILURES[failure])
    before = far.lock_path.read_bytes()
    code, out, err = _run(capsys, *_argv(command, far))
    assert (code, out) == (1, "")
    error = _error(err)
    assert cell in error and "cannot read the STAC item" in error, error
    assert far.lock_path.read_bytes() == before
    assert far.file_requests() == [] and not far.out.exists()


SERVER_STEPS = [("status", status) for status in (400, 401, 405, 410, 429, 502, 504)]
SERVER_STEPS.append(("cut", 20))  # a body that ends 20 bytes in: the transport's own failure


@pytest.mark.parametrize("command", ["lock", "download"])
@pytest.mark.parametrize("step", SERVER_STEPS, ids=[f"{kind}-{n}" for kind, n in SERVER_STEPS])
def test_a_server_that_does_not_answer_404_does_not_make_a_cell_absent(far, capsys, step, command):
    # the stand-in serves a status for any item path, but a body only for a published item
    cell = ABSENT[0] if command == "download" and step[0] == "status" else PRESENT[0]
    far.script[far.item_path(PHOTO, f"swissimage-dop10_2023_{cell}")] = [step]
    before = far.lock_path.read_bytes()
    code, out, err = _run(capsys, *_argv(command, far))
    assert (code, out) == (1, "")
    error = _error(err)
    assert cell in error and "cannot read the STAC item" in error, error
    assert far.lock_path.read_bytes() == before
    assert far.file_requests() == [] and not far.out.exists()


# --- what the refusals of a new and of a vanished item tell the owner --------------------------


def test_the_refusal_of_a_vanished_item_names_the_file_and_the_checksum_the_lock_pins(far, capsys):
    cell = PRESENT[3]
    pinned = far.pinned["datasets"]["swissimage_far"]["tiles"][cell]
    far.withdraw_far(cell)
    code, out, err = _run(capsys, "download", "farphoto", "--out", str(far.out))
    assert (code, out) == (1, "")
    error = _error(err)
    assert cell in error and pinned["file"] in error and pinned["sha256"] in error, error
    assert far.file_requests() == [] and not far.out.exists()


def test_the_refusal_of_a_new_item_names_the_file_and_the_checksum_swisstopo_now_publishes(
    far, capsys
):
    cell, body = ABSENT[0], b"a tile swisstopo added after the lock\n" * 7
    far.publish_far(cell, body)
    code, out, err = _run(capsys, "download", "farphoto", "--out", str(far.out))
    assert (code, out) == (1, "")
    error = _error(err)
    assert cell in error and far_name(cell) in error and sha256(body) in error, error
    assert far.file_requests() == [] and not far.out.exists()


# --- the truncation of the fit's refusals (X34) -----------------------------------------------


def _margin(monkeypatch, tmp_path, margin_m):
    data = json.loads(COMMITTED_CONFIG.read_text(encoding="utf-8"))
    data["areas"]["village"]["margin_m"] = margin_m
    path = tmp_path / "surroundings.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    monkeypatch.setattr(download, "SURROUNDINGS_PATH", path)


def _entry_of(cells, *, also_absent=()):
    """The committed entry cut down to `cells`; `also_absent` of its pinned cells listed absent too."""
    keep, absent = set(cells), set(COMMITTED_ENTRY["absent"])
    entry = copy.deepcopy(COMMITTED_ENTRY)
    entry["tiles"] = {c: v for c, v in COMMITTED_ENTRY["tiles"].items() if c in keep}
    entry["absent"] = sorted({c for c in keep if c in absent} | set(also_absent))
    return entry


def _fit(entry):
    whole = {"schema": 1, "datasets": {"swissimage_far": entry}}
    return lock.fit_problem(whole, load_datasets(), load_world(), "village", "swissimage_far")


def _listed(cells, limit=6):
    """How a refusal lists cells: all of them up to six, else the first six and how many more."""
    return str(cells) if len(cells) <= limit else f"{cells[:limit]} and {len(cells) - limit} more"


@pytest.mark.parametrize("count", [1, 5, 6, 7, 8, 1800])
def test_the_fit_lists_at_most_six_of_the_cells_it_does_not_need(monkeypatch, tmp_path, count):
    # margin 0 is the village alone: 6 cells, and 1800 of the committed lock's lie beside them
    _margin(monkeypatch, tmp_path, 0)
    needed = download.farphoto_cells(load_world(), "village", margin_m=0)
    extras = [cell for cell in COMMITTED_CELLS if cell not in needed]
    assert len(needed) == 6 and len(extras) == 1800
    chosen = extras[:count]
    problem = _fit(_entry_of([*needed, *chosen]))
    assert f"holds the tiles {_listed(chosen)}, which the area does not need" in problem, problem
    assert LOCK_FARPHOTO in problem and len(problem) < 500, problem


@pytest.mark.parametrize("count", [1, 6, 7, 100])
def test_the_fit_lists_at_most_six_of_the_cells_the_lock_lacks(count):
    needed = download.area_farphoto_cells(load_world(), "village")
    assert len(needed) == 1806
    problem = _fit(_entry_of(needed[count:]))
    expected = (
        f"neither pins a checksum for nor records as absent the tiles {_listed(needed[:count])} "
        f"of the area"
    )
    assert expected in problem, problem
    assert LOCK_FARPHOTO in problem and len(problem) < 500, problem


@pytest.mark.parametrize("count", [1, 6, 7])
def test_the_fit_lists_at_most_six_of_the_cells_recorded_both_ways(count):
    chosen = sorted(COMMITTED_ENTRY["tiles"])[:count]
    problem = _fit(_entry_of(COMMITTED_CELLS, also_absent=chosen))
    expected = f"records the cells {_listed(chosen)} both as pinned tiles and as absent"
    assert expected in problem, problem
    assert LOCK_FARPHOTO in problem and len(problem) < 500, problem


# --- the runner cancels what has not started (decision 7) ----------------------------------------


@pytest.mark.parametrize("bug", [RuntimeError, KeyboardInterrupt])
def test_a_failure_that_is_no_refusal_starts_no_item_that_was_waiting(bug):
    started = []

    def work(item):
        started.append(item)
        if item == 0:
            raise bug("item 0")
        if item <= 2:
            time.sleep(0.5)  # items 1 and 2 hold both workers while the run is cancelled
        return item

    with pytest.raises(bug):
        download._in_parallel(work, list(range(40)), 2)
    # items 1 and 2 may be cancelled in the instant they are taken, and never more than a
    # third one slips through; a run that does not cancel starts all 40
    assert 0 in started and len(started) <= 4, started


# --- the words of `--help` (decision 8) --------------------------------------------------------


def _help_clause(capsys, command, dataset):
    """What the `dataset` argument's help says of `dataset`: from `<dataset>: ` to the next `;`."""
    with pytest.raises(SystemExit) as stopped:
        cli.main([command, "--help"])
    assert stopped.value.code == 0
    out = capsys.readouterr().out
    text = " ".join(out.split("positional arguments:", 1)[1].split("options:", 1)[0].split())
    return text.split(f"{dataset}: ", 1)[1].split(";", 1)[0]


@pytest.mark.parametrize("command", ["lock", "download"])
def test_the_help_of_farphoto_and_regio_says_what_each_reads(capsys, command):
    far_clause = _help_clause(capsys, command, "farphoto")
    regio_clause = _help_clause(capsys, command, "regio")
    _, spacing_m = download.surroundings_settings("village")
    resolution_m = load_datasets()[download.FARPHOTO]["resolution_m"]
    assert "SWISSIMAGE" in far_clause and f"{resolution_m:g} m" in far_clause, far_clause
    assert "10 cm" not in far_clause, far_clause  # that is the photo's
    assert f"{download.TILE_M // 1000} km cells around the area" in far_clause, far_clause
    assert "margin" in far_clause and "spacing" not in far_clause, far_clause
    assert download.EXPECTED_CONFIG_NAMES[download.FARPHOTO] in far_clause, far_clause
    assert "swissALTIRegio" in regio_clause and f"{spacing_m // 1000} km tiles" in regio_clause
    assert "margin and spacing" in regio_clause, regio_clause
    assert download.EXPECTED_CONFIG_NAMES[download.REGIO] in regio_clause, regio_clause


# --- layers that cover one another (X7, X33) ------------------------------------------------


@pytest.mark.parametrize(
    "junk",
    [None, 5, True, "2603-1075", {"2603-1075": 1}, {}],
    ids=["null", "number", "true", "text", "object", "empty-object"],
)
def test_validate_lock_refuses_an_absent_that_is_not_a_list(junk):
    data = copy.deepcopy(COMMITTED)
    data["datasets"]["swissimage_far"]["absent"] = junk
    with pytest.raises(lock.LockError) as refused:
        lock.validate_lock(data, "lock.json")
    message = str(refused.value)
    assert "dataset 'swissimage_far': absent must be a list of tile ids" in message, message
    assert f"`{LOCK_FARPHOTO}`" in message, message


FILE_DATASETS = [
    (name, "sheets" if "sheets" in entry else "tiles")
    for name, entry in sorted(COMMITTED["datasets"].items())
    if "sheets" in entry or "tiles" in entry
]


@pytest.mark.parametrize(
    "junk", [None, ["2603-1075"], "tiles", 5], ids=["null", "list", "text", "number"]
)
@pytest.mark.parametrize(("name", "files"), FILE_DATASETS, ids=[n for n, _ in FILE_DATASETS])
def test_the_fit_refuses_a_files_object_that_is_not_an_object_and_never_raises(name, files, junk):
    assert "swissimage_far" in dict(FILE_DATASETS)
    data = copy.deepcopy(COMMITTED)
    data["datasets"][name][files] = junk
    problem = lock.fit_problem(data, load_datasets(), load_world(), "village", name)
    assert problem is not None and f"has no {files}" in problem, problem
    assert download.LOCK_COMMAND_OF[name] in problem, problem


@pytest.mark.parametrize(
    "resolution", [0, -2, True, "2", None, float("nan"), float("inf")], ids=repr
)
def test_download_farphoto_names_an_unusable_resolution_before_anything_else(far, resolution):
    datasets = copy.deepcopy(load_datasets())
    datasets[download.FARPHOTO]["resolution_m"] = resolution
    with pytest.raises(download.DownloadError) as refused:
        download.download_farphoto(
            load_world(),
            datasets,
            far.out,
            download.urllib_fetch_json,
            download.urllib_fetch_file,
            lock=far.pinned,
            area="village",
        )
    message = str(refused.value)
    assert download.FARPHOTO in message and "resolution_m must be a positive number" in message
    assert far.requests == [] and not far.out.exists()


def test_the_entry_and_the_provenance_follow_the_datasets_config(tmp_path):
    """Another collection, edition, resolution and credit than the committed config's: the lock's
    entry and provenance.json carry them, not the committed values (nothing is hard-coded)."""
    datasets = copy.deepcopy(load_datasets())
    datasets[download.FARPHOTO].update(
        collection="ch.example.far", edition="2031", resolution_m=5, attribution="© example"
    )
    world, cells = load_world(), download.area_farphoto_cells(load_world(), "village")
    published = cells[100:103]
    names = {cell: f"swissimage-dop10_2031_{cell}_5_2056.tif" for cell in published}
    bodies = {names[cell]: f"far bytes of {cell}\n".encode() * 3 for cell in published}
    prefix = "https://data.geo.admin.ch/api/stac/v1/collections/ch.example.far/items/"

    def fetch_json(url):
        cell = url.removeprefix(prefix).removeprefix("swissimage-dop10_2031_")
        if cell not in cells:
            raise AssertionError(f"asked for {url}")
        if cell not in published:
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
        return {
            "id": f"swissimage-dop10_2031_{cell}",
            "properties": {"datetime": "2031-01-01T00:00:00Z"},
            "assets": {
                names[cell]: {
                    "href": f"https://example.invalid/{names[cell]}",
                    "file:checksum": "1220" + sha256(bodies[names[cell]]).upper(),
                }
            },
        }

    def fetch_file(url, dest):
        dest.write_bytes(bodies[url.rsplit("/", 1)[1]])

    entry = lock.farphoto_entry(world, datasets, fetch_json, area="village")
    assert entry == {
        "absent": sorted(set(cells) - set(published)),
        "collection": "ch.example.far",
        "edition": "2031",
        "resolution_m": 5,
        "tiles": {
            cell: {"file": names[cell], "sha256": sha256(bodies[names[cell]])} for cell in published
        },
    }
    whole = lock.with_entry(COMMITTED, download.FARPHOTO, entry)
    download.download_farphoto(
        world, datasets, tmp_path, fetch_json, fetch_file, lock=whole, area="village"
    )
    written = (tmp_path / download.FARPHOTO / "2031" / download.PROVENANCE).read_text("utf-8")
    provenance = json.loads(written)
    assert provenance["attribution"] == "© example"
    assert provenance["collection"] == "ch.example.far" and provenance["edition"] == "2031"
    assert provenance["resolution_m"] == 5 and provenance["absent"] == entry["absent"]
    assert [tile["tile"] for tile in provenance["tiles"]] == published


# --- the live check's offline twin ----------------------------------------------------------


def test_the_committed_lock_is_what_the_code_makes_of_its_items_for_all_1806_cells():
    """`lock farphoto` run offline over the committed lock's own items, the real URL form."""
    base = "https://data.geo.admin.ch/api/stac/v1/collections/ch.swisstopo.swissimage-dop10/items/"
    items = {}
    for cell, pinned in COMMITTED_ENTRY["tiles"].items():
        item_id = f"swissimage-dop10_2023_{cell}"
        items[base + item_id] = {
            "id": item_id,
            "properties": {"datetime": "2023-01-01T00:00:00Z"},
            "assets": {
                photo_name(cell): {
                    "href": f"https://example.invalid/{photo_name(cell)}",
                    "file:checksum": "1220" + "AB" * 32,
                },
                pinned["file"]: {
                    "href": f"https://example.invalid/{pinned['file']}",
                    "file:checksum": "1220" + pinned["sha256"].upper(),
                },
            },
        }
    for cell in COMMITTED_ENTRY["absent"]:
        items[base + f"swissimage-dop10_2023_{cell}"] = None
    asked, guard = [], threading.Lock()

    def fetch_json(url):
        with guard:
            asked.append(url)
        if url not in items:
            raise AssertionError(f"asked for an item the committed lock has no cell for: {url}")
        if items[url] is None:
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
        return items[url]

    entry = lock.farphoto_entry(load_world(), load_datasets(), fetch_json, area="village")
    assert len(items) == 1806 and sorted(asked) == sorted(items)
    assert entry == COMMITTED_ENTRY


class _Reply(io.BytesIO):
    """What `urllib.request.urlopen` gives: a body to read, and headers."""

    def __init__(self, body=b"", headers=None):
        super().__init__(body)
        self.headers = headers if headers is not None else http.client.HTTPMessage()


def test_the_json_fetcher_asks_for_json_as_the_pipeline_and_with_a_timeout(monkeypatch):
    seen = {}

    def urlopen(request, timeout=None):
        seen.update(request=request, timeout=timeout)
        return _Reply(b'{"id": "an-item"}')

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    assert download.urllib_fetch_json("https://example.invalid/an-item") == {"id": "an-item"}
    request = seen["request"]
    accept = request.get_header("Accept")
    assert "application/geo+json" in accept and "application/json" in accept, accept
    assert request.get_header("User-agent") == download.USER_AGENT
    assert request.get_method() == "GET" and request.full_url == "https://example.invalid/an-item"
    assert seen["timeout"] == download.TIMEOUT_S and download.TIMEOUT_S > 0


@pytest.mark.parametrize(
    ("headers", "expected"),
    [
        ({"Content-Length": "1234", "x-amz-meta-sha256": "ab" * 32}, (1234, "ab" * 32)),
        ({"Content-Length": "1234"}, (1234, None)),
        ({"x-amz-meta-sha256": "ab" * 32}, (None, "ab" * 32)),
        ({"Content-Length": "many"}, (None, None)),
        ({}, (None, None)),
    ],
    ids=["both", "length-only", "checksum-only", "length-not-a-number", "neither"],
)
def test_the_head_fetcher_reads_the_two_headers_the_file_host_sends(monkeypatch, headers, expected):
    message = http.client.HTTPMessage()
    for key, value in headers.items():
        message[key] = value
    seen = {}

    def urlopen(request, timeout=None):
        seen.update(request=request, timeout=timeout)
        return _Reply(headers=message)

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    assert download.urllib_head("https://example.invalid/a-file") == expected
    assert seen["request"].get_method() == "HEAD" and seen["timeout"] == download.TIMEOUT_S


def test_the_head_fetcher_reads_what_the_stand_in_s_file_host_sends(far):
    name = far_name(PRESENT[2])
    body = far.bodies[name]
    assert download.urllib_head(far.base + far.file_path(name)) == (len(body), sha256(body))
