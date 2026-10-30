"""tools/release_pack.sh and tools/release_checks.sh run on a stand-in build (brief v0.5.0-06).

The scripts under test are the repository's own, copied unchanged into a scratch tree laid out
like the repository (`release_tree`): the two scripts, tools/release_notes.md,
game/project.godot and game/sky/stars.csv, and a stand-in uv (fake_tools.FAKE_UV: `uv run ...
python -c` runs this Python). `build/linux/` and `build/windows/` hold the five files of each
platform: small stand-in bytes for the libraries, the data packs and the Windows executable,
`mattini.pck` in Godot 4.6.3's pack format 3 (fake_tools.write_pck) holding `sky/stars.csv`
with the stars table's bytes, and for Linux a bash stand-in for the exported game
(`FAKE_GAME`) that behaves as the 0.4.0 release gate measured the real one (docs/releases/
v0.4.0.md §Checked at this release; brain.md H15):
- it prints one "mattini <version>: data pack <name> loaded" line per mattini-*.pck beside it,
  in name order, then three startup lines ("terrain", "buildings", "roofs"), with
  game/project.godot's version, or the version an override.cfg beside it sets
  (`[application]` `config/version="..."`);
- with mattini-photo.pck missing, DataPacks' ERROR line naming it, "the aerial photo" and its
  own folder (its real path), Godot's "   at:" line, and PhotoGrid's ERROR line ending
  "download the release folder again";
- `--print-fps` adds "Project FPS: 60 (16.67 mspf)";
- every line goes to stdout and to $XDG_DATA_HOME/godot/app_userdata/mattini/logs/godot.log as
  it is printed; with `--quit-after` it exits 0, without it it waits until it is killed.
Knobs, set in the environment by a test: FAKE_FPS (another frame cap), FAKE_NO_OVERRIDE=1 (an
override.cfg is not read), FAKE_NO_PACK_ERROR=1 (no DataPacks line), FAKE_PACK_FOLDER=<path> (the
DataPacks line names that folder instead of its own), FAKE_NO_PHOTO_LINE=1 (no
PhotoGrid line), FAKE_LOG_AT_EXIT=1 (godot.log is written only when it is killed or quits),
FAKE_ERROR=<line> (one more line, printed after the startup lines), FAKE_EXIT=<status>.
The scripts run with RELEASE_CHECKS_LIVE_TIMEOUT_S=20: check 5 waits 20 s, not 120 s, for a
log that never fills.

Does NOT prove: that the real exported game prints exactly these lines (measured by hand at
the 0.3.1 and 0.4.0 release gates; the workflow's first live run is the next measurement);
anything on Windows.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from fake_tools import BASH, FAKE_UV, REPO, VERSION, write_pck

LINUX_FILES = [
    "libterrain.linux.release.x86_64.so",
    "mattini-photo.pck",
    "mattini-terrain.pck",
    "mattini.pck",
    "mattini.x86_64",
]
WINDOWS_FILES = [
    "libterrain.windows.release.x86_64.dll",
    "mattini-photo.pck",
    "mattini-terrain.pck",
    "mattini.exe",
    "mattini.pck",
]
STARS = REPO / "game" / "sky" / "stars.csv"
EPOCH = 1761782400  # 2025-10-30 00:00:00 UTC, even (a zip keeps two-second times)

FAKE_GAME = r"""#!/usr/bin/env bash
# A stand-in for the exported Linux game (pipeline/tests/fake_release.py).
here="$(cd "$(dirname "$0")" && pwd -P)"
version="$FAKE_VERSION"
if [ -f "$here/override.cfg" ] && [ -z "${FAKE_NO_OVERRIDE:-}" ]; then
	set_version="$(sed -n 's/^config\/version="\(.*\)"$/\1/p' "$here/override.cfg")"
	[ -n "$set_version" ] && version="$set_version"
fi
log="${XDG_DATA_HOME:-$HOME/.local/share}/godot/app_userdata/mattini/logs/godot.log"
mkdir -p "$(dirname "$log")"
: > "$log"
lines=()
say() {
	echo "$1"
	if [ -n "${FAKE_LOG_AT_EXIT:-}" ]; then
		lines+=("$1")
	else
		echo "$1" >> "$log"
	fi
}
flush() {
	[ "${#lines[@]}" -gt 0 ] && printf '%s\n' "${lines[@]}" >> "$log"
	lines=()
}
trap 'flush; exit 143' TERM
say "Godot Engine v4.6.3.stable.official.7d41c59c4 - https://godotengine.org"
quit=""
for arg in "$@"; do
	case "$arg" in
		--print-fps) say "Project FPS: ${FAKE_FPS:-60} (16.67 mspf)" ;;
		--quit-after) quit=1 ;;
	esac
