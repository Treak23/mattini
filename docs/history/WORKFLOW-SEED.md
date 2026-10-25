<!-- The handoff the owner brought on 2026-10-24 from another of their projects ("Miko"), kept verbatim as the source of docs/WORKFLOW.md and the role docs (SPEC §13 row 47). Where a case is not covered by mattini's docs, this file is the one to open; mattini's docs win where they differ. -->

# Workflow handoff — the one-session release process, made portable

Written 2026-10-24 for reuse on other projects. It describes the process as it stands after the
2026-10-24 process review (`docs/PROCESS-REVIEW-2026-10-24.md`) — the version D33 is running under —
with Miko's names taken out. `docs/start.md` is the older kit (state of 2026-09-28): its Part 1 owner
questionnaire is still good, but where its process differs from this file, this file wins.

Miko's home for each rule is named in brackets, so you can open the original when a new project
meets a case this summary does not cover.

---

## 1. The idea in six lines

1. **The repo is the only memory.** Plans, decisions, briefs, rulings, feedback and release records
   are files on `main`. Chat history carries nothing a later session needs.
2. **One session per release, started fresh** by the owner with one word. It triages, plans, gets one
   "go", builds through helper agents, reviews, gates, publishes, writes the record, and ends.
3. **The session judges; helper agents do the mechanical work.** It never writes production code
   itself — a builder agent does, under a brief, tests first.
4. **A release has a size: two days of build** and about half a week's usage allowance. The owner's
   own reported items come first; everything else waits for the next release.
5. **Gates are cheap per commit, real per batch, complete once per release.** No agent ever sits
   polling a long gate.
6. **Questions to the owner are plain text in the chat and never stop the work.** Rules bind the
   agents, never the owner.

## 2. Why this shape (the evidence, briefly)

| Release | Shape | Wall clock | Note |
|---|---|---|---|
| v3.65.0 | three kinds of session + a supervisor | 20.5 h | a third of its commits were supervisor bookkeeping |
| v3.66.0 | one session, first trial | 23 h | 156 commits, all work; the model for everything after |
| v3.67–3.69 | one session, scope and ceremony growing | 80 h → 83 h → 11 days | each 3–4x the cost of v3.66; the record said so and nothing stopped |
| D33 (now) | one session, after the 10-24 fixes | 13 briefs, 47 commits in about 15 h so far | the first release under the size cap and per-batch gate |

What made v3.69 a disaster, so a new project does not repeat it: no size limit on a release (the
owner said "recommend" to the whole backlog), a full 80-minute gate on every commit and after every
rebase, two build lanes fighting in one container, seven agents per batch writing more paperwork than
code (127 of 229 commits were docs), agents polling gates (cache reads 228x the output), and the
weekly limit hit mid-gate with red tests on `main` for 61 hours. Every fix below answers one of those.

## 3. The files a project needs

```
CLAUDE.md                 hard rules + the spawn-word router (section 4)
brain.md                  compressed handoff: aim, state, key files, build quirks
docs/SPEC.md              design of record
docs/WORKFLOW.md          the shared process skeleton (this file, adapted)
docs/roles/DESIGN.md      the release session's instructions
docs/roles/BUILD.md       the builder's rules + the ten-line card
docs/roles/FEEDBACK.md    the intake clerk's filing rules
docs/RELEASE.md           the publish checklist, walked top to bottom
docs/ROADMAP.md           the board: OPEN items only
docs/LESSONS.md           numbered lessons, each tagged with the role it binds
docs/feedback/INBOX.md    FB-NNN entries, Open section only; shipped ones → ARCHIVE.md
docs/feedback/shots/      screenshots saved byte-for-byte
docs/briefs/TEMPLATE.md   the brief template (section 9)
docs/briefs/BLOCKED.md    open questions only
docs/briefs/RELEASE-WORKFLOW.js   the standing per-batch helper-agent script
docs/history/blocked/     answered questions, one file per ruling set
docs/history/RULINGS.md   one-line index of every answer, read before ruling again
docs/releases/vX.Y.Z.md   one record per release (the chat report-back is a copy of it)
.claude/settings.json     permissions (section 11); pins no model and no effort
```

Start small: CLAUDE.md, brain.md, SPEC, the three role docs, RELEASE.md, ROADMAP, INBOX, TEMPLATE.
The history folders appear the first time something is answered.

## 4. Spawn words — the owner's whole manual

