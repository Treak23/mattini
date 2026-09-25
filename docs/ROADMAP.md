# ROADMAP.md — the board

Open items only. Shipped and answered items live in `docs/history/` and
`docs/releases/`. Sources cited (`FB-nnn`, brief ids). Effort: **S** = part of a brief,
**M** = one brief, **ARC** = several.

## Open now

No arc is running. **Next: M2 Buildings**, planned in a fresh `design` session.

**Last shipped:** 0.1.0, 2026-09-25: the village terrain at 0.5 m with a free-fly camera
(`docs/releases/v0.1.0.md`; `dist` `2e81625`, built from `main` `05f86ef`).

Arc M1 — Terrain: closed 2026-09-25, shipped 0.1.0; the close in full is
`docs/history/ARCS.md` §M1.

**For M2 planning** (from the M1 close):
- M1's review residue, fifteen findings with the fix named, is M2's first work
  (`docs/history/ARCS.md` §M1, the carry-over table). T-01 and T-02 need design data: the
  expected SHA-256 of the village at 1 m and 2 m, a build test from 2 × 2 tiles, a second
  game fixture.
- Ask the owner how builds reach them once a file passes 100 MiB (D16): the `.pck` has
  8.3 MiB of room, and M2's buildings go into it.
- The spawn prompts' sync line (D21; brain.md H14).
- The owner's first look at 0.1.0 arrives through `feedback`.

**Parked questions:** none.

**Open decisions (SPEC §14):**
- macOS builds — OPEN.
- Licence of mattini's own code — OPEN.
- Weather: simulated or real data — OPEN (M6).
- Backdrop and larger-area extents and resolutions — OPEN (M5).
- Access route for swissBUILDINGS3D (one 14.1 GB national file) — OPEN (M2); for
  swissTLM3D (national only) — OPEN (M3).
- A committed sample of real swisstopo data as a test fixture — OPEN (M1 used a synthetic
  fixture).
- An export over 100 MB on `dist` — OPEN; nothing was over at 0.1.0; asked at M2 planning
  (D16).
- Game type — OPEN (later).

## Next, in order (confirmed by the owner, 2026-09-24)

v1 = M0–M6: walking, the day/night cycle and weather are in v1 (owner, 2026-09-24). M0
and M1 are closed.

1. M2 Buildings — ARC, next
2. M3 Surfaces and trees — ARC
3. M4 Sun cycle — ARC
4. M5 Scale up — ARC
5. M6 Weather and walking — ARC

## DEFERRED, said out loud

Nothing deferred: the inbox is empty.

## Residues and hazards

- Terrain3D 1.0.2's traps (brain.md H11) and its deprecation warning, printed once per
  process (H4). Collision over holes prints ERROR lines: M1 runs without collision, and
  walking (M6) needs an answer.
- swissBUILDINGS3D and swissTLM3D come only as national multi-GB files (brain.md H7): M2
  and M3 need an access route before any download.
- The export's size: Godot's Windows template alone is 99.81 MiB, 198 KB under GitHub's
  limit, and the `.pck` has 8.3 MiB of room (D16; brain.md H15).
- M1 R1 residue: fifteen findings carried into M2 (`docs/history/ARCS.md` §M1).
- Software screenshots use the Compatibility renderer; Forward+ crashes in software when
  Terrain3D draws (brain.md H12). They are evidence of what is drawn, not of the look.
- A session's checkout is shallow, and its local `main` can be an old ref that `git pull`
  calls diverged (brain.md H14): for M2 planning (the spawn prompts).
- Two M1 tick sessions were not archived at the close, because the auto-mode classifier
  refused it: `session_01Nf7BgWfr9p8KWviRiSQHKG` (tick 5) and
  `session_01X6QWucdq2PdcnnthGwjLX9` (tick 7). For the owner, from the session list.

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

- **0.1.0** — 2026-09-25 — arc M1: the village terrain at 0.5 m, the free-fly camera, the
  pause screen and credits (`docs/releases/v0.1.0.md`).
