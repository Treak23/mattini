"""Pinning tests for brief v0.5.0-11 (0.4.0's whole-range review residue: S-05's second half and
png_l8's words, the v0.4.0-01 batch log's residue): tools/stars_table.py gets its first tests, and
the PNG writer names what it encodes.

Pinned decisions:
- tools/stars_table.py (brief v0.4.0-06; no change): a source of any size but 53316318 bytes is
  refused before anything is written (exit 1, one line naming the size found and the one wanted,
  no output file), then any other SHA-256; its formatter `build` turns catalogue records (450
  characters and an LF, RAhms at bytes 18-28, DEdms at 30-40 with the sign at byte 30, Vmag at
  42-46) into the header and one line per star with V <= 6.0, sorted by V, then right
  ascension, then declination, 4 decimals for the positions and 2 for V. The records here are
  synthetic (no catalogue is downloaded): their order in the file, by V and by right ascension
  all differ, one sits at V 6.00 exactly, one at 6.01, one has a blank V, and one has a
  declination of -00 00 00.5 whose sign only byte 30 carries; two share a V (the tie-break by
  right ascension, the later one first in the file) and two share a V and a right ascension (the
  tie-break by declination, the northern one first in the file). The expected lines were computed
  by hand from the ReadMe's rule.
- `mattini.surfaces.png_l8(pixels, top=ROAD, *, what="classes")`: its three refusals name what it
  encodes, "the <what> must be a two-dimensional array of uint8", "<columns> × <rows> <what> do
  not make a PNG" and "the <what> are 0 to <top>, found <max>"; the classes' words are unchanged
  byte for byte; the step and `write_surfaces` encode the flow with `what="flow codes"` and the
  classes with the default words (a refused class grid in either says "the classes"). The
  keyword changes no byte of any PNG: the designed fixture PNGs (classes and flow) are written
  again here, and their SHA-256s stay pinned by test_surfaces_fixture.py and
  test_surfaces_flow.py.

Does NOT prove: that the real catalogue makes the shipped table (the table's own SHA-256 is pinned
by test_m4_05_stars.gd; the script's real run needs the 53 MB download); that every message of
surfaces.py names its subject (only png_l8's three are read here).
"""

import hashlib
import importlib.util
import inspect
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from test_surfaces_fixture import BOX
from test_surfaces_flow import GENERATED, _build, _case

from mattini import surfaces
from mattini.surfaces import FLOW_CODES, SurfacesError, png_l8, read_png_l8, write_surfaces

REPO = Path(__file__).resolve().parents[2]
STARS_TABLE = REPO / "tools" / "stars_table.py"
SOURCE_BYTES = 53316318
SOURCE_SHA256 = "58ceabb104d647160d9437ce6e513a02a036bb4ad9f8879a5a22fd52943616e0"


