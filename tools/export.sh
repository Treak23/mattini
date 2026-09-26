#!/usr/bin/env bash
# Exports a release of the current tree (docs/SPEC.md §11; docs/RELEASE.md §C; brief M1-06):
# Linux and Windows x86_64, each with its .pck beside the executable, into build/
# (git-ignored). Run from anywhere; it works in the repository it lives in:
#
#   tools/export.sh
#
# In order, stopping with a non-zero exit and a message at the first failure:
#   1. rewrites the generated manifest, which re-checks the generated data against the
#      config (and writes a block null when its generated data is gone);
#   2. refuses unless the manifest step 1 has just written has a terrain block and a
#      buildings block (the build ships them), naming the commands that build the missing
#      one. Nothing is exported before this check (M2 R1 G-03: it used to run before the
#      rewrite, so a block the rewrite dropped was found only after both exports);
#   3. installs Godot 4.6.3-stable's export templates for these two presets into Godot's
#      templates folder when they are missing, from Godot's download mirror (github.com
#      release downloads are refused in cloud containers, brain.md H6), verified against
#      the SHA-256 pinned below; a Godot other than 4.6.3 is refused, as its templates
#      would not be these;
#   4. exports both presets of game/export_presets.cfg, each into a fresh folder, and
#      fails naming any ERROR or SCRIPT ERROR line in Godot's output (Godot has exited 0
#      on errors, brain.md H1, H2), or a file the export did not write;
#   5. lists every file in build/ with its size, and fails naming any file over 100 MiB
#      (104'857'600 bytes, GitHub's file limit: docs/RELEASE.md §C);
#   6. starts the Linux build headless for 300 frames (build/linux/mattini.x86_64
#      --headless --quit-after 300, with user:// in a scratch folder, so the owner's is not
#      touched), and requires its two startup lines
#      "mattini <version>: terrain <area> loaded, <columns> x <rows> vertices at <spacing> m"
#      and "mattini <version>: buildings <area> loaded, <n> buildings in <k> chunks, <t>
#      triangles" with game/project.godot's version and the manifest's values (brief M2-05),
#      exit 0 and no ERROR line (M1 review G-02: an export without its terrain passed every
#      step before this one). A manifest without one of the blocks is refused there too,
#      with step 2's message.
#      It needs Linux, and fails on another system. Nothing here starts the Windows build
#      (the owner's PC is its test).
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
ROOT="$PWD"

GODOT="${GODOT:-godot}"
GODOT_VERSION="4.6.3.stable"
# The whole template set as the mirror served it on 2026-09-25: 1'255'918'323 bytes; its
# SHA-512 equals the one Godot publishes for Godot_v4.6.3-stable_export_templates.tpz
# (github.com/godotengine/godot-builds, releases/godot-4.6.3-stable.json).
TEMPLATES_URL="https://downloads.godotengine.org/?version=4.6.3&flavor=stable&slug=export_templates.tpz&platform=templates"
TEMPLATES_SHA256="3fbe2c0e2dec9d537ab9ec97bcf8da91dcf23357fc51f67092dd068d839290a8"
# The templates the two presets use, release and debug; the other platforms' are not
# installed.
TEMPLATES=(
	version.txt
	linux_debug.x86_64
	linux_release.x86_64
	windows_debug_x86_64.exe
	windows_debug_x86_64_console.exe
	windows_release_x86_64.exe
	windows_release_x86_64_console.exe
)
MANIFEST="game/assets/generated/manifest.json"
UV_RUN=(uv run --project pipeline --frozen)
# Preset name and export path, as in game/export_presets.cfg.
PRESETS=(
	"Linux|build/linux/mattini.x86_64"
	"Windows Desktop|build/windows/mattini.exe"
)
LIMIT_BYTES=104857600
# Step 6: the build is killed if it has not quit after this many seconds (it took 6.3 s in
# the M1 review, 5.3 s in brief M2-02's run).
START_TIMEOUT_S=300

SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT

fail() {
	echo "export: $1" >&2
	exit 1
}

step() {
	echo "== export: $1"
}

# Copies the output file $1 to $2 with ANSI colours removed, and prints it.
clean_output() {
	sed 's/\x1b\[[0-9;]*[A-Za-z]//g' "$1" > "$2"
	cat "$2"
}

# The lines of the cleaned output $1 that Godot writes for an error; grep -a, so a NUL byte
# in the output cannot turn the scan into "binary file matches" (M0 review G-07).
error_lines() {
	grep -a -E '^(ERROR|SCRIPT ERROR)' "$1" || true
}

