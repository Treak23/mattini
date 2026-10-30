#!/usr/bin/env bash
# docs/RELEASE.md §C's runtime checks of a release build, as a script (brief v0.5.0-06):
#
#   tools/release_checks.sh [<linux build folder>]      (default build/linux)
#
# One line per check, `release check: <name>: PASS|FAIL <what it found>`; every check runs
# whatever the one before found; the last line is `== release checks: all passed` or
# `== release checks: <n> failed`; exit 0 only when all five pass, else 1. Every start of the
# game is headless, with user:// in a scratch folder (XDG_DATA_HOME) and a timeout. In order:
#   1. stars         mattini.pck's directory holds sky/stars.csv with game/sky/stars.csv's size
#                    and MD5 (a build without it shows a starless night and no ESA credit);
#   2. frame cap     --headless --print-fps --quit-after 600 prints `Project FPS: 60`, exits 0,
#                    prints no ERROR / SCRIPT ERROR line, and prints one "mattini <version>:
#                    data pack <name> loaded" line per mattini-*.pck beside the executable and
#                    further "mattini <version>: " lines after them (check 5 expects those);
#   3. override.cfg  one written beside the executable (a marker version, MSAA off) makes the
#                    startup lines show the marker; it is removed after; one already there
#                    fails the check and is not touched;
#   4. missing pack  with mattini-photo.pck moved aside, DataPacks' ERROR line names it, "the
#                    aerial photo" and the build folder's real path, and PhotoGrid's ERROR line
#                    ends "download the release folder again"; the pack goes back, its SHA-256
#                    unchanged (FB-005);
#   5. live log      started with no --quit-after, its output and user://logs/godot.log hold
#                    every startup line of check 2 while the process is alive (within 120 s,
#                    or RELEASE_CHECKS_LIVE_TIMEOUT_S seconds); then it is stopped by its PID
#                    (FB-006).
# The build folder is left as it was found after a pass and after a failure (a trap puts the
# pack back and removes the override.cfg this script wrote).
set -uo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
export LC_ALL=C

FOLDER_ARG="${1:-build/linux}"
[ -d "$FOLDER_ARG" ] || { echo "release_checks: $FOLDER_ARG is not a folder" >&2; exit 1; }
FOLDER="$(cd "$FOLDER_ARG" && pwd -P)"
EXE="$FOLDER/mattini.x86_64"
PCK="$FOLDER/mattini.pck"
PHOTO_PACK="$FOLDER/mattini-photo.pck"
OVERRIDE="$FOLDER/override.cfg"
STARS="game/sky/stars.csv"
MARKER="0.0.0-override-check"
LIVE_TIMEOUT_S="${RELEASE_CHECKS_LIVE_TIMEOUT_S:-120}"
RUN_TIMEOUT_S=300

SCRATCH="$(mktemp -d)"
ASIDE=""
WROTE_OVERRIDE=0
GAME_PID=""
cleanup() {
	[ -n "$GAME_PID" ] && kill "$GAME_PID" 2> /dev/null
	[ -n "$ASIDE" ] && [ -f "$ASIDE" ] && [ ! -e "$PHOTO_PACK" ] && mv "$ASIDE" "$PHOTO_PACK"
	[ "$WROTE_OVERRIDE" -eq 1 ] && rm -f "$OVERRIDE"
	rm -rf "$SCRATCH"
}
trap cleanup EXIT

FAILED=0
verdict() {
	local name="$1" result="$2"
	shift 2
	echo "release check: $name: $result $*"
	[ "$result" = "PASS" ] || FAILED=$((FAILED + 1))
}

# The game's output, with ANSI colours and a CR at the end of a line removed.
clean() {
	sed -e 's/\x1b\[[0-9;]*[A-Za-z]//g' -e 's/\r$//' "$1"
}

# Runs the game headless with the arguments given, user:// in its own scratch folder; the
# cleaned output goes to $RUN_OUT, the status to $RUN_STATUS.
RUN_OUT=""
RUN_STATUS=0
run_game() {
	local home raw
	home="$(mktemp -d "$SCRATCH/xdg.XXXXXX")"
	raw="$(mktemp "$SCRATCH/raw.XXXXXX")"
	RUN_OUT="$raw.clean"
	XDG_DATA_HOME="$home" timeout "$RUN_TIMEOUT_S" "$EXE" --headless "$@" > "$raw" 2>&1
	RUN_STATUS=$?
	clean "$raw" > "$RUN_OUT"
}

has_exe() {
	[ -x "$EXE" ]
}

