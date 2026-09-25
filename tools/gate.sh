#!/usr/bin/env bash
# The standard gate (CLAUDE.md §Build & Test): runs every check the repository has, in
# order, and stops at the first failing step with a non-zero exit, naming that step.
# Commit only on its own exit status: tools/gate.sh > gate.log && git commit ...
#
# Godot exits 0 on import errors, on scripts that do not parse, and GUT passes when it
# skips a test script it cannot load (brain.md §Hazards H1-H3) or runs nothing at all
# (its own "[ERROR]:  Nothing was run.", measured on GUT 9.6.1), so the Godot steps also
# scan their output. The GUT step also scans for engine ERROR lines, which GUT itself
# charges to no test when they come from before_all or after_all, and it passes only when
# GUT's own last line says "---- All tests passed! ----": a run cut short by a quit, or
# holding a pending or risky test, prints no such line (M0 review G-02, G-03). GUT reads
# no .gutconfig.json (-gconfig=), so only this command line configures it (G-04). The
# scans are only as good as the output formats they were measured on, so the first Godot
# step requires Godot 4.6.3 (G-09). An error line known to be benign may be excepted in
# tools/gate_allowlist.txt: one entry per line, "<text the error line contains> # <reason>";
# blank lines and lines starting with # are ignored; an entry without a reason, or whose
# text is empty or only spaces (it would match every line), fails the gate. Every entry is
# a Findings item of the brief that adds it.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

UV_RUN=(uv run --project pipeline --frozen)
GODOT="${GODOT:-godot}"
GODOT_VERSION="4.6.3.stable"
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

# Says why the allowlist is refused, in the log and on the terminal.
allowlist_refused() {
	echo "gate allowlist entry $1: $2"
	echo "gate allowlist entry $1: $2" >&2
}

# The allowlist's texts, one per line, without blank lines (an empty pattern would match
# every line). Fails when an entry has no reason, or a text that is empty or only spaces.
allowed_texts() {
	[ -f "$ALLOWLIST" ] || return 0
	local line text
	while IFS= read -r line || [ -n "$line" ]; do
		case "$line" in
			"" | "#"*) continue ;;
			*" # "?*)
				text="${line%% # *}"
				case "$text" in
					*[![:space:]]*) printf '%s\n' "$text" ;;
					*)
						allowlist_refused "with an empty text" "$line"
						return 1
						;;
				esac
				;;
			*)
				allowlist_refused "without a reason" "$line"
				return 1
				;;
		esac
	done < "$ALLOWLIST"
}

# Godot, with user:// in this run's scratch folder: on Linux user:// lives under
# $XDG_DATA_HOME, so two gates at once (two worktrees) no longer share one (M0 review
# G-10). No effect on Windows.
run_godot() {
	XDG_DATA_HOME="$SCRATCH/data" "$GODOT" "$@"
}

# Runs a command, prints its output with ANSI colours removed, and fails when the command
# exits non-zero or when an output line matches the extended regex $1 and is not allowed.
# The cleaned output stays in $SCRATCH/out.log for the caller. grep -a: a NUL byte in the
# output must not turn the scan into "binary file matches" (M0 review G-07).
run_scanned() {
	local pattern="$1"
	shift
	local out="$SCRATCH/out.log" allowed="$SCRATCH/allowed.txt" status=0
	allowed_texts > "$allowed" || return 1
	"$@" > "$out.raw" 2>&1 || status=$?
	sed 's/\x1b\[[0-9;]*[A-Za-z]//g' "$out.raw" > "$out" || return 1
	cat "$out"
	local found
	found="$(grep -a -E "$pattern" "$out" | grep -a -v -F -f "$allowed" || true)"
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

# A fresh checkout's first headless Godot run that discovers a GDExtension (Terrain3D)
# aborts at exit, exit 134, after importing; with game/.godot/extension_list.cfg written
# first it exits 0 (brain.md H11). Written only when missing, listing every
# res://addons/**/*.gdextension, one per line, as Godot writes it.
extension_list() {
	local list="game/.godot/extension_list.cfg"
	[ -f "$list" ] && return 0
	mkdir -p game/.godot || return 1
	find game/addons -name '*.gdextension' -print | LC_ALL=C sort | sed 's|^game/|res://|' > "$list"
	echo "wrote $list:"
	cat "$list"
}

# The scans match the output formats measured on Godot 4.6.3; another version may print
# its errors differently, so it is refused, naming what it found (M0 review G-09).
godot_version() {
	local found status=0
	found="$(run_godot --version 2>&1)" || status=$?
	echo "$found"
	if [ "$status" -ne 0 ]; then
		echo "== gate: $GODOT --version exited $status"
		return 1
	fi
	case "$found" in
		"$GODOT_VERSION"*) ;;
		*)
			echo "== gate: Godot $GODOT_VERSION required, $GODOT is: $found"
			return 1
			;;
	esac
}

# The headless import, its output scanned. Godot prints an import error only on the run
# that imports the file; its .import file keeps valid=false afterwards (measured on
# 4.6.3), so a re-run with the broken file still in place is caught by the second check.
godot_import() {
	run_scanned '^(ERROR|SCRIPT ERROR)' run_godot --headless --path game --import || return 1
	local invalid
	invalid="$(grep -a -rl --include='*.import' --exclude-dir=.godot '^valid=false' game || true)"
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
			run_godot --headless --path game --check-only -s "res://${file#game/}" || status=1
	done
	return "$status"
}

# The GUT run. Both checks always run, so a failing run names every reason it failed.
gut_run() {
	local status=0
	rm -f "$SCRATCH/out.log"
	run_scanned '^(ERROR|SCRIPT ERROR)|Ignoring script|Parse Error|Failed to load script|\[ERROR\]' \
		run_godot --headless --path game -s addons/gut/gut_cmdln.gd \
		-gdir=res://tests -ginclude_subdirs -gexit -gconfig= || status=1
	if ! grep -a -q -s -E '^---- All tests passed! ----[[:space:]]*$' "$SCRATCH/out.log"; then
		echo "== gate: GUT printed no line '---- All tests passed! ----'"
		status=1
	fi
	return "$status"
}

step "uv lock --check" uv lock --check --project pipeline
step "pytest" "${UV_RUN[@]}" pytest pipeline/tests
step "ruff check" "${UV_RUN[@]}" ruff check pipeline
step "ruff format --check" "${UV_RUN[@]}" ruff format --check pipeline
step "manifest" "${UV_RUN[@]}" python -m mattini manifest
step "godot extension list" extension_list
step "godot version" godot_version
step "godot import" godot_import
step "godot parse check" parse_check
step "gut" gut_run
step "gdlint" "${UV_RUN[@]}" gdlint "${GD_FILES[@]}"
step "gdformat --check" "${UV_RUN[@]}" gdformat --check "${GD_FILES[@]}"

echo "== gate: all steps passed"
