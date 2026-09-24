# ARCS.md — the per-arc record

## M0 — Setup and the first M1 step · closed 2026-09-24 · no version

The close record (DESIGN.md rule 4: a close without a version writes it here). Part 1 is
the report-back, copied to chat; part 2 is the close in full.

### Part 1 — Report-back

**What M0 built.**
- The pipeline (Python 3.13 with uv and a committed lockfile). `python -m mattini manifest`
  writes the file from which the game learns the origin. `python -m mattini download
  terrain` fetches the six swissALTI3D 2024 tiles of the village (0.5 m, 108.3 MB) into
  `data/`, checks each against swisstopo's published SHA-256, never fetches a verified file
  twice, and records what it got in `provenance.json` with `© swisstopo`.
- `config/world.json`, read by both halves. The LV95 → Godot conversions agree bit for
  bit on the shared test points, and the origin is subtracted in 64-bit before anything
  becomes 32-bit.
- A Godot 4.6.3 project (the main scene is still empty) with GUT 9.6.1 and `WorldConfig`.
- `tools/gate.sh`, one command for every check, hardened against the three ways Godot and
  GUT were measured to exit 0 on a failure.
- Briefs: M0-01 `4475f6f`, M0-02 `1d53a00`, M0-03 `ff9e9d6`, M0-04 `a383cff`.

**Gate at the close.** On `main` `d8bcbcc`, run alone in a fresh worktree: exit 0. pytest
209 passed (2 network tests deselected); GUT 5 scripts, 13 tests, 943 asserts; 0
failures. The 41 `ERROR` lines are the ones the refusal tests provoke on purpose. The close
commit is chained to the same gate, re-run with the corrected test point: the same counts.

**Things you reported:** none. The inbox was empty, and nothing has reached you yet.

**What the review found** (round R1: two Opus reviewers, coordinates at Tier 1 and the gate
at Tier 2): no P0 and no P1. There are 11 P2 and 8 P3 findings, all weaknesses that no
code trips today:
- the determinism tests cannot see a field that changes by day or by machine;
- the check for a second copy of the origin misses some file types and spellings;
- the game's world → LV95 conversion is untested for 8 of the 24 rotations;
- a Windows checkout with default Git settings changes the manifest's bytes and breaks
  the gate script;
- four ways to switch the gate off or cut the test run short that the builders' own
  checks did not reach;
- a failed re-download leaves `provenance.json` listing a file it deleted;
- the download folder can keep tiles that `provenance.json` no longer lists;
- in a fresh cloud session, one check the builder added is the only thing that catches a
  broken asset at import.

One finding is fixed at this close (C-09: a test point rounded by 25 cm). The import
check is ratified (G-05). The rest are the first work of M1, before any M1 code that would
trip them.

**What M0 does NOT prove.**
- That anything renders: nothing is drawn yet, and the containers have no GPU.
- That your PCs get the same environment and bytes: nothing has run there. Windows line
  endings are a known break until M1 (brain.md H10).
- That no second copy of the origin exists: the check reads text only.
- That other editions and tiles name their files the same way.
- How the download behaves when the network drops mid-file, beyond the `.part` handling
  the tests cover.
- That every Godot error format is caught: the gate knows only 4.6.3's.
- That the pinned tests are right: design checked them against scratch implementations.

**For you to look at:** nothing yet, because nothing is drawn. Optional before M1 (a note,
never a gate): set up one PC. Install Godot 4.6.3 and uv. On Windows, clone with
`git clone -c core.autocrlf=false`. Then run `uv run --project pipeline python -m mattini
manifest` and `… download terrain`, and open `game/` in Godot. Anything odd goes to
`feedback`.

**Cost** (each session's own `usage.cost_usd`; this close cannot read its own, see the
usage page):

| Who | $ |
|---|---|
| Design, day one: the process, SPEC v0, the M0 briefs and pinning tests | 18.01 |
| Supervision: the waker 3.36 + four ticks 5.29 | 8.65 |
| Builders, two sessions | 9.38 |
| Review, two sessions | 9.74 |

