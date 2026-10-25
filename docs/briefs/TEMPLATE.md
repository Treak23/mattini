# Brief: <release>-<nn> — <title>
Status: OPEN
Lane: <A|B|…> · after: <brief ids or none> · tier: <1|2>

Written by the release session (`docs/roles/DESIGN.md`); built by one fresh builder agent
under `docs/roles/BUILD.md`. Batch-sized: one coherent change a builder finishes in an hour
or two (WORKFLOW §The release has a size). Copy this template; delete the guidance lines
in <>. `Status` becomes `DONE (<sha from origin/main>)` or `BLOCKED`. `tier: 1` is
`config/world.json`, the coordinate transforms or the pipeline's determinism (WORKFLOW
§Review policy); everything else is `tier: 2`.

## Goal

<One paragraph, outcome language, small: what exists and works when this is done. Never
"build the shell".>

## Read first, in order

<Files and SPEC sections this depends on. Name the ground truth explicitly (e.g.
`config/world.json`, a dataset's documentation).>

## Decisions already made

<With their source: SPEC section, RULINGS line, owner's word.>

## Scope — files you may touch

<Explicit list or narrow glob; nothing else. Shares no file with another brief of the same
lane letter running at the same time (the plan's hot-file order decides). The brief's own
file and its screenshots under `docs/briefs/shots/<id>-*` are always in Scope.>

## Done when (gates)

<Runnable checks, command plus expected result. The pinning tests already exist under
`docs/briefs/pinning/<id>/` (WORKFLOW §Brief lifecycle); a missing one is a BLOCKED
question, never skipped. Every gate carries a "does NOT prove" line; if it is hard to
write, the gate is not understood yet.>

- [ ] `cmp -r docs/briefs/pinning/<id>/. .` on the pinned paths: identical
      - does NOT prove: that the tests test the right thing
- [ ] <gate: the pinning tests, red before the change, green after>
      - does NOT prove: <the claim this gate cannot settle>
- [ ] Commit gate on every commit: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: <e.g. that it renders or looks right — required on every brief
        that changes what is drawn>
- [ ] Batch gate once before DONE: the standard gate from a clean worktree at the pushed
      head, plus <the mutation rows this brief asks for; tier 1: both ways>
      - does NOT prove: <…>

## Forbidden

<Version bumps, new dependencies, design changes — whatever this brief must not do beyond
the standing rules.>

## Findings (the builder writes; tables only)

| Gate run | Command | Exit | Counts |
|---|---|---|---|

| Mutation | What was broken | Which test failed, how | Restored run |
|---|---|---|---|

| File outside Scope | Why (compile-forced) | Commit |
|---|---|---|

| Brief says | Repo has | What the builder did |
|---|---|---|

Surprises (at most ten lines; a measurement that argues with the design goes here; for
visual briefs: what the owner should look at, where the camera was, the screenshots):
