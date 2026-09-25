# Brief: M2-08 — M2 R1's fixes, the game and tools half
Status: OPEN

Written in the design realm; executed under `docs/roles/BUILD.md` (in M2 by an Opus agent
of the one M2 session, the owner's word of 2026-09-25, `docs/history/RULINGS.md`).

## Goal

The game and tools findings of review round M2 R1 (`docs/reviews/M2-R1-*.md`) are fixed.

- **Placement in the scene (P-01, P-04):** a test proves that the buildings stand where
  the world config puts them and on their terrain. The reader's world check is tested.
- **The look (G-01):** the buildings' look is tested, as the terrain's clay look is.
- **The camera (G-02):** with the terrain refused, the camera starts over the buildings,
  not 1.6 km below them.
- **The export script (G-03, G-06):**
  - `tools/export.sh` checks the blocks on the manifest it has just rewritten;
  - the export ships no tool;
- **The gate (G-04, G-05, M2-02's check):** the gate refuses a GUT other than 9.6.1, an
  allowlist text that is too short to be specific, and a pass line that a test printed
  itself.
- **Wording (G-07):** `tools/shot.sh` says truly what fails.

## Read first, in order

1. `CLAUDE.md`; `brain.md` §7 H1 to H4, H8, H11.
2. `docs/SPEC.md` §8 *The buildings* (the game part), §10 *M2's game*.
3. `docs/reviews/M2-R1-placement.md` P-01, P-04; `docs/reviews/M2-R1-game.md` G-01 to G-07;
   `docs/briefs/M2-02-terrain-residue-game-and-tools.md`, its check's G-04 note on the
   ROADMAP.
4. `game/scripts/main.gd`, `game/scripts/buildings/`, `game/tests/complete_world.gd`,
   `game/export_presets.cfg`, `tools/gate.sh`, `tools/export.sh`, `tools/shot.sh`.
5. The pinned tests, `docs/briefs/pinning/M2-08/game/tests/`. Design ran them against a
   throwaway implementation of this brief before pinning (5/5 and 2/2 passed; each fails
   without it).

## Decisions already made

- **The test world's box (P-01):** `game/tests/complete_world.gd`'s box stands on its
  terrain.
  - Its floor's corner is `BOX_FLOOR = Vector3(1024.0, 603.0, 15.5)`, and a new
    `const BOX_HEIGHT := 6.0` makes it 2 × 6 × 2 m.
  - The fixture's ground under it is about 605.4 m. Today the box's roof, 601 m, lies 4 m
    under the ground: the helper said "standing" and it was buried.
  - `test_scene_placement.gd` (pinned) checks the ground between floor and roof, the
    Buildings node and the chunk meshes at the identity transform, and every named vertex
    of the buildings fixture at `WorldConfig.to_local` of its LV95 point in the scene.
- **The reader's world check (P-04):** `BuildingChunks._check_world` stays and is tested
  (pinned). Its header says what it compares: the origin and the height offset, the fields
  the positions depend on. The axes are compared too: a WorldConfig read from the
  manifest's own world block and the one given must map one metre east, north and up
  (`to_local` of unit steps from the origin) to the same local vectors.
- **The look (G-01):** `test_building_materials.gd` (pinned) reads, on the meshes the loader
  built:
  - shading per pixel, back faces culled, opaque, no albedo texture and no alpha;
  - the roofs' luminance below the walls' and above 0.3.

  The colours stay the owner's to tune.
- **The camera without terrain (G-02):** when the terrain is refused and the buildings
  load, `main.gd` starts the view over the centre of the buildings' bounds, `START_ABOVE_M`
  above the highest vertex, facing `START_BEARING_DEG`, `START_PITCH_DOWN_DEG` down
  (pinned). Its header says so.
- **export.sh (G-03, G-06):**
  - the checks for both blocks run after step 2 has rewritten the manifest, and before
    any export;
  - `expected_startup_lines` refuses a missing block with step 1's message, not a
    traceback;
  - both presets' `exclude_filter` gains `tools/*`, and the live preset test pins it.
- **The gate (G-04, G-05, M2-02's check):**
  - its Godot-version step also requires GUT 9.6.1 (`game/addons/gut/plugin.cfg`,
    `version="9.6.1"`), naming what it found;
  - an allowlist text (global or scoped) shorter than 12 characters, or equal to a scan
    prefix (`ERROR`, `SCRIPT ERROR`, `[ERROR]`), is refused;
  - the GUT step passes only when GUT's run summary (`= Run Summary`) comes before the
    last `---- ` line, so a test that prints the pass line and quits fails. Prove each
    by mutation (Findings).
- **The allowlist:** two scoped entries for the pinned test's deliberate refusals, measured
  by design: `no terrain has been built @ res://tests/test_scene_placement.gd` and `the
  WorldConfig given was not read from this manifest @ res://tests/test_scene_placement.gd`.
- **tools/shot.sh (G-07):** its header and `shot.gd`'s say that a six-field view fails
  when the terrain is refused, and is taken with the panel over the terrain when only the
  buildings are.

## Scope: files you may touch

`game/scripts/main.gd` · `game/scripts/buildings/building_chunks.gd` · `game/tests/` ·
`game/tools/shot.gd` · `game/export_presets.cfg` · `tools/gate.sh` ·
`tools/gate_allowlist.txt` · `tools/export.sh` · `tools/shot.sh`.

## Depends on

None beyond what is merged. It shares no file with M2-07.

## Done when (gates)

- [ ] The pinned copies are in place and byte-identical (`cmp`).
      - does NOT prove: that the pinned tests are the right tests.
- [ ] Mutations (Findings: both runs of each):
      - the Buildings node shifted 1 km (the review's): the placement test fails;
      - the walls unshaded, back faces drawn and roofs black (the review's M): the
        materials test fails;
      - a test script prints `---- All tests passed! ----` and quits: the gate fails;
      - a one-word allowlist entry `ERROR # x`: the gate refuses the allowlist;
      - `plugin.cfg`'s version changed: the gate refuses.
      - does NOT prove: that no other transform or material change slips through.
- [ ] `tools/export.sh` passes on the real village (terrain and buildings built from the
      scratch inputs), and the `.pck` holds no file under `tools/` (its `Storing File`
      lines).
      - does NOT prove: that the Windows build starts.
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that it renders or looks right.

## Forbidden

A version bump; a change to the look's colours or to any fixture's bytes; switching GUT's
error tracking off.

## Findings (executor writes)
