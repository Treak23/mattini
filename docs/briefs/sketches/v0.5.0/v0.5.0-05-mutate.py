"""The mutation rows of brief v0.5.0-05, as the pin author ran them on the throwaway (2026-10-30).

python3 -I docs/briefs/sketches/v0.5.0/v0.5.0-05-mutate.py N   applies row N to the working tree
(run from the repository's root; each edit must match exactly once). The rows' meaning, the
tests that fail and the harm are in the brief and in v0.5.0-05-PINSPEC.md. A builder's code may
read otherwise: the brief's table names the mistake, not these lines.
"""

import sys
from pathlib import Path

MAIN = "game/scripts/main.gd"
EXPORT = "tools/export.sh"
RENDER_PHOTO = "game/tests/render/render_photo.gd"
READ = (
    "\tvar read_shadows := _caught(CaptureShadowGrid.from_manifest.bind(manifest_path, world))\n"
    "\tvar shadows: CaptureShadowGrid = read_shadows[0]\n"
    "\tif shadows == null:\n"
    "\t\trefusals.append([SHADOWS_WHAT, read_shadows[1], SHADOWS_FIX])\n"
)
ROOFS = "\t# The roof colours are checked against the buildings: without them there is one cause.\n"
LINE = (
    "\tif shadows != null:\n"
    '\t\tvar text := "mattini %s: shadows %s loaded, %d x %d cells at %s m"\n'
    "\t\tprint(text % [v, shadows.area, shadows.columns, shadows.rows, _number(shadows.cell_m)])\n"
)
ROOFS_LINE = "\t\tprint(text % [v, roofs.area, coloured, count])\n"
CREDIT = (
    "\tif shadows != null:\n"
    "\t\tvar editions := shadows.editions\n"
    "\t\tvar edition := editions[0]\n"
    "\t\tif editions.size() > 1:\n"
    '\t\t\tedition = "%s-%s" % [editions[0], editions[editions.size() - 1]]\n'
    "\t\tlines[_dataset_line(shadows.dataset, edition, shadows.attribution)] = true\n"
)
PY_SHADOWS = (
    'shadows = manifest["shadows"]\n'
    'fields = (version, shadows["area"], shadows["columns"], shadows["rows"], '
    'number(shadows["cell_m"]))\n'
    'print("mattini %s: shadows %s loaded, %d x %d cells at %s m" % fields)\n'
)
SKY = (
    "\tvar read_sky := _caught(SkySite.from_manifest.bind(manifest_path, world))\n"
    "\t_site = read_sky[0]\n"
    "\tif _site == null:\n"
    "\t\trefusals.append([SKY_WHAT, read_sky[1], SKY_FIX])\n"
)
PY_ROOFS = (
    'print("mattini %s: roofs %s loaded, %d of %d buildings coloured" % fields)\n'
)

