#!/usr/bin/env bash
# Packs a release for GitHub (brief v0.5.0-06; docs/RELEASE.md §C):
#
#   tools/release_pack.sh <version> <sha> [<build> [<out>]]
#
# <build> (default build) holds linux/ and windows/ as tools/export.sh writes them; <out>
# (default build/release) gets four files, and SHA256SUMS is printed:
#   mattini-<version>-linux.tar.gz    the five Linux files under mattini-<version>-linux/
#   mattini-<version>-windows.zip     the five Windows files under mattini-<version>-windows/
#   SHA256SUMS                        the two archives and the ten files by their path inside
#                                     them, sorted by path (C locale); `sha256sum -c` passes
#                                     beside the two unpacked archives
#   release-notes.md                  tools/release_notes.md with @VERSION@, @SHA@ and the line
#                                     @SHA256SUMS@ filled
# Each archive holds its five files only (no folder entry), in name order (C locale), byte for
# byte. The time of every entry is SOURCE_DATE_EPOCH, else the commit time of <sha>; in the
# tar owner and group are 0, the mode 0755 for mattini.x86_64 and 0644 for the rest; the zip's
# times are UTC. The same build gives the same bytes, whatever the files' times and the time
# zone.
#
# Refused with exit 1, naming the cause and writing nothing into <out>: a version that is not
# X.Y.Z or not game/project.godot's, a sha that is not 40 lower-case hex digits, any of the ten
# files missing, a mattini-*.pck in a build folder that the archive would leave out, no
# SOURCE_DATE_EPOCH and no such commit, a placeholder left in the notes.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
export LC_ALL=C

fail() {
	echo "release_pack: $1" >&2
	exit 1
}

[ "$#" -ge 2 ] && [ "$#" -le 4 ] || fail "usage: tools/release_pack.sh <version> <sha> [<build> [<out>]]"
VERSION="$1"
SHA="$2"
BUILD="${3:-build}"
OUT="${4:-build/release}"

LINUX_FILES=(
	libterrain.linux.release.x86_64.so
	mattini-photo.pck
	mattini-terrain.pck
	mattini.pck
	mattini.x86_64
)
WINDOWS_FILES=(
	libterrain.windows.release.x86_64.dll
	mattini-photo.pck
	mattini-terrain.pck
	mattini.exe
	mattini.pck
)
TEMPLATE="tools/release_notes.md"
PROJECT="game/project.godot"

