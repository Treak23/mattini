"""Pinning tests for brief v0.5.0-06: .github/workflows/release.yml, read as YAML.

Pinned decisions (the owner's 1a, docs/history/blocked/2026-10-29-2.md: a GitHub Actions
workflow, workflow_dispatch, contents: write, only the runner's GITHUB_TOKEN, a draft Release the
owner publishes; CLAUDE.md Hard Rule 1; brief v0.5.0-06 decisions 1, 2 and 6):
- the only trigger is workflow_dispatch; its inputs are exactly sha, version, manifest_bytes,
  manifest_sha256 (required strings) and dry_run (a boolean, default true: a run nobody set
  creates no Release);
- the workflow's permissions are exactly `contents: write` and no job widens them; no secret but
  GITHUB_TOKEN is named; no `${{ ... }}` inside a `run:` (the inputs reach the shell through the
  job's env, so an input cannot become a command: RELEASE_SHA, RELEASE_VERSION, MANIFEST_BYTES,
  MANIFEST_SHA256); the only actions used are actions/checkout and actions/upload-artifact;
  checkout of the sha keeps no credentials;
- one job, on an Ubuntu runner, with timeout-minutes between 60 and 360; bash for every run
  (pipefail);
- the first step refuses malformed inputs (run here as bash with the job's env: exit 0 for good
  inputs, 1 for each bad one), before any download;
- the order: the inputs, checkout, Godot from tools/pins.sh, the downloads, the pipeline in
  docs/RELEASE.md §C's order with `shadows` before `sky` and `manifest` last, the manifest pair
  (`sha256sum -c` against the inputs), tools/export.sh, tools/release_checks.sh,
  tools/release_pack.sh, then either the artifact (dry run, 3 days) or `gh release create
  v<version> --draft --target <sha>` with the rendered notes and the three assets, GH_TOKEN from
  GITHUB_TOKEN;
- the pins' one home: tools/pins.sh holds Godot's URL and SHA-256 and uv's version; the hook
  and the workflow source it and spell no SHA-256 of their own.

Since the release's checkers (2026-10-30; brief v0.5.0-06 decisions 1 and 2): nothing lets a
failure through: no `continue-on-error` anywhere, no run text with `|| true`, `|| :`, `|| exit 0`
or `set +e`, no step `if` with always(), failure() or cancelled(); the Godot step pipes
GODOT_SHA256 into `sha256sum -c` before it unpacks the zip; the manifest pair's step, run here as
bash with the job's env, exits 0 for the pair and non-zero for another size or another SHA-256;
the step after checkout, run here in a scratch repository, exits non-zero when HEAD is not
RELEASE_SHA; the export step greps its log for ", as written here"; every `uv sync` and `uv run`
is `--frozen`.

Since brief v0.6.0-03 (the 0.5.0 residue: R1-CD-04, owner N2; this file re-pinned whole, the
tests above unchanged):
- the Release's Python interpreter is pinned: tools/pins.sh holds PYTHON_VERSION, exactly
  3.13.14 (the uv-managed CPython the 0.5.0 Release's run 41095845807 used, its log's "Using
  CPython 3.13.14"); the job's env sets UV_PYTHON_PREFERENCE to only-managed; one step after uv's
  and before the downloads sources tools/pins.sh, runs `uv python install "$PYTHON_VERSION"`
  before any `uv sync`, writes `UV_PYTHON=<the pin>` into $GITHUB_ENV (so every later uv call
  uses it), prints `python --version` and zlib.ZLIB_RUNTIME_VERSION into the log and refuses
  (exit non-zero, naming both) an interpreter other than the pin. Run here as bash with a
  stand-in uv whose `uv run ... python ...` runs this Python: a pin equal to this Python's
  version exits 0, another pin exits non-zero. The workflow spells no Python version of its
  own; pipeline/.python-version and pyproject's requires-python are unchanged, and the
  container's hook and gate keep their system Python (neither names PYTHON_VERSION or
  UV_PYTHON: the pipeline's own byte checks refuse another zlib or JPEG encoder, lesson 43);
- a Release is refused from a sha not on main: one step after the checkout's and before Godot
  (so before any download) fetches main's history alone and refuses unless `git merge-base
  --is-ancestor "$RELEASE_SHA"` main exits 0, naming the sha and main. Run here in a shallow
  checkout of the sha (as actions/checkout leaves it) from a scratch origin with main, dist and
  another branch: exit 0 for main's tip and for an older commit of main, non-zero for a commit
  of another branch (its output names the sha and main), and no branch but main fetched.

Since brief v0.6.0-10 (design §1, §2 and §6: the far terrain's two inputs and two steps; this
file re-pinned whole on v0.6.0-03's, only PIPELINE, DOWNLOADS, the order test's download loop
and this paragraph change): the downloads step also fetches `download regio` (swissALTIRegio)
and `download farphoto` (SWISSIMAGE 2 m), and the pipeline runs `surroundings`, then
`farcolour`, after `trees` and before `shadows` (`python -m mattini`'s own order, brief v0.6.0-07
decision 1), so the far terrain's block is in the manifest the pair checks.

Does NOT prove: that GitHub runs it (the session's dry run on GitHub after the batch lands,
then the live run); that the runner has the disk, memory and time (the same run); that the
hook still installs Godot in a fresh container (a census of its text: the next session's
start is that proof); anything about the bytes the steps write; that uv on the runner can
download CPython 3.13.14 or that its zlib is the one design's bytes need (the pipeline's own
checks and the dry run); that the runner's origin answers an unauthenticated fetch of main
(true while the repository is public: the dry run).
"""