Open a fresh session on the repo, pick **Auto** in the mode selector, pick the model, type one line:

- **`ultracode design`** — a release, start to finish. (`ultracode` is the owner's switch for
  multi-agent workflows; only the owner's typed word turns it on, a doc cannot.)
- **`design`** — a conversation: ideas, "this looks wrong", what's next. Builds nothing without the word.
- **`feedback`** — the clerk. Send it bugs, ideas, screenshots whenever; it answers "Filed as FB-NNN".
  Filing never disturbs a running build — the build doesn't read the inbox, the next triage does.

The router, pasted into CLAUDE.md:

> When the owner's first message is one of these words, adopt that role: first run
> `git fetch origin main && git checkout main && git pull origin main`, then read the role doc and
> follow it — `design` → `docs/roles/DESIGN.md` · `feedback` → `docs/roles/FEEDBACK.md`.

Each role doc's header also carries a full fallback prompt, because a **reopened old chat is a time
capsule** (its checkout is from the day it was created): sync first, judge second, and never rewrite a
doc you cannot see.

## 5. Rules about rules (put these in WORKFLOW.md verbatim)

1. **Rules bind the agents, never the owner.** A rule protecting the owner's data from *agent* action
   never blocks building a feature the owner asked for — build it safely (confirmation, scope,
   recoverability), never refuse.
2. **The owner's explicit word overrides any process rule** except the project's absolutes (for Miko:
   no secrets in the repo, migrations never wipe, no unrecoverable data loss). The override costs one
   recorded line, never a debate.
3. **One home per rule.** Link to it; retelling is how copies drift.
4. **A rule states who it binds and what harm it prevents.** A reading that ends in "refuse the
   owner" is almost certainly wrong — re-read it against its stated harm.

Also: **deferrals are said out loud** (every item not taken is listed with its reason and its cost to
the owner), and **a remark is not a rule** (a one-off "work through the night" became a standing day
rule that idled builders for three weeks).

## 6. The release, step by step [DESIGN.md §The release]

**Startup.** Sync `main`. Read CLAUDE.md, brain.md, WORKFLOW, the board, LESSONS, the inbox, open
briefs, BLOCKED §Open, the last record's questions. Histories are opened for one section when needed,
never at startup. Say in a few lines what's open, then start.

1. **Triage.** Read-only helper agents check every open item against the code. One proposal per item:
   a fix, a decision (options, one recommended, one line of consequence each), or declined with reason.
   Presented as **two lists**:
   - **This release — two days of build.** By default the owner's open inbox entries and nothing else.
     Board items, review leftovers and the session's own ideas come in only if the owner names them.
     States the expected days and allowance.
   - **Next release** — everything else, ending in the DEFERRED list.
   Then wait for the go.
2. **The go.** Record the owner's decisions in `docs/history/blocked/<date>-<n>.md` (their words, item
   by item) and index lines in RULINGS.md, before building. The go also fixes three things, one line
   each: **the helpers' model** ("builders on Sonnet"), **the budget** (two days, about half a week's
   allowance), **the lane count**.
   - **The list is frozen at the go.** Anything filed during the build goes to the next release
     (which is only two days away), unless it is a P0 or the owner says "in this one" knowing it adds
     about a day.
   - **Batches**: one coherent change a builder finishes in an hour or two, Scope disjoint from its
     neighbours, one brief each.
   - **The plan is a dependency graph.** Each brief has a `Lane` line. Scopes sharing no file may run
     in parallel; Scopes sharing a file run in order in one lane. Hot files are listed once at the top
     of the plan with their batch order. A tier-1 batch (data, schema, security boundary) runs alone
     in its lane; a migration goes first. **A lane is a separate session in its own container**,
     never a second build lane in the same box. Owner-reported items first in each lane; words-only
     batches last.
