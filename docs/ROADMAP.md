# ROADMAP.md — the board

Open items only. Shipped and answered items live in `docs/history/` and
`docs/releases/`. Sources cited (`FB-nnn`, brief ids). Effort: **S** = part of a brief,
**M** = one brief, **ARC** = several.

## Open now

**Last shipped:** nothing yet. Arc M0 closed on 2026-09-24 without a version, because
there was nothing to play yet: record in `docs/history/ARCS.md` §M0.

**OPEN briefs:** none. Next: M1 planning, in a fresh `design` session.

**Decisions for the close:** none (M0's were ruled at its close: D1–D12, RULINGS
2026-09-24).

**Parked questions:** none.

**Open decisions (from start.md Part 1 / 1A; SPEC §14):**
- macOS builds — OPEN.
- Does the owner design screens or visuals (`docs/design/`)? — OPEN.
- Where the game shows its version — OPEN (asked at M1 planning; the first version is
  planned for M1's close, SPEC §11).
- Licence of mattini's own code — OPEN.
- Weather: simulated or real data — OPEN (M6).
- In-game terrain resolution for the village: 0.5, 1 or 2 m — OPEN (asked at M1
  planning).
- Backdrop and larger-area extents and resolutions — OPEN (M5).
- Access route for swissBUILDINGS3D (one 14.1 GB national file) — OPEN (M2); for
  swissTLM3D (national only) — OPEN (M3).
- A committed sample of real swisstopo data as a test fixture — OPEN.
- Software rendering in containers for smoke screenshots — OPEN.
- An export over 100 MB on `dist` — OPEN (first release).
- Version scheme — PROPOSED (SPEC §11; asked at M1 planning).
- Game type — OPEN (later).

## Next, in order (confirmed by the owner, 2026-09-24)

v1 = M0–M6: walking, the day/night cycle and weather are in v1 (owner, 2026-09-24). M0
is closed.

1. M1 Terrain (the village area, SPEC §7) — ARC.
   - First, the M0 carry-over: 17 review findings plus `uv lock --check`. The table is in
     `docs/history/ARCS.md` §M0. It lands before any M1 brief that writes a shader,
     project settings, manifest fields, a main-scene script or a Terrain3D test (D12).
   - Then the tiles become Terrain3D terrain with a free-fly camera. The terrain step reads
     only `provenance.json`, checked against the config (D9), and the tiles' SHA-256 are
     pinned in the repository (D7).
2. M2 Buildings — ARC
3. M3 Surfaces and trees — ARC
4. M4 Sun cycle — ARC
5. M5 Scale up — ARC
6. M6 Weather and walking — ARC

## DEFERRED, said out loud

Nothing deferred: the inbox is empty.

## Residues and hazards

- Terrain3D 1.0.2 on Godot 4.6.3 prints a deprecation warning GUT counts as a failure
  (brain.md H4). M1's tests must handle it, and never by switching GUT's error tracking
  off (G-04, brain.md H8).
- swissBUILDINGS3D and swissTLM3D come only as national multi-GB files (brain.md H7): M2
  and M3 need an access route before any download.
- An exported build may exceed GitHub's 100 MB file limit on `dist` (SPEC §11).
- Landing wakes. In M0 no landing started a tick; every tick came from a scheduled wake
  (ledger, 2026-09-24). At the M1 go, check once that `fire_trigger` on the new waker's
  Routine wakes it (its session turns running). If it does, the next miss lies in the
  builders' fire or the waker's due check.
- Windows line endings break the gate and change the manifest's bytes until M1's
  `.gitattributes` (brain.md H10).

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
