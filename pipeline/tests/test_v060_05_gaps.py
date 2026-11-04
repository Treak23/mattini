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

Run as the owner runs the commands, against the local stand-in (local_farphoto.py, real urllib,
the `margin_m` 1000 box: 20 cells, 17 with an item), except the runner's own tests, which call
`download._in_parallel` with plain functions and events. No sleep decides whether a correct run
passes: the holds in `Meter` only make a pool that is too wide overlap, and the one wait of 0.3 s
only bounds how long a correct run waits for a call that must not come.

Does NOT prove: that a runner of another make (a pool that is not `ThreadPoolExecutor`) keeps
these properties; the order of the refusals when the calls that fail are not all started (the
skipped ones cannot fail); what the live swisstopo servers do under eight connections.
"""

import json
import re
import shutil
import threading
import time

import pytest
from local_farphoto import ABSENT, LocalFarphoto, cells_of, far_name

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
