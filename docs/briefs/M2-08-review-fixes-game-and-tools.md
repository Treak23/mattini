# Brief: M2-08 — M2 R1's fixes, the game and tools half
Status: DONE (20c5a80)

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

- [x] The pinned copies are in place and byte-identical (`cmp`).
      (Findings 1: both identical before each commit; 5/5 and 2/2 in the gate.)
      - does NOT prove: that the pinned tests are the right tests.
- [x] Mutations (Findings: both runs of each):
      (Findings 4: runs 1 to 5 each fail as listed, 3 and 4 also isolated from the other
      scans; the unmutated run is Findings 2.)
      - the Buildings node shifted 1 km (the review's): the placement test fails;
      - the walls unshaded, back faces drawn and roofs black (the review's M): the
        materials test fails;
      - a test script prints `---- All tests passed! ----` and quits: the gate fails;
      - a one-word allowlist entry `ERROR # x`: the gate refuses the allowlist;
      - `plugin.cfg`'s version changed: the gate refuses.
      - does NOT prove: that no other transform or material change slips through.
- [x] `tools/export.sh` passes on the real village (terrain and buildings built from the
      scratch inputs), and the `.pck` holds no file under `tools/` (its `Storing File`
      lines).
      (Findings 5: exit 0, 78 `Storing File` lines per preset, none under `res://tools/`;
      `.pck` 99'405'400 bytes; both startup lines.)
      - does NOT prove: that the Windows build starts.
- [x] Standard gate: `tools/gate.sh > gate.log && git commit …`
      (Findings 2: `20c5a80`, chained on exit 0.)
      - does NOT prove: that it renders or looks right.

## Forbidden

A version bump; a change to the look's colours or to any fixture's bytes; switching GUT's
error tracking off.

## Findings (executor writes)

Executor agent of the one M2 session, 2026-09-25, in its own worktree and branch (the
owner's run mode; nothing synced or pushed). The worktree started at `63816ac` (main);
`git merge --ff-only 2f7636a` fast-forwarded it to the brief's commit. Implementation
commit `20c5a80` on top of `2f7636a`. The real village was built into the worktree's
git-ignored `game/assets/generated/` from the scratch download (`mattini terrain --raw`:
`b6334c1f…`, the value `config/terrain.json` expects; `mattini buildings --raw`: 1486
buildings in 6 chunks, 92594 vertices, 178910 triangles, 3258048 bytes, the SHA-256s
`config/buildings.json` expects); nothing of it is committed.

1. **Pinned copies:** `cp -r docs/briefs/pinning/M2-08/. .` placed
   `game/tests/test_scene_placement.gd` and `game/tests/test_building_materials.gd`; `cmp`
   with the pinned files: identical before the implementation commit and before this one.
   In the gate: `test_scene_placement.gd` 5/5, `test_building_materials.gd` 2/2.
2. **Standard gate** (`tools/gate.sh > gate-M2-08.log 2>&1 && git commit`), exit 0 for
   `20c5a80`: `uv lock --check`; pytest **662 passed**, 4 deselected, 79 warnings (as
   before); ruff check and format; `manifest`; Godot `4.6.3.stable.official.7d41c59c4` and
   `GUT: game/addons/gut/plugin.cfg: version="9.6.1"`; import and parse check; GUT **23
   scripts, 110 tests, 110 passing, 2800 asserts**, `---- All tests passed! ----` after
   `= Run Summary`; gdlint clean; gdformat 32 files unchanged; `== gate: all steps passed`.
   83 `ERROR` lines, all in the GUT step and all excepted; four come from the new scripts:
   the pinned `test_scene_placement.gd`'s three (two `TerrainGrid: … no terrain has been
   built`, one `BuildingChunks: … the WorldConfig given was not read from this manifest
   (its origin or height offset differs)`, each under its new scoped entry) and
   `test_building_chunks_world.gd`'s one `WorldConfig: user://test_…` (the mirrored-axes
   case below, under the existing global entry).
3. **What changed, per finding.**
   - *P-01:* `complete_world.gd`'s box has `BOX_FLOOR = Vector3(1024.0, 603.0, 15.5)` and
     `BOX_HEIGHT := 6.0`. The fixture's ground over the box's footprint, read from
     `fixture.f32` (rows 10–14, columns 18–22): 604.157 to 606.657 m, 605.407 m at its
     middle, so between the floor (603) and the roof (609). No other test depended on the
     old box.
   - *P-04:* `BuildingChunks._check_world(world, path, block)` compares the origin and the
     height offset with the manifest's world block (as before), then reads
     `WorldConfig.from_manifest(path)` and compares `to_local` of one metre east, north
     and up from the origin, exactly, for the two configs; the header and the class header
     say so. `world_config.gd` is outside the Scope and has no way to build a WorldConfig
     from the already parsed block, so the manifest is read a second time; when
     WorldConfig refuses that world block itself, its own push_error comes before
     BuildingChunks' (header says so). Tested two ways: the pinned
     `test_a_world_config_from_another_manifest_is_refused` through `from_manifest`, and
     my `test_building_chunks_world.gd` (5 tests) calling `_check_world` itself with
     WorldConfigs read from copies of the buildings fixture's manifest that differ in one
     field each: the origin (+1 m east), the height offset (+1 m), the axes (x = +n, y =
     +h, z = +e, a quarter turn with the same origin and offset, which only the axes
     comparison can tell apart), and a manifest whose world block is mirrored (x = −e),
     which WorldConfig refuses. Calling the function directly returns the text without an
     `ERROR` line, so no allowlist entry beyond the brief's two was needed.
   - *G-01:* nothing to change in the code: the materials already have the look the pinned
     test reads (it passes on the unchanged `.tres` files; mutation 2 proves it can fail).
   - *G-02:* `main.gd`'s `_load_world`, when TerrainGrid refused and BuildingChunks
     accepted, calls `_start_view_over(node)`: the union of every chunk mesh's AABB through
     its global transform, the camera `START_ABOVE_M` above its top (the highest vertex),
     over its centre, facing `START_BEARING_DEG`, `START_PITCH_DOWN_DEG` down (the shared
     `_start_view_at`). With neither terrain nor buildings the camera stays at the scene's
     origin; the header says each case. On the buildings fixture: highest vertex
     1046.09 m (local), camera 150 m above it.
   - *G-03:* see item 6.
   - *G-04:* the Godot-version step also reads `game/addons/gut/plugin.cfg`'s `version=`
     line and requires it to be exactly `version="9.6.1"`, naming the line it found (or
     "no version line").
   - *G-05:* `read_allowlist` refuses a text shorter than 12 characters or equal to a scan
     prefix, for global and scoped entries. Two readings of the brief's words, both
     stricter: the length is measured with the spaces at the text's ends removed (they add
     no specificity), and the prefix comparison also ignores a colon and spaces after the
     prefix, since Godot prints `SCRIPT ERROR: ` and a 13-character `SCRIPT ERROR:` would
     otherwise pass and match every SCRIPT ERROR line. A scratch harness running the
     gate's own `read_allowlist` on 13 entries: `ERROR`, `SCRIPT ERROR`, `SCRIPT ERROR:`,
     `  SCRIPT ERROR:  `, `[ERROR]:`, `ERROR:` plus spaces, `short text`, `11 chars ab`
     and a scoped `SCRIPT ERROR @ res://tests/test_scene_placement.gd` refused;
     `exactly12chr`, `ERROR: Something`, `WorldConfig: user://test_` and the new scoped
     entry accepted; the live allowlist accepted (2 global, 6 scoped).
   - *M2-02's check:* the GUT step also requires a `= Run Summary` line before GUT's last
     `---- ` line (an awk over the cleaned output), with its own message.
   - *G-06:* both presets' `exclude_filter` is `tests/*, addons/gut/*, tools/*`, pinned
     exactly by `test_release_settings.gd`.
   - *G-07:* `tools/shot.sh`'s and `shot.gd`'s headers: a six-field view fails when the
     terrain is refused (the whole manifest or only its terrain block); with only the
     buildings refused it is taken with the panel over the terrain; the `name` view is the
     start view, over the buildings when only the terrain is refused. Measured with a
     terrain-null copy of the real village's manifest (scratch): `start` was written and
     `over,2623906,1096422,60,315,35` failed with `shot: view over: the scene has no
     terrain (see its error panel)`, exit 1, as the header now says.
   - *The allowlist:* the brief's two scoped entries, verbatim, each with a reason:
     `no terrain has been built @ res://tests/test_scene_placement.gd # it opens the main
     scene on the shared buildings fixture, which has no terrain, on purpose (brief
     M2-08)` and `the WorldConfig given was not read from this manifest @
     res://tests/test_scene_placement.gd # it gives BuildingChunks another manifest's
     WorldConfig on purpose (brief M2-08)`. The log shows exactly those three lines inside
     `test_scene_placement.gd`'s window.
4. **Mutation proofs.** Each mutation is a saved diff in the scratch folder
   (`m208_mut/mut-<run>.diff`), applied with `git apply` (a new test file with
   `git apply --index`, since the gate's pytest step refuses an untracked test script),
   run through the full gate (`m208_mut/gate-mut-<run>.log`), then undone with
   `git apply -R` (`--index` for the new files; the `.uid` Godot generated for a scratch
   test removed with it); `git status` after each showed only the brief's work. The
   unmutated run is item 2 (exit 0, 110/110).

   | Run | Mutation | What failed | Owner-visible harm |
   |---|---|---|---|
   | 1 | the review's: `buildings.position = Vector3(1000.0, 0.0, 0.0)` in `BuildingLoader.create` | exit 1 at `gut`, 108/110, 2782/2800: `test_the_buildings_sit_at_the_scene_origin` (`[TRANSFORM3D(… O: (1000.0, 0.0, 0.0))] expected to equal [TRANSFORM3D(… O: (0.0, 0.0, 0.0))]: the Buildings node`, and `chunk 2601-1199`) and `test_every_named_vertex_lies_in_the_scene_where_the_world_config_puts_it` (16 vertices 887.99 to 1000.0 m off, e.g. `[1000.0] expected to be < than [0.0001]: {C45B19E7-…-000000000007} (Kapelle) vertex 0`) | every building 1 km off its terrain with the gate green (Hard Rule 4; P-01) |
   | 2 | the review's M: walls `cull_mode = 2`, `shading_mode = 0`; roofs `albedo_color = Color(0.1, 0.1, 0.1, 1)` | exit 1 at `gut`, 108/110, 2793/2800: `test_every_surface_is_lit_culled_opaque_and_untextured` (`[0] expected to equal [1]: walls: lit`, `[2] expected to equal [0]: walls: back faces culled`, once per chunk with walls, 3 chunks) and `test_the_roofs_are_darker_than_the_walls` (`[0.10000000149012] expected to be > than [0.3]: not near black`) | unlit, double-sided walls and black roofs with the gate green (G-01) |
   | 3 | a new `test_aaa_quit.gd` whose test prints `---- All tests passed! ----`, calls `get_tree().quit(0)` and awaits a frame | exit 1 at `gut`, naming two reasons: the scan's `ERROR: 3 resources still in use at exit` and `== gate: GUT's run summary ('= Run Summary') does not come before its last '---- ' line: the run did not reach GUT's summary`. The last-line check did not fire: the printed line was the last | a test that ends the run early hides every test after it |
   | 3 + 3b + 3c | 3, the exit leak line allowlisted globally (3b), and the new summary check deleted (3c) | nothing: exit 0, `== gate: all steps passed`, GUT ran one script (log lines 213–218). M2-02's check residue reproduced | the same, gate green |
   | 3 + 3b | 3 and 3b, the new check in place | exit 1 at `gut`, only the run-summary message | (the check alone catches it) |
   | 4 | `ERROR # x` added to the allowlist | exit 1 at `godot import`: `gate allowlist entry with a text shorter than 12 characters (too short to be specific): ERROR # x` | one careless line silences every scan (G-05) |
   | 4 + 4e + 4c | 4, a scratch `test_aab_error.gd` whose one passing test logs `push_error("mutation 4: an error line nobody expects")` (handled in GUT, so only the gate's scan can see it), and the new length and prefix checks deleted (4c) | nothing: exit 0, `== gate: all steps passed` with `ERROR: mutation 4: an error line nobody expects` in the log (line 213) | an unexpected engine error passes the gate |
   | 4 + 4e | 4 and 4e, the checks in place | exit 1 at `godot import`, the same refusal | (the checks alone catch it) |
   | 5 | `plugin.cfg`'s `version="9.6.2"` | exit 1 at `godot version`: `== gate: GUT 9.6.1 required (game/addons/gut/plugin.cfg: version="9.6.1"), found: version="9.6.2"` | a GUT whose per-script lines differ re-opens the scoped-window escape (G-04) |
   | 6 (mine) | `_check_world`'s axes comparison never refuses (`if false and given != its`) | exit 1 at `gut`, 109/110: `test_other_axes_are_refused` (`You passed "" and "the WorldConfig given was not read from this manifest"`, and `"axes differ"`) | a turned WorldConfig accepted for buildings placed with the manifest's axes |
   | 7 (mine) | `main.gd` no longer calls `_start_view_over` | exit 1 at `gut`, 109/110: `test_without_terrain_the_camera_starts_over_the_buildings` (`[0.0] expected to be > than [1046.09375]: above the highest building`; `[0.0…] expected to be between [895.481018066406] and [1074.91198730469]: over the buildings (x)`) | G-02: the owner sees sky, the village 1.6 km above |
   | 8 (mine) | the review's P-04: `if true: return ""` first in `_check_world` | exit 1 at `gut`, 105/110: the pinned `test_a_world_config_from_another_manifest_is_refused` (`Expected [<RefCounted#…>(building_chunks.gd)] to be NULL: another world's config is refused`; `one push_error names the manifest`) and four of `test_building_chunks_world.gd` | a WorldConfig from another world accepted silently (P-04) |

   Run 1 did not fail `test_the_box_stands_on_its_terrain`: it reads heights, and the
   shift was 1 km east; a vertical shift would reach it (not run).
5. **tools/export.sh on the real village** (`tools/export.sh > export-M2-08.log 2>&1`, at
   `20c5a80`): exit 0, `== export: done in 20 s`. Step 3 found the templates installed
   (nothing downloaded). 156 `Storing File` lines, 78 per preset (the review counted 80 at
   `88678e2`; `res://tools/shot.gd.remap` and `res://tools/shot.gdc` are gone), none under
   `res://tools/` and none under `res://tests/`. Both `.pck` files **99'405'400 bytes**
   (5'452'200 under the 104'857'600-byte limit), the same SHA-256
   `e92818a58db58e2afaa3885a7577bfc317774b1e79fad231c886e68c03f040fa`;
   `mattini.exe` 104'659'456 bytes. Step 6: `started: mattini 0.1.0: terrain village
   loaded, 4001 x 6001 vertices at 0.5 m` and `started: mattini 0.1.0: buildings village
   loaded, 1486 buildings in 6 chunks, 178910 triangles`. The `.pck`'s bytes do name
   `res://tools/shot.gd` once, inside the stored `res://.godot/uid_cache.bin` (its 9'239
   bytes found in the `.pck` at offsets 99'384'288 to 99'393'527; the path at
   99'393'508): Godot's uid cache lists every script's uid and path, the excluded tests'
   too. A path, not the script.
6. **export.sh's order (G-03), and a surprise.** My first version kept step 1's check and
   ran it again after the rewrite ("both places"). The review's E5 (the buildings'
   `village.json` moved aside, the manifest still holding the block) then failed at step
   2, before any export. But the next export, with `village.json` back, was refused at
   step 1 on the manifest E5's rewrite had left (`buildings: null`), although step 2's
   rewrite would have restored the block. So the check now runs only after the rewrite:
   step 1 rewrites the manifest (`mattini manifest`), step 2 refuses unless the manifest
   step 1 wrote has both blocks, naming the commands; steps 3 to 6 unchanged. That is the
   brief's "after step 2 has rewritten the manifest, and before any export" in the old
   numbering; the old step 1's missing-manifest message goes with it, since the rewrite
   writes the manifest and a block null when its data is missing. Re-measured: E5 fails
   at step 2 (`export: game/assets/generated/manifest.json has no buildings block: run uv
   run --project pipeline python -m mattini download buildings, then uv run --project
   pipeline python -m mattini buildings`), no `build/` folder written; the review saw both
   exports written and a traceback at step 6. `expected_startup_lines`, run from
   `export.sh`'s own text by a scratch harness on the manifest with `buildings: null`:
   exit 1, that message on stderr, nothing on stdout, no traceback.
7. **Follow-up candidates** (not done; each outside the brief's decisions or Scope):
   - The GUT scan's other texts, `Ignoring script` (15 characters) and `Failed to load
     script` (21), pass the new allowlist rule: a global entry equal to either would hide
     every skipped test script (H3) or every script-load error line. Same class as G-05
     (lesson 9); the brief named three prefixes, so only those are refused.
   - The run-summary check is fooled by a test that prints both `= Run Summary` and the
     pass line before quitting; today such a quit also leaves `ERROR: 3 resources still in
     use at exit`, which the scan catches (run 3). A stronger check: every script heading
     closed by its `<n>/<m> passed.` line before the summary.
   - GUT prints its version from `addons/gut/utils.gd:207` (`'9.6.1' # gut_versrion
     (source of truth)`), not from `plugin.cfg`; a vendoring that changed one and not the
     other would pass or fail the gate wrongly. The brief decided `plugin.cfg`.
   - CLAUDE.md's gate paragraph ("refuses … any Godot but 4.6.3") and M2-05's
     does-NOT-prove enumeration (the review asked for the scene transform there) lag;
     both are design's.
8. **Out-of-scope touches:** none. `building_loader.gd`, `world_config.gd`, the materials
   and `plugin.cfg` were touched only by the mutations, each undone.
9. **Evidence outside the gate:** a software screenshot of the real village with the
   terrain refused (`tools/shot.sh`, Compatibility on llvmpipe, scratch only; not
   committed, `docs/briefs/shots/` is outside the Scope): the error panel over white
   buildings in view below it. Evidence of what is drawn, not of the look.
