"""Mutation rows of brief v0.5.0-13 (pin author's rehearsal). Run from the clone's root:
python3 mutate.py <out.tsv> [row ids...]. Each row: one exact replacement in tools/export.sh,
`git diff` saved, the export tests and the pin run, undone with `git apply -R` and run again
(both ways). Run it with TMPDIR set outside /tmp's shared space: row B11 leaks scratch folders."""
import re, subprocess, sys
from pathlib import Path

ROWS_DIR = Path(sys.argv[1]).resolve().parent / "rows"  # beside the out file, outside the tree
ROWS_DIR.mkdir(exist_ok=True)
EXISTING = ["pipeline/tests/test_export_checks.py", "pipeline/tests/test_export_startup_lines.py",
            "pipeline/tests/test_export_pack_list.py", "pipeline/tests/test_m4_08_export_packs.py"]
PIN = "pipeline/tests/test_v050_13_export_refusals.py"
F = "tools/export.sh"
T = lambda old: (old, "true" + old[old.index(" ||"):])  # "<check> || fail ..." -> "true || fail ..."
ROWS = [
 # the review's 31 (M3-R1-G-05), re-constructed: K = killed then, S = survived then
 ("R01", "K Linux-only refusal", '[ "$system" = "Linux" ] \\', 'true \\'),
 ("R02", "K PACKED_FOLDERS without photo", "PACKED_FOLDERS=(photo terrain)", "PACKED_FOLDERS=(terrain)"),
 ("R03", "K the Windows pack copy", '\tcp "build/linux/$pack" "build/windows/$pack.part"\n\tmv -f "build/windows/$pack.part" "build/windows/$pack"\n', "\t:\n"),
 ("R04", "K a startup line never printed passes", '[ -n "$printed" ] || fail "the Linux build did not print its startup line: $line"', '[ -n "$printed" ] || continue'),
 ("R05", "K the lines' order", "'$1 > previous { print $1; exit }'", "'{ print $1; exit }'"),
 ("R06", "K the started build's ERROR lines", '[ -z "$errors" ] || fail "the Linux build printed error lines:"', 'true || fail "the Linux build printed error lines:"'),
 ("R07", "K step 2's require_blocks", '[ -f "$MANIFEST" ] || fail "$MANIFEST is missing after step 1 wrote it"\nrequire_blocks\n', '[ -f "$MANIFEST" ] || fail "$MANIFEST is missing after step 1 wrote it"\n:\n'),
 ("R08", "K the CR strip", "sed -e 's/\\x1b\\[[0-9;]*[A-Za-z]//g' -e 's/\\r$//' \"$1\"", "sed -e 's/\\x1b\\[[0-9;]*[A-Za-z]//g' \"$1\""),
 ("R09", "K the packs-written check (a missing generated folder)", '[ "$packs_written" = "$PACKS_EXPECTED" ] \\', 'true \\'),
 ("R10", "S step 5's 100 MiB check", '[ "$size" -le "$LIMIT_BYTES" ] || over+=("$file")', 'true'),
 ("R11", "S all of 4c", '|| fail "the packs do not hold every generated file exactly once, as it is:"$\'\\n\'"$problems"', '|| true'),
 ("R12", "S 4c: a big file outside the packed folders", 'if pack_for(rel) == "mattini.pck" and size >= limit:', 'if False:'),
 ("R13", "S 4c: mattini.pck missing", 'if "mattini.pck" not in names:', 'if False:'),
 ("R14", "S 4c: holders != [want]", 'if holders != [want]:', 'if False:'),
 ("R15", "S 4c: the size and MD5 compare", 'elif packs[want][GENERATED_PREFIX + rel] != expected[rel]:', 'elif False:'),
 ("R16", "S 4c: a stray generated path", 'if path[len(GENERATED_PREFIX) :] not in expected:', 'if False:'),
 ("R17", "S 4c: a data pack holding something outside assets/generated/", 'elif name != "mattini.pck":', 'elif False:'),
 ("R18", "S 4c: the header test", 'if magic != 0x43504447 or fmt != 3 or (major, minor, patch) != (4, 6, 3) or flags != 2:', 'if False:'),
 ("R19", "S 4c: an entry past the end", 'if base + offset + length_of_file > size:', 'if False:'),
 ("R20", "S 4c: a path twice", 'if name in entries:', 'if False:'),
 ("R21", "S UNPACKED_LIMIT_BYTES a thousandfold", 'UNPACKED_LIMIT_BYTES=10485760', 'UNPACKED_LIMIT_BYTES=10485760000'),
 ("R22", "S the started build's exit status", '[ "$status" -eq 0 ] || fail "the Linux build exited', 'true || fail "the Linux build exited'),
 ("R23", "S SCRIPT ERROR dropped from the scan", "'^(ERROR|SCRIPT ERROR)'", "'^(ERROR)'"),
 ("R24", "S the export's own error scan", '[ -z "$errors" ] || fail "Godot\'s export of $preset printed error lines:"', 'true || fail "Godot\'s export of $preset printed error lines:"'),
 ("R25", "S the pack tool's exit status", '[ "$status" -eq 0 ] || fail "the pack tool failed for $folder', 'true || fail "the pack tool failed for $folder'),
 ("R26", "S the pack tool's error lines", '[ -z "$errors" ] || fail "the pack tool printed error lines', 'true || fail "the pack tool printed error lines'),
 ("R27", "S the pack exists", '[ -s "build/linux/$pack" ] || fail "the pack tool did not write', 'true || fail "the pack tool did not write'),
 ("R28", "S the exported files exist", '[ -s "$file" ] || fail "the export of $preset did not write $file"', 'true || fail "the export of $preset did not write $file"'),
 ("R29", "S the Godot-version refusal", '*) fail "Godot $GODOT_VERSION is needed for these templates; $GODOT is: $found" ;;', '*) ;;'),
 ("R30", "S step 1's refusal", '|| fail "python -m mattini manifest refused the generated data (see above)"', '|| true'),
 ("R31", "S the expected-line count", '[ "${#EXPECTED[@]}" -eq $((7 + ${#PACKS_WRITTEN[@]})) ] \\', 'true \\'),
 # this brief's own rows
 ("B01", "the flag set at step 4b, not 4", 'step "4. the exports"\nSTARTED_BUILD=1\n', 'step "4. the exports"\n', 'step "4b. the data packs"\n', 'step "4b. the data packs"\nSTARTED_BUILD=1\n'),
 ("B02", "the flag set before step 1", 'STARTED_BUILD=0\n', 'STARTED_BUILD=1\n'),
 ("B03", "the unfinished line never printed", '\t[ "$STARTED_BUILD" = 0 ] || echo "export: build/ is unfinished, do not ship it" >&2\n', ''),
 ("B04", "the unfinished line printed at every exit (an EXIT trap)", "trap 'rm -rf \"$SCRATCH\"' EXIT", "trap 'rm -rf \"$SCRATCH\"; [ \"$STARTED_BUILD\" = 0 ] || echo \"export: build/ is unfinished, do not ship it\" >&2' EXIT"),
 ("B05", "a refusal exits 2", '\t[ "$STARTED_BUILD" = 0 ] || echo "export: build/ is unfinished, do not ship it" >&2\n\texit 1\n', '\t[ "$STARTED_BUILD" = 0 ] || echo "export: build/ is unfinished, do not ship it" >&2\n\texit 2\n'),
 ("B06", "step 5: -le to -lt", '[ "$size" -le "$LIMIT_BYTES" ] || over+=("$file")', '[ "$size" -lt "$LIMIT_BYTES" ] || over+=("$file")'),
 ("B07", "step 5: only the last file over named", '[ "$size" -le "$LIMIT_BYTES" ] || over+=("$file")', '[ "$size" -le "$LIMIT_BYTES" ] || over=("$file")'),
 ("B08", "LIMIT_BYTES doubled", 'LIMIT_BYTES=104857600', 'LIMIT_BYTES=209715200'),
 ("B09", "4c: only a file in two packs refused", 'if holders != [want]:', 'if len(holders) > 1:'),
 ("B10", "4c: the size compared, not the MD5", 'elif packs[want][GENERATED_PREFIX + rel] != expected[rel]:', 'elif packs[want][GENERATED_PREFIX + rel][0] != expected[rel][0]:'),
 # rows added at the finalization (the checker's two wrong twins)
 ("B11", "an EXIT trap that prints the line and drops the scratch cleanup", '\t[ "$STARTED_BUILD" = 0 ] || echo "export: build/ is unfinished, do not ship it" >&2\n', '', "trap 'rm -rf \"$SCRATCH\"' EXIT", "trap 's=$?; [ \"$STARTED_BUILD\" = 0 ] || [ \"$s\" = 0 ] || echo \"export: build/ is unfinished, do not ship it\" >&2' EXIT"),
 ("B12", "the unfinished line on stdout", 'echo "export: build/ is unfinished, do not ship it" >&2', 'echo "export: build/ is unfinished, do not ship it"'),
]

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)

