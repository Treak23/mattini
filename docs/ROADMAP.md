# ROADMAP.md — the board

Open items only. Shipped and answered items live in `docs/history/` and
`docs/releases/`. Sources cited (`FB-nnn`, brief ids). Effort: **S** = part of a brief,
**M** = one brief, **ARC** = several.

## Open now

**M3 Surfaces and trees — closed 2026-10-16: version 0.3.0 is shipped on `dist` (commit `5f08379`, on the owner's word "push dist") and recorded (`docs/releases/v0.3.0.md`).** The plan is
`docs/briefs/M3-plan.md` (status DONE); the close in full is `docs/history/ARCS.md` §M3. All fourteen briefs and the six review fixes are DONE; rounds R1, V1 and R2 are adjudicated (`docs/reviews/M3-round1.md`, `M3-V1.md`, `M3-round2.md`): no P0, P1 or P2 is open, and the P3 and the Tier 2 P2 are on the residue list below. The standard gate from a fresh clone of `main` `697a154` is exit 0 (pytest 2228, GUT 47 scripts, 261 tests, 9760 asserts, the render step run); the real village rebuilt from the pinned inputs gives the manifest `3ca0445c…`; the ten files are under 100 MiB; a fresh clone of `dist` verifies against the README and its Linux build starts with all eight startup lines.

**Release 0.3.1 — GO 2026-10-25 (the owner), building.** The 0.3.0 test's items (FB-003 to
FB-007): five tier-2 batches in one lane, builders on Sonnet, two days and about half a week's
allowance (`docs/briefs/v0.3.1-plan.md`; the go: `docs/history/blocked/2026-10-25-1.md`). The
process changed on 2026-10-24 (SPEC §13 row 49, `docs/WORKFLOW.md`); this is its first release.
- v0.3.1-01 the river — DONE (`d568f5a`): pins red then green, 11 mutation rows killed, batch gate green (GUT 48 scripts, 262 tests); review: no P0–P2. Looking towards the sun the new water shows a broad soft glare where 0.3.0 had sharp glints and a jagged rim (`docs/briefs/shots/v0.3.1-01-sun-*.jpg`): for the owner's look
- v0.3.1-02 frame cap, log, edges — DONE (`b784d96`): three settings in `project.godot`, 8 mutation rows killed, batch gate green (GUT 49 scripts, 265 tests); render numbers under 4× MSAA as rehearsed (trees 0.9380 → 0.9387); review: no P0–P2, and a scratch project showed the flush writes while the game runs
- v0.3.1-03 a missing pack named — OPEN
- v0.3.1-04 the export checks the packs — OPEN
- v0.3.1-05 the pause cap and the pack panel — OPEN

**Next release, 0.4.0 — the moving sun:** the rest of M4 (`docs/briefs/M4-plan.md`; the owner's
answers are SPEC §13 rows 41–48; its process note says what 0.3.1 took and what the next cut must
rebuild): SkyClock, SkyRig and the physical sky, the stars, the sky step, the main scene's clock
and keys (about 16 builder hours). Then the far mountains' shadows and the softened photo shadows
(13 batches, mostly tier 1: one more cut). M4-08 is superseded by 0.3.1's batches.

