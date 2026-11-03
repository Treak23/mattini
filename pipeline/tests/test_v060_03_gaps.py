"""Guards of brief v0.6.0-03 the pinned tests leave open (decision 6; the batch gate's prover).

The pinned copies run the new steps and checks against stand-ins that agree with themselves:
the stand-in game writes every line to the output and to godot.log together, the pinned
"other" Python is 3.13.0, the pinned step conditions are the two delivery ones, and the pair
in §C is replaced by the scratch manifest's before the command runs. Each guard below is one
the prover showed a mutation could break unseen. This file closes them by the class and not by
the instance (lesson 9); the pinned copies stay untouched.

- *Check 5 reads both files, in every branch* (extra rows E2, E2b). A game that exits by itself
  is told "held all" only when the output AND godot.log hold every startup line; a game whose
  output or whose godot.log lacks one is told "before ... held the startup lines". The same two
  reads decide the check while the game still runs: a line missing from the output alone, or
  from godot.log alone, is a FAIL, never a PASS. Each file is withheld a line in turn (a game
  stand-in edited as the pinned tests edit it), so neither read can stand in for the other.
- *The count check 5 prints is the count of the startup lines* (E15): `held all <n> startup
  lines`, in the PASS line and in the exited-by-itself FAIL line, is the number of `mattini
  <version>: ` lines the game printed with `--quit-after`, counted here by running the stand-in
  game, not by reading the script's own variable.
- *The Python comparison is the whole version* (E1, E1b). A pin that is a prefix of the
  interpreter's version, a suffix of it, the version with a digit or a part added, or its
  major.minor alone is refused like any other: the step compares `major.minor.micro` as a whole
  string, never as a substring, a prefix or a pattern. The pin equal to the interpreter is the
  control that passes.
- *Nothing but the two delivery steps can be skipped* (E28): no step of the job and not the job
  itself carries an `if`, except the dry run's archive upload and the draft Release, so a dry
  run (or any other input) cannot skip the sha-on-main step, the Python step or any other check
  by a condition the always()/failure()/cancelled() census does not see.
- *§C's command spells the pair its own bullet names* (E24): the size (twice) and the SHA-256
  in §C's one command are the first pair the bullet's prose names, the release's own, so a
  literal edited in the command alone (a wrong SHA-256, another size) disagrees with its
  prose and fails here, where the pinned test replaces both literals before it runs the
  command.

Does NOT prove: that the pair in §C and its prose are the release's (a doc cannot prove that;
each release's plan names its pair, the session writes both places and the workflow's own pair
step compares the build with it); that the session pastes the command; the workflow cases that
need GitHub itself (the runner's unauthenticated fetch of main, uv's CPython download, zlib's
byte parity), which no stand-in runs: the session's dry run of 0.6.0 is that proof.
"""

import re
import subprocess
import sys

import pytest
from fake_release import release_tree, run_checks
from fake_tools import BASH, REPO, VERSION

bash_only = pytest.mark.skipif(
    BASH is None or sys.platform != "linux", reason="runs a step or a script with bash"
)

# ------------------------------------------------------------------- check 5's two files

QUITS_BY_ITSELF = ('if [ -n "$quit" ]; then', "if true; then")
# The stand-in's `say` (fake_release.FAKE_GAME) writes each line to stdout, then to godot.log.
# Without --quit-after (check 5's start; checks 2 to 4 give it) the last startup line, "roofs",
# is left out of one of the two.
WITHHELD = ("output", "godot.log")
SKIP_ROOFS = '[[ -n "$quit" || "$1" != *"roofs village"* ]]'


def _withhold(root, which):
    """Edit the stand-in game so check 5's start leaves its last startup line out of `which`."""
    game = root / "build" / "linux" / "mattini.x86_64"
    text = game.read_text(encoding="utf-8")
    if which == "output":
        old = '\techo "$1"\n\tif [ -n "${FAKE_LOG_AT_EXIT:-}" ]'
        new = f'\t{SKIP_ROOFS} && echo "$1"\n\tif [ -n "${{FAKE_LOG_AT_EXIT:-}}" ]'
    else:
        old = '\t\techo "$1" >> "$log"'
        new = f'\t\t{SKIP_ROOFS} && echo "$1" >> "$log"'
    assert text.count(old) == 1, f"the stand-in game's say() changed: {old!r}"
    game.write_text(text.replace(old, new), encoding="utf-8")


def _quit_by_itself(root):
    game = root / "build" / "linux" / "mattini.x86_64"
    text = game.read_text(encoding="utf-8")
    assert text.count(QUITS_BY_ITSELF[0]) == 1, "the stand-in game's exit branch changed"
    game.write_text(text.replace(*QUITS_BY_ITSELF), encoding="utf-8")


def _live_log_line(output):
    lines = [line for line in output.splitlines() if line.startswith("release check: live log: ")]
    assert len(lines) == 1, output
    return lines[0]


