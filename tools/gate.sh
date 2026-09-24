#!/usr/bin/env bash
# The standard gate (CLAUDE.md §Build & Test): runs every check the repository has, in
# order, and stops at the first failing step with a non-zero exit, naming that step.
# Commit only on its own exit status: tools/gate.sh > gate.log && git commit ...
#
# Godot exits 0 on import errors, on scripts that do not parse, and GUT passes when it
# skips a test script it cannot load (brain.md §Hazards H1-H3) or runs nothing at all
# (its own "[ERROR]:  Nothing was run.", measured on GUT 9.6.1), so the Godot steps also
# scan their output. An error line known to be benign may be excepted in
# tools/gate_allowlist.txt: one entry per line, "<text the error line contains> # <reason>";
# blank lines and lines starting with # are ignored; an entry without a reason fails the
# gate. Every entry is a Findings item of the brief that adds it.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

UV_RUN=(uv run --project pipeline --frozen)
GODOT="${GODOT:-godot}"
ALLOWLIST="tools/gate_allowlist.txt"
SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT

fail() {
	echo "== gate: FAILED at step: $1"
	echo "== gate: FAILED at step: $1" >&2
	exit 1
}

step() {
	local name="$1"
	shift
	echo "== gate: step: $name"
	if ! "$@"; then
		fail "$name"
	fi
}

# The allowlist's texts, one per line, without blank lines (an empty pattern would match
# every line). Fails when an entry has no reason.
allowed_texts() {
	[ -f "$ALLOWLIST" ] || return 0
	local line
	while IFS= read -r line || [ -n "$line" ]; do
		case "$line" in
			"" | "#"*) continue ;;
			*" # "?*) printf '%s\n' "${line%% # *}" ;;
			*)
				echo "gate allowlist entry without a reason: $line" >&2
				return 1
				;;
		esac
	done < "$ALLOWLIST"
}

# Runs a command, prints its output with ANSI colours removed, and fails when the command
# exits non-zero or when an output line matches the extended regex $1 and is not allowed.
run_scanned() {
	local pattern="$1"
	shift
	local out="$SCRATCH/out.log" allowed="$SCRATCH/allowed.txt" status=0
	allowed_texts > "$allowed" || return 1
	"$@" > "$out.raw" 2>&1 || status=$?
	sed 's/\x1b\[[0-9;]*[A-Za-z]//g' "$out.raw" > "$out" || return 1
	cat "$out"
	local found
	found="$(grep -E "$pattern" "$out" | grep -v -F -f "$allowed" || true)"
	if [ -n "$found" ]; then
		echo "== gate: error lines in the output:"
		printf '%s\n' "$found"
		return 1
	fi
	if [ "$status" -ne 0 ]; then
		echo "== gate: exit status $status"
		return 1
	fi
}

# The headless import, its output scanned. Godot prints an import error only on the run
# that imports the file; its .import file keeps valid=false afterwards (measured on
# 4.6.3), so a re-run with the broken file still in place is caught by the second check.
godot_import() {
	run_scanned '^(ERROR|SCRIPT ERROR)' "$GODOT" --headless --path game --import || return 1
	local invalid
	invalid="$(grep -rl --include='*.import' --exclude-dir=.godot '^valid=false' game || true)"
	if [ -n "$invalid" ]; then
		echo "== gate: imports marked valid=false:"
		printf '%s\n' "$invalid"
		return 1
	fi
}

# Every .gd under game/ except the vendored addons, in a stable order.
mapfile -d '' GD_FILES < <(find game -path game/addons -prune -o -name '*.gd' -print0 | sort -z)

parse_check() {
	local file status=0
	for file in "${GD_FILES[@]}"; do
		echo "-- ${file#game/}"
		run_scanned '^(ERROR|SCRIPT ERROR)' \
			"$GODOT" --headless --path game --check-only -s "res://${file#game/}" || status=1
	done
	return "$status"
}

step "pytest" "${UV_RUN[@]}" pytest pipeline/tests
step "ruff check" "${UV_RUN[@]}" ruff check pipeline
step "ruff format --check" "${UV_RUN[@]}" ruff format --check pipeline
step "manifest" "${UV_RUN[@]}" python -m mattini manifest
step "godot import" godot_import
step "godot parse check" parse_check
step "gut" run_scanned 'Ignoring script|SCRIPT ERROR|Parse Error|Failed to load script|\[ERROR\]' \
	"$GODOT" --headless --path game -s addons/gut/gut_cmdln.gd \
	-gdir=res://tests -ginclude_subdirs -gexit
step "gdlint" "${UV_RUN[@]}" gdlint "${GD_FILES[@]}"
step "gdformat --check" "${UV_RUN[@]}" gdformat --check "${GD_FILES[@]}"

echo "== gate: all steps passed"
