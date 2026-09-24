"""Pinning tests for brief M0-02: the manifest carries config/world.json verbatim.

Pinned decisions (SPEC §6 and §8): the game reads the origin and axes only from the
generated manifest; its `world` block is config/world.json verbatim and `world_sha256` is
the SHA-256 of that file's bytes; writing it is deterministic (Hard Rule 5); the gate's
command `python -m mattini manifest --out <dir>` writes the same file.
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from mattini.manifest import write_manifest

REPO = Path(__file__).resolve().parents[2]
CONFIG = REPO / "config" / "world.json"


def test_world_block_is_config_verbatim(tmp_path):
    path = write_manifest(tmp_path)
    assert path == tmp_path / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest["schema"] == 1
    assert manifest["world"] == json.loads(CONFIG.read_text(encoding="utf-8"))
    assert manifest["world_sha256"] == hashlib.sha256(CONFIG.read_bytes()).hexdigest()


def test_writing_twice_gives_identical_bytes(tmp_path):
    first = write_manifest(tmp_path / "a").read_bytes()
    second = write_manifest(tmp_path / "b").read_bytes()
    assert first == second
    assert str(tmp_path).encode() not in first  # no absolute paths in generated output


def test_cli_writes_the_same_manifest(tmp_path):
    subprocess.run(
        [sys.executable, "-m", "mattini", "manifest", "--out", str(tmp_path / "cli")],
        cwd=REPO,
        check=True,
    )
    expected = write_manifest(tmp_path / "api").read_bytes()
    assert (tmp_path / "cli" / "manifest.json").read_bytes() == expected