# FAKE_ERROR is one more line after the startup lines: here a sixth "mattini <version>: " line, so
# that a count written into the script as a number cannot agree with the stand-in by luck.
GAMES = {
    "five-lines": {},
    "six-lines": {"FAKE_ERROR": f"mattini {VERSION}: one more startup line"},
}


def _startup_count(tmp_path, root, **knobs):
    """The 'mattini <version>: ' lines the stand-in game prints with --quit-after, counted here."""
    done = subprocess.run(
        [str(root / "build" / "linux" / "mattini.x86_64"), "--headless", "--quit-after", "600"],
        env={
            "PATH": "/usr/bin:/bin",
            "XDG_DATA_HOME": str(tmp_path / "count-xdg"),
            "FAKE_VERSION": VERSION,
            **knobs,
        },
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return sum(1 for line in done.stdout.splitlines() if re.match(r"mattini [^ :]+: ", line))


@bash_only
@pytest.mark.parametrize("which", WITHHELD)
def test_a_game_that_quits_with_one_file_short_is_not_told_it_held_all_lines(tmp_path, which):
    root = release_tree(tmp_path)
    _withhold(root, which)
    _quit_by_itself(root)
    done = run_checks(tmp_path, root)
    assert done.returncode == 1, done.stdout
    line = _live_log_line(done.stdout)
    assert re.match(r"release check: live log: FAIL the process exited by itself\b", line), line
    assert re.search(r"\b(before|lacked)\b", line), line
    assert "held all" not in line, f"{which} lacked a startup line, and the line says it held all"


@bash_only
@pytest.mark.parametrize("which", WITHHELD)
def test_a_running_game_with_one_file_short_fails_the_live_log(tmp_path, which):
    """While the game runs, the output alone or godot.log alone holding the lines is no PASS."""
    root = release_tree(tmp_path)
    _withhold(root, which)
    done = run_checks(tmp_path, root, RELEASE_CHECKS_LIVE_TIMEOUT_S="3")
    assert done.returncode == 1, done.stdout
    line = _live_log_line(done.stdout)
    assert line.startswith("release check: live log: FAIL "), line
    assert "held all" not in line, line


@bash_only
@pytest.mark.parametrize("knobs", GAMES.values(), ids=list(GAMES))
def test_the_count_check_5_prints_is_the_count_of_startup_lines(tmp_path, knobs):
    root = release_tree(tmp_path)
    count = _startup_count(tmp_path, root, **knobs)
    assert count >= 5, f"two data packs and three startup lines at least, counted {count}"
    done = run_checks(tmp_path, root, **knobs)
    assert done.returncode == 0, done.stdout
    line = _live_log_line(done.stdout)
    assert re.search(rf"\bheld all {count} startup lines\b", line), (count, line)


@bash_only
@pytest.mark.parametrize("knobs", GAMES.values(), ids=list(GAMES))
def test_the_count_check_5_prints_after_a_quit_is_the_count_of_startup_lines(tmp_path, knobs):
    root = release_tree(tmp_path)
    count = _startup_count(tmp_path, root, **knobs)
    _quit_by_itself(root)
    done = run_checks(tmp_path, root, **knobs)
    assert done.returncode == 1, done.stdout
    line = _live_log_line(done.stdout)
    assert re.search(rf"\bheld all {count} startup lines\b", line), (count, line)


# ------------------------------------------------------------- the workflow's two guards

WORKFLOW = REPO / ".github" / "workflows" / "release.yml"
PINS = REPO / "tools" / "pins.sh"
PYTHON_LINE = re.compile(r'^PYTHON_VERSION="([^"]*)"[ \t]*(?:#.*)?$', re.MULTILINE)
THIS_PYTHON = "{}.{}.{}".format(*sys.version_info[:3])

# A stand-in uv (as test_release_workflow.py's): `uv run ... python <args>` runs this Python.
FAKE_UV = r"""#!/usr/bin/env bash
printf '%s|%s\n' "${UV_PYTHON:-}" "$*" >> "$FAKE_UV_CALLS"
if [ "${1:-}" = run ]; then
	shift
	while [ "$#" -gt 0 ] && [ "$1" != python ] && [ "$1" != python3 ]; do shift; done
	[ "$#" -gt 0 ] || exit 2
	shift
	exec "$FAKE_PY" "$@"
fi
[ "${1:-}" = --version ] && echo "uv 0.11.32"
exit 0
"""


def _job():
    import yaml  # PyYAML, locked in pipeline/uv.lock through gdtoolkit

    jobs = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]
    assert len(jobs) == 1, f"one job, found {sorted(jobs)}"
    return next(iter(jobs.values()))


def _delivery(step):
    """The dry run's archive upload and the draft Release: the two steps one input decides."""
    return "actions/upload-artifact" in step.get("uses", "") or "gh release create" in step.get(
        "run", ""
    )


