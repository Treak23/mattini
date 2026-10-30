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
# GUT's last line starting with "---- " (its final line) is "---- All tests passed! ----"
# and GUT's run summary ("= Run Summary") comes before that line: a run cut short by a quit
# prints neither, and a pending or risky test makes the final line another (M0 review G-02,
# G-03; M1 review G-04 and M2-02's check: a test printing the pass line itself and quitting
# does not count). GUT reads no .gutconfig.json (-gconfig=), so only this command line
# configures it (G-04). The scans are only as good as the output formats they were
# measured on, so the Godot-version step requires Godot 4.6.3 (G-09) and GUT 9.6.1, as
# game/addons/gut/plugin.cfg names it (M2 R1 G-04: the scoped window below reads GUT's
# lines), and the GUT run requires GUT's own line "GUT version:  9.6.1" (two spaces; GUT's
# source of truth is its utils.gd, not plugin.cfg) and a script count in GUT's run summary
# ("Scripts <n>") equal to the test_*.gd files under game/tests/ (M3-02: V1-G-06, V1-G-05;
# a test that prints the summary and the pass line itself and quits has no count of its own
# after its fake summary, and GUT counts an inner test class as one more script, so none may
# exist). Every output is read with the ANSI codes and a CR at the end of a line removed, so
# a CR LF run (a Windows console) reads as an LF one (V1-G-07).
#
# The render step runs last (SPEC §12, §13 row 38; brief M3-R1-fix-3): four SceneTree scripts
# under game/tests/render/ render a synthetic world (Compatibility renderer on Mesa's llvmpipe,
# under xvfb-run) and measure, by number, where the photo, the surface classes, the capture-shadow
# lift and the crowns' colour land, and which way and how fast the river's ripples drift against
# the flow (brief v0.5.0-09), so that a flipped, shifted or swapped placement in a shader or a
# loader fails the gate with the check's own result line ("RENDER <check>: FAIL ..."). Every
# script runs at --fixed-fps 60, so that shader TIME advances exactly 1/60 s per drawn frame
# whatever llvmpipe's speed and the flow check's two frames are a known time apart (brain.md
# H29). It proves where those land and the drift's direction and speed on three synthetic
# bands, never the look, Forward+, the colour encoding or the owner's GPU. The step passes only when
# every check prints its "RENDER <check>: PASS" line and none a FAIL line, besides the scans and
# the exit status every Godot step has (a timeout kills a script that hangs: brain.md H25). Where
# xvfb-run is missing it fails, naming it and MATTINI_SKIP_RENDER=1; with that variable set it
# prints a SKIPPED line, in the log and on the terminal, and passes. The variable excuses only a
# machine that has no xvfb-run (the owner's Windows): where xvfb-run is found the step runs
# whatever the variable says. No brief, builder or review in a container sets it.
#
# An error line known to be benign may be excepted in tools/gate_allowlist.txt, one entry
# per line; blank lines and lines starting with # are ignored. Two kinds (M1 review G-03):
#   <text the error line contains> # <reason>
#       global: excepts a line containing the text in every Godot step;
#   <text the error line contains> @ res://tests/<script>.gd # <reason>
#       scoped to one test script: excepts a line containing the text only in the GUT
#       step, and only while that script runs. GUT 9.6.1 prints a script's path on a line
#       of its own before its before_all and its tests, and "<n>/<m> passed." after its
#       after_all (gut.gd:786 and :874; measured, brief M2-02); a line belongs to the
#       script whose path came last before it, until that script's "passed." line, the
#       next script's path or GUT's "= Run Summary". A script with no test prints no path,
#       so its lines belong to no script.
# An entry without a reason, whose text is empty or only spaces (it would match every
# line), whose text (spaces at its ends not counted) is shorter than 12 characters or is a
# scan prefix (ERROR, SCRIPT ERROR or [ERROR], with or without the colon Godot and GUT
# print after it: every line of its kind holds it), or scoped to anything but an existing
# file res://tests/<script>.gd, fails the gate (M2 R1 G-05). So does an entry whose text
# holds "Ignoring script" or "Failed to load script": those lines mean a test script did not
# run, and no entry, global or scoped, excepts them (M3-02, V1-G-01: the review passed a
# whole gate with an ignored script allowlisted). Every entry is a Findings item of the
# brief that adds it.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

UV_RUN=(uv run --project pipeline --frozen)
GODOT="${GODOT:-godot}"
GODOT_VERSION="4.6.3.stable"
GUT_VERSION="9.6.1"
GUT_PLUGIN="game/addons/gut/plugin.cfg"
ALLOWLIST="tools/gate_allowlist.txt"
# The shortest allowlist text that is specific enough to except anything (M2 R1 G-05).
ALLOWLIST_MIN_TEXT=12
# The lines that mean a test script did not run (GUT's "Ignoring script <path> because it
# does not extend GutTest", Godot's "Failed to load script"): an extended regex, never
# excepted by the allowlist (M3-02, V1-G-01).
NOT_RUN_LINES='Ignoring script|Failed to load script'
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

