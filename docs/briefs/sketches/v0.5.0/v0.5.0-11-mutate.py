"""The mutation rows of brief v0.5.0-11, as the pin author ran them on the throwaway (2026-10-30).

python3 -I docs/briefs/sketches/v0.5.0/v0.5.0-11-mutate.py N   applies row N to the working tree
(run from the repository's root; each edit must match exactly once). The rows' meaning, the
tests that fail and the harm are in the brief and in v0.5.0-11-PINSPEC.md. A builder's code may
read otherwise: the brief's table names the mistake, not these lines. Rows 19 and 20 mutate the
pinned margins test itself (they show its new counts are not vacuous); every other row mutates
production code or the stars script. Rows 31 to 34 were added at the re-cut on origin/main for the
checker's two P3 findings (the classes' calls mislabelled, the sort's tie-breaks).
"""

import sys
from pathlib import Path

RIG = "game/scripts/sky/sky_rig.gd"
SHADER = "game/shaders/sky_physical.gdshader"
CLOCK = "game/scripts/sky/sky_clock.gd"
MAIN = "game/scripts/main.gd"
SITE = "game/scripts/sky/sky_site.gd"
MARGINS = "game/tests/test_v040_04_sky_clock_margins.gd"
SURFACES = "pipeline/mattini/surfaces.py"
STARS = "tools/stars_table.py"

RA_IF = "\t\tif not (ra >= 0.0 and ra < 360.0):\n"
DEC_IF = "\t\tif not (dec > -90.0 and dec < 90.0):\n"
RA_RETURN = "\t\t\t\t\t% [path, number, fields[0], line]\n\t\t\t\t)\n\t\t\t)\n\t\t\treturn null\n"
DECLARATION = "hint_default_black, repeat_enable;\n"
COMMENT = (
    "// mattini: repeat_enable (brief v0.5.0-11): the linear filter wraps across right"
    " ascension 0/360\n"
    "// mattini: instead of clamping a one-texel seam there; it also wraps v across the poles"
    " (row 0\n"
    "// mattini: blends with row 2047 within half a texel of a pole), which is harmless: the"
    " stars'\n"
    "// mattini: rows run from 8 to 2036, both pole rows are black.\n"
)
SUN_DOC = (
    "## [0, 360) as a double; stored in the Vector2 (float32) a value within 1.5e-5 of 360 reads\n"
    "## 360.0, which means north as 0 does (every user takes its sine and cosine). Elevation"
    " apparent\n"
)
MOON_DOC = (
    "## azimuth true, clockwise from north, in [0, 360) as a double; stored in the Vector3"
    " (float32)\n"
    "## a value within 1.5e-5 of 360 reads 360.0, which means north as 0 does. The fraction\n"
)
DIFFERS = (
    'or ManifestValue.differs(block["world_sha256"], manifest.get("world_sha256"))\n'
)
NUMBER = "\t\tif not number or not is_finite(value) or absf(value) > LIMITS[key]:\n"
AREA = '\tif typeof(block["area"]) != TYPE_STRING or not areas.has(block["area"]):\n'
WORLD = (
    '\t\tproblem = BuildingChunks._check_world(world, path, manifest.get("world"))\n'
)
SIGNATURE = 'def png_l8(pixels: np.ndarray, top: int = ROAD, *, what: str = "classes") -> bytes:\n'
FLOW_CALL = (
    '    flow_png = png_l8(flow, FLOW_CODES, what="flow codes")\n    flow_png_sha256'
)
WRITER_CALL = (
    '        flow_png = png_l8(flow, FLOW_CODES, what="flow codes")\n    e_min'
)
WRITER_CLASSES = "        png = png_l8(grid)\n    if flow_png is None:"
STEP_CLASSES = "    png = png_l8(grid)\n    png_sha256"
FLOW_WORDS = 'png_l8(grid, what="flow codes")'