import hashlib
import re
import subprocess
import sys

import pytest
from fake_tools import BASH, REPO

WORKFLOW = REPO / ".github" / "workflows" / "release.yml"
PINS = REPO / "tools" / "pins.sh"
HOOK = REPO / ".claude" / "hooks" / "session-start.sh"
INPUT_ENV = {
    "RELEASE_SHA": "${{ inputs.sha }}",
    "RELEASE_VERSION": "${{ inputs.version }}",
    "MANIFEST_BYTES": "${{ inputs.manifest_bytes }}",
    "MANIFEST_SHA256": "${{ inputs.manifest_sha256 }}",
}
GOOD = {
    "RELEASE_SHA": "0123456789abcdef0123456789abcdef01234567",
    "RELEASE_VERSION": "0.5.0",
    "MANIFEST_BYTES": "324931",
    "MANIFEST_SHA256": "a03c5722da8231349323f71d61e2db2f1cbb6919070d545177d9a31caf510ce5",
}
PIPELINE = [
    "terrain",
    "buildings",
    "photo",
    "roofs",
    "surfaces",
    "trees",
    "surroundings",
    "farcolour",
    "shadows",
    "sky",
    "manifest",
]
# What the downloads step fetches, `python -m mattini download <name>` each.
DOWNLOADS = ("terrain", "buildings", "photo", "surface", "tlm", "regio", "farphoto")
HEX64 = re.compile(r"(?<![0-9a-fA-F])[0-9a-fA-F]{64}(?![0-9a-fA-F])")


def _text():
    assert WORKFLOW.is_file(), ".github/workflows/release.yml is missing"
    return WORKFLOW.read_text(encoding="utf-8")


def _workflow():
    import yaml  # PyYAML, locked in pipeline/uv.lock through gdtoolkit

    return yaml.safe_load(_text())


def _job():
    jobs = _workflow()["jobs"]
    assert len(jobs) == 1, f"one job, found {sorted(jobs)}"
    return next(iter(jobs.values()))


def _steps():
    return _job()["steps"]


def _runs():
    """Every step's run text, in step order (a step without one gives "")."""
    return [step.get("run", "") for step in _steps()]


def _first_step(predicate, what):
    for index, step in enumerate(_steps()):
        if predicate(step):
            return index
    raise AssertionError(f"no step {what}")


def _run_with(pattern, what):
    return _first_step(lambda step: re.search(pattern, step.get("run", "")), what)


def test_the_only_trigger_is_workflow_dispatch():
    workflow = _workflow()
    on = workflow.get("on", workflow.get(True))  # YAML 1.1 reads a bare `on` as true
    assert isinstance(on, dict) and list(on) == ["workflow_dispatch"], on


