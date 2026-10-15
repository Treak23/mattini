# Brief: M3-02 — M2's residue, the game and the tools
Status: DONE (d67e17e)

Written in the design realm; executed by one fresh builder session under
`docs/roles/BUILD.md`. Lane B of wave 1, first; M3-08 follows in this lane
(`docs/briefs/M3-plan.md`).

## Goal

The game-and-tools half of M2's residue (`docs/history/ARCS.md` §M2, "Carried into M3"):
seven V1 findings and one builder's follow-up, each a P3.

- The gate never excepts a line that means a test script did not run (V1-G-01).
- GUT's script count is checked against the test scripts on disk (V1-G-05).
- The gate requires GUT's own version line (V1-G-06).
- CR is stripped before the scans in gate.sh and export.sh (V1-G-07).
- TerrainGrid's refusal says "origin or height offset" (V1-G-08).
- The camera test pins the start view's centre and height (V1-G-02).
- The axes check is tested with each step kept (V1-G-03).
- `export.sh` refuses a system other than Linux before it downloads or exports anything
  (M2-02 Findings 9).

V1-G-04 (the look test) moved to M3-12, whose new walls and roof colours change that test
anyway.

## Read first, in order

1. `CLAUDE.md` (the gate paragraph); `brain.md` H3, H8, H9, H18.
2. `docs/history/ARCS.md` §M2 (D25 and the carried table); `docs/reviews/M2-V1.md`.
3. `tools/gate.sh`, `tools/gate_allowlist.txt`, `tools/export.sh`;
   `game/scripts/terrain/terrain_grid.gd`; `game/tests/test_scene_placement.gd`,
   `test_building_chunks_world.gd`; `pipeline/tests/test_release_hygiene.py` (how the
   repository tests `tools/`).
4. The pinned tests: `docs/briefs/pinning/M3-02/`.

## Decisions already made

1. **The not-run lines (V1-G-01).** gate.sh's `unexcused_lines` reports a line matching
   `Ignoring script` or `Failed to load script` whatever the allowlist says, global or
   scoped. Measured on the real gate: a `test_zz_notgut.gd` that extends Node, with an
   allowlist entry for its line, passed with exit 0 and GUT counting 23 scripts for 24 files.
   Optionally, `read_allowlist` also refuses an entry holding either phrase.
2. **GUT's script count (V1-G-05).** The GUT step reads `Scripts <n>` after the last
   `= Run Summary` and requires it to equal the number of `test_*.gd` files under
   `game/tests/` on disk (counted as GUT collects them), naming both numbers.
   - Measured: a test that prints a fake summary and the pass line and then quits passed
     the whole gate, with no allowlist entry.
   - GUT counts an inner test class as one more script (measured). None exists; the
     equality forbids them (design's decision).
3. **GUT's version (V1-G-06).** The GUT step requires a line exactly `GUT version:  9.6.1`
   (two spaces), as GUT prints it, and names what it found. A prefix such as `9.6.10` is
   refused.
4. **CR (V1-G-07).** gate.sh's and export.sh's cleanings also remove a CR at a line's end
   (`s/\r$//`) before any scan. Measured: a CR LF copy of a passing run failed the gate
   closed, and a scoped entry stopped applying.
5. **TerrainGrid (V1-G-08).** Its refusal says "(its origin or height offset differs)",
   BuildingChunks' wording, split over two lines (one line exceeds gdlint's 100 characters,
   measured).
6. **The camera test (V1-G-02) and the axes test (V1-G-03)** close test gaps: `main.gd` and
   `building_chunks.gd` are right. `test_scene_placement.gd` is replaced whole, because the
   allowlist's scopes name that file.
7. **export.sh (M2-02 Findings 9)** checks `uname -s` = Linux before step 1 (at the latest
   before step 3). On another system it downloads, installs and exports nothing, and its
   message names the system and Linux.
8. **The tools tests** are pytest files under `pipeline/tests/`. `fake_tools.py` copies the
   real `tools/gate.sh` or `tools/export.sh`, unchanged, into a scratch tree and runs it with
   stand-ins for Godot and uv; GUT's output is built from measured probes.
   - They skip where bash is missing or the system is not Linux.
   - The stand-in export writes a real Godot pack (format 3, PCKPacker's bytes for a
     three-file pack, measured), because M3-08's step 4c reads every `.pck`.

## Scope — files you may touch

- `tools/gate.sh`, `tools/export.sh`.
- `game/scripts/terrain/terrain_grid.gd`.
- `game/tests/`: `test_scene_placement.gd` (the pinned replacement),
  `test_building_chunks_axes.gd` and `test_terrain_grid_world.gd` (pinned, new) and their
  `.uid` files (Godot writes them at the first import; `test_repo_tracked.py` requires them
  staged).
