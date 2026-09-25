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

## M1 — Terrain · closed 2026-09-25 · version 0.1.0

The report-back is the release record, `docs/releases/v0.1.0.md` (DESIGN.md rule 4); this
is the close in full. Arc: the go `e83a36a` at 04:01Z, READY TO CLOSE `05f86ef` at 06:24Z
(the board said 06:40Z; the commit's time is the record), six briefs, one review round.

**Decisions** (RULINGS 2026-09-25, D13–D21; numbered on from M0's D1–D12; each keeps what
was built unless it says otherwise).

- **D13 · The builders' reversible choices are kept:** M1-01 Findings 6 (the lock check's
  order, `load_lock`'s strictness, the module layout), M1-02 Findings 6 (`run_godot`, the
  step order, WorldConfig's `_built` flag and its own NaN test), M1-03 Findings 6 (the
  resampling as the plain 64-bit window mean, which equals the area-weighted mean because
  every window's pixels are equally covered, measured by the terrain lens at all three
  spacings; the refusal order; the terrain config's strictness; how `manifest` reads the
  description; `progress`), M1-04 Findings 8 (TerrainGrid's extra refusals and order; no
  NaN scan, since the SHA-256 ties the file to the pipeline, which refuses non-finite
  heights; no out-of-tree guard, since the failure is a loud `SCRIPT ERROR`; `shot.gd` and
  `shot.sh`'s choices; `LC_ALL=C sort`), M1-05 Findings 6 and 7 (exposure 0.85, the credits
  a RichTextLabel, the error panel through a `Logger`, the controls from the InputMap, the
  camera's numbers, `canvas_items` at 1280 × 720, the sky's ground colours, `shot.gd`
  rendering `main.tscn`: the look and the controls are the owner's to react to through
  `feedback`), M1-06 Findings 9 (all kept; its unscanned export output joins G-02's fix).
- **D14 · 0.1.0 ships at this close, without a fix tranche first.** The round found no P0
  and no P1. The three residues whose first consumer is this release were done by hand
  here: T-01's real-data half (`village.f32` rebuilt from the pinned tiles is `b6334c1f…`),
  G-02 (the exported Linux build started: its startup line, no `ERROR`) and G-08
  (RELEASE.md §B). The rest go into M2's first briefs, D12's pattern: a separate M1
  tranche would hold back the owner's first look for fixes no current code trips.
- **D15 · The layout of `dist`** replaces "`*-previous.*`", which cannot work for this
  export: each executable finds its `.pck` by its own name, and Terrain3D's library keeps a
  fixed name. `windows/` and `linux/` hold the current version under fixed names;
  `mattini-<version>/windows/` and `…/linux/` hold each version under its name; the last
  three named folders are kept, and the one before the current is the rollback. A
  `README.md` says how to download, start and roll back, with every file's SHA-256; a
  `.gitattributes` (`* binary`) keeps a `core.autocrlf=true` clone from touching the
  builds. SPEC §11, RELEASE.md §C and §E, WORKFLOW §Pace and risk and FEEDBACK.md's
  `crash` line follow. Reversible: nothing reads `dist` but people.
- **D16 · An export over 100 MB (SPEC §14) stays OPEN:** nothing is over at 0.1.0. The
  largest file is `mattini.exe`, Godot 4.6.3's Windows release template unchanged, at
  104'659'456 bytes, 198 KB under GitHub's 104'857'600; each `.pck` is 96'124'108 bytes,
  8.3 MiB of room. M2's buildings go into the `.pck`, so M2 planning asks it before M2's
  first build brief, with the options: a second resource pack for the heights (loaded at
  start), the heights compressed by the pipeline (measure first), Git LFS on `dist` (a
  quota), GitHub Releases (assets up to 2 GiB; uploading from a container is unmeasured),
  or a coarser spacing (the owner's call, SPEC §7).
- **D17 · godot-cpp's notice (R1 G-06).** Terrain3D's library compiles in godot-cpp (MIT,
  "Copyright (c) 2017-present Godot Engine contributors"). The credits carry its notice:
  M2's first game brief adds it, and RELEASE.md §A names it from now on. 0.1.0 lacks it;
  it is the owner's own build, and the record says so before it is shared.
- **D18 · Grades.** The committed reports' grades stand. The game lens session's summary
  in the session list called G-01, G-02 and G-03 "P1s"; its report grades them P2, each
  resting on a harm a future change would meet (lesson 30; M0's D11, again).
- **D19 · The residue** (18 findings): G-08 and the SPEC half of T-08 fixed at this close;
  T-09 and T-10 declined; fifteen carried into M2 with the fix named (the table below).
  T-01 and T-02 need design data, which M2 planning computes two independent ways, as it
  did the M1 fixture.
  - T-09 declined: the builder's own `test_a_rotated_world_is_refused_for_its_axes` sees
    the axes check go (M1-04 run e), and the pipeline refuses a rotated world before it
    writes anything.
  - T-10 declined: the worst variant is a refusal that names the fix, never a wrong
    terrain; every file read is still hashed against provenance and the lock.
- **D20 · The known items.** brain.md H11 is corrected twice: the fresh-checkout abort
  (M1-04 Findings 1) did not reproduce in any fresh-checkout run since design's one
  measurement (the M1-04 builder's eleven, the game lens's two, this close's export), and
  the extension-list step stays, as it costs nothing; and Terrain3D looks for its
  camera at its first physics frame, not on entering the tree (M1-05 Findings 1). M1-06
  Findings 2 is noted; the filter is needed and G-02 covers the class. M1-02 Findings 8 is
  in the ledger. M1-06 Findings 5–7 are on the owner's list in the release record.
- **D21 · The board's items for design.**
  - The waker's due rule counting OPEN briefs whose dependencies are not DONE: measured, no
    tick was wasted (each of the nine had a landing, a report or the go behind it). No
    rule change.
  - Landing wakes: working. Every tick started 0.5 to 5 minutes after the landing or report
    that made it due (the builders' and lenses' `fire_trigger`, without `text`). M0's
    ledger item is closed.
  - The spawn prompts' sync line: carried to M2 planning, which writes the next spawns.
    Measured twice, the same shape: a checkout whose local `main` is an old ref that the
    shallow clone's boundary hides as an ancestor, so `git fetch` says "forced update" and
    `git pull` says "diverged" (M1-05 Findings 8; this close, where `git fetch --unshallow`
    showed `6364451` to be an ancestor of `origin/main`). Proposed: `git fetch --unshallow
    origin main` when `git rev-parse --is-shallow-repository` says true, then `git pull
    --ff-only origin main` (brain.md H14).

**Carried into M2**: fifteen findings, first work of the arc, before any M2 brief that
writes a manifest block, chunk-grid code, a loader, the terrain material or the export.
Suggested split: a pipeline brief and a game-and-tools brief, whose Scopes share no file,
so they can run at once.

| id | grade | brief | the fix |
|---|---|---|---|
| T-01 | P2 | pipeline | (a) A build test from at least 2 × 2 synthetic tiles, with an area that cuts the outer tiles, pinned to exact bytes design computes two ways. (b) The expected SHA-256 of each built terrain is design data in `config/terrain.json`, per area and spacing (the village at 0.5 m `b6334c1f…`; 1 m and 2 m computed at M2 planning); `terrain` fails when its output differs, naming both values; `manifest` refuses a terrain whose SHA-256 is not the expected one. Until built, RELEASE.md §C's line. |
| T-03 | P2 | pipeline | `build_terrain`'s own output for a fixed synthetic input pinned to exact bytes (T-01's test can do it); `manifest` requires exact key sets for `source` and each of its `tiles`. |
| T-04 | P2 | pipeline | `manifest` compares the block's `source` with the lock (each tile's SHA-256) and with `config/datasets.json` (attribution, collection), refusing and naming `terrain`. The fourth member, the pipeline's own code, is closed by T-01 (b): a changed rule changes the bytes. |
| T-05 | P2 | pipeline | The census also catches the kilometre pair reversed, the pair on lines up to three apart in either order, and a mantissa with trailing zeros (`2.6230e6`). It still proves text only (lesson 5). |
| T-06 | P3 | pipeline | One home for the area the pipeline serves: `download terrain` and `lock terrain` read it from `config/terrain.json`. |
| T-07 | P3 | pipeline | The tracked-files test scoped by exclusion (lesson 37), so the fixture and Terrain3D's binaries are covered. |
| T-08 | P3 | pipeline | The live rules test's docstring states SPEC §8's condition: one rounding while the offset subtracts exactly. |
| T-02 | P2 | game | A second shared fixture north-west of its origin, crossing a row of regions, at 2 m, its heights computed by design two ways; the loader tests read it back on its own vertices. |
| G-01 | P2 | game | A test reads `show_checkered` (false), `shader_override_enabled` (true) and the override's `resource_path` on the loaded terrain. The `height_offset_m` uniform stays a does-NOT-prove line until an arc changes the material (M3, M4). |
| G-02 | P2 | game and tools | `tools/export.sh` scans the export's output for `ERROR` lines and gains a step 6: start `build/linux/mattini.x86_64 --headless --quit-after 300` and require the startup line with the manifest's columns, rows and spacing, and no `ERROR` line. The live preset test pins the include filter exactly. |
| G-03 | P2 | game and tools | The unbuilt-WorldConfig allowlist entry stops being global: the test's deliberate object is marked so that an entry scoped like the others (`user://test_…`) covers it, or the entry is scoped to its one test script. M2 planning picks the mechanism. |
| G-04 | P3 | tools | The GUT step compares GUT's last `---- ` line, as its comment says. |
| G-05 | P3 | game | The live version test checks every visible `Control` with a `text` outside the pause menu, not only `Label`s. |
| G-06 | P3 | game | The credits carry godot-cpp's MIT notice (D17). |
| G-07 | P3 | tools | `tools/shot.sh`'s header and usage name M1-05's views (`name`, `name,pause`) and the error-panel capture. |

Also for M2 planning: D16's question to the owner, the spawn prompts' sync line (D21), and
the design data T-01 and T-02 need.

**RELEASE.md, walked at the close.**
- §A. `git status` clean. Every brief reads `DONE (<sha>)` and each sha is on
  `origin/main`. The design realm wrote no production code: in `e83a36a..05f86ef` only the
  six `feat:` commits touch `pipeline/`, `game/`, `tools/`, `config/`, `tests/` or
  `.claude/`; M1 planning (`b2b58b1`) committed design data, the shared fixture and pinning
  tests (DESIGN.md rule 5), and this close changes docs only. No brief carries an unfinished
  review. No census stands alone over load-time code: the scenes and loaders are tested by
  running them, and the export was started. All 32 gates carry a does-NOT-prove line; the
  set is in the release record. Attribution: the credits read `swissalti3d 2024, ©
  swisstopo`, then Godot's licence and its components', then Terrain3D 1.0.2's (the R1 game
  lens, from the real manifest; the `.pck` holds `© swisstopo` twice and Terrain3D's
  `LICENSE.txt`); godot-cpp's is D17. No raw data or unmanaged binary entered history: the
  largest blobs are the four vendored Terrain3D binaries (3.3 to 4.2 MB, byte-identical to
  the release zip, SPEC §9), and the only `.f32` files are the synthetic fixture's two.
- §B. `0.1.0` in `game/project.godot`, shown on the pause screen only (the pinned test; the
  lens's reading). Full gate from a clean worktree of `05f86ef`, to a log: exit 0 in 63 s,
  pytest 367 passed, 3 deselected, GUT 15 scripts, 69 tests, 1641 asserts.
- §C. In a fresh worktree of `05f86ef`: `download terrain` 6 tiles verified, 6 fetches,
  `provenance.json` `28523b17…`; `terrain`: `village.f32` `b6334c1f…` (96'040'004 bytes),
  manifest `0e4572fb…`; `tools/export.sh` exit 0 in 75 s, with a fresh templates folder, so
  the templates were downloaded (1'255'918'323 bytes) and checked against the pinned
  SHA-256; no `ERROR` line in its output, and no `Aborted` though nothing wrote
  `extension_list.cfg` first. The six files have M1-06's sizes; `mattini.x86_64` and
  `mattini.exe` equal Godot's release templates byte for byte, the libraries the vendored
  Terrain3D ones; the two `.pck` files are identical to each other (`9fca1a21…`) and differ
  from earlier exports at the same size (nothing claims a byte-reproducible export). The
  Linux build started: `--headless --quit-after 300`, exit 0 in 5.3 s, the startup line,
  no `ERROR` line. The `dist` commit `2e81625` (orphan, the first) carries the version, the
  source sha and the gate's line; pushed plain as a new branch in 36 s; GitHub warned about
  three files over 50 MB and refused nothing.
- §D. The release record was committed before the chat message; the board was updated and
  the arc's narrative moved here; no Routine is enabled on the account; the ratio is in the
  record.

**Sessions** (tag `M1`, cost from each one's `usage.cost_usd`):

| Session | Id | $ | At the close |
|---|---|---|---|
| Waker · M1 (04:01Z–04:20Z) | `session_01RJDQ3THu2YpVyofW3Pn924` | 1.68 | archived |
| Waker · M1 (04:20Z–05:22Z) | `session_019do6LK4hFYQ9c4ykJwQcNw` | 1.70 | archived |
| Waker · M1 (05:22Z–06:25Z) | `session_01EEAeJBE7KpsQsoGUEmhTVm` | 2.27 | archived |
| Tick 1 · 04:02Z | `session_0155cpPoMH3XqcqMNUWBiH7a` | 1.31 | archived |
| Tick 2 · 04:15Z | `session_01H8a28u2bPTo3gpVd4cxyVe` | 1.24 | archived |
| Tick 3 · 04:22Z | `session_01RDGSCQm3yq8URfoMD7YVDJ` | 0.97 | archived |
| Tick 4 · 04:31Z | `session_01QHegXTq5Z4seMJyWAbX2HR` | 1.00 | archived |
| Tick 5 · 04:54Z | `session_01Nf7BgWfr9p8KWviRiSQHKG` | 1.19 | not archived: the auto-mode classifier refused it; left for the owner |
| Tick 6 · 05:26Z | `session_01R7sAANf4bkpLp1n8jYopTa` | 1.29 | archived |
| Tick 7 · 05:39Z | `session_01X6QWucdq2PdcnnthGwjLX9` | 1.98 | not archived: refused likewise; left for the owner |
| Tick 8 · 06:14Z | `session_01HcaQDdwr1EXLVPJNNdRAWG` | 1.00 | archived |
| Tick 9 · 06:19Z | `session_011aAzn6wpccxzxsPN2VtCqW` | 2.01 | archived |
| Builder · M1-01, M1-03 | `session_01UxbykwYFJSxYM4GVUxoxky` | 7.50 | archived |
| Builder · M1-02, M1-04 | `session_018DsC2M2fzoruSxhZSkXs3Z` | 12.38 | archived |
| Builder · M1-05, M1-06 | `session_01C1AkkQheFeaoMGMvdomW9k` | 11.01 | archived |
| Lens · M1 R1 · terrain | `session_01XJY3cAYkoCiJxwb7EVLcki` | 8.89 | archived |
| Lens · M1 R1 · game | `session_01AkH5MvA3pEEQS5zJF8BEzF` | 8.81 | archived |
| ⚡ Waker · M1 · hourly wake (stray, brain.md H13) | `session_01QSSgKNoYUzz1jYhNjBjCES` | 0.24, read at the go | gone: `get_session` finds none |

Not tagged:
- the M1 planning session "Design" (`session_012KGaYP1VjcM8pR799MMjb1`, $36.44), the
  owner's own, left as it is;
- this close ("Design", `session_012bXTsixRhS7anZasuSVnLC`), which cannot read its own
  cost.

Totals: design 36.44 (planning) · supervision 17.64 (wakers 5.64, ticks 11.99) · builders
30.89 · review 17.70 · stray 0.24. Supervision 0.57 × the builders; design's planning
1.18 × the builders.

Routines: none is enabled on the account at the close. The waker's hourly Routine
(`trig_01LxXVtmJjWGmvzExTFWz4m9`) is gone; the two M1 30-minute one-shots still listed
fired and disabled themselves (`run_once_fired`). No M1 Routine remains.
