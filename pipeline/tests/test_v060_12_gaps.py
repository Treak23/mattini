"""Gaps file for brief v0.6.0-12 (the prover's findings on test_v060_12_notes.py; lesson 51).

The harm: prose in tools/release_notes.md that no test reads. The Release notes are what the
owner and the few people the game is shared with read first, and what they say about the
placeholders and the far terrain's limits is a claim (CLAUDE.md Hard Rule 2). The prover found
two ways a sentence of the `## Placeholders and limits` section changed without any test failing:
the slow-start line (its second assertion, "far terrain", stood in the limits' paragraph too) and
the paragraph explaining the far colour's note ("That last one is ..."), which no test read.
test_v060_12_notes.py now pins the slow-start line whole; this file closes the class.

Decisions tested:
- Every word of the section is pinned, in order. The section is cut into the pieces below, each
  required exactly once and in this order, and nothing may stand between two of them or after
  the last: a sentence added, reworded or dropped anywhere in the section fails here, not only
  the ones a key word was chosen for.
- Where a piece carries a number or a claim the repository can check, the piece is built from
  the source and not written twice: the walls', trees' and streams' notes and the far colour's
  fragments from the game's constants, the far colour's share and edition from the configs, the
  "1 km cell" from `farcolour.TILE_M`, "about a third" from the village's
  `expected_filled_fraction`, the area's "2 km x 3 km" from config/world.json, "50 m" from
  config/surroundings.json, "first four", "Placeholders" and "Escape" from main.gd's credits
  and the project's pause action.

Does NOT prove: that a sentence is true (a census reads text and runs nothing); that Italy is the
whole of what SWISSIMAGE does not cover (the note's own claim, design's knowledge: a literal
here); that the "15 to 31 m" is still the measure of the real heights; that the pause screen
shows these lines (test_v060_09_gaps.gd reads the game's label); that the published Release shows
the rendered notes.
"""

import re

from fake_tools import REPO
from test_v060_12_notes import (
    DATASETS_CONFIG,
    FIXED_NOTES,
    MAIN_GD,
    SECTION_HEADING,
    START_SENTENCE,
    SURROUNDINGS_CONFIG,
    WORLD_CONFIG,
    _const_text,
    _far_fragments,
    _flat,
    _json,
    _section_text,
    _share_words,
)

from mattini import farcolour

PROJECT_GODOT = REPO / "game" / "project.godot"
# KEY_ESCAPE in Godot's Key enum (the pause action's physical key).
KEY_ESCAPE = 4194305
# The simple fractions the notes may name a share by, with their words.
SIMPLE_FRACTIONS = {1 / 4: "a quarter", 1 / 3: "a third", 1 / 2: "a half"}
# How far a share may be from the simple fraction it is named by ("about a third").
ABOUT = 0.03


def _fraction_words(fraction):
    """The words of the simple fraction nearest to [fraction], refused when none is near."""
    nearest = min(SIMPLE_FRACTIONS, key=lambda simple: abs(simple - fraction))
    assert abs(nearest - fraction) <= ABOUT, (
        f"the village's far colour share {fraction} is within {ABOUT} of no simple fraction "
        f"{sorted(SIMPLE_FRACTIONS.values())}: the note's 'about ...' has to be reworded"
    )
    return SIMPLE_FRACTIONS[nearest]


def _village():
    return _json(SURROUNDINGS_CONFIG)["areas"]["village"]


def _far_colour_line():
    """FAR_COLOUR_NOTE with the village's values: its share and the far colour's edition twice."""
    fraction = _village()["colour"]["expected_filled_fraction"]
    edition = _json(DATASETS_CONFIG)["datasets"]["swissimage_far"]["edition"]
    first, second, third, fourth = _far_fragments()
    return first + _share_words(fraction) + second + edition + third + edition + fourth


def _pieces():
    """The section's text as the pieces it is made of, in order, each built from its source."""
    spacing = {area["spacing_m"] for area in _json(SURROUNDINGS_CONFIG)["areas"].values()}
    assert len(spacing) == 1
    (metres,) = spacing
    area = _json(WORLD_CONFIG)["areas"]["village"]
    east = (area["e_max"] - area["e_min"]) / 1000
    north = (area["n_max"] - area["n_min"]) / 1000
    fraction = _village()["colour"]["expected_filled_fraction"]
    tile_km = farcolour.TILE_M / 1000
    intro = (
        "What the picture holds that is not measured data. The game lists the first four on its"
        " pause screen (Escape), under Placeholders, in these words:"
    )
    meaning = (
        "That last one is the far terrain's colour where SWISSIMAGE has no image: Italy and"
        f" every {tile_km:g} km cell it does not cover, about {_fraction_words(fraction)} of the"
        " village's far colour."
    )
    limits = (
        f"The far terrain, the mountains around the {east:g} km x {north:g} km area, has two"
        " limits."
    )
    surface = (
        f"It is a surface of {metres} m means, so summits are drawn 15 to 31 m lower than they are."
    )
    return [
        SECTION_HEADING,  # the heading, then what the section is and where the game lists it
        intro,
        # The four notes, the game's words (the fixed ones, the far colour with the village's).
        *[_const_text(path, name) for name, path in FIXED_NOTES.items()],
        _far_colour_line(),
        meaning,  # what the far colour's note means
        limits,  # the far terrain's two limits
        surface,
        "And outside the area it is smooth up close, a smear and not the real ground.",
        START_SENTENCE,  # the slow start
    ]


def test_every_word_of_the_section_is_a_pinned_piece_in_order():
    text = _section_text()
    position = 0
    for piece in _pieces():
        piece = _flat(piece)
        assert text.count(piece) == 1, f"the section holds this piece once: {piece!r}"
        found = text.index(piece)
        between = text[position:found].strip()
        assert found >= position, f"out of order, or inside another piece: {piece!r}"
        assert not between, f"prose no test pins, before {piece!r}: {between!r}"
        position = found + len(piece)
    rest = text[position:].strip()
    assert not rest, f"prose no test pins, after the last piece: {rest!r}"


def test_the_explanation_follows_the_far_colour_note_it_explains():
    # "That last one" is the far colour's note only while that note is the line before it.
    text = _section_text()
    note = _flat(_far_colour_line())
    assert text.count(note) == 1
    assert text.index(note) + len(note) + 1 == text.index("That last one"), (
        "the explanation stands right after the far colour's note"
    )


def test_the_intro_s_claims_are_the_games():
    source = MAIN_GD.read_text(encoding="utf-8")
    # "under Placeholders": the credits' heading, then the three fixed notes, in the template's order.
    listed = re.search(
        r'"Placeholders",\s*BuildingLoader\.WALLS_NOTE,\s*TreeLoader\.TREES_NOTE,\s*STREAMS_NOTE\s*\]',
        source,
    )
    assert listed, "main.gd lists the walls', the trees' and the streams' notes under Placeholders"
    after = source[listed.end() :]
    assert re.match(
        r"\s*\)\s*if not _far_colour_note\.is_empty\(\):\s*lines\.append\(_far_colour_note\)", after
    ), "main.gd lists the far colour's note after them, when it is not empty"
    # "the first four": the three fixed notes and the far colour's.
    assert len(FIXED_NOTES) + 1 == 4
    # "(Escape)": the pause action's key.
    project = PROJECT_GODOT.read_text(encoding="utf-8")
    pause = re.search(r"^pause=\{.*?\n\}", project, re.MULTILINE | re.DOTALL)
    assert pause, "project.godot has the pause action"
    assert f'"physical_keycode":{KEY_ESCAPE},' in pause.group(0), "the pause action is Escape"
