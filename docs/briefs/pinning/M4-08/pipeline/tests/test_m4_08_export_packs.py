"""Pinning tests for brief M4-08: tools/export.sh writes exactly the data packs the game expects.

Pinned decisions (brief M4-08; FB-005): the game's DataPacks names the packs an exported build
needs, `const EXPECTED_PACKS := [...]` on one line of game/scripts/data_packs.gd, and says so
when one is missing. tools/export.sh reads that constant (step 2b, before anything is
exported) and refuses, naming data_packs.gd, both lists and "nothing was exported", unless it
is exactly `mattini-<folder>.pck` for its PACKED_FOLDERS, in order; a data_packs.gd without
the constant is refused there too. After step 4b it refuses, naming the packs written and the
packs expected, unless the packs it wrote are exactly EXPECTED_PACKS (a packed folder that is
not there gets no pack, and the release would show the player an error); the build is not
started then.

The script under test is the repository's own, run on stand-ins (fake_tools.py, briefs M3-02,
M3-14 and this one's replacement): the stand-in Godot writes the data packs as
game/tools/pack.gd does.

Does NOT prove: that the started build finds the packs (step 6 and the brief's export run);
that the game's own message names the right pack (test_m4_08_data_packs_expected.gd).
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


def _replace(path, old, new):
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1, f"{path} holds {old!r} once"
    path.write_text(text.replace(old, new), encoding="utf-8")


def _exported(tmp_path):
    return [call for call in fake_tools.calls(tmp_path) if "--export-release" in call]


def test_the_packs_the_game_expects_are_written_beside_both_executables(tmp_path):
    root = _tree(tmp_path)
    done = fake_tools.run_export(tmp_path, root, fake_tools.start_output())
    assert done.returncode == 0 and DONE in done.stdout, done.stdout[-3000:]
    assert "the game expects mattini-photo.pck mattini-terrain.pck" in done.stdout
    for build in ("linux", "windows"):
        for pack in ("mattini-photo.pck", "mattini-terrain.pck"):
            assert (root / "build" / build / pack).stat().st_size > 0, (build, pack)
    for line in fake_tools.PACK_LINES:
        assert f"started: {line}" in done.stdout


@pytest.mark.parametrize(
    "line, named",
    [
        (
            EXPECTED_LINE.replace('", "', '", "mattini-surroundings.pck", "'),
            "mattini-photo.pck mattini-surroundings.pck mattini-terrain.pck",
        ),
        ('const EXPECTED_PACKS := ["mattini-terrain.pck"]', "mattini-terrain.pck"),
        (
            'const EXPECTED_PACKS := ["mattini-terrain.pck", "mattini-photo.pck"]',
            "mattini-terrain.pck mattini-photo.pck",
        ),
    ],
    ids=["one-more", "one-fewer", "another-order"],
)
def test_another_expectation_is_refused_before_any_export(tmp_path, line, named):
    root = _tree(tmp_path)
    _replace(root / "game" / "scripts" / "data_packs.gd", EXPECTED_LINE, line)
    done = fake_tools.run_export(tmp_path, root, fake_tools.start_output())
    assert done.returncode != 0 and DONE not in done.stdout, done.stdout[-3000:]
    message = f"game/scripts/data_packs.gd expects the data packs {named}"
    assert message in done.stdout, done.stdout[-3000:]
    assert "mattini-photo.pck mattini-terrain.pck" in done.stdout
    assert "nothing was exported" in done.stdout
    assert not _exported(tmp_path)
    assert not (root / "build").exists()


def test_another_packed_folder_list_is_refused_before_any_export(tmp_path):
    root = _tree(tmp_path)
    _replace(
        root / "tools" / "export.sh", "PACKED_FOLDERS=(photo terrain)", "PACKED_FOLDERS=(photo)"
    )
    done = fake_tools.run_export(tmp_path, root, fake_tools.start_output())
    assert done.returncode != 0 and DONE not in done.stdout, done.stdout[-3000:]
    assert "this script writes mattini-photo.pck (PACKED_FOLDERS)" in done.stdout
    assert not _exported(tmp_path)


def test_a_data_packs_script_without_the_constant_is_refused(tmp_path):
    root = _tree(tmp_path)
    _replace(root / "game" / "scripts" / "data_packs.gd", EXPECTED_LINE, "")
    done = fake_tools.run_export(tmp_path, root, fake_tools.start_output())
    assert done.returncode != 0 and DONE not in done.stdout, done.stdout[-3000:]
    assert "game/scripts/data_packs.gd has no one-line const EXPECTED_PACKS" in done.stdout
    assert not _exported(tmp_path)


def test_a_pack_not_written_fails_before_the_build_starts(tmp_path):
    root = _tree(tmp_path)
    generated = root / "game" / "assets" / "generated"
    (generated / "terrain" / "village.f32").unlink()
    (generated / "terrain").rmdir()
    done = fake_tools.run_export(tmp_path, root, fake_tools.start_output())
    assert done.returncode != 0 and DONE not in done.stdout, done.stdout[-3000:]
    assert (
        "the data packs written (mattini-photo.pck) are not the ones the game expects "
        "(mattini-photo.pck mattini-terrain.pck)"
    ) in done.stdout, done.stdout[-3000:]
    assert "== export: 6." not in done.stdout
