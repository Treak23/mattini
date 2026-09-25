#!/usr/bin/env bash
# Software screenshots of a manifest's terrain (docs/SPEC.md §12; brief M1-04). Evidence,
# never a gate: Godot's Compatibility renderer on Mesa's llvmpipe under Xvfb, not the
# Forward+ look (brain.md H12).
#
#   tools/shot.sh <manifest> <out_dir> "<name>,E,N,above_m,bearing_deg,pitch_deg;..."
#
# E and N are LV95 metres; above_m is the height above the terrain there; the bearing is
# clockwise from north; the pitch is degrees below the horizon. Writes <out_dir>/<name>.jpg
# (1280 x 720) per view, and fails unless every one was written: Godot exits 0 even when
# its script does not parse (brain.md H2), and a runtime error in a script run with -s
# leaves Godot running, so the run is killed after SHOT_TIMEOUT seconds (default 300).
set -euo pipefail

if [ "$#" -ne 3 ]; then
	echo "usage: tools/shot.sh <manifest> <out_dir> \"<name>,E,N,above_m,bearing_deg,pitch_deg;...\"" >&2
	exit 2
fi
if ! command -v xvfb-run > /dev/null; then
	echo "shot: xvfb-run is missing; it is needed to render without a display (brain.md H12)" >&2
	exit 1
fi

GODOT="${GODOT:-godot}"
MANIFEST="$(realpath "$1")"
mkdir -p "$2"
OUT="$(realpath "$2")"
VIEWS="$3"

# The names this run must write; a stale file of the same name must not pass for a new one.
NAMES=()
IFS=';' read -r -a SPECS <<< "$VIEWS"
for spec in "${SPECS[@]}"; do
	[ -n "${spec// /}" ] || continue
	name="${spec%%,*}"
	name="${name// /}"
	NAMES+=("$name")
	rm -f "$OUT/$name.jpg"
done

cd "$(dirname "${BASH_SOURCE[0]}")/.."
status=0
xvfb-run -a timeout --kill-after=10 "${SHOT_TIMEOUT:-300}" "$GODOT" --path game --rendering-method gl_compatibility --resolution 1280x720 \
	-s res://tools/shot.gd -- "$MANIFEST" "$OUT" "$VIEWS" || status=$?

for name in "${NAMES[@]}"; do
	if [ ! -s "$OUT/$name.jpg" ]; then
		echo "shot: $OUT/$name.jpg was not written" >&2
		status=1
	fi
done
exit "$status"
