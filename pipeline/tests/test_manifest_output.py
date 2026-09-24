"""The manifest's bytes and the command line, beyond the pinned tests (brief M0-02).

Hard Rule 5: the same config gives the same bytes on every platform (LF endings, sorted
keys, no paths), whatever the working directory. Hard Rule 2: a refused config writes no
manifest and the command exits non-zero with the file named.
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

import mattini.__main__ as cli
from mattini.manifest import write_manifest
from mattini.world import WorldConfigError

REPO = Path(__file__).resolve().parents[2]
CONFIG = REPO / "config" / "world.json"


def test_bytes_are_sorted_json_with_lf_endings(tmp_path):
    raw = write_manifest(tmp_path).read_bytes()
    assert b"\r" not in raw
    assert raw.endswith(b"}\n")
    manifest = json.loads(raw)
    assert list(manifest) == sorted(manifest)
    assert raw == (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")


def test_cli_output_does_not_depend_on_the_working_directory(tmp_path):
    out = tmp_path / "from-tmp"
    result = subprocess.run(
        [sys.executable, "-m", "mattini", "manifest", "--out", str(out)],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == str(out / "manifest.json")
    assert (out / "manifest.json").read_bytes() == write_manifest(tmp_path / "api").read_bytes()


def test_manifest_follows_the_config_it_was_given(tmp_path):
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    data["areas"]["village"]["n_max"] = 1099000.0
    config = tmp_path / "world.json"
    config.write_text(json.dumps(data), encoding="utf-8")
    manifest = json.loads(write_manifest(tmp_path / "out", config).read_bytes())
    assert manifest["world"] == data
    assert manifest["world_sha256"] == hashlib.sha256(config.read_bytes()).hexdigest()
    assert manifest["world_sha256"] != hashlib.sha256(CONFIG.read_bytes()).hexdigest()


def test_a_refused_config_writes_no_manifest(tmp_path):
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    data["axes"]["z"] = "+n"
    config = tmp_path / "world.json"
    config.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(WorldConfigError, match="mirror"):
        write_manifest(tmp_path / "out", config)
    assert not (tmp_path / "out" / "manifest.json").exists()


def test_cli_reports_a_refused_config_and_exits_non_zero(tmp_path, monkeypatch, capsys):
    def refuse(out):
        raise WorldConfigError(f"{CONFIG}: axes mirror the world")

    monkeypatch.setattr(cli, "write_manifest", refuse)
    assert cli.main(["manifest", "--out", str(tmp_path)]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert str(CONFIG) in captured.err and "mirror" in captured.err
