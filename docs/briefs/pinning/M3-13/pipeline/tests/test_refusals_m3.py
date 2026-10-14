"""Pinning tests for brief M3-13: the new steps on the command line end in one line, never a
traceback.

Pinned decisions (docs/SPEC.md §8; brief M3-13): `python -m mattini photo`, `roofs`,
`surfaces` and `trees` each load the committed configs (config/world.json, datasets.json,
datasets.lock.json, the step's own config and, where its build function takes it,
config/terrain.json), build from the downloads under `--raw` (default data/raw) into
`--out` (default game/assets/generated), then write the manifest and print its path, as
`terrain` and `buildings` do. A refusal is one `mattini: error: ...` line on stderr, exit
status 1, nothing on stdout and no traceback; with no download under `--raw` it names a
`python -m mattini download` command and writes nothing under `--out`. A Ctrl-C during a
step is caught: one line on stderr starting `mattini: ` that names the step's command to
run again, exit status 130 (as the shell reports an interrupted command), no traceback.
The help lists the commands in pipeline order: lock, download, terrain, buildings, photo,
roofs, surfaces, trees, manifest.

Each command runs as the owner runs it, `python -m mattini`'s `main` in a process of its
own (an uncaught exception prints its traceback there), with the network refused. The
Ctrl-C is raised from the step's build function, `<module>.build_<step>`, which the command
calls through its module. M3-01's test_refusals_not_tracebacks.py keeps the earlier
commands' cases.

Does NOT prove: that every other input ends in a refusal (the steps' own tests), nor a Ctrl-C
at every point of a step.
"""

import json
import subprocess
import sys

import pytest

DRIVER = """
import json, sys
import mattini.__main__ as cli
from mattini import download

spec = json.loads(sys.argv[1])

def no_network(*args):
    raise AssertionError("the test reached for the network")

download.urllib_fetch_json = no_network
download.urllib_fetch_file = no_network
if spec["interrupt"]:
    import importlib
    module = importlib.import_module("mattini." + spec["interrupt"])

    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt

    setattr(module, "build_" + spec["interrupt"], interrupted)
sys.exit(cli.main(spec["argv"]))
"""

STEPS = ["photo", "roofs", "surfaces", "trees"]
PIPELINE_ORDER = [
    "lock",
    "download",
    "terrain",
    "buildings",
    "photo",
    "roofs",
    "surfaces",
    "trees",
    "manifest",
]


def _run(tmp_path, argv, *, interrupt=None):
    spec = {"argv": argv, "interrupt": interrupt}
    return subprocess.run(  # the exit status is checked by the tests
        [sys.executable, "-c", DRIVER, json.dumps(spec)],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize("step", STEPS)
def test_a_step_without_its_downloads_is_one_error_line(tmp_path, step):
    raw, out = tmp_path / "raw", tmp_path / "out"
    raw.mkdir()
    done = _run(tmp_path, [step, "--raw", str(raw), "--out", str(out)])
    assert "Traceback" not in done.stderr, done.stderr
    assert done.returncode == 1, (done.returncode, done.stderr)
    assert done.stdout == ""
    lines = done.stderr.splitlines()
    assert len(lines) == 1 and lines[0].startswith("mattini: error: "), done.stderr
    assert "python -m mattini download " in lines[0], lines[0]
    assert not out.exists() or not any(out.rglob("*")), "a refusal writes nothing"


@pytest.mark.parametrize("step", STEPS)
def test_a_ctrl_c_in_a_step_names_the_command_to_run_again(tmp_path, step):
    raw, out = tmp_path / "raw", tmp_path / "out"
    raw.mkdir()
    done = _run(tmp_path, [step, "--raw", str(raw), "--out", str(out)], interrupt=step)
    assert "Traceback" not in done.stderr and "KeyboardInterrupt" not in done.stderr, done.stderr
    assert done.returncode == 130, (done.returncode, done.stderr)
    assert done.stdout == ""
    lines = done.stderr.splitlines()
    assert len(lines) == 1 and lines[0].startswith("mattini: "), done.stderr
    assert f"python -m mattini {step}" in lines[0], lines[0]


def test_the_help_lists_the_commands_in_pipeline_order(tmp_path):
    done = _run(tmp_path, ["--help"])
    assert done.returncode == 0, done.stderr
    assert "{" + ",".join(PIPELINE_ORDER) + "}" in done.stdout, done.stdout