[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || fail "the version $VERSION is not X.Y.Z"
[[ "$SHA" =~ ^[0-9a-f]{40}$ ]] || fail "the sha $SHA is not 40 lower-case hex digits"

project_version="$(sed -n 's/^config\/version="\(.*\)"[[:space:]]*$/\1/p' "$PROJECT" | head -n 1)"
[ -n "$project_version" ] || fail "$PROJECT has no config/version"
[ "$VERSION" = "$project_version" ] \
	|| fail "the version $VERSION is not $PROJECT's version $project_version"

problems=""
check_folder() {
	local platform="$1" name pack listed known
	shift
	local files=("$@")
	for name in "${files[@]}"; do
		[ -f "$BUILD/$platform/$name" ] || problems+=$'\n'"  $BUILD/$platform/$name is missing"
	done
	for pack in "$BUILD/$platform"/mattini-*.pck; do
		[ -e "$pack" ] || continue
		listed=0
		for known in "${files[@]}"; do
			[ "$(basename "$pack")" = "$known" ] && listed=1
		done
		[ "$listed" -eq 1 ] \
			|| problems+=$'\n'"  $pack is a data pack the archive would leave out (add it to this script's list)"
	done
}
check_folder linux "${LINUX_FILES[@]}"
check_folder windows "${WINDOWS_FILES[@]}"
[ -z "$problems" ] || fail "the build in $BUILD is not the ten files of a release:$problems"

[ -f "$TEMPLATE" ] || fail "$TEMPLATE is missing"

EPOCH="${SOURCE_DATE_EPOCH:-}"
if [ -z "$EPOCH" ]; then
	EPOCH="$(git show -s --format=%ct "$SHA" 2> /dev/null)" \
		|| fail "SOURCE_DATE_EPOCH is not set and git has no commit $SHA to take the time from"
fi
[[ "$EPOCH" =~ ^[0-9]+$ ]] || fail "the archive time $EPOCH is not a whole number of seconds"

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/files" "$STAGE/out"

LINUX_DIR="mattini-$VERSION-linux"
WINDOWS_DIR="mattini-$VERSION-windows"
mkdir -p "$STAGE/files/$LINUX_DIR" "$STAGE/files/$WINDOWS_DIR"
for name in "${LINUX_FILES[@]}"; do
	cp "$BUILD/linux/$name" "$STAGE/files/$LINUX_DIR/$name"
	if [ "$name" = "mattini.x86_64" ]; then chmod 0755 "$STAGE/files/$LINUX_DIR/$name"; else chmod 0644 "$STAGE/files/$LINUX_DIR/$name"; fi
	touch -d "@$EPOCH" "$STAGE/files/$LINUX_DIR/$name"
done
for name in "${WINDOWS_FILES[@]}"; do
	cp "$BUILD/windows/$name" "$STAGE/files/$WINDOWS_DIR/$name"
	chmod 0644 "$STAGE/files/$WINDOWS_DIR/$name"
	touch -d "@$EPOCH" "$STAGE/files/$WINDOWS_DIR/$name"
done

linux_members=()
for name in "${LINUX_FILES[@]}"; do linux_members+=("$LINUX_DIR/$name"); done
windows_members=()
for name in "${WINDOWS_FILES[@]}"; do windows_members+=("$WINDOWS_DIR/$name"); done

# The members are given by name, in name order, so no folder entry is written.
(
	cd "$STAGE/files"
	tar --format=gnu --numeric-owner --owner=0 --group=0 --mtime="@$EPOCH" -cf - "${linux_members[@]}" \
		| gzip -n -9 > "$STAGE/out/$LINUX_DIR.tar.gz"
	TZ=UTC zip -q -X -D -9 "$STAGE/out/$WINDOWS_DIR.zip" "${windows_members[@]}"
)

(
	cd "$STAGE/files"
	sha256sum "${linux_members[@]}" "${windows_members[@]}"
	cd "$STAGE/out"
	sha256sum "$LINUX_DIR.tar.gz" "$WINDOWS_DIR.zip"
) | sort -b -k2 > "$STAGE/out/SHA256SUMS"
[ "$(wc -l < "$STAGE/out/SHA256SUMS")" -eq 12 ] || fail "SHA256SUMS does not hold 12 lines"

notes=""
while IFS= read -r line || [ -n "$line" ]; do
	if [ "$line" = "@SHA256SUMS@" ]; then
		line="$(cat "$STAGE/out/SHA256SUMS")"
	else
		line="${line//@VERSION@/$VERSION}"
		line="${line//@SHA@/$SHA}"
	fi
	notes+="$line"$'\n'
done < "$TEMPLATE"
if printf '%s' "$notes" | grep -q -E '@[A-Z0-9_]+@'; then
	fail "$TEMPLATE leaves a placeholder: $(printf '%s' "$notes" | grep -o -E '@[A-Z0-9_]+@' | sort -u | tr '\n' ' ')"
fi
printf '%s' "$notes" > "$STAGE/out/release-notes.md"

mkdir -p "$OUT"
cp "$STAGE/out/$LINUX_DIR.tar.gz" "$STAGE/out/$WINDOWS_DIR.zip" "$STAGE/out/SHA256SUMS" \
	"$STAGE/out/release-notes.md" "$OUT/"
echo "== release_pack: wrote $OUT (SHA256SUMS follows)"
cat "$OUT/SHA256SUMS"
