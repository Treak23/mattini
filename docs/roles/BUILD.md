# BUILD.md — the executor realm

**Spawn words: `ultracode build`** ("ultracode" must come from the owner's message or the
spawning session's prompt). Fallback:

> ultracode. Run git fetch --unshallow origin main || git fetch origin main, then git
> checkout main && git pull --ff-only origin main — you work on main and push to main,
> never the session's scratch branch. Then read CLAUDE.md, docs/LESSONS.md and
> docs/roles/BUILD.md. If this prompt names briefs, you are a lane builder: work those and
> only those under BUILD.md §A lane builder's whole life, and report each landing with
> send_message to the orchestrator session this prompt names. Otherwise you are the
> orchestrator: run the open arc plan in docs/briefs/ under BUILD.md §The orchestrator.
> Stop only when no brief of yours remains OPEN or every remaining one is BLOCKED (for the
> orchestrator: when the release has shipped) — never between briefs, and never to report
> progress.

**One fresh session per run, never resumed.** A session is the **orchestrator** when the
owner started it with `ultracode build` and the prompt names no briefs; it is a **lane
builder** when its prompt names briefs (the orchestrator spawned it).

## The orchestrator

Takes the arc from the go to the release, as wide in parallel as the arc plan allows
(WORKFLOW §Parallel by design).

1. **Orient.** Sync `main`. Read `CLAUDE.md`, the `[build]` and `[all]` lessons,
   `brain.md` §Key files and §Hazards, the board, `docs/briefs/<arc>-plan.md`, every
   brief's status line (`grep ^Status: docs/briefs/`) and `BLOCKED.md` §Open. Briefs
   themselves only as a decision needs them; your builders read them. The plan's status
   reads `GO` (the design session recorded the owner's GO), or `READY` and the owner
   started you by typing `ultracode build`, which is the GO: set `Status: GO (<date>, the
   owner)`, commit, push. Neither → the owner has not given the GO; say so and stop.
   At the release, set `Status: DONE (<version or sha>)`.
2. **Spawn a wave.** For every lane of the current wave whose briefs are OPEN and have no
   `Builder:` line: write `Builder: <brief ids> · <session id> · since <UTC>` on the board
   (commit and push BEFORE the spawn), then `create_session` with `source_revision` AND
   `outcome_branch` = `main`, `source_url` and `clone_depth` passed explicitly,
   `permission_mode` = `auto` (if refused, once without it), no model (it inherits),
   `title` = `Builder · <brief ids>`, `tags` = [`<arc>`], and as prompt this doc's fallback
   with the brief list filled in, your own session id to report to, plus: **never wait on
   a permission prompt — reach the result another way and name it in Findings.** Then
   check with `get_session` that the repository is under `session_context.sources`; if
   not, spawn once more; a second miss is asked. Spawn every lane of the wave at once.
   Without session tools, run the lanes as in-session agents with worktree isolation
   (brain.md H19: merge `main` into the worktree first), as many at once as the wave holds.
3. **Wait for landings, never on silence** (lessons 27, 30). A lane builder reports with
   `send_message` after each landing; a landing is a sha on GitHub (`git ls-remote origin
   main` and the API), never an agent's summary. Keep one `send_later` check-in armed
   while lanes run, so a lost report or a dead builder is still seen. A rate-limited
   session is not dead: wait past the reset; replace it only if still idle twenty minutes
   after. Never resume a builder; never a duplicate for a brief with a board line.
4. **Integrate the wave.** When every lane of the wave has landed: pull `main`, run the
   full gate YOURSELF on the combined head (redirected to a log, the next step chained on
   its exit), and fix the seams between the wave's briefs (lesson 8): the fix is scoped to
   the files those briefs touched, gated and committed like any brief (rule 3c), and named
   in the arc plan's integration notes. A seam that needs a design change is a BLOCKED
   question. Then remove the wave's `Builder:` lines and start the next wave.
5. **Decide what the record already decides** (lesson 29). A builder's question or a
   Findings line that a brief, the arc plan, the SPEC, a hard rule, this doc or
   `RULINGS.md` answers → answer it, quote the deciding line, and append *`<date> · build
   · <brief> · <question> → <answer>, per <citation>`* to `RULINGS.md`. Two reversible
   options inside a brief's scope, neither touching Hard Rules 3–5 nor anything the owner
   will see or play → take the one easiest to undo, write both in Findings. Everything
   else → `BLOCKED.md` §Open; that brief is BLOCKED, the rest continue. Never: a change to
   a brief's shape or a ruling from an unmeasured premise (lesson 12).
6. **Review per the arc plan's review plan** (WORKFLOW §Review policy) once every brief is
   DONE and integrated. Each lens is its own session or isolated agent (lesson 20: own
   worktree, fresh caches, tree removed before reporting; the release gate runs solo from
   clean) with the prompt the plan wrote, the diff range, the rule *prove it or downgrade
   it*, and one output, `docs/reviews/<arc>-R<n>-<lens>.md`, committed alone. Adjudicate
   the round into `docs/reviews/<arc>-round<n>.md`. Fix the P0/P1 findings whose fix is
   unambiguous and in the arc's scope (spawned as lanes when they share no file); a fix
   that needs design is a BLOCKED question; P2/P3 go to the board's residue list.
7. **Ship.** Rounds clean, every brief DONE, full gate green on the head from clean →
   walk `docs/RELEASE.md` top to bottom: the release record in `docs/releases/` FIRST,
   then the report-back in chat as a copy of it, the board updated, one
   `PushNotification`. Archive the arc's sessions only with the owner present
   (WORKFLOW §Permissions 5).

## A lane builder's whole life

1. Sync `main`. Read `CLAUDE.md`, the `[build]` and `[all]` lessons in `docs/LESSONS.md`,
   `brain.md` §Key files and §Hazards, then your brief: the first the prompt names (the
   lowest OPEN one when you run alone). A brief with a `Builder:` line naming another
   session belongs to someone else (`Builder: owner` included).
2. Copy the brief's pinning tests into place (WORKFLOW §Brief lifecycle), then work the
   brief to green: its gates plus the standard gate.
3. Commit (chained on the gate, rule 3c), `git pull --rebase origin main`, re-run the gate
   if the rebase brought commits in, push `main` (a rejected push means rebase again,
   never force). Fill Findings; set `Status: DONE (<sha>)` with the sha copied from
   `git log origin/main` AFTER the push. If the prompt names an orchestrator session,
   `send_message` it the brief id and the sha; if that fails, carry on.
4. Take the next brief of yours. The session ends only when none remains OPEN or all
   remaining are BLOCKED.

## The rules

1. **No design authority** beyond §The orchestrator step 5. A measurement that argues
   with the design goes in Findings; the build follows the spec.
2. **Blocked ≠ improvise.** Genuine ambiguity → `docs/briefs/BLOCKED.md` in plain text,
   brief `BLOCKED`, next brief (lesson 1).
2b. **Untestable ≠ downgrade.** If the only available gate is weaker than the change's
   failure class, that is a BLOCKED question (lesson 6). **Exception, recorded here by
   design:** "renders / looks right" cannot be gated in a container without a GPU; for
   that claim alone, the brief's `does NOT prove: that it renders or looks right` line is
   the accepted answer, and the owner's PC is the check. Software screenshots
   (WORKFLOW §Pace and risk) are evidence in Findings, never a gate.
3. **Done = gates green**, not "looks done".
3b. **What a gate is made of matters.** Every gate carries its "does NOT prove:" line. A
   source census proves text, never behaviour; it is never the sole gate for code that
   runs at scene load, `_ready()`, autoload initialisation or pipeline start-up —
   instantiate the scene or run the step headless instead (lessons 4, 5).
3c. **The commit is chained to the gate's own exit status:** `tools/gate.sh > gate.log &&
   git commit …`. A pipe or `;` breaks the chain (lesson 7).
4. **Scope is the brief.** Files outside its list are off limits except compile-forced
   necessities named in the commit message, and the orchestrator's seam fixes (§The
   orchestrator step 4), which stay inside the files the wave's briefs touched. When the
   brief's shape needs a file its Scope forbids, Scope wins: file it in BLOCKED.
5. **Never commit raw geodata or large binaries** outside the storage method the SPEC
   names (CLAUDE.md Hard Rule 3; SPEC §Storage). Downloads go to `data/`.
6. A turn ends on a shipped result or a real blocker. All `CLAUDE.md` hard rules apply.

## Commits and the gate

- Conventional commits; the harness's attribution trailer on every commit; model ids
  nowhere in the repo.
- Gate before every commit, redirected to a log, chained (rule 3c); rebase before every
  push, gate again after a rebase that brought commits in; never force-push.
- Container facts: Godot and the Python environment come from the session-start hook
  (`.claude/hooks/session-start.sh`); run `godot --headless --path game --import` once
  before the Godot tests in a fresh container. Known hazards with their exact signatures
  live in brain.md §Hazards; cite them by name.
- **Auto mode:** undo a mutation with `git apply -R` of its saved diff or in a separate
  worktree, never with the commands Auto blocks (WORKFLOW §Permissions 4).
