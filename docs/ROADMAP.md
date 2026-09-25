# ROADMAP.md — the board

Open items only. Shipped and answered items live in `docs/history/` and
`docs/releases/`. Sources cited (`FB-nnn`, brief ids). Effort: **S** = part of a brief,
**M** = one brief, **ARC** = several.

## Open now

**Last shipped:** nothing yet. Arc M0 closed on 2026-09-24 without a version, because
there was nothing to play yet: record in `docs/history/ARCS.md` §M0.

### Arc M1 — Terrain (planned 2026-09-25)

Supervision: ON · M1 · since 2026-09-25T04:00Z
Waker: session_019do6LK4hFYQ9c4ykJwQcNw · Routine trig_011umFC7mvuuPiadHHw9DE56 · since 2026-09-25T04:21Z
Tick: session_01Nf7BgWfr9p8KWviRiSQHKG · started 2026-09-25T04:55Z
Last tick: 2026-09-25T04:34Z · main 3a3fe0e · ticks 4
Cost: waker $1.68 (first waker, handed off 04:20Z; successor unread) · ticks $3.52 (ticks 1–3; tick 4 unread) · builders $7.50 (M1-01 and M1-03's builder) · lenses $0 (read from each other session's `usage.cost_usd`; a session cannot read its own, so the last tick at a later tick or the close's usage page)
Builder: session_018DsC2M2fzoruSxhZSkXs3Z · M1-02, M1-04 · spawned 2026-09-25T04:04Z

**OPEN briefs** (lanes may run at once: no shared file, no dependency):

| Brief | What | Depends on | Lane |
|---|---|---|---|
| M1-01 | Pinned inputs, byte-pinned outputs: the tile lock, provenance lifecycle, goldens, census, `.gitattributes`, tracked files | — | pipeline |
| M1-02 | The gate cannot be switched off; WorldConfig's corners tested | — | game |
| M1-03 | The village terrain from the downloaded tiles (`python -m mattini terrain`) | M1-01 | pipeline |
| M1-04 | Terrain3D in the game: vendoring, TerrainGrid, TerrainLoader, clay look, `tools/shot.sh` | M1-02 | game |
| M1-05 | Free-fly over the village: main scene, camera, pause screen, credits, errors on screen | M1-03, M1-04 | — |
| M1-06 | Release preparation for 0.1.0: presets, `tools/export.sh`, a real export | M1-05 | — |

Landed: M1-01 `25972d4` (DONE) — full gate green on `7fa1470` at tick 2 (pytest 275
passed, GUT 13/13, exit 0). M1-02 `c635411` (DONE, Findings `bdba171`) — full gate green on
`1f2578e` at tick 3 (pytest 275 passed, GUT 18/18, exit 0). M1-03 `0794554` (DONE, Findings
`1dbb31e`, `7d94d4c`) — full gate green on `3a3fe0e` at tick 4 (pytest 361 passed, GUT
18/18, exit 0).

**Review** (WORKFLOW §Review policy): Tier 1 covers the terrain grid on both sides (the
pipeline's grid and resampling, `TerrainGrid`/`TerrainLoader` placement, the manifest's
`terrain` block) with `config/world.json` and the transforms; Tier 2 covers the rest
(gate, camera, UI, look, export, vendoring, credits).

**The close** ships 0.1.0 (SPEC §11): the owner's first look at the village.

**Decisions for the close:**
- Keep or reverse the builders' reversible choices inside scope: M1-01 Findings 6 (lock
  check order, `load_lock` strictness, module layout), M1-02 Findings 6 (gate's
  `run_godot` wrapper and step order, WorldConfig's `_built` flag and own NaN test), M1-03
  Findings 6 (resampling as the plain 64-bit window mean, the refusal order, the terrain
  config's strictness, how `manifest` reads the terrain description, the `progress`
  keyword).
- M1-03 Findings 7, for design: the pinned stray-tile test fails the folder-reading
  mutation only through the stray tile's unknown id, never through its content.

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
- While M1-05 and M1-06 wait on M1-04 they have no `Builder:` line, so the waker's due
  rule (SUPERVISE §The waker 2.5) counts a tick at every wake until M1-04 lands (tick 4,
  2026-09-25): for design.
- Landing wakes. In M0 no landing started a tick; every tick came from a scheduled wake
  (ledger, 2026-09-24). Checked at M1 tick 1 (2026-09-25T04:05Z): `fire_trigger` on the
  waker's Routine turned its session running within a second. The next miss lies in the
  builders' fire or the waker's due check. Only without `text`: a fire with `text` starts
  a stray session instead (brain.md H13). Design's first test at the go passed `text` and
  left one, "⚡ Waker · M1 · hourly wake" (`session_01QSSgKNoYUzz1jYhNjBjCES`, $0.24, no
  repository), tagged `M1` for the close's sweep and ledger.
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