ROWS = {
    # main.gd: the hand-over
    1: [
        (
            MAIN,
            "TerrainLoader.create(grid, self, photo, surfaces, shadows)",
            "TerrainLoader.create(grid, self, photo, surfaces)",
        )
    ],
    # main.gd: the mask read only with a photo (one cause would hide the other)
    2: [
        (
            MAIN,
            READ,
            (
                "\tvar shadows: CaptureShadowGrid = null\n"
                "\tif photo != null:\n"
                "\t\tvar read_shadows := _caught("
                "CaptureShadowGrid.from_manifest.bind(manifest_path, world))\n"
                "\t\tshadows = read_shadows[0]\n"
                "\t\tif shadows == null:\n"
                "\t\t\trefusals.append([SHADOWS_WHAT, read_shadows[1], SHADOWS_FIX])\n"
            ),
        )
    ],
    # main.gd: the mask read before the roof colours (its panel entry before theirs)
    3: [(MAIN, READ, ""), (MAIN, ROOFS, READ + ROOFS)],
    # main.gd: the fix without the download
    4: [
        (
            MAIN,
            'const SHADOWS_FIX := [RUN + "download surface", RUN + "shadows"]',
            'const SHADOWS_FIX := [RUN + "shadows"]',
        )
    ],
    # main.gd: a refused manifest still names seven
    5: [(MAIN, "\t\t\tSHADOWS_WHAT,\n", "")],
    # main.gd: the mask named after the sky in a refused manifest
    6: [
        (
            MAIN,
            "\t\t\tSHADOWS_WHAT,\n\t\t\tSKY_WHAT\n",
            "\t\t\tSKY_WHAT,\n\t\t\tSHADOWS_WHAT\n",
        ),
    ],
    # main.gd: the startup line before the roofs'
    7: [
        (MAIN, LINE, ""),
        (
            MAIN,
            "\tif roofs != null:\n\t\tvar count := 0\n",
            LINE + "\tif roofs != null:\n\t\tvar count := 0\n",
        ),
    ],
    # main.gd: the startup line's columns and rows swapped
    8: [
        (
            MAIN,
            "shadows.area, shadows.columns, shadows.rows,",
            "shadows.area, shadows.rows, shadows.columns,",
        )
    ],
    # main.gd: the mask not credited
    9: [(MAIN, CREDIT, "")],
    # main.gd: the mask's editions written as a list
    10: [
        (
            MAIN,
            "lines[_dataset_line(shadows.dataset, edition, shadows.attribution)]",
            "lines[_dataset_line(shadows.dataset, editions, shadows.attribution)]",
        )
    ],
    # main.gd: one edition written as a range ("2022-2022")
    11: [
        (
            MAIN,
            "\t\tif editions.size() > 1:\n\t\t\tedition",
            "\t\tif editions.size() > 0:\n\t\t\tedition",
        )
    ],
    # render_photo.gd (the pinned file, restored at once): no override of the lift
    12: [
        (RENDER_PHOTO, '\tterrain.material.set_shader_param("shadow_lift", 1.0)\n', "")
    ],
    # export.sh: no shadows block required
    13: [(EXPORT, '\t"shadows|download surface|shadows"\n', "")],
    # export.sh: the count still 6 + the packs
    14: [
        (
            EXPORT,
            "-eq $((7 + ${#PACKS_WRITTEN[@]}))",
            "-eq $((6 + ${#PACKS_WRITTEN[@]}))",
        ),
    ],
    # export.sh: the shadows' line expected before the roofs'
    15: [(EXPORT, PY_SHADOWS, ""), (EXPORT, PY_ROOFS, PY_SHADOWS + PY_ROOFS)],
    # export.sh: the shadows' line not expected (and the count 6 + the packs, so step 6 agrees)
    16: [
        (EXPORT, PY_SHADOWS, ""),
        (
            EXPORT,
            "-eq $((7 + ${#PACKS_WRITTEN[@]}))",
            "-eq $((6 + ${#PACKS_WRITTEN[@]}))",
        ),
    ],
    # the release's checkers (2026-10-30)
    # main.gd: the mask read only when the terrain was read
    18: [
        (
            MAIN,
            READ,
            (
                "\tvar shadows: CaptureShadowGrid = null\n"
                "\tif grid != null:\n"
                "\t\tvar read_shadows := _caught("
                "CaptureShadowGrid.from_manifest.bind(manifest_path, world))\n"
                "\t\tshadows = read_shadows[0]\n"
                "\t\tif shadows == null:\n"
                "\t\t\trefusals.append([SHADOWS_WHAT, read_shadows[1], SHADOWS_FIX])\n"
            ),
        )
    ],
    # main.gd: the mask read after the sky (its panel entry after the sky's)
    19: [(MAIN, READ, ""), (MAIN, SKY, SKY + READ)],
    # export.sh: the shadows' line computed from the surfaces' block
    20: [(EXPORT, 'shadows = manifest["shadows"]\n', 'shadows = manifest["surfaces"]\n')],
    # main.gd: the credit's edition range from the first two editions
    21: [
        (
            MAIN,
            '"%s-%s" % [editions[0], editions[editions.size() - 1]]',
            '"%s-%s" % [editions[0], editions[1]]',
        )
    ],
}


def main() -> None:
    for path, old, new in ROWS[int(sys.argv[1])]:
        text = Path(path).read_text(encoding="utf-8")
        if text.count(old) != 1:
            sys.exit(f"{path}: {old!r} found {text.count(old)} times")
        Path(path).write_text(text.replace(old, new), encoding="utf-8")


if __name__ == "__main__":
    main()
