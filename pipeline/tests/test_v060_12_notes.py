"""Tests for brief v0.6.0-12 (the whole-range review's fix batch, A7, A9 and A10): the Release
notes carry the placeholders the pause screen shows and the far terrain's limits, and the credits
note's band is the config's.

Decisions tested (docs/reviews/v0.6.0-round1.md; the brief's decisions 5 and 6; CLAUDE.md Hard
Rule 2, lesson 2: the notes carry what the game shows):
- The pause screen's Placeholders section lists the walls', the trees' and the streams' notes
  always (`BuildingLoader.WALLS_NOTE`, `TreeLoader.TREES_NOTE`, `STREAMS_NOTE` in main.gd) and,
  where the far colour was filled, `FAR_COLOUR_NOTE` with the share, the edition and the band.
  tools/release_notes.md holds each fixed note word for word on a line of its own, and the far
  colour's note as its fixed fragments around the three `%s` (the share, the colour's edition
  twice) with the village's values: the share the config's `expected_filled_fraction` gives in
  the game's words ("about 32 %"), the edition `swissimage_far`'s in config/datasets.json.
- `FAR_COLOUR_NOTE`'s "100 m" is a literal in the game, a copy of `colour.band_m` in
  config/surroundings.json: it equals that number.
- The template names the far terrain's two limits (a 50 m surface of means whose summits are drawn
  15 to 31 m lower than they are, and smooth up close outside the 2 km x 3 km area) and that the
  window may stay blank for several seconds at start; and it holds no placeholder `@...@` but the
  three test_release_notes.py allows.

Does NOT prove: that the pause screen shows these lines or that the game's text is what the
census reads (the game's tests, test_v060_09_gaps.gd; a census reads text, it runs nothing);
that the 15 to 31 m is still the measure of the real heights (design's measurement, the design
sketch of 0.6.0 §0: the numbers are literals here); that the start is slow in a window (never
timed in one) or how many seconds; that the published Release shows the rendered notes (the
session's audit of the draft).
"""

import json
import re

from fake_tools import REPO

TEMPLATE = REPO / "tools" / "release_notes.md"
MAIN_GD = REPO / "game" / "scripts" / "main.gd"
WALLS_GD = REPO / "game" / "scripts" / "buildings" / "building_loader.gd"
TREES_GD = REPO / "game" / "scripts" / "trees" / "tree_loader.gd"
SURROUNDINGS_CONFIG = REPO / "config" / "surroundings.json"
DATASETS_CONFIG = REPO / "config" / "datasets.json"
WORLD_CONFIG = REPO / "config" / "world.json"
# The notes the game always lists, and the file each const is in.
FIXED_NOTES = {
    "WALLS_NOTE": WALLS_GD,
    "TREES_NOTE": TREES_GD,
    "STREAMS_NOTE": MAIN_GD,
}


def _template():
    assert TEMPLATE.is_file(), "tools/release_notes.md is missing"
    return TEMPLATE.read_text(encoding="utf-8")


def _flat(text):
    return " ".join(text.split())


def _const_text(path, name):
    """The text of `const <name> := ...` in a GDScript file: its string literals, joined.

    The const is one line (`const NAME := "text"`) or a block that ends with a line starting
    `)` (`const NAME := (` and the literals joined with `+`).
    """
    source = path.read_text(encoding="utf-8")
    start = re.search(r"^const " + name + r" := ", source, re.MULTILINE)
    assert start, f"{path.name} has no `const {name} :=`"
    rest = source[start.end() :]
    if rest.startswith("("):
        end = re.search(r"^\)", rest, re.MULTILINE)
        assert end, f"{path.name}: `const {name} := (` is never closed"
        body = rest[1 : end.start()]
    else:
        body = rest.split("\n", 1)[0]
    parts = re.findall(r'"((?:[^"\\]|\\.)*)"', body)
    assert parts, f"{name} holds no string literal"
    return "".join(parts)


def _far_fragments():
    """FAR_COLOUR_NOTE split at its `%s`: the text around the share and the edition twice."""
    fragments = _const_text(MAIN_GD, "FAR_COLOUR_NOTE").split("%s")
    assert len(fragments) == 4, "FAR_COLOUR_NOTE has three %s: the share, the edition, the edition"
    return fragments


def _share_words(fraction):
    """main.gd's `_far_note` words for a share of 0 to 1 (`roundi` of the percent)."""
    percent = fraction * 100.0
    return "less than 1 %" if percent < 1.0 else f"about {int(percent + 0.5)} %"


def _json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_the_template_carries_each_fixed_placeholder_note_word_for_word():
    lines = _template().splitlines()
    for name, path in FIXED_NOTES.items():
        note = _const_text(path, name)
        assert note in lines, f"the notes lack {name}, on a line of its own: {note!r}"


def test_the_template_carries_the_far_colour_note_with_the_villages_values():
    fragments = _far_fragments()
    pattern = "(.+?)".join(re.escape(fragment) for fragment in fragments)
    found = [m.groups() for line in _template().splitlines() if (m := re.fullmatch(pattern, line))]
    assert len(found) == 1, f"one line of the notes is FAR_COLOUR_NOTE around its %s: {fragments}"
    share, edition, edition_again = found[0]
    village = _json(SURROUNDINGS_CONFIG)["areas"]["village"]["colour"]
    assert share == _share_words(village["expected_filled_fraction"]), share
    far_edition = _json(DATASETS_CONFIG)["datasets"]["swissimage_far"]["edition"]
    assert edition == edition_again == far_edition, (edition, edition_again, far_edition)


def test_the_credits_note_s_band_is_the_config_s_colour_band():
    # A census: it reads the text of main.gd and of the config and proves the numbers agree.
    bands = {area["colour"]["band_m"] for area in _json(SURROUNDINGS_CONFIG)["areas"].values()}
    assert len(bands) == 1, f"one colour band for every area, the note names one: {bands}"
    (band,) = bands
    found = re.findall(r"(\d+) m of altitude", _const_text(MAIN_GD, "FAR_COLOUR_NOTE"))
    assert found == [str(band)], (
        f"FAR_COLOUR_NOTE names the band {found} m; config/surroundings.json's colour.band_m is "
        f"{band}: the literal in main.gd and the config must agree"
    )


def test_the_template_names_the_far_terrain_s_two_limits():
    text = _flat(_template())
    spacing = {a["spacing_m"] for a in _json(SURROUNDINGS_CONFIG)["areas"].values()}
    assert len(spacing) == 1
    (metres,) = spacing
    area = _json(WORLD_CONFIG)["areas"]["village"]
    east = (area["e_max"] - area["e_min"]) / 1000
    north = (area["n_max"] - area["n_min"]) / 1000
    assert f"{metres} m means" in text, "the surface is one of 50 m means"
    assert "15 to 31 m lower" in text, "summits are drawn 15 to 31 m lower than they are"
    assert "smooth up close" in text, "the far terrain is smooth up close"
    assert f"{east:g} km x {north:g} km" in text, "outside the village's area box"


def test_the_template_says_the_window_may_stay_blank_at_start():
    text = _flat(_template())
    assert "blank for several seconds" in text, "the window may stay blank for several seconds"
    assert "far terrain" in text, "while the terrain and the far terrain are built"


def test_the_template_has_exactly_the_three_placeholders_still():
    text = _template()
    assert set(re.findall(r"@[A-Z0-9_]+@", text)) == {"@VERSION@", "@SHA@", "@SHA256SUMS@"}
