# M3 round R1 — adjudication

The build orchestrator, 2026-10-15. Head reviewed `410dbba` (diff `9a9612e..410dbba`); the three
lens reports are `M3-R1-placement.md`, `M3-R1-game.md` and `M3-R1-inputs.md`, each committed
alone. Tiers per the plan: placement Tier 1; game and inputs Tier 2 (the inputs lens with Hard
Rule 5's full discipline). Every lens ran in its own fresh clones, built the real village from
the pinned inputs (manifest `3ca0445c…`, 324'359 bytes, in all three) and ran the standard gate
at the head: exit 0 each time (pytest 2169, GUT 44 scripts, 236 tests, 8745 asserts).

**Counts:** placement 0 P0, 0 P1, 3 P2, 1 P3; game 0 P0, 1 P1, 4 P2, 7 P3; inputs 0 P0, 0 P1,
1 P2, 5 P3. No grade was changed.

## Dispositions

| id | grade | what | disposition |
|---|---|---|---|
| G-01 | P1 | the trees' flat normals point into the tree: lit from the wrong side, both renderers | fix brief `M3-R1-fix-4`, DONE `77e8508` |
| P-02 | P2 | nothing gates the Trees node's transform or that trees stand on the ground | `M3-R1-fix-1`, DONE `0385a7f` |
| P-03 | P2 | no gate runs the shaders that place the photo, classes and crown colour | interim half in `M3-R1-fix-1`, DONE `0385a7f` (seven mutations now fail a named test, text and data checks, a census where it is one); the render step is **BLOCKED** (design: amends BUILD.md rule 2b), fix brief `M3-R1-fix-3` not written |
| P-01 | P2 | trees take y from the 0.5 m grid at any terrain spacing: 1 m puts 3'542 trees more than 5 cm off the ground, 2 m 18'932 | **BLOCKED** (design: SPEC §7 and §8 disagree; both remedies are design's), fix brief `M3-R1-fix-2` not written |
| G-03 | P2 | a wrong-typed manifest field turns a `!=` guard into a runtime error that accepts the block (21 cases; a numeric `world_sha256` passes all six readers) | taken to Tier 1 (its member is Hard Rule 4's detector; WORKFLOW §Review policy, Escalation) and fixed as a pattern: `M3-R1-fix-5` |
| G-04 | P2 | the readers' refusal tests assert refusal, not cause: PhotoGrid 24 of 38 and SurfaceGrid 23 of 42 guards removable, among them the photo's and surfaces' origin and height-offset guard | its Hard Rule 4 part (CLAUDE.md: such code MUST have mutation-proved tests) in `M3-R1-fix-5`; the rest to the residue list |
| I-01 | P2 | the surfaces PNG's SHA-256 depends on the zlib build and is copied into the manifest, so `manifest.json` is a property of the machine's zlib | residue, as a **design question that does not hold 0.3.0**: each remedy (an expected PNG hash in `config/surfaces.json` with a refusal naming the zlib; dropping the PNG's hash from the description; a deflate of mattini's own) changes a schema or design data. The shipped bytes come from the pinned environment; SPEC §8 and RELEASE.md §C already say the PNG depends on zlib; the release record names the dependence and the manifest comparison |
| G-02, G-05 | P2 | `source_color` of the photo, detail textures and tree colours pinned by no test (H21's hazard reproduced); 22 of 31 mutations of `tools/export.sh`'s refusals leave its tests green | residue (Tier 2 P2; the release walk runs the export and its 100 MiB check by hand) |
| P-04 | P3 | the roof/wall split runs on float32 local coordinates: in another world one triangle changes class | residue |
| G-06 to G-12 | P3 | the terrain's credits line is validated by no reader; the readers' messages in a build still say "run pipeline commands" and a damaged pack reads "missing"; the photo shader's wiring and the loaders' look parameters mostly unpinned; `roofs_problem`'s refusing branch and the tile check untested; two gate behaviours unpinned; the steps' JSON copies ship in the packs; the manifest's `world` block is not bound to `world_sha256` at read time (by design, said once) | residue |
| I-02 to I-06 | P3 | a cut transfer is told from a good one only by the SHA-256 after one retry and the message does not say so; an `OSError` ends a command in a traceback; `resolution_m` for two datasets has no test; the roofs step's inputs-before-provenance order is not pinned; a step runs to its end before the manifest refuses another step's damaged config | residue |

## What the round proved (the must-proves)

- **Placement:** the real village's trees stand on Terrain3D's ground (0 of 34'412 more than
  5 cm off, worst 0.244 mm, measured through the main scene); the photo's corner texels sit at the
  box's corners (rectangle (0, −2000, 2000, 3000), the pixel SHA-256 re-derived independently from
  the source tiles); surfaces agree with an independent shapely rasterisation at 99.9999 %;
  roof colours 1486 of 1486 reproduced from the chunk geometry and the photo tiles; 52 mutations
  of half a texel, flipped axes, a swapped origin, a building order off by one and a height offset:
  45 failed a named test, the seven that did not are P-02 and P-03, which fix-1 closed.
- **Inputs:** every new refusal reached by a test and by a command; two fresh builds of every new
  output identical (the surfaces PNG content-identical, I-01); the determinism tests catch a time
  or a host name added to every output; M2's sixteen residue fixes hold under mutation; 180
  mutations.
- **Game:** each reader refuses a wrong block, file or world; the export exited 0 in 109 s with
  the orchestrator's sizes to the byte, all eight startup lines, no ERROR, every file under
  100 MiB, started with, without and with damaged packs; the credits name all five datasets and
  the three CC0 textures.

## Not proven, said out loud

That anything renders or looks right on the owner's GPU; the Windows build starting; a real
republish; behaviour at a terrain spacing other than 0.5 m (P-01 is open).

## What the round changed besides findings

The game lens installed Mesa's software Vulkan driver (`apt-get update`, then `apt-get install
mesa-vulkan-drivers`) and rendered the whole village and the exported build with Forward+ on
lavapipe under Xvfb: brain.md H12 ("Forward+ on lavapipe crashes as soon as Terrain3D draws") is
stale and is corrected at the close. A Forward+ software render is still not the owner's GPU.

## Next

1. `M3-R1-fix-5` (lane K) lands; then **verification pass V1** (Tier 2, one round) over the
   fixes `77e8508`, `0385a7f` and `M3-R1-fix-5`: reproduce each finding's harm on the unfixed
   tree and show it gone on the fixed one, and look for what each fix broke.
2. Design answers BLOCKED Q1 (P-01) and Q2 (P-03's render step); their fix briefs are written
   from the answers and built as a lane.
3. **Placement is Tier 1: rounds until clean.** The placement lens re-runs over the fixes that
   touch placement (fix-1, fix-5 and the answers' fixes); the round is clean when it reports no
   P2 or above. Release 0.3.0 (docs/RELEASE.md §C) follows a clean round, V1 clean and the full
   gate green from clean.