3. **Batches**, one after another per lane, each as one helper-agent workflow:
   - **one builder** (helpers' model), under BUILD.md: pinning tests red first, the change, green;
     the commit gate chained to every commit; the batch gate once before DONE; push after every commit;
   - **tier 2** (UI, words, tools): **one** read-only reviewer over the batch's diff, both lenses
     (*correctness and seams*, *what the owner sees*), reporting **P0–P2 only**, on the session's model;
   - **tier 1** (the owner's data, schema, the security/isolation boundary): two lens reviewers, a
     data-and-boundary reviewer, and a mutation prover running the brief's proofs both ways;
   - **a fixer only when warranted** (tier 2: a P0/P1 stands; tier 1: any P0–P2), who verifies each
     finding against the code before changing anything; tier 1 adds a read-only verifier of the fix diff;
   - **no recorder agent**: the session writes one board line per batch from the agents' results.
   Before every batch the session reads its usage limit status; after every third batch the owner
   gets one line: allowance used, batches done, batches left.
4. **The whole-range review.** Reviewers over the entire release diff, the same lenses plus **the seams
   between batches** (two of v3.66's three serious findings lived only where batches met). Its
   findings become **one** fix batch taking P0, P1 and owner-reported items only; P2/P3 go to the board.
5. **The release gate**: everything, all targets and variants, `--rerun-tasks`, solo, as a tracked
   background task, never polled; counts compared to the last release's.
6. **The release** per RELEASE.md: bump, publish, the record with the report-back list (owner-reported
   items separate from review-found ones, each traced to its FB id), *Questions for you* with the
   defaults taken, inbox drained, board and brain.md current, one push notification.
7. **The end.** The session is done. Nothing is scheduled after; the next release is a fresh session.

## 7. How the session decides and asks [DESIGN.md §Questions, §What the session decides]

Before anything reaches the owner, in this order:
1. **Decide from the record** — a brief, the spec, a hard rule or a ruling answers it: answer it,
   quote the deciding line, add a RULINGS.md line.
2. **Decide the reversible** — two workable options inside a batch's scope, touching no hard rule, no
   schema, nothing the owner will see: take the easier one to undo, record both in Findings.
3. **Ask** — everything else. Plain text, numbered, options with one recommended and one line of
   consequence each. **A question never stops the work**: the batch that needs it waits, the rest
   continues. Still open at release → *Questions for you* with the default taken.

And: **rulings need evidence** (locate the mechanism at file:line first); **a status you didn't verify
is not a status** (a landing is a sha on `origin/main`); **never answer a working agent by message**
(it resumes a second copy of the agent writing into the same worktree — answers are commits it reads).

## 8. The builder [BUILD.md]

One fresh builder per brief, never resumed. It reads only CLAUDE.md, **the card**, brain.md's key-files
section and its brief. The rules:

1. **No design authority.** A measurement that argues against the design goes in Findings; the build
   follows the spec.
2. **Blocked is not improvise.** Genuine ambiguity → a question in BLOCKED.md, brief marked BLOCKED,
   move on. Fabrication that looks done is the worst failure class.
3. **Untestable is not downgrade.** If the only gate available is weaker than the change's failure
   class, that is a BLOCKED question. (Five quiet downgrades; the fifth shipped a startup crash.)
4. **Done = gates green**, never "looks done".
5. **Scope is the brief.** A file outside it is touched only when compile-forced, named in the commit.
   When the brief's own shape asks for a file its Scope forbids, Scope wins and the contradiction is filed.

**The card** — ten lines a builder reads instead of all the lessons (generic form):

1. Chain the commit to the gate's exit status with `&&`; a pipe or `;` eats it. Docs commits too.
2. Pinning tests first, red, failing by the harm's name; then the change; then green.
3. Scope wins over the brief's own shape; a contradiction is filed, never resolved by hand.
4. Blocked is not improvise; untestable is not downgrade.
5. Copy a red test's report (e.g. JUnit XML) into Findings before any re-run — the re-run deletes it.
6. Push after every commit; a rejected push means rebase and push again, never force.
7. Read the status sha from `git log origin/main` after the push, never from the local log.
8. A source scan proves text is arranged a certain way, never that code runs; every gate carries its
   "does NOT prove" line.
9. Undo an experiment with `git apply -R` of its own diff, never `reset --hard` / `checkout -- .`.
10. Stop only your own build daemons, by PID; build in your own worktree, without shared caches.

## 9. Gates — three levels [BUILD.md §Commits and the gate]

| Gate | When | What | Typical cost |
|---|---|---|---|
| **commit gate** | every commit | compile + the test classes the commit touched and their package neighbours | minutes |
| **batch gate** | once, before `Status: DONE` | every module's tests in one variant, lint, a debug build | about 30% under the full gate |
| **release gate** | once per release, solo, by the session | everything, all variants, cache bypassed | the full run |

After a rebase that brought commits in: the targeted tests again, not the full gate. **Every test task
has a timeout** (Miko: 45 min) so a hang fails by name instead of eating an hour; hitting it is a
defect to report, never a reason to raise the number. **A gate is never polled** — it runs as the
shell tool's tracked background task and the agent makes no call until it returns; an untracked
background run dies with the turn.

**The brief template** (`docs/briefs/TEMPLATE.md`):

```
# Brief: <arc>-<nn> — <title>
Status: OPEN            → DONE (<sha from origin/main>) | BLOCKED
Lane: <A|B> · after: <ids or none> · tier: <1|2>

## Goal            one paragraph, outcome language, small
## Read first      the files/spec sections it depends on
## Scope           explicit files or a narrow glob; nothing else
## Done when       runnable gates, each with:  - does NOT prove: <the claim it cannot settle>
                   (pinning tests named here; missing one = BLOCKED, not skipped)
## Forbidden       what this batch must not do beyond the standing rules
## Findings        tables only: gate runs · mutation rows · files outside Scope ·
                   brief-vs-repo disagreements · at most ten lines of surprises
```

The "does NOT prove" line is the cheapest defect-finder in the process: the gate behind Miko's one
shipped startup crash was a regex, and its honest line would have read "does NOT prove: that the
object can be constructed" — the entire defect.

## 10. Models, effort and budget [WORKFLOW §Models, §Cost is measured]

- **Nothing pins a model or an effort** — no settings file, doc or script. Two models per release,
  both the owner's word: the session's (picked in the selector; Opus as a rule, Fable for a hard
  triage or design talk) and the helpers' (one line in the go). The session names the helpers' model
  on every builder, fixer and sweep it spawns; reviewers and scouts follow the session, because
  judgment is where a builder's miss is caught. The record says which model ran where.
- **Effort** follows the same shape. Never set an effort environment variable — it overrides the
  dropdown too. High effort only where it has earned it (the tier-1 boundary lens, the mutation prover).
- **The budget unit is the weekly allowance**, not API-equivalent dollars (on a flat subscription
  those are only for comparing releases). At the go: two days and about half a week's allowance.
  **At 100% of either, start no new batch**: finish the one in flight, run the whole-range review on
  what is built, publish. At the limit's *warning*, finish the current batch and wait for the reset —
  so a pause never lands mid-gate with red tests on `main`.
- **Every release record** states the allowance at go and publish, the API-equivalent cost of every
  session, wall clock, commits, code/test lines and tests added, beside the previous release's. A rule
  that only *reports* an overrun changes nothing — the stop above is what was missing.

## 11. Permissions, branches, isolation [WORKFLOW §Permissions, §Branches]

- **Every session runs in Auto**, picked by the owner at open (a project file can't choose it for a
  cloud session; a spawn is never more permissive than its parent). `.claude/settings.json` allows the
  built-in tools, web tools and the GitHub/session servers, and **denies force pushes and branch
  deletion in every mode** — so "revert to a previous commit" always holds.
- Auto falls back to prompting after three blocks in a row or twenty in a session, which for an
  unwatched agent is a hang. So a blocked action is answered by **another route, never the same
  command again**, and builders avoid the commands Auto blocks (`reset --hard`, `checkout -- .`,
  `restore .`, `clean -fd`, `stash drop`).
- Connectors that send, delete, share or trade are set to need approval on the owner's account; no
  coding session uses them.
- **One trunk.** `main` is the default and only working branch: no PRs, no release branches. Platform
  `claude/…` branches are mirrors at most, swept daily by a GitHub Action that deletes any whose tip is
  an ancestor of `main`. Feature branches only for big multi-night builds, on the owner's call.
- **Isolation:** any agent that compiles or runs tests gets its own `git worktree`, builds without the
  shared cache, leaves the tree clean and removes the worktree. **One build-running agent per
  container.** Parallelism comes from more sessions in more containers, never more lanes in one box.
- Sessions don't archive themselves or each other (the classifier refuses it inconsistently); the
  owner archives a release session after reading its report-back.

## 12. Review policy — priced by recoverability [WORKFLOW §Review policy]

- **Tier 1** — anything whose failure the owner cannot undo (their data, schema/migrations, the
  security or isolation boundary): adversarial rounds until clean, fixes mutation-proved both ways,
  **round 2 reviews the diff of round 1's fixes, not the area again**.
- **Tier 2** — everything else: one reviewer, P0–P2, a fix only for P0/P1, then the whole-range review.
- A finding touching tier-1 territory escalates its area to tier 1. A truncated review round (limit hit,
  dead agent) means the release stays unpublished — unpublished code on `main` costs nothing.
- Reviewers read diffs, never the whole tree, and probe interactions between batches.

## 13. The feedback clerk [FEEDBACK.md]

A long-lived chat on a cheap model, pinned on the owner's devices. It is a notepad, not a colleague:

- Writes only to `docs/feedback/INBOX.md` and `shots/`; touches nothing else, ever.
- **Never asks the owner anything.** A gap is filed as a gap (`not stated`); design chases it later.
  Its whole output is the receipt line.
- **The owner's words are quoted verbatim**, typos and all; structured fields are additions.
- Never merges duplicates — files anyway with `Possibly same as: FB-NN`.
- One commit per item, pushed to `main` immediately (`pull --rebase` first, never force). Ids come
  from the highest FB number across inbox and archive at the moment of allocation.
- Screenshots: copy byte-for-byte when a file path exists; otherwise describe precisely and say it
  couldn't be saved. Never fabricate an image.
- Entry fields: id · date · kind (`bug|idea|design|crash`) · place · machine · build · `Impact:`
  (`blocks-use|degraded|wish`, by observation) · owner's words · what happened · expected · repro ·
  screenshots · possibly same as. A `blocks-use` commit subject gets a `!` so `git log` is a triage list.
- For a crash: recite the project's fixed rollback line verbatim first, then file.

## 14. Release checklist essentials [RELEASE.md]

- **Preconditions or it stays unpublished:** clean tree; every brief `DONE (<sha>)`; no production
  code written by the session's own hand; no truncated review; no scan-only gate over code that runs
  at construction/startup (or the report-back says "unverified on device"); every "does NOT prove"
  line read as a set; a schema change tells the owner to export a backup first.
- **The bump:** version code strictly above the published one (checked, not assumed); full gate
  redirected to a log with its exit checked; signing key verified against the shelf's (a fresh
  container's own key once made every build uninstallable over the last).
- **The publish:** the current build becomes the rollback copy; the new one is written under the
  fixed link and a versioned name; the commit carries version, source sha and gate exit line; plain
  push, never forced.
- **The record** is written and committed before the chat message, which is a copy of it.
- **When the owner reports a broken build:** point at the rollback in the first reply, before any
  diagnosis.

## 15. Porting it — what to keep, what to adapt

**Keep exactly:** the repo-as-memory rule; spawn words and the sync-first router; rules about rules;
one fresh session per release; the two-list triage and the two-day cap; the frozen list; briefs with
Scope and "does NOT prove"; pinning tests red first; the builder's no-design-authority and
blocked-is-not-improvise; the three gate levels and never polling; one build agent per container;
the two review tiers; answers as commits; the allowance budget with a hard stop; the clerk's
never-ask rule; report-back lists that separate the owner's items from review findings.

**Adapt per project:**
- **The absolute.** Ask the owner: what is the one thing that can never happen? (Miko: unrecoverable
  loss of personal memory.) That defines tier 1 and the overrides rule 2 cannot touch.
- **The gate commands** — the project's equivalents of the commit, batch and release gates, and the
  per-test-task timeout.
- **The publish** — RELEASE.md's B–C sections are Miko's sideloaded-APK shelf; a web app's are a
  deploy and its rollback.
- **The review lenses** — keep *correctness and seams* and *what the owner sees*; rename the tier-1
  lens to the project's boundary (data, money, auth…).
- **Owner profile** — Miko's owner is not a programmer: no jargon, outcomes not mechanics, no emoji,
  plain-text questions only. Write the new owner's preferences into DESIGN.md §Interaction rules.

**Leave behind:** Miko's realms, fidelity gate and phone/desk rules (project-specific); the archived
three-realm process; the 280-line lessons history (start a new `LESSONS.md` and let it earn its lines,
then distil a builder card from it once it passes about twenty).

**Bootstrap in a new repo:** copy this file in as `docs/WORKFLOW-SEED.md`, fill in `docs/start.md`'s
Part 1 questionnaire (what, why, for whom, platforms, v1 in/out, stack, services, the one thing that
can never happen), then open a session in Auto and send:

> ultracode design. Read docs/WORKFLOW-SEED.md and the owner's answers, write this project's CLAUDE.md,
> brain.md, SPEC.md, WORKFLOW.md, the three role docs, RELEASE.md, the brief template and an empty
> board and inbox from them, then propose the first release.
