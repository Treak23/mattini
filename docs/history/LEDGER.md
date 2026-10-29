# LEDGER.md — the failure ledger

What the agents got wrong on mattini, what it cost, and what now guards it. Written at
arc closes; opened one section at a time, never at startup.

### Not following instructions

- **2026-09-24 · M0 · the M0-01 builder.** A rebase before the push brought in a board
  commit, and the gate was re-run only after the push, not before it (BUILD.md §Commits).
  Cost: none. The rebase brought docs only, and the pushed head's re-run exited 0. The
  builder recorded it itself (M0-01 Findings 7). Guard: BUILD.md §Commits, unchanged.
- **2026-09-24 · M0 · the two R1 lens sessions.** Their closing summaries, which the owner
  sees in the session list, graded P2 findings as "5 P1 gaps" and "5 critical". The
  committed reports grade them P2. Cost: none, because the tick adjudicated from the
  reports. Guard: lesson 30 (an agent's summary is not a status). The close read the
  reports, and D11 keeps their grades.
- **2026-09-25 · M1 · the M1-02 builder.** Its Findings commit was pushed after a rebase
  that brought one board commit, without re-running the gate (M1-02 Findings 8). Cost:
  none; the re-run on the pushed head exited 0, and the builder recorded it. The second
  time: M0-01 made the same slip. Guard: BUILD.md §Commits, and as the backstop the tick's
  full gate on every landing (SUPERVISE §The tick 3), which runs whether or not the builder
  re-ran it.
- **2026-09-25 · M1 · the game lens.** Its summary in the session list called G-01, G-02
  and G-03 "P1s"; its committed report grades all three P2. Cost: none; tick 9 adjudicated
  from the report, and D18 keeps its grades. The second time (M0's D11). Guard: lesson 30.
  The summary is written from the session's transcript, not by the report, so a line in
  the lens prompt may not change it.
- **2026-09-25 · M1 · design at the go.** A test `fire_trigger` with `text` started a
  stray session ("⚡ Waker · M1 · hourly wake", no repository, $0.24). Cost: $0.24; the
  session is gone at the close. Guard: brain.md H13, and "without `text`" in BUILD.md step
  3 and SUPERVISE §Review rounds.
- **2026-09-25 · M2 · design (the one M2 session).** DESIGN.md rule 2 and lesson 1: two
  briefs' pinned tests were pinned without being run where they would live. M2-03's
  `test_sheets.py` failed ruff's import order once its module existed. M2-05's three game
  tests failed as pinned: a helper overrode `Object._set`, `generate_normals` smoothed, and
  16-bit normals were compared exactly. Cost: two BLOCKED rounds and two merges finished by
  hand. Guard: lesson 40; M2-08's and M2-09's pinned tests were run against the live code
  before pinning.

- **2026-10-24 · process change · the session that adopted the one-session process.** It committed
  the owner's adopted process to its harness branch `claude/festive-dirac-fd2rke` only; `main` never
  got it, and the next session (started with the new spawn word) found it there and merged it
  (`bb1d547`), with a SPEC §13 row both sides had numbered 47. Cost: a merge; nothing lost (the janitor
  never deletes a diverged branch). Guard: WORKFLOW §Branches (push to `main`, mirror into the harness's
  branch), DESIGN.md startup 1.
- **2026-10-26 · 0.3.1 · the v0.3.1-05 builder.** Its code commit's gate ran as `( time tools/gate.sh >
  gate.log ) | tail`, so the exit status did not decide the commit (BUILD.md card 1, lesson 7); the
  builder read the log's last line before committing and recorded the slip. Cost: none (the log read
  `all steps passed`, and the batch gate passed again from a clean worktree). Guard: card 1, unchanged.

### Fabricated instead of read

Nothing found in M0.

- **2026-09-25 · M1 · tick 9.** It wrote `Supervision: OFF · M1 · since
  2026-09-25T06:40Z (READY TO CLOSE)`; its commit `05f86ef` is 06:24:23Z and the session
  ended at 06:24:52Z, so the time was not read from any clock. Cost: none; the close took
  the commit's time. Guard: none new; a time on the board is a commit's or a tool's.
- **2026-09-25 · M2 · M2-05's builder and design's check of it.** `complete_world.gd`
  said its box stood on the terrain, and the box's roof lay 4 m under the fixture's ground;
  every main-scene test used it and passed (R1 P-01). Cost: none shipped; a placement
  test the arc thought it had was missing until M2-08. Guard: lesson 42;
  `test_scene_placement.gd` checks the ground between floor and roof.

### Shipped defects the owner had to find

None in M0: nothing reached the owner.

None found at the M1 close: 0.1.0 is the first build that reaches the owner, and their
first look comes back through `feedback`.

### Wasted time and tokens

- **2026-10-25 · 0.3.1 · the batch machinery before its first run.** The adopted process told a builder
  in a worktree to `git push origin main`, which from the worktree's own branch pushes nothing and exits 0:
  every batch would have reported DONE with nothing on `main`. Found by the triage's process scout before
  any batch ran, fixed in BUILD.md and `RELEASE-WORKFLOW.js` (`git push origin HEAD:main`, the ancestry
  check, the NOTHING_LANDED status). Cost: none. Guard: lesson 50.
- **2026-10-26 · 0.3.1 · a container restart.** The platform restarted the session's container four
  minutes into batch v0.3.1-04's first run, with nothing heavy running; the builder had copied its pins and
  written no code. Cost: about five minutes and a re-run from the same commit. Guard: push after every
  commit; a landing is a sha on `origin/main`.
- **2026-10-26 · 0.3.1 · the release gate's first launch.** Its timing wrapper (`/usr/bin/time`) does not
  exist in the container, so the first gate never ran; the agent saw it in the log and ran it again. Cost:
  minutes.

- **2026-09-24 · M0 · no landing started a tick.** All four ticks began at a scheduled
  wake: the hourly one at :45, or the 30-minute one-shot at 05:16. Each came 9 to 53
  minutes after the landing or report that made it due:

  | Landing or report | Next tick |
  |---|---|
  | M0-02 at 03:53 (M0-04 could have started) | 04:46 (M0-04 spawned then) |
  | M0-03 at 04:07 | 04:46 |
  | M0-04 at 04:57 | 05:17 |
  | the lens reports at 05:38 | 05:47 |

  About an hour of the arc's two hours was waiting. Nothing this close can read records
  why. Either the builders and lenses did not fire the waker's Routine (BUILD.md step 3,
  SUPERVISE §Review rounds), or the fire failed, or the waker judged those wakes not due.
  Cost: wall-clock only. Guard: none yet. The board carries a check for the M1 go.
- **2026-09-24 · M0 · cost of the arc.** Readable costs:
  - day-one design (the whole process scaffold, SPEC v0, the M0 briefs): $18.01;
  - supervision: $8.65;
  - builders: $9.38;
  - review: $9.74.

  Supervision cost 0.92 × the builders: a four-brief arc barely pays back the waker's
  fixed cost. The close's own cost is on the owner's usage page.
- **2026-09-25 · M1 · landing wakes, fixed.** M0's hour of waiting did not come back.
  Every tick started 0.5 to 5 minutes after the landing or report that made it due
  (builders and lenses fired the waker's Routine without `text`):

  | Landing or report | Next tick |
  |---|---|
  | M1-01 DONE, 04:14:41 | 04:16:14 |
  | M1-02 DONE, 04:18:58 | 04:23:57 (a waker hand-off between) |
  | M1-03 DONE, 04:30:28 | 04:31:55 |
  | M1-04 DONE, 04:54:28 | 04:55:00 |
  | M1-05 DONE, 05:24:21 | 05:26:22 (a waker hand-off between) |
  | M1-06 DONE, 05:38:08 | 05:39:52 |
  | terrain lens report, 06:12:56 | 06:14:39 |
  | game lens report, 06:18:45 | 06:20:26 |

- **2026-09-25 · M1 · cost of the arc.** Design's planning $36.44 (one session; its
  context had grown to 741K tokens by its end); supervision $17.64 (three wakers 5.64, nine
  ticks 11.99); builders $30.89; review $17.70; the stray session $0.24. Supervision cost
  0.57 × the builders (M0: 0.92). Design's planning cost 1.18 × the builders: most of it
  was measurement that the builders then did not have to repeat (Terrain3D's traps, the
  software renderer, the fixture computed two ways), but a context of 741K re-read at every
  call is lesson 32's mechanism in a design session; the next planning can send its sweeps
  and measurements to Opus agents and keep its own context small (DESIGN.md rule 7).
- **2026-09-26 · M2 · pinned tests that cannot tell the decision from its twin.** Lesson 34
  again, three times in design's own pins: the camera test accepts a corner and the lowest
  vertex (V1-G-02), the sample test accepted a turned triangle (M2-09's check, fixed at the
  close), and no test tells the canonical lock form from an unsorted one (V1-P-08). Each
  was found by a checker's or lens's mutation, none by the gate. Cost: two carried P3s and
  one close-time fix. Guard: lesson 34 in design's pinning, and the checkers' own mutations.
- **2026-09-26 · M2 · cost of the arc.** One session did planning, nine briefs, the
  review, the verification pass and the close; its `usage.cost_usd` is in the release
  record. It is not separable by role, so there is no supervision ratio. M1 cost $102.87
  over twenty sessions. The account reached the seven-day limit's warning during the close.

### The net

- **M0**: four briefs built and verified, and one review round clean (no P0 or P1). 17 P2
  and P3 findings were carried into M1, and one was fixed at the close. No defect reached
  the owner.
- **M1**: six briefs built and verified, one review round clean (no P0 or P1), and 0.1.0
  shipped. Of 18 P2 and P3 findings, two were fixed at the close, two declined, and fifteen
  carried into M2. Before the owner's first look, no defect is known to have reached them.
- **M2**: nine briefs built and checked, one review round clean (no P0 or P1) and its
  fixes verified, and 0.2.0 shipped. Twenty-one R1 findings: eighteen fixed by M2-07 and
  M2-08, two by the close, I-07 moved to M5. Seventeen V1 P3s: one fixed at the close,
  sixteen carried into M3. Before the owner's first look, no defect is known to have
  reached them.
- **0.3.1** (the first release of the one-session process): six batch briefs built, each reviewed;
  the whole-range review clean of P0-P2; the release gate green from a fresh clone; shipped on `dist`.
  Before the owner's first look, no defect is known to have reached them.
- **0.4.0** (the first release to run two lanes, on the owner's word): eleven batch briefs built and reviewed (six at tier 1 with
  provers); the provers found real unpinned guards in 01, 02, 07 and 08, each closed by a test-only round 2 and a read-only
  verifier; the whole-range review clean of P0 and P1; the release gate green from a fresh clone. The `dist` push was refused by
  the auto-mode classifier and waits for the owner's word. Process slips: batch 06's first run was BLOCKED (the catalogue's host
  reset every connection; answered by a commit); every tier-1 brief had only pinned copies in its Scope, so a prover's gap
  could not be closed in-round (lesson 51); two batch builders ran their commit through a separate gate call because the shell
  refused a `&&` chain with git (the gate's exit was read alone, then the commit: nothing committed on a red gate); one
  whole-range-review sub-reviewer's finding (an empty Findings table) was stale (it read only the feature commit).
