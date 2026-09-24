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

### Fabricated instead of read

Nothing found in M0.

### Shipped defects the owner had to find

None in M0: nothing reached the owner.

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

### The net

- **M0**: four briefs built and verified, and one review round clean (no P0 or P1). 17 P2
  and P3 findings were carried into M1, and one was fixed at the close. No defect reached
  the owner.