done
for pack in $(cd "$here" && LC_ALL=C ls -1 | grep -E '^mattini-.*\.pck$'); do
	say "mattini $version: data pack $pack loaded"
done
if [ ! -f "$here/mattini-photo.pck" ]; then
	if [ -z "${FAKE_NO_PACK_ERROR:-}" ]; then
		say "ERROR: DataPacks: the data pack mattini-photo.pck (the aerial photo) is missing from ${FAKE_PACK_FOLDER:-$here}: download the release folder again"
		say "   at: push_error (core/variant/variant_utility.cpp:1098)"
	fi
	if [ -z "${FAKE_NO_PHOTO_LINE:-}" ]; then
		say "ERROR: PhotoGrid: res://assets/generated/manifest.json: the photo res://assets/generated/photo/village.jpg is missing; it ships in the release's packs: download the release folder again"
	fi
fi
say "mattini $version: terrain village loaded, 4001 x 6001 vertices at 0.5 m"
say "mattini $version: buildings village loaded, 1486 buildings in 6 chunks, 512345 triangles"
say "mattini $version: roofs village loaded, 1480 of 1486 buildings coloured"
[ -n "${FAKE_ERROR:-}" ] && say "$FAKE_ERROR"
if [ -n "$quit" ]; then
	flush
	exit "${FAKE_EXIT:-0}"
fi
while true; do
	sleep 0.2
done
"""


def _executable(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    path.chmod(0o755)


def release_tree(tmp_path: Path) -> Path:
    """A scratch tree laid out like the repository, with the stand-in build in build/."""
    root = tmp_path / "repo"
    (root / "tools").mkdir(parents=True)
    for name in ("release_pack.sh", "release_checks.sh"):
        source = REPO / "tools" / name
        if source.exists():
            shutil.copy2(source, root / "tools" / name)
    notes = REPO / "tools" / "release_notes.md"
    if notes.exists():
        shutil.copy2(notes, root / "tools" / "release_notes.md")
    (root / "game" / "sky").mkdir(parents=True)
    shutil.copy2(REPO / "game" / "project.godot", root / "game" / "project.godot")
    shutil.copy2(STARS, root / "game" / "sky" / "stars.csv")
    pck = [("sky/stars.csv", STARS.read_bytes()), ("scripts/main.gdc", b"a stand-in script")]
    for platform, files in (("linux", LINUX_FILES), ("windows", WINDOWS_FILES)):
        folder = root / "build" / platform
        folder.mkdir(parents=True)
        for name in files:
            path = folder / name
            if name == "mattini.pck":
                write_pck(path, pck)
            elif name == "mattini.x86_64":
                _executable(path, FAKE_GAME)
            else:
                path.write_bytes(f"a stand-in for {platform}/{name}\n".encode() * 64)
    return root


def _env(tmp_path: Path, **extra) -> dict:
    bin_dir = tmp_path / "bin"
    if not bin_dir.exists():
        bin_dir.mkdir()
        _executable(bin_dir / "uv", FAKE_UV)
    env = dict(os.environ)
    env.update(
        PATH=f"{bin_dir}{os.pathsep}{env.get('PATH', '')}",
        FAKE_CALLS=str(tmp_path / "calls.txt"),
        FAKE_PYTHON=sys.executable,
        FAKE_VERSION=VERSION,
        XDG_DATA_HOME=str(tmp_path / "xdg"),
        RELEASE_CHECKS_LIVE_TIMEOUT_S="20",
        LC_ALL="C",
    )
    env.pop("SOURCE_DATE_EPOCH", None)
    env.update({key: str(value) for key, value in extra.items()})
    return env


def run_pack(tmp_path: Path, root: Path, *args: str, timeout: int = 120, **extra):
    """tools/release_pack.sh in `root` with `args`; SOURCE_DATE_EPOCH is EPOCH unless given."""
    extra.setdefault("SOURCE_DATE_EPOCH", EPOCH)
    return subprocess.run(
        [BASH, "-c", 'tools/release_pack.sh "$@"', "release_pack.sh", *args],
        cwd=root,
        env=_env(tmp_path, **extra),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def run_checks(tmp_path: Path, root: Path, *args: str, timeout: int = 240, **extra):
    """tools/release_checks.sh in `root` with `args`, stdout and stderr together."""
    return subprocess.run(
        [BASH, "-c", 'tools/release_checks.sh "$@"', "release_checks.sh", *args],
        cwd=root,
        env=_env(tmp_path, **extra),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
        check=False,
    )
