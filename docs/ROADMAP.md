# ROADMAP.md — the board

Open items only. Shipped and answered items live in `docs/history/` and
`docs/releases/`. Sources cited (`FB-nnn`, brief ids). Effort: **S** = part of a brief,
**M** = one brief, **ARC** = several.

## Open now

**Last shipped:** nothing yet.

### Arc M0 — Setup and the first M1 step

Supervision: ON · M0 · since 2026-09-24T03:44Z
Waker: session_012t9Gvi7HQtMJDJFdZtvd9W · Routine trig_01V6UzfBMJzJ7Z8dW3nYRKAf · since 2026-09-24T03:45Z
Last tick: 2026-09-24T04:48Z · main c546125 · ticks 2
Tick: session_01GXrQfvYt5ZUAHo2BNbt8HV · started 2026-09-24T05:17Z
Lens: session_01T4q5GCbYTRUNAccbuwnQfK · R1 coordinates · spawned 2026-09-24T05:20Z
Lens: session_01EMAwuHwKi69zA8n735G7FD · R1 gate · spawned 2026-09-24T05:20Z
Cost: waker $? · ticks $? · builders $9.38 · lenses $0 (a session cannot read its own dollar cost; read the usage page at the close)

**OPEN briefs:** none.

**DONE:** M0-01 (4475f6f), M0-02 (1d53a00), M0-03 (ff9e9d6), M0-04 (a383cff); full gate
green on a8cfa63 (tick 3: 209 pytest, 2 network tests deselected, 13 GUT tests, 0 failures).

**Review round R1** (WORKFLOW §Review policy), over `git diff 366b0b5..a8cfa63` without
`game/addons/` and `pipeline/uv.lock`, two lenses (at most two builds at once, lesson 20):
- `coordinates` — Tier 1: `config/world.json`, both transforms, the manifest, the shared
  vectors, the pipeline's determinism, the seams M0-02↔M0-03 and M0-02↔M0-04. Rounds until
  clean.
- `gate` — Tier 2: `tools/gate.sh`, the hygiene tests, the Godot project and GUT, the
  download's errors, licence and attribution, the seam M0-01↔M0-03. One round plus one
  verification pass over its fixes.
Reports: `docs/reviews/M0-R1-<lens>.md`. The lens split and the P0–P3 scale in the lens
prompts are the supervisor's reversible choices (tick 3): P0 a Hard Rule broken or a gate
that cannot fail on the harm it names; P1 a defect the owner or the next arc will hit; P2
a weakness with no current consumer; P3 clarity. The alternative: one lens per brief pair.

**Decisions for the close:**
- Ratify: `height_offset_m` read as y = H − height_offset_m on both sides, pinned by tests
  (M0-02 Findings 5, M0-03 Findings 10). At the committed 0.0 it gives SPEC §6's "y = H
  (real LN02 metres, no vertical offset)"; what a non-zero value means is undefined.
- Ratify or remove: three gate checks beyond M0-03's list — import fails on any
  `valid=false` `.import` file, GUT fails on `[ERROR]`, ANSI codes stripped before scanning
  (M0-03 Findings 6); the first is a brain.md §Hazards candidate (H1's second half).
- CLAUDE.md's `uv run --project pipeline gdlint game`, commented "vendored addons
  excluded", lints the vendored GUT (645 problems; `gdformat --check game`: 85 files). The
  gate's own file list is right. A root `gdlintrc`/`gdformatrc` or a changed CLAUDE.md line
  (M0-03 Findings 8).
- Follow-up candidates (M0-01 Findings 6): `uv lock --check` as a gate step (`--frozen`
  does not see a lockfile out of step with `pyproject.toml`); `.gitattributes`
  `*.sh text eol=lf` for the owner's Windows PC (unmeasured).
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
