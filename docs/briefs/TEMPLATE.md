# Brief: <arc>-<nn> — <title>
Status: OPEN

Written in the design realm; executed by one fresh executor session (or the owner, if the
board says `Builder: owner`). Executor rules: `docs/roles/BUILD.md`. Copy this template;
delete the guidance lines in <>.

## Goal

<One paragraph, outcome language: what exists and works when this is done. One slice,
never "build the shell".>

## Read first, in order

<Files and SPEC sections this depends on. Name the ground truth explicitly (e.g.
`config/world.json`, a dataset's documentation).>

## Decisions already made

<With their source: SPEC section, RULINGS line, owner's word.>

## Scope — files you may touch

<Explicit list or narrow glob. Anything else is off limits except compile-forced
necessities named in the commit message.>

## Depends on

<Brief ids, or "none". The supervisor uses this and Scope to decide whether two builders
may run at once.>

## Done when (gates)

<Runnable checks, command plus expected result. The pinning tests already exist in the
tree (under `docs/briefs/pinning/<id>/`, WORKFLOW §Brief lifecycle); a missing one is a
BLOCKED question. Every gate carries a "does NOT prove" line; if
it is hard to write, the gate is not understood yet.>

- [ ] <gate 1>
      - does NOT prove: <the claim this gate cannot settle>
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: <e.g. that it renders or looks right — required on every brief
        that changes what is drawn>

## Forbidden

<Version bumps, new dependencies, design changes — whatever this brief must not do beyond
the standing rules.>

## Findings (executor writes)

<Numbers, surprises, out-of-scope touches, follow-up candidates. A measurement that argues
with the design goes HERE; the build follows the spec. For visual briefs: what the owner
should look at, and where the camera should be, and the software screenshots committed
under `docs/briefs/shots/` (SPEC §12).>
