"""Tests for brief v0.5.0-15: the Release notes carry the credits the game shows and a real rollback.

Pinned decisions: the Software paragraph names what ships (Godot Engine, Terrain3D, godot-cpp),
not GUT (a test addon, excluded from the export); the Sky notes are carried word for word from
game/scripts/main.gd (SUN_NOTE, MOON_NOTE); the rollback for 0.5.0 is the dist branch's
mattini-0.3.1/ folder; the checksum command uses --ignore-missing; tools/export.sh's header
says what its "unfinished" line covers and what it does not.

Since brief v0.6.0-11 (this file re-pinned whole; only this paragraph, the import of VERSION, the
constants ROLLBACK and VERSION_BEFORE and the rollback's test change, every other line as v0.5.0-15
left it): the rollback line names the previous version's GitHub Release, Release v0.5.0
(https://github.com/Treak23/mattini/releases/tag/v0.5.0, published by the owner on 2026-10-31,
docs/releases/v0.5.0.md), in place of the dist branch's mattini-0.3.1/ folder; it names the version
it is written for, game/project.godot's (so a version raised without rewriting the line fails here:
"A later release's session rewrites this line"), and no dist folder any more.

Does NOT prove: that the Release page renders as intended on GitHub, or that the credits are
legally sufficient; that Release v0.5.0 is still published and its archives still download (the
session's audit of the draft, docs/RELEASE.md §C); that VERSION_BEFORE is the version before
game/project.godot's (a constant of this file, rewritten with the line).
"""

import re

from fake_tools import REPO, VERSION

TEMPLATE = REPO / "tools" / "release_notes.md"
MAIN_GD = REPO / "game" / "scripts" / "main.gd"
EXPORT_SH = REPO / "tools" / "export.sh"
VERSION_BEFORE = "0.5.0"  # the Release this version's notes roll back to (brief v0.6.0-11)
ROLLBACK = (
    "The rollback is the previous version's Release: download its archive and unpack it into a "
    f"folder of its own. For {VERSION} it is Release v{VERSION_BEFORE} "
    f"(https://github.com/Treak23/mattini/releases/tag/v{VERSION_BEFORE}). A later release's "
    "session rewrites this line."
)


def _template():
    return TEMPLATE.read_text(encoding="utf-8")


def _const_text(name):
    src = MAIN_GD.read_text(encoding="utf-8")
    match = re.search(r"^const " + name + r" := \((.*?)^\)", src, re.DOTALL | re.MULTILINE)
    assert match, f"main.gd has no `const {name} := (...)`"
    parts = re.findall(r'"((?:[^"\\]|\\.)*)"', match.group(1))
    assert parts, f"{name} holds no string literal"
    return "".join(parts)


def test_sun_note_word_for_word():
    assert _const_text("SUN_NOTE") in _template()


def test_moon_note_word_for_word():
    assert _const_text("MOON_NOTE") in _template()


def test_sky_heading_beside_stars_credit():
    text = _template()
    assert "Sky:" in text
    assert text.index("Sky:") < text.index("Stars derived from the Hipparcos")


def test_names_godot_cpp():
    assert "godot-cpp" in _template()


def test_does_not_name_gut():
    assert not re.search(r"\bGUT\b", _template()), "GUT is a test addon and is not shipped"


def test_rollback_names_the_previous_release():
    text = _template()
    assert ROLLBACK in " ".join(text.split()), "the rollback paragraph is not the pinned one"
    assert text.count("The rollback is") == 1, "one rollback paragraph"
    assert "releases/tag/v" + VERSION_BEFORE in text
    assert "mattini-0.3.1" not in text, "the dist folder is no longer the rollback"
    assert "tree/dist" not in text, "the dist branch is no longer the rollback"
    assert "Release of the version before this one: download" not in text


def test_checksum_line_ignores_missing():
    assert "sha256sum -c --ignore-missing SHA256SUMS" in _template()


def test_export_header_narrow_words():
    head = EXPORT_SH.read_text(encoding="utf-8").split("set -euo pipefail")[0]
    assert "export: build/ is unfinished, do not ship it" in head
    assert "set -e" in head, (
        "the header must say a command dying under set -e ends without the line"
    )
    assert "no such line" in head


def test_software_paragraph_names_both_licence_homes():
    """Every `game/...` path the notes name exists in the tree; godot-cpp's licence home is named.

    godot-cpp's licence is game/credits/godot-cpp-LICENSE.txt (main.gd GODOT_CPP_LICENSE), not
    beside an addon, so "beside each addon" alone would be untrue (review R15-01).
    """
    text = _template()
    paths = [p for p in re.findall(r"`(game/[^`]*)`", text)]
    assert paths, "the notes name no repository path under game/"
    for path in paths:
        assert (REPO / path).exists(), f"the notes name `{path}`, which is not in the tree"
    assert "game/credits/" in text, "the notes must name where godot-cpp's licence sits"
    assert "game/addons/terrain_3d/" in text
