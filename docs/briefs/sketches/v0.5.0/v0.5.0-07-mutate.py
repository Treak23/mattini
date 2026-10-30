"""The mutation rows of brief v0.5.0-07, as the pin author ran them on the throwaway (2026-10-30).

python3 -I docs/briefs/sketches/v0.5.0/v0.5.0-07-mutate.py N   applies row N to the working tree
(run from the repository's root; each edit must match exactly once). The rows' meaning, the
tests that fail and the harm are in the brief and in v0.5.0-07-PINSPEC.md. A builder's code may
read otherwise: the brief's table names the mistake, not these lines.
"""

import sys
from pathlib import Path

RIG = "game/scripts/sky/sky_rig.gd"
RENDER_PHOTO = "game/tests/render/render_photo.gd"
RENDER_TREES = "game/tests/render/render_trees.gd"
CONSTANT = "const HAZE_DENSITY := 5.27e-5\n"
ON = "\tenvironment.fog_enabled = true\n"
MODE = "\tenvironment.fog_mode = Environment.FOG_MODE_EXPONENTIAL\n"
DENSITY = "\tenvironment.fog_density = HAZE_DENSITY\n"
AERIAL = "\tenvironment.fog_aerial_perspective = 1.0\n"
SKY = "\tenvironment.fog_sky_affect = 0.0\n"
EXPOSURE = "\t_environment.tonemap_exposure = _exposure(sun_el)\n"
PHOTO_OFF = "\t# And no haze (brief v0.5.0-07): the fog would add the sky's colour to every pixel.\n"
TREES_OFF = (
    "\t# No haze (brief v0.5.0-07): the fog would add the sky's colour to the crowns and the"
    " ground.\n"
    '\tvar environment: Environment = main.get_node("Environment").environment\n'
    "\tenvironment.fog_enabled = false\n"
)
TREES_CAPTURE = "\tvar image := await Common.capture(self)\n"
FOG_OFF = "\tenvironment.fog_enabled = false\n"

ROWS = {
    1: [(RIG, ON, "")],
    2: [(RIG, MODE, MODE.replace("EXPONENTIAL", "DEPTH"))],
    3: [(RIG, MODE, "")],
    4: [(RIG, CONSTANT, CONSTANT.replace("5.27e-5", "0.01"))],
    5: [(RIG, CONSTANT, CONSTANT.replace("5.27e-5", "1e-5"))],
    6: [(RIG, DENSITY, DENSITY.replace("HAZE_DENSITY", "6.0e-5"))],
    7: [
        (RIG, CONSTANT, CONSTANT.replace("HAZE_DENSITY", "FOG_DENSITY")),
        (RIG, DENSITY, DENSITY.replace("HAZE_DENSITY", "FOG_DENSITY")),
    ],
    8: [(RIG, AERIAL, AERIAL.replace("1.0", "0.0"))],
    9: [(RIG, AERIAL, "")],
    10: [(RIG, SKY, "")],
    11: [(RIG, SKY, SKY + "\tenvironment.fog_height_density = 0.002\n")],
    12: [(RIG, EXPOSURE, EXPOSURE + "\t_environment.fog_enabled = sun_el > -6.0\n")],
    13: [
        (
            RIG,
            EXPOSURE,
            EXPOSURE
            + "\t_environment.fog_density = HAZE_DENSITY * maxf(_sun.light_energy, 0.2)\n",
        )
    ],
    14: [(RENDER_PHOTO, PHOTO_OFF + "\tenvironment.fog_enabled = false\n", "")],
    15: [(RENDER_TREES, TREES_OFF + TREES_CAPTURE, TREES_CAPTURE + TREES_OFF)],
    # Rows 16 to 21: the checker's findings, added at the re-cut on origin/main.
    16: [(RENDER_TREES, FOG_OFF, "#" + FOG_OFF)],
    17: [(RIG, SKY, SKY + "\tenvironment.fog_sun_scatter = 0.5\n")],
    18: [(RIG, SKY, SKY + "\tenvironment.volumetric_fog_enabled = true\n")],
    19: [(RIG, SKY, SKY + "\tenvironment.fog_height_density = 5e-5\n")],
    20: [(RENDER_PHOTO, FOG_OFF, "\tif false:\n\t" + FOG_OFF)],
    21: [(RIG, EXPOSURE, EXPOSURE + "\t_environment.fog_sun_scatter = 0.1\n")],
}


def main() -> None:
    for path, old, new in ROWS[int(sys.argv[1])]:
        text = Path(path).read_text(encoding="utf-8")
        if text.count(old) != 1:
            sys.exit(f"{path}: {old!r} found {text.count(old)} times")
        Path(path).write_text(text.replace(old, new), encoding="utf-8")


if __name__ == "__main__":
    main()