def test_no_step_but_the_two_delivery_steps_can_be_skipped():
    job = _job()
    assert "if" not in job, f"the job itself is skipped by {job.get('if')!r}"
    steps = job["steps"]
    assert sum(_delivery(step) for step in steps) == 2, "the dry run's upload and the draft Release"
    for step in steps:
        if not _delivery(step):
            assert "if" not in step, f"step {step.get('name')!r} is skipped by {step.get('if')!r}"
    names = " | ".join(step.get("name", "") for step in steps)
    for checked in ("the sha is on main", "Python, from the pins"):
        assert checked in names, f"no step named {checked!r}: the census would hold nothing"


def _python_step():
    runs = [
        s["run"] for s in _job()["steps"] if re.search(r"\buv python install\b", s.get("run", ""))
    ]
    assert len(runs) == 1, "one step installing the pinned Python"
    return runs[0]


def _python_run(tmp_path, pin):
    """The Python step, run as GitHub runs a bash step, with tools/pins.sh's pin set to `pin`."""
    text = PINS.read_text(encoding="utf-8")
    assert len(PYTHON_LINE.findall(text)) == 1, "one PYTHON_VERSION line in tools/pins.sh"
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "pins.sh").write_text(
        PYTHON_LINE.sub(f'PYTHON_VERSION="{pin}"', text), encoding="utf-8"
    )
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "uv").write_text(FAKE_UV, encoding="utf-8")
    (bin_dir / "uv").chmod(0o755)
    (tmp_path / "github_env").write_text("", encoding="utf-8")
    env = {
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "HOME": str(tmp_path),
        "FAKE_UV_CALLS": str(tmp_path / "calls.txt"),
        "FAKE_PY": sys.executable,
        "GITHUB_ENV": str(tmp_path / "github_env"),
        **{k: str(v) for k, v in _job().get("env", {}).items() if not str(v).startswith("${{")},
    }
    return subprocess.run(
        [BASH, "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", _python_step()],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _lookalikes():
    major, minor, micro = THIS_PYTHON.split(".")
    return {
        "a-prefix": THIS_PYTHON[:-1],
        "a-suffix": f"{minor}.{micro}",
        "a-digit-longer": f"{THIS_PYTHON}0",
        "a-leading-digit-longer": f"1{THIS_PYTHON}",
        "a-part-longer": f"{THIS_PYTHON}.1",
        "major-minor-alone": f"{major}.{minor}",
    }


@bash_only
def test_the_pin_equal_to_the_interpreter_passes(tmp_path):
    """The control of the next test: the harness itself is not what fails."""
    done = _python_run(tmp_path, THIS_PYTHON)
    assert done.returncode == 0, done.stdout + done.stderr


@bash_only
@pytest.mark.parametrize("name", list(_lookalikes()))
def test_a_pin_that_only_resembles_the_interpreter_is_refused(tmp_path, name):
    pin = _lookalikes()[name]
    assert pin != THIS_PYTHON
    done = _python_run(tmp_path, pin)
    out = done.stdout + done.stderr
    assert f"Python {THIS_PYTHON}" in out, f"the step got as far as printing the version: {out}"
    assert done.returncode != 0, f"pin {pin} was accepted for Python {THIS_PYTHON}: {out}"
    assert pin in out and THIS_PYTHON in out, f"the refusal names both: {out}"


# ------------------------------------------------------------------ §C's pair, twice told

RELEASE_MD = REPO / "docs" / "RELEASE.md"
MANIFEST = "game/assets/generated/manifest.json"
HEX64 = re.compile(r"(?<![0-9a-fA-F])[0-9a-f]{64}(?![0-9a-fA-F])")
SIZE = r"(\d{1,3}(?:'\d{3})+|\d{4,})"


def _bullet_and_command():
    """§C's list item holding the manifest-pair command, and the command (one inline span)."""
    text = RELEASE_MD.read_text(encoding="utf-8")
    start = text.index("\n## C. ")
    section = text[start : text.index("\n## ", start + 1)]
    spans = [
        span
        for span in re.findall(r"`([^`\n]+)`", section)
        if f"wc -c < {MANIFEST}" in span and "sha256sum -c" in span
    ]
    assert len(spans) == 1, f"one manifest-pair command in §C, found {spans}"
    command = spans[0]
    items = re.split(r"\n(?=- \[[ x]\] )", section)
    bullets = [item for item in items if command in item]
    assert len(bullets) == 1, "the command sits in one list item of §C"
    return bullets[0], command


def test_the_command_spells_the_pair_its_bullet_names_first():
    bullet, command = _bullet_and_command()
    prose = bullet.replace(command, "")
    sizes = re.findall(rf"{SIZE} bytes", prose)
    shas = HEX64.findall(prose)
    assert sizes and shas, f"the bullet's prose names a size and a SHA-256 in full: {prose}"
    plan_size, plan_sha = sizes[0].replace("'", ""), shas[0]
    command_sizes = re.findall(rf"(?<![\w.]){SIZE}(?![\w.])", HEX64.sub("", command))
    assert len(command_sizes) == 2, f"the size is spelt twice in the command: {command_sizes}"
    assert set(command_sizes) == {plan_size}, (command_sizes, plan_size)
    assert set(HEX64.findall(command)) == {plan_sha}, (HEX64.findall(command), plan_sha)
