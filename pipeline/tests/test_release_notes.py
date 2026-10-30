"""Pinning tests for brief v0.5.0-06: the Release's notes carry every credit the game shows.

Pinned decisions (CLAUDE.md Hard Rule 3: every shared build shows `© swisstopo` and any
dataset-specific wording; SPEC §13 row 51: the stars' credit word for word, "Credit: ESA",
CC BY-NC 3.0 IGO and its URL; docs/RELEASE.md §A Attribution; brief v0.5.0-06 decision 5):
the committed template tools/release_notes.md, from which tools/release_pack.sh renders every
Release's notes, holds
- `© swisstopo`;
- each dataset line the pause screen shows for the real village, `<dataset> <edition>,
  <attribution>` (game/scripts/main.gd `_dataset_line`), computed from config/datasets.json and
  the lock (swissSURFACE3D's edition is the first and last of its tiles' editions, as the trees
  block gives it) and equal to SPEC §10's list, on a line of its own;
- the stars' credit, game/sky/stars.csv's first line without its "# ", which is also
  main.gd's STARS_NOTE, on a line of its own, word for word;
- the CC0 textures' source (Poly Haven, CC0);
- the three placeholders @VERSION@, @SHA@ and the line @SHA256SUMS@, and no other.

Does NOT prove: that the pause screen shows these lines (the game's tests,
test_main_scene_data.gd); that the published Release shows the rendered notes (the session's
audit of the draft); that a dataset added later is credited here (the computed set fails then,
by design: the test reads the configs).
"""

import json
import re

from fake_tools import REPO

TEMPLATE = REPO / "tools" / "release_notes.md"
SPEC_LINES = [
    "swissalti3d 2024, © swisstopo",
    "swissbuildings3d 2020, © swisstopo",
    "swissimage 2023, © swisstopo",
    "swisssurface3d 2021-2022, © swisstopo",
    "swisstlm3d 2026-02, © swisstopo",
]


def _template():
    assert TEMPLATE.is_file(), "tools/release_notes.md is missing"
    return TEMPLATE.read_text(encoding="utf-8")


def _dataset_lines():
    datasets = json.loads((REPO / "config" / "datasets.json").read_text(encoding="utf-8"))
    lock = json.loads((REPO / "config" / "datasets.lock.json").read_text(encoding="utf-8"))
    lines = []
    for name, entry in sorted(datasets["datasets"].items()):
        edition = entry.get("edition")
        if edition is None:
            tiles = lock["datasets"][name]["tiles"].values()
            editions = sorted({tile["edition"] for tile in tiles})
            edition = editions[0] if len(editions) == 1 else f"{editions[0]}-{editions[-1]}"
        lines.append(f"{name} {edition}, {entry['attribution']}")
    return lines


def _stars_note():
    first = (REPO / "game" / "sky" / "stars.csv").read_text(encoding="utf-8").splitlines()[0]
    assert first.startswith("# Stars derived from the Hipparcos Catalogue"), first
    return first[2:]


def _main_gd_stars_note():
    text = (REPO / "game" / "scripts" / "main.gd").read_text(encoding="utf-8")
    block = re.search(r"^const STARS_NOTE := \((.*?)^\)", text, re.DOTALL | re.MULTILINE)
    assert block, "main.gd has no const STARS_NOTE := ( ... )"
    return "".join(re.findall(r'"((?:[^"\\]|\\.)*)"', block.group(1)))


def test_the_dataset_lines_are_the_configs_and_spec_s():
    assert _dataset_lines() == SPEC_LINES


def test_the_template_carries_swisstopo_and_every_dataset_line():
    lines = _template().splitlines()
    assert any("© swisstopo" in line for line in lines)
    for line in SPEC_LINES:
        assert line in lines, f"the notes lack the credit line: {line}"


def test_the_template_carries_the_stars_credit_word_for_word():
    note = _stars_note()
    assert note == _main_gd_stars_note(), "stars.csv's first line and main.gd's STARS_NOTE agree"
    assert "Credit: ESA. CC BY-NC 3.0 IGO" in note
    assert note in _template().splitlines(), "the stars' credit, on a line of its own"


def test_the_template_names_the_textures_source():
    text = _template()
    assert "Poly Haven" in text and "CC0" in text


def test_the_template_has_exactly_the_three_placeholders():
    text = _template()
    assert set(re.findall(r"@[A-Z0-9_]+@", text)) == {"@VERSION@", "@SHA@", "@SHA256SUMS@"}
    assert "@SHA256SUMS@" in text.splitlines(), "@SHA256SUMS@ is a line of its own"