Supervision cost 0.92 × the builders. That is under WORKFLOW's line, narrowly: a
four-brief arc barely pays back the waker's fixed cost. Design cost 1.9 × the builders,
and that includes the whole day-one scaffold. Wall-clock: go 03:44Z → READY TO CLOSE
05:50Z. About an hour of that was waiting, because every tick started at a scheduled
wake and none at a landing (ledger).

**Next.** M1 Terrain, planned in a fresh `design` session. Its first briefs carry the
review's fixes; then the downloaded tiles become Terrain3D terrain with a free-fly camera.
It will ask you three things: the in-game terrain resolution (0.5, 1 or 2 m), where the
game shows its version, and the version scheme. The first version is planned for M1's
close.

### Part 2 — The close in full

**Decisions** (RULINGS 2026-09-24, D1–D12; each keeps what was built unless it says
otherwise).

- **D1 · No version at the M0 close.** Nothing in M0 is playable: the main scene is an
  empty `Node3D`, so an export would be an empty window. A version also first needs two
  answers from the owner: where the game shows it (OPEN) and the scheme (PROPOSED, SPEC
  §11). The first version is planned for M1's close, and both questions are asked when M1
  is planned. RELEASE.md §B and §C do not apply (no bump); §A was walked (below); this
  record takes the place of `docs/releases/` (DESIGN.md rule 4, amended). Reversible: the
  owner can ask for a build of the empty project at any time.
- **D2 · `height_offset_m`** is kept as built (M0-02 Findings 5, M0-03 Findings 10). It is
  the vertical part of the origin: y = H − height_offset_m and back, pinned on both
  sides. At the committed 0.0 this is SPEC §6's "y = H". A non-zero value is a design
  change (SPEC §6 now says so).
- **D3 · The three gate checks beyond M0-03's list are kept.**
  - `valid=false`: in fresh cloud sessions it is the import step's only detector (R1
    G-05, runs k1 and k2).
  - GUT's `[ERROR]`: it catches a run that ran nothing (M0-03 run g).
  - ANSI codes stripped before scanning: a colour prefix cannot hide an `ERROR` line.

  brain.md H1 gains its second half. The hook's warm-up still discards its output: the
  gate names the broken file, and deleting its `.import` and importing again shows
  Godot's reason (brain.md H1).
- **D4 · CLAUDE.md's game-lint line was wrong as written.** It linted the vendored GUT
  (645 problems, M0-03 Findings 8). It now gives the gate's own file list; measured at the
  close, `gdlint` and `gdformat --check` pass with it. There is no root `gdlintrc` or
  `gdformatrc`: one list, the gate's.
- **D5 · `uv lock --check` joins the gate, and `.gitattributes` holds `* text=auto
  eol=lf` for the whole repository.** Both are M1 builder work.
  - `uv lock --check`, measured at the close: exit 0, offline, in 12 ms. `--frozen` alone
    does not see a lockfile out of step with `pyproject.toml` (M0-01 Findings 6).
  - `.gitattributes` widens M0-01 Findings 6 by R1 C-04. Measured at the close in a
    scratch clone: the index holds no CRLF file (309 LF, 22 binary, 5 with no line end),
    so `git add --renormalize .` stages nothing else. A `core.autocrlf=true` clone is then
    byte-identical to the LF checkout: `config/world.json`'s SHA-256 is `d2607d13…`
    instead of `fbc5b597…`, and `tools/gate.sh` has no CR.
  - Its test must show the harm, not the file: a checkout configured for CRLF gives the
    same bytes.
