"""Pinning tests for brief v0.4.0-07 (brief M4-09 cut to the sky): `python -m mattini sky`
ends in one line, never a traceback.

Pinned decisions (brief M4-09 decision 1, the sky only): `python -m mattini sky` takes `--out`
only (default game/assets/generated; it reads no download, so it has no `--raw`); it loads
config/world.json and config/sky.json through the modules (`mattini.sky.load_sky_config`),
calls `sky.build_sky(world, sky_config, out_dir, progress=…)` through the module, then writes
the manifest and prints its path, as the other steps do. With the committed configs it writes
`sky/village.json`, exactly config/sky.json's values with the area and the world's SHA-256
(`json.dumps(block, indent=2, sort_keys=True, ensure_ascii=False)` and an LF), no `.part` left,
and the manifest's `sky` block is that description, every other block null. A refusal (a
SkyError: here a sky config computed for another world) is one `mattini: error: ...` line on
stderr, exit status 1, nothing on stdout, no traceback and nothing written. A Ctrl-C during
the step is caught: one line on stderr starting `mattini: ` that names `python -m mattini sky`
to run again, exit status 130. The help lists the commands in pipeline order: lock, download,
terrain, buildings, photo, roofs, surfaces, trees, sky, manifest.

Each command runs as the owner runs it, `python -m mattini`'s `main` in a process of its own
(an uncaught exception prints its traceback there), with the network refused.

Does NOT prove: that every other input ends in a refusal (test_m4_09_sky_step.py has the
step's own), nor a Ctrl-C at every point of the step.
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

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
    from mattini import sky

    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt

    sky.build_sky = interrupted
if spec["other_world"]:
    from mattini import sky

    load = sky.load_sky_config

    def computed_for_another_world(*args, **kwargs):
        data = load(*args, **kwargs)
        (area,) = data["areas"].values()
        area["computed_for"]["world_sha256"] = "ab" * 32
        return data

    sky.load_sky_config = computed_for_another_world
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
    "sky",
    "manifest",
]


def _run(tmp_path, argv, *, interrupt=False, other_world=False):
    spec = {"argv": argv, "interrupt": interrupt, "other_world": other_world}
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
    assert sorted(p.name for p in out.iterdir()) == ["manifest.json", "sky"]
    manifest = json.loads((out / "manifest.json").read_bytes())
    assert manifest["sky"] == block
    assert [
        key for key, value in manifest.items() if isinstance(value, dict) and key != "world"
    ] == ["sky"]


def test_sky_has_no_raw_option(tmp_path):
    done = _run(tmp_path, ["sky", "--raw", str(tmp_path), "--out", str(tmp_path / "out")])
    assert done.returncode == 2 and "unrecognized arguments: --raw" in done.stderr, done.stderr
    assert not (tmp_path / "out").exists()


def test_a_sky_config_for_another_world_is_one_error_line_and_writes_nothing(tmp_path):
    out = tmp_path / "out"
    line = _one_line(_run(tmp_path, ["sky", "--out", str(out)], other_world=True), 1)
    assert "design recomputes" in line and "config/sky.json" in line, line
    assert "python -m mattini sky" not in line, line
    assert not out.exists(), "a refusal writes nothing"


def test_a_ctrl_c_in_the_sky_step_names_the_command_to_run_again(tmp_path):
    argv = ["sky", "--out", str(tmp_path / "out")]
    line = _one_line(_run(tmp_path, argv, interrupt=True), 130, prefix="mattini: ")
    assert "python -m mattini sky" in line, line


def test_the_help_lists_the_commands_in_pipeline_order(tmp_path):
    done = _run(tmp_path, ["--help"])
    assert done.returncode == 0, done.stderr
    assert "{" + ",".join(PIPELINE_ORDER) + "}" in done.stdout, done.stdout
