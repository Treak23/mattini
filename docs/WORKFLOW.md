# WORKFLOW.md — the one-session release process

Adopted on the owner's word, 2026-10-24, from the process another of the owner's projects
runs (its handoff is kept verbatim as `docs/history/WORKFLOW-SEED.md`; open it when a case
here is not covered). It replaces the three-realm process (design session, `ultracode build`
orchestrator with builder sessions per wave, clerk), whose record is `docs/history/ARCS.md`.
This file is the shared skeleton; each role's rules live in its role doc
(`docs/roles/DESIGN.md`, `BUILD.md`, `FEEDBACK.md`). Rules cite lessons by number
(`docs/LESSONS.md`).

## The idea in six lines

1. **The repo is the only memory.** Plans, decisions, briefs, rulings, feedback and release
   records are files on `main`. Chat history carries nothing a later session needs.
2. **One session per release, started fresh** by the owner with one word. It triages, plans,
   gets one go, builds through helper agents, reviews, gates, publishes, writes the record,
   and ends.
3. **The session judges; helper agents do the mechanical work.** It never writes production
   code itself; a builder agent does, under a brief, pinning tests first (lesson 15).
4. **A release has a size: two days of build** and about half a week's usage allowance. The
   owner's own reported items come first; everything else waits for the next release.
5. **Gates are cheap per commit, real per batch, complete once per release.** No agent ever
   sits polling a gate.
6. **Questions to the owner are plain text in the chat and never stop the work.** Rules bind
   the agents, never the owner.

## Spawn words — the owner's whole manual

Open a fresh Claude Code session on this repo, pick **Auto** in the mode selector, pick the
model, type one line:

- **`ultracode design`** — a release, start to finish (DESIGN.md §The release). `ultracode`
  is the owner's switch for multi-agent workflows; only the owner's typed word turns it on,
  a doc cannot.
- **`design`** — a conversation: ideas, "this looks wrong", what comes next, a decision to
  record. It builds nothing without the word `ultracode design`.
- **`feedback`** — the clerk. Send it bugs, ideas and screenshots whenever; it answers
  "Filed as FB-NNN". Filing never disturbs a running release: the release does not read the
  inbox after its go, the next triage does.

The router is in `CLAUDE.md` §Process. A reopened old chat is a time capsule (its checkout is
from the day it was created): re-send the word; if it flounders, paste the fallback prompt
from the role doc's header. Sync first, judge second, never rewrite a doc you cannot see
(lesson 16).

**Your two settings, once:** Auto in the mode selector before the first message of every
session you open (a spawned agent is never more permissive than its parent). In your
claude.ai connector settings, every connector tool that sends, deletes, shares or trades
needs your approval (§Permissions).

## Rules about rules

1. **Rules bind the agents, never the owner.** A rule protecting something from AGENT
   action never blocks building what the owner asks for; the answer to a risky feature is
   confirmation, scope and recoverability, not refusal (lesson 11).
2. **The owner's explicit word overrides any process rule** except the absolutes: no
   secrets in the repo, no unrecoverable loss of the owner's work. (There is no
   never-happen rule: the owner chose none, 2026-09-24.) An override costs one recorded
   line where the decision lands, never a debate.
3. **One home per rule.** Other docs link to it; retelling is how copies drift.
4. **A rule states WHO it binds and WHAT harm it prevents.** A reading that ends in
   "refuse the owner" is almost certainly rule 1 being violated: re-read it against its
   stated harm.

Also: **deferrals are said out loud** (§Deferrals), and **a remark is not a rule**: a
one-off instruction becomes a standing rule only when the owner says so and it is written
where it binds.

## The release has a size

Harm prevented: a release that grows until the allowance runs out mid-gate with red tests
on `main`; the source project's v3.69 took eleven days and 3 to 4 times the cost of the
release it was modelled on, and its record said so while nothing stopped it.

- **Two days of build and about half a week's allowance**, fixed at the go in one line
  each (DESIGN.md §The release, step 2). By default the release holds the owner's open inbox
  entries and nothing else; board items, review leftovers and the session's own ideas come
  in only when the owner names them.
- **The list is frozen at the go.** Anything filed during the build goes to the next
  release, which is two days away, unless it is a P0 or the owner says "in this one"
  knowing it adds about a day.
- **At 100 % of either budget, start no new batch:** finish the one in flight, run the
  whole-range review on what is built, publish. At the allowance's warning, finish the
  current batch and wait for the reset, so a pause never lands mid-gate.
