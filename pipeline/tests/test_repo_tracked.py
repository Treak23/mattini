"""Pinning test for brief M1-01, scoped by exclusion since M2-01: what the gate and the game
depend on is tracked (M0 R1 G-08; M1 R1 T-07; lesson 37).

Pinned decision (docs/history/ARCS.md §M0, D10 G-08): M0-01's hygiene test checks that
paths are not ignored; that is not "tracked" (`git rm --cached` passed it). M1-01 listed
the paths; M1's review found the list missing the shared terrain fixture and Terrain3D's
binaries (T-07). Since M2-01 the test is scoped by exclusion: every file on disk under
`config/`, `tests/shared/`, `tools/`, `game/` (the vendored addons and Terrain3D's
binaries included) and `pipeline/` must be in git's index, except the named exclusions:
Godot's import cache (`game/.godot/`), the pipeline's regenerated output
(`game/assets/generated/`), the Python environment (`pipeline/.venv/`) and the caches
(`__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `*.pyc`). Harm prevented: a commit
that drops a file the gate or the game needs passes the gate, and the owner's next clone
lacks it (no fixture: the gate fails there; no Terrain3D: no terrain). Stage new files
before running the gate.

Does NOT prove: that a fresh clone was made and runs (the harm follows from what git
stores); anything about files outside the five folders and the two root files; that a
file deleted from disk and index together is caught (test_the_required_ones_exist covers
the named ones).
"""

import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
ROOTS = ("config", "tests/shared", "tools", "game", "pipeline")
ROOT_FILES = (".gitattributes", ".gitignore")
EXCLUDED_DIRS = ("game/.godot", "game/assets/generated", "pipeline/.venv")
CACHE_DIRS = {"__pycache__", ".pytest_cache", ".ruff_cache"}
CACHE_SUFFIXES = (".pyc", ".pyo", ".pyd")
TERRAIN3D_BINARIES = [
    "libterrain.linux.debug.x86_64.so",
    "libterrain.linux.release.x86_64.so",
    "libterrain.windows.debug.x86_64.dll",
    "libterrain.windows.release.x86_64.dll",
]
REQUIRED = [
    ".gitattributes",
    ".gitignore",
    "config/world.json",
    "config/datasets.json",
    "config/datasets.lock.json",
    "config/terrain.json",
    "config/buildings.json",
    "pipeline/uv.lock",
    "pipeline/.python-version",
    "pipeline/pyproject.toml",
    "tools/gate.sh",
    "tools/gate_allowlist.txt",
    "tests/shared/world_vectors.json",
    "tests/shared/terrain_vectors.json",
    "tests/shared/terrain_vectors_nw.json",
    "tests/shared/buildings_vectors.json",
    "game/project.godot",
    "game/addons/gut/plugin.cfg",
    "game/addons/terrain_3d/terrain.gdextension",
]


def _excluded(rel: str) -> bool:
    parts = rel.split("/")
    return (
        any(rel == d or rel.startswith(d + "/") for d in EXCLUDED_DIRS)
        or any(part in CACHE_DIRS for part in parts[:-1])
        or rel.endswith(CACHE_SUFFIXES)
    )


def _on_disk() -> list[str]:
    """Every file under the roots, minus the exclusions, as repository-relative paths."""
    found = [rel for rel in ROOT_FILES if (REPO / rel).is_file()]
    for root in ROOTS:
        for dirpath, dirnames, filenames in os.walk(REPO / root):
            here = Path(dirpath).relative_to(REPO).as_posix()
            dirnames[:] = sorted(d for d in dirnames if not _excluded(f"{here}/{d}/x"))
            found += [f"{here}/{name}" for name in sorted(filenames)]
    return [rel for rel in found if not _excluded(rel)]


def _tracked() -> set[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=REPO, check=True, capture_output=True
    ).stdout
    return {p for p in out.decode("utf-8").split("\0") if p}


def test_every_file_the_gate_or_the_game_depends_on_is_tracked():
    untracked = [rel for rel in _on_disk() if rel not in _tracked()]
    assert untracked == [], f"on disk but not in git's index (stage them): {untracked}"


def test_the_scan_reaches_the_files_m1_s_list_missed():
    """Not vacuous: the fixture, the second fixture and Terrain3D's binaries are scanned."""
    scanned = set(_on_disk())
    for rel in (
        "tests/shared/terrain_fixture/source.f32",
        "tests/shared/terrain_fixture/generated/terrain/fixture.f32",
        "tests/shared/terrain_fixture_nw/source.f32",
        "pipeline/mattini/terrain.py",
        "tools/export.sh",
    ):
        assert rel in scanned, rel
    # all four Terrain3D libraries: Linux and Windows, debug and release (M2-06)
    for name in TERRAIN3D_BINARIES:
        assert f"game/addons/terrain_3d/bin/{name}" in scanned, name


@pytest.mark.parametrize(
    ("rel", "excluded"),
    [
        ("game/.godot/extension_list.cfg", True),
        ("game/assets/generated/manifest.json", True),
        ("game/assets/generated/terrain/village.f32", True),
        ("pipeline/.venv/bin/python", True),
        ("pipeline/mattini/__pycache__/terrain.cpython-313.pyc", True),
        ("pipeline/.pytest_cache/README.md", True),
        ("game/addons/terrain_3d/bin/libterrain.linux.release.x86_64.so", False),
        ("game/assets/icon.svg", False),
        ("tests/shared/terrain_fixture/source.f32", False),
        ("pipeline/tests/fake_swisstopo.py", False),
        ("config/terrain.json", False),
    ],
)
def test_only_the_named_exclusions_are_left_out(rel, excluded):
    assert _excluded(rel) is excluded, rel


def test_the_required_ones_exist():
    assert [p for p in REQUIRED if not (REPO / p).is_file()] == []