**Waiting on the owner:** switching the repository to public (the owner's word, 2026-10-26; RULINGS):
the README's swisstopo credit and the inbox's paths are ready on `main`; then GitHub rulesets
blocking force pushes and deletions on `main` and `dist` (never `claude/*`, which the janitor
deletes). A second developer may join: how a person works beside the release sessions (the
process assumes only agents commit to `main`) is a `design` conversation when they do. The Windows
build's first start stays deferred by the owner ("not a priority" until sharing).

**Open licence question:** the Yale Bright Star Catalogue (BSC5) states no licence anywhere
authoritative (the triage of 2026-10-25: NASA's old archive called its data public domain, the
catalogue's ReadMe restricts distribution to that archive's CD; every alternative is worse). 0.4.0
decides whether it must be settled before any sale or before sharing at all (the repository goes public:
the stars table is published the day M4-05 commits it), and its closing condition (SPEC §13 row 48).

**Decisions for the owner to audit** (the session's reversible calls, DESIGN.md §How the session
decides 2), release 0.3.1: four water screenshots instead of M4-06's two (v0.3.1-01); the copied
pins' comments re-pinned with the 0.3.1 brief ids (v0.3.1-02 to -05); if a render check fails under
MSAA, the render scripts turn MSAA off (they measure placement, not edges); ReleaseBuild's comment
names no caller, so v0.3.1-05 edits no file of v0.3.1-03; the three new release-gate checks are
permanent in `docs/RELEASE.md` §C. The briefs' Findings carry both options of each.

**Last shipped:** 0.3.0, 2026-10-16: the village in a realistic look made from the data
(`docs/releases/v0.3.0.md`; `dist` `5f08379`, built from `main` `697a154`). Before it: 0.2.0, 2026-09-26, the village with its
1'486 buildings (`docs/releases/v0.2.0.md`; `dist` `5ce4888`, built from `main` `10f0060`), kept on `dist` as `mattini-0.2.0/`, the rollback.

Arc M3 — Surfaces and trees: closed 2026-10-16, shipped 0.3.0; the close in full is `docs/history/ARCS.md` §M3. Arc M2 — Buildings: closed 2026-09-26, shipped 0.2.0; the close in full is
`docs/history/ARCS.md` §M2. Arc M1 — Terrain: closed 2026-09-25, shipped 0.1.0 (ARCS §M1).

**Parked questions:** none.

**Open decisions (SPEC §14):**
- macOS builds — OPEN.
- Licence of mattini's own code — OPEN.
- Weather: simulated or real data — OPEN (M6).
- Backdrop and larger-area extents and resolutions — OPEN (M5), with the buildings' missing
  sheets near Zermatt (M2 R1 I-07, SPEC §14).
- Delivery when the data outgrows packs on `dist` — OPEN (M5; SPEC §13 rows 23, 32).
- Game type — OPEN (later; the owner: "keep open, lets just build the map first", §13 row 34).

## Next, in order (confirmed by the owner, 2026-09-24)

v1 = M0–M6: walking, the day/night cycle and weather are in v1 (owner, 2026-09-24). M0 to M3
are closed.

1. 0.3.1 — the 0.3.0 test's fixes (building, `docs/briefs/v0.3.1-plan.md`)
2. 0.4.0 — the moving sun (the rest of M4's sky)
3. The far mountains' shadows and the softened photo shadows (the rest of M4)
4. M5 Scale up
5. M6 Weather and walking

## DEFERRED, said out loud

0.3.1's list, with reasons and costs, is in `docs/briefs/v0.3.1-plan.md` §DEFERRED (M4's in
`docs/briefs/M4-plan.md`, M3's in `docs/briefs/M3-plan.md`). Every Open inbox entry (FB-003 to
FB-007) is in 0.3.1 or on its DEFERRED list (FB-004 items 1, 3, 5 and the look items); FB-001 is
closed (0.3.0, ARCHIVE).

## Residues and hazards

- Terrain3D 1.0.2's traps (brain.md H11) and its deprecation warning, printed once per
  process (H4). Collision over holes prints ERROR lines: M1 runs without collision, and
  walking (M6) needs an answer.
- swissTLM3D comes only as a national 2.88 GB FileGDB: M3 reads it straight from its zip
  (brain.md H20; SPEC §13 row 33). swissBUILDINGS3D's is the 2020 edition per map sheet (the
  owner, 2026-09-25).
- The export's size: Godot's Windows template alone is 99.81 MiB, 198 KB under GitHub's
  limit; from M3 the large data ships in packs (`mattini-terrain.pck` 96 MB, 8.4 MiB under,
  `mattini-photo.pck` 50 MB; SPEC §11). M5's larger area needs more (SPEC §14).
- Software screenshots use the Compatibility renderer, evidence of what is drawn, not of the
  look; Forward+ on lavapipe works since M3's review (brain.md H12). From M3-R1-fix-3 the gate's
  render step measures placement (SPEC §12).
- A session's checkout is shallow, and its local `main` can be an old ref that `git pull`
  calls diverged (brain.md H14): the spawn prompts' sync line handles it since M2
  planning.
- Process residue (the 0.3.1 triage, 2026-10-25): `docs/roles/FEEDBACK.md` commits each item
  without the gate, which lesson 18 forbids (a rule stated two ways, older than the process
  change); no tool reads the weekly allowance (DESIGN.md step 3 reports the five-hour status and
  the API-equivalent cost); the lane-session path is not written (one lane per release until it
  is); a `:<branch>` deletion refspec has no deny rule; WORKFLOW's "a tier-1 batch runs alone in
  its lane" has no testable meaning with one lane; builder worktrees that hold commits stay in
  the session's container (the harness removes only unchanged ones).

## M3 R1 residue (P2 and P3 of round R1, `docs/reviews/M3-round1.md`)

