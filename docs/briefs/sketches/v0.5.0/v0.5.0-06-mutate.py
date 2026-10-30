"""The release's checkers' mutation rows of brief v0.5.0-06 (rows 17 to 25), on the throwaway.

python3 -I docs/briefs/sketches/v0.5.0/v0.5.0-06-mutate.py N   applies row N (from the repository's root).
"""
import sys
from pathlib import Path

WF = ".github/workflows/release.yml"
RC = "tools/release_checks.sh"
SUM = '          echo "$MANIFEST_SHA256  game/assets/generated/manifest.json" | sha256sum -c -\n'
SIZE = '          test "$(wc -c < game/assets/generated/manifest.json)" -eq "$MANIFEST_BYTES"\n'
ROWS = {
    17: [(WF, "      - name: the manifest pair\n", "      - name: the manifest pair\n        continue-on-error: true\n")],
    18: [(WF, SUM, SUM.replace("sha256sum -c -", "sha256sum -c - || true"))],
    19: [(WF, '| sha256sum -c -\n          mkdir -p "$RUNNER_TEMP/godot"', '| sha256sum\n          mkdir -p "$RUNNER_TEMP/godot"')],
    20: [(WF, SIZE, SIZE.rstrip("\n") + ' || echo "the manifest\'s size differs"\n')],
    21: [(WF, SIZE, "          set +e\n" + SIZE)],
    22: [(WF, '      - name: the checkout is the sha\n        run: test "$(git rev-parse HEAD)" = "$RELEASE_SHA"\n', "")],
    23: [(WF, '          grep -F ", as written here" export.log\n', "")],
    24: [(WF, "uv run --project pipeline --frozen python -m mattini shadows", "uv run --project pipeline python -m mattini shadows")],
    25: [(RC, """' "$BUILD/mattini.pck" "$STARS")" && pass stars""", """' "$BUILD/mattini.pck" "$STARS" 2>&1)" && pass stars""")],
}
for path, old, new in ROWS[int(sys.argv[1])]:
    text = Path(path).read_text(encoding="utf-8")
    if text.count(old) != 1:
        sys.exit(f"{path}: {old!r} found {text.count(old)} times")
    Path(path).write_text(text.replace(old, new), encoding="utf-8")
