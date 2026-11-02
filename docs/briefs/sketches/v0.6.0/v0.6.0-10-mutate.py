"""The pin author's mutation rows for brief v0.6.0-10 (run from the clone's root on the throwaway).

python3 -I docs/briefs/sketches/v0.6.0/v0.6.0-10-mutate.py N   applies row N (each replacement
refused unless its old text occurs exactly once; row 4 has two); restore with
`git checkout -- <file>`.
"""

import pathlib
import sys

EX = "tools/export.sh"
WF = ".github/workflows/release.yml"
MD = "docs/RELEASE.md"
ENTRY = '\t"surroundings|download regio|download farphoto|surroundings|farcolour"\n'
SHADOWS = 'print("mattini %s: shadows %s loaded, %d x %d cells at %s m" % fields)\n'
FAR_PRINT = (
    'print("mattini %s: surroundings %s loaded, %d x %d vertices at %s m, colour %d x %d at %s m"'
    " % (fields + colour))\n"
)
ROWS = {
    1: [(EX, ENTRY, "")],
    2: [(EX, ENTRY, '\t"surroundings|download regio|download farphoto|surroundings"\n')],
    3: [(EX, ENTRY, ENTRY.replace("download regio|download farphoto", "download farphoto|download regio"))],
    4: [
        (EX, '[ "${#EXPECTED[@]}" -eq $((8 + ', '[ "${#EXPECTED[@]}" -eq $((7 + '),
        (EX, 'fail "expected $((8 + ', 'fail "expected $((7 + '),
    ],
    5: [(EX, 'far["columns"], far["rows"], number(far["spacing_m"])', 'far["rows"], far["columns"], number(far["spacing_m"])')],
    6: [(EX, 'colour = (far["colour_columns"], far["colour_rows"],', 'colour = (far["columns"], far["rows"],')],
    7: [(EX, 'number(far["colour_cell_m"]))', 'number(far["spacing_m"]))')],
    8: [(EX, FAR_PRINT, 'print("mattini %s: surroundings %s loaded, %d x %d heights at %s m" % fields)\n')],
    9: [
        (EX, SHADOWS, ""),
        (EX, FAR_PRINT, FAR_PRINT + 'fields = (version, shadows["area"], shadows["columns"], shadows["rows"], number(shadows["cell_m"]))\n' + SHADOWS),
    ],
    10: [(EX, 'number(far["spacing_m"]))\ncolour', 'far["spacing_m"])\ncolour')],
    11: [(WF, "          uv run --project pipeline --frozen python -m mattini download farphoto\n", "")],
    12: [
        (
            WF,
            "      - name: pipeline, farcolour\n        run: uv run --project pipeline --frozen python -m mattini farcolour\n",
            "",
        ),
        (
            WF,
            "      - name: pipeline, sky\n",
            "      - name: pipeline, farcolour\n        run: uv run --project pipeline --frozen python -m mattini farcolour\n      - name: pipeline, sky\n",
        ),
    ],
    13: [
        (
            WF,
            "      - name: pipeline, surroundings\n        run: uv run --project pipeline --frozen python -m mattini surroundings\n",
            "",
        )
    ],
    14: [(MD, "`surroundings`,\n      `farcolour`, `shadows`", "`surroundings`,\n      `shadows`")],
    15: [(MD, "requires ten startup lines", "requires nine startup lines")],
    16: [(MD, "`c851d12d…`, `44de978f…`, the photo's", "`c851d12d…`, the photo's")],
    17: [(EX, "PACKED_FOLDERS=(photo terrain)", "PACKED_FOLDERS=(photo surroundings terrain)")],
}

for path, old, new in ROWS[int(sys.argv[1])]:
    file = pathlib.Path(path)
    text = file.read_text(encoding="utf-8")
    if text.count(old) != 1:
        sys.exit(f"row {sys.argv[1]}: {old!r} occurs {text.count(old)} times in {path}")
    file.write_text(text.replace(old, new), encoding="utf-8")
print(f"row {sys.argv[1]} applied")
