#!/usr/bin/env bash
# Exports a release of the current tree (docs/SPEC.md §11; docs/RELEASE.md §C; brief M1-06):
# Linux and Windows x86_64, each with its .pck beside the executable, into build/
# (git-ignored). Run from anywhere; it works in the repository it lives in:
#
#   tools/export.sh
#
# Before step 1 it refuses a system other than Linux (`uname -s`), naming the system and
# Linux: step 6 starts the Linux build, so on another system the export used to run to its
# end and then fail. Nothing is downloaded, installed or exported on a refusal (brief M3-02;
# M2-02 Findings 9). In order, stopping with a non-zero exit and a message at the first
# failure:
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
#      on errors, brain.md H1, H2), or a file the export did not write; then
#      4b. writes the data packs (brief M3-08): the generated folders in PACKED_FOLDERS
#      (photo, terrain) are too large for mattini.pck, which the presets keep them out of,
#      so game/tools/pack.gd writes each folder that exists into build/linux/mattini-<folder>.pck
#      (a folder that does not exist gets no pack, and the script says so), and the pack is
#      copied beside the Windows executable too; then
#      4c. reads the directory of mattini.pck and of every mattini-*.pck in each build folder
#      (Godot 4.6.3's pack format 3, in Python) and fails, listing every problem, unless each
#      file under game/assets/generated/ (but names starting with ".", *.part and *.import)
#      is in exactly one pack, the right one, with its size and MD5; no pack holds a
#      generated path that is not such a file; no data pack holds anything outside
#      assets/generated/; and no generated file of UNPACKED_LIMIT_BYTES or more stays in
#      mattini.pck;
#   5. lists every file in build/ with its size, and fails naming any file over 100 MiB
#      (104'857'600 bytes, GitHub's file limit: docs/RELEASE.md §C);
#   6. starts the Linux build headless for 300 frames (build/linux/mattini.x86_64
#      --headless --quit-after 300, with user:// in a scratch folder, so the owner's is not
#      touched), and requires its startup lines, in this order: one
#      "mattini <version>: data pack <name> loaded" per pack step 4b wrote (name order),
#      then
#      "mattini <version>: terrain <area> loaded, <columns> x <rows> vertices at <spacing> m"
#      and "mattini <version>: buildings <area> loaded, <n> buildings in <k> chunks, <t>
#      triangles" with game/project.godot's version and the manifest's values (brief M2-05),
#      exit 0 and no ERROR line (M1 review G-02: an export without its terrain passed every
#      step before this one). A manifest without one of the blocks is refused there too,
#      with step 2's message.
#      Nothing here starts the Windows build (the owner's PC is its test).
# Godot's output is read with ANSI colours and a CR at the end of a line removed, so a CR LF
# run reads as an LF one (brief M3-02, V1-G-07).
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
# The generated folders that ship as data packs beside the executable, in name order, and
# the same list the presets' exclude filters hold (game/export_presets.cfg; brief M3-08).
PACKED_FOLDERS=(photo terrain)
# Step 4c: a generated file of this size (10 MiB) or more must be in a packed folder.
UNPACKED_LIMIT_BYTES=10485760
# Step 4b: the pack tool is killed if it has not quit after this many seconds (a 96 MB
# folder took a few seconds).
PACK_TIMEOUT_S=300
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

# Copies the output file $1 to $2 with ANSI colours and a CR at the end of a line removed
# (V1-G-07), and prints it.
clean_output() {
	sed -e 's/\x1b\[[0-9;]*[A-Za-z]//g' -e 's/\r$//' "$1" > "$2"
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

# The startup lines of the started build, one per line: first one per data pack name given
# as an argument ("mattini <version>: data pack <name> loaded", which
# game/scripts/data_packs.gd prints), in the order given; then the two lines
# game/scripts/main.gd prints: once the terrain is loaded, the version from
# game/project.godot, the area, columns, rows and spacing from the manifest's terrain block,
# the spacing written as main.gd writes it (at most two decimals, no trailing zeros); once
# the buildings are loaded, the version, the area, the count of buildings, of chunks and of
# triangles from the manifest's buildings block. A missing block is refused with step 2's
# message, not a traceback.
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
for pack in sys.argv[5:]:
    print("mattini %s: data pack %s loaded" % (version, pack))
spacing = ("%.2f" % terrain["spacing_m"]).rstrip("0").rstrip(".")
fields = (version, terrain["area"], terrain["columns"], terrain["rows"], spacing)
print("mattini %s: terrain %s loaded, %d x %d vertices at %s m" % fields)
chunks = buildings["chunks"]
count = sum(chunk["buildings"] for chunk in chunks)
triangles = sum(chunk["triangles"] for chunk in chunks)
fields = (version, buildings["area"], count, len(chunks), triangles)
print("mattini %s: buildings %s loaded, %d buildings in %d chunks, %d triangles" % fields)
' "$MANIFEST" game/project.godot "$NO_TERRAIN" "$NO_BUILDINGS" "$@"
}

