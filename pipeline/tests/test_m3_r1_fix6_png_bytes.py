"""Brief M3-R1-fix-6: the surfaces PNG's bytes are design's, so the manifest is the same everywhere.

Design's answer to M3 R1 I-01 (2026-10-15, SPEC §13 row 39): the PNG's SHA-256 goes into the
surfaces description and from there into manifest.json, and its bytes depend on the machine's
deflate (zlib 1.3 and 1.3.2 write the same bytes; zlib-ng does not, measured). So each surfaces
config holds `expected_png_sha256`, keyed by cell exactly as `expected_pixels_sha256` is, and the
step refuses a PNG with another SHA-256 before anything is written, naming the machine's zlib.

Pinned decisions:
1. Every surfaces config has `expected_png_sha256` with the same keys as
   `expected_pixels_sha256`, each 64 lower-case hex digits; `check_surfaces_config` refuses a
   config without it or with a malformed value.
2. The shared fixture's values are design's (below; computed with zlib 1.3.2, the 0.2 one equal
   to the committed fixture PNG, which zlib 1.3 wrote). The village's 0.2 value is the PNG the
   R1 inputs lens built independently (1'148'917 bytes, SHA-256 starting 8922edf9).
3. The committed fixture PNG re-encodes byte for byte on the machine that runs the gate: a
   machine whose deflate writes other bytes fails the gate, and the message names its zlib.
4. `build_surfaces` refuses a PNG whose SHA-256 is not the config's for the cell with a
   SurfacesError that names zlib and `zlib.ZLIB_RUNTIME_VERSION`, and writes no PNG.

Does NOT prove: that every other deflate is refused by the fixture (a small grid can compress
alike: measured at 0.5 and 1 m, where zlib-ng wrote the fixture's bytes); the manifest's own
comparison (the brief's builder tests it); Windows (not measured).
"""

import copy
import hashlib
import re
import zlib
from pathlib import Path

import pytest
from test_surfaces_checks import _build, _case

from mattini import surfaces
from mattini.surfaces import (
    SurfacesError,
    check_surfaces_config,
    load_surfaces_config,
    png_l8,
    read_png_l8,
)

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "shared" / "surfaces_fixture"
FIXTURE_PNG = FIXTURE / "generated" / "surfaces" / "fixture.png"
FIXTURE_PNG_SHA256 = {  # design's data, zlib 1.3.2 (the 0.2 one is the committed fixture PNG)
    "0.2": "ef3828f91d98d0a68309981621e0fd706f0e07c1dbd3767dace243b83775e347",
    "0.5": "e0106ac1337bb0b12adc0a4a175a10954d6ecfc4d8dbd4c98687d92f1e0d1554",
    "1": "49e7647f6f1807291e1cd02c042f1dee5b9692a3bdd51425954d0686b3c17240",
}
VILLAGE_PNG_0_2_PREFIX = "8922edf9"  # the R1 inputs lens's own build of the village
HEX64 = re.compile(r"[0-9a-f]{64}")
CONFIGS = [REPO / "config" / "surfaces.json", FIXTURE / "surfaces.json"]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.mark.parametrize("path", CONFIGS, ids=["village", "fixture"])
def test_every_surfaces_config_names_the_png_of_each_cell(path):
    (area,) = load_surfaces_config(path)["areas"].values()
    assert set(area["expected_png_sha256"]) == set(area["expected_pixels_sha256"])
    assert all(HEX64.fullmatch(value) for value in area["expected_png_sha256"].values())


def test_the_values_are_designs():
    (fixture,) = load_surfaces_config(FIXTURE / "surfaces.json")["areas"].values()
    assert fixture["expected_png_sha256"] == FIXTURE_PNG_SHA256
    assert _sha(FIXTURE_PNG.read_bytes()) == FIXTURE_PNG_SHA256["0.2"]
    (village,) = load_surfaces_config(REPO / "config" / "surfaces.json")["areas"].values()
    assert village["expected_png_sha256"]["0.2"].startswith(VILLAGE_PNG_0_2_PREFIX)


@pytest.mark.parametrize("value", [None, {}, {"0.2": "ABC"}, "x" * 64])
def test_a_config_without_well_formed_png_values_is_refused(value):
    data = copy.deepcopy(load_surfaces_config(FIXTURE / "surfaces.json"))
    (area,) = data["areas"].values()
    if value is None:
        del area["expected_png_sha256"]
    else:
        area["expected_png_sha256"] = value
    with pytest.raises(SurfacesError, match="expected_png_sha256"):
        check_surfaces_config(data)


def test_this_machine_writes_the_designed_png_bytes():
    png = FIXTURE_PNG.read_bytes()
    again = png_l8(read_png_l8(png))
    assert _sha(again) == FIXTURE_PNG_SHA256["0.2"], (
        f"this machine's zlib {zlib.ZLIB_RUNTIME_VERSION} writes other PNG bytes than design's"
    )


def test_a_png_that_is_not_the_configs_is_refused_naming_zlib(tmp_path, monkeypatch):
    case = _case(tmp_path)
    original = zlib.compress  # surfaces.zlib is this module: patch with a closure over it
    monkeypatch.setattr(surfaces.zlib, "compress", lambda data, level=-1: original(data, 1))
    with pytest.raises(SurfacesError) as caught:
        _build(case)
    text = str(caught.value)
    assert "zlib" in text and zlib.ZLIB_RUNTIME_VERSION in text, text
    assert not list(case.out.rglob("*.png")), "no PNG may be written"