ROWS = {
    1: [(RIG, RA_IF, "\t\tif false:\n")],
    2: [(RIG, RA_IF, RA_IF.replace("ra < 360.0", "ra <= 360.0"))],
    3: [(RIG, RA_IF, RA_IF.replace("ra >= 0.0", "ra > 0.0"))],
    4: [(RIG, DEC_IF, "\t\tif false:\n")],
    5: [(RIG, DEC_IF, "\t\tif absf(dec) > 90.0:\n")],
    6: [
        (RIG, "%s line %d: right ascension", "%s: right ascension"),
        (RIG, "% [path, number, fields[0], line]", "% [path, fields[0], line]"),
    ],
    7: [(RIG, RA_RETURN, RA_RETURN.replace("\t\t\treturn null\n", ""))],
    8: [
        (RIG, "floor(0.5 / cos(deg_to_rad(dec)))", "floor(0.6 / cos(deg_to_rad(dec)))")
    ],
    9: [(SHADER, DECLARATION, "hint_default_black;\n")],
    10: [(SHADER, COMMENT, "")],
    11: [(CLOCK, SUN_DOC, "## [0, 360). Elevation apparent\n")],
    12: [(CLOCK, MOON_DOC, "## azimuth true, clockwise from north. The fraction\n")],
    13: [
        (
            MAIN,
            "FALLBACK_SUN_AZIMUTH_GRID_DEG := 184.67",
            "FALLBACK_SUN_AZIMUTH_GRID_DEG := 184.65",
        )
    ],
    14: [
        (
            MAIN,
            "FALLBACK_SUN_ELEVATION_DEG := 50.1",
            "FALLBACK_SUN_ELEVATION_DEG := 50.0",
        )
    ],
    15: [(SITE, DIFFERS, 'or block["world_sha256"] != manifest.get("world_sha256")\n')],
    16: [(SITE, WORLD, "\t\tpass\n")],
    17: [(SITE, NUMBER, "\t\tif not is_finite(value) or absf(value) > LIMITS[key]:\n")],
    18: [(SITE, AREA, "\tif false:\n")],
    19: [
        (
            MARGINS,
            '\t\tif v["sun_elevation_deg"] > 2.0:\n',
            '\t\tif v["sun_elevation_deg"] > -90.0:\n',
        )
    ],
    20: [
        (
            MARGINS,
            '\tfor v in _doc["vectors"]:\n\t\tvar got := SkyClock.moon(',
            "\tfor v in []:\n\t\tvar got := SkyClock.moon(",
        )
    ],
    21: [
        (
            CLOCK,
            "\televation += _refraction_arcsec(elevation) / 3600.0\n",
            "\televation += 0.0 * _refraction_arcsec(elevation) / 3600.0\n",
        )
    ],
    22: [
        (SURFACES, 'f"the {what} must be', 'f"the classes must be'),
        (SURFACES, "{rows} {what} do not", "{rows} classes do not"),
        (SURFACES, 'f"the {what} are 0 to', 'f"the classes are 0 to'),
    ],
    23: [(SURFACES, FLOW_CALL, FLOW_CALL.replace(', what="flow codes"', ""))],
    24: [(SURFACES, WRITER_CALL, WRITER_CALL.replace(', what="flow codes"', ""))],
    25: [(SURFACES, SIGNATURE, SIGNATURE.replace('"classes"', '"class codes"'))],
    26: [(STARS, "    if len(data) != SOURCE_BYTES:\n", "    if False:\n")],
    27: [
        (STARS, 'f"{ra:.4f},{dec:.4f},{v:.2f}\\n"', 'f"{ra:.3f},{dec:.3f},{v:.2f}\\n"')
    ],
    28: [
        (
            STARS,
            "    stars.sort()\n",
            "    stars.sort(key=lambda s: (s[1], s[0], s[2]))\n",
        )
    ],
    29: [(STARS, "float(vmag) > V_MAX", "float(vmag) >= V_MAX")],
    30: [
        (
            STARS,
            'sign = -1 if dec_field[0] == "-" else 1',
            'sign = -1 if d.startswith("-") else 1',
        )
    ],
    # Rows 31 to 34: the checker's fixes on origin/main (the re-cut, 2026-10-30).
    31: [
        (SURFACES, WRITER_CLASSES, WRITER_CLASSES.replace("png_l8(grid)", FLOW_WORDS))
    ],
    32: [(SURFACES, STEP_CLASSES, STEP_CLASSES.replace("png_l8(grid)", FLOW_WORDS))],
    33: [(STARS, "    stars.sort()\n", "    stars.sort(key=lambda s: s[0])\n")],
    34: [
        (
            STARS,
            "    stars.sort()\n",
            "    stars.sort(key=lambda s: (s[0], s[2], s[1]))\n",
        )
    ],
}


def main(argv: list[str]) -> int:
    row = int(argv[1])
    for path, old, new in ROWS[row]:
        text = Path(path).read_text(encoding="utf-8")
        if text.count(old) != 1:
            sys.exit(f"row {row}: {path}: {old!r} found {text.count(old)} times")
        Path(path).write_text(text.replace(old, new), encoding="utf-8")
    print(f"row {row} applied")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
