"""`python -m mattini terrain` and `manifest` on the command line (brief M1-03).

`terrain` builds the heights, then writes the manifest, printing the manifest's path on
stdout and progress on stderr; a refusal is `mattini: error: …` on stderr, exit 1, and
nothing on stdout. `manifest` refuses a built terrain that no longer matches, naming
`python -m mattini terrain`, and writes no manifest. The one-tile world of
test_terrain_refusals.py stands in for the village.
"""

import hashlib
import json
import shutil

import pytest
from test_terrain_refusals import FIXTURE, case  # noqa: F401 (case is a fixture)

import mattini.__main__ as cli
from mattini import lock, manifest, terrain
from mattini.world import REPO


def test_terrain_builds_then_writes_the_manifest(case, monkeypatch, capsys):  # noqa: F811
    lock_path = case["tmp"] / "datasets.lock.json"
    lock.write_lock(case["lock"], lock_path)
    world_path = case["world"].path
    terrain_config = case["tmp"] / "terrain.json"
    terrain_config.write_text(json.dumps(case["config"]), encoding="utf-8")
    monkeypatch.setattr(lock, "LOCK_PATH", lock_path)
    monkeypatch.setattr(cli, "load_world", lambda: case["world"])
    monkeypatch.setattr(terrain, "load_terrain_config", lambda: case["config"])
    monkeypatch.setattr(
        cli,
        "write_manifest",
        lambda out: manifest.write_manifest(out, world_path, terrain_config_path=terrain_config),
    )
    out = case["out"]
    assert cli.main(["terrain", "--raw", str(case["tmp"] / "raw"), "--out", str(out)]) == 0
    captured = capsys.readouterr()
    assert captured.out == f"{out / 'manifest.json'}\n"
    assert "reading " in captured.err and "501 × 501 vertices" in captured.err
    written = json.loads((out / "manifest.json").read_bytes())
    block = json.loads((out / "terrain" / "village.json").read_bytes())
    assert written["terrain"] == block


def test_terrain_without_a_download_fails_naming_the_download(tmp_path, capsys):
    out = tmp_path / "generated"
    assert cli.main(["terrain", "--raw", str(tmp_path / "raw"), "--out", str(out)]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("mattini: error: ")
    assert "provenance.json" in captured.err
    assert "`python -m mattini download terrain`" in captured.err
    assert not out.exists()


@pytest.mark.parametrize("change", ["world_sha256", "heights"])
def test_manifest_refuses_a_stale_terrain_and_writes_nothing(tmp_path, capsys, change):
    out = tmp_path / "generated"
    (out / "terrain").mkdir(parents=True)
    block = json.loads((FIXTURE / "generated" / "terrain" / "fixture.json").read_bytes())
    block.update(area="village", file="terrain/village.f32")  # the committed config's area
    heights = FIXTURE / "generated" / "terrain" / "fixture.f32"
    shutil.copy(heights, out / "terrain" / "village.f32")
    if change == "heights":
        world = (REPO / "config" / "world.json").read_bytes()
        block["world_sha256"] = hashlib.sha256(world).hexdigest()
        (out / "terrain" / "village.f32").write_bytes(heights.read_bytes()[:-4])
    (out / "terrain" / "village.json").write_text(json.dumps(block), encoding="utf-8")
    assert cli.main(["manifest", "--out", str(out)]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("mattini: error: ")
    assert "`python -m mattini terrain`" in captured.err
    assert not (out / "manifest.json").exists()
