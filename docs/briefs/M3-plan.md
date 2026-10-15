# M3 — Surfaces and trees: the arc plan

Status: GO (2026-10-14, the owner)

**Base:** the commit that set this status line (its message starts `docs: M3 GO`; `git log
--grep '^docs: M3 GO' -1`). It is the base of integration note 1 and of the review's diff
range.

**The build's model** (the owner's word at the GO, `docs/history/RULINGS.md` 2026-10-14):
every session this arc spawns, the orchestrator's builders, reviewers and any successor
included, passes the model the orchestrator's own spawn prompt names. BUILD.md's "no
model" does not apply to M3; a hand-off prompt carries the model on.

Written by the design realm (`docs/roles/DESIGN.md` §The arc plan); run by one `ultracode
build` orchestrator (`docs/roles/BUILD.md` §The orchestrator). The owner's answers of
2026-10-14 are SPEC §13 rows 29–34 and `docs/history/RULINGS.md`; FB-001 is the arc's
reason, FB-002 is on the board's ideas. Design's working notes, which the pinned tests cite
as "m3-design §N", are `docs/briefs/sketches/m3-design.md` (SPEC and the briefs outrank
them).

## What M3 delivers

Version **0.3.0**: the village in a realistic look made from swisstopo data (SPEC §1, §8,
§10). The 2023 aerial photo lies on the terrain at 0.2 m. Roads, paths, water and rock come
from swissTLM3D and are drawn on the ground with free CC0 detail textures, and the water
moves. Each roof has its own colour, measured from the photo. The 34'412 trees the LiDAR
surface model shows stand where they grow, as procedural conifers. The sun stands where
it stood in the photo, and the lighting renders the photo at its own brightness. The walls are
one neutral plaster, a labelled placeholder. The build ships in data packs, each file under
GitHub's 100 MiB limit. First come M2's sixteen residue fixes.

## Briefs, lanes and waves

A lane is one builder session; its briefs run in order on shared files. The lanes of a wave
run at once and share no file in their Scopes (checked from each brief's Scope and Depends
on lines). Shared design data (the four new fixtures under `tests/shared/`, their vectors,
and the expected values in `config/photo.json`, `config/roofs.json`, `config/surfaces.json`
and `config/trees.json`) is committed by design with this plan. No lane writes it; every
lane reads it.

**Wave 1: seven sessions at once.**

