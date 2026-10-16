"""Tests for brief M3-R1-fix-3: what tools/gate.sh's render step requires and refuses.

Pinned decisions (CLAUDE.md, the standard gate; brief M3-R1-fix-3, Decisions 1 and 3):
tools/gate.sh, run as the owner runs it (here in a scratch tree, fake_tools.py: a stand-in
Godot whose render scripts print the lines a test gives them, a stand-in xvfb-run, or none):
- where xvfb-run is not on PATH the step fails, naming xvfb-run and MATTINI_SKIP_RENDER=1, and
  runs no script; with MATTINI_SKIP_RENDER=1 it prints the SKIPPED line, to the log and to the
  terminal, and the gate passes; only the value 1 skips;
- where xvfb-run is found the step runs both scripts whatever the variable says, and says
  that it is set;
- it passes only when every check prints its "RENDER <check>: PASS" line (photo, classes,
  trees) and none a "RENDER ...: FAIL" line, the script exits 0, and no Godot error line
  appears that the allowlist does not except (a global entry does; one scoped to a GUT script
  does not: it applies in the GUT step only);
- it is the last step.

Each case differs from the positive control in one respect. The mutations that prove these
tests are in the brief's Findings.

Does NOT prove: that the real scripts' numbers hold or that a mutated shader fails them (the
brief's eight mutations, run on the real render); what a machine without Mesa but with
xvfb-run prints (the scripts' own result lines are missing there, which is the refusal tested
below as a missing line); anything on Windows (these tests run where bash is, and skip
elsewhere).
"""

import sys

import pytest
from fake_tools import BASH, calls, gate_tree, gut_output, run_gate

pytestmark = pytest.mark.skipif(
    BASH is None or sys.platform != "linux", reason="runs tools/gate.sh with bash, on Linux"
)

ALPHA = ("res://tests/test_alpha.gd", [("test_one", [])])
PASSED = "== gate: all steps passed"
FAILED = "== gate: FAILED at step: render"
SKIPPED = (
    "== render: SKIPPED (MATTINI_SKIP_RENDER=1): where the photo, the classes and the "
    "crowns' colour land is not checked"
)
PHOTO = "RENDER photo: PASS correlation 0.9761"
CLASSES = "RENDER classes: PASS agreement 83091 of 83427"
TREES = "RENDER trees: PASS correlation 0.9380 over 20 trees"
SCRIPT = "--rendering-method gl_compatibility --resolution 1280x720 -s res://tests/render/"


def _gate(tmp_path, *, allowlist="", **kwargs):
    root = gate_tree(tmp_path, ["test_alpha.gd"], allowlist)
    return run_gate(tmp_path, root, gut_output([ALPHA]), **kwargs)


def _passes(done):
    assert done.returncode == 0 and PASSED in done.stdout, done.stdout[-3000:]


def _fails_at_render(done):
    assert done.returncode != 0 and PASSED not in done.stdout, done.stdout[-3000:]
    assert FAILED in done.stdout, done.stdout[-3000:]


def _scripts_run(tmp_path):
    return [line for line in calls(tmp_path) if line.startswith("xvfb-run") and SCRIPT in line]


def test_two_passing_scripts_pass_and_each_runs_under_xvfb_run(tmp_path):
    """Positive control: every case below differs from this run in one respect."""
    done = _gate(tmp_path)
    _passes(done)
    photo, trees = _scripts_run(tmp_path)
    assert photo.startswith("xvfb-run -a timeout --kill-after=10 180 ")
    assert photo.endswith(SCRIPT + "render_photo.gd")
    assert trees.endswith(SCRIPT + "render_trees.gd")
    assert "--audio-driver Dummy" in photo and "--audio-driver Dummy" in trees
    assert PHOTO in done.stdout and CLASSES in done.stdout and TREES in done.stdout


def test_the_render_step_comes_after_gdformat_and_last(tmp_path):
    done = _gate(tmp_path)
    steps = [line for line in done.stdout.splitlines() if line.startswith("== gate: step: ")]
    assert steps[-2:] == ["== gate: step: gdformat --check", "== gate: step: render"], steps


# ---------------------------------------------------------------- xvfb-run and the skip


def test_without_xvfb_run_the_step_fails_naming_it_and_the_skip(tmp_path):
    done = _gate(tmp_path, xvfb=False)
    _fails_at_render(done)
    refusal = [line for line in done.stdout.splitlines() if "xvfb-run is missing" in line]
    assert len(refusal) == 1, done.stdout[-3000:]
    assert "MATTINI_SKIP_RENDER=1" in refusal[0]
    assert "SKIPPED" not in done.stdout
    assert _scripts_run(tmp_path) == []


