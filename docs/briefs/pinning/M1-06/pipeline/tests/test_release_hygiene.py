"""Pinning tests for brief M1-06: exports stay out of git; the export script exists.

Pinned decisions (docs/RELEASE.md §C; docs/SPEC.md §11): `tools/export.sh` exports both
presets into `build/`, which is git-ignored; binaries reach the `dist` shelf only through
the release, never through `main` (Hard Rule 3's storage rule, SPEC §9).
"""

import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "rel",
    [
        "build/linux/mattini.x86_64",
        "build/linux/mattini.pck",
        "build/windows/mattini.exe",
        "build/windows/libterrain.windows.release.x86_64.dll",
    ],
)
def test_exports_are_ignored(rel):
    result = subprocess.run(["git", "check-ignore", "--no-index", "-q", rel], cwd=REPO, check=False)
    assert result.returncode == 0, f"{rel} must be git-ignored"


def test_the_export_script_exists_and_is_executable():
    script = REPO / "tools" / "export.sh"
    assert script.is_file()
    assert os.access(script, os.X_OK)