def tests():
    out = run(["uv", "run", "--project", "pipeline", "pytest", "-q", "-p", "no:cacheprovider", "-rf", *EXISTING, PIN]).stdout
    failed = re.findall(r"^FAILED (\S+)", out, re.M)
    summary = [l for l in out.splitlines() if re.search(r"\d+ (passed|failed)", l)]
    return failed, summary[-1] if summary else out[-300:]

out = open(sys.argv[1], "a")
pick = set(sys.argv[2:])
for rid, what, old, new, *more in ROWS:
    if pick and rid not in pick:
        continue
    src = Path(F).read_text()
    pairs = [(old, new)] + ([tuple(more)] if more else [])
    if any(src.count(o) != 1 for o, _ in pairs):
        out.write(f"{rid}\t{what}\tNOT-APPLICABLE\n"); out.flush(); continue
    text = src
    for o, n in pairs:
        text = text.replace(o, n)
    Path(F).write_text(text)
    patch = ROWS_DIR / f"row-{rid}.patch"
    patch.write_text(run(["git", "diff", "--", F]).stdout)
    failed, summary = tests()
    ex = [f for f in failed if not f.startswith(PIN)]
    pin = [f.split("::", 1)[1] for f in failed if f.startswith(PIN)]
    r = run(["git", "apply", "-R", str(patch)])
    clean = Path(F).read_text() == src
    back_failed, back = tests()  # the other way: the row undone, every test green again
    out.write(f"{rid}\t{what}\texisting_failed={len(ex)}\tpin_failed={len(pin)}\t{summary}\trestored={clean and r.returncode == 0}\tback={back} ({len(back_failed)} failed)\tEX={';'.join(x.split('::',1)[1] for x in ex)}\tPIN={';'.join(pin)}\n")
    out.flush()