def test_the_inputs():
    workflow = _workflow()
    inputs = workflow.get("on", workflow.get(True))["workflow_dispatch"]["inputs"]
    assert set(inputs) == {"sha", "version", "manifest_bytes", "manifest_sha256", "dry_run"}
    for name in ("sha", "version", "manifest_bytes", "manifest_sha256"):
        assert inputs[name].get("required") is True, name
        assert inputs[name].get("type") == "string", name
    assert inputs["dry_run"].get("type") == "boolean"
    assert inputs["dry_run"].get("default") is True, "a run nobody set creates no Release"


def test_the_permissions_are_exactly_contents_write():
    workflow = _workflow()
    assert workflow.get("permissions") == {"contents": "write"}
    for name, job in workflow["jobs"].items():
        assert job.get("permissions", {"contents": "write"}) == {"contents": "write"}, name


def test_no_secret_but_the_runner_s_token():
    named = set(re.findall(r"secrets\.([A-Za-z0-9_]+)", _text()))
    assert named <= {"GITHUB_TOKEN"}, named


def test_no_expression_inside_a_run():
    for index, run in enumerate(_runs()):
        assert "${{" not in run, f"step {index}: an expression in run: {run}"


def test_the_inputs_reach_the_shell_through_the_job_s_env():
    env = _job().get("env", {})
    for name, value in INPUT_ENV.items():
        assert env.get(name) == value, (name, env.get(name))


def test_only_first_party_actions():
    for step in _steps():
        if "uses" in step:
            action = step["uses"].split("@")[0]
            assert action in {"actions/checkout", "actions/upload-artifact"}, step["uses"]


def test_the_checkout_is_the_sha_without_credentials():
    index = _first_step(lambda s: s.get("uses", "").startswith("actions/checkout@"), "checkout")
    with_ = _steps()[index].get("with", {})
    assert with_.get("ref") == "${{ inputs.sha }}"
    assert with_.get("persist-credentials") is False


def test_one_ubuntu_job_with_a_timeout_and_bash():
    job = _job()
    assert str(job.get("runs-on", "")).startswith("ubuntu-"), job.get("runs-on")
    timeout = job.get("timeout-minutes")
    assert isinstance(timeout, int) and 60 <= timeout <= 360, timeout
    shell = _workflow().get("defaults", {}).get("run", {}).get("shell")
    assert shell == "bash" or all(s.get("shell") == "bash" for s in _steps() if "run" in s)


