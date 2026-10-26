"""Tests of brief v0.3.1-04 (decisions 3 and 4): how tools/export.sh reads the game's pack list.

Decisions (brief v0.3.1-04; M4-08 decisions 4 and 5): step 2b reads the one-line
`const EXPECTED_PACKS := [...]` of game/scripts/data_packs.gd as text, a CR at a line's end
removed first (the gate's rule for every scan), and refuses before anything is exported. The
three branches test_m4_08_export_packs.py does not reach:
- a data_packs.gd that is not there is refused saying so, not reported as one without the
  constant;
- the constant on two lines of the file is refused as a file without it is (exactly one line
  must match);
- a data_packs.gd with CR LF line ends is read as an LF one is.

The script under test is the repository's own, run on stand-ins (fake_tools.py).

Does NOT prove: that Godot could parse the data_packs.gd these tests feed the script (the
gate's parse check covers the real one); that the real file is read as written (the release
gate's export run).
"""

import platform

import fake_tools
import pytest

pytestmark = pytest.mark.skipif(
    fake_tools.BASH is None or platform.system() != "Linux",
    reason="tools/export.sh runs on Linux with bash",
)

DONE = "== export: done in"
EXPECTED_LINE = 'const EXPECTED_PACKS := ["mattini-photo.pck", "mattini-terrain.pck"]'


def _tree(tmp_path):
    templates = tmp_path / "xdg" / "godot" / "export_templates" / "4.6.3.stable"
    return fake_tools.export_tree(tmp_path, templates)


def _exported(tmp_path):
    return [call for call in fake_tools.calls(tmp_path) if "--export-release" in call]


def test_a_missing_data_packs_script_is_refused_before_any_export(tmp_path):
    root = _tree(tmp_path)
    (root / "game" / "scripts" / "data_packs.gd").unlink()
    done = fake_tools.run_export(tmp_path, root, fake_tools.start_output())
    assert done.returncode != 0 and DONE not in done.stdout, done.stdout[-3000:]
    assert "game/scripts/data_packs.gd is missing: nothing was exported" in done.stdout
    assert not _exported(tmp_path)


def test_the_constant_written_twice_is_refused_before_any_export(tmp_path):
    root = _tree(tmp_path)
    path = root / "game" / "scripts" / "data_packs.gd"
    text = path.read_text(encoding="utf-8")
    assert text.count(EXPECTED_LINE) == 1, "data_packs.gd holds the constant's line once"
    path.write_text(
        text.replace(EXPECTED_LINE, f"{EXPECTED_LINE}\n{EXPECTED_LINE}"), encoding="utf-8"
    )
    done = fake_tools.run_export(tmp_path, root, fake_tools.start_output())
    assert done.returncode != 0 and DONE not in done.stdout, done.stdout[-3000:]
    assert "game/scripts/data_packs.gd has no one-line const EXPECTED_PACKS" in done.stdout
    assert not _exported(tmp_path)


def test_a_crlf_data_packs_script_is_read(tmp_path):
    root = _tree(tmp_path)
    path = root / "game" / "scripts" / "data_packs.gd"
    data = path.read_bytes()
    assert b"\r" not in data and data.count(b"\n") > 0, "data_packs.gd starts with LF line ends"
    path.write_bytes(data.replace(b"\n", b"\r\n"))
    done = fake_tools.run_export(tmp_path, root, fake_tools.start_output())
    assert done.returncode == 0 and DONE in done.stdout, done.stdout[-3000:]
    assert "the game expects mattini-photo.pck mattini-terrain.pck" in done.stdout
