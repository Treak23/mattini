"""Pinning tests for brief v0.6.0-07: `python -m mattini surroundings` and `farcolour`.

Pinned decisions (brief v0.6.0-07 decisions 1 and 2; brief M4-09 decision 1, re-scoped; brief
v0.5.0-02's wiring of `shadows`, followed):

- `surroundings` and `farcolour` take `--raw` (default data/raw) and `--out` (default
  game/assets/generated), as `trees` and `shadows` do. Each loads config/world.json,
  config/datasets.json, config/datasets.lock.json and config/surroundings.json, the last through
  `surroundings.load_surroundings_config()` looked up on its module when the command runs (the
  config's one reader: `farcolour` reads the same file, design §5); then calls
  `surroundings.build_surroundings(world, datasets, lock, config, raw_root, out_dir,
  progress=…)`, or `farcolour.build_farcolour(...)` with the same arguments, through the module;
  then writes the manifest and prints its path, alone, on stdout.
- With no download under `--raw` each is one `mattini: error: ...` line naming a `python -m
  mattini download` command (`download regio` for `surroundings`; `download regio` or `download
  farphoto` for `farcolour`, the step's own order), exit status 1, nothing on stdout, no
  traceback, and nothing written under `--out`: the steps' own refusals, caught as a
  SurroundingsError or a FarColourError beside the other steps' classes.
- A config the reader refuses is one `mattini: error:` line naming the file, exit status 1,
  nothing written.
- A Ctrl-C during either step names the command to run again, exit status 130.
- The help lists the commands in pipeline order: lock, download, terrain, buildings, photo,
  roofs, surfaces, trees, surroundings, farcolour, shadows, sky, manifest.

Each command runs as the owner runs it, `python -m mattini`'s `main` in a process of its own (an
uncaught exception prints its traceback there), with the network refused.

Does NOT prove: that the steps build the real village from the command line (the brief's real
run); every other input's refusal (the steps' own tests, briefs v0.6.0-04 and -06).
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

DRIVER = """
import copy, json, sys
from pathlib import Path
import mattini.__main__ as cli
from mattini import download, farcolour, surroundings

spec = json.loads(sys.argv[1])

def no_network(*args, **kwargs):
    raise AssertionError("the test reached for the network")

download.urllib_fetch_json = no_network
download.urllib_fetch_file = no_network
real_load = surroundings.load_surroundings_config
if spec.get("config_path"):
    def load_given(*args, **kwargs):
        return real_load(spec["config_path"])

    surroundings.load_surroundings_config = load_given
if spec.get("margin_m") is not None:
    def load_marked(*args, **kwargs):
        data = copy.deepcopy(real_load(*args, **kwargs))
        (area,) = data["areas"].values()
        area["margin_m"] = spec["margin_m"]
        return data

    surroundings.load_surroundings_config = load_marked
module = {"surroundings": surroundings, "farcolour": farcolour}.get(spec.get("step"))
name = "build_" + spec.get("step", "")
if spec.get("interrupt"):
    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt

    setattr(module, name, interrupted)
if spec.get("record_to"):
    def record(world, datasets, lock, config, raw_root, out_dir, *, progress=None):
        Path(spec["record_to"]).write_text(json.dumps({
            "world": str(world.path),
            "datasets": sorted(datasets),
            "lock": sorted(lock["datasets"]),
            "config": config,
            "raw_root": str(raw_root),
            "out_dir": str(out_dir),
            "progress": callable(progress),
        }))
        return {}

    setattr(module, name, record)
