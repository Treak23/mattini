"""Pinning test for brief M1-01: files the repository depends on are tracked (G-08).

Pinned decision (docs/history/ARCS.md §M0, D10 G-08): M0-01's hygiene test checks that
these paths are not ignored; that is not "tracked" (`git rm --cached` passed it). This live
test asserts `git ls-files --error-unmatch` for every listed path that exists. Harm
prevented: a commit that drops the lockfile, the gate or a config from git passes the gate,
and the owner's next clone lacks it. Stage new files before running the gate.
"""

import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
DEPENDED_ON = [
    ".gitattributes",
    ".gitignore",
    "config/world.json",
    "config/datasets.json",
    "config/datasets.lock.json",
    "config/terrain.json",
    "pipeline/uv.lock",
    "pipeline/.python-version",
    "pipeline/pyproject.toml",
    "tools/gate.sh",
    "tools/gate_allowlist.txt",
    "tests/shared/world_vectors.json",
    "tests/shared/terrain_vectors.json",
    "game/project.godot",
    "game/addons/gut/plugin.cfg",
    "game/addons/terrain_3d/terrain.gdextension",
]


@pytest.mark.parametrize("rel", [p for p in DEPENDED_ON if (REPO / p).exists()])
def test_is_tracked(rel):
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", rel],
        cwd=REPO,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, f"{rel} exists but is not tracked by git"


def test_the_required_ones_exist():
    required = [p for p in DEPENDED_ON if not p.startswith("game/addons/terrain_3d/")]
    assert [p for p in required if not (REPO / p).exists()] == []
