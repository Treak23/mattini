# BUILD.md — the builder

A builder is a helper agent the release session spawns for one brief
(`docs/briefs/RELEASE-WORKFLOW.js`, DESIGN.md §The release step 3): one fresh builder per
brief, never resumed, in its own worktree. There is no `ultracode build` session any more
(the three-realm process, retired 2026-10-24; its record is `docs/history/ARCS.md`): the
release session judges, the builder builds. A session the owner starts with the old word is
told so and stops.

The builder reads only `CLAUDE.md`, **the card** below, `brain.md` §Hazards and §Key files,
and its brief. The `[build]` lessons are the card's sources, opened when the card cites one.

## The card — ten lines a builder reads instead of all the lessons

1. **Chain the commit to the gate's exit status with `&&`**: `tools/gate.sh > gate.log &&
   git commit …`. A pipe or `;` eats it. Docs commits too (lessons 7, 18).
2. **Pinning tests first, red,** failing by the harm's name (copy them in with `cp -r
   docs/briefs/pinning/<id>/. .`); then the change; then green. The live copies stay
   byte-identical to the pinned ones for the whole brief (`cmp`).
3. **Scope wins over the brief's own shape**; a contradiction is filed in `BLOCKED.md`,
   never resolved by hand (lesson 31).
4. **Blocked is not improvise; untestable is not downgrade** (lesson 6). Genuine ambiguity,
   or a gate weaker than the change's failure class → a plain-text question in
   `docs/briefs/BLOCKED.md`, the brief `Status: BLOCKED`, stop. The one recorded exception:
   "renders or looks right" cannot be gated without a GPU; for that claim alone the brief's
   `does NOT prove: that it renders or looks right` line is the accepted answer (WORKFLOW
   §Pace and risk).
5. **Copy a red gate's report into Findings before any re-run** (the failing lines of
   `gate.log`, GUT's or pytest's); the re-run overwrites it.
6. **Push after every commit** (`git pull --rebase origin main`, the gate again if the
   rebase brought commits in, `git push origin main`); a rejected push means rebase and
   push again, never force.
7. **Read the status sha from `git log origin/main` after the push**, never from the local
   log: `Status: DONE (<sha>)`.
8. **A source scan proves text is arranged a certain way, never that code runs** (lesson 5);
   every gate carries its "does NOT prove" line, and a census is never the sole gate for
   code that runs at scene load, `_ready()`, autoload initialisation or pipeline start-up.
9. **Undo an experiment with `git apply -R` of its own diff**, never `reset --hard`,
   `checkout -- .`, `restore .`, `clean -fd` or `stash drop` (Auto blocks them; a blocked
   action is answered by another route, never the same command again).
10. **Build in your own worktree, with your own `XDG_DATA_HOME`** (brain.md H9), one gate at
    a time in the container; leave the tree clean. Stop only processes you started, by PID.

## The rules

1. **No design authority.** A measurement that argues with the design goes in Findings; the
   build follows the spec. Two reversible options inside your Scope that touch no hard rule,
   no `config/` data and nothing the owner sees: take the easier to undo and write both in
   Findings; everything else is the session's call (DESIGN.md §How the session decides).
2. **Blocked ≠ improvise; untestable ≠ downgrade** (card 4). Fabrication that looks done is
   the worst failure class (lesson 1).
3. **Done = gates green**, never "looks done": the brief's `Done when` boxes, the commit gate
   on every commit, the batch gate once before `Status: DONE` (WORKFLOW §Gates).
4. **Scope is the brief.** A file outside its list is touched only when compile-forced,
   named in the commit message. The brief's own file (Status, Findings) and its screenshots
   under `docs/briefs/shots/<brief id>-*` are always in Scope.
5. **Never commit raw geodata or large binaries** outside the storage method the SPEC names
   (CLAUDE.md Hard Rule 3; SPEC §Storage). Downloads go to `data/`.
6. **Findings are tables**: gate runs (command, exit, counts) · mutation rows (what was
   broken, which test failed, both runs) · files outside Scope · brief-vs-repo
   disagreements · at most ten lines of surprises. A measurement that argues with the
   design goes here. For visual briefs: what the owner should look at, where the camera
   was, and the software screenshots committed.
7. A turn ends on a shipped result or a real blocker. All `CLAUDE.md` hard rules apply.

## A builder's whole life

1. In your worktree: `git merge --ff-only origin/main` (a worktree of an in-session agent
   starts from the default branch, brain.md H19); check the head. Read the card, `brain.md`
   §Hazards and §Key files, then your brief.
2. Copy the pinning tests into place; run the named tests and see them red by the harm's
   name; copy the red report into Findings.
3. Work the brief to green: its gates plus the standard gate, committing in small steps,
   each chained to the gate, each pushed (card 1, 6).
4. The batch gate (WORKFLOW §Gates): the standard gate from a clean worktree at the pushed
   head, the brief's `Done when` boxes ticked with their results, the mutation rows run
   both ways where the brief asks. Fill Findings; set `Status: DONE (<sha>)` with the sha
   from `git log origin/main` after the push (card 7); commit and push the brief file.
5. Return the brief id, the sha, and the Findings' gate table as your result. A question
   you cannot settle → `BLOCKED.md` (card 4), the brief `BLOCKED`, return that. Never take
   another brief.

## Commits and the gate

- Conventional commits; the harness's attribution trailer on every commit (it is the
  harness's, not a process rule); no model id anywhere else.
- Gate before every commit, redirected to a log, chained (card 1); rebase before every
  push, gate again after a rebase that brought commits in; never force-push. The gate is
  never polled: run it in the foreground redirected to a log, or as the shell tool's
  tracked background task, and make no call until it returns.
- Container facts: Godot and the Python environment come from the session-start hook
  (`.claude/hooks/session-start.sh`); run `godot --headless --path game --import` once
  before the Godot tests in a fresh worktree. Known hazards with their exact signatures
  live in brain.md §Hazards; cite them by name.