- **D6 · The M0-01 process slip** (the gate re-run after the push, not before; the pushed
  head's re-run exited 0) is recorded in the ledger. BUILD.md §Commits already says it.
- **D7 · A tile republished inside an edition** (M0-04 Findings 7). Today the change is
  visible (`provenance.json` changes), but nobody decides it, and two machines that
  download at different times can hold different inputs for one config. Ruled: the
  repository pins the SHA-256 of every tile the pipeline uses. The download refuses a
  published checksum that differs, naming the tile and both values, so adopting a
  republished tile is a deliberate change like a new edition. Built in M1 (SPEC §5). M1
  planning picks the form: a lock file under `config/` written by a pipeline command, or
  checksums in `datasets.json`.
- **D8 · M0-04's reversible choices (Findings 8) are all kept:**
  - editions must be four-digit years;
  - a damaged file is deleted before its re-fetch;
  - STAC item fetches are not retried (a re-run resumes);
  - `provenance.json` keeps its fields, without the `terms` string;
  - progress goes to stderr, the path to stdout.

  That nothing was measured on Windows (Findings 9) stays a does-NOT-prove.
- **D9 · M1's tile list (C-05 and G-06, one question).**
  - `provenance.json` is the only list M1's terrain step reads. That step refuses a
    `provenance.json` whose edition, resolution or tile list differs from what the
    current config asks for, and names `download terrain` as the fix.
  - The download removes `provenance.json` before its first change on disk (an unlink or
    a file fetch). So it exists only after a run that completed, and a run that fails
    before changing anything (offline, for example) leaves the previous one in place.
  - Stray `.tif` files from another box or resolution stay on disk, because nothing lists
    the folder. Removing or reporting them is declined.
- **D10 · The other design's-call findings** are ruled as in the carry-over table below:
  - C-02 part 2: the census also catches the kilometre spelling.
  - C-04: per D5.
  - C-07: `push_error` plus NaN.
  - C-09: fixed now, in `tests/shared/world_vectors.json`. The Matterhorn name point is E
    2617048.75, so x = −5951.25, re-read from swisstopo's gazetteer at the close (the two
    address points were re-read too, and match). Proved in both directions: the corrected
    pair passes the gate, and the old x (−5951.0) against the corrected easting fails
    two pytest and two GUT tests, one pair on each side.
  - G-02: only `All tests passed!` passes. A pending test is a skipped test; a risky one
    asserts nothing.
  - G-03: option (a).
  - G-05: per D3.
  - G-08: the check goes in a live test; the pinned copy stays unchanged.
  - G-10: `XDG_DATA_HOME` is set per gate run, plus brain.md H9.
- **D11 · Grades.** The committed reports' P2 grades stand. The lens sessions' closing
  summaries ("5 P1 gaps", "5 critical") overstated their own reports (ledger).
- **D12 · Timing.** M1's first briefs carry the residue, before any M1 brief that writes a
  shader, project settings, new manifest fields, a main-scene script or a Terrain3D test:
  the consumers the P2s name. There is no separate M0 tranche: the review found no P0 or
  P1, and a second M0 close would cost more than the fixes.

**Carried into M1**: 17 review findings, plus `uv lock --check` and D7. The first briefs
start from this table. Suggested split: two briefs whose Scopes share no file, so they can
run at once.

