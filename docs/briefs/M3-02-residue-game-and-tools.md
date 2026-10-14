# Brief: M3-02 — M2's residue, the game and the tools
Status: OPEN

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
  (pinned, new), and your own tests under names M3-01 does not use.

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