# What steps 2 and 6 say when the manifest lacks a block, naming the commands that build
# it.
NO_TERRAIN="$MANIFEST has no terrain block: run uv run --project pipeline python -m mattini download terrain, then uv run --project pipeline python -m mattini terrain"
NO_BUILDINGS="$MANIFEST has no buildings block: run uv run --project pipeline python -m mattini download buildings, then uv run --project pipeline python -m mattini buildings"

# The two startup lines game/scripts/main.gd prints, one per line: once the terrain is
# loaded, the version from game/project.godot, the area, columns, rows and spacing from the
# manifest's terrain block, the spacing written as main.gd writes it (at most two decimals,
# no trailing zeros); once the buildings are loaded, the version, the area, the count of
# buildings, of chunks and of triangles from the manifest's buildings block. A missing
# block is refused with step 2's message, not a traceback.
expected_startup_lines() {
	"${UV_RUN[@]}" python -c '
import json, sys

manifest = json.load(open(sys.argv[1], encoding="utf-8"))
terrain, buildings = manifest.get("terrain"), manifest.get("buildings")
if not isinstance(terrain, dict):
    sys.exit(sys.argv[3])
if not isinstance(buildings, dict):
    sys.exit(sys.argv[4])
section, version = "", None
for line in open(sys.argv[2], encoding="utf-8"):
    line = line.strip()
    if line.startswith("["):
        section = line
    elif section == "[application]" and line.startswith("config/version="):
        version = json.loads(line.split("=", 1)[1])
if not isinstance(version, str) or not version:
    sys.exit(sys.argv[2] + " has no application/config/version")
spacing = ("%.2f" % terrain["spacing_m"]).rstrip("0").rstrip(".")
fields = (version, terrain["area"], terrain["columns"], terrain["rows"], spacing)
print("mattini %s: terrain %s loaded, %d x %d vertices at %s m" % fields)
chunks = buildings["chunks"]
count = sum(chunk["buildings"] for chunk in chunks)
triangles = sum(chunk["triangles"] for chunk in chunks)
fields = (version, buildings["area"], count, len(chunks), triangles)
print("mattini %s: buildings %s loaded, %d buildings in %d chunks, %d triangles" % fields)
' "$MANIFEST" game/project.godot "$NO_TERRAIN" "$NO_BUILDINGS"
}

# Godot's templates folder for this version (Linux, or Windows under Git Bash).
templates_dir() {
	case "$(uname -s)" in
		MINGW* | MSYS* | CYGWIN*) echo "${APPDATA:?}/Godot/export_templates/$GODOT_VERSION" ;;
		*) echo "${XDG_DATA_HOME:-$HOME/.local/share}/godot/export_templates/$GODOT_VERSION" ;;
	esac
}

# Exits 0 when the manifest's block named $1 is an object (not null, not missing), else 1.
has_block() {
	"${UV_RUN[@]}" python -c 'import json, sys; sys.exit(0 if isinstance(json.load(open(sys.argv[1], encoding="utf-8")).get(sys.argv[2]), dict) else 1)' "$MANIFEST" "$1"
}

step "1. the manifest, rewritten and re-checked against the config"
"${UV_RUN[@]}" python -m mattini manifest || fail "python -m mattini manifest refused the generated data (see above)"

step "2. the manifest step 1 wrote has a terrain block and a buildings block"
[ -f "$MANIFEST" ] || fail "$MANIFEST is missing after step 1 wrote it"
has_block terrain || fail "$NO_TERRAIN"
has_block buildings || fail "$NO_BUILDINGS"
echo "both blocks are there"

step "3. Godot $GODOT_VERSION's export templates"
found="$("$GODOT" --version 2>&1)" || fail "$GODOT --version failed: $found"
case "$found" in
	"$GODOT_VERSION"*) ;;
	*) fail "Godot $GODOT_VERSION is needed for these templates; $GODOT is: $found" ;;
esac
DIR="$(templates_dir)"
missing=()
for name in "${TEMPLATES[@]}"; do
	[ -s "$DIR/$name" ] || missing+=("$name")
done
if [ "${#missing[@]}" -eq 0 ]; then
	echo "installed in $DIR"
