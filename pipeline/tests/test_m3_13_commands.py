"""Brief M3-13's own tests of the four new commands' wiring and of the manifest's write.

Pinned decisions (brief M3-13, decisions 1 and 2; SPEC §8): `python -m mattini photo`, `roofs`,
`surfaces` and `trees` load config/world.json, datasets.json, datasets.lock.json and their
step's config (the roofs and the trees config/terrain.json too), call `<module>.build_<step>`
with them, `--raw` and `--out` as paths and a `progress` that writes lines to stderr, then
write the manifest to `--out` and print its path alone on stdout. A refusal the step raises
is one `mattini: error:` line and exit status 1, and no manifest is written. The manifest is
written through a `.part` rename: the rename is the last act, the final file is never opened
for writing, and a rename that fails leaves the manifest that was there.

The step is a stand-in that records what it was given; test_refusals_m3.py runs the real
commands as the owner does (a missing download, a Ctrl-C), and the real village's run is the
brief's gate.

Harm prevented: a command that passes a step the wrong config (the terrain config to the
photo, say), one that prints something else beside the manifest's path, and a manifest of
324 KB that a cut write leaves half written, which the game refuses as JSON.

Does NOT prove: that a step builds (their own tests), nor a write cut by a power failure.
"""

import json
import os
from pathlib import Path

import pytest

import mattini.__main__ as cli
from mattini import manifest as manifest_module
from mattini import photo, roofs, surfaces, trees
from mattini.datasets import load_datasets
from mattini.lock import LOCK_PATH, load_lock
from mattini.manifest import FILENAME, write_manifest
from mattini.terrain import load_terrain_config
from mattini.world import REPO, load_world

WORLD_ARGUMENT = REPO / "tests" / "shared" / "terrain_fixture" / "world.json"
BLOCKS = ["buildings", "photo", "roofs", "surfaces", "terrain", "trees"]
# step -> (module, what it is given between the lock and the folders, in order)
STEPS = {
    "photo": (photo, lambda: [photo.load_photo_config()]),
    "roofs": (roofs, lambda: [roofs.load_roofs_config(), load_terrain_config()]),
    "surfaces": (surfaces, lambda: [surfaces.load_surfaces_config()]),
    "trees": (trees, lambda: [trees.load_trees_config(), load_terrain_config()]),
}


@pytest.mark.parametrize("step", sorted(STEPS))
def test_a_step_is_given_the_committed_configs_and_the_folders_then_the_manifest_is_written(
    tmp_path, monkeypatch, capsys, step
):
    module, configs = STEPS[step]
    given = []

    def stand_in(*args, **kwargs):
        given.append((args, kwargs))
        kwargs["progress"]("a progress line")
        return {}

    monkeypatch.setattr(module, f"build_{step}", stand_in)
    raw, out = tmp_path / "raw", tmp_path / "out"
    status = cli.main([step, "--raw", str(raw), "--out", str(out)])
    captured = capsys.readouterr()
    assert status == 0
    ((args, kwargs),) = given
    expected = [load_world(), load_datasets(), load_lock(LOCK_PATH), *configs(), raw, out]
    assert list(args) == expected
    assert [type(a) for a in args[-2:]] == [type(raw), type(out)]
    assert set(kwargs) == {"progress"}
    assert captured.err == "a progress line\n"
    path = out / FILENAME
    assert captured.out == f"{path}\n"
    written = json.loads(path.read_bytes())
    assert {key: written[key] for key in BLOCKS} == dict.fromkeys(BLOCKS)


@pytest.mark.parametrize("step", sorted(STEPS))
def test_a_refusal_of_the_step_is_one_error_line_and_no_manifest(
    tmp_path, monkeypatch, capsys, step
):
    module, _ = STEPS[step]
    error = {"photo": "PhotoError", "roofs": "RoofsError"}.get(step, f"{step.title()}Error")

    def refuse(*args, **kwargs):
        raise getattr(module, error)("the step says no")

    monkeypatch.setattr(module, f"build_{step}", refuse)
    out = tmp_path / "out"
    status = cli.main([step, "--raw", str(tmp_path / "raw"), "--out", str(out)])
    captured = capsys.readouterr()
    assert status == 1
    assert captured.out == ""
    assert captured.err == "mattini: error: the step says no\n"
    assert not (out / FILENAME).exists()


def test_the_manifest_is_written_to_a_part_file_and_renamed(tmp_path, monkeypatch):
    out = tmp_path / "generated"
    seen = []
    real = os.replace

    def replace(source, target):
        source, target = os.fspath(source), os.fspath(target)
        seen.append((source, target, os.path.exists(target), Path(source).read_bytes()))
        real(source, target)

    monkeypatch.setattr(manifest_module.os, "replace", replace)
    path = write_manifest(out, WORLD_ARGUMENT)
    ((source, target, existed, text),) = seen
    assert source == f"{path}.part" and target == str(path) and not existed
    assert text == path.read_bytes() and text.endswith(b"}\n")
    assert sorted(os.listdir(out)) == [FILENAME], "no .part is left"


def test_a_rename_that_fails_leaves_the_manifest_that_was_there(tmp_path, monkeypatch):
    out = tmp_path / "generated"
    out.mkdir()
    (out / FILENAME).write_bytes(b'{"the": "previous manifest"}\n')

    def cut(source, target):
        raise OSError("the disk went away")

    monkeypatch.setattr(manifest_module.os, "replace", cut)
    with pytest.raises(OSError, match="the disk went away"):
        write_manifest(out, WORLD_ARGUMENT)
    assert (out / FILENAME).read_bytes() == b'{"the": "previous manifest"}\n'