# Reads the allowlist into $SCRATCH/allowed.txt, the global entries' texts one per line,
# and $SCRATCH/scoped.txt, "<script>\t<text>" per scoped entry; neither holds an empty text
# (an empty pattern would match every line). Fails when an entry has no reason, a text
# that is empty or only spaces, shorter than ALLOWLIST_MIN_TEXT characters or a scan
# prefix (spaces at its ends not counted, nor a colon after the prefix), a text holding
# one of the NOT_RUN_LINES phrases, or a scope that is not an existing test script.
read_allowlist() {
	: > "$SCRATCH/allowed.txt" || return 1
	: > "$SCRATCH/scoped.txt" || return 1
	[ -f "$ALLOWLIST" ] || return 0
	local line entry text script trimmed bare
	while IFS= read -r line || [ -n "$line" ]; do
		case "$line" in
			"" | "#"*) continue ;;
			*" # "?*) entry="${line%% # *}" ;;
			*)
				allowlist_refused "without a reason" "$line"
				return 1
				;;
		esac
		text="$entry"
		script=""
		case "$entry" in
			*" @ "*)
				text="${entry% @ *}"
				script="${entry##* @ }"
				;;
		esac
		case "$text" in
			*[![:space:]]*) ;;
			*)
				allowlist_refused "with an empty text" "$line"
				return 1
				;;
		esac
		trimmed="${text#"${text%%[![:space:]]*}"}"
		trimmed="${trimmed%"${trimmed##*[![:space:]]}"}"
		if [ "${#trimmed}" -lt "$ALLOWLIST_MIN_TEXT" ]; then
			allowlist_refused "with a text shorter than $ALLOWLIST_MIN_TEXT characters (too short to be specific)" "$line"
			return 1
		fi
		# The text without the colon and spaces printed after a prefix ("SCRIPT ERROR: ").
		bare="${trimmed%"${trimmed##*[![:space:]:]}"}"
		case "$bare" in
			"ERROR" | "SCRIPT ERROR" | "[ERROR]")
				allowlist_refused "whose text is a scan prefix, which every line of its kind holds" "$line"
				return 1
				;;
		esac
		case "$text" in
			*"Ignoring script"* | *"Failed to load script"*)
				allowlist_refused "whose text holds a line that means a test script did not run, which no entry excepts" "$line"
				return 1
				;;
		esac
		if [ -z "$script" ]; then
			printf '%s\n' "$text" >> "$SCRATCH/allowed.txt"
			continue
		fi
		case "$script" in
			res://tests/*.gd) ;;
			*)
				allowlist_refused "scoped to something other than res://tests/<script>.gd" "$line"
				return 1
				;;
		esac
		if [ ! -f "game/${script#res://}" ]; then
			allowlist_refused "scoped to a test script that does not exist" "$line"
			return 1
		fi
		printf '%s\t%s\n' "$script" "$text" >> "$SCRATCH/scoped.txt"
	done < "$ALLOWLIST"
}

# Prints the lines of the cleaned output $2 that match the extended regex $1 and that no
# allowlist entry excepts (read_allowlist has read them); a line matching NOT_RUN_LINES is
# printed whatever the allowlist says. A global entry excepts a line
# containing its text. A scoped entry does so only when $3 is "gut", and only while its
# script runs: after GUT's line naming the script and before that script's "<n>/<m>
# passed." line, the next script's line or "= Run Summary" (the header above).
unexcused_lines() {
	PATTERN="$1" STEP="${3:-}" NOT_RUN="$NOT_RUN_LINES" awk '
		FILENAME == ARGV[1] { global[++globals] = $0; next }
		FILENAME == ARGV[2] {
			tab = index($0, "\t")
			scope[++scopes] = substr($0, 1, tab - 1)
			scoped[scopes] = substr($0, tab + 1)
			next
		}
		ENVIRON["STEP"] == "gut" && !summary {
			if ($0 ~ /^res:\/\/.*\.gd(\.[A-Za-z0-9_]+)?$/) running = $0
			else if ($0 ~ /^[0-9]+\/[0-9]+ passed\.$/) running = ""
			else if ($0 == "= Run Summary") { running = ""; summary = 1 }
		}
		$0 !~ ENVIRON["PATTERN"] { next }
		$0 ~ ENVIRON["NOT_RUN"] { print; next }
		{
			for (i = 1; i <= globals; i++) if (index($0, global[i])) next
			if (running != "")
				for (i = 1; i <= scopes; i++)
					if (scope[i] == running && index($0, scoped[i])) next
			print
		}
	' "$SCRATCH/allowed.txt" "$SCRATCH/scoped.txt" "$2"
}

