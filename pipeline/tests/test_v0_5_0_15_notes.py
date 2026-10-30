"""Tests for brief v0.5.0-15: the Release notes carry the credits the game shows and a real rollback.

Pinned decisions: the Software paragraph names what ships (Godot Engine, Terrain3D, godot-cpp),
not GUT (a test addon, excluded from the export); the Sky notes are carried word for word from
game/scripts/main.gd (SUN_NOTE, MOON_NOTE); the rollback for 0.5.0 is the dist branch's
mattini-0.3.1/ folder; the checksum command uses --ignore-missing; tools/export.sh's header
says what its "unfinished" line covers and what it does not.

Does NOT prove: that the Release page renders as intended on GitHub, or that the credits are
legally sufficient.
"""

import re

from fake_tools import REPO

TEMPLATE = REPO / "tools" / "release_notes.md"
MAIN_GD = REPO / "game" / "scripts" / "main.gd"
EXPORT_SH = REPO / "tools" / "export.sh"


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


def test_rollback_names_dist_folder():
    text = _template()
    assert "mattini-0.3.1/" in text
    assert "https://github.com/Treak23/mattini/tree/dist/mattini-0.3.1" in text
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
