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
| M2-03 | The building inputs: sheets, lock, download | M2-01 | DONE (ad12280), was BLOCKED on design's pinned lint |
| M2-04 | The village buildings from the sheets | M2-03 | DONE (b980214), checked |
| M2-05 | The buildings in the game | M2-02, M2-04 | DONE (86d764c), was BLOCKED on design's pinned tests |
| M2-06 | The terrain block's shape, three test gaps (M2-01's check) | M2-04 | DONE (cefa1ac), checked |
| M2-07 | M2 R1's fixes, the pipeline half | none | DONE (b3ec242), checked |
| M2-08 | M2 R1's fixes, the game and tools half | none | DONE (20c5a80), checked |
| M2-09 | The real sample, the buildings reader's fixture (the owner's "yes") | M2-07 | OPEN |

Review round M2 R1 (`docs/reviews/M2-round1.md`): clean, no P0 or P1; its five P2s and
fifteen of its sixteen P3s are M2-07 and M2-08; I-07 goes to M5 planning. Then one
verification pass, then the close.

Each brief is built by one agent in its own worktree, then checked by a second agent that
re-runs the gate, compares the pinned copies and proves the new tests by mutation. Residue
the checks graded P3 waits for the review round: M2-02's gate can be fooled by a test that
prints GUT's pass line itself and quits (G-04 only partly closed); the scoped allowlist's
line-end matching is unmeasured on Windows; the credits show godot-cpp's `# MIT License`
heading as raw text; M2-03's check: the download's refusal before any fetch is proven only
when the earlier sheets are already on disk (P2), provenance removed before a fetch is
untested, two refusals reach the owner as a traceback; M2-04's check: every command loads
fiona (the manifest imports the buildings module), an earlier build's chunk files are not
removed and an export would ship them, the real reader's output meets the step only in
the real run.

**The owner's answers (2026-09-25; RULINGS, SPEC §13 rows 22–24, 27):** 1 "a", the 2020
edition per map sheet, on which M2-03 to M2-05 were built; 2 "later", an export over
100 MiB stays open until M5; 3 "push to main"; 4 "yes", the real sample, brief M2-09.

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
- Access route for swissTLM3D (national only) — OPEN (M3).
- An export over 100 MB on `dist` — OPEN until M5 (the owner, 2026-09-25: "later"; D16).
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
