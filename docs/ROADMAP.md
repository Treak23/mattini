# ROADMAP.md — the board

Open items only. Shipped and answered items live in `docs/history/` and
`docs/releases/`. Sources cited (`FB-nnn`, brief ids). Effort: **S** = part of a brief,
**M** = one brief, **ARC** = several.

## Open now

**M3 Surfaces and trees — GO (2026-10-14, the owner); the build runs.** The plan is
`docs/briefs/M3-plan.md`: fourteen briefs in two waves (wave 1 seven sessions at once, wave 2
two), the review plan and the release 0.3.0: the village in a realistic look made from
swisstopo data (the photo at 0.2 m, roads, paths, water and rock from swissTLM3D, roof
colours, LiDAR trees, data packs). The owner's answers of 2026-10-14 are SPEC §13 rows 29–34 (rows 35–36 are design's).
M2's residue is M3-01 and M3-02.

Orchestrator: session_014zvmfwGgSKjxfe3feiiL91 · M3 · since 2026-10-14T19:45Z
Builder: M3-01, M3-03 · pending · since 2026-10-14T19:47Z
Builder: M3-02, M3-08 · pending · since 2026-10-14T19:47Z
Builder: M3-04, M3-05 · pending · since 2026-10-14T19:47Z
Builder: M3-06, M3-07 · pending · since 2026-10-14T19:47Z
Builder: M3-09, M3-10 · pending · since 2026-10-14T19:47Z
Builder: M3-11 · pending · since 2026-10-14T19:47Z
Builder: M3-12 · pending · since 2026-10-14T19:47Z

**Waiting on the owner:** the first look at 0.2.0's Windows build (FB-001 reported Linux
all OK).

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
- M2's residue: sixteen P3s and the builders' follow-ups, M3-01 and M3-02.
- Software screenshots use the Compatibility renderer; Forward+ crashes in software when
  Terrain3D draws (brain.md H12). They are evidence of what is drawn, not of the look.
- A session's checkout is shallow, and its local `main` can be an old ref that `git pull`
  calls diverged (brain.md H14): the spawn prompts' sync line handles it since M2
  planning.
- Two M1 sessions of the former supervisor were not archived at the close, because the
  auto-mode classifier refused it: `session_01Nf7BgWfr9p8KWviRiSQHKG` and
  `session_01X6QWucdq2PdcnnthGwjLX9`. For the owner, from the session list.

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
