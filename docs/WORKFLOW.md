# WORKFLOW.md — the three-realm process

The expensive model goes where judgment matters, the cheaper model where tokens burn, and
the repo, never chat history, carries state between sessions. This file is the shared
skeleton; each realm's rules live in its role doc (`docs/roles/DESIGN.md`, `BUILD.md`,
`SUPERVISE.md`, `FEEDBACK.md`). Rules cite lessons by number (`docs/LESSONS.md`); lessons
1–32 are the ones the process was born with (start.md Part 5, I1–I32), this project's own
follow.

## Spawning a realm (owner's manual)

Open a fresh Claude Code session on this repo and type one line:

- **`design`** — ideas, feedback discussion, "this looks wrong", what's next, reviews,
  releases.
- **`ultracode build`** — a builder: works every OPEN brief to green, then stops.
- **`feedback`** — the clerk: send bugs, ideas and screenshots as they happen; it answers
  only "Filed as FB-NNN".
- **`supervise`** — normally started for you by the design chat at an arc's go; typed by
  hand it runs one tick, which is how you nudge an arc that seems stuck.

A reopened old chat is a time capsule (its checkout is from the day it was created):
re-send the word; if it flounders, paste the fallback prompt from the role doc's header.
Design arguments belong in `design`, never with a builder or the clerk.

**Your two settings, once:** pick **Auto** in the mode selector before the first message
of every session you open (a spawned session is never more permissive than its parent).
In your claude.ai connector settings, set every connector tool that sends, deletes,
shares or trades to need your approval (§Permissions).

## Rules about rules

1. **Rules bind the agents, never the owner.** A rule protecting something from AGENT
   action never blocks building what the owner asks for; the answer to a risky feature
   is confirmation, scope and recoverability, not refusal (lesson 11).
2. **The owner's explicit word overrides any process rule** except the absolutes: no
   secrets in the repo, no unrecoverable loss of the owner's work. (There is no
   never-happen rule: the owner chose none, 2026-09-24.) An override costs one recorded
   line where the decision lands.
3. **One home per rule.** Other docs link to it.
4. **A rule states WHO it binds and WHAT harm it prevents.** A reading that ends in
   "refuse the owner" is almost certainly rule 1 being violated.

## Models

- **Design = Fable or the newest Opus, the owner's pick, started ONLY by the owner.** No
  agent, Routine or session ever spawns Fable.
- **Build = the newest Opus (ultracode). Supervise = the newest Opus. Feedback = Sonnet.**
- **Every spawn names the full id** (`claude-opus-5-5`, the current Opus id on 2026-09-24),
  never an alias; when a newer model ships, the design realm bumps the id everywhere it is
  written.
- **Anything an agent spawns runs Opus or lower.** `.claude/settings.json` sets the default
  subagent model to the same full id, so an in-session subagent spawned with no model
  named never inherits Fable; a cheaper one is named `sonnet` or `haiku` on the call.
- **Fable tokens are for judgment:** scouting, sweeps, draft passes and review lenses go to
  Opus-or-lower agents.

**Effort per role** (the defaults; the owner accepted them on 2026-09-24): design `max` (the effort dropdown;
drop to `xhigh` only when the usage limit bites); build and supervise `xhigh` (spawned
sessions take `effortLevel` from `.claude/settings.json`, which also sets in-session
subagents); feedback `high`. Never set `CLAUDE_CODE_EFFORT_LEVEL` in the environment: it
overrides everything.

## Permissions — unattended after the owner's go

Harm prevented: a session parked on a prompt nobody answers (lesson 30), and the owner
interrupted after the go.

1. **Every session runs in Auto.** The owner picks it for sessions they open; every
   `create_session` passes `permission_mode` = `auto`.
2. **`.claude/settings.json` allows every built-in tool, both web tools, and the session
   and GitHub servers**, so a session outside Auto is rarely asked anything.
3. **History is never rewritten by an agent.** The settings deny force pushes and
   push-deletions in every mode; Auto blocks force pushes by default.
4. **Auto is not "never asks."** Three blocked actions in a row, or twenty in one
   session, and it falls back to prompting. Builders avoid the default blocks (force
   push, `git reset --hard`, `git checkout -- .`, `git restore .`, `git clean -fd`,
   `git stash drop`); a blocked action is answered by another route, never the same
   command again.
5. **Nothing unattended archives a session.** Auto refuses it; every session of an arc
   carries its tag and a clear title, and the close archives them with the owner present.
6. **Connectors stay out of coding sessions.** Nothing here uses a claude.ai connector
   other than GitHub.

## Branches — one trunk

- **`main` is the default AND the only working branch.** Builders are spawned with
  `source_revision` = `outcome_branch` = `main`. No PRs, no per-arc branches.
- **`claude/*` scratch branches are platform noise.** No realm commits to one; the janitor
  (`.github/workflows/janitor.yml`, daily) deletes any whose tip is contained in `main`,
  and never touches a diverged branch, `main`, or `dist` (the delivery shelf, SPEC
  §Delivery).
- **A reopened chat syncs `main` before judging anything**; a doc you cannot see is never
  a doc you rewrite (lesson 16).
- **Feature branches only for big multi-night builds, on the owner's call.** Deleting a
  diverged branch needs an ancestry check and the owner (lesson 17).

