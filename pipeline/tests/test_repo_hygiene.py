"""Pinning tests for briefs M0-01 and M2-09: repository hygiene.

Pinned decisions: raw downloads and generated assets stay out of git (CLAUDE.md Hard
Rule 3; SPEC §9, the owner's answer 7b), but the one real sample the owner allowed on
2026-09-25 (SPEC §13 row 24), which is named here with its SHA-256 so that no other file
and no other bytes pass under its name; config, lockfile, gate and vendored addons stay
tracked; Python 3.13 via uv with a lockfile (SPEC §13 #5); the standard gate exists
(CLAUDE.md §Build & Test); nothing raw or oversized is about to be committed (SPEC §9).
"""

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

RAW_SUFFIXES = {".tif", ".tiff", ".las", ".laz", ".xyz", ".zip", ".gpkg", ".dwg", ".shp"}
MAX_BYTES = 10 * 1024 * 1024
# The one file of raw geodata in git (SPEC §13 row 24; tests/shared/buildings_sample/README.md).
REAL_SAMPLE = {
    "tests/shared/buildings_sample/swissbuildings3d_3_0_2020_1328-33_2056_5728.gdb.zip": (
        "72b2502856d315b9f265f8279a9491cfa3f45065a42cc492824fd9731d7c4292"
    ),
}


def _git_ignored(rel: str) -> bool:
    result = subprocess.run(["git", "check-ignore", "--no-index", "-q", rel], cwd=REPO, check=False)
    assert result.returncode in (0, 1), f"git check-ignore failed for {rel}"
    return result.returncode == 0


def _committable_files() -> list[str]:
    """Tracked files plus untracked files that are not ignored: what a commit could hold."""
    out = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=REPO,
        check=True,
        capture_output=True,
    ).stdout
    return [p for p in out.decode("utf-8").split("\0") if p]


@pytest.mark.parametrize(
    "rel",
    [
        "data/raw/swissalti3d/2024/swissalti3d_2024_2623-1096_0.5_2056_5728.tif",
        "data/anything.las",
        "game/assets/generated/manifest.json",
        "game/assets/generated/terrain/region_0_0.res",
        "game/.godot/imported/icon.svg-1.ctex",
        "pipeline/.venv/bin/python",
        "gate.log",
    ],
)
def test_raw_generated_and_caches_are_ignored(rel):
    assert _git_ignored(rel), f"{rel} must be git-ignored"


@pytest.mark.parametrize(
    "rel",
    [
        "config/world.json",
        "config/datasets.json",
        "pipeline/uv.lock",
        "pipeline/.python-version",
        "tools/gate.sh",
        "tests/shared/world_vectors.json",
        "game/project.godot",
        "game/addons/gut/plugin.cfg",
        "game/addons/terrain_3d/terrain.gdextension",
    ],
)
def test_sources_config_and_vendored_addons_stay_tracked(rel):
    assert not _git_ignored(rel), f"{rel} must not be git-ignored"


def test_python_is_3_13_via_uv():
    assert sys.version_info[:2] == (3, 13), sys.version
    pinned = (REPO / "pipeline" / ".python-version").read_text(encoding="utf-8").strip()
    assert pinned.startswith("3.13"), pinned


def test_lockfile_exists():
    assert (REPO / "pipeline" / "uv.lock").is_file()


def test_gate_script_is_executable():
    gate = REPO / "tools" / "gate.sh"
    assert gate.is_file()
    assert os.access(gate, os.X_OK)


def test_no_raw_geodata_about_to_be_committed():
    offenders = [
        p
        for p in _committable_files()
        if (
            Path(p).suffix.lower() in RAW_SUFFIXES
            or any(part.lower().endswith(".gdb") for part in Path(p).parts)
        )
        and p not in REAL_SAMPLE
    ]
    assert offenders == [], offenders


def test_the_one_real_sample_is_swisstopo_s_file_with_its_readme():
    committable = _committable_files()
    for rel, sha256 in REAL_SAMPLE.items():
        assert rel in committable, f"{rel} is not in the repository"
        assert hashlib.sha256((REPO / rel).read_bytes()).hexdigest() == sha256, rel
        readme = (REPO / rel).parent / "README.md"
        text = readme.read_text(encoding="utf-8")
        assert "© swisstopo" in text and sha256 in text, readme


def test_no_file_over_10_mb_about_to_be_committed():
    big = [
        p
        for p in _committable_files()
        if (REPO / p).is_file() and (REPO / p).stat().st_size > MAX_BYTES
    ]
    assert big == [], big