I-01 (P2, the PNG's bytes and zlib) is fix brief `M3-R1-fix-6`; P-01 and P-03 are `M3-R1-fix-2` and `-3` (all three DONE, 2026-10-16).
For design (fix wave): `tests/shared/surfaces_vectors.json` still says "its bytes depend on the zlib build, so only its pixels are pinned" (stale since fix-6; design's file, outside every lane's Scope); the render step's trees check sees a synthetic flat world and 20 trees, not the village's relief or its MultiMesh cells (fix-3 Findings 10d).
P2: **G-02** `source_color` of the photo, detail textures and tree colours is pinned by no test;
**G-04** (the part that is not Hard Rule 4) the readers' refusal tests assert refusal, not cause;
**G-05** 22 of 31 mutations of `tools/export.sh`'s refusals leave its tests green (step 5's 100 MiB
check, 4c, exit status).
P3: P-04 roof/wall split on float32 local coordinates; G-06 the terrain's credits line unvalidated;
G-07 build messages still say "run pipeline commands", a damaged pack reads "missing"; G-08 the photo
shader's wiring and loaders' look parameters mostly unpinned; G-09 `BuildingLoader.roofs_problem`'s
refusing branch and the tile check untested; G-10 two gate behaviours unpinned; G-11 the steps' JSON
copies ship in the packs; G-12 the manifest's `world` block not bound to `world_sha256` at read time
(by design); I-02 a cut transfer is told only by the SHA-256 (the message does not say run it
again); I-03 an `OSError` ends a command in a traceback; I-04 `resolution_m` for swissimage and
swisssurface3d has no test; I-05 the roofs step's inputs-before-provenance order is not pinned; I-06
a step runs to its end before the manifest refuses another step's damaged config; wave 1 and 2's
carried items: `PhotoGrid` does not refuse a photo wider than 16384 texels (M3-09 Findings 5),
`trees.py` imports private grid helpers from `surfaces.py`, a manifest write cut before its rename
leaves `manifest.json.part` (M3-13 Findings 8).

Round R2 (`docs/reviews/M3-round2.md`, closed clean), all P3: P-01 the render step's trees check passes with no tree drawn (`VISIBILITY_END_M`, a `discard`, a zero draw count leave the whole gate green) and its PASS line says "over 20 trees"; P-02 the render world is 16 m wide, flat and positive-coordinates-only (an `abs()`, a scale of 1.002, a shift of the terrain's vertices pass; nine edits move it north-west); P-03 the classes check reads the water class only, and the `tools/gate.sh` header and `game/tests/render/render_common.gd` say "the surface classes" (CLAUDE.md and SPEC §12 corrected 2026-10-25; the rest is a builder's); P-04 the classes check's 0.1 m rule rests on three samples in one direction; S-01 no test gives a 40 to 63 digit hex string to the SHA-256 check (only the message would be lost); S-02 RELEASE.md §C's manifest box prints nothing on a wrong size (the release walk records `wc -c` and the exit status); S-03 SPEC §8's config shape omits `expected_png_sha256`; V1-2 and V1-3 below stay open.

Round V1 (`docs/reviews/M3-V1.md`, the verification pass: every R1 fix verified, no P0 to P2), all P3: V1-1 fix-1's placement census does not name `xz` or `origin` (an edit of either after its declaration moves the classes or the crowns' colour with the gate green: the remainder of P-03); V1-2 fix-4's normal census counts lines that begin with `NORMAL` (a braced second statement passes, a correct `dFdyCoarse` spelling fails); V1-3 the scene-level tree tests see one cell south-east of the origin (a sign error that shows only at x < 0 passes); V1-4 `ManifestValue.differs` calls a String and a StringName different types (no site passes a StringName); V1-5 the fix-5 brief's gate boxes were unticked (ticked).

## Later

- First game-mode prototype (type OPEN).

## Ideas (the owner's, unshaped)

- Game types discussed: co-op builder, walking game, shooter; also mountain guide, rescue
  helicopter, freeride, photography, historical Zermatt, glacier time-travel, mystery,
  trail race, lift or hotel management.
- A collaborative "Zermatt builder" usable for a variety of projects (FB-002, 2026-10-14; the
  owner: "keep open, lets just build the map first"). What it would need early: the same base
  world on every machine (true already: Hard Rule 5, every file checked by SHA-256), each
  building's id in the game (from M3-05 and M3-12), then saved edits as a layer over the
  read-only world, and networking.

## Not planned (with the reason)

- Browser and mobile builds — owner's decision, desktop only.
- Photorealism beyond what the data gives (hand-made or procedural detail everywhere) —
  the owner chose the look made from the data, option (a), 2026-10-14 (SPEC §13 row 29).
- Google Maps / 3D Tiles data — licence forbids shipping or deriving from it.

## Shipped

- **0.2.0** — 2026-09-26 — arc M2: the village's 1'486 buildings as a white architectural
  model, the real sample as a test fixture, godot-cpp's notice in the credits
  (`docs/releases/v0.2.0.md`).
- **0.1.0** — 2026-09-25 — arc M1: the village terrain at 0.5 m, the free-fly camera, the
  pause screen and credits (`docs/releases/v0.1.0.md`).
