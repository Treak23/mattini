#!/usr/bin/env bash
# Exports a release of the current tree (docs/SPEC.md §11; docs/RELEASE.md §C; brief M1-06):
# Linux and Windows x86_64, each with its .pck beside the executable, into build/
# (git-ignored). Run from anywhere; it works in the repository it lives in:
#
#   tools/export.sh
#
# In order, stopping with a non-zero exit and a message at the first failure:
#   1. refuses unless the generated manifest has a terrain block (the build ships it);
#   2. rewrites the manifest, which re-checks the generated data against the config;
#   3. installs Godot 4.6.3-stable's export templates for these two presets into Godot's
#      templates folder when they are missing, from Godot's download mirror (github.com
#      release downloads are refused in cloud containers, brain.md H6), verified against
#      the SHA-256 pinned below; a Godot other than 4.6.3 is refused, as its templates
#      would not be these;
#   4. exports both presets of game/export_presets.cfg, each into a fresh folder;
#   5. lists every file in build/ with its size, and fails naming any file over 100 MiB
#      (104'857'600 bytes, GitHub's file limit: docs/RELEASE.md §C).
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

SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT

fail() {
	echo "export: $1" >&2
	exit 1
}

step() {
	echo "== export: $1"
}

# Godot's templates folder for this version (Linux, or Windows under Git Bash).
templates_dir() {
	case "$(uname -s)" in
		MINGW* | MSYS* | CYGWIN*) echo "${APPDATA:?}/Godot/export_templates/$GODOT_VERSION" ;;
		*) echo "${XDG_DATA_HOME:-$HOME/.local/share}/godot/export_templates/$GODOT_VERSION" ;;
	esac
}

step "1. the manifest has a terrain block"
[ -f "$MANIFEST" ] || fail "$MANIFEST is missing: run uv run --project pipeline python -m mattini download terrain, then uv run --project pipeline python -m mattini terrain"
"${UV_RUN[@]}" python -c 'import json, sys; sys.exit(0 if isinstance(json.load(open(sys.argv[1], encoding="utf-8")).get("terrain"), dict) else 1)' "$MANIFEST" \
	|| fail "$MANIFEST has no terrain block: run uv run --project pipeline python -m mattini download terrain, then uv run --project pipeline python -m mattini terrain"

step "2. the manifest, re-checked against the config"
"${UV_RUN[@]}" python -m mattini manifest || fail "python -m mattini manifest refused the generated data (see above)"

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
	"$GODOT" --headless --path game --export-release "$preset" "$ROOT/$path" \
		|| fail "Godot's export of $preset failed (see above)"
	# Godot has exited 0 on errors before (brain.md H1, H2): the files must be there.
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

echo "== export: done in ${SECONDS} s"