else
	command -v unzip > /dev/null || fail "unzip is needed to install the templates"
	echo "missing in $DIR: ${missing[*]}"
	echo "downloading $TEMPLATES_URL"
	curl -fsSL --retry 3 -o "$SCRATCH/templates.tpz" "$TEMPLATES_URL" || fail "the templates' download failed"
	echo "downloaded $(stat -c %s "$SCRATCH/templates.tpz") bytes"
	echo "$TEMPLATES_SHA256  $SCRATCH/templates.tpz" | sha256sum -c --quiet - \
		|| fail "the downloaded templates do not have the pinned SHA-256 $TEMPLATES_SHA256; nothing installed"
	unzip -q -o "$SCRATCH/templates.tpz" "${TEMPLATES[@]/#/templates/}" -d "$SCRATCH" \
		|| fail "the templates archive lacks one of: ${TEMPLATES[*]}"
	[ "$(tr -d '[:space:]' < "$SCRATCH/templates/version.txt")" = "$GODOT_VERSION" ] \
		|| fail "the templates archive is not for Godot $GODOT_VERSION"
	mkdir -p "$DIR"
	for name in "${TEMPLATES[@]}"; do
		# Copied beside, then renamed: an interrupted install leaves no half file behind.
		cp "$SCRATCH/templates/$name" "$DIR/$name.partial"
		mv -f "$DIR/$name.partial" "$DIR/$name"
	done
	echo "installed ${TEMPLATES[*]} in $DIR"
fi

step "4. the exports"
for entry in "${PRESETS[@]}"; do
	preset="${entry%%|*}"
	path="${entry#*|}"
	folder="$(dirname "$path")"
	rm -rf "$folder"
	mkdir -p "$folder"
	echo "-- $preset -> $path"
	status=0
	"$GODOT" --headless --path game --export-release "$preset" "$ROOT/$path" \
		> "$SCRATCH/export.raw" 2>&1 || status=$?
	clean_output "$SCRATCH/export.raw" "$SCRATCH/export.log"
	# Godot has exited 0 on errors before (brain.md H1, H2): its error lines fail the step,
	# and the files must be there.
	errors="$(error_lines "$SCRATCH/export.log")"
	[ -z "$errors" ] || fail "Godot's export of $preset printed error lines:"$'\n'"$errors"
	[ "$status" -eq 0 ] || fail "Godot's export of $preset failed, exit $status (see above)"
	for file in "$path" "${path%.*}.pck"; do
		[ -s "$file" ] || fail "the export of $preset did not write $file"
	done
done

step "5. every file in build/ against GitHub's limit"
over=()
while IFS= read -r -d '' file; do
	size="$(stat -c %s "$file")"
	awk -v s="$size" -v f="$file" 'BEGIN { printf "%12d bytes %9.2f MiB  %s\n", s, s / 1048576, f }'
	[ "$size" -le "$LIMIT_BYTES" ] || over+=("$file")
done < <(find build -type f -print0 | LC_ALL=C sort -z)
if [ "${#over[@]}" -gt 0 ]; then
	fail "over 100 MiB ($LIMIT_BYTES bytes), which GitHub refuses (docs/RELEASE.md §C): ${over[*]}"
fi

step "6. the Linux build starts"
[ "$(uname -s)" = "Linux" ] \
	|| fail "step 6 starts the Linux build, which needs Linux; this is $(uname -s): run tools/export.sh on Linux"
expected="$(expected_startup_lines)" || fail "no startup lines to expect (see above)"
mapfile -t EXPECTED <<< "$expected"
[ "${#EXPECTED[@]}" -eq 2 ] || fail "expected two startup lines, found: $expected"
for line in "${EXPECTED[@]}"; do
	echo "expecting: $line"
done
status=0
XDG_DATA_HOME="$SCRATCH/data" timeout --kill-after=10 "$START_TIMEOUT_S" \
	build/linux/mattini.x86_64 --headless --quit-after 300 > "$SCRATCH/start.raw" 2>&1 || status=$?
clean_output "$SCRATCH/start.raw" "$SCRATCH/start.log"
errors="$(error_lines "$SCRATCH/start.log")"
[ -z "$errors" ] || fail "the Linux build printed error lines:"$'\n'"$errors"
[ "$status" -eq 0 ] || fail "the Linux build exited $status (124: still running after $START_TIMEOUT_S s)"
for line in "${EXPECTED[@]}"; do
	grep -a -q -x -F -e "$line" "$SCRATCH/start.log" \
		|| fail "the Linux build did not print its startup line: $line"
	echo "started: $line"
done

echo "== export: done in ${SECONDS} s"