| id | grade | brief | the fix |
|---|---|---|---|
| C-01 | P2 | pipeline | Pin the exact bytes (golden) of the manifest and of `provenance.json` for fixed inputs, and their exact key sets. A later manifest field changes the golden on purpose. |
| C-02 | P2 | pipeline | The origin census reads every file `git ls-files -co --exclude-standard` lists, of any suffix, except `config/`, `tests/`, `docs/`, `game/addons/` and `pipeline/uv.lock`. It adds e-notation (`2.623e6`, `1096e3`, `1_096e3`) and the kilometre pair (`2623` followed within a few characters by `1096`). It still proves text only (lesson 5). |
| C-04 | P2 | pipeline | `.gitattributes` `* text=auto eol=lf` (D5), with a test that a checkout configured for CRLF gives the same bytes. |
| G-06 | P2 | pipeline | `provenance.json` is removed before the download's first change on disk (D9). Tests: a failed re-run after a damaged file leaves none; a run that fails before any change leaves the old one byte-identical. |
| G-08 | P3 | pipeline | A live test asserts `git ls-files --error-unmatch` for the hygiene test's listed paths that exist. |
| C-03 | P2 | gate and game | The game's rotation loop also asserts `to_lv95(to_local(p)) ≈ p` for all 24 rotations. |
| C-06 | P3 | gate and game | The random round trips draw 64-bit offsets, e.g. `randi_range(-20000000, 20000000) / 1000.0 + randf() * 0.001`. |
| C-07 | P3 | gate and game | A `WorldConfig` not built by `from_manifest` calls `push_error` when used and returns NaN, never a plausible origin. |
| C-08 | P3 | gate and game | An empty manifest is reported as "the manifest is empty". |
| G-01 | P2 | gate and game | The allowlist refuses an entry whose text is empty or blank. |
| G-02 | P2 | gate and game | The GUT step requires GUT's final line `---- All tests passed! ----`, after ANSI stripping (D10). |
| G-03 | P2 | gate and game | The GUT step also scans `^ERROR`, with one allowlist entry: `WorldConfig: user://test_world_config_ # the refusal tests provoke these on purpose`. Design then updates CLAUDE.md's gate paragraph. |
| G-04 | P2 | gate and game | `-gconfig=` on the gate's GUT command (measured by the lens, e3 and e4); CLAUDE.md's GUT line gets it with the brief. |
| G-07 | P3 | gate and game | `grep -a` in the scans. |
| G-09 | P3 | gate and game | A first Godot step requires `$GODOT --version` to start `4.6.3.stable`. |
| G-10 | P3 | gate and game | The gate exports `XDG_DATA_HOME` into its scratch folder for the Godot steps. On Linux this gives a fresh `user://` per run; it has no effect on Windows. |
| lock | — | gate and game | `uv lock --check --project pipeline` as a gate step (D5). |
| C-05, D7 | P2 | M1 terrain | The terrain step's check of `provenance.json` against the config (D9), and the pinned tile checksums (D7). |

Decided at the close and not carried: C-09 (fixed), G-05 (ratified, D3).

**RELEASE.md §A, walked at the close.**
- `git status` is clean.
- Every brief reads `DONE (<sha>)`, and each sha is on `origin/main`.
- The design realm wrote no production code. In `366b0b5..d8bcbcc` only the four `feat:`
  commits touch `pipeline/`, `game/`, `tools/`, `config/`, `tests/shared/` or `.claude/`.
  The close changes docs, CLAUDE.md and the shared test data.
- No brief carries an unfinished review.
- No census stands alone over load-time code. The origin census is a Hard Rule 4
  tripwire; the transforms and the main scene are tested by running them.
- Every gate's does-NOT-prove line is filled in; the set is in part 1.
- Attribution: no build is shared yet, and `© swisstopo` is in the config and in
  `provenance.json`, pinned by tests.
- No raw data or unmanaged binaries are in history. The largest blob is 235 KB, a vendored
  GUT font, and no raster or point-cloud suffix was ever committed.

**Sessions** (tag `M0`, with their cost):

| Session | Id | $ |
|---|---|---|
| Waker · M0 | `session_012t9Gvi7HQtMJDJFdZtvd9W` | 3.36 |
| Tick 03:45Z | `session_014hf7nKBEfYUKvLAPhozEqK` | 0.83 |
| Tick 04:46Z | `session_013c1o7eqEMpgV5P8LYyAnqE` | 1.11 |
| Tick 05:17Z | `session_01GXrQfvYt5ZUAHo2BNbt8HV` | 1.48 |
| Tick 05:46Z | `session_01ATZL94YefFAtheB99u8Jb5` | 1.87 |
| Builder · M0-01, M0-02, M0-03 | `session_01NSgBnxx9h39syb6PE5SYpA` | 6.47 |
| Builder · M0-04 | `session_01UMSSmssoyATV5gxuKB5rwj` | 2.91 |
| Lens · gate | `session_01EMAwuHwKi69zA8n735G7FD` | 4.83 |
| Lens · coordinates | `session_01T4q5GCbYTRUNAccbuwnQfK` | 4.92 |

Not tagged:
- the day-one design session "Getting started" (`session_016CuUgzTF2JDV5YxVjN1UbE`,
  $18.01), the owner's own;
- this close ("Design", `session_015Cf9YvRHVSL484aDyoY15A`).

Routines: the waker's hourly Routine is gone from the account's Routine list at the close
(tick 4 was to delete it at READY TO CLOSE). No M0 Routine remains.
