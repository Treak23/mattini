# ROADMAP.md — the board

Open items only. Shipped and answered items live in `docs/history/` and
`docs/releases/`. Sources cited (`FB-nnn`, brief ids). Effort: **S** = part of a brief,
**M** = one brief, **ARC** = several.

## Open now

**M3 Surfaces and trees — GO (2026-10-14, the owner); built, reviewed and verified; the fix wave READY, waiting for the owner's GO (design, 2026-10-15).** The plan is
`docs/briefs/M3-plan.md`: fourteen briefs in two waves, the review plan and the release 0.3.0: the village in a realistic look made from
swisstopo data (the photo at 0.2 m, roads, paths, water and rock from swissTLM3D, roof
colours, LiDAR trees, data packs). The owner's answers are SPEC §13 rows 29–34 and 37–38 (rows 35–36, 39–40 are design's).

**State (2026-10-15):** all fourteen briefs DONE and integrated; round R1 adjudicated (`docs/reviews/M3-round1.md`), its fixes fix-1, fix-4, fix-5 DONE, V1 clean (`docs/reviews/M3-V1.md`). Design answered Q1 (P-01 → b) and Q2 (P-03 → a) with the owner, and I-01 itself (RULINGS 2026-10-15). **Next, after the owner's GO:** the fix wave, three lanes at once (`M3-R1-fix-2` trees refuse a terrain spacing other than 0.5; `M3-R1-fix-3` the render step in the gate; `M3-R1-fix-6` the surfaces PNG's bytes), then round R2 (placement, Tier 1, until clean; fix-6's verification), the standard gate from clean, release 0.3.0 (plan §Fix wave). Nobody holds the orchestrator claim.

**Waiting on the owner:** the first look at 0.2.0's Windows build (FB-001 reported Linux
all OK).

**Decisions for design to audit:** none (the M3 list of ten audited and kept, RULINGS 2026-10-15).

**Last shipped:** 0.2.0, 2026-09-26: the village with its 1'486 buildings
(`docs/releases/v0.2.0.md`; `dist` `5ce4888`, built from `main` `10f0060`).

Arc M2 — Buildings: closed 2026-09-26, shipped 0.2.0; the close in full is
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

v1 = M0–M6: walking, the day/night cycle and weather are in v1 (owner, 2026-09-24). M0,
M1 and M2 are closed.

1. M3 Surfaces and trees — ARC, building (`docs/briefs/M3-plan.md`)
2. M4 Sun cycle — ARC
3. M5 Scale up — ARC
4. M6 Weather and walking — ARC

## DEFERRED, said out loud

M3's list, with reasons and costs, is in `docs/briefs/M3-plan.md` §DEFERRED. The inbox's one
Open entry, FB-001, goes to M3.

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
- Two M1 sessions of the former supervisor were not archived at the close, because the
  auto-mode classifier refused it: `session_01Nf7BgWfr9p8KWviRiSQHKG` and
  `session_01X6QWucdq2PdcnnthGwjLX9`. For the owner, from the session list.

## M3 R1 residue (P2 and P3 of round R1, `docs/reviews/M3-round1.md`)

I-01 (P2, the PNG's bytes and zlib) is fix brief `M3-R1-fix-6`; P-01 and P-03 are `M3-R1-fix-2` and `-3`.
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
