"""Pinning tests for brief M3-02 (M2 V1-G-01, V1-G-05, V1-G-06, V1-G-07): what the gate reads in GUT's run.

Pinned decisions (CLAUDE.md, the standard gate; brief M3-02): tools/gate.sh, run as the
owner runs it (here in a scratch tree, on GUT output the test writes, fake_tools.py):
- never lets an allowlist entry, global or scoped, except a line that means a test script
  did not run: GUT's `Ignoring script` and Godot's `Failed to load script` (V1-G-01; the
  review passed a whole gate with an ignored script allowlisted);
- requires GUT's run summary to count as many scripts (`Scripts <n>`, after the last
  `= Run Summary`) as there are test scripts (`test_*.gd`) under game/tests/, so a test
  that prints the summary and the pass line itself, then quits, fails (V1-G-05);
- requires GUT's own version line, exactly `GUT version:  9.6.1` (two spaces), besides
  plugin.cfg's (V1-G-06: GUT's source of truth is utils.gd, not plugin.cfg);
- removes a CR at the end of a line before any scan, so a CR LF run (a Windows console)
  reads as the LF one: it passes when that passes, scoped entries included, and fails when
  that fails (V1-G-07).
A refusal ends the gate with a non-zero status at the GUT step (`FAILED at step: gut`),
where GUT's output is read; an entry refused when the allowlist is read fails the gate
earlier, which the test of the plain entry accepts too.

Each case keeps every other check satisfied, so it fails only on its own rule: the
ignored script is hidden from the count by an inner test class, which GUT counts as a
script (measured: 4 scripts for 3 files and one inner class), and the count case prints no
ignored line.

Does NOT prove: anything on Windows (the CR LF output is simulated; these tests run where
bash is, and skip elsewhere); that the scans catch a line format nobody measured.
"""

import sys

import pytest
from fake_tools import BASH, crlf, gate_tree, gut_output, run_gate

pytestmark = pytest.mark.skipif(
    BASH is None or sys.platform != "linux", reason="runs tools/gate.sh with bash, on Linux"
)

TESTS = ["test_alpha.gd", "test_beta.gd"]
ALPHA = ("res://tests/test_alpha.gd", [("test_one", []), ("test_two", [])])
BETA = ("res://tests/test_beta.gd", [("test_three", [])])
PASSED = "== gate: all steps passed"
GUT_FAILED = "== gate: FAILED at step: gut"


def _gate(tmp_path, output, tests=TESTS, allowlist=""):
    return run_gate(tmp_path, gate_tree(tmp_path, tests, allowlist), output)


def _passes(done):
    assert done.returncode == 0 and PASSED in done.stdout, done.stdout[-3000:]


def _fails_at_gut(done):
    assert done.returncode != 0 and PASSED not in done.stdout, done.stdout[-3000:]
    assert GUT_FAILED in done.stdout, done.stdout[-3000:]


def test_a_complete_passing_run_passes(tmp_path):
    """Positive control: every case below differs from this run in one respect."""
    _passes(_gate(tmp_path, gut_output([ALPHA, BETA])))


# ---------------------------------------------------------------------- V1-G-06


@pytest.mark.parametrize("version", ["9.6.0", "9.6.10", None], ids=["9.6.0", "9.6.10", "none"])
def test_gut_s_own_version_line_must_say_9_6_1(tmp_path, version):
    """plugin.cfg says 9.6.1 in every case; GUT's own line says otherwise or nothing."""
    _fails_at_gut(_gate(tmp_path, gut_output([ALPHA, BETA], gut_version=version)))


# ---------------------------------------------------------------------- V1-G-05


def test_a_test_printing_the_summary_and_the_pass_line_then_quitting_fails(tmp_path):
    """The measured shape (GUT 9.6.1, a test printing both lines, then get_tree().quit()):
    GUT runs the scripts on, prints no summary of its own, and Godot warns at exit."""
    faker = (
        "res://tests/test_beta.gd",
        [("test_three", ["= Run Summary", "---- All tests passed! ----"])],
    )
    leak = [
        "WARNING: ObjectDB instances leaked at exit (run with --verbose for details).",
        "   at: cleanup (core/object/object.cpp:2663)",
    ]
    _fails_at_gut(_gate(tmp_path, gut_output([ALPHA, faker], summary=False, after=leak)))


def test_a_summary_counting_fewer_scripts_than_game_tests_holds_fails(tmp_path):
    output = gut_output([ALPHA, BETA], scripts_total=2)
    _passes(_gate(tmp_path / "two", output))  # control: two test scripts, two counted
    three = [*TESTS, "test_gamma.gd"]
    _fails_at_gut(_gate(tmp_path / "three", output, tests=three))