- **A batch** is one coherent change a builder finishes in an hour or two, Scope disjoint
  from its neighbours, one brief each (`docs/briefs/TEMPLATE.md`). Briefs are batch-sized
  from 2026-10-24 on; the arc-sized briefs of M0 to M3 stay as the record.

## Lanes — parallel by the plan

Harm prevented: parallel work that collides in the same files, and two gates in one
container colliding on Godot's `user://` (brain.md H9).

- **The plan is a dependency graph.** Each brief has a `Lane:` line (`Lane: <letter> ·
  after: <ids or none> · tier: <1|2>`). Scopes sharing no file may run in parallel; Scopes
  sharing a file run in order in one lane. Hot files (`main.gd`, `project.godot`,
  `__main__.py`, `manifest.py`, `tools/gate.sh`, `tools/gate_allowlist.txt`) are listed
  once at the top of the plan with their batch order. A tier-1 batch runs alone in its lane.
  Owner-reported items first in each lane; words-only batches last.
- **A lane is a separate session in its own container**, never a second build lane in the
  same box: **one build-running agent per container.** The release session runs lane A's
  batches itself as helper-agent workflows; a second lane would be a second session given
  the plan and its lane letter, which builds that lane's batches and ends. That path is not
  written yet (who starts it, how the release session learns it has finished, and whether a
  session the first one spawns gets the `ultracode` switch at all): until it is, a release
  runs one lane (the go of 2026-10-25). Parallelism comes from more sessions, never from
  more lanes in one container.
- Any agent that runs the gate works in its own `git worktree`, with its own
  `XDG_DATA_HOME` (brain.md H9) and leaves the tree clean (lesson 20); the Workflow harness
  removes an unchanged worktree, and keeps one that holds commits.

## Gates — three levels

| Gate | When | What | Cost |
|---|---|---|---|
| **commit gate** | every commit, chained (`tools/gate.sh > gate.log && git commit …`) | the standard gate: pytest, ruff, the Godot import and parse check, GUT, gdlint, the render step | minutes |
| **batch gate** | once, before a brief's `Status: DONE` | the standard gate from a clean worktree at the pushed head, the brief's own `Done when` gates, its mutation rows (tier 1: both ways), `cmp` of the pinned tests | the standard gate plus the brief's gates |
| **release gate** | once per release, solo, by the session | `docs/RELEASE.md` §B and §C: a fresh clone, the pipeline from the pinned inputs, the standard gate, `tools/export.sh`, the Linux export started; counts compared with the last release's | an hour or so |

The standard gate is cheap enough (about a minute in M1, a few minutes now) to be the
commit gate as it is. After a rebase that brought commits in: the standard gate again. The
render step's scripts have a timeout (brain.md H25, H28); hitting one is a defect to
report, never a reason to raise the number. **A gate is never polled:** it runs as the
shell tool's tracked background task, or in the foreground redirected to a log, and the
agent makes no call until it returns. An untracked background run dies with the turn.