# Step 4c's check (Python, run through uv like step 6's): arguments are the generated folder,
# the size at which an unpacked file is refused, the packed folders (one string, blank
# separated) and the build folders to read. Prints one line per problem and exits 1 if there
# is any.
CHECK_PACKS="$(
	cat << 'PY'
import hashlib
import os
import struct
import sys

generated, limit, packed, *builds = sys.argv[1:]
limit, packed, problems = int(limit), packed.split(), []
GENERATED_PREFIX = "assets/generated/"


def pack_for(rel):
    top = rel.split("/")[0] if "/" in rel else ""
    return "mattini-%s.pck" % top if top in packed else "mattini.pck"


def md5_of(path):
    digest = hashlib.md5()
    with open(path, "rb") as file:
        for block in iter(lambda: file.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_pack(path):
    # Godot 4.6.3's pack format 3: 24 bytes of magic GDPC, format, version 4.6.3 and flags
    # (2 = relative file base), the file base and the directory's offset as u64, 16 reserved
    # u32; the directory: a u32 count, then per file a u32 path length (padded to 4), the
    # path, a u64 offset from the file base, a u64 size, a 16-byte MD5 and u32 flags.
    entries, size = {}, os.path.getsize(path)
    with open(path, "rb") as file:
        head = file.read(104)
        if len(head) < 104:
            raise ValueError("shorter than a pack's header")
        magic, fmt, major, minor, patch, flags = struct.unpack_from("<6I", head)
        if magic != 0x43504447 or fmt != 3 or (major, minor, patch) != (4, 6, 3) or flags != 2:
            raise ValueError("not format 3 of Godot 4.6.3 with a relative file base")
        base, directory = struct.unpack_from("<QQ", head, 24)
        file.seek(directory)
        (count,) = struct.unpack("<I", file.read(4))
        for _ in range(count):
            (length,) = struct.unpack("<I", file.read(4))
            raw = file.read(length).rstrip(b"\0").decode("utf-8")
            offset, length_of_file = struct.unpack("<QQ", file.read(16))
            md5 = file.read(16).hex()
            file.read(4)
            if base + offset + length_of_file > size:
                raise ValueError("%s ends beyond the end of the file" % raw)
            name = raw.removeprefix("res://")
            if name in entries:
                raise ValueError("%s is in it twice" % name)
            entries[name] = (length_of_file, md5)
    return entries


expected = {}
for here, dirs, files in os.walk(generated):
    dirs[:] = sorted(name for name in dirs if not name.startswith("."))
    for name in sorted(files):
        if name.startswith(".") or name.endswith((".part", ".import")):
            continue
        path = os.path.join(here, name)
        rel = os.path.relpath(path, generated).replace(os.sep, "/")
        expected[rel] = (os.path.getsize(path), md5_of(path))

for rel, (size, _) in sorted(expected.items()):
    if pack_for(rel) == "mattini.pck" and size >= limit:
        problems.append(
            "%s/%s is %d bytes, %d or more, outside the packed folders (%s)"
            % (generated, rel, size, limit, " ".join(packed))
        )

for build in builds:
    packs = {}
    names = sorted(
        name
        for name in os.listdir(build)
        if name == "mattini.pck" or (name.startswith("mattini-") and name.endswith(".pck"))
    )
    if "mattini.pck" not in names:
        problems.append("%s: mattini.pck is missing" % build)
    for name in names:
        try:
            packs[name] = read_pack(os.path.join(build, name))
        except (OSError, ValueError, UnicodeDecodeError, struct.error) as error:
            problems.append("%s: %s cannot be read as a Godot 4.6.3 pack (%s)" % (build, name, error))
    for rel in sorted(expected):
        holders = sorted(name for name, entries in packs.items() if GENERATED_PREFIX + rel in entries)
        want = pack_for(rel)
        if holders != [want]:
            problems.append(
                "%s: %s is in %s, not in %s alone" % (build, rel, ", ".join(holders) or "no pack", want)
            )
        elif packs[want][GENERATED_PREFIX + rel] != expected[rel]:
            held, file = packs[want][GENERATED_PREFIX + rel], expected[rel]
            problems.append(
                "%s: %s in %s has %d bytes, MD5 %s; the file has %d bytes, MD5 %s"
                % (build, rel, want, held[0], held[1], file[0], file[1])
            )
    for name in sorted(packs):
        for path in sorted(packs[name]):
            if path.startswith(GENERATED_PREFIX):
                if path[len(GENERATED_PREFIX) :] not in expected:
                    problems.append(
                        "%s: %s holds %s, which is not a generated file that ships" % (build, name, path)
                    )
            elif name != "mattini.pck":
                problems.append("%s: %s holds %s, outside %s" % (build, name, path, GENERATED_PREFIX))

print("\n".join(problems))
sys.exit(1 if problems else 0)
PY
)"