| Lane | Briefs, in order | Files (summary; each brief's Scope is the rule) |
|---|---|---|
| A · pipeline inputs | M3-01 residue, pipeline → M3-03 inputs: photo, surface model, swissTLM3D | `download.py`, `lock.py`, `datasets.py`, `manifest.py`, `terrain.py`, `buildings.py`, `__main__.py`, `config/datasets.json`, `config/datasets.lock.json`, their tests |
| B · tools and packs | M3-02 residue, game and tools → M3-08 data packs | `tools/gate.sh`, `tools/gate_allowlist.txt`, `tools/export.sh`, `game/export_presets.cfg`, `game/project.godot`, `game/scripts/data_packs.gd`, `game/tools/pack.gd`, `game/scripts/terrain/terrain_grid.gd`, named game tests, the tools tests under `pipeline/tests/` (`fake_tools.py`, `test_gate_gut_run.py`, `test_export_checks.py`) |
| C · photo and roofs (pipeline) | M3-04 the photo step → M3-05 roof colours | `pipeline/mattini/photo.py`, `roofs.py`, their tests, `pipeline/pyproject.toml` and `uv.lock` (Pillow) |
| D · surfaces and trees (pipeline) | M3-06 the surfaces step → M3-07 the trees step | `pipeline/mattini/surfaces.py`, `trees.py`, their tests |
| E · the terrain's look (game) | M3-09 the photo on the terrain → M3-10 roads, paths, water and rock on the terrain | `game/scripts/terrain/photo_grid.gd`, `surface_grid.gd`, `terrain_loader.gd`, `game/shaders/terrain_photo.gdshader`, `game/textures/`, their tests |
| F · trees (game) | M3-11 trees in the game | `game/scripts/trees/`, `game/shaders/tree_conifer.gdshader`, their tests |
| G · buildings (game) | M3-12 roof colours and walls in the game | `game/scripts/buildings/building_roofs.gd`, `building_loader.gd`, `game/materials/`, named tests |

**Wave 2: two sessions at once, after wave 1 has landed and been integrated.**

| Lane | Briefs | Files |
|---|---|---|
| H · pipeline wiring | M3-13 the new steps on the command line and in the manifest | `pipeline/mattini/__main__.py`, `manifest.py`, `lock.py`, the fit checks in `photo.py`, `roofs.py`, `surfaces.py`, `trees.py` (onto `lock.fit_problem`) and the `entries_sha256` calls in `roofs.py` and `trees.py`, the three M2 fixture manifests, their tests |
| I · the scene | M3-14 the main scene: the new data, the sun, the light, the credits | `game/scripts/main.gd`, `game/main.tscn`, `game/export_presets.cfg` (include filters), `tools/export.sh` (steps 2 and 6), `tools/gate_allowlist.txt` (six lines), `game/tests/test_main_scene*.gd`, `test_scene_placement.gd`, `complete_world.gd`, `test_release_settings.gd`, `pipeline/tests/fake_tools.py`, `test_export_startup_lines.py` |

The one shared file of wave 1 is `tools/gate_allowlist.txt`, append-only. Briefs M3-08,
M3-09, M3-10, M3-11 and M3-12 each append their pinned line or lines, because their tests
make readers log refusals on purpose. A builder whose rebase brings another lane's lines
keeps every line, re-runs the gate and records it in Findings. Lane B owns the file's rules
(M3-02), not its other lanes' lines.

Dependency note: lane C adds the one new dependency, Pillow, for the photo's JPEG. Lane D
lands in the same wave, so it adds none: the surfaces step writes its PNG with a small
writer on Python's own zlib (SPEC §8, the surfaces).

**Hints for every lane** (measured in design's rehearsals of both waves, 2026-10-14; each
would have stopped a lane's gate):

- M2-01's area census forbids the area's name anywhere in `pipeline/mattini/`, comments
  included: write "the area", never its name.
- fiona is imported only inside the function that reads a FileGDB (M3-01's
  `test_fiona_import.py` walks every module of the package).
- The gate runs `ruff format --check` and `gdformat --check`: format before committing.
- A docstring or comment that no longer says what the code does is a Hard Rule 2 breach no
  census sees (the rehearsal's throwaways left stale ones in `lock.py` and `terrain.py`):
  re-read the ones your change touches.
- The real village's steps run on one machine shared by seven sessions: keep a step's peak
  memory near design's (M3-04's is a gate: under 2 GB).
- Your own new test files are named `test_m3_<nn>_*` (your brief's number) unless your brief
  names a prefix, so no two lanes add the same file.
- Every brief's Scope also covers its own brief file (its Status line and Findings) and its
  screenshots, `docs/briefs/shots/<brief id>-*.jpg`.
- Wave 1's visual briefs (M3-09 to M3-12) may skip their screenshots: the main scene draws
  their work only from M3-14 (M3-12's walls at once). M3-14 and the after-wave-2 step take
  them (design's departure from WORKFLOW's screenshot rule and SPEC §12, 2026-10-14).
- Never name another lane's test file in a comment or docstring: M3-01's census fails when
  the file has not landed yet. Name the brief instead.
- Lanes C and D check the lock's fit in their own step modules in wave 1, importing only
  the names M3-01 keeps (its decision 10); M3-13 moves them onto `lock.fit_problem`.

## Integration notes (the seams the orchestrator checks; lesson 8)

Design rehearsed both waves on throwaway implementations before the GO (the agents' notes:
the pipeline lanes landed in order, then M3-13, gate exit 0 with 1'007 pytest tests; the
game and tools lanes, then M3-14). The seams below are the ones they hit.

**After wave 1** (every lane landed; pull `main`; the full gate on the combined head, to a log):

1. **The shared fixtures are untouched.** `git diff <base>..HEAD -- tests/shared/
   config/photo.json config/roofs.json config/surfaces.json config/trees.json` is empty: no
   lane rewrote design's data.
2. **Each pipeline step meets its game reader at its fixture.** Each pair passes its own pinned
   tests on the combined head:
   - photo (C) and PhotoGrid (E);
   - surfaces (D) and SurfaceGrid (E);
   - trees (D) and TreeChunks/TreeLoader (F);
   - roofs (C) and BuildingRoofs (G).
3. **The inputs meet the steps** (A with C and D). This is the arc's first real-data run, made
   in a scratch checkout and recorded here:
   - `lock photo`, `lock surface` and `lock tlm` write design's entries (M3-03's table);
   - `download photo`, `download surface` and `download tlm` fetch and verify;
   - then each step's `build_*` function is called from a Python one-liner, since the
     command line arrives in wave 2. Each must write its expected values: config/photo.json,
     roofs.json, surfaces.json and trees.json.
   - A difference is a seam to fix in the briefs' files, or a BLOCKED question if it needs
     design.
4. **The gate's own residue fixes hold with the new test scripts.** GUT's script count (M3-02)
   counts the scripts present, so wave 1's new ones raise it; the run summary and the version
   line are still required.
5. **Pillow** is in `pipeline/uv.lock` (lane C), and `uv lock --check` passes.
6. **`datasets.py`** is edited by M3-01 and M3-03 in the same loop (one lane, in order): the
   edition rule first, then the `resolution_m` check for `swissalti3d`, `swissimage` and
   `swisssurface3d`.
7. **The lock seam:** M3-03's `test_expected_inputs_m3.py` checks the four step configs'
   `computed_for` against the committed lock; the steps' own tests read no committed lock.
8. **The TLM's two readers:** M3-07 reads swissTLM3D through M3-06's `read_tlm` and its
   adapter (integer millimetres to metres); the trees' chunks must still be design's.
9. **The allowlist:** every lane's appended line is present once (M3-08, M3-09, M3-10,
   M3-11, M3-12), and no entry holds `Ignoring script` or `Failed to load script` (M3-02).
10. **What wave 2 relies on from wave 1:** each new reader refuses with one
    `push_error("<Reader>: <path>: <problem>")` (PhotoGrid, SurfaceGrid, TreeChunks,
    BuildingRoofs); `TreeLoader.TREES_NOTE` and `BuildingLoader.WALLS_NOTE` hold their
    briefs' texts (pinned); lane A's modules still hold the names M3-01 decision 10 keeps;
    `RoofsError` is a ValueError; each step refuses a missing download naming its
    `download` command before writing anything, a missing provenance before any progress
    line (M3-13's pinned CLI test).

**Wave 1 integration record** (the orchestrator, 2026-10-15, head `37a628a`; every brief DONE;
no seam needed a fix):

- Item 1: `git diff 9a9612e..HEAD` over the shared fixtures and the four expected-value files is
  empty. Item 5: `pillow>=12.3.0` is in `pyproject.toml` and `uv.lock`; `uv lock --check` passes.
  Item 9: the allowlist holds 13 lines, `BuildingRoofs`, `PhotoGrid`, `TreeChunks`, `SurfaceGrid`
  and `DataPacks` once each, no `Ignoring script` or `Failed to load script` entry.
- The full gate on the combined head, to a log, exit 0: pytest 1954 passed (5 network tests
  deselected), GUT 41 scripts = 41 `test_*.gd` files, 224 tests, 8618 asserts, `GUT version:  9.6.1`.
- Item 3, the real village, in a scratch `git clone` (H22): `download` terrain, buildings, photo,
  surface and tlm fetched and verified; then each step's `build_*` function, one process each,
  matched `config/*.json` before writing: terrain `b6334c1f…` (5.8 s, 1'044 MB), buildings
  1'486 in six chunks (5.8 s, 346 MB), photo pixels `00533bc6…` and JPEG `cf83c705…` (65.2 s,
  1'214 MB), roofs `8d9664b6…` with 1'486 of 1'486 coloured (29.0 s, 1'266 MB), surfaces
  `93d78ba6…` (22.5 s, 399 MB), trees 34'412 in six chunks (29.4 s, 1'303 MB). One detail: the
  first `download photo` ended `mattini: error:` on a SHA-256 mismatch of tile 2624-1097 after its
  one refetch (tile 2624-1096 had needed its refetch too); the second run fetched that tile once
  and verified all six. A transfer cut or corrupted on the way, caught as designed; not a
  republish (the lock's checksums are unchanged and now match).
- Items 2, 4, 6, 7, 8 and 10 are carried by the pinned tests in that gate (each pair at its
  fixture); the pipeline-to-reader pairs on the real village are the after-wave-2 end-to-end run.
- Carried to the review round (the board's residue list when it closes): `BuildingLoader.
  roofs_problem`'s refusing branch has no gate test (M3-12 Findings 2); `PhotoGrid` does not
  refuse a photo wider than 16384 texels (M3-09 Findings 5); export checks 4b and 4c have no
  committed stand-in pytest (M3-08 Findings); `trees.py` imports private grid helpers from
  `surfaces.py`, so a rename there must move `trees.py` (M3-07 Findings).

**After wave 2:**

1. **The real village end to end.** In a scratch checkout, run every step from the command
   line (lane H), then `manifest` (`3ca0445c…`, 324'359 bytes, design's rehearsal), then
   `tools/export.sh` with the packs (lane B). The exported Linux build must start headless
   with its packs and print all eight startup lines in order (lane I's), with no ERROR line.
   Every file must be under 100 MiB. Lane I runs this itself only if lane H had landed when
   its pins passed; otherwise this step is its gate (M3-14's Findings say which).
   Design's rehearsal measured `mattini.pck` 21.3 MB (the textures), `mattini-terrain.pck`
   96.0 MB, `mattini-photo.pck` 50.2 MB, and `mattini.exe` 198 KB under the limit.
2. **Software screenshots** (`tools/shot.sh`) of the start view, 60 m over the centre, a street
   at 30 m, the river and a rock face go into `docs/briefs/shots/M3-*`. They are evidence,
   not a gate.
3. **Lanes H and I meet at the manifest:** M3-13's three M2 fixture manifests and M3-14's
   `complete_world.gd` leave every game test green on the combined head (measured in
   design's rehearsal); the gate's GUT count rises with M3-14's three new scripts.

**Wave 2 integration record** (the orchestrator, 2026-10-15, head `ffa5b91`; M3-13 `3ccb38f`,
M3-14 `4f7af57`; no seam needed a fix):

- The full gate on the combined head, to a log, exit 0: pytest 2169 passed (5 network tests
  deselected), GUT 44 scripts = 44 `test_*.gd` files, 236 tests, 8745 asserts, `GUT version:  9.6.1`.
- Item 1, the real village end to end, in a scratch `git clone` with the wave-1 downloads: every
  step from the command line wrote design's values (terrain 14.9 s, buildings 8.8 s, photo 85.2 s
  at 1'213 MB, roofs 32.3 s at 1'299 MB, surfaces 217.1 s (a cold page cache: it hashes the TLM's
  2.88 GB first; 22 s when the file is cached), trees 38.1 s at 1'304 MB); `manifest` is
  `3ca0445c9109eec4696d654d1c7536f50220f4db04503fab836412f5b0c01065`, 324'359 bytes, design's. Then
  `tools/export.sh` (its own `XDG_DATA_HOME`, H9) exit 0 in 102 s: no ERROR line, the exported Linux
  build started headless with its two packs and printed all eight startup lines in order. Sizes:
  `mattini.pck` 21'280'420, `mattini-terrain.pck` 96'041'728, `mattini-photo.pck` 50'224'444,
  `mattini.exe` 104'659'456 (99.81 MiB), `mattini.x86_64` 71'075'864; every file under 100 MiB.
- Item 2: seven software screenshots, `docs/briefs/shots/M3-14-*.jpg` (start, centre at 60 m,
  street and river and forest edge at 30 m, rock face, pause screen), taken by M3-14 in the
  Compatibility renderer. They are evidence of what is drawn, not of the look: the conifers read
  near black there (the owner's Forward+ is the check, brain.md H21, H23).
- Item 3: lanes H and I met at the manifest: `complete_world.gd` and the three M2 fixture manifests
  leave every game test green; the gate's GUT count rose from 41 to 44 scripts.

## The review plan (WORKFLOW §Review policy)

Run by the orchestrator once every brief is DONE and integrated (BUILD.md §The orchestrator
6). Diff range: from the base (above) to the integrated head. Every lens is its own
session or isolated agent, in its own worktree with fresh caches; it builds the real village
from the pinned inputs, works by *prove it or downgrade it*, and commits one report,
`docs/reviews/M3-R1-<lens>.md`. Grades: P0 crash or wrong world, P1 a wrong result the owner
would see or a Hard Rule broken, P2 a weakness a realistic change trips, P3 the rest.

**Round R1: three lenses.**

1. **placement (Tier 1).** *Prompt:* "Prove or break that the photo, the surfaces, the
   trees and the roof colours land where config/world.json and the data say. Probe every
   seam between the pipeline's grids and the game: the photo rectangle's corners and texel
   centres, the surfaces grid against the photo grid, the axis mapping and the height offset,
   each tree's base height against Terrain3D's get_height and its position against to_local,
   and the roof colours against the building order and counts. Use asymmetric worlds (another
   origin, a height offset, a grid north-west of its origin), mutate the transforms, and
   show each named harm reproduced and caught." *Must prove:* for each seam, a mutation that
   misplaces it (half a texel, a flipped axis, a swapped origin, a building order off by one)
   fails a named test; the real village's trees stand on Terrain3D's ground (count those
   more than 5 cm off); the photo's corner texels sit at the box's corners. *Does NOT prove:*
   that it renders or looks right.
2. **inputs and determinism (Tier 2, with Hard Rule 5's full discipline).** *Prompt:* "Prove
   or break the three new inputs and the four new steps: lock and download refuse every
   republish, wrong edition or unfitting lock before fetching; computed_for and the expected
   values refuse a changed world or new inputs as design changes; every output is
   byte-identical across two runs and fresh checkouts (content-identical for the surfaces'
   PNG); the expected values were not copied from the code under test; M2's sixteen
   residue fixes hold." *Must prove:* each new refusal reached by a test and by a command
   (`mattini: error:`, no traceback); two fresh builds of every new output identical;
   mutation proofs for the determinism tests (lesson 33: a time or a host name added to an
   output must fail the gate). *Does NOT prove:* a real republish (none exists).
3. **game and tools (Tier 2).** *Prompt:* "Prove or break the game's readers, loaders and
   shader parameters, the trees' instancing, the walls' placeholder and its label, the
   credits and the startup lines, the data packs from export to start, and the gate's and
   export's residue fixes. Run the export and start the Linux build with and without its
   packs." *Must prove:* each reader refuses a wrong block, file or world with the error
   panel naming the fix; the exported build starts with its packs and prints every startup
   line; every file under 100 MiB; the credits name every dataset and CC0 texture. *Does
   NOT prove:* that it renders or looks right; the Windows build starts.

**Adjudication:** `docs/reviews/M3-round1.md`. P0, P1 and every placement (Tier 1) P2 get
fix briefs (BUILD.md §The orchestrator 6); the other P2s and the P3s go to the board's
residue list. **Verification pass V1** over the fixes (one round, Tier 2). **Tier 1 rounds
until clean:** a placement round is clean when it reports no P2 or above; until then lens 1
re-runs over each fix. A truncated round leaves the arc open.

## The release

**0.3.0**, shipped through `docs/RELEASE.md` with the data packs (§C). The record's "please
look at these" list must name, for the owner's RTX 4090:

- the photo on the terrain: sharpness at 30, 60 and 150 m;
- the baked shadows: the photo was taken at 13:30 in September, so its shadows point north,
  and the game's sun is placed there;
- the "ghost roofs" of buildings newer than the 2020 model;
- roads, paths, water (does it move?) and rock;
- the trees: generic conifers, where the LiDAR found them;
- the walls: one placeholder colour;
- the roof colours;
- the light (exposure 0.54, sky 0.25, calibrated in software, not Forward+);
- memory and GPU memory (about 2–3 GB expected);
- the Windows build, never started here;
- what it does NOT prove: that it renders or looks right.

FB-001 is the feedback the release closes, or closes in part: its record says which, from
the owner's first look.

## DEFERRED, said out loud

| Item | Reason | Cost to the owner |
|---|---|---|
| Close-range detail for meadows, scree and forest floor | not chosen (option b); the photo carries their colour | below about 30 m, grass and scree are soft photo pixels |
| Façade materials beyond one neutral plaster | no open wall data; the owner chose "neutral" | walls read as plain blocks up close |
| Tree species, broad-leaved trees, bushes | no open species data | every tree is a generic conifer |
| Railways, cable cars, names | not asked for M3 | they show only as lines in the photo |
| Lightening the photo's baked shadows | needs the moving sun (M4) | under another sun, the photo's shadows still point north |
| Buildings newer than 2020 (the ghost roofs) | no newer per-sheet building data (the 2026 edition is one national 14 GB file) | some roofs lie flat on the ground in the photo with no building |
| The area beyond the 2 × 3 km box | M5 | sky beyond the box's edge, as in 0.2.0 |
| Delivery beyond packs on `dist` | M5's size decides (SPEC §14) | none in M3 |
| A public per-building derivation in `buildings.py` | two lanes of wave 1 would share the file; `roofs.py` repeats the selection with the buildings step's own helpers | two copies of the selection loop, held equal by the roofs fixture |
