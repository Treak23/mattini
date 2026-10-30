# ROADMAP.md — the board

Open items only. Shipped and answered items live in `docs/history/` and
`docs/releases/`. Sources cited (`FB-nnn`, brief ids). Effort: **S** = part of a brief,
**M** = one brief, **ARC** = several.

## Open now

**Release 0.5.0 — in progress (the go of 2026-10-29, `docs/history/blocked/2026-10-29-2.md`):** the softened photo shadows
(FB-004 item 3) and delivery through GitHub Releases, built by a GitHub Actions workflow into a draft Release the owner
publishes (1a); and, by the owner's "question A OK", the trees' haze (FB-004 item 5), the clock's note outside 2020 to 2035, a RENDER check of the river's direction and four residue groups (tests and messages); the list is frozen. **0.4.0 was never delivered:** its
audited `dist` commit `e2633b6` lived only in the previous session's container and is lost; the owner's "2c": 0.5.0, which
contains 0.4.0, is the next build the owner gets. `dist` stays at 0.3.1 (`5b51347`), the rollback record.

**Next release (the owner's order):** the softened photo shadows (FB-004 item 3; M4-03, M4-06, the shadows parts of M4-09 and
M4-10, rebuilt on 0.4.0's files: the plan's process note), and **delivery through GitHub Releases** (assets up to 2 GB; `dist`
kept as the rollback record; `tools/export.sh`, RELEASE.md §C, the README, SPEC §11 and §14 rewritten; the owner's "Yes if it
makes sense", 2026-10-29; the 100 MiB per-file limit of a push stays, public or not); then the far mountains' shadows; the trees'
variant the owner chooses (the record's table); a clamp or label for the clock's 2020 to 2035; the move to Godot 4.8 once it is
out of beta.

**The owner's first look at 0.3.1 (2026-10-26):** it starts with 4× MSAA, 60 fps and 15 paused, the GPU at
40 % against 0.3.0's 94 % (68 °C against 87 °C), the log fills while running; "everything else is good"; the
river "flows but side to side, we will need to give it a direction" (FB-008, for 0.4.0's triage).

**Waiting on the owner:** nothing for 0.5.0 until its record. A
second developer may join: how a person works beside the release sessions (the process assumes only agents commit to `main`)
and the licence of mattini's own code are a `design` conversation when they do. The Windows build's first start stays deferred by
the owner ("not a priority" until sharing). Done 2026-10-26: the repository is public, and ruleset 25920774 blocks deletion and
non-fast-forward pushes on `main` and `dist` with no bypass actors.

**The stars' licence (SPEC §13 row 51, settled 2026-10-27):** the Hipparcos Catalogue under CC BY-NC 3.0 IGO,
"Credit: ESA"; the open condition is a sale, which needs ESA's permission (data.licences@esa.int) or section S's
files removed. The Yale catalogue was refused (no licence; the ADC's recorded word forbids altered copies). Known limits (v0.4.0-06): positions are J1991.25, not precessed to the date (0.13 to 0.35°); no star colours. The licence's §7(b) reinstates it if a breach is cured within 30 days (the triage said otherwise).

**Decisions for the owner to audit** (the session's reversible calls, DESIGN.md §How the session
decides 2; all below kept by the owner's "6a yes", 2026-10-29), release 0.4.0 (the plan): SkyClock (v0.4.0-04) at tier 1 although it reads no world config; the sky rig and
the stars (05, 06) at tier 2, their frame reviewed in 08 at tier 1; the river's ripples run in real time whatever the
game clock does. Release 0.3.1, kept at 0.4.0's go (2026-10-27, shown to the owner, no objection): four water screenshots instead of M4-06's two (v0.3.1-01); the copied
pins' comments re-pinned with the 0.3.1 brief ids (v0.3.1-02 to -05); if a render check fails under
MSAA, the render scripts turn MSAA off (they measure placement, not edges); ReleaseBuild's comment
names no caller, so v0.3.1-05 edits no file of v0.3.1-03; the three new release-gate checks are
permanent in `docs/RELEASE.md` §C. The briefs' Findings carry both options of each. At the publish: `dist`
pushed without a separate "push dist" (DESIGN.md step 6 publishes; it added 21 MB, `mattini.pck`, every
other file 0.3.0's; RULINGS 2026-10-26); `mattini-0.1.0/` left `dist`'s tree (the last three kept).

**Last shipped:** 0.3.1, 2026-10-26: the 0.3.0 test's fixes (`docs/releases/v0.3.1.md`; `dist` `5b51347`,
built from `main` `cb5946e`). Before it: 0.3.0, 2026-10-16, the village in a realistic look made from the data
(`docs/releases/v0.3.0.md`; `dist` `5f08379`), kept on `dist` as `mattini-0.3.0/`, the rollback; 0.2.0 as
`mattini-0.2.0/`.

Arc M3 — Surfaces and trees: closed 2026-10-16, shipped 0.3.0; the close in full is `docs/history/ARCS.md` §M3. Arc M2 — Buildings: closed 2026-09-26, shipped 0.2.0; the close in full is
`docs/history/ARCS.md` §M2. Arc M1 — Terrain: closed 2026-09-25, shipped 0.1.0 (ARCS §M1).

**Parked questions:** none.

**Open decisions (SPEC §14):**
- macOS builds — OPEN.
- Licence of mattini's own code — OPEN.
- Weather: simulated or real data — OPEN (M6).
- Backdrop and larger-area extents and resolutions — OPEN (M5), with the buildings' missing
  sheets near Zermatt (M2 R1 I-07, SPEC §14).
- Delivery when the data outgrows packs on `dist` — settled in 0.5.0 by GitHub Releases (SPEC §13 row 54, §14): each file
  under 2 GB; M5's extents keep that constraint.
- Game type — OPEN (later; the owner: "keep open, lets just build the map first", §13 row 34).

## Next, in order (confirmed by the owner, 2026-09-24)

v1 = M0–M6: walking, the day/night cycle and weather are in v1 (owner, 2026-09-24). M0 to M3
are closed.

The project's direction (the owner, 2026-10-27; SPEC §13 row 50): this repository is the map, as detailed and
accurate as the data allows; each game is a branch or fork that takes what it needs.

1. (0.4.0, shipped: the river's direction per stretch and the moving sun; the `dist` push waits)
2. The softened photo shadows (FB-004 item 3) and delivery through GitHub Releases, then the far mountains' shadows (the rest of M4)
3. M5 Scale up
4. M6 Weather and walking
- When Godot 4.8 is out of beta: the move to it (the owner, 2026-10-27), a release of its own once Terrain3D and
  GUT support it (SPEC §4's pins)

## DEFERRED, said out loud

0.3.1's list (shipped; its deferrals carry into 0.4.0's triage), with reasons and costs, is in `docs/briefs/v0.3.1-plan.md` §DEFERRED (M4's in
`docs/briefs/M4-plan.md`, M3's in `docs/briefs/M3-plan.md`). Every Open inbox entry (FB-003 to
FB-007) is in 0.3.1 or on its DEFERRED list (FB-004 items 1, 3, 5 and the look items); FB-001 is
closed (0.3.0, ARCHIVE).

## Residues and hazards

Closed in 0.5.0 and struck below (each checked against the code at `805223c`): 0.4.0's S-01 (the stars in the pack are checked
by `tools/release_checks.sh` check 1 on every Release build), S-02, S-03, S-05, S-06 (the clock's note), CD-3, TG-09, `png_l8`'s
words, the float32 360.0 note, the river's direction (RENDER flow); 0.3.1's R1-05, R1-06; M3's I-02, I-04, I-05, R2 P-01, P-03,
P-04 (replaced by the measured gaps, the z limit below), R2 S-01, and G-05 in part (briefs v0.5.0-09 to -13). Found already fixed by
0.5.0's triage: 0.3.1's R1-03 (the crossfade's 3600 s is a whole number of phases) and F6 (the census skips no reader, v0.4.0-09);
M3's I-03 (`OSError` in `main()`'s tuple, v0.4.0-07), V1-1 (the render step catches both edits, M3-R1-fix-3), V1-5, and the stale
zlib line of `tests/shared/surfaces_vectors.json`. This paragraph moves to 0.5.0's record at the publish.

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
- 0.4.0's release gate and renders (2026-10-29): the Controls list clears Resume by 9.5 px at 1280 x 720 (software render); two time keys read "Period" on the pause screen under the render container's keyboard map (check on the owner's PC); water more than 12 m from every drawn stream line stands still; a straight-down view from 300 m was rendered with its casters on screen only.
- 0.3.1's whole-range review, P3 (`docs/reviews/v0.3.1-round1.md`): R1-02 the packs' folder computed in
  `data_packs.gd` and `main.gd` separately; F7 the frame-cap test's engine half has a second
  writer since v0.3.1-05; F10 `test_m4_08_data_packs_expected.gd` leaves scratch subfolders in `user://`.
- 0.4.0's whole-range review, P3 (`docs/reviews/v0.4.0-round1.md`): the sky shader assumes up = +y (S-07); `config/sky.json` names
  only the world's SHA-256 (CD-6).
- 0.5.0's whole-range review, P3 (`docs/reviews/v0.5.0-round1.md`): `tools/gate_allowlist.txt` line 20 excuses every error on the
  buildings fixture's path, so CaptureShadowGrid's and SkySite's refusals there are excused unnamed (S-09); `star_image`'s
  declination guard refuses exactly ±90 only: just inside, the run width `floor(0.5 / cos dec)` is unbounded (a hang at
  89.9999999, a doubled star at 89.99; the shipped table tops out at Polaris, +89.26) (correctness N2); `release_checks.sh` check
  5's FAIL message says the game exited before the lines appeared even when they had (the verdict is right) (N4);
  `release.yml` takes any 40-hex `sha` and never checks it is on `main`, while the notes say "built from `main`" (owner N2); the
  mask reader's tests use LV95 values a float32 holds exactly, so a 32-bit origin subtraction passes (R1-CD-02, H5); the workflow
  does not pin the Python interpreter whose zlib the PNGs' bytes depend on (the runner's uv-managed 3.13.14, the container's
  system 3.13.17; R1-CD-04, H27).
- 0.5.0's batches, P3 (`docs/briefs/v0.5.0-plan.md`, the batch log): the readers' world guard says "its origin differs" when only
  the height offset differs (v0.5.0-03, in every reader that copies it: `shadow_grid.gd`, `surface_grid.gd`); RENDER lift's
  east-west and transposed comparators read 0.0 and never decide (v0.5.0-04, a pinned file); the mask's credit takes the
  config's first and last edition unsorted where TreeChunks sorts (v0.5.0-05); RENDER flow encodes the band bearings with its
  own copy of the axis mapping (labels only; v0.5.0-09) and does not see where the flow is read
  (a north-south or an east-west shift within the bands), ripple map b reversed alone (only the 0.60 correlation floor) or a
  dropped validity factor (said in its words by v0.5.0-15, not gated); the classes check resolves the water's placement in z to about 0.2 m only (a 0.1 m shift passes;
  v0.5.0-12); `tools/export.sh`: 16 of 31 refusal mutations still survive its tests (R12, R13, R16 to R23, R26 to R31; R22 the
  started build's exit status and R23 its error scan first; v0.5.0-13), the rest of M3's G-05.
- Process residue (the 0.3.1 triage, 2026-10-25): the clerk's gate is settled (WORKFLOW §Gates, 2026-10-27); no tool reads the weekly allowance (DESIGN.md step 3 reports the five-hour status and
  the API-equivalent cost); the lane-session path is not written (one lane per release until it
  is); WORKFLOW's "a tier-1 batch runs alone in
  its lane" has no testable meaning with one lane; builder worktrees that hold commits stay in
  the session's container (the harness removes only unchanged ones).

## M3 R1 residue (P2 and P3 of round R1, `docs/reviews/M3-round1.md`)

I-01 (P2, the PNG's bytes and zlib) is fix brief `M3-R1-fix-6`; P-01 and P-03 are `M3-R1-fix-2` and `-3` (all three DONE, 2026-10-16).
For design (fix wave): the render step's trees check sees a synthetic flat world and 20 trees, not the village's relief or its MultiMesh cells (fix-3 Findings 10d).
P2: **G-02** `source_color` of the photo, detail textures and tree colours is pinned by no test;
**G-04** (the part that is not Hard Rule 4) the readers' refusal tests assert refusal, not cause;
**G-05** 16 of 31 mutations of `tools/export.sh`'s refusals leave its tests green (22 before
v0.5.0-13, which pinned step 5's 100 MiB check and part of 4c; the survivors are 0.5.0's batches line above).
P3: P-04 roof/wall split on float32 local coordinates; G-06 the terrain's credits line unvalidated;
G-07 build messages still say "run pipeline commands", a damaged pack reads "missing"; G-08 the photo
shader's wiring and loaders' look parameters mostly unpinned; G-09 `BuildingLoader.roofs_problem`'s
refusing branch and the tile check untested; G-10 two gate behaviours unpinned; G-11 the steps' JSON
copies ship in the packs; G-12 the manifest's `world` block not bound to `world_sha256` at read time
(by design); I-06
a step runs to its end before the manifest refuses another step's damaged config; wave 1 and 2's
carried items: `PhotoGrid` does not refuse a photo wider than 16384 texels (M3-09 Findings 5),
`trees.py` imports private grid helpers from `surfaces.py`, a manifest write cut before its rename
leaves `manifest.json.part` (M3-13 Findings 8).

Round R2 (`docs/reviews/M3-round2.md`, closed clean), all P3: P-02 the render world is 16 m wide, flat and positive-coordinates-only (an `abs()`, a scale of 1.002, a shift of the terrain's vertices pass; nine edits move it north-west); S-02 RELEASE.md §C's manifest box prints nothing on a wrong size (the release walk records `wc -c` and the exit status); S-03 SPEC §8's config shape omits `expected_png_sha256`; V1-2 and V1-3 below stay open.

Round V1 (`docs/reviews/M3-V1.md`, the verification pass: every R1 fix verified, no P0 to P2), all P3: V1-2 fix-4's normal census counts lines that begin with `NORMAL` (a braced second statement passes, a correct `dFdyCoarse` spelling fails); V1-3 the scene-level tree tests see one cell south-east of the origin (a sign error that shows only at x < 0 passes); V1-4 `ManifestValue.differs` calls a String and a StringName different types (no site passes a StringName).

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

- **0.4.0** — 2026-10-29 — the river flows downstream; the sun and the moon move, a physical sky, the stars
  (`docs/releases/v0.4.0.md`; built, recorded, the `dist` push waits for the owner).
- **0.3.1** — 2026-10-26 — the 0.3.0 test's fixes: the river, the frame cap, the log, MSAA, a missing
  pack named (`docs/releases/v0.3.1.md`).
- **0.3.0** — 2026-10-16 — arc M3: the village in a realistic look made from the data
  (`docs/releases/v0.3.0.md`).
- **0.2.0** — 2026-09-26 — arc M2: the village's 1'486 buildings as a white architectural
  model, the real sample as a test fixture, godot-cpp's notice in the credits
  (`docs/releases/v0.2.0.md`).
- **0.1.0** — 2026-09-25 — arc M1: the village terrain at 0.5 m, the free-fly camera, the
  pause screen and credits (`docs/releases/v0.1.0.md`).