def test_with_the_variable_set_to_1_and_no_xvfb_run_the_step_is_skipped_and_says_so(tmp_path):
    done = _gate(tmp_path, xvfb=False, env={"MATTINI_SKIP_RENDER": "1"})
    _passes(done)
    assert SKIPPED in done.stdout.splitlines()
    assert _scripts_run(tmp_path) == []
    # on the terminal as well as in the log: the gate's stdout is redirected, its stderr is not
    assert done.stdout.splitlines().count(SKIPPED) == 2


@pytest.mark.parametrize("value", ["", "0", "true", "yes", " 1", "1 "])
def test_only_the_value_1_skips(tmp_path, value):
    done = _gate(tmp_path, xvfb=False, env={"MATTINI_SKIP_RENDER": value})
    _fails_at_render(done)
    assert "SKIPPED" not in done.stdout


def test_where_xvfb_run_is_found_the_variable_changes_nothing(tmp_path):
    done = _gate(tmp_path / "passing", env={"MATTINI_SKIP_RENDER": "1"})
    _passes(done)
    assert len(_scripts_run(tmp_path / "passing")) == 2
    assert "SKIPPED" not in done.stdout
    assert "MATTINI_SKIP_RENDER=1 is set but xvfb-run is here" in done.stdout
    failing = _gate(
        tmp_path / "failing",
        render={"render_trees": ["RENDER trees: FAIL correlation 0.1495 below 0.60"]},
        render_status=1,
        env={"MATTINI_SKIP_RENDER": "1"},
    )
    _fails_at_render(failing)


# ---------------------------------------------------------------- what a script must print


@pytest.mark.parametrize(
    ("script", "lines", "missing"),
    [
        ("render_photo", [PHOTO], "classes"),
        ("render_photo", [CLASSES], "photo"),
        ("render_photo", [], "photo"),
        ("render_trees", [], "trees"),
        ("render_trees", ["RENDER trees: PASSED"], "trees"),
        ("render_trees", ["render trees: PASS"], "trees"),
        ("render_trees", [" RENDER trees: PASS"], "trees"),
        ("render_trees", ["RENDER photo: PASS"], "trees"),
    ],
    ids=[
        "no-classes-line",
        "no-photo-line",
        "photo-script-prints-nothing",
        "trees-script-prints-nothing",
        "a-near-miss-word",
        "lower-case-prefix",
        "indented-line",
        "another-check-s-line",
    ],
)
def test_a_check_that_printed_no_pass_line_fails(tmp_path, script, lines, missing):
    done = _gate(tmp_path, render={script: lines})
    _fails_at_render(done)
    assert f"'RENDER {missing}: PASS' line" in done.stdout, done.stdout[-3000:]


@pytest.mark.parametrize("status", [0, 1])
def test_a_fail_line_fails_the_step_whatever_the_status_and_the_pass_lines(tmp_path, status):
    """Exit status 0 with a PASS line and a FAIL line: a script that lost its exit code."""
    fail = "RENDER photo: FAIL correlation 0.0554 below 0.95; the photo reads better mirrored"
    done = _gate(tmp_path, render={"render_photo": [fail, PHOTO, CLASSES]}, render_status=status)
    _fails_at_render(done)
    assert fail in done.stdout
    if status == 0:
        assert "a render check failed" in done.stdout


def test_a_script_that_exits_non_zero_after_its_pass_lines_fails(tmp_path):
    """A timeout kills the script (exit 124): the lines it printed before do not pass it."""
    done = _gate(tmp_path, render_status=124)
    _fails_at_render(done)
    assert "exit status 124" in done.stdout


# ---------------------------------------------------------------- the engine's error lines


@pytest.mark.parametrize(
    "line",
    [
        'ERROR: Condition "status < 0" is true. Returning: ERR_CANT_OPEN',
        'SCRIPT ERROR: Parse Error: Identifier "x" not declared in the current scope.',
    ],
    ids=["engine-error", "script-error"],
)
def test_an_engine_error_line_fails_even_with_every_pass_line_printed(tmp_path, line):
    done = _gate(tmp_path, render={"render_trees": [line, TREES]})
    _fails_at_render(done)
    assert "error lines in the output" in done.stdout


def test_a_global_allowlist_entry_excepts_an_error_line_and_a_scoped_one_does_not(tmp_path):
    line = "ERROR: the harness printed this line on purpose"
    render = {"render_trees": [line, TREES]}
    entry = "the harness printed this line on purpose"
    done = _gate(tmp_path / "global", render=render, allowlist=f"{entry} # a test\n")
    _passes(done)
    scoped = f"{entry} @ res://tests/test_alpha.gd # a test\n"
    _fails_at_render(_gate(tmp_path / "scoped", render=render, allowlist=scoped))
