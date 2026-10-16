# Brief: M3-R1-fix-3 — The gate renders where the photo, the classes and the crowns' colour land
Status: OPEN

Written in the design realm from review finding M3-R1-P-03 (P2, Tier 1;
`docs/reviews/M3-R1-placement.md`) and the owner's answer of 2026-10-15 (SPEC §13 row 38, which
amends row 18); executed by one fresh builder session under `docs/roles/BUILD.md`. Lane F-B of
the fix wave (`docs/briefs/M3-plan.md` §Fix wave).

## Goal

`tools/gate.sh` gains a render step that measures, by number, where the photo shader puts the
photo and the surface classes and where the tree shader reads the crowns' colour, so that a
silent shift of any of them fails the gate. Today six such misplacements leave the full pytest
and GUT green and the first leaves the whole gate at exit 0; fix-1 pinned their expressions as
text, which proves text (lesson 5) and has gaps of its own (M3-V1-1, M3-V1-2). A software render
(Compatibility renderer, Mesa llvmpipe under Xvfb) tells each apart in about 19 s.

What a render proves here is placement, never the look: SPEC §12 and BUILD.md rule 2b (amended
2026-10-15) say which claims it gates.

## Read first, in order

1. `docs/reviews/M3-R1-placement.md`: §M3-R1-P-03, §The render checks, Appendix B
   (`render_check.gd`), Appendix C (`render_trees.gd`), Appendix F (the mutations' edits).
2. `docs/reviews/M3-V1.md` §V1-1, §V1-2.
3. `docs/SPEC.md` §12 (amended), `docs/roles/BUILD.md` rule 2b (amended), CLAUDE.md's gate
   paragraph and "What the gate cannot see" (amended).
4. `tools/gate.sh` (its header and `step` list), `tools/shot.sh` (how it calls `xvfb-run`),
   `pipeline/tests/test_gate_gut_run.py`, `game/tests/complete_world.gd`.
5. brain.md H12 (software rendering), H21 (colour under Compatibility), H25 (`--check-only`
   first, `timeout` around a SceneTree script).

## Decisions already made

1. **The step** is `step "render" …` after `gdformat --check`, running two SceneTree scripts
   under `xvfb-run -a timeout … "$GODOT" --path game --rendering-method gl_compatibility
   --resolution 1280x720 -s <script>`: the photo-and-classes check (from Appendix B) and the
   trees check (from Appendix C). Put them in `game/tests/render/` with names that do not start
   `test_` (GUT must not count them; the gate's script count stays the `test_*.gd` files). Each
   writes its own world under `user://` (the gate's `XDG_DATA_HOME` keeps runs apart), reads
   nothing of the shaders' text, prints one result line per check and exits non-zero on any
   failed assertion; the step also fails on a missing result line, a timeout, or a Godot
   `ERROR`/`SCRIPT ERROR` line (the gate's scan, with the allowlist as for the other steps).
2. **The assertions** (the lens's, measured): photo luminance correlation at shift 0 at least
   0.95 and above every flipped (north-south, east-west) and shifted (±0.4 m, the 17-step scans
   in x and z) alternative; the water mask's best shift 0 in x and z within the 0.05 m step, with
   agreement above the flipped data's; the trees' crown colour correlation at least 0.6 and the
   maximum over the same alternatives. If a threshold proves flaky over ten clean runs, record
   the ten values and file BLOCKED rather than loosening it.
3. **Where `xvfb-run` is missing** the step fails, naming it and the skip, unless
   `MATTINI_SKIP_RENDER=1` is set, in which case it prints `== render: SKIPPED
   (MATTINI_SKIP_RENDER=1): where the photo, the classes and the crowns' colour land is not
   checked` and passes. The variable is for a machine that cannot render (the owner's Windows);
   no brief, builder or lens in a container sets it, and the gate's log shows it when set.
4. **Fix-1's text pins stay** (cheap; they name the expression a render failure points at).
5. **No pinned file:** the reference implementation is the review's Appendix B and C (run
   by the lens on this tree), and the first gate below, eight mutations that the step must fail
   on its own, is the pin of the decisions: it proves behaviour, which a pinned text could not.
6. **Time:** the step's wall time in the container is recorded in Findings; over 60 s is a
   Findings item, not a reason to drop a check.

## Scope — files you may touch

- `tools/gate.sh` (the step, its helper and its header comment).
- New: `game/tests/render/*.gd` (the two scripts and any helper), and their `.uid` files if
  Godot writes them.
- `pipeline/tests/test_gate_gut_run.py` or a new `pipeline/tests/test_gate_render.py` (the
  refusal and the skip, tested by running the step's helper with `xvfb-run` hidden from `PATH`).
- `tools/gate_allowlist.txt`, only for an error line the render run prints that is measured
  benign (a Findings item each, scoped as narrowly as the gate allows).
- This brief file (Status and Findings) and `docs/briefs/shots/` (one shot per check, evidence).

## Depends on

None. (Fix-1 and fix-4, which this step's checks cover, are DONE.)

## Done when (gates)

- [ ] Each of the six P-03 mutations of Appendix F (`SH-photo-uv-flip`, `SH-photo-uv-shift`,
      `SH-class-half-texel`, `SH-class-ns-flip`, `GM-surf-texture-flip`, `SH-tree-uv-zx`) and
      V1-1's two (an assignment to `xz` in the photo shader after its declaration, one to `origin`
      in the tree shader after its), applied in a throwaway clone from a saved diff, makes the
      render step fail with the check's own result line (with fix-1's text pins removed for the
      run, so the render is shown to catch it alone); undone with `git apply -R`; output in
      Findings with the owner-visible harm each reproduces.
      - does NOT prove: placement under Forward+ or on the owner's GPU, the look, the colour
        encoding (H21: Compatibility shows none), or a mutation outside the eight.
- [ ] Ten clean runs of the step: every check passes, the values recorded (min and max).
      - does NOT prove: another Mesa or Godot build.
- [ ] The refusal and the skip, by your test: `xvfb-run` hidden, no variable → the step fails
      naming both; with `MATTINI_SKIP_RENDER=1` → the skip line printed, step passes.
      - does NOT prove: a machine without Mesa but with `xvfb-run` (the step fails on its missing
        result lines, which is the intended refusal; say what it prints).
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`, the render step included and
      not skipped.
      - does NOT prove: that it renders or looks right on the owner's PC.

## Forbidden

Any change to a shader, a loader, `main.gd` or a pipeline module; Forward+ or lavapipe in the
gate (H12: it works, but the step is Compatibility only, 2026-10-15); setting
`MATTINI_SKIP_RENDER` in any committed file; a version bump; a new dependency; a model's name or
id anywhere in the repository.

## Findings (executor writes)
