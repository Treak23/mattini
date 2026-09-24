# ROADMAP.md — the board

Open items only. Shipped and answered items live in `docs/history/` and
`docs/releases/`. Sources cited (`FB-nnn`, brief ids). Effort: **S** = part of a brief,
**M** = one brief, **ARC** = several.

## Open now

READY TO CLOSE: eb65041, pytest 209 (2 network deselected) + GUT 13 tests / 943 asserts + ruff, gdlint, gdformat, Godot import and parse check, 0 failures, 2026-09-24 (arc M0; full gate from a fresh worktree, tick 4)

**Last shipped:** nothing yet.

### Arc M0 — Setup and the first M1 step

Supervision: OFF · M0 · since 2026-09-24T05:50Z (READY TO CLOSE)
Waker: session_012t9Gvi7HQtMJDJFdZtvd9W · Routine trig_01V6UzfBMJzJ7Z8dW3nYRKAf · since 2026-09-24T03:45Z
Last tick: 2026-09-24T05:50Z · main eb65041 · ticks 4
Cost: waker $3.36 (to 05:46Z) · ticks $3.42 (ticks 1–3; tick 4 unread) · builders $9.38 · lenses $9.74 (read from each other session's `usage.cost_usd`; a session cannot read its own, so tick 4 and the waker's rest at the close's usage page)

**OPEN briefs:** none.

**DONE:** M0-01 (4475f6f), M0-02 (1d53a00), M0-03 (ff9e9d6), M0-04 (a383cff); full gate
green on eb65041 from a fresh worktree (tick 4: 209 pytest, 2 network tests deselected,
GUT 13 tests / 943 asserts, 0 failures).

**Review round R1: clean** (no P0, no P1; ruling in `docs/history/RULINGS.md`). Lenses
`coordinates` (Tier 1, `docs/reviews/M0-R1-coordinates.md`) and `gate` (Tier 2,
`docs/reviews/M0-R1-gate.md`) over `git diff 366b0b5..a8cfa63`; adjudication
`docs/reviews/M0-round1.md`: 11 P2 and 8 P3, all to the residue below. The lens split and
the P0–P3 scale (P0 a Hard Rule broken or a gate that cannot fail on the harm it names; P1 a
defect the owner or the next arc will hit; P2 a weakness with no current consumer; P3
clarity) are the supervisor's reversible choices (tick 3); the alternative was one lens per
brief pair.

**Decisions for the close:**
- Ratify: `height_offset_m` read as y = H − height_offset_m on both sides, pinned by tests
  (M0-02 Findings 5, M0-03 Findings 10). At the committed 0.0 it gives SPEC §6's "y = H
  (real LN02 metres, no vertical offset)"; what a non-zero value means is undefined.
- Ratify or remove: three gate checks beyond M0-03's list — import fails on any
  `valid=false` `.import` file, GUT fails on `[ERROR]`, ANSI codes stripped before scanning
  (M0-03 Findings 6); the first is a brain.md §Hazards candidate (H1's second half).
  R1 measured it (G-05): in every fresh cloud session it is the import step's only
  detector, since the hook's warm-up import discards Godot's errors; the lens says ratify.
- CLAUDE.md's `uv run --project pipeline gdlint game`, commented "vendored addons
  excluded", lints the vendored GUT (645 problems; `gdformat --check game`: 85 files). The
  gate's own file list is right. A root `gdlintrc`/`gdformatrc` or a changed CLAUDE.md line
  (M0-03 Findings 8).
- Follow-up candidates (M0-01 Findings 6): `uv lock --check` as a gate step (`--frozen`
  does not see a lockfile out of step with `pyproject.toml`); `.gitattributes`
  `*.sh text eol=lf` for the owner's Windows PC (unmeasured). R1 C-04 widens it: with
  `core.autocrlf=true` (simulated on Linux) `config/world.json` checks out with CRLF and
  `world_sha256`, so the manifest bytes, change; `config/**` and `tests/shared/**` too.
- Process slip recorded (M0-01 Findings 7): gate re-run after the push, not before; the
  pushed head's re-run exited 0.
- For design to know (M0-04 Findings 7): a re-run of `download terrain` fetches the six
  STAC items again; were swisstopo to republish a tile inside the 2024 edition, the file
  and `provenance.json` would change (visibly). Hard Rule 5's "same inputs" then rests on
  swisstopo not republishing within an edition.
- Audit the builder's reversible choices (M0-04 Findings 8): editions must be four-digit
  years; a damaged file on disk is deleted before its re-fetch; STAC item fetches are not
  retried; `provenance.json` fields and no `terms` string in it; progress on stderr,
  path on stdout. Not measured on Windows (Findings 9).
- Review R1 residue (`docs/reviews/M0-round1.md`): ten findings whose fix is unambiguous
  and inside an M0 brief's scope (C-01, C-02 part 1, C-03, C-06, C-08, G-01, G-04, G-06,
  G-07, G-09) — one cheap fix tranche if design wants it; ten more are design's call.
  Six name M1 as their first consumer (C-02, C-05, G-02, G-03, G-04, G-05): a tranche
  before M1, or M1's briefs carry them. C-05 and G-06 are one question (what is M1's tile
  list?). CLAUDE.md:27-28 says the gate fails on Godot error lines; the GUT step does not
  scan `^ERROR` (G-03).
- The lens sessions' closing summaries called their P2s "critical" / "priority-1"; the
  committed reports grade them P2 and are the record (lesson 30). Regrade here if design
  disagrees.

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
- M0 R1 residue, 11 P2 and 8 P3 (`docs/reviews/M0-round1.md`): C-01…C-09, G-01…G-10.

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
