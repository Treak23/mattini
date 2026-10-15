# Brief: M3-R1-fix-5 — The readers' world guard: type-safe compares and the origin tests
Status: OPEN

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

