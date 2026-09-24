# ROADMAP.md — the board

Open items only. Shipped and answered items live in `docs/history/` and
`docs/releases/`. Sources cited (`FB-nnn`, brief ids). Effort: **S** = part of a brief,
**M** = one brief, **ARC** = several.

## Open now

**Last shipped:** nothing yet.

### Arc M0 — Setup and the first M1 step

Supervision: ON · M0 · since 2026-09-24T03:44Z
Waker: session_012t9Gvi7HQtMJDJFdZtvd9W · Routine trig_01V6UzfBMJzJ7Z8dW3nYRKAf · since 2026-09-24T03:45Z

**OPEN briefs:**
- M0-01 Repo skeleton, Python environment and the standard gate — M
- M0-02 World config and coordinate transforms, pipeline side (Tier 1) — M
- M0-03 Godot project, GUT, GDScript lint, WorldConfig and a hardened gate — M
- M0-04 Terrain download for the village area (the first M1 step) — M

Order: M0-01 → M0-02 → M0-03 and M0-04 (disjoint scopes; both depend on M0-02 only).

**Builders running:** none.

**Decisions for the close:** none yet.

**Parked questions:** none.

**Open decisions (from start.md Part 1 / 1A; SPEC §14):**
- macOS builds — OPEN.
- Does the owner design screens or visuals (`docs/design/`)? — OPEN.
- Where the game shows its version — OPEN (before the first release).
- Licence of mattini's own code — OPEN.
- Weather: simulated or real data — OPEN (M6).
- In-game terrain resolution for the village: 0.5, 1 or 2 m — OPEN (M1).
- Backdrop and larger-area extents and resolutions — OPEN (M5).
- Access route for swissBUILDINGS3D (one 14.1 GB national file) — OPEN (M2); for
  swissTLM3D (national only) — OPEN (M3).
- A committed sample of real swisstopo data as a test fixture — OPEN.
- Software rendering in containers for smoke screenshots — OPEN.
- An export over 100 MB on `dist` — OPEN (first release).
- Version scheme — PROPOSED (SPEC §11).
- Game type — OPEN (later).

## Next, in order (confirmed by the owner, 2026-09-24)

v1 = M0–M6: walking, the day/night cycle and weather are in v1 (owner, 2026-09-24).

1. M0 Setup — ARC (briefed above)
2. M1 Terrain (the village area, SPEC §7) — ARC
3. M2 Buildings — ARC
4. M3 Surfaces and trees — ARC
5. M4 Sun cycle — ARC
6. M5 Scale up — ARC
7. M6 Weather and walking — ARC

## DEFERRED, said out loud

Nothing deferred: the inbox is empty.

## Residues and hazards

- Terrain3D 1.0.2 on Godot 4.6.3 prints a deprecation warning GUT counts as a failure
  (brain.md H4): M1's tests must handle it.
- swissBUILDINGS3D and swissTLM3D come only as national multi-GB files (brain.md H7): M2
  and M3 need an access route before any download.
- An exported build may exceed GitHub's 100 MB file limit on `dist` (SPEC §11).

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

Nothing shipped yet.
