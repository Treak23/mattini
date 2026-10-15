"""Pinning tests for brief M3-02 (M2 V1-G-07, M2-02 Findings 9): what tools/export.sh checks.

Pinned decisions (docs/RELEASE.md §C; brief M3-02): tools/export.sh, run as the owner runs
it (here in a scratch tree with stand-ins for Godot and uv, fake_tools.py):
- refuses a system other than Linux before its templates step and before any export: no
  template is downloaded or installed, Godot exports nothing, build/ is not made, and
  the refusal names the system and Linux. Step 6 starts the Linux build, so on another
  system the export used to run to its end and then fail (M2-02 Findings 9);
- removes a CR at the end of a line of Godot's output before its scans, so a CR LF run
  finds its startup lines as the LF one does, and still fails on an error line (V1-G-07).

Does NOT prove: anything on Windows or macOS themselves (`uname` is a stand-in there; these
tests run where bash is, on Linux, and skip elsewhere); that a real export or start prints
these lines (measured at M2's close, brief M2-02 Findings 4).
"""

import sys

import pytest
from fake_tools import BASH, STARTUP_LINES, calls, crlf, export_tree, run_export, start_output

pytestmark = pytest.mark.skipif(
    BASH is None or sys.platform != "linux", reason="runs tools/export.sh with bash, on Linux"
)

WINDOWS = "MINGW64_NT-10.0-19045"  # what Git Bash's uname -s says on the owner's Windows 10
DONE = "== export: done in"


def _linux_templates(tmp_path):
    return tmp_path / "xdg" / "godot" / "export_templates" / "4.6.3.stable"


def _windows_templates(tmp_path):
    return tmp_path / "appdata" / "Godot" / "export_templates" / "4.6.3.stable"


def test_the_export_passes_on_linux(tmp_path):
    """Positive control: the stand-ins and this tree let the script run to its end."""
    root = export_tree(tmp_path, _linux_templates(tmp_path))
    done = run_export(tmp_path, root, start_output())
    assert done.returncode == 0 and DONE in done.stdout, done.stdout[-3000:]
    assert sum("--export-release" in call for call in calls(tmp_path)) == 2


@pytest.mark.parametrize("installed", [True, False], ids=["templates-installed", "no-templates"])
@pytest.mark.parametrize("system", [WINDOWS, "Darwin"], ids=["windows-git-bash", "macos"])
def test_another_system_is_refused_before_the_templates_and_the_exports(
    tmp_path, system, installed
):
    templates = _windows_templates(tmp_path) if system == WINDOWS else _linux_templates(tmp_path)
    root = export_tree(tmp_path, templates if installed else None)
    done = run_export(tmp_path, root, start_output(), system=system)
    assert done.returncode != 0 and DONE not in done.stdout, done.stdout[-3000:]
    assert system in done.stdout and "Linux" in done.stdout, done.stdout[-3000:]
    made = calls(tmp_path)
    assert not any("--export-release" in call for call in made), made
    assert not any(call.startswith("curl") for call in made), made
    assert not (root / "build").exists()
    if not installed:
        assert not templates.exists()


def test_a_crlf_start_finds_its_startup_lines(tmp_path):
    root = export_tree(tmp_path, _linux_templates(tmp_path))
    done = run_export(tmp_path, root, crlf(start_output()))
    assert done.returncode == 0 and DONE in done.stdout, done.stdout[-3000:]
    for line in STARTUP_LINES:
        assert f"started: {line}" in done.stdout, (line, done.stdout[-3000:])


def test_a_crlf_start_with_an_error_line_still_fails(tmp_path):
    """Control: removing the CR hides no error line."""
    error = "ERROR: TerrainGrid: res://assets/generated/manifest.json: a refusal"
    root = export_tree(tmp_path, _linux_templates(tmp_path))
    done = run_export(tmp_path, root, crlf(start_output([*STARTUP_LINES, error])))
    assert done.returncode != 0 and DONE not in done.stdout, done.stdout[-3000:]
    assert "printed error lines" in done.stdout, done.stdout[-3000:]
