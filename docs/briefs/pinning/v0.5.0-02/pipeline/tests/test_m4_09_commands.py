"""Pinning tests for briefs v0.4.0-07 and v0.5.0-02 (brief M4-09 cut to the sky, then to the
shadows): `python -m mattini sky` and `python -m mattini shadows` end in one line, never a
traceback.

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
to run again, exit status 130.

Pinned decisions (brief M4-09 decision 1, the shadows only; brief v0.5.0-02): `python -m mattini
shadows` takes `--raw` (default data/raw) and `--out` (default game/assets/generated), as `trees`
does; it loads config/world.json, config/datasets.json, config/datasets.lock.json and
config/shadows.json (`mattini.shadows.load_shadows_config`), calls
`shadows.build_shadows(world, datasets, lock, shadows_config, raw_root, out_dir, progress=…)`
through the module, then writes the manifest and prints its path. With no download under
`--raw` it is one `mattini: error: ...` line naming `python -m mattini download surface`, exit
status 1, nothing on stdout, no traceback, and nothing written under `--out` (the step's own
refusal, caught as a ShadowsError). A Ctrl-C during the step names `python -m mattini shadows`,
exit status 130.

The help lists the commands in pipeline order: lock, download, terrain, buildings, photo, roofs,
surfaces, trees, shadows, sky, manifest.

Each command runs as the owner runs it, `python -m mattini`'s `main` in a process of its own
(an uncaught exception prints its traceback there), with the network refused.

Does NOT prove: that every other input ends in a refusal (test_m4_09_sky_step.py and
test_m4_03_step.py have the steps' own), nor a Ctrl-C at every point of a step; that the shadows
step builds the real village from the command line (the brief's real run).
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
if spec.get("interrupt_shadows"):
    from mattini import shadows

    def interrupted_shadows(*args, **kwargs):
        raise KeyboardInterrupt

    shadows.build_shadows = interrupted_shadows
if spec.get("record_to"):
    from pathlib import Path

    from mattini import shadows

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

    shadows.build_shadows = record
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
    "shadows",
    "sky",
    "manifest",
]


def _run(tmp_path, argv, *, interrupt=False, other_world=False, shadows=None):
    spec = {"argv": argv, "interrupt": interrupt, "other_world": other_world}
    if shadows == "interrupt":
        spec["interrupt_shadows"] = True
    elif shadows == "record":
        spec["record_to"] = str(tmp_path / "called.json")
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


def test_shadows_without_its_download_is_one_error_line_naming_download_surface(tmp_path):
    raw, out = tmp_path / "raw", tmp_path / "out"
    raw.mkdir()
    line = _one_line(_run(tmp_path, ["shadows", "--raw", str(raw), "--out", str(out)]), 1)
    assert "python -m mattini download surface" in line, line
    assert not out.exists(), "a refusal writes nothing, not even the output folder"


def test_shadows_builds_with_the_committed_configs_then_writes_the_manifest(tmp_path):
    """`build_shadows` replaced on the module by a recorder: it is called once with the
    committed world, datasets config, lock and config/shadows.json, `--raw`, `--out` and a
    progress function; then the manifest is written (nothing built: every block null) and its
    path printed, alone, on stdout."""
    raw, out = tmp_path / "raw", tmp_path / "out"
    done = _run(tmp_path, ["shadows", "--raw", str(raw), "--out", str(out)], shadows="record")
    assert done.returncode == 0, done.stderr
    assert "Traceback" not in done.stderr
    assert done.stdout == f"{out / 'manifest.json'}\n"
    called = json.loads((tmp_path / "called.json").read_text())
    config = json.loads((REPO / "config" / "shadows.json").read_bytes())
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
    assert manifest["shadows"] is None and manifest["sky"] is None
    assert sorted(p.name for p in out.iterdir()) == ["manifest.json"]


def test_a_ctrl_c_in_the_shadows_step_names_the_command_to_run_again(tmp_path):
    (tmp_path / "raw").mkdir()
    argv = ["shadows", "--raw", str(tmp_path / "raw"), "--out", str(tmp_path / "out")]
    line = _one_line(_run(tmp_path, argv, shadows="interrupt"), 130, prefix="mattini: ")
    assert "python -m mattini shadows" in line, line