def _validate(env):
    run = _steps()[0].get("run", "")
    return subprocess.run(
        [BASH, "-e", "-o", "pipefail", "-c", run],
        env={"PATH": "/usr/bin:/bin", **env},
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.skipif(BASH is None or sys.platform != "linux", reason="runs a step with bash")
def test_the_first_step_accepts_good_inputs():
    assert "uses" not in _steps()[0], "the inputs are checked before anything else"
    done = _validate(GOOD)
    assert done.returncode == 0, done.stdout + done.stderr


@pytest.mark.skipif(BASH is None or sys.platform != "linux", reason="runs a step with bash")
@pytest.mark.parametrize(
    "name, value",
    [
        ("RELEASE_SHA", "0123456"),
        ("RELEASE_SHA", "0123456789abcdef0123456789abcdef01234567; rm -rf ."),
        ("RELEASE_SHA", "0123456789ABCDEF0123456789ABCDEF01234567"),
        ("RELEASE_VERSION", "v0.5.0"),
        ("RELEASE_VERSION", "0.5"),
        ("RELEASE_VERSION", "0.5.0 && echo"),
        ("MANIFEST_BYTES", "0"),
        ("MANIFEST_BYTES", "32a"),
        ("MANIFEST_SHA256", "a03c5722"),
        ("MANIFEST_SHA256", ""),
    ],
)
def test_the_first_step_refuses_a_bad_input(name, value):
    done = _validate({**GOOD, name: value})
    assert done.returncode == 1, (name, value, done.stdout + done.stderr)


def test_the_steps_run_in_release_order():
    order = [
        ("the inputs", 0),
        ("checkout", _first_step(lambda s: "actions/checkout" in s.get("uses", ""), "checkout")),
        ("Godot", _run_with(r"\. tools/pins\.sh[\s\S]*GODOT_SHA256", "installing Godot")),
        ("the downloads", _run_with(r"python -m mattini download\b", "downloading")),
    ]
    for command in PIPELINE:
        order.append(
            (command, _run_with(rf"python -m mattini {command}(\s|$)", f"running {command}"))
        )
    order += [
        ("the manifest pair", _run_with(r"MANIFEST_SHA256[\s\S]*sha256sum -c", "the pair")),
        ("export", _run_with(r"(^|\s)tools/export\.sh", "exporting")),
        ("checks", _run_with(r"(^|\s)tools/release_checks\.sh", "the release checks")),
        ("pack", _run_with(r"(^|\s)tools/release_pack\.sh", "packing")),
        ("release", _run_with(r"gh release create", "creating the Release")),
    ]
    indices = [index for _, index in order]
    assert indices == sorted(indices), order
    joined = "\n".join(_runs())
    positions = [joined.index(f"python -m mattini {command}") for command in PIPELINE]
    assert positions == sorted(positions), "the pipeline in RELEASE.md §C's order"
    downloads = _steps()[order[3][1]]["run"]
    for dataset in DOWNLOADS:
        assert re.search(rf"python -m mattini download {dataset}(\s|$)", downloads), (
            f"the {dataset} download"
        )
    pair = _steps()[order[4 + len(PIPELINE)][1]]["run"]
    assert "MANIFEST_BYTES" in pair and "manifest.json" in pair


def test_a_dry_run_uploads_the_archives_for_three_days():
    index = _first_step(
        lambda s: s.get("uses", "").startswith("actions/upload-artifact@"), "uploading"
    )
    step = _steps()[index]
    assert re.sub(r"[\s${}]", "", str(step.get("if", ""))) == "inputs.dry_run", step.get("if")
    assert step["with"].get("retention-days") == 3
    path = step["with"].get("path", "")
    for name in ("-linux.tar.gz", "-windows.zip", "SHA256SUMS"):
        assert name in path, name
    assert index > _run_with(r"tools/release_pack\.sh", "packing")


def test_a_real_run_creates_a_draft_release_with_the_runner_s_token():
    index = _run_with(r"gh release create", "creating the Release")
    step = _steps()[index]
    assert re.sub(r"[\s${}]", "", str(step.get("if", ""))) == "!inputs.dry_run", step.get("if")
    run = step["run"]
    assert re.search(r'gh release create "v\$RELEASE_VERSION"', run), run
    assert "--draft" in run and '--target "$RELEASE_SHA"' in run and "--notes-file" in run
    for name in ("-linux.tar.gz", "-windows.zip", "SHA256SUMS"):
        assert name in run, name
    assert "--latest" not in run and "--draft=false" not in run
    assert "gh release edit" not in _text() and "gh release upload" not in _text()
    token = step.get("env", {}).get("GH_TOKEN")
    assert token in {"${{ secrets.GITHUB_TOKEN }}", "${{ github.token }}"}, token


def test_the_pins_have_one_home():
    assert PINS.is_file(), "tools/pins.sh is missing"
    done = subprocess.run(
        [BASH or "bash", "-c", '. "$1"; echo "$GODOT_URL|$GODOT_SHA256|$UV_VERSION"', "-", PINS],
        capture_output=True,
        text=True,
        check=True,
    )
    url, sha, uv = done.stdout.strip().split("|")
    assert url.startswith("https://downloads.godotengine.org/?version=4.6.3&"), url
    assert re.fullmatch(r"[0-9a-f]{64}", sha), sha
    assert re.fullmatch(r"\d+\.\d+\.\d+", uv), uv
    assert not HEX64.search(_text()), "the workflow spells a SHA-256 of its own"
    hook = HOOK.read_text(encoding="utf-8")
    assert sha not in hook and not HEX64.search(hook), "the hook spells a SHA-256 of its own"
    sourced = re.search(r"^\. .*tools/pins\.sh\"?\s*$", hook, re.MULTILINE)
    assert sourced, "the hook sources tools/pins.sh"
    first_use = hook.index("$GODOT_URL")
    assert sourced.start() < first_use, "before it uses the pins"
    assert "uv==$UV_VERSION" in _text(), "the runner's uv is the pinned one"


FORGIVING = [
    re.compile(r"\|\|\s*(?:true|:)(?![\w-])"),
    re.compile(r"\|\|\s*exit\s+0\b"),
    re.compile(r"\bset\s+(?:\+e\b|\+o\s+errexit\b)"),
]


def _keys(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from _keys(value)
    elif isinstance(node, list):
        for value in node:
            yield from _keys(value)


def test_nothing_lets_a_failure_through():
    assert "continue-on-error" not in set(map(str, _keys(_workflow()))), "continue-on-error"
    assert "continue-on-error" not in _text()
    for index, run in enumerate(_runs()):
        for pattern in FORGIVING:
            assert not pattern.search(run), f"step {index}: {pattern.pattern} in {run}"
    for index, step in enumerate(_steps()):
        condition = str(step.get("if", ""))
        assert not re.search(r"\b(always|failure|cancelled)\(", condition), (index, condition)


def test_the_godot_zip_is_checked_against_the_pin():
    index = _run_with(r"\. tools/pins\.sh[\s\S]*GODOT_URL", "installing Godot")
    lines = _steps()[index]["run"].splitlines()
    check = [
        n
        for n, line in enumerate(lines)
        if re.search(r"\$GODOT_SHA256\b.*\|\s*sha256sum (-c|--check)\b", line)
    ]
    assert check, "the zip's SHA-256 is piped into sha256sum -c"
    unzip = [n for n, line in enumerate(lines) if re.search(r"\bunzip\b", line)]
    assert unzip and check[0] < unzip[0], "and checked before it is unpacked"


def _bash_step(run, cwd, env):
    """A step's run as GitHub's `shell: bash` runs it (bash -e -o pipefail)."""
    return subprocess.run(
        [BASH, "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", run],
        cwd=cwd,
        env={"PATH": "/usr/bin:/bin", **env},
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.skipif(BASH is None or sys.platform != "linux", reason="runs a step with bash")
def test_the_manifest_pair_s_failure_fails_the_run(tmp_path):
    index = _run_with(r"MANIFEST_SHA256[\s\S]*sha256sum -c", "the pair")
    step = _steps()[index]
    assert "if" not in step and "continue-on-error" not in step, step
    manifest = tmp_path / "game" / "assets" / "generated" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    data = b'{"schema": 1}\n'
    manifest.write_bytes(data)
    pair = {"MANIFEST_BYTES": str(len(data)), "MANIFEST_SHA256": hashlib.sha256(data).hexdigest()}
    done = _bash_step(step["run"], tmp_path, pair)
    assert done.returncode == 0, done.stdout + done.stderr
    for name, value in (("MANIFEST_BYTES", str(len(data) + 1)), ("MANIFEST_SHA256", "ab" * 32)):
        done = _bash_step(step["run"], tmp_path, {**pair, name: value})
        assert done.returncode != 0, (name, done.stdout + done.stderr)


@pytest.mark.skipif(BASH is None or sys.platform != "linux", reason="runs a step with bash")
def test_the_checkout_is_verified_to_be_the_sha(tmp_path):
    checkout = _first_step(lambda s: "actions/checkout" in s.get("uses", ""), "checkout")
    index = _run_with(r"git rev-parse HEAD", "comparing HEAD with the sha")
    godot = _run_with(r"\. tools/pins\.sh[\s\S]*GODOT_URL", "installing Godot")
    assert checkout < index < godot, (checkout, index, godot)
    run = _steps()[index]["run"]
    assert "RELEASE_SHA" in run, run
    git = [
        "git",
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@example.invalid",
        "-c",
        "commit.gpgsign=false",
    ]
    subprocess.run([*git, "init", "-q", str(tmp_path)], check=True)
    subprocess.run(
        [*git, "-C", str(tmp_path), "commit", "-q", "--allow-empty", "-m", "t"], check=True
    )
    head = subprocess.run(
        ["git", "-C", str(tmp_path), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    done = _bash_step(run, tmp_path, {"RELEASE_SHA": head})
    assert done.returncode == 0, done.stdout + done.stderr
    done = _bash_step(run, tmp_path, {"RELEASE_SHA": "0" * 40})
    assert done.returncode != 0, "another commit than the sha is refused"


def test_the_export_log_must_say_as_written_here():
    run = _steps()[_run_with(r"(^|\s)tools/export\.sh", "exporting")]["run"]
    lines = run.splitlines()
    export = [n for n, line in enumerate(lines) if re.search(r"(^|\s)tools/export\.sh", line)]
    grep = [n for n, line in enumerate(lines) if re.search(r"\bgrep\b.*, as written here", line)]
    assert grep and export[0] < grep[0], run


def test_every_uv_call_is_frozen():
    calls = [
        line
        for run in _runs()
        for line in run.splitlines()
        if re.search(r"\buv (sync|run)\b", line)
    ]
    assert len(calls) >= 3, calls
    for line in calls:
        assert "--frozen" in line, line


# Since brief v0.6.0-03 ---------------------------------------------------------------------

PYTHON_PIN = "3.13.14"  # the 0.5.0 Release's interpreter (run 41095845807: "Using CPython 3.13.14")
PYTHON_LINE = re.compile(r'^PYTHON_VERSION="([^"]*)"[ \t]*(?:#.*)?$', re.MULTILINE)
THIS_PYTHON = "{}.{}.{}".format(*sys.version_info[:3])

FAKE_UV_RUN = r"""#!/usr/bin/env bash
# A stand-in uv (test_release_workflow.py): records each call as UV_PYTHON|UV_PYTHON_PREFERENCE|args;
# `uv run ... python <args>` runs the test's Python with <args>; everything else exits 0.
printf '%s|%s|%s\n' "${UV_PYTHON:-}" "${UV_PYTHON_PREFERENCE:-}" "$*" >> "$FAKE_UV_CALLS"
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


def _python_step():
    return _run_with(r"\buv python install\b", "installing the pinned Python")


def test_the_python_pin_has_one_home():
    assert PINS.is_file(), "tools/pins.sh is missing"
    found = PYTHON_LINE.findall(PINS.read_text(encoding="utf-8"))
    assert found == [PYTHON_PIN], f"tools/pins.sh's PYTHON_VERSION lines: {found}"
    done = subprocess.run(
        [BASH or "bash", "-c", '. "$1"; echo "$PYTHON_VERSION"', "-", PINS],
        capture_output=True,
        text=True,
        check=True,
    )
    assert done.stdout.strip() == PYTHON_PIN, done.stdout
    assert PYTHON_PIN not in _text(), "the workflow spells a Python version of its own"
    env = _job().get("env", {})
    assert env.get("UV_PYTHON_PREFERENCE") == "only-managed", env
    assert "UV_PYTHON" not in env, "UV_PYTHON comes from the pins, through GITHUB_ENV"


def test_the_container_keeps_its_own_python():
    """The hook and the gate keep the container's system Python (lesson 43: the pipeline's own
    byte checks refuse another zlib or JPEG encoder); the project's Python lines are unchanged."""
    for path in (HOOK, REPO / "tools" / "gate.sh"):
        text = path.read_text(encoding="utf-8")
        for name in ("PYTHON_VERSION", "UV_PYTHON"):
            assert name not in text, f"{path.name} names {name}"
    assert (REPO / "pipeline" / ".python-version").read_text(encoding="utf-8") == "3.13\n"
    pyproject = (REPO / "pipeline" / "pyproject.toml").read_text(encoding="utf-8")
    assert re.search(r'^requires-python = ">=3\.13,<3\.14"$', pyproject, re.MULTILINE)


def test_the_python_is_installed_before_any_sync_and_before_the_downloads():
    uv = _run_with(r"uv==\$UV_VERSION", "installing uv")
    python = _python_step()
    downloads = _run_with(r"python -m mattini download\b", "downloading")
    assert uv < python < downloads, (uv, python, downloads)
    run = _steps()[python]["run"]
    assert re.search(r"^\s*\. tools/pins\.sh\s*$", run, re.MULTILINE), "the step sources the pins"
    assert re.search(r'uv python install "\$PYTHON_VERSION"', run), run
    lines = [line for run in _runs() for line in run.splitlines()]
    install = next(n for n, line in enumerate(lines) if "uv python install" in line)
    syncs = [n for n, line in enumerate(lines) if re.search(r"\buv sync\b", line)]
    assert syncs and install < syncs[0], "the pinned Python is installed before any uv sync"


def _python_tree(tmp_path, pin):
    """A scratch checkout holding tools/pins.sh with PYTHON_VERSION set to `pin`, and a stand-in uv."""
    text = PINS.read_text(encoding="utf-8")
    assert len(PYTHON_LINE.findall(text)) == 1, "one PYTHON_VERSION line in tools/pins.sh"
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "pins.sh").write_text(
        PYTHON_LINE.sub(f'PYTHON_VERSION="{pin}"', text), encoding="utf-8"
    )
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "uv").write_text(FAKE_UV_RUN, encoding="utf-8")
    (bin_dir / "uv").chmod(0o755)
    (tmp_path / "github_env").write_text("", encoding="utf-8")
    (tmp_path / "github_path").write_text("", encoding="utf-8")
    return {
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "HOME": str(tmp_path),
        "FAKE_UV_CALLS": str(tmp_path / "calls.txt"),
        "FAKE_PY": sys.executable,
        "GITHUB_ENV": str(tmp_path / "github_env"),
        "GITHUB_PATH": str(tmp_path / "github_path"),
        **{k: str(v) for k, v in _job().get("env", {}).items() if not str(v).startswith("${{")},
    }


def _python_run(tmp_path, pin):
    env = _python_tree(tmp_path, pin)
    done = subprocess.run(
        [
            BASH,
            "--noprofile",
            "--norc",
            "-e",
            "-o",
            "pipefail",
            "-c",
            _steps()[_python_step()]["run"],
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    calls_file = tmp_path / "calls.txt"
    calls = calls_file.read_text(encoding="utf-8").splitlines() if calls_file.exists() else []
    return done, [call.split("|", 2) for call in calls]


@pytest.mark.skipif(BASH is None or sys.platform != "linux", reason="runs a step with bash")
def test_the_pinned_python_is_installed_used_and_logged(tmp_path):
    import zlib

    done, calls = _python_run(tmp_path, THIS_PYTHON)
    out = done.stdout + done.stderr
    assert done.returncode == 0, out
    installs = [
        n for n, (_, _, args) in enumerate(calls) if args.split()[:2] == ["python", "install"]
    ]
    assert installs, f"no uv python install: {calls}"
    assert calls[installs[0]][2].split()[2:] == [THIS_PYTHON], calls[installs[0]]
    used = [(n, c) for n, c in enumerate(calls) if c[2].split()[:1] in (["sync"], ["run"])]
    assert used, f"the step runs the pipeline's Python: {calls}"
    for n, (uv_python, preference, args) in used:
        assert n > installs[0], (n, args)
        assert uv_python == THIS_PYTHON or f"--python {THIS_PYTHON}" in args, (uv_python, args)
        assert preference == "only-managed", (preference, args)
    exported = (tmp_path / "github_env").read_text(encoding="utf-8").splitlines()
    assert f"UV_PYTHON={THIS_PYTHON}" in exported, exported
    assert f"Python {THIS_PYTHON}" in out, "python --version in the log"
    zlib_lines = [line for line in out.splitlines() if "zlib" in line.lower()]
    assert any(zlib.ZLIB_RUNTIME_VERSION in line for line in zlib_lines), (
        "zlib.ZLIB_RUNTIME_VERSION in the log",
        out,
    )


@pytest.mark.skipif(BASH is None or sys.platform != "linux", reason="runs a step with bash")
def test_another_python_than_the_pin_is_refused(tmp_path):
    other = "3.13.0" if THIS_PYTHON != "3.13.0" else "3.13.1"
    done, _ = _python_run(tmp_path, other)
    out = done.stdout + done.stderr
    assert done.returncode != 0, out
    assert other in out and THIS_PYTHON in out, f"the refusal names the pin and the Python: {out}"


GIT = [
    "git",
    "-c",
    "user.name=t",
    "-c",
    "user.email=t@example.invalid",
    "-c",
    "commit.gpgsign=false",
]


def _git(*args, cwd):
    return subprocess.run(
        [*GIT, *args], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout.strip()


def _origin(tmp_path):
    """A scratch origin: main (four commits), dist and another branch off main's first commit."""
    origin = tmp_path / "origin"
    origin.mkdir()
    _git("init", "-q", "-b", "main", cwd=origin)
    commits = {}
    for n in range(1, 4):
        _git("commit", "-q", "--allow-empty", "-m", f"main {n}", cwd=origin)
        commits[f"main{n}"] = _git("rev-parse", "HEAD", cwd=origin)
    for branch in ("dist", "other"):
        _git("checkout", "-q", "-b", branch, commits["main1"], cwd=origin)
        _git("commit", "-q", "--allow-empty", "-m", branch, cwd=origin)
        commits[branch] = _git("rev-parse", "HEAD", cwd=origin)
    _git("checkout", "-q", "main", cwd=origin)
    _git("commit", "-q", "--allow-empty", "-m", "main 4", cwd=origin)
    commits["main4"] = _git("rev-parse", "HEAD", cwd=origin)
    return origin, commits


def _checkout(tmp_path, origin, sha):
    """The sha as actions/checkout leaves it: a shallow fetch of the sha alone, detached."""
    work = tmp_path / f"work-{sha[:8]}"
    work.mkdir()
    _git("init", "-q", cwd=work)
    _git("remote", "add", "origin", origin.as_uri(), cwd=work)
    _git("fetch", "-q", "--no-tags", "--depth=1", "origin", sha, cwd=work)
    _git("checkout", "-q", "--detach", sha, cwd=work)
    return work


def _ancestry_step():
    return _run_with(r"git merge-base --is-ancestor", "checking the sha is on main")


def test_the_sha_is_checked_to_be_on_main_before_any_download():
    checkout = _first_step(lambda s: "actions/checkout" in s.get("uses", ""), "checkout")
    index = _ancestry_step()
    godot = _run_with(r"\. tools/pins\.sh[\s\S]*GODOT_URL", "installing Godot")
    downloads = _run_with(r"python -m mattini download\b", "downloading")
    assert checkout < index < godot < downloads, (checkout, index, godot, downloads)
    run = _steps()[index]["run"]
    assert re.search(r'git merge-base --is-ancestor "\$RELEASE_SHA"', run), run
    fetches = [line for line in run.splitlines() if re.search(r"\bgit fetch\b", line)]
    assert fetches, "the step fetches main's history"
    for line in fetches:
        assert re.search(r"\bmain\b", line), f"only main is fetched: {line}"
        assert not re.search(r"--all\b|--unshallow\b|refs/heads/\*", line), line
    with_ = _steps()[checkout].get("with", {})
    assert with_.get("fetch-depth", 1) == 1, "the checkout fetches no other history (dist's packs)"


@pytest.mark.skipif(BASH is None or sys.platform != "linux", reason="runs a step with git and bash")
@pytest.mark.parametrize("name", ["main4", "main2"], ids=["main-s-tip", "an-older-commit-of-main"])
def test_a_sha_on_main_passes(tmp_path, name):
    origin, commits = _origin(tmp_path)
    work = _checkout(tmp_path, origin, commits[name])
    done = _bash_step(_steps()[_ancestry_step()]["run"], work, {"RELEASE_SHA": commits[name]})
    assert done.returncode == 0, done.stdout + done.stderr
    for branch in ("dist", "other"):
        refs = _git("for-each-ref", "--format=%(refname)", cwd=work)
        assert branch not in refs.split("/"), f"{branch} was fetched: {refs}"
        missing = subprocess.run(
            ["git", "cat-file", "-e", commits[branch]], cwd=work, capture_output=True, check=False
        )
        assert missing.returncode != 0, f"{branch}'s commit was fetched"


@pytest.mark.skipif(BASH is None or sys.platform != "linux", reason="runs a step with git and bash")
def test_a_sha_off_main_is_refused_naming_the_sha_and_main(tmp_path):
    origin, commits = _origin(tmp_path)
    work = _checkout(tmp_path, origin, commits["other"])
    done = _bash_step(_steps()[_ancestry_step()]["run"], work, {"RELEASE_SHA": commits["other"]})
    out = done.stdout + done.stderr
    assert done.returncode != 0, out
    assert commits["other"] in out and re.search(r"\bmain\b", out), out
    missing = subprocess.run(
        ["git", "cat-file", "-e", commits["dist"]], cwd=work, capture_output=True, check=False
    )
    assert missing.returncode != 0, "dist's commit was fetched"
