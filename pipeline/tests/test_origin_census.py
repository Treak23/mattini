"""Pinning tests for brief M1-01: the Hard Rule 4 census, scoped by exclusion (M0 R1 C-02).

Pinned decisions (docs/history/ARCS.md §M0, D10; lesson 37): the census reads every file
git would commit (`git ls-files -co --exclude-standard`), of any suffix, except the homes
of design data and oracles: `config/`, `docs/`, `game/addons/`, any folder named `tests`,
Markdown prose and `pipeline/uv.lock`. It looks for the origin in every spelling the M0
review found: the plain number with or without separators, e-notation, and the
kilometre pair (a 2623 followed within 12 characters by a 1096, which also catches a
village tile id or an LV95 point written into code). Since M2-01 (M1 R1 T-05) also: the
kilometre pair reversed (a 1096 within 12 characters before a 2623), the pair on lines up
to three apart in either order (two constants on neighbouring lines), and a mantissa with
trailing zeros (`2.6230e6`, `2.62300E+06`, `2623.0e3`); a pair four lines apart is not
counted, the bound design chose against false alarms.

It proves TEXT only (lesson 5): it finds these spellings written in a scanned file, never
that the code does not place the world by another origin. A second origin computed from
other numbers, or spelt in a way not listed here, passes it.
"""

import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

EXCLUDED_PREFIXES = ("config/", "docs/", "game/addons/")
EXCLUDED_FILES = {"pipeline/uv.lock"}
SPELLINGS = [
    r"2[' _]?623[' _]?000",  # 2623000, 2'623'000, 2_623_000, 2 623 000
    r"1[' _]?096[' _]?000",
    r"2\.623(?:_?0)*[eE]\+?0*6",  # 2.623e6, 2.623E+06, 2.6230e6, 2.62300E+06
    r"2_?623(?:\.0*)?[eE]\+?0*3",  # 2623e3, 2_623e3, 2623.0e3
    r"1\.096(?:_?0)*[eE]\+?0*6",  # 1.096e6, 1.0960e6
    r"1_?096(?:\.0*)?[eE]\+?0*3",  # 1096e3, 1_096e3, 1096.0e3
    r"2623.{0,12}1096",  # the kilometre pair: Vector2i(2623, 1096), "2623-1096"
    r"1096.{0,12}2623",  # the pair reversed: (1096, 2623)
    r"2623[^\n]*\n(?:[^\n]*\n){0,2}[^\n]*1096",  # the pair on lines 1 to 3 apart
    r"1096[^\n]*\n(?:[^\n]*\n){0,2}[^\n]*2623",  # and reversed
]
ORIGIN = re.compile("|".join(SPELLINGS))


def _committable() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=REPO,
        check=True,
        capture_output=True,
    ).stdout
    return [p for p in out.decode("utf-8").split("\0") if p]


def _scanned(rel: str) -> bool:
    parts = Path(rel).parts
    return not (
        rel.startswith(EXCLUDED_PREFIXES)
        or rel in EXCLUDED_FILES
        or "tests" in parts[:-1]
        or rel.endswith(".md")
    )


def test_the_origin_lives_only_in_config():
    offenders = []
    for rel in _committable():
        path = REPO / rel
        if not _scanned(rel) or not path.is_file():
            continue
        text = path.read_bytes().decode("utf-8", errors="replace")
        for match in ORIGIN.finditer(text):
            offenders.append(f"{rel}: {match.group(0)!r}")
    assert offenders == [], offenders


@pytest.mark.parametrize(
    "spelling",
    [
        "ORIGIN_E = 2623000.0",
        "origin_n=1_096_000",
        "const ORIGIN_E := 2.623e6",
        "ORIGIN_N = 1096e3",
        "ORIGIN_N = 1_096e3",
        "E = 2.623E+06",
        "const ORIGIN_KM := Vector2i(2623, 1096)",
        'TILE = "2623-1096"',
        "KIRCHPLATZ = (2623825.25, 1096489.75)",
        # M1 R1 T-05, the three spellings mutation C added
        "const ORIGIN_TILE_E_KM := 2623\nconst ORIGIN_TILE_N_KM := 1096",
        "ORIGIN_TILE_KM = (1096, 2623)",
        "ORIGIN_E = 2.6230e6",
        # and their neighbours
        "ORIGIN_N = 1.0960e6",
        "E = 2.62300E+06",
        "ORIGIN_E = 2623.0e3",
        "N_KM = 1096\n# the tile the church square is in\n\nE_KM = 2623",
        "E_KM = 2623\r\nN_KM = 1096\r\n",
    ],
)
def test_every_spelling_the_review_found_is_caught(spelling):
    assert ORIGIN.search(spelling), spelling


@pytest.mark.parametrize(
    "text",
    [
        "E_KM = 2623\n\n\n\nN_KM = 1096",  # four lines apart: beyond the bound design chose
        "E = 2.6231e6",  # another number
        "SPACING_KEYS = ('0.5', '1', '2')",
    ],
)
def test_what_the_census_does_not_count(text):
    assert not ORIGIN.search(text), text


@pytest.mark.parametrize(
    "rel",
    [
        "game/project.godot",
        "game/shaders/terrain_clay.gdshader",
        "game/scripts/terrain/terrain_loader.gd",
        "pipeline/mattini/terrain.py",
        "pipeline/scripts/place.py",
        "tools/export.sh",
        ".claude/hooks/session-start.sh",
    ],
)
def test_code_and_settings_outside_the_named_folders_are_scanned(rel):
    assert _scanned(rel), rel


@pytest.mark.parametrize(
    "rel",
    [
        "config/world.json",
        "docs/SPEC.md",
        "tests/shared/world_vectors.json",
        "pipeline/tests/test_world.py",
        "game/tests/test_world_config.gd",
        "game/addons/gut/gut.gd",
        "pipeline/uv.lock",
        "brain.md",
    ],
)
def test_design_data_oracles_and_prose_are_not(rel):
    assert not _scanned(rel), rel