# 1. stars -----------------------------------------------------------------------------------
check_stars() {
	local reason status=0
	# The reader's own words are the line; uv's stderr is not captured into it.
	reason="$(uv run --project pipeline --frozen python -c '
import hashlib
import os
import struct
import sys

pack, stars = sys.argv[1:3]
want = (os.path.getsize(stars), hashlib.md5(open(stars, "rb").read()).hexdigest())


def fail(why):
    print("sky/stars.csv in %s: %s" % (os.path.basename(pack), why))
    sys.exit(1)


# Godot 4.6.3 pack format 3: magic GDPC, format, version, flags (2 = relative file base), the
# file base and the directory offset as u64; the directory: a u32 count, then per file a u32
# path length (padded to 4), the path, a u64 offset, a u64 size, a 16-byte MD5 and u32 flags.
try:
    size = os.path.getsize(pack)
    with open(pack, "rb") as file:
        head = file.read(104)
        if len(head) < 104:
            fail("not a pack (shorter than its header)")
        magic, fmt, major, minor, patch, flags = struct.unpack_from("<6I", head)
        if magic != 0x43504447 or fmt != 3 or (major, minor, patch) != (4, 6, 3) or flags != 2:
            fail("not format 3 of Godot 4.6.3 with a relative file base")
        base, directory = struct.unpack_from("<QQ", head, 24)
        file.seek(directory)
        (count,) = struct.unpack("<I", file.read(4))
        found = {}
        for _ in range(count):
            (length,) = struct.unpack("<I", file.read(4))
            raw = file.read(length).rstrip(b"\0").decode("utf-8")
            offset, length_of_file = struct.unpack("<QQ", file.read(16))
            md5 = file.read(16).hex()
            file.read(4)
            if base + offset + length_of_file > size:
                fail("%s ends beyond the end of the pack" % raw)
            found[raw.removeprefix("res://")] = (length_of_file, md5)
except (OSError, ValueError, struct.error) as error:
    fail("the pack cannot be read (%s)" % error)
if "sky/stars.csv" not in found:
    fail("the pack holds no sky/stars.csv: a starless night and no ESA credit")
if found["sky/stars.csv"] != want:
    fail("holds %d bytes, MD5 %s; game/sky/stars.csv has %d bytes, MD5 %s" % (*found["sky/stars.csv"], *want))
print("sky/stars.csv in %s: %d bytes, MD5 %s, as game/sky/stars.csv" % (os.path.basename(pack), *want))
' "$PCK" "$STARS")" || status=$?
	if [ "$status" -eq 0 ]; then verdict stars PASS "$reason"; else verdict stars FAIL "${reason:-sky/stars.csv in mattini.pck: the reader did not run (exit $status)}"; fi
}

# 2. frame cap -------------------------------------------------------------------------------
STARTUP_LINES=()
check_frame_cap() {
	has_exe || { verdict "frame cap" FAIL "$EXE is missing or not executable (mattini.x86_64)"; return; }
	run_game --print-fps --quit-after 600
	local problems="" fps packs found version last_pack n errors line
	fps="$(grep -a -E -m 1 '^Project FPS: 60( |$)' "$RUN_OUT")"
	[ -n "$fps" ] || problems+="; no 'Project FPS: 60' line"
	[ "$RUN_STATUS" -eq 0 ] || problems+="; exit status $RUN_STATUS"
	errors="$(grep -a -c -E '^(ERROR|SCRIPT ERROR)' "$RUN_OUT")"
	[ "$errors" -eq 0 ] || problems+="; $errors ERROR line(s), the first: $(grep -a -m 1 -E '^(ERROR|SCRIPT ERROR)' "$RUN_OUT")"
	packs="$(cd "$FOLDER" && ls -1 | grep -E '^mattini-.*\.pck$' | tr '\n' ' ')"
	found="$(sed -n -E 's/^mattini [^ :]+: data pack (\S+) loaded$/\1/p' "$RUN_OUT" | tr '\n' ' ')"
	[ "$found" = "$packs" ] || problems+="; the data pack lines name [${found% }], the packs beside the executable are [${packs% }]"
	STARTUP_LINES=()
	while IFS= read -r line; do STARTUP_LINES+=("$line"); done < <(grep -a -E '^mattini [^ :]+: ' "$RUN_OUT")
	version="$(printf '%s\n' "${STARTUP_LINES[0]:-}" | sed -n -E 's/^mattini ([^ :]+): .*/\1/p')"
	last_pack="$(grep -a -n -E '^mattini [^ :]+: data pack \S+ loaded$' "$RUN_OUT" | tail -n 1 | cut -d: -f1)"
	n=0
	if [ -n "$last_pack" ]; then
		n="$(tail -n +"$((last_pack + 1))" "$RUN_OUT" | grep -a -c -E '^mattini [^ :]+: ')"
	fi
	[ "$n" -ge 1 ] || problems+="; no startup line after the data pack lines"
	if [ -z "$problems" ]; then
		verdict "frame cap" PASS "$fps; exit 0, no ERROR line, ${#STARTUP_LINES[@]} 'mattini $version:' lines ($n after the data pack lines)"
	else
		verdict "frame cap" FAIL "${problems#; }"
	fi
}

