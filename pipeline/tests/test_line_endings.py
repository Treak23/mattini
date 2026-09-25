"""Pinning tests for brief M1-01: a checkout's line-ending settings cannot change bytes (C-04).

Pinned decisions (docs/history/ARCS.md §M0, D5): `.gitattributes` holds `* text=auto eol=lf`
for the whole repository, and marks the binary formats the repository holds or the
pipeline writes as binary. Harm prevented: with core.autocrlf=true (Git for Windows'
default installer choice) config/world.json would be checked out with CRLF, changing its
SHA-256 and so the manifest (Hard Rule 5), tools/gate.sh would stop running in bash, and a
raw float file whose bytes contain 0x0A would be corrupted.

The test shows the harm, not the file: it commits the working tree's .gitattributes and
files into a scratch repository, clones that with core.autocrlf=true, and compares bytes.
Measured on Linux, simulating Windows' setting; nothing here runs on Windows.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
TEXT_FILES = [
    "config/world.json",
    "config/datasets.json",
    "tools/gate.sh",
    "tests/shared/world_vectors.json",
    "tests/shared/terrain_fixture/world.json",
    "tests/shared/terrain_fixture/generated/manifest.json",
]
BINARY_FILES = [
    "tests/shared/terrain_fixture/source.f32",
    "tests/shared/terrain_fixture/generated/terrain/fixture.f32",
]
# A raw float whose bytes hold LF, CR LF and no NUL: git's own guess would call it text.
TRAP = bytes([0x41, 0x0A, 0x42, 0x0D, 0x0A, 0x43, 0x44, 0x45]) * 4


def _git(*args, cwd):
    return subprocess.run(
        ["git", "-c", "user.name=pin", "-c", "user.email=pin@example.invalid", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


def test_gitattributes_forces_lf_and_marks_binaries():
    lines = (REPO / ".gitattributes").read_text(encoding="utf-8").splitlines()
    rules = [line.split() for line in lines if line.strip() and not line.startswith("#")]
    assert ["*", "text=auto", "eol=lf"] in rules
    for pattern in ("*.f32", "*.jpg", "*.png"):
        assert [pattern, "binary"] in rules, pattern


@pytest.mark.skipif(shutil.which("git") is None, reason="git is required")
def test_a_crlf_configured_clone_gets_the_same_bytes(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    _git("init", "-q", cwd=src)
    shutil.copy(REPO / ".gitattributes", src / ".gitattributes")
    for rel in TEXT_FILES + BINARY_FILES:
        (src / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO / rel, src / rel)
    (src / "trap.f32").write_bytes(TRAP)
    _git("-c", "core.autocrlf=false", "add", "-A", cwd=src)
    _git("-c", "core.autocrlf=false", "commit", "-q", "-m", "scratch", cwd=src)

    dst = tmp_path / "dst"
    _git("-c", "core.autocrlf=true", "clone", "-q", str(src), str(dst), cwd=tmp_path)
    for rel in TEXT_FILES + BINARY_FILES:
        assert (dst / rel).read_bytes() == (REPO / rel).read_bytes(), rel
    assert b"\r" not in (dst / "tools" / "gate.sh").read_bytes()
    assert (dst / "trap.f32").read_bytes() == TRAP
