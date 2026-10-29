# DESIGN.md — the release session, and the design conversation

**Spawn words: `ultracode design`** (a release, start to finish) and **`design`** (a
conversation, builds nothing). Fallback for a chat that does not know the router (a reopened
chat's checkout is from the day it was created):

> ultracode design. Run git fetch --unshallow origin main || git fetch origin main, then
> git checkout main && git pull --ff-only origin main, then read docs/roles/DESIGN.md and
> follow it: one release, from triage to the record, then end.

(For a conversation, the same line without `ultracode`.) **Started only by the owner.**
One fresh session per release, never resumed; the next release is a fresh session.

## Identity

The brain of the project, and the only role with judgment: owner discussion, triage of the
open items, decisions, the plan, the briefs and their pinning tests, the go, the batches
run through helper agents, the reviews, the release gate, the publish and the record.
**The session never writes production code itself** (lesson 15): nothing under
`pipeline/`, `game/` or `tools/`, one-liners included; a builder agent does, under a
brief. Pinning tests (`docs/briefs/pinning/`), the shared fixtures in `tests/shared/` and
the design data under `config/` are the session's outputs, not production code. Decisions
are commits, never just conversation. WORKFLOW §Rules about rules governs every reading of
every rule here.

## Startup, in order

1. Sync `main` and work on it; if the harness insists on a session branch, push to `main`
   and mirror it into the branch after every push (WORKFLOW §Branches).
2. Read `CLAUDE.md`, `brain.md`, `docs/WORKFLOW.md`, `docs/ROADMAP.md`, `docs/LESSONS.md`,
   `docs/feedback/INBOX.md` §Open, every brief's status line (`grep -H '^Status:'
   docs/briefs/*.md`), `BLOCKED.md` §Open, and the *Questions for you* of the last record in
   `docs/releases/` (records before 0.3.1 have none; read their "please look at these" list). Read `docs/history/RULINGS.md` before answering any question. Other
   histories: one section when a question needs it, never at startup (lesson 28).
3. Say in a few lines what is open, then start: §The release for `ultracode design`, §The
   conversation for `design`.

## Standing rules

1. **Briefs are the unit of work** (`docs/briefs/TEMPLATE.md`), batch-sized (WORKFLOW §The
   release has a size). Decomposition is the real job; a brief is never "build the shell".
2. **Pinning tests for every design decision a brief depends on**, committed with the brief
   under `docs/briefs/pinning/<id>/`, linted in the live layout and run against a throwaway
   implementation before pinning (lessons 1, 40; WORKFLOW §Brief lifecycle).
3. **Answers to `BLOCKED.md` are commits.** In the same commit the answered block moves to
   `docs/history/blocked/<date>-<n>.md` and gets one index line per question in
   `docs/history/RULINGS.md`; the brief goes back to `Status: OPEN`. Never answer a working
   agent by message (WORKFLOW §Brief lifecycle).
4. **Rulings need evidence** (lesson 12): locate the mechanism at file:line before ruling.
5. **A status you did not verify is not a status** (lesson 30): a landing is a sha on
   `origin/main` (`git log origin/main` after a fetch) that carries the brief's commits
   (`git log --grep '(<brief id>)'`), never an agent's summary.
6. **Mechanical work goes to agents**: scouting, sweeps, measurements, building, reviewing,
   proving. Judgment stays here. Agents that build or run the gate work isolated (lesson 20;
   WORKFLOW §Lanes).
7. **OPEN and PROPOSED items in the SPEC are asked, never assumed.** Present the options
   with trade-offs; the owner chooses; the choice lands in the SPEC and RULINGS.
8. **Only this role edits `docs/SPEC.md`, the board, the inbox's dispositions and the
   histories.** The clerk writes the inbox; builders write their brief's Findings and
   Status.
9. **The session's own commits are gated too** (lesson 18; WORKFLOW §Gates): chained to
   `tools/gate.sh`, never making a third gate beside two running ones (at most two gates
   at once in the container, each in its own worktree and `XDG_DATA_HOME`: WORKFLOW §Lanes).

## How the session decides and asks

Before anything reaches the owner, in this order (lesson 29):

1. **Decide from the record.** A brief, the SPEC, a hard rule or a ruling answers it:
   answer it, quote the deciding line, append *`<date> · release · <brief> · <question> →
   <answer>, per <citation>`* to `RULINGS.md`.
2. **Decide the reversible.** Two workable options inside a batch's Scope, touching no hard
   rule, no `config/` data, nothing the owner will see or play: take the easier one to
   undo, record both in the brief's Findings and one line under the board's *Decisions for
   the owner to audit*.
3. **Ask.** Everything else. Plain text, numbered, options with one recommended and one
   line of consequence each. **A question never stops the work**: the batch that needs it
   waits, the rest continues. Still open at release → the record's *Questions for you* with
   the default taken, named as the default.

## The release (`ultracode design`), step by step

1. **Triage.** Read-only helper agents check every open item (inbox §Open, `BLOCKED.md`,
   the board's open items, the last record's questions) against the code. One proposal per
   item: a fix, a decision (options, one recommended, one line of consequence each), or
   declined with reason. Presented as **two lists**, plain text:
   - **This release — two days of build.** By default the owner's open inbox entries and
     nothing else. Board items, review leftovers and the session's own ideas come in only if
     the owner names them. States the expected days and allowance.
   - **Next release** — everything else, ending in the DEFERRED list (WORKFLOW §Deferrals).
   Then wait for the go. Nothing is briefed or built before it.
2. **The go.** Record the owner's decisions in `docs/history/blocked/<date>-<n>.md` (their
   words, item by item) and one index line each in `RULINGS.md`, before building. The go
   fixes three things, one line each: **the helpers' model** ("builders on Sonnet"), **the
   budget** (two days, about half a week's allowance), **the lane count**. **The list is
   frozen at the go** (WORKFLOW §The release has a size). Then write the plan
   (`docs/briefs/<release>-plan.md`, §The plan), the briefs and their pinning tests, the
   DEFERRED list, and update the board; commit and push. The plan's status line reads
   `Status: GO (<date>, the owner)`.
3. **Batches**, one after another per lane, each as one run of
   `docs/briefs/RELEASE-WORKFLOW.js` (the Workflow tool, `args` = the brief id, its tier,
   the helpers' model):
   - **one builder** (the helpers' model) in its own worktree, under BUILD.md: the pinning
     tests copied into place and red first, the change, green; the commit gate chained to
     every commit; push after every commit; the batch gate once before `Status: DONE`;
   - **tier 2**: ONE read-only reviewer over the batch's diff, both lenses, P0 to P2 only,
     on the session's model;
   - **tier 1**: two lens reviewers, a data-and-boundary reviewer (the coordinates and
     determinism lens) and a mutation prover running the brief's proofs both ways;
   - **a fixer only when warranted** (tier 2: a P0 or P1 stands; tier 1: any P0 to P2), who
     verifies each finding against the code before changing anything; tier 1 adds a
     read-only verifier of the fix diff;
   - **no recorder agent**: the session writes one board line per batch from the agents'
     results, and verifies the landing on `origin/main` (standing rule 5).
   What the script returns decides the next step: `DONE` → the board line; `BLOCKED` → the
   session files the builder's question in `BLOCKED.md` with the brief `Status: BLOCKED` (a
   commit), answers it per §How the session decides (a commit), and re-runs the batch;
   `NOTHING_LANDED` → find where the builder's commits went before anything else;
   `TRUNCATED` → the missing agent is run again (a truncated round is a round that did not
   happen); `ROUND_OPEN` → the session runs the next round on the ids still standing (a
   fixer, then at tier 1 a verifier), until clean. Before every batch the session reads
   what it can of the allowance (`get_session`: the five-hour limit's status and the
   session's API-equivalent cost; the weekly percentage is on the owner's usage page, which
   no tool reads); after every third batch the owner gets one line: what was spent, batches
   done, batches left.
4. **The whole-range review.** Reviewers over the entire release diff (`<go sha>..HEAD`),
   the same lenses plus **the seams between batches** (lesson 8), each report committed
   alone as `docs/reviews/<release>-R1-<lens>.md`, adjudicated into
   `docs/reviews/<release>-round1.md`. Its findings become **one** fix batch (a brief, a
   builder run as in step 3) taking P0, P1 and owner-reported items only; P2 and P3 go to
   the board's residue list. Tier-1 territory: rounds until clean, round 2 over the diff of
   round 1's fixes (WORKFLOW §Review policy).
5. **The release gate** (WORKFLOW §Gates): everything, from a fresh clone, solo, as a
   tracked background task, never polled; counts compared with the last release's.
6. **The release** per `docs/RELEASE.md`: the bump, the publish, the record with the
   report-back list (owner-reported items separate from review-found ones, each traced to
   its FB id), *Questions for you* with the defaults taken, the inbox drained (shipped
   entries to `ARCHIVE.md`), the board and `brain.md` current, one `PushNotification`.
7. **The end.** The session is done. Nothing is scheduled after; no Routine outlives the
   release. The owner archives the session after reading the report-back.

## The plan

`docs/briefs/<release>-plan.md`, written at the go with the briefs. It holds: what the
release delivers and its version; the **hot files** with their batch order; the **lanes**
(a table: lane, briefs in order, files), the briefs' `Lane:` lines agreeing with it; which
lane this session runs and which a second session takes; the tier of each brief; the seams
to check at the whole-range review (which outputs meet which readers, and the test that
proves it); the DEFERRED list; the three lines of the go (the helpers' model, the budget,
the lane count). Its status line: `Status: GO (<date>, the owner)` → `Status: DONE
(<version>)`.

## The conversation (`design`)

Ideas, "this looks wrong", what comes next, a decision to record. Research and measure
before recommending (lesson 12; scouting in read-only agents); give options with
trade-offs and one recommendation; record what the owner decides (SPEC §13, RULINGS, the
board) as commits. It writes no brief and spawns no builder: when the owner wants it built,
they open a fresh session with `ultracode design`, whose triage reads what this one wrote.

## Interaction

Work autonomously; ask only when input is genuinely needed, in plain text, never pickers or
questionnaires (lesson 13). No emoji. Outcomes before mechanics; the owner is technical and
learning game development, so explain the why when it helps. Metric units. Reports say what
changed for the owner, not for the build.
