"""Pinning tests for brief M4-09: the new commands end in one line, never a traceback.

Pinned decisions (brief M4-09): `python -m mattini surroundings`, `shadows` and `sky` each
load the committed configs (config/world.json; surroundings and shadows also datasets.json,
datasets.lock.json; each its own config, config/surroundings.json, shadows.json, sky.json),
build into `--out` (default game/assets/generated) from the downloads under `--raw` (default
data/raw; `sky` reads no download and has no `--raw`), then write the manifest and print its
path, as the M3 steps do. They call `<module>.build_<step>` through the module (`sky.build_sky`
for the sky). A refusal is one `mattini: error: ...` line on stderr, exit status 1, nothing on
stdout and no traceback; with no download under `--raw` it names `python -m mattini download
regio` (surroundings) or `download surface` (shadows) and writes nothing under `--out`. A
Ctrl-C during a step is caught: one line on stderr starting `mattini: ` that names the
step's command to run again, exit status 130. The help lists the commands in pipeline order:
lock, download, terrain, buildings, photo, roofs, surfaces, trees, surroundings, shadows, sky,
manifest.

`sky` with the committed configs writes `sky/village.json`, exactly config/sky.json's values
with the area and the world's SHA-256 (`json.dumps(block, indent=2, sort_keys=True,
ensure_ascii=False)` and an LF), and the manifest's `sky` block is that description.

Each command runs as the owner runs it, `python -m mattini`'s `main` in a process of its own
(an uncaught exception prints its traceback there), with the network refused.

Does NOT prove: that every other input ends in a refusal (the steps' own tests), nor a Ctrl-C
at every point of a step.
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

DRIVER = """
import json, sys
import mattini.__main__ as cli
from mattini import download

spec = json.loads(sys.argv[1])

def no_network(*args, **kwargs):
    raise AssertionError("the test reached for the network")

download.urllib_fetch_json = no_network
download.urllib_fetch_file = no_network
if spec["interrupt"]:
    import importlib
    module = importlib.import_module("mattini." + spec["interrupt"])

    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt

    setattr(module, "build_" + spec["interrupt"], interrupted)
if spec.get("record"):
    import importlib
    from pathlib import Path
    module = importlib.import_module("mattini." + spec["record"])

    def record(world, datasets, lock, config, raw_root, out_dir, *, progress=None):
        Path(spec["record_to"]).write_text(json.dumps({
            "world": str(world.path),
            "datasets": sorted(datasets),
            "lock": sorted(lock["datasets"]),
            "config": config,
            "raw_root": str(raw_root),
            "out_dir": str(out_dir),
        }))

    setattr(module, "build_" + spec["record"], record)
sys.exit(cli.main(spec["argv"]))
"""

DOWNLOAD_OF = {
    "surroundings": "python -m mattini download regio",
    "shadows": "python -m mattini download surface",
}
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
    "shadows",
    "sky",
    "manifest",
]


def _run(tmp_path, argv, *, interrupt=None, record=None):
    spec = {"argv": argv, "interrupt": interrupt}
    if record:
        spec.update(record=record, record_to=str(tmp_path / "called.json"))
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


@pytest.mark.parametrize("step", sorted(DOWNLOAD_OF))
def test_a_step_without_its_downloads_is_one_error_line(tmp_path, step):
    raw, out = tmp_path / "raw", tmp_path / "out"
    raw.mkdir()
    line = _one_line(_run(tmp_path, [step, "--raw", str(raw), "--out", str(out)]), 1)
    assert DOWNLOAD_OF[step] in line, line
    assert not out.exists() or not any(out.rglob("*")), "a refusal writes nothing"


@pytest.mark.parametrize("step", sorted(DOWNLOAD_OF))
def test_a_step_builds_with_the_committed_configs_then_writes_the_manifest(tmp_path, step):
    """`build_<step>` replaced by a recorder: it is called once with the committed world,
    datasets config, lock and the step's own config, `--raw` and `--out`; then the manifest
    is written (nothing built: every block null) and its path printed."""
    raw, out = tmp_path / "raw", tmp_path / "out"
    done = _run(tmp_path, [step, "--raw", str(raw), "--out", str(out)], record=step)
    assert done.returncode == 0, done.stderr
    assert done.stdout == f"{out / 'manifest.json'}\n"
    called = json.loads((tmp_path / "called.json").read_text())
    config = json.loads((REPO / "config" / f"{step}.json").read_bytes())
    lock = json.loads((REPO / "config" / "datasets.lock.json").read_bytes())
    datasets = json.loads((REPO / "config" / "datasets.json").read_bytes())
    assert called == {
        "world": str(REPO / "config" / "world.json"),
        "datasets": sorted(datasets["datasets"]),
        "lock": sorted(lock["datasets"]),
        "config": config,
        "raw_root": str(raw),
        "out_dir": str(out),
    }
    manifest = json.loads((out / "manifest.json").read_bytes())
    assert manifest["surroundings"] is None and manifest["shadows"] is None


@pytest.mark.parametrize("step", ["shadows", "sky", "surroundings"])
def test_a_ctrl_c_in_a_step_names_the_command_to_run_again(tmp_path, step):
    argv = [step, "--out", str(tmp_path / "out")]
    if step != "sky":
        (tmp_path / "raw").mkdir()
        argv += ["--raw", str(tmp_path / "raw")]
    line = _one_line(_run(tmp_path, argv, interrupt=step), 130, prefix="mattini: ")
    assert f"python -m mattini {step}" in line, line


def test_sky_writes_the_config_s_values_for_this_world_then_the_manifest(tmp_path):
    out = tmp_path / "out"
    done = _run(tmp_path, ["sky", "--out", str(out)])
    assert done.returncode == 0, done.stderr
    assert "Traceback" not in done.stderr
    assert done.stdout == f"{out / 'manifest.json'}\n"
    world = (REPO / "config" / "world.json").read_bytes()
    (values,) = json.loads((REPO / "config" / "sky.json").read_bytes())["areas"].values()
    block = {
        "area": "village",
        "latitude_deg": values["latitude_deg"],
        "longitude_deg": values["longitude_deg"],
        "true_to_grid_deg": values["true_to_grid_deg"],
        "world_sha256": hashlib.sha256(world).hexdigest(),
    }
    text = json.dumps(block, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    assert (out / "sky" / "village.json").read_bytes() == text.encode("utf-8")
    assert sorted(p.name for p in (out / "sky").iterdir()) == ["village.json"], "no .part left"
    manifest = json.loads((out / "manifest.json").read_bytes())
    assert manifest["sky"] == block
    assert [
        key for key, value in manifest.items() if isinstance(value, dict) and key != "world"
    ] == ["sky"]


def test_the_help_lists_the_commands_in_pipeline_order(tmp_path):
    done = _run(tmp_path, ["--help"])
    assert done.returncode == 0, done.stderr
    assert "{" + ",".join(PIPELINE_ORDER) + "}" in done.stdout, done.stdout
