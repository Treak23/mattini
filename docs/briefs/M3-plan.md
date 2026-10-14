# M3 — Surfaces and trees: the arc plan

Status: DRAFT — being prepared by design (2026-10-14)

Written by the design realm (`docs/roles/DESIGN.md` §The arc plan); run by one `ultracode
build` orchestrator (`docs/roles/BUILD.md` §The orchestrator). The owner's answers of
2026-10-14 are SPEC §13 rows 29–34 and `docs/history/RULINGS.md`; FB-001 is the arc's
reason, FB-002 is on the board's ideas.

## What M3 delivers

Version **0.3.0**: the village in a realistic look made from swisstopo data (SPEC §1, §8,
§10). The 2023 aerial photo lies on the terrain at 0.2 m. Roads, paths, water and rock come
from swissTLM3D and are drawn on the ground with free CC0 detail textures, and the water
moves. Each roof has its own colour, measured from the photo. The roughly 38'000 trees the
LiDAR surface model shows stand where they grow, as procedural conifers. The sun stands where
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
| B · tools and packs | M3-02 residue, game and tools → M3-08 data packs | `tools/gate.sh`, `tools/gate_allowlist.txt`, `tools/export.sh`, `game/export_presets.cfg`, `game/project.godot`, `game/scripts/data_packs.gd`, `game/tools/pack.gd`, `game/scripts/terrain/terrain_grid.gd`, named game tests |
| C · photo and roofs (pipeline) | M3-04 the photo step → M3-05 roof colours | `pipeline/mattini/photo.py`, `roofs.py`, their tests, `pipeline/pyproject.toml` and `uv.lock` (Pillow) |
| D · surfaces and trees (pipeline) | M3-06 the surfaces step → M3-07 the trees step | `pipeline/mattini/surfaces.py`, `trees.py`, their tests |
| E · the terrain's look (game) | M3-09 the photo on the terrain → M3-10 roads, paths, water and rock on the terrain | `game/scripts/terrain/photo_grid.gd`, `surface_grid.gd`, `terrain_loader.gd`, `game/shaders/terrain_photo.gdshader`, `game/textures/`, their tests |
| F · trees (game) | M3-11 trees in the game | `game/scripts/trees/`, `game/shaders/tree.gdshader`, their tests |
| G · buildings (game) | M3-12 roof colours and walls in the game | `game/scripts/buildings/building_roofs.gd`, `building_loader.gd`, `game/materials/`, named tests |

**Wave 2: two sessions at once, after wave 1 has landed and been integrated.**

| Lane | Briefs | Files |
|---|---|---|
| H · pipeline wiring | M3-13 the new steps on the command line and in the manifest | `pipeline/mattini/__main__.py`, `manifest.py`, their tests |
| I · the scene | M3-14 the main scene: the new data, the sun, the light, the credits | `game/scripts/main.gd`, `game/main.tscn`, `tools/export.sh` (step 6's lines), their tests |

The one shared file of wave 1 is `tools/gate_allowlist.txt`, append-only. Briefs M3-08,
M3-09, M3-10, M3-11 and M3-12 each append their pinned line or lines, because their tests
make readers log refusals on purpose. A builder whose rebase brings another lane's lines
keeps every line, re-runs the gate and records it in Findings. Lane B owns the file's rules
(M3-02), not its other lanes' lines.

Dependency note: lane C adds the one new dependency, Pillow, for the photo's JPEG. Lane D
lands in the same wave, so it adds none: the surfaces step writes its PNG with a small
writer on Python's own zlib (SPEC §8, the surfaces).

## Integration notes (the seams the orchestrator checks; lesson 8)

**After wave 1** (every lane landed; pull `main`; the full gate on the combined head, to a log):

1. **The shared fixtures are untouched.** `git diff <plan commit>..HEAD -- tests/shared/
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

**After wave 2:**

1. **The real village end to end.** In a scratch checkout, run every step from the command
   line (lane H), then `manifest`, then `tools/export.sh` with the packs (lane B). The
   exported Linux build must start headless with its packs and print every startup line
   (lane I's), with no ERROR line. Every file must be under 100 MiB.
2. **Software screenshots** (`tools/shot.sh`) of the start view, 60 m over the centre, a street
   at 30 m, the river and a rock face go into `docs/briefs/shots/M3-*`. They are evidence,
   not a gate.

## The review plan (WORKFLOW §Review policy)

Run by the orchestrator once every brief is DONE and integrated (BUILD.md §The orchestrator
6). Diff range: from this plan's commit to the integrated head. Every lens is its own
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

**Adjudication:** `docs/reviews/M3-round1.md`. P0 and P1 get fix briefs (BUILD.md §The
orchestrator 6); P2 and P3 go to the board's residue list. **Verification pass V1** over
the fixes (one round, Tier 2). **Tier 1 rounds until clean:** a placement finding of P2 or
above re-runs lens 1 over the fix. A truncated round leaves the arc open.

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