# Godot, with user:// in this run's scratch folder: on Linux user:// lives under
# $XDG_DATA_HOME, so two gates at once (two worktrees) no longer share one (M0 review
# G-10). No effect on Windows.
run_godot() {
	XDG_DATA_HOME="$SCRATCH/data" "$GODOT" "$@"
}

# Runs a command, prints its output with ANSI colours and a CR at the end of a line removed
# (V1-G-07), and fails when the command exits non-zero or when an output line matches the
# extended regex $1 and is not allowed. With $2 "gut", the entries scoped to a test script
# apply too; with "", only the global ones. The cleaned output stays in $SCRATCH/out.log
# for the caller. The scan reads a NUL byte in the output as any other byte (awk; grep would
# need -a, M0 review G-07).
run_scanned() {
	local pattern="$1" scan="$2"
	shift 2
	local out="$SCRATCH/out.log" status=0
	read_allowlist || return 1
	"$@" > "$out.raw" 2>&1 || status=$?
	sed -e 's/\x1b\[[0-9;]*[A-Za-z]//g' -e 's/\r$//' "$out.raw" > "$out" || return 1
	cat "$out"
	local found
	found="$(unexcused_lines "$pattern" "$out" "$scan")" || return 1
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

# The scans match the output formats measured on Godot 4.6.3 and GUT 9.6.1; another
# version may print its errors or its per-script lines differently, so it is refused,
# naming what it found (M0 review G-09; M2 R1 G-04: GUT's version is its plugin.cfg's
# version line, exactly).
godot_version() {
	local found status=0 gut
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
	gut="$(grep -a -E '^version=' "$GUT_PLUGIN" 2>&1)" || true
	echo "GUT: $GUT_PLUGIN: ${gut:-no version line}"
	if [ "$gut" != "version=\"$GUT_VERSION\"" ]; then
		echo "== gate: GUT $GUT_VERSION required ($GUT_PLUGIN: version=\"$GUT_VERSION\"), found: ${gut:-no version line}"
		return 1
	fi
}

# The headless import, its output scanned. Godot prints an import error only on the run
# that imports the file; its .import file keeps valid=false afterwards (measured on
# 4.6.3), so a re-run with the broken file still in place is caught by the second check.
godot_import() {
	run_scanned '^(ERROR|SCRIPT ERROR)' "" run_godot --headless --path game --import || return 1
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
		run_scanned '^(ERROR|SCRIPT ERROR)' "" \
			run_godot --headless --path game --check-only -s "res://${file#game/}" || status=1
	done
	return "$status"
}

# The test scripts GUT collects from res://tests (-gdir with -ginclude_subdirs): the files
# named test_*.gd under game/tests/, hidden files and folders left out as GUT leaves them
# out (gut.gd _get_files; M3-02).
test_script_count() {
	find game/tests -name '.?*' -prune -o -type f -name 'test_*.gd' -print | wc -l | tr -d '[:space:]'
}

# The GUT run, with the scoped allowlist entries. All checks always run, so a failing run
# names every reason it failed. The second compares GUT's last line starting with "---- ",
# its trailing spaces removed, with the pass line; the third requires GUT's run summary
# ("= Run Summary") before that line, so a test that prints the pass line itself and quits
# before GUT's summary passes nothing (M2-02's check); the fourth requires the script count
# in the last run summary ("Scripts <n>") to equal the test scripts on disk, so a test that
# prints a fake summary and the pass line, then quits, has no count to show, and an ignored
# or unloaded script, or an inner test class, shows as a difference (V1-G-05); the fifth
# requires GUT's own version line (V1-G-06). The last four read the cleaned output the first
# left in $SCRATCH/out.log; when the allowlist was refused nothing ran and they are skipped.
gut_run() {
	local status=0 last version counted expected
	rm -f "$SCRATCH/out.log"
	run_scanned '^(ERROR|SCRIPT ERROR)|Ignoring script|Parse Error|Failed to load script|\[ERROR\]' gut \
		run_godot --headless --path game -s addons/gut/gut_cmdln.gd \
		-gdir=res://tests -ginclude_subdirs -gexit -gconfig= || status=1
	[ -f "$SCRATCH/out.log" ] || return 1
	last="$(grep -a -s -E '^---- ' "$SCRATCH/out.log" | tail -n 1)" || true
	last="${last%"${last##*[![:space:]]}"}"
	if [ "$last" != "---- All tests passed! ----" ]; then
		echo "== gate: GUT's last '---- ' line is not '---- All tests passed! ----': ${last:-there is none}"
		status=1
	fi
	if ! awk '
		$0 == "= Run Summary" { summary = NR }
		/^---- / { last = NR; before = summary }
		END { exit !(last && before) }
	' "$SCRATCH/out.log" 2> /dev/null; then
		echo "== gate: GUT's run summary ('= Run Summary') does not come before its last '---- ' line: the run did not reach GUT's summary"
		status=1
	fi
	counted="$(awk '
		$0 == "= Run Summary" { count = ""; reading = 1; next }
		reading && count == "" && /^Scripts +[0-9]+ *$/ { count = $2 }
		END { print count }
	' "$SCRATCH/out.log")" || true
	expected="$(test_script_count)"
	if [ -z "$counted" ]; then
		echo "== gate: GUT's last run summary has no 'Scripts <n>' line: it counted no test scripts ($expected test_*.gd files under game/tests)"
		status=1
	elif [ "$counted" != "$expected" ]; then
		echo "== gate: GUT counted $counted test scripts, game/tests holds $expected test_*.gd files: a script was ignored, not loaded or is an inner class, or the run did not reach its summary"
		status=1
	fi
	version="$(grep -a -s -E '^GUT version:' "$SCRATCH/out.log" | head -n 1)" || true
	if ! grep -a -s -q -x -F "GUT version:  $GUT_VERSION" "$SCRATCH/out.log"; then
		echo "== gate: GUT's own line 'GUT version:  $GUT_VERSION' (two spaces) is not in its output; found: ${version:-no GUT version line}"
		status=1
	fi
	return "$status"
}

# The render step's four scripts (the photo and the classes, the lift, the flow, the trees) and
# the checks each prints; the timeout, in seconds, kills a script that hangs (a SceneTree script
# that fails in _initialize can run on with no output, brain.md H25), 10 s later by force.
# RENDER_FPS is the fixed frame rate every script runs at (--fixed-fps), so that shader TIME is
# the drawn frames / 60 and the flow check's frames are 0.25 s apart on every machine.
RENDER_TIMEOUT=180
RENDER_FPS=60
RENDER_SKIP_LINE="== render: SKIPPED (MATTINI_SKIP_RENDER=1): where the photo, the classes, the lift and the crowns' colour land and which way the ripples drift are not checked"

# One render script ($1, a res:// path) under xvfb-run, its output scanned for engine errors as
# the other Godot steps are (the allowlist's global entries apply); then each check named in the
# rest of the arguments must have printed "RENDER <check>: PASS", and no line may read
# "RENDER <check>: FAIL". A script that fails an assertion exits 1, which run_scanned refuses
# too; the lines are what name the check. user:// is in this run's scratch folder (run_godot's
# reason), and the audio driver is the dummy one because a container has no sound card and
# Godot's own probing of one prints an ERROR line.
render_script() {
	local script="$1" check status=0
	shift
	run_scanned '^(ERROR|SCRIPT ERROR)' "" \
		env XDG_DATA_HOME="$SCRATCH/data" xvfb-run -a timeout --kill-after=10 "$RENDER_TIMEOUT" \
		"$GODOT" --path game --audio-driver Dummy --fixed-fps "$RENDER_FPS" --rendering-method gl_compatibility \
		--resolution 1280x720 -s "$script" || return 1
	for check in "$@"; do
		if ! grep -a -q -E "^RENDER $check: PASS( |\$)" "$SCRATCH/out.log"; then
			echo "== gate: $script did not print a 'RENDER $check: PASS' line: the check did not run to its end"
			status=1
		fi
	done
	if grep -a -E '^RENDER [^:]+: FAIL' "$SCRATCH/out.log"; then
		echo "== gate: a render check failed (the lines above name it and its numbers)"
		status=1
	fi
	return "$status"
}

render_step() {
	if ! command -v xvfb-run > /dev/null; then
		if [ "${MATTINI_SKIP_RENDER:-}" = "1" ]; then
			echo "$RENDER_SKIP_LINE"
			echo "$RENDER_SKIP_LINE" >&2
			return 0
		fi
		echo "== gate: xvfb-run is missing, so the render step cannot run: install it (the xvfb package), or on a machine that cannot render set MATTINI_SKIP_RENDER=1, which skips the step and says so in this log"
		return 1
	fi
	if [ -n "${MATTINI_SKIP_RENDER:-}" ]; then
		echo "== render: MATTINI_SKIP_RENDER=$MATTINI_SKIP_RENDER is set but xvfb-run is here, so the step runs: the variable excuses only a machine without xvfb-run"
	fi
	render_script res://tests/render/render_photo.gd photo classes || return 1
	render_script res://tests/render/render_lift.gd lift || return 1
	render_script res://tests/render/render_flow.gd flow || return 1
	render_script res://tests/render/render_trees.gd trees
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
step "render" render_step

echo "== gate: all steps passed"
