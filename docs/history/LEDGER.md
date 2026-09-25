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

### Fabricated instead of read

Nothing found in M0.

- **2026-09-25 · M1 · tick 9.** It wrote `Supervision: OFF · M1 · since
  2026-09-25T06:40Z (READY TO CLOSE)`; its commit `05f86ef` is 06:24:23Z and the session
  ended at 06:24:52Z, so the time was not read from any clock. Cost: none; the close took
  the commit's time. Guard: none new; a time on the board is a commit's or a tool's.

### Shipped defects the owner had to find

None in M0: nothing reached the owner.

None found at the M1 close: 0.1.0 is the first build that reaches the owner, and their
first look comes back through `feedback`.

### Wasted time and tokens

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

### The net

- **M0**: four briefs built and verified, and one review round clean (no P0 or P1). 17 P2
  and P3 findings were carried into M1, and one was fixed at the close. No defect reached
  the owner.
- **M1**: six briefs built and verified, one review round clean (no P0 or P1), and 0.1.0
  shipped. Of 18 P2 and P3 findings, two were fixed at the close, two declined, and fifteen
  carried into M2. Before the owner's first look, no defect is known to have reached them.