def _stars_table():
    spec = importlib.util.spec_from_file_location("stars_table", STARS_TABLE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _record(hip: int, rahms: str, dedms: str, vmag: str) -> str:
    """A catalogue record as the ReadMe lays it out: 450 characters, '|' between the fields."""
    line = f"H|{hip:>12}| |{rahms}|{dedms}|{vmag:>5}|"
    assert line[17:28] == rahms and line[29:40] == dedms and line[41:46] == f"{vmag:>5}"
    return line.ljust(449, " ") + "|"


# In the file's order: neither V's order nor the right ascension's.
RECORDS = [
    _record(11767, "02 31 49.09", "-05 30 00.0", "1.97"),
    _record(20000, "05 00 00.00", "+10 00 00.0", "6.01"),
    _record(91262, "18 36 56.20", "+38 46 58.8", "0.03"),
    _record(30000, "06 00 00.00", "+20 00 00.0", ""),
    _record(40000, "00 00 00.00", "-00 00 00.5", "6.00"),
    _record(50000, "01 00 00.00", "+01 00 00.0", "1.97"),
    _record(60000, "03 00 00.00", "+02 00 00.0", "3.00"),
    _record(70000, "03 00 00.00", "-02 00 00.0", "3.00"),
]
# By hand: ra = (h + m/60 + s/3600) * 15, dec = sign * (d + m/60 + s/3600), sorted by V, then
# right ascension (15 before 37.9545 at V 1.97), then declination (-2 before 2 at V 3.00, ra 45).
STAR_LINES = (
    "279.2342,38.7830,0.03\n"
    "15.0000,1.0000,1.97\n"
    "37.9545,-5.5000,1.97\n"
    "45.0000,-2.0000,3.00\n"
    "45.0000,2.0000,3.00\n"
    "0.0000,-0.0001,6.00\n"
)


def test_stars_table_refuses_a_source_of_another_size_and_writes_nothing(tmp_path):
    source = tmp_path / "hip_main.dat"
    source.write_bytes(b"not the catalogue")
    out = tmp_path / "stars.csv"
    done = subprocess.run(
        [sys.executable, "-I", str(STARS_TABLE), str(source), str(out)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 1
    assert done.stderr == f"stars_table: the file has 17 bytes, not {SOURCE_BYTES}\n"
    assert done.stdout == ""
    assert not out.exists(), "nothing written"


def test_stars_table_refuses_a_source_of_the_right_size_and_another_sha256():
    module = _stars_table()
    data = bytes(SOURCE_BYTES)
    found = hashlib.sha256(data).hexdigest()
    with pytest.raises(SystemExit) as refusal:
        module._check(data)
    assert refusal.value.code == f"stars_table: the file has SHA-256 {found}, not {SOURCE_SHA256}"


def test_stars_table_formats_synthetic_records_as_the_readme_says():
    module = _stars_table()
    text = module.build(("\n".join(RECORDS) + "\n").encode("ascii"))
    header = (
        "# Stars derived from the Hipparcos Catalogue (ESA 1997, ESA SP-1200): stars to V 6.0,"
        " positions rounded and reformatted. Credit: ESA. CC BY-NC 3.0 IGO,"
        " https://creativecommons.org/licenses/by-nc/3.0/igo/\n"
    )
    assert text.startswith(header), "the credit first"
    assert text.count("\n# ") == 2 and "\nra_deg,dec_deg,vmag\n" in text, "four header lines"
    assert text == module.HEADER + STAR_LINES
    assert text.endswith("\n") and "\r" not in text


def test_png_l8_takes_what_it_encodes_as_a_keyword():
    what = inspect.signature(png_l8).parameters.get("what")
    assert what is not None, "png_l8 takes what="
    assert what.kind is inspect.Parameter.KEYWORD_ONLY
    assert what.default == "classes"


@pytest.mark.parametrize(
    ("pixels", "words"),
    [
        (np.zeros((3, 3), dtype=np.int64), "the {} must be a two-dimensional array of uint8"),
        (np.zeros((0, 3), dtype=np.uint8), "3 × 0 {} do not make a PNG"),
    ],
    ids=["not-uint8", "empty"],
)
def test_png_l8_names_what_it_refuses(pixels, words):
    with pytest.raises(SurfacesError) as classes:
        png_l8(pixels)
    assert str(classes.value) == words.format("classes"), "the classes' words, unchanged"
    with pytest.raises(SurfacesError) as flow:
        png_l8(pixels, FLOW_CODES, what="flow codes")
    assert str(flow.value) == words.format("flow codes")


def test_png_l8_names_the_bound_of_what_it_encodes():
    with pytest.raises(SurfacesError) as classes:
        png_l8(np.full((3, 3), 5, dtype=np.uint8))
    assert str(classes.value) == "the classes are 0 to 4, found 5"
    with pytest.raises(SurfacesError) as flow:
        png_l8(np.full((3, 3), FLOW_CODES + 1, dtype=np.uint8), FLOW_CODES, what="flow codes")
    assert str(flow.value) == f"the flow codes are 0 to {FLOW_CODES}, found {FLOW_CODES + 1}"


def test_the_step_names_the_flow_codes_it_refuses(tmp_path, monkeypatch):
    designed = read_png_l8((GENERATED / "surfaces" / "fixture-flow.png").read_bytes())
    too_high = designed.copy()
    too_high[0, 0] = FLOW_CODES + 1
    monkeypatch.setattr(surfaces, "flow_grid", lambda *args: too_high)
    case = _case(tmp_path)
    # the pixels' comparison passes, so the step reaches the flow's encoder
    sha = hashlib.sha256(too_high.tobytes()).hexdigest()
    case.config["areas"]["fixture"]["expected_flow_pixels_sha256"] = sha
    with pytest.raises(SurfacesError) as refusal:
        _build(case)
    assert f"the flow codes are 0 to {FLOW_CODES}, found {FLOW_CODES + 1}" in str(refusal.value)
    assert not case.out.exists(), "refused before anything is written"


def test_write_surfaces_names_the_flow_codes_it_refuses(tmp_path):
    block = json.loads((GENERATED / "surfaces" / "fixture.json").read_text(encoding="utf-8"))
    grid = read_png_l8((GENERATED / "surfaces" / "fixture.png").read_bytes())
    flow = read_png_l8((GENERATED / "surfaces" / "fixture-flow.png").read_bytes())
    flow[0, 0] = FLOW_CODES + 1
    with pytest.raises(SurfacesError) as refusal:
        write_surfaces(
            tmp_path, "fixture", grid, BOX, 0.2, block["world_sha256"], block["source"], flow, 2.0
        )
    assert str(refusal.value) == f"the flow codes are 0 to {FLOW_CODES}, found {FLOW_CODES + 1}"
    assert not (tmp_path / "surfaces").exists(), "refused before anything is written"


def test_write_surfaces_names_the_classes_it_refuses(tmp_path):
    block = json.loads((GENERATED / "surfaces" / "fixture.json").read_text(encoding="utf-8"))
    grid = read_png_l8((GENERATED / "surfaces" / "fixture.png").read_bytes())
    flow = read_png_l8((GENERATED / "surfaces" / "fixture-flow.png").read_bytes())
    grid[0, 0] = 5
    with pytest.raises(SurfacesError) as refusal:
        write_surfaces(
            tmp_path, "fixture", grid, BOX, 0.2, block["world_sha256"], block["source"], flow, 2.0
        )
    assert str(refusal.value) == "the classes are 0 to 4, found 5"
    assert not (tmp_path / "surfaces").exists(), "refused before anything is written"


def test_the_step_names_the_classes_it_refuses(tmp_path, monkeypatch):
    designed = read_png_l8((GENERATED / "surfaces" / "fixture.png").read_bytes())
    too_high = designed.copy()
    too_high[0, 0] = 5
    monkeypatch.setattr(surfaces, "class_grid", lambda *args: too_high)
    case = _case(tmp_path)
    # the pixels' comparison passes at every cell size, so the step reaches the classes' encoder
    sha = hashlib.sha256(too_high.tobytes()).hexdigest()
    expected = case.config["areas"]["fixture"]["expected_pixels_sha256"]
    for cell in expected:
        expected[cell] = sha
    with pytest.raises(SurfacesError) as refusal:
        _build(case)
    assert "the classes are 0 to 4, found 5" in str(refusal.value)
    assert "flow" not in str(refusal.value)
    assert not case.out.exists(), "refused before anything is written"


def test_the_keyword_changes_no_byte_of_the_designed_pngs():
    for name, top, what in [
        ("fixture.png", 4, "classes"),
        ("fixture-flow.png", 240, "flow codes"),
    ]:
        designed = (GENERATED / "surfaces" / name).read_bytes()
        pixels = read_png_l8(designed)
        assert png_l8(pixels, top, what=what) == designed, name
        assert png_l8(pixels, top, what="anything else") == designed, name
