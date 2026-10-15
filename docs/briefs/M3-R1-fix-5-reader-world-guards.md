# Brief: M3-R1-fix-5 — The readers' world guard: type-safe compares and the origin tests
Status: DONE (8cbb5c1)

Written by the build orchestrator from review findings M3-R1-G-03 and, for its Hard Rule 4
part, M3-R1-G-04 (`docs/reviews/M3-R1-game.md`; both graded P2 by the game lens, taken in
because they lie in Tier-1 territory: WORKFLOW §Review policy, "a finding in Tier-1 territory
moves its area to Tier 1"), executed by one fresh builder session under
`docs/roles/BUILD.md`. Lane K of the fix round.

## Goal

The check that a block was built for the manifest's own world, Hard Rule 4's detector in
the game, can no longer fall silent. Two defects:

1. **A wrong-typed manifest field makes a `!=` guard a runtime error that accepts the block**
   (G-03). In GDScript, `!=` between a `float` read from JSON and a `String` or `Dictionary`
   constant is a runtime error ("Invalid operands … in operator '!='"), the check that holds
   it does not refuse, and the reader returns a grid. The lens's fuzz run found 21 accepted
   cases, among them the top-level `world_sha256` set to a number: all six readers accept it
   (`PhotoGrid`, `SurfaceGrid`, `TreeChunks`, `BuildingRoofs`, and the pre-arc `TerrainGrid`
   and `BuildingChunks`), six SCRIPT ERROR lines, all startup lines, no error panel.
2. **The photo's and the surfaces' origin and height-offset guard has no test** (G-04):
   `photo_grid.gd` (the `origin.get("e") != world.origin_e or …` check, about line 140) and
   `surface_grid.gd` (about line 152), made never true, leave every game test green, and the
   reader then accepts a manifest whose `world.origin_lv95.e` is 1000 m further east.
   CLAUDE.md: "the code that guards Hard Rules 4 and 5 … MUST have tests, mutation-proved".

## Read first, in order

1. `docs/reviews/M3-R1-game.md`: findings G-03 and G-04 in full (the fuzz run, the list of
   21 cases, the world-guard probe), and G-12 (known, by design, not yours).
2. `game/scripts/terrain/photo_grid.gd`, `surface_grid.gd`, `terrain_grid.gd`,
   `game/scripts/trees/tree_chunks.gd`, `game/scripts/buildings/building_roofs.gd`,
   `building_chunks.gd`, `game/scripts/world/world_config.gd`.
3. The readers' tests: `test_photo_grid.gd`, `test_surface_grid.gd`, `test_tree_chunks.gd`,
   `test_m3_11_tree_chunks_checks.gd`, `test_building_roofs.gd`, `test_m3_12_roofs_checks.gd`,
   `test_terrain_grid*.gd`, `test_building_chunks*.gd`, `test_scene_placement.gd` (how it
   gives BuildingChunks another manifest's WorldConfig).
4. brain.md H9 (Godot's JSON reads every number as a float), lessons 5, 9, 34.

## Decisions already made

1. **One helper, every site.** A static comparison that is false-safe on type, in one place
   (the lens's sketch: `_differs(value, expected)`: `typeof(value) != typeof(expected) or
   value != expected`; where it lives is yours, said in Findings), used at every site G-03
   names: `world_sha256` in the six readers; `format` (`photo_grid.gd`, `tree_chunks.gd`,
   `building_roofs.gd`); `source.dataset` (`photo_grid.gd`, `surface_grid.gd`); `classes`
   (`surface_grid.gd`); `area` and the chunk entries' `tile` and `source.buildings`
   (`building_roofs.gd`); and any other `!=` between a manifest value and a constant that you
   find by grep in the six readers (a pattern, lesson 9: walk the writers of the guard, not
   the lens's list). A wrong type is refused with the reader's one `push_error` naming the
   field, as a wrong value is, and a null result.
2. **One test per site**, each with a needle (the problem's own words), asserting exactly one
   `push_error` and a null result and no SCRIPT ERROR: the 21 cases of the fuzz run, by
   field.
3. **The world guard of PhotoGrid and SurfaceGrid is tested with asymmetric data** (lesson
   34): another manifest's WorldConfig differing in `origin_e` only, in `origin_n` only, in
   `height_offset` only (each by a different, non-symmetric amount), as `test_scene_placement.gd`
   does for the buildings; each case's needle is the world guard's own words ("the WorldConfig
   given was not read from this manifest"), so that removing the guard fails it and a later
   check cannot stand in (the lens's finding is exactly that one did not). PhotoGrid's and
   SurfaceGrid's rotated-world refusal is already pinned (the lens: it dies); do not touch it.
4. **The readers' refusals log on purpose**: each new refusing test needs a scoped
   `tools/gate_allowlist.txt` line (append-only; keep every line; a text of 12 characters at
   least; the scoped form `<text> @ res://tests/<script>.gd # reason`).
5. Not yours (residue, the board): G-04's other survivors (the folder-escape, `cell_m`,
   the digests' shape, the tile and count checks of chunk order) and G-12. If one of your
   helper's sites is one of them, it is yours; say which in Findings.

## Scope — files you may touch

- `game/scripts/terrain/photo_grid.gd`, `surface_grid.gd`, `terrain_grid.gd`;
  `game/scripts/trees/tree_chunks.gd`; `game/scripts/buildings/building_roofs.gd`,
  `building_chunks.gd`; one new helper script under `game/scripts/world/` (with its `.uid`),
  unless an existing shared script is the right home.
- The readers' test files listed above, new test files named `test_m3_r1_fix5_*`, and
  `tools/gate_allowlist.txt` (appended lines only).
- This brief file (Status and Findings).

## Depends on

None. (M3-R1-fix-1 and M3-R1-fix-4 have landed: rebase onto them; they touched only tests and
the tree shader.)

## Done when (gates)

- [ ] The fuzz cases of G-03 are refused, one by one, with exactly one named `push_error`, a
      null result and no SCRIPT ERROR, by the new tests; a numeric `world_sha256` is refused by
      all six readers. Mutation: put the plain `!=` back at any one site; that site's test
      fails and names the field (record the failing output of every site, saved diffs undone
      with `git apply -R`).
      - does NOT prove: that no other manifest field of a wrong type is mishandled (a field no
        reader reads), nor that the pre-arc readers' other checks are right.
- [ ] The world guard of `PhotoGrid` and of `SurfaceGrid`: made never true (`if false and (`),
      each of the three differences (origin e, origin n, height offset) fails a named test
      whose needle is the guard's words; record all six runs.
      - does NOT prove: that the manifest's `world` copy is bound to `config/world.json` at read
        time (G-12, by design: the pipeline's step 1 writes it and its tests pin it).
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`; GUT's script count equals the
      `test_*.gd` files; new files are `git add`ed first (test_repo_tracked), `.uid` files
      included.
      - does NOT prove: that it renders or looks right.

## Forbidden

A change to what a reader accepts that is not a type refusal (no relaxed or tightened value
check); the shaders; the pipeline; a version bump; a new dependency; a model's name or id
anywhere in the repository.

## Findings (executor writes)

1. **The change** (two commits on `main`: `2c70fd7` the helper, the sites and two test files, `8cbb5c1`
   the helper's own test; no pipeline, shader, scene or `main.gd` line moved):
   - **Home of the helper:** a new script, `game/scripts/world/manifest_value.gd` (+ `.uid`),
     `class_name ManifestValue`, one static `differs(value, expected) -> bool`: true when the two
     have another type, or the same type and another value; an int and a float are one type
     (`5 != 5.0` is false in GDScript and Godot's JSON reads every number as a float, so what a
     reader accepted before it accepts now); never a runtime error. A new script and not a static
     of `TerrainGrid` because five other readers would call a sibling reader for a comparison that
     belongs to none of them.
   - **The 31 lines it replaces a plain `!=` on**, in the six readers (the brief's pattern walk,
     lesson 9; `file:line` at `8cbb5c1`):
     `world_sha256`: `terrain_grid.gd:93`, `building_chunks.gd:79`, `photo_grid.gd:121`,
     `surface_grid.gd:133`, `tree_chunks.gd:96`, `building_roofs.gd:87` ·
     the world guard's three terms (origin e, origin n, height offset) in four readers, the same
     twelve-line shape: `terrain_grid.gd:113-115`, `building_chunks.gd:102-104`,
     `photo_grid.gd:141-143`, `surface_grid.gd:153-155` (TreeChunks and BuildingRoofs go through
     `BuildingChunks._check_world`) ·
     `format`: `terrain_grid.gd:140`, `building_chunks.gd:126`, `photo_grid.gd:168`,
     `surface_grid.gd:199`, `tree_chunks.gd:137`, `building_roofs.gd:118` ·
     `dataset`: `photo_grid.gd:209`, `surface_grid.gd:235`, `tree_chunks.gd:189` ·
     `classes`: `surface_grid.gd:201` · `building_roofs.gd`: `area` :120, `source.buildings` :148,
     the chunk entry's `tile` :215.
     Beyond G-03's list: the terrain's and the buildings' `format`, the world guard's twelve terms
     (reachable by any caller that gives a reader another manifest's WorldConfig, as the tests
     do; the main scene's own WorldConfig refuses a non-number first).
   - **The other `!=`, `==`, `<`, `>`, `<=`, `>=` of the six readers, read one by one and left:**
     each is behind an earlier `typeof`/`_is_number`/`_is_text`/`_is_sha256`/`_is_count` test
     (a digest's `to_lower()`, the counts, `float(count) != floorf(count)`, the sorted key
     arrays), or compares values the reader computed (Vector3 axes, sizes, `fit_columns`).
     Outside the six: `world_config.gd:91,99,101` (guarded by `_is_number` and a Dictionary
     test) and `building_loader.gd:80` (both sides come from readers that validated them).
2. **What Godot does, measured** (probe with `Expression`, which runs `Variant::evaluate` as the
   VM does for untyped operands; twelve JSON-shaped samples in every pair): `null` compares with
   every type; an int and a float compare; a `bool`, `String`, `Array` or `Dictionary` against
   any other type (a `float` against a `String`, a `String` against a `Dictionary`, an `Array`
   against a `Dictionary`, a `bool` against a number) is "Invalid operands … in operator '!='".
   Two Arrays or two Dictionaries compare without an error whatever their elements hold (nested
   `[1.0]` against `["x"]`, `{"a": {"b": 1.0}}` against `{"a": "x"}` give true), so the top-level
   type test is all the helper needs. A probe that hit the error in a SceneTree script's
   `_initialize` hung with no exit (brain.md H25, met again; the matrix ran under `Expression`).
   Candidate for brain.md H9 at the close (not touched: out of Scope).
3. **The tests** (3 new files, 18 tests; the allowlist gets seven scoped lines, none removed):
   - `test_m3_r1_fix5_type_guards.gd` (8 tests, 942 asserts): the complete test world
     (`complete_world.gd`) with one field changed, read by the reader that checks it; each case
     asserts a null result, **exactly one** `push_error` naming the manifest and saying the
     check's own words, and no other error (a SCRIPT ERROR is one; GUT would also fail the test
     on it). Cases: a control (every reader reads the unchanged world); the top-level
     `world_sha256` = 5.0, `true`, `[]`, `{}`, `null` in all six readers (G-03's headline); the
     block's own `world_sha256` of those types; `format` of those types and `"png"` in six
     readers; `dataset` (photo, surfaces, and each of the four `trees.source` blocks); the class
     table (`[]`, 5.0, `true`, `null`, text, `{}`, a shorter table, a table with `4: 4.0`, a table
     with a sixth class); `roofs.area`, `roofs.chunks[0].tile` (needle: "the buildings' chunk 0 is
     2601-1199") and `roofs.source.buildings`; and the world guard's e, n and height offset
     as `"x"`, `true`, `[]`, `{}` against a WorldConfig read from another manifest, in all six
     readers. All 21 of the fuzz run's accepted cases are in it (the 6 `world_sha256` readers,
     buildings/surfaces/trees/roofs `format`, photo and surfaces `dataset`, the four trees
     `dataset`s, `classes`, `roofs.area`, `roofs.source.buildings`, the roofs chunk `tile`: its
     [0] and [5] are one site); 232 refusal cases in all.
   - `test_m3_r1_fix5_world_guard.gd` (7 tests, 35 asserts): PhotoGrid and SurfaceGrid given
     another manifest's WorldConfig (the fixture's world block with one field moved: east
     +1000 m, north +37.5 m, height offset +0.25 m, each alone), needle "the WorldConfig given
     was not read from this manifest"; the control: their own WorldConfig, and a copy of its
     block, are accepted (a guard comparing e with n, or refusing everything, fails it).
   - `test_m3_r1_fix5_manifest_value.gd` (3 tests, 10 asserts): nineteen values in every pair
     (361), equal ones do not differ, any other pair does, `5` and `5.0` are one, `5.0` and
     `"5.0"` and `1.0` and `true` differ, and no pair is a runtime error.
4. **Mutations** (a throwaway `git clone` of the repository with this work committed locally as
   the baseline; each mutation one exact string edit, `git diff` saved, the named script run, the
   diff undone with `git apply -R`, `git diff --quiet` clean after every one; 62 runs in four
   groups and the whole-reader run below, none committed; the scripts and logs are in the scratchpad, which dies with the container).
   Baseline: each named script green. **The reproduction of G-03 as a whole:** the three
   reader folders put back at `c73f6c0` (before this brief), `type_guards` run: 6 of 8 tests
   fail (the two that pass are the control and the block-level hash, which `typeof` already
   refused), 176 `SCRIPT ERROR` lines.
   - **A. The plain `!=` back at one site** (31 runs, `test_m3_r1_fix5_type_guards`; harm each
     reproduces: a damaged or newer manifest read, no panel, only a SCRIPT ERROR in the log):

     | sites | failing test | what failed |
     |---|---|---|
     | `world_sha256` in each of the six readers (6 runs) | `test_a_world_sha256_of_the_wrong_type_is_refused_by_every_reader` | that reader's four cases (5.0, `true`, `[]`, `{}`); four `SCRIPT ERROR: Invalid operands 'String' and 'float'/'bool'/'Array'/'Dictionary' in operator '!='` |
     | `format` in each of the six readers (6) | `test_a_format_of_the_wrong_type_or_value_is_refused` | that reader's four cases, four SCRIPT ERROR lines |
     | `dataset` in photo, surfaces, trees (3) | `test_a_dataset_of_the_wrong_type_or_value_is_refused` | that reader's cases (trees: all four blocks); 8, 8 and 20 SCRIPT ERROR lines: the wrong type also reaches `dataset = source["dataset"]`, a String variable |
     | `classes` (1) | `test_a_class_table_of_the_wrong_type_or_value_is_refused` | `[]`, 5.0, `true`, `"classes"` |
     | roofs `area`, `source.buildings`, `tile` (3) | `test_roofs_of_the_wrong_area_tile_or_buildings_source_are_refused` | four cases each (`source.buildings`: 5.0, `true`, `[]`, `"swissbuildings3d"`) |
     | the world guard's e, n and height offset in TerrainGrid, PhotoGrid, SurfaceGrid (9) | `test_an_origin_or_height_offset_of_the_wrong_type_is_refused_by_every_reader` | that reader's four cases of that field |
     | the same three terms in `BuildingChunks._check_world` (3) | the same | twelve cases: BuildingChunks, TreeChunks and BuildingRoofs, which share it |

   - **B. G-04's world guard** (`test_m3_r1_fix5_world_guard`, 14 runs), made never true (`if (` →
     `if false and (` at `photo_grid.gd:140` and `surface_grid.gd:152`): the six runs, each
     difference alone, `-gunit_test_name=` one test per run, `---- 1 failing tests ----` each
     time, the assert "one push_error names <manifest> and says 'the WorldConfig given was not
     read from this manifest'" (and "a null result": the reader returned a grid) failing:

     | reader | east +1000 m | north +37.5 m | height offset +0.25 m |
     |---|---|---|---|
     | PhotoGrid | `test_photo_grid_refuses_another_east_origin` fails | `…_another_north_origin` fails | `…_another_height_offset` fails |
     | SurfaceGrid | `test_surface_grid_refuses_another_east_origin` fails | `…_another_north_origin` fails | `…_another_height_offset` fails |

     Whole-guard runs: 3 failing tests of 7 each (the control passes). Each term alone replaced
     by `false` (6 runs): exactly the one test of that difference fails.
   - **C. G-04's survivors that are this helper's sites, the guard made never true**
     (`false and ` before the `differs` call; 13 runs, `type_guards`): `format` ×6 (incl.
     `photo_grid.gd:168`), `dataset` ×3 (`:209`, `surface_grid.gd:235`, `tree_chunks.gd:189`),
     `classes` (`:201`), roofs `area`, `source.buildings` and `tile` (`:215`): each fails its
     named test above on every case, the wrong **values** (`"png"`, `"swissalti3d"`,
     `"swisstlm3d"`, `"elsewhere"`, `"2999-1199"`, a changed class table, another buildings
     source) among them. The first try of `dataset` at `tree_chunks.gd:189` put `false and`
     before an `or`, a parse error of the reader: one SCRIPT ERROR line, exit 0, no test
     counted and no `----` result line (brain.md H2, H3); caught by the missing result
     line, redone with `or false and`.
   - **D. The helper** (`test_m3_r1_fix5_manifest_value`, 4 runs): its type test never true
     (2 tests fail, 258 SCRIPT ERROR lines); an int and a float made two types (`5 is 5.0`
     fails); the same type never differing (`5 is not 6.0` fails); the comparison done as text
     (3 tests fail: `5.0` against `"5.0"`, `1.0` against `true`, `5` against `5.0`).
5. **G-04's other survivors, as the brief's decision 5 asked.** Mine, now pinned: `photo_grid.gd:168`
   (format), `:209` (dataset), `surface_grid.gd:201` (classes), `:235` (dataset),
   `building_roofs.gd:215` (the tile of chunk *i*; see C), and the world guard (B). Not mine,
   untouched, still residue: the folder-escape (`_is_plain_relative_path`), `cell_m`, the
   digests' shape, the count and sum checks of the roofs chunk order, `photo_grid.gd:206-209`'s
   and `surface_grid.gd:233`'s source-text checks (they are `typeof` tests, not helper sites),
   `building_loader.gd:80,223`, G-12. The existing chunk-reversal test in `test_building_roofs.gd`
   still has no needle; the tile check is pinned by the wrong-tile case instead (C).
6. **Observation, not changed** (a message, not what a reader accepts; no design authority):
   PhotoGrid's and SurfaceGrid's world guard says "(its origin differs)" when only the height
   offset differs; TerrainGrid's and BuildingChunks' say "(its origin or height offset differs)"
   after M3-02 (V1-G-08). The new tests' needle is the shared first half, so a rewording will not
   break them. For the board's residue.
7. **Traps met:** a test helper named `_set` is `Object._set`'s name: `Parse Error: The function
   signature doesn't match the parent` and GUT skips the script (`Nothing was run`, lesson 40's
   trap); gdlint's `max-returns` (6) refused a `match` with eight `return`s (the first gate run
   failed at gdlint, 46 scripts green; fixed before any commit). The lens's fuzz scripts
   (`fuzz_gen.py`, `fuzz_run.gd`) were in another container's scratchpad and not available: the
   21 cases were rebuilt by hand from the report's list, and the 1243-case fuzz was not re-run.
8. **Gates:** baseline at `c73f6c0` green (4 min 18 s). The standard gate on `2c70fd7` and again
   on `8cbb5c1` (each `tools/gate.sh > log && git commit …`): all steps passed; GUT `Scripts 46`
   then `47` = the `test_*.gd` files, `---- All tests passed! ----`, gdlint and `gdformat --check`
   clean; the new files and their `.uid` files `git add`ed before the gate. `main` had not moved
   at the rebase. The allowlist: seven lines appended (`<Reader>: user://test_ @
   res://tests/test_m3_r1_fix5_type_guards.gd` ×6 and `the WorldConfig given was not read from
   this manifest @ res://tests/test_m3_r1_fix5_world_guard.gd`), each with its reason; every
   earlier line kept.
9. **Does NOT prove** (the brief's lines, kept): that no other manifest field of a wrong type is
   mishandled (a field no reader reads; the fuzz's 1243 cases were not re-run); that the pre-arc
   readers' other checks are right; that the manifest's `world` copy is bound to
   `config/world.json` at read time (G-12, by design); that a refusal of a wrong-typed manifest
   reaches the error panel in the started game (the readers' refusals are collected as before;
   no main-scene test was added); that it renders or looks right.