**The clerk's commits** touch only `docs/feedback/` and are chained to the tests that read
those files, `pipeline/tests/test_repo_hygiene.py` (`docs/roles/FEEDBACK.md` rule 6), not to
the standard gate: a filing then costs seconds and never waits on a `main` that is red for
someone else. This holds while `git grep -l -e INBOX -e docs/feedback -- pipeline/tests
game/tests tools` finds no other test; when it finds one, the clerk's commits take the
standard gate (lesson 18; the owner's "4c", 2026-10-27).

Every gate carries its "does NOT prove" line (lesson 10). A source census proves text,
never behaviour (lesson 5): it is never the sole gate for code that runs at scene load,
`_ready()`, autoload initialisation or pipeline start-up.

## Models, effort and budget

- **Nothing pins a model**: no settings file, doc or script. Two models per
  release, both the owner's word: the session's (picked in the selector) and the helpers'
  (one line in the go, "builders on Sonnet"). The session names the helpers' model on every
  builder, fixer and sweep it spawns; reviewers, provers and scouts follow the session,
  because judgment is where a builder's miss is caught. The record says which model ran
  where.
- **Effort** follows the same shape: the dropdown, never `CLAUDE_CODE_EFFORT_LEVEL` in the
  environment or `effortLevel` in `.claude/settings.json` (removed 2026-10-24). The one effort
  the repo sets is `docs/briefs/RELEASE-WORKFLOW.js`'s `high` on the tier-1 coordinates lens,
  the mutation prover and the fix verifier: high effort only where it has earned it.
- **The budget unit is the weekly allowance.** API-equivalent cost is recorded only to
  compare releases. The stop rule is §The release has a size.
- **Every release record** states the allowance at go and publish, the API-equivalent cost
  of every session, wall clock, commits, code and test lines and tests added, beside the
  previous release's.

## Permissions — unattended after the owner's go

Harm prevented: a session parked on a prompt nobody answers (lesson 30), and the owner
interrupted after the go.

1. **Every session runs in Auto.** The owner picks it for sessions they open; every
   `create_session` passes `permission_mode` = `auto`.
2. **`.claude/settings.json` allows every built-in tool, both web tools, and the session
   and GitHub servers**, so a session outside Auto is rarely asked anything.
3. **History is never rewritten by an agent.** The settings deny force pushes (`--force`,
   `-f`, `--force-with-lease`, a `+` refspec) and `--delete` pushes in every mode; Auto blocks
   force pushes by default. A `:<branch>` deletion refspec has no deny rule (the CLI's rule
   syntax cannot express it without also denying `HEAD:main`); Auto and the janitor's
   ancestry rule are its guard.
4. **Auto is not "never asks."** Three blocked actions in a row, or twenty in one
   session, and it falls back to prompting. Builders avoid the default blocks (force
   push, `git reset --hard`, `git checkout -- .`, `git restore .`, `git clean -fd`,
   `git stash drop`); a blocked action is answered by another route, never the same
   command again.
5. **Nothing unattended archives a session.** The owner archives a release session after
   reading its report-back.
6. **Connectors stay out of coding sessions.** Nothing here uses a claude.ai connector
   other than GitHub.

## Branches — one trunk

- **`main` is the default AND the only working branch.** No PRs, no release branches.
- **`claude/*` scratch branches are platform noise.** No role commits to one on purpose; a
  session the harness holds on one pushes to `main` and mirrors `main` into it. The janitor
  (`.github/workflows/janitor.yml`, daily) deletes any whose tip is contained in `main`, and
  never touches a diverged branch, `main`, or `dist` (the delivery shelf, SPEC §Delivery).
- **A reopened chat syncs `main` before judging anything**; a doc you cannot see is never
  a doc you rewrite (lesson 16).
- **Feature branches only for big multi-night builds, on the owner's call.** Deleting a
  diverged branch needs an ancestry check and the owner (lesson 17).

## Pace and risk

The owner left pace and testing unstated in start.md and accepted the defaults on day one
("13 ok", 2026-09-24): testing happens organically, bugs come in through feedback. From
2026-10-24 work moves in releases of two days (§The release has a size). There is no
never-happen rule, so full discipline applies to Hard Rules 4 and 5 only.

- **Owner testing is never a gate**: owner checks in Findings are notes; bugs return
  through feedback.
- **Visual work:** containers have no GPU (start.md Part 1A). A brief that changes what
  is drawn is DONE on its headless gates plus the line *"does NOT prove: that it renders
  or looks right"*; the owner's first look is recorded through feedback, never waited
  for. Its builder also commits a few software screenshots (Compatibility renderer,
  `tools/shot.sh`, SPEC §12) under `docs/briefs/shots/` and names them in Findings: evidence
  of what is drawn and where, never a gate, and not the Forward+ look (the owner's choice,
  2026-09-25). The gate's render step (from M3-R1-fix-3, SPEC §12) is the one exception:
  it measures where the photo, the water class and the crowns' colour land, never the look.
- **When the owner designs** (files in `docs/design/`): the design files are the spec;
  a designed surface is DONE only when every element is built or on a "NOT BUILT — needs
  owner decision" list. Nothing is silently simplified.
- **Full discipline around Hard Rules 4 and 5** (coordinates, determinism): every hard
  rule, mutation proofs, zero unannounced behaviour change. The licence rule (Hard Rule 3)
  is soft by the owner's choice: a test and `docs/RELEASE.md` enforce it, reviewed at
  Tier 2. Everything else is priced by recoverability.
- **Rollback:** the previous version's named folder on the `dist` shelf
  (`mattini-<version>/`, RELEASE.md §C; delivery (b), the owner's choice on 2026-09-24).

## The reading list per role

Every role reads at startup only what its role doc names. The board (`docs/ROADMAP.md`)
holds open items only; `BLOCKED.md` holds Open only; answered questions live in
`docs/history/blocked/`, indexed one line each in `docs/history/RULINGS.md` (read BEFORE
filing a question). Lessons are tagged: build reads `[build]` + `[all]` (the builder reads
the card in BUILD.md instead), the release session all of them. Histories
(`docs/history/`, `docs/feedback/ARCHIVE.md`, `docs/reviews/`) are opened one section at a
time when a decision needs them, never at startup (lesson 28).

## Review policy — priced by recoverability

The release session designs and runs the reviews through helper agents
(`docs/briefs/RELEASE-WORKFLOW.js`, DESIGN.md §The release, steps 3 and 4). Reviewers read
diffs, never the whole tree, and probe the interactions between batches (lesson 8). Two
lenses on every batch: *correctness and seams*, *what the owner sees*; tier 1 adds the
*coordinates and determinism* lens.

- **Tier 1 — `config/world.json`, the coordinate transforms** (pipeline, manifest and game
  sides) **and the pipeline's determinism** (Hard Rules 4 and 5). Per batch: two lens
  reviewers, a data-and-boundary reviewer and a mutation prover running the brief's proofs
  both ways; a fixer for any P0 to P2, verified by a read-only verifier of the fix diff.
  Adversarial rounds until clean; round 2 reviews the diff of round 1's fixes, not the area
  again. No round cap.
- **Tier 2 — everything else** (rendering, materials, UI, cameras, tools, words, and
  licence and attribution, soft by the owner's choice). Per batch: ONE read-only reviewer
  over the batch's diff, both lenses, P0 to P2 only; a fixer only when a P0 or P1 stands.
- **The whole-range review** (DESIGN.md step 4) runs over the entire release diff with the
  same lenses plus the seams between batches; its findings become ONE fix batch taking P0,
  P1 and owner-reported items only; P2 and P3 go to the board's residue list and the
  report-back.
- **Escalation:** a finding in Tier-1 territory moves its area to Tier 1. The owner can
  order more rounds anytime. A truncated round (limit hit, dead agent) means the release
  stays unpublished; unpublished code on `main` costs nothing.

## Deferrals are said out loud

Every Open feedback item not taken into the release appears on the plan's DEFERRED list
with one line of reason and one line of cost to the owner; the owner's go approves them
knowingly.

## Brief lifecycle

`docs/briefs/<release>-<nn>-<slug>.md` per `docs/briefs/TEMPLATE.md` (`<release>` is the
version it ships in, `v0.4.0-01`; M0 to M4's briefs keep their arc ids). A brief cut out of
another gets a new id, never another id plus `-` (the batch script finds a brief by
`docs/briefs/<id>-*.md`). The status line reads `Status: OPEN` → `Status: DONE (<sha from
origin/main>)`, or `Status: BLOCKED` with the question in `BLOCKED.md` §Open. Done briefs
stay in the tree as the execution record.

**Pinning tests travel with their brief.** The release session commits a brief's pinning
tests under `docs/briefs/pinning/<brief id>/`, mirroring the paths they will have
(`docs/briefs/pinning/M0-02/pipeline/tests/test_world.py` becomes
`pipeline/tests/test_world.py`), linted in the live layout and run against a throwaway
implementation first (lesson 40). The builder's first step copies them into place
(`cp -r docs/briefs/pinning/<id>/. .`); for the whole brief the live copies stay
byte-identical to the pinned ones (the brief's first gate checks it: `(cd
docs/briefs/pinning/<id> && find . -type f -print0 | xargs -0 -I{} cmp {} "$OLDPWD/{}")`;
GNU cmp has no `-r`). A brief with nothing to pin (words only, a review's fix batch whose
tests the fixer writes) has no pinning folder and says so in its gates. Harm
prevented: the pinning tests of several OPEN briefs sitting in the live test tree would
keep the standard gate red for every brief but the last, and a gate that is always red
gets ignored (lesson 31). After the brief is DONE the live copies may evolve with later
briefs; the pinned copies stay as the record.

**Answers are commits.** A builder's question is answered by a commit it reads
(`BLOCKED.md` → `docs/history/blocked/`, the brief back to OPEN), never by a message to a
working agent (lesson 30; a message resumes a second copy writing into the same worktree).

## Releases

The release session ships: it walks `docs/RELEASE.md` top to bottom before any version
bump. Release records live in `docs/releases/`; the chat report-back is a copy of the
record, with the owner's reported items kept separate from what the review found.
