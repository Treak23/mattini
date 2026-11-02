"""The pin author's mutation rows for brief v0.6.0-03 (run from the clone's root on the throwaway).

python3 -I docs/briefs/sketches/v0.6.0/v0.6.0-03-mutate.py N   applies row N (one exact text
replacement, refused unless the old text occurs exactly once); restore with `git checkout -- <file>`.
"""

import pathlib
import sys

WF = ".github/workflows/release.yml"
ROWS = {
    1: ("tools/pins.sh", 'PYTHON_VERSION="3.13.14"', 'PYTHON_VERSION="3.13.17"'),
    2: (
        WF,
        '          uv python install "$PYTHON_VERSION"\n',
        "",
    ),
    3: (WF, '          echo "UV_PYTHON=$PYTHON_VERSION" >> "$GITHUB_ENV"\n', ""),
    4: (WF, '          if [ "$found" != "$PYTHON_VERSION" ]; then', "          if false; then"),
    5: (
        WF,
        "          uv run --project pipeline --frozen python -c 'import zlib; "
        "print(\"zlib\", zlib.ZLIB_RUNTIME_VERSION)'\n",
        "",
    ),
    6: (WF, "      UV_PYTHON_PREFERENCE: only-managed\n", ""),
    7: (WF, 'uv python install "$PYTHON_VERSION"', "uv python install 3.13.14"),
    8: (
        WF,
        '          if ! git merge-base --is-ancestor "$RELEASE_SHA" refs/remotes/origin/main; then',
        '          if ! git merge-base --is-ancestor "$RELEASE_SHA" refs/remotes/origin/main && false; then',
    ),
    9: (
        WF,
        'git fetch --no-tags origin "+refs/heads/main:refs/remotes/origin/main"',
        'git fetch --no-tags origin "+refs/heads/*:refs/remotes/origin/*"',
    ),
    10: (
        WF,
        'git merge-base --is-ancestor "$RELEASE_SHA" refs/remotes/origin/main',
        'git merge-base --is-ancestor "$RELEASE_SHA" HEAD',
    ),
    11: (WF, '          echo "$RELEASE_SHA is not on main (main is $main): a Release is built from main only"\n', '          echo "not on main"\n'),
    12: ("tools/release_checks.sh", "		if all_lines_in \"$out\" && all_lines_in \"$log\"; then\n			verdict \"live log\" FAIL \"the process exited by itself after", "		if false; then\n			verdict \"live log\" FAIL \"the process exited by itself after"),
    13: ("tools/release_checks.sh", 'if [ "$both" -eq 1 ] && [ "$alive" -eq 1 ]; then', 'if [ "$both" -eq 1 ]; then'),
    14: ("docs/RELEASE.md", 'else echo "the size check failed: $size bytes, the plan names 326124"; false; fi', 'else echo "the size check failed: $size bytes, the plan names 326124"; fi'),
    15: ("docs/RELEASE.md", 'echo "manifest.json: $size bytes"; ', ""),
    16: (".claude/hooks/session-start.sh", "UV_BIN=", 'export UV_PYTHON="$PYTHON_VERSION"\nUV_BIN='),
    17: ("pipeline/.python-version", "3.13\n", "3.13.14\n"),
}

row = int(sys.argv[1])
path, old, new = ROWS[row]
file = pathlib.Path(path)
text = file.read_text(encoding="utf-8")
assert text.count(old) == 1, (row, path, text.count(old))
file.write_text(text.replace(old, new), encoding="utf-8")
print(f"row {row}: {path}")