# 3. override.cfg ----------------------------------------------------------------------------
check_override() {
	has_exe || { verdict override.cfg FAIL "$EXE is missing or not executable (mattini.x86_64)"; return; }
	if [ -e "$OVERRIDE" ]; then
		verdict override.cfg FAIL "an override.cfg is already beside the executable; it is not touched, remove it and run again"
		return
	fi
	printf '[application]\nconfig/version="%s"\n\n[rendering]\nanti_aliasing/quality/msaa_3d=0\n' "$MARKER" > "$OVERRIDE"
	WROTE_OVERRIDE=1
	run_game --quit-after 300
	rm -f "$OVERRIDE"
	WROTE_OVERRIDE=0
	local shown
	shown="$(grep -a -c -E "^mattini $MARKER: " "$RUN_OUT")"
	if [ "$shown" -ge 1 ]; then
		verdict override.cfg PASS "the startup lines show the marker $MARKER ($shown lines); the file is removed"
	else
		verdict override.cfg FAIL "no startup line shows the marker $MARKER: the override.cfg was not read"
	fi
}

# 4. missing pack ----------------------------------------------------------------------------
check_missing_pack() {
	has_exe || { verdict "missing pack" FAIL "$EXE is missing or not executable (mattini.x86_64)"; return; }
	[ -f "$PHOTO_PACK" ] || { verdict "missing pack" FAIL "mattini-photo.pck is not beside the executable to move aside"; return; }
	local before after data_line photo_line problems=""
	before="$(sha256sum "$PHOTO_PACK" | cut -d' ' -f1)"
	ASIDE="$SCRATCH/mattini-photo.pck.aside"
	mv "$PHOTO_PACK" "$ASIDE"
	run_game --quit-after 300
	mv "$ASIDE" "$PHOTO_PACK"
	after="$(sha256sum "$PHOTO_PACK" | cut -d' ' -f1)"
	[ "$before" = "$after" ] || problems+="; the pack's SHA-256 changed ($before, then $after)"
	data_line="$(grep -a -F -x -m 1 "ERROR: DataPacks: the data pack mattini-photo.pck (the aerial photo) is missing from $FOLDER: download the release folder again" "$RUN_OUT")"
	[ -n "$data_line" ] || problems+="; no DataPacks line naming mattini-photo.pck, 'the aerial photo' and $FOLDER"
	photo_line="$(grep -a -m 1 -E '^ERROR: PhotoGrid: .*download the release folder again$' "$RUN_OUT")"
	[ -n "$photo_line" ] || problems+="; no PhotoGrid line ending 'download the release folder again'"
	if [ -z "$problems" ]; then
		verdict "missing pack" PASS "both lines found, the pack is back with SHA-256 $after"
		echo "$data_line"
		echo "$photo_line"
	else
		verdict "missing pack" FAIL "${problems#; }"
	fi
}

# 5. live log --------------------------------------------------------------------------------
all_lines_in() {
	local file="$1" line
	[ -f "$file" ] || return 1
	for line in "${STARTUP_LINES[@]}"; do
		clean "$file" | grep -a -F -x -q -- "$line" || return 1
	done
}

check_live_log() {
	has_exe || { verdict "live log" FAIL "$EXE is missing or not executable (mattini.x86_64)"; return; }
	if [ "${#STARTUP_LINES[@]}" -eq 0 ]; then
		verdict "live log" FAIL "check 2 found no startup lines to expect in the log"
		return
	fi
	local home out log waited=0 start alive=1 both=0
	home="$(mktemp -d "$SCRATCH/xdg.XXXXXX")"
	out="$SCRATCH/live.out"
	log="$home/godot/app_userdata/mattini/logs/godot.log"
	: > "$out"
	XDG_DATA_HOME="$home" "$EXE" --headless > "$out" 2>&1 &
	GAME_PID=$!
	start=$SECONDS
	while [ $((SECONDS - start)) -lt "$LIVE_TIMEOUT_S" ]; do
		if ! kill -0 "$GAME_PID" 2> /dev/null; then alive=0; fi
		if all_lines_in "$out" && all_lines_in "$log"; then
			both=1
			break
		fi
		[ "$alive" -eq 1 ] || break
		sleep 0.5
	done
	waited=$((SECONDS - start))
	kill -0 "$GAME_PID" 2> /dev/null || alive=0
	if [ "$alive" -eq 1 ]; then
		kill "$GAME_PID" 2> /dev/null
		wait "$GAME_PID" 2> /dev/null
	else
		wait "$GAME_PID" 2> /dev/null
	fi
	GAME_PID=""
	if [ "$both" -eq 1 ] && [ "$alive" -eq 1 ]; then
		verdict "live log" PASS "the output and godot.log held all ${#STARTUP_LINES[@]} startup lines while the process ran (${waited} s); stopped by its PID"
	elif [ "$alive" -eq 0 ]; then
		verdict "live log" FAIL "the process exited by itself before the log held the startup lines (no --quit-after was given)"
	else
		verdict "live log" FAIL "after ${waited} s godot.log or the output still lacked startup lines while the process ran"
	fi
}

check_stars
check_frame_cap
check_override
check_missing_pack
check_live_log

if [ "$FAILED" -eq 0 ]; then
	echo "== release checks: all passed"
	exit 0
fi
echo "== release checks: $FAILED failed"
exit 1