# Godot's templates folder for this version (Linux only: the script refuses any other system
# before it gets here).
templates_dir() {
	echo "${XDG_DATA_HOME:-$HOME/.local/share}/godot/export_templates/$GODOT_VERSION"
}

# Exits 0 when the manifest's block named $1 is an object (not null, not missing), else 1.
has_block() {
	"${UV_RUN[@]}" python -c 'import json, sys; sys.exit(0 if isinstance(json.load(open(sys.argv[1], encoding="utf-8")).get(sys.argv[2]), dict) else 1)' "$MANIFEST" "$1"
}

system="$(uname -s)"
[ "$system" = "Linux" ] \
	|| fail "step 6 starts the Linux build, which needs Linux; this is $system: run tools/export.sh on Linux (nothing was downloaded, installed or exported)"

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

step "4b. the data packs"
PACKS_WRITTEN=()
for folder in "${PACKED_FOLDERS[@]}"; do
	if [ ! -d "game/assets/generated/$folder" ]; then
		echo "no game/assets/generated/$folder: no mattini-$folder.pck"
		continue
	fi
	pack="mattini-$folder.pck"
	rm -f "build/linux/$pack" "build/linux/$pack.part"
	status=0
	XDG_DATA_HOME="$SCRATCH/data" timeout --kill-after=10 "$PACK_TIMEOUT_S" "$GODOT" --headless --path game \
		-s res://tools/pack.gd -- "$ROOT/build/linux/$pack" "res://assets/generated/$folder" \
		> "$SCRATCH/pack.raw" 2>&1 || status=$?
	clean_output "$SCRATCH/pack.raw" "$SCRATCH/pack.log"
	errors="$(error_lines "$SCRATCH/pack.log")"
	[ -z "$errors" ] || fail "the pack tool printed error lines for $folder:"$'\n'"$errors"
	[ "$status" -eq 0 ] || fail "the pack tool failed for $folder, exit $status (124: still running after $PACK_TIMEOUT_S s; see above)"
	[ -s "build/linux/$pack" ] || fail "the pack tool did not write build/linux/$pack"
	# Beside the Windows executable too, through a .part and a rename.
	cp "build/linux/$pack" "build/windows/$pack.part"
	mv -f "build/windows/$pack.part" "build/windows/$pack"
	PACKS_WRITTEN+=("$pack")
done

step "4c. every generated file is in exactly one pack, as it is"
build_folders=()
for entry in "${PRESETS[@]}"; do
	build_folders+=("$(dirname "${entry#*|}")")
done
problems="$("${UV_RUN[@]}" python -c "$CHECK_PACKS" game/assets/generated "$UNPACKED_LIMIT_BYTES" "${PACKED_FOLDERS[*]}" "${build_folders[@]}" 2>&1)" \
	|| fail "the packs do not hold every generated file exactly once, as it is:"$'\n'"$problems"
echo "checked ${build_folders[*]}: every generated file is in its pack, with its size and MD5"

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
expected="$(expected_startup_lines ${PACKS_WRITTEN[@]+"${PACKS_WRITTEN[@]}"})" || fail "no startup lines to expect (see above)"
mapfile -t EXPECTED <<< "$expected"
[ "${#EXPECTED[@]}" -eq $((2 + ${#PACKS_WRITTEN[@]})) ] \
	|| fail "expected $((2 + ${#PACKS_WRITTEN[@]})) startup lines, found: $expected"
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
previous=0
for line in "${EXPECTED[@]}"; do
	at="$(grep -a -n -x -F -e "$line" "$SCRATCH/start.log" | head -n 1 | cut -d: -f1)" || true
	[ -n "$at" ] || fail "the Linux build did not print its startup line: $line"
	[ "$at" -gt "$previous" ] || fail "the Linux build printed its startup line out of order: $line"
	previous="$at"
	echo "started: $line"
done

echo "== export: done in ${SECONDS} s"
