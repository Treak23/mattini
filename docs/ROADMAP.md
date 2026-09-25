# ROADMAP.md — the board

Open items only. Shipped and answered items live in `docs/history/` and
`docs/releases/`. Sources cited (`FB-nnn`, brief ids). Effort: **S** = part of a brief,
**M** = one brief, **ARC** = several.

## Open now

**Arc M2 — Buildings: running since 2026-09-25**, in this one session: design, build,
review and close by the one Opus 5.5 session with in-session workflow agents, and no
waker, ticks or spawned builders (the owner's word, RULINGS 2026-09-25).

| Brief | What | Depends on | Status |
|---|---|---|---|
| M2-01 | M1's residue, the pipeline half (T-01, T-03 to T-08) | none | DONE (b5a45e5), checked |
| M2-02 | M1's residue, the game and tools half (T-02, G-01 to G-07) | none | DONE (2cf5660), checked |
| M2-03 | The building inputs: sheets, lock, download | M2-01 | building |
| M2-04 | The village buildings from the sheets | M2-03 | OPEN |
| M2-05 | The buildings in the game | M2-02, M2-04 | OPEN |
| M2-06 | The terrain block's shape, three test gaps (M2-01's check) | M2-04 | OPEN |

Each brief is built by one agent in its own worktree, then checked by a second agent that
re-runs the gate, compares the pinned copies and proves the new tests by mutation. Residue
the checks graded P3 waits for the review round: M2-02's gate can be fooled by a test that
prints GUT's pass line itself and quits (G-04 only partly closed); the scoped allowlist's
line-end matching is unmeasured on Windows; the credits show godot-cpp's `# MIT License`
heading as raw text.

M2-03 to M2-05 are written on the source design PROPOSES (question 1 below: (a), the 2020
edition per map sheet), so the work goes on while the owner's answer is awaited. Nothing of
it reaches `main` or a build before the answer; another answer rewrites them. The real
sample (question 4) is not committed before the owner agrees.

**Asked of the owner at M2 planning (2026-09-25), waiting:**
1. The swissBUILDINGS3D access route (SPEC §14): (a) 3.0, 2020 edition, per map sheet,
   design's recommendation; (b) 2.0, 2024-05, per sheet (DXF); (c) the 14 GB national
   3.0 file.
2. An export over 100 MiB (D16): design recommends leaving it open until M5; the
   buildings add about 3 to 6 MB and there are 8.3 MiB of room.
3. Where the session pushes: `main` as usual, or the session branch only; and `dist` for
   0.2.0.
4. A committed real swisstopo sample (SPEC §14): the 45.7 KB buildings sheet 1328-33 as
   a reader fixture; design recommends yes.

**Last shipped:** 0.1.0, 2026-09-25: the village terrain at 0.5 m with a free-fly camera
(`docs/releases/v0.1.0.md`; `dist` `2e81625`, built from `main` `05f86ef`).

Arc M1 — Terrain: closed 2026-09-25, shipped 0.1.0; the close in full is
`docs/history/ARCS.md` §M1. Its fifteen carried findings are M2-01 and M2-02; the spawn
prompts' sync line (D21) is fixed at M2 planning (brain.md H14).

**Parked questions:** none.

**Open decisions (SPEC §14):**
- macOS builds — OPEN.
- Licence of mattini's own code — OPEN.
- Weather: simulated or real data — OPEN (M6).
- Backdrop and larger-area extents and resolutions — OPEN (M5).
- Access route for swissBUILDINGS3D — asked at M2 planning (above); for swissTLM3D
  (national only) — OPEN (M3).
- A committed sample of real swisstopo data as a test fixture — asked at M2 planning
  (above).
- An export over 100 MB on `dist` — asked at M2 planning (above); nothing was over at
  0.1.0 (D16).
- Game type — OPEN (later).

## Next, in order (confirmed by the owner, 2026-09-24)

v1 = M0–M6: walking, the day/night cycle and weather are in v1 (owner, 2026-09-24). M0
and M1 are closed.

1. M2 Buildings — ARC, running
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
