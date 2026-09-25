# BUILD.md — the executor realm

**Spawn words: `ultracode build`** ("ultracode" must come from the owner's message or the
spawning session's prompt). Fallback:

> ultracode. Run git fetch origin main && git checkout main && git pull origin main —
> you work on main and push to main, never the session's scratch branch. Then read
> CLAUDE.md, docs/LESSONS.md and docs/roles/BUILD.md, and work the OPEN briefs in
> docs/briefs/ in ascending order — or, when this prompt names briefs, those and only
> those — under the executor rules in BUILD.md. For each: work until its gates are
> green, commit, rebase on main, push, set its status line, then take the next. Stop
> only when no brief of yours remains OPEN or every remaining one is BLOCKED — never
> between briefs, and never to report progress.

**Model: the newest Opus, ultracode. One fresh session per run, never resumed.**

## A session's whole life

1. Sync `main`. Read `CLAUDE.md`, the `[build]` and `[all]` lessons in `docs/LESSONS.md`,
   `brain.md` §Key files and §Hazards, then your brief: the lowest OPEN one, or the first
   the prompt names. A brief with a `Builder:` line on the board belongs to someone else
   (`Builder: owner` included).
2. Copy the brief's pinning tests into place (WORKFLOW §Brief lifecycle), then work the
   brief to green: its gates plus the standard gate.
3. Commit (chained on the gate, rule 3c), `git pull --rebase origin main`, re-run the gate
   if the rebase brought commits in, push `main` (a rejected push means rebase again,
   never force). Fill Findings; set `Status: DONE (<sha>)` with the sha copied from
   `git log origin/main` AFTER the push. If the board has a `Waker:` line, `fire_trigger`
   the Routine it names; if that fails, carry on.
4. Take the next OPEN brief of yours. The session ends only when none remains OPEN or all
   remaining are BLOCKED.

## The rules

1. **No design authority.** A measurement that argues with the design goes in Findings;
   the build follows the spec.
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
   necessities named in the commit message. When the brief's shape needs a file its Scope
   forbids, Scope wins: file it in BLOCKED.
5. **Never commit raw geodata or large binaries** outside the storage method the SPEC
   names (CLAUDE.md Hard Rule 3; SPEC §Storage). Downloads go to `data/`.
6. A turn ends on a shipped result or a real blocker. All `CLAUDE.md` hard rules apply.

## Commits and the gate

- Conventional commits; the harness's attribution trailer on every commit; model ids
  nowhere else.
- Gate before every commit, redirected to a log, chained (rule 3c); rebase before every
  push, gate again after a rebase that brought commits in; never force-push.
- Container facts: Godot and the Python environment come from the session-start hook
  (`.claude/hooks/session-start.sh`); run `godot --headless --path game --import` once
  before the Godot tests in a fresh container. Known hazards with their exact signatures
  live in brain.md §Hazards; cite them by name.
- **Auto mode:** undo a mutation with `git apply -R` of its saved diff or in a separate
  worktree, never with the commands Auto blocks (WORKFLOW §Permissions 4).