# ---------------------------------------------------------------------- V1-G-01

IGNORED = (
    "\x1b[33m[WARNING]:  \x1b[0mIgnoring script res://tests/test_notgut.gd because it does "
    "not extend GutTest"
)
INNER = ("res://tests/test_beta.gd.TestInner", [("test_four", [])])


@pytest.mark.parametrize(
    "entry",
    [
        "Ignoring script res://tests/test_notgut.gd # it is not ready yet",
        "res://tests/test_notgut.gd because it does not extend GutTest # not ready yet",
        "res://tests/test_notgut.gd because it does not extend @ res://tests/test_alpha.gd # x",
    ],
    ids=["global", "global-without-the-words", "scoped"],
)
def test_no_entry_excepts_an_ignored_test_script(tmp_path, entry):
    """Three test files, the third not a GutTest: GUT ignores it, and an inner test class
    of the second makes its count three again (measured), so only the line tells."""
    tests = [*TESTS, "test_notgut.gd"]
    output = gut_output([ALPHA, BETA, INNER], before=[IGNORED])
    done = _gate(tmp_path, output, tests=tests, allowlist=entry + "\n")
    assert done.returncode != 0 and PASSED not in done.stdout, done.stdout[-3000:]
    if "Ignoring script" not in entry:  # an entry only the scan can tell
        assert GUT_FAILED in done.stdout, done.stdout[-3000:]


FAILED_LOAD = 'ERROR: Failed to load script "res://scripts/broken.gd" with error "Parse error".'


@pytest.mark.parametrize(
    "entry",
    [
        'Failed to load script "res://scripts/broken.gd" # it is broken on purpose',
        'script "res://scripts/broken.gd" with error # it is broken on purpose',
        'Failed to load script "res://scripts/broken.gd" @ res://tests/test_alpha.gd # x',
    ],
    ids=["global", "global-without-the-words", "scoped"],
)
def test_no_entry_excepts_a_script_that_failed_to_load(tmp_path, entry):
    """The line printed while the first script runs, its backtrace beside it (measured)."""
    printed = [
        FAILED_LOAD,
        "   at: load (modules/gdscript/gdscript.cpp:2907)",
        "   GDScript backtrace (most recent call first):",
        "       [0] test_one (res://tests/test_alpha.gd:5)",
    ]
    alpha = (ALPHA[0], [("test_one", printed), ("test_two", [])])
    done = _gate(tmp_path, gut_output([alpha, BETA]), allowlist=entry + "\n")
    assert done.returncode != 0 and PASSED not in done.stdout, done.stdout[-3000:]
    if "Failed to load script" not in entry:
        assert GUT_FAILED in done.stdout, done.stdout[-3000:]


def test_an_entry_still_excepts_a_benign_error_line(tmp_path):
    """Control: the allowlist works as before for any other line, scoped as before."""
    printed = ["ERROR: Probe: user://test_probe/manifest.json: a refusal on purpose"]
    alpha = (ALPHA[0], [("test_one", printed), ("test_two", [])])
    entry = "Probe: user://test_probe/ @ res://tests/test_alpha.gd # it refuses on purpose\n"
    _passes(_gate(tmp_path, gut_output([alpha, BETA]), allowlist=entry))


# ---------------------------------------------------------------------- V1-G-07


def test_a_crlf_run_that_passes_passes(tmp_path):
    _passes(_gate(tmp_path, crlf(gut_output([ALPHA, BETA]))))


def test_a_crlf_run_s_scoped_entry_applies_while_its_script_runs(tmp_path):
    printed = ["ERROR: Probe: user://test_probe/manifest.json: a refusal on purpose"]
    alpha = (ALPHA[0], [("test_one", printed), ("test_two", [])])
    entry = "Probe: user://test_probe/ @ res://tests/test_alpha.gd # it refuses on purpose\n"
    _passes(_gate(tmp_path, crlf(gut_output([alpha, BETA])), allowlist=entry))


def test_a_crlf_run_that_fails_fails(tmp_path):
    """Control: no CR hides an error line, a version line or a short count."""
    printed = ["ERROR: Probe: user://test_probe/manifest.json: a refusal nobody excepted"]
    alpha = (ALPHA[0], [("test_one", printed), ("test_two", [])])
    _fails_at_gut(_gate(tmp_path / "error", crlf(gut_output([alpha, BETA]))))
    _fails_at_gut(_gate(tmp_path / "version", crlf(gut_output([ALPHA, BETA], gut_version="9.6.0"))))
    output = crlf(gut_output([ALPHA, BETA]))
    _fails_at_gut(_gate(tmp_path / "count", output, tests=[*TESTS, "test_gamma.gd"]))
