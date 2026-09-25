# ROADMAP.md — the board

Open items only. Shipped and answered items live in `docs/history/` and
`docs/releases/`. Sources cited (`FB-nnn`, brief ids). Effort: **S** = part of a brief,
**M** = one brief, **ARC** = several.

## Open now

**Last shipped:** nothing yet. Arc M0 closed on 2026-09-24 without a version, because
there was nothing to play yet: record in `docs/history/ARCS.md` §M0.

### Arc M1 — Terrain (planned 2026-09-25; the go below)

**OPEN briefs** (lanes may run at once: no shared file, no dependency):

| Brief | What | Depends on | Lane |
|---|---|---|---|
| M1-01 | Pinned inputs, byte-pinned outputs: the tile lock, provenance lifecycle, goldens, census, `.gitattributes`, tracked files | — | pipeline |
| M1-02 | The gate cannot be switched off; WorldConfig's corners tested | — | game |
| M1-03 | The village terrain from the downloaded tiles (`python -m mattini terrain`) | M1-01 | pipeline |
| M1-04 | Terrain3D in the game: vendoring, TerrainGrid, TerrainLoader, clay look, `tools/shot.sh` | M1-02 | game |
| M1-05 | Free-fly over the village: main scene, camera, pause screen, credits, errors on screen | M1-03, M1-04 | — |
| M1-06 | Release preparation for 0.1.0: presets, `tools/export.sh`, a real export | M1-05 | — |

**Review** (WORKFLOW §Review policy): Tier 1 covers the terrain grid on both sides (the
pipeline's grid and resampling, `TerrainGrid`/`TerrainLoader` placement, the manifest's
`terrain` block) with `config/world.json` and the transforms; Tier 2 covers the rest
(gate, camera, UI, look, export, vendoring, credits).

**The close** ships 0.1.0 (SPEC §11): the owner's first look at the village.

**Decisions for the close:** none yet.

**Parked questions:** none.

**Open decisions (SPEC §14):**
- macOS builds — OPEN.
- Licence of mattini's own code — OPEN.
- Weather: simulated or real data — OPEN (M6).
- Backdrop and larger-area extents and resolutions — OPEN (M5).
- Access route for swissBUILDINGS3D (one 14.1 GB national file) — OPEN (M2); for
  swissTLM3D (national only) — OPEN (M3).
- A committed sample of real swisstopo data as a test fixture — OPEN (M1 uses a synthetic
  fixture).
- An export over 100 MB on `dist` — OPEN, decided at M1's close if a file is over (SPEC
  §11: the village `.pck` sits just under).
- Game type — OPEN (later).

Answered at M1 planning (SPEC §13 rows 14–19): terrain resolution 0.5 m; the version only on
the pause screen; the version scheme; no owner designs; software screenshots as evidence.

## Next, in order (confirmed by the owner, 2026-09-24)

v1 = M0–M6: walking, the day/night cycle and weather are in v1 (owner, 2026-09-24). M0
is closed.

1. M1 Terrain (the village area, SPEC §7) — ARC, running (above).
2. M2 Buildings — ARC
3. M3 Surfaces and trees — ARC
4. M4 Sun cycle — ARC
5. M5 Scale up — ARC
6. M6 Weather and walking — ARC

## DEFERRED, said out loud

Nothing deferred: the inbox is empty.

## Residues and hazards

- Terrain3D 1.0.2's traps (brain.md H11) shape M1-04; its deprecation warning prints once
  per process (H4). Collision over holes prints ERROR lines: M1 runs without collision, and
  walking (M6) needs an answer.
- swissBUILDINGS3D and swissTLM3D come only as national multi-GB files (brain.md H7): M2
  and M3 need an access route before any download.
- An exported build may exceed GitHub's 100 MB file limit on `dist` (SPEC §11): at 0.5 m
  the village's heights are 96 MB.
- Landing wakes. In M0 no landing started a tick; every tick came from a scheduled wake
  (ledger, 2026-09-24). At the M1 go, check once that `fire_trigger` on the new waker's
  Routine wakes it (its session turns running). If it does, the next miss lies in the
  builders' fire or the waker's due check.
- Windows line endings break the gate and change the manifest's bytes until M1-01's
  `.gitattributes` (brain.md H10).
- Software screenshots use the Compatibility renderer; Forward+ crashes in software when
  Terrain3D draws (brain.md H12). They are evidence of what is drawn, not of the look.

## Later

- First game-mode prototype (type OPEN).

## Ideas (the owner's, unshaped)

- Game types discussed: co-op builder, walking game, shooter; also mountain guide, rescue
  helicopter, freeride, photography, historical Zermatt, glacier time-travel, mystery,
  trail race, lift or hotel management.

## Not planned (with the reason)

- Browser and mobile builds — owner's decision, desktop only.
- Photorealism — owner's decision, stylised diorama look.
- Google Maps / 3D Tiles data — licence forbids shipping or deriving from it.

## Shipped

Nothing shipped yet (M0 closed without a version).