## Day and night

There is no day rule — builders run whenever there is work.

## Pace and risk

The owner left pace and testing unstated in start.md and accepted the defaults on day one
("13 ok", 2026-09-24): testing happens organically, bugs come in through feedback; work
moves in arc-sized pushes. There is no never-happen rule, so full discipline applies to
Hard Rules 4 and 5 only (below).

- **Briefs are ARC-sized** unless the owner says otherwise. **Owner testing is never a
  gate**: owner checks in Findings are notes; bugs return through feedback.
- **Visual work:** containers cannot render (start.md Part 1A). A brief that changes what
  is drawn is DONE on its headless gates plus the line *"does NOT prove: that it renders
  or looks right"*; the owner's first look is recorded through feedback, never waited
  for.
- **When the owner designs** (files in `docs/design/`): the design files are the spec;
  a designed surface is DONE only when every element is built or on a "NOT BUILT — needs
  owner decision" list. Nothing is silently simplified.
- **Full discipline around Hard Rules 4 and 5** (coordinates, determinism): every hard
  rule, mutation proofs, zero unannounced behaviour change. The licence rule (Hard Rule 3)
  is soft by the owner's choice: a test and `docs/RELEASE.md` enforce it, reviewed at
  Tier 2. Everything else is priced by recoverability.
- **Rollback:** the previous binaries on the `dist` shelf (`*-previous.*`, RELEASE.md §C;
  delivery (b), the owner's choice on 2026-09-24). Before the first release there is
  nothing to roll back to.

## Supervision must cost less than the work

1. **The supervisor is a waker plus fresh ticks** (SUPERVISE.md): the waker holds one
   hourly cron dead-man and, while builders run, one 30-minute one-shot; builders wake it
   after a landing; each tick is a fresh session, so no context grows with the arc
   (lesson 32).
2. **A design session is per PHASE, not per day:** plan-and-brief in one, close in a fresh
   one.
3. **Nothing the design realm spawns runs higher than Opus**; the arc runs on the Opus
   waker and ticks once the design chat's turn has ended.
4. **The supervisor decides what the record already decides** (SUPERVISE.md §What the
   supervisor decides); the owner's word in the waker session is a ruling.
5. **At most two builders at once**, only on briefs that share no file and no dependency.

Measured at every close and written into the release record: design spend against
builder spend. If supervision is the larger number, the arc was run wrong.

## The reading list per role

Every role reads at startup only what its role doc names. The board
(`docs/ROADMAP.md`) holds open items only; `BLOCKED.md` holds Open only; answered
questions live in `docs/history/blocked/`, indexed one line each in
`docs/history/RULINGS.md` (read BEFORE filing a question). Lessons are tagged: builders
read `[build]` + `[all]`, the supervisor `[supervise]` + `[all]`, design all of them.
Histories (`docs/history/`, `docs/feedback/ARCHIVE.md`) are opened one section at a time
when a decision needs them, never at startup (lesson 28).

## Review policy — two tiers

- **Tier 1 — `config/world.json` and the coordinate transforms** (pipeline, manifest and
  game sides). Adversarial rounds until clean, fixes mutation-proved in both directions,
  every "does NOT prove" enumerated. No round cap.
- **Tier 2 — everything else** (rendering, materials, UI, cameras, tools, and licence and
  attribution, soft by the owner's choice). ONE
  adversarial round over the arc diff + ONE verification pass over the fixes, then ship.
  Residual P2/P3s go to the board and the report-back.
- **Escalation:** a finding in Tier-1 territory, or a P1+ in the verification pass,
  moves its area to Tier 1. The owner can order more rounds anytime.
- A truncated round leaves the arc OPEN. Rounds probe brief INTERACTIONS (lesson 8) and
  review the arc's diff, never the whole tree.

## Deferrals are said out loud

Every Open feedback item not taken into a tranche appears on its DEFERRED list with one
line of reason and one line of cost to the owner; the owner's go approves them knowingly.

## Brief lifecycle

`docs/briefs/<arc>-<nn>-<slug>.md` per `docs/briefs/TEMPLATE.md`. The status line reads
`Status: OPEN` → `Status: DONE (<commit sha>)`, or `Status: BLOCKED` with the question in
`BLOCKED.md` §Open. Done briefs stay in the tree as the execution record.

**Pinning tests travel with their brief.** The design realm commits a brief's pinning
tests under `docs/briefs/pinning/<brief id>/`, mirroring the paths they will have
(`docs/briefs/pinning/M0-02/pipeline/tests/test_world.py` becomes
`pipeline/tests/test_world.py`). The executor's first step copies them into place
(`cp -r docs/briefs/pinning/<id>/. .`); for the whole brief the live copies stay
byte-identical to the pinned ones (the brief's first gate checks it with `cmp`). Harm
prevented: the pinning tests of several OPEN briefs sitting in the live test tree would
keep the standard gate red for every brief but the last, and a gate that is always red
gets ignored (lesson 31). After the brief is DONE the live copies may evolve with later
briefs; the pinned copies stay as the record.

## Releases

`docs/RELEASE.md` is walked top to bottom before any version bump. Release records live
in `docs/releases/`; the chat report-back is a copy of the record.