sys.exit(cli.main(spec["argv"]))
"""

PIPELINE_ORDER = [
    "lock",
    "download",
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
STEPS = ["surroundings", "farcolour"]
DOWNLOAD = re.compile(r"python -m mattini download (?:regio|farphoto)\b")
ANY_COMMAND = re.compile(r"python -m mattini [a-z]+(?: [a-z]+)?")


def _run(tmp_path, argv, **spec):
    spec["argv"] = argv
    return subprocess.run(  # the exit status is checked by the tests
        [sys.executable, "-c", DRIVER, json.dumps(spec)],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        timeout=120,
        check=False,
    )


def _one_line(done, status: int, prefix: str = "mattini: error: ") -> str:
    assert "Traceback" not in done.stderr and "KeyboardInterrupt" not in done.stderr, done.stderr
    assert done.returncode == status, (done.returncode, done.stderr)
    assert done.stdout == ""
    lines = done.stderr.splitlines()
    assert len(lines) == 1 and lines[0].startswith(prefix), done.stderr
    return lines[0]


def _argv(tmp_path, step):
    (tmp_path / "raw").mkdir(exist_ok=True)
    return [step, "--raw", str(tmp_path / "raw"), "--out", str(tmp_path / "out")]


def test_the_help_lists_the_commands_in_pipeline_order(tmp_path):
    done = _run(tmp_path, ["--help"])
    assert done.returncode == 0, done.stderr
    assert "{" + ",".join(PIPELINE_ORDER) + "}" in done.stdout, done.stdout


def test_surroundings_without_its_download_names_download_regio(tmp_path):
    line = _one_line(_run(tmp_path, _argv(tmp_path, "surroundings")), 1)
    assert set(ANY_COMMAND.findall(line)) == {"python -m mattini download regio"}, line
    assert not (tmp_path / "out").exists(), "a refusal writes nothing, not even the folder"


def test_farcolour_without_its_downloads_names_a_download_command(tmp_path):
    line = _one_line(_run(tmp_path, _argv(tmp_path, "farcolour")), 1)
    named = set(ANY_COMMAND.findall(line))
    assert named and all(DOWNLOAD.fullmatch(c) for c in named), line
    assert not (tmp_path / "out").exists(), "a refusal writes nothing, not even the folder"


@pytest.mark.parametrize("step", STEPS)
def test_each_step_builds_with_the_committed_configs_then_writes_the_manifest(tmp_path, step):
    """The build function replaced on its module by a recorder: called once with the committed
    world, datasets config, lock and config/surroundings.json, `--raw`, `--out` and a progress
    function; then the manifest is written (nothing built: the block null) and its path printed,
    alone, on stdout."""
    raw, out = tmp_path / "raw", tmp_path / "out"
    argv = [step, "--raw", str(raw), "--out", str(out)]
    done = _run(tmp_path, argv, step=step, record_to=str(tmp_path / "called.json"))
    assert done.returncode == 0, done.stderr
    assert "Traceback" not in done.stderr
    assert done.stdout == f"{out / 'manifest.json'}\n"
    called = json.loads((tmp_path / "called.json").read_text())
    config = json.loads((REPO / "config" / "surroundings.json").read_bytes())
    lock = json.loads((REPO / "config" / "datasets.lock.json").read_bytes())
    datasets = json.loads((REPO / "config" / "datasets.json").read_bytes())
    assert called == {
        "world": str(REPO / "config" / "world.json"),
        "datasets": sorted(datasets["datasets"]),
        "lock": sorted(lock["datasets"]),
        "config": config,
        "raw_root": str(raw),
        "out_dir": str(out),
        "progress": True,
    }
    manifest = json.loads((out / "manifest.json").read_bytes())
    assert manifest["surroundings"] is None
    assert sorted(p.name for p in out.iterdir()) == ["manifest.json"]


@pytest.mark.parametrize("step", STEPS)
def test_each_step_reads_the_config_through_its_one_reader(tmp_path, step):
    """`surroundings.load_surroundings_config` replaced on its module: the step is given what
    it returns (here the committed config with margin_m 19950)."""
    argv = _argv(tmp_path, step)
    done = _run(tmp_path, argv, step=step, record_to=str(tmp_path / "called.json"), margin_m=19950)
    assert done.returncode == 0, done.stderr
    config = json.loads((tmp_path / "called.json").read_text())["config"]
    assert config["areas"]["village"]["margin_m"] == 19950


@pytest.mark.parametrize("step", STEPS)
def test_a_config_the_reader_refuses_is_one_error_line_naming_the_file(tmp_path, step):
    data = json.loads((REPO / "config" / "surroundings.json").read_bytes())
    data["areas"]["village"]["spacing_m"] = 50.5
    path = tmp_path / "surroundings.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    line = _one_line(_run(tmp_path, _argv(tmp_path, step), config_path=str(path)), 1)
    assert str(path) in line and "spacing_m" in line, line
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("step", STEPS)
def test_a_ctrl_c_in_the_step_names_the_command_to_run_again(tmp_path, step):
    line = _one_line(
        _run(tmp_path, _argv(tmp_path, step), step=step, interrupt=True), 130, prefix="mattini: "
    )
    assert f"python -m mattini {step}" in line, line