- `pipeline/tests/`: `fake_tools.py`, `test_gate_gut_run.py`, `test_export_checks.py`
  (pinned, new), and your own tests, named `test_m3_02_*` (no other lane uses the prefix).

Not `tools/gate_allowlist.txt`: no entry is needed, and other lanes append there. Not
`main.gd`, `building_chunks.gd`, or the pipeline's modules.

## Depends on

None. First in lane B; M3-08 follows and changes `export.sh` again (it keeps these changes).

## Done when (gates)

- [ ] The pinned copies are in place (`cp -r docs/briefs/pinning/M3-02/. .`) and stay
      byte-identical (`cmp`).
      - does NOT prove: that they are the right tests.
- [ ] Before the fix, the pinned files fail for their findings' reasons; record the count per
      file. Design measured on the unmodified tools: `test_gate_gut_run.py` 12,
      `test_export_checks.py` 5, `test_terrain_grid_world.gd` 2. The others pass today:
      they close test gaps.
      - does NOT prove: the behaviour on Windows (the CR case is simulated).
- [ ] On the real gate, in a scratch clone: a `test_zz_notgut.gd` extending Node with an
      allowlist entry for its `Ignoring script` line, and a test printing a fake summary and
      quitting. Each is refused at the GUT step, naming the counts; record the lines.
      - does NOT prove: every way a GUT run can be cut short.
- [ ] Mutations, each failing a named pinned test, recorded:
      - main.gd's start at the bounds' corner, at the lowest vertex, or both;
      - the axes check reduced to the east step, or to the north step.
      - does NOT prove: anything about the look.
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that it renders or looks right.

## Forbidden

Changing `main.gd`, `building_chunks.gd`, the allowlist's lines or a pinned file; any
pipeline module (M3-01).

## Findings (executor writes)

Lane builder B (a wave-1 builder session of the M3 orchestrator), 2026-10-14/15, on `main`
at `2aba135`. Nothing outside the Scope was touched; `tools/gate_allowlist.txt` is
unchanged (no entry was needed).

1. **Pinned copies.** The six files of `docs/briefs/pinning/M3-02/` were copied one by one
   (`cp -r … .` was refused by the sandbox's classifier as a bulk overwrite; the only live file
   it replaces is `test_scene_placement.gd`, saved first). `cmp` with the pinned files:
   identical before the gate and before the commit. The two `.uid` files were written by
   Godot's first run and are staged.
2. **Before the fix** (the pinned files against the unmodified tools and `terrain_grid.gd`):
   `test_gate_gut_run.py` **12 failed** of 16, `test_export_checks.py` **5 failed** of 6,
   `test_terrain_grid_world.gd` **2 failed** of 3; `test_scene_placement.gd` 5/5 and
   `test_building_chunks_axes.gd` 4/4 pass, as designed (they close test gaps). Exactly design's
   counts. After: 16/16, 6/6, 3/3.
3. **Standard gate** (`tools/gate.sh > gate.log && git commit`), exit 0: `uv lock --check`;
   pytest **766 passed**, 4 deselected (743 before + the 23 tests of the two pinned pytest
   files); ruff check and format; `manifest`; Godot `4.6.3.stable.official.7d41c59c4`,
   GUT `version="9.6.1"`; import and parse check; GUT **25 scripts, 117 tests, 117 passing,
   2830 asserts** with `GUT version:  9.6.1` and `Scripts 25` equal to the 25 `test_*.gd` files
   on disk; gdlint clean; gdformat 34 files unchanged; 85 `ERROR` lines in the log, all
   excepted by the existing entries (the gate would fail on one that is not).
