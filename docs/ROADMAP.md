# ROADMAP.md — the board

Open items only. Shipped and answered items live in `docs/history/` and
`docs/releases/`. Sources cited (`FB-nnn`, brief ids). Effort: **S** = part of a brief,
**M** = one brief, **ARC** = several.

## Open now

No arc is running. Next: M3 Surfaces and trees, planned in a fresh `design` session. Its
first briefs carry M2's residue: sixteen P3s of the verification pass and the builders'
open follow-ups, none touching the build that shipped (`docs/history/ARCS.md` §M2,
*Carried into M3*). M3 planning asks the access route for swissTLM3D.

**Waiting on the owner:** whether 0.2.0's builds go on `dist`. They are prepared as the
`dist` commit `5ce4888` (about 77 MB new: the `.pck`; everything else is 0.1.0's blobs);
"push to main" named `main` only.

**Last shipped:** 0.2.0, 2026-09-26: the village with its 1'486 buildings
(`docs/releases/v0.2.0.md`; built from `main` `10f0060`; its builds reach `dist` with the
push above).

Arc M2 — Buildings: closed 2026-09-26, shipped 0.2.0; the close in full is
`docs/history/ARCS.md` §M2. It ran in one session by the owner's word (RULINGS
2026-09-25). Arc M1 — Terrain: closed 2026-09-25, shipped 0.1.0 (ARCS §M1).

**Parked questions:** none.

**Open decisions (SPEC §14):**
- macOS builds — OPEN.
- Licence of mattini's own code — OPEN.
- Weather: simulated or real data — OPEN (M6).
- Backdrop and larger-area extents and resolutions — OPEN (M5), with the buildings' missing
  sheets near Zermatt (M2 R1 I-07, SPEC §14).
- Access route for swissTLM3D (national only) — OPEN (M3).
- An export over 100 MB on `dist` — OPEN until M5 (the owner, 2026-09-25: "later"; D16).
- Game type — OPEN (later).

## Next, in order (confirmed by the owner, 2026-09-24)

v1 = M0–M6: walking, the day/night cycle and weather are in v1 (owner, 2026-09-24). M0,
M1 and M2 are closed.

1. M3 Surfaces and trees — ARC, next
2. M4 Sun cycle — ARC
3. M5 Scale up — ARC
4. M6 Weather and walking — ARC

## DEFERRED, said out loud

Nothing deferred: the inbox is empty.

## Residues and hazards

- Terrain3D 1.0.2's traps (brain.md H11) and its deprecation warning, printed once per
  process (H4). Collision over holes prints ERROR lines: M1 runs without collision, and
  walking (M6) needs an answer.
- swissTLM3D comes only as a national multi-GB file (brain.md H7): M3 needs an access
  route before any download. swissBUILDINGS3D's is the 2020 edition per map sheet (the
  owner, 2026-09-25).
- The export's size: Godot's Windows template alone is 99.81 MiB, 198 KB under GitHub's
  limit, and the `.pck` has 5.2 MiB of room at 0.2.0 (5'452'200 bytes; D16; brain.md H15).
  M3's surfaces and trees go into it: an export over 100 MiB is open until M5 by the
  owner's word, so M3 planning measures what M3 adds first.
- M2's residue: sixteen P3s and the builders' follow-ups, carried into M3
  (`docs/history/ARCS.md` §M2).
- Software screenshots use the Compatibility renderer; Forward+ crashes in software when
  Terrain3D draws (brain.md H12). They are evidence of what is drawn, not of the look.
- A session's checkout is shallow, and its local `main` can be an old ref that `git pull`
  calls diverged (brain.md H14): the spawn prompts' sync line handles it since M2
  planning.
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

- **0.2.0** — 2026-09-26 — arc M2: the village's 1'486 buildings as a white architectural
  model, the real sample as a test fixture, godot-cpp's notice in the credits
  (`docs/releases/v0.2.0.md`).
- **0.1.0** — 2026-09-25 — arc M1: the village terrain at 0.5 m, the free-fly camera, the
  pause screen and credits (`docs/releases/v0.1.0.md`).
