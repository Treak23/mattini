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

Does NOT prove: that GitHub runs it (the session's dry run on GitHub after the batch lands,
then the live run); that the runner has the disk, memory and time (the same run); that the
hook still installs Godot in a fresh container (a census of its text: the next session's
start is that proof); anything about the bytes the steps write.
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
    "shadows",
    "sky",
    "manifest",
]
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
    for dataset in ("terrain", "buildings", "photo", "surface", "tlm"):
        assert re.search(rf"\b{dataset}\b", downloads), f"the {dataset} download"
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