4. **What changed, per finding.**
   - *V1-G-01:* `unexcused_lines` prints a line matching `Ignoring script|Failed to load
     script` (`NOT_RUN_LINES`) before it looks at any entry, global or scoped. The optional
     half is built too: `read_allowlist` refuses an entry whose text holds either phrase, so
     such an entry now fails the gate at the first scanned step (the import) with its own message.
     The scan covers the entries the refusal cannot see (`res://tests/… because it does not
     extend GutTest`, `script "res://…" with error`).
   - *V1-G-05:* `gut_run` reads `Scripts <n>` after the last `= Run Summary` and requires it to
     equal `find game/tests -name '.?*' -prune -o -type f -name 'test_*.gd' -print | wc -l`
     (hidden files and folders left out, as GUT's `_get_files` leaves them out, `gut.gd:957`).
     It names both numbers, or says the summary has no count. When the allowlist was refused
     nothing ran, and `gut_run` returns at once instead of adding messages about a missing log.
   - *V1-G-06:* `gut_run` requires the line `GUT version:  9.6.1` exactly (`grep -x -F`) and
     names the `GUT version:` line it found.
   - *V1-G-07:* `run_scanned` (gate.sh) and `clean_output` (export.sh) remove a CR at a line's
     end after the ANSI codes (`sed -e … -e 's/\r$//'`).
   - *V1-G-08:* `TerrainGrid._check_world` says `(its origin or height offset differs)`, split
     over two lines as BuildingChunks' is.
   - *V1-G-02, V1-G-03:* test-only; `main.gd` and `building_chunks.gd` are untouched.
   - *M2-02 Findings 9:* `export.sh` checks `uname -s` = Linux before step 1, so on another
     system it downloads, installs and exports nothing; its message names the system and
     Linux. The check that was in step 6 is gone (it could not be reached any more), and so is
     the MINGW/MSYS/CYGWIN branch of `templates_dir`, which only the other systems could reach
     (my reading of the brief's decision 7, not its words: a dead branch whose comment claimed
     Windows support would be a Hard Rule 2 breach); the header comments say so. Nothing else
     changed in `export.sh`.
5. **Real gate, in a scratch clone** (`git clone`, so no copied venv, H22; the probes
   staged, which `test_repo_tracked.py` requires), logs kept in the session's scratchpad:
   - *A, an ignored script.* `game/tests/test_zz_notgut.gd` extending Node, 26 files on disk.
     With the entry `Ignoring script res://tests/test_zz_notgut.gd # …`: refused when the
     allowlist is read, `== gate: FAILED at step: godot import` (exit 1). With the entry
     `res://tests/test_zz_notgut.gd because it does not extend GutTest # …` (no phrase, so only
     the scan can tell): `FAILED at step: gut`, with the lines `[WARNING]:  Ignoring script
     res://tests/test_zz_notgut.gd because it does not extend GutTest` and `GUT counted 25 test
     scripts, game/tests holds 26 test_*.gd files: a script was ignored, not loaded or is an inner
     class, or the run did not reach its summary`.
   - *B, a fake summary.* `test_zz_fake.gd` printing `= Run Summary` and `---- All tests
     passed! ----`, then `get_tree().quit()`: `FAILED at step: gut` with `GUT's last run summary
     has no 'Scripts <n>' line: it counted no test scripts (26 test_*.gd files under
     game/tests)` (the run printed the fake summary and pass line and no `Scripts` line). The
     unmodified gate's verdict on this probe is design's measurement (exit 0, no allowlist
     entry); I did not repeat it, since a comparison run through the pinned pytest files cannot
     use the old script.
6. **Mutations**, each in the scratch clone, undone with `git apply -R` of its saved diff
   (nothing in the working tree was mutated); controls first: `test_scene_placement.gd` 5/5, M2-08's
   old copy of it 5/5, `test_building_chunks_axes.gd` 4/4, `test_building_chunks_world.gd` 5/5.
   Harm each reproduces: the owner's first view starts off the village (over a corner of the
   buildings' bounds, or at the height of their lowest vertex) or the world's axes are accepted
   when two of three are wrong (a mirrored or turned world places buildings elsewhere).
   - `main.gd` start at the bounds' corner (`bounds.position.x/z` for `centre.x/z`):
     `test_scene_placement.gd::test_without_terrain_the_camera_starts_over_the_buildings`
     fails on "over the centre of the bounds" (x: 895.48 against 985.20; z: −26.42 against 14.70).
     M2-08's old copy passes (5/5).
   - at the lowest vertex (`bounds.position.y` for `bounds.end.y`): the same test fails on
     "START_ABOVE_M above the highest vertex" (1153.61 against 1196.09). Old copy 5/5.
   - both: the same test, three assertions. Old copy 5/5.
   - the axes check reduced to the east step: `test_building_chunks_axes.gd::
     test_east_kept_north_and_up_turned_is_refused` fails (the check returns `""`); the old
     `test_building_chunks_world.gd` passes (5/5).
   - reduced to the north step: `…::test_north_kept_east_and_up_turned_is_refused` fails; the
     old test passes (5/5).
   - reduced to the up step (extra): `…::test_up_kept_east_and_north_turned_is_refused` fails;
     the old test fails here too.
7. **Left as it was, said aloud.** `test_zzold_placement.gd`, the probes and their logs live
   only in the scratch clone and the session's scratchpad. The gate's two checks that I added
   read GUT's text, so they prove what GUT printed, not that every script ran: a test that
   prints both a fake summary and a `Scripts <n>` line equal to the count, then quits, still
   passes (not measured, not closed). The CR handling was tested on simulated CR LF output only.
8. **Rebase and the combined head.** `main` moved twice while this brief ran: lane G's
   M3-12 (`fb30619`, which appended one line to `tools/gate_allowlist.txt`, left in place,
   this brief adds none) and its docs commit. The standard gate was re-run on the tree with
   `fb30619` under this brief's changes before the commit: exit 0, pytest 766 passed, GUT
   **29 scripts** (25 + M3-12's four) equal to the 29 `test_*.gd` files, `GUT version:  9.6.1`.
   The implementation commit is `d67e17e` on `origin/main`.
