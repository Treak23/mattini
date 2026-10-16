# Brief: M3-R1-fix-2 — The trees tie the terrain to 0.5 m, and refuse any other spacing
Status: DONE (43aeb86)

Written in the design realm from review finding M3-R1-P-01 (P2, Tier 1;
`docs/reviews/M3-R1-placement.md`) and the owner's answer of 2026-10-15 (SPEC §13 row 37);
executed by one fresh builder session under `docs/roles/BUILD.md`. Lane F-A of the fix wave
(`docs/briefs/M3-plan.md` §Fix wave).

## Goal

A terrain config whose `spacing_m` is not 0.5 can no longer give trees that float or sink: the
trees step and the manifest's trees block refuse it, naming `config/terrain.json`, the spacing
found and 0.5. Today a tree's base height comes from the 0.5 m grid whatever the terrain's
spacing (`pipeline/mattini/trees.py:485`), and at 1 m the placement lens measured 3'542 of the
village's 34'412 trees more than 5 cm off Terrain3D's ground (18'932 at 2 m), with every
command at exit 0. The harm becomes inexpressible (lesson 5) instead of watched for.

## Read first, in order

1. `docs/reviews/M3-R1-placement.md` §M3-R1-P-01.
2. `docs/SPEC.md` §7 (the terrain resolution, amended 2026-10-15) and §8, the trees, item 7.
3. `pipeline/mattini/trees.py`: `build_trees`, `_area`, `built_trees_block`.
4. The pinned test: `docs/briefs/pinning/M3-R1-fix-2/pipeline/tests/test_m3_r1_fix2_trees_spacing.py`.

## Decisions already made

1. **The owner's answer (b)** (2026-10-15, SPEC §13 row 37): refuse, do not interpolate. The
   switch to 1 or 2 m (§7) gains the trees step when the owner wants it; nothing of option (a)
   is built.
2. **Where:** `build_trees` refuses before it reads the lock, provenance or any input, before it
   creates anything under `out_dir` and before any progress line. `built_trees_block` refuses
   only when trees are built (their description exists); with none built it returns None as
   today, so a terrain-only manifest at 1 m is not blocked by trees nobody built.
3. **The message** is a `TreesError` naming `config/terrain.json`, the spacing found (as
   swisstopo writes it, `format(spacing, "g")`) and 0.5, and saying that the trees take their
   base heights from the 0.5 m grid (SPEC §8, trees, item 7). The pinned test checks the three
   names; the wording is yours.
4. Allowed spacings stay the terrain step's (0.5, 1, 2): the terrain step itself is not
   changed.

## Scope — files you may touch

- `pipeline/mattini/trees.py` (the two refusals; its module docstring's check order and item
  7's comment, which must say what the code now does).
- `pipeline/tests/test_m3_r1_fix2_trees_spacing.py` (the pinned copy, byte-identical) and, only
  if an existing test now fails for this reason, the trees test that builds at another spacing
  (none did in design's throwaway run: the full pytest passed 2176).
- This brief file (Status and Findings).

## Depends on

None.

## Done when (gates)

- [ ] `cmp docs/briefs/pinning/M3-R1-fix-2/pipeline/tests/test_m3_r1_fix2_trees_spacing.py
      pipeline/tests/test_m3_r1_fix2_trees_spacing.py` exits 0, and the file's seven cases pass.
      - does NOT prove: that the trees stand on the 0.5 m terrain (fix-1's scene test does).
- [ ] Mutation proof, in a throwaway clone, each from a saved diff undone with `git apply -R`:
      (1) the refusal in `build_trees` removed; (2) the one in `built_trees_block` removed;
      (3) the comparison made `> 1.0` (2 m refused, 1 m let through); (4) the refusal in
      `build_trees` moved after the lock check. Each fails a
      named case; the failing output in Findings, with the owner-visible harm it reproduces
      (trees floating on a 1 m terrain with exit 0).
      - does NOT prove: a mutation outside the four.
- [ ] Real check, if the real inputs are on the machine (else say so in Findings): set
      `spacing_m` to 1.0 in a scratch copy of `config/terrain.json` in a clone, run `python -m
      mattini trees` and `manifest`: the first ends `mattini: error:` naming config/terrain.json,
      exit 1, no traceback; with 0.5 the village's chunks are still design's six.
      - does NOT prove: the game at 1 m (no change there).
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`.
      - does NOT prove: that it renders or looks right.

## Forbidden

Interpolating the trees' heights at another spacing (option a); any change to the terrain
step, `config/terrain.json`, `config/trees.json` or a game file; a version bump; a new
dependency; a model's name or id anywhere in the repository.

## Findings (executor writes)

1. **What changed.** `pipeline/mattini/trees.py` only (plus the pinned test, byte-identical, `cmp`
   exit 0). One helper, `_spacing_refusal(area, terrain_config)`, raises a `TreesError` when the
   area's `spacing_m` is not `SOURCE_M` (0.5); the message starts `config/terrain.json:` and
   names the spacing found (`spacing_key`, so `1` or `2` as swisstopo writes it), 0.5, SPEC §8
   trees item 7 and SPEC §7. `build_trees` calls it straight after `_area` (the two configs'
   checks), so before the world checks, the lock, provenance, every input, anything under
   `out_dir` and every progress line. `built_trees_block` calls it right after the
   "description does not exist, return None" line, so a terrain-only manifest at 1 m is still
   written. The module docstring's item 7 and its check order, and both functions' docstrings,
   say what the code now does. The terrain step, both configs and the game are untouched.
2. **Pinned cases:** 7 passed. The full pytest in the gate: 2176 passed, 5 deselected, with the
   pinned file in (design's throwaway run counted the same 2176); no existing test needed a
   change.
3. **Mutations** (throwaway `git clone`, each from a saved diff undone with `git apply -R`,
   `git status` clean after each). Each reproduces the owner-visible harm: trees written or
   accepted on a 1 m or 2 m terrain with exit 0, floating or sunk.
   - (1) the call in `build_trees` removed: `FAILED ...::test_the_trees_step_refuses_a_terrain_that_is_not_half_a_metre[1.0]` and `[2.0]` (2 failed, 5 passed); the error that
     came instead was `the lock has no 'swissalti3d' entry`, i.e. the step went on to read the
     lock.
   - (2) the call in `built_trees_block` removed: `FAILED ...::test_the_manifest_refuses_built_trees_on_a_terrain_that_is_not_half_a_metre[1.0]` and `[2.0]` (2 failed, 5 passed).
   - (3) `spacing != SOURCE_M` made `spacing > 1.0` (2 m refused, 1 m let through): `FAILED`
     `test_the_trees_step_refuses_...[1.0]` and `test_the_manifest_refuses_built_trees_...[1.0]`
     (2 failed, 5 passed): the 1 m case, the one the placement lens measured at 3'542 trees
     off, is what the twin catches.
   - (4) the call in `build_trees` moved after the lock check: `FAILED
     test_the_trees_step_refuses_...[1.0]` and `[2.0]` (2 failed, 5 passed), the lock's
     refusal arriving first.
   - does NOT prove: a mutation outside the four. In particular the cases never have a
     spacing that is a non-`float` number (e.g. `1`), which `check_terrain_config` already
     refuses (`_is_spacing`, terrain.py:640) before this code runs.
4. **Real check, as far as this machine allows.** The raw swisstopo downloads are not on this
   machine (no `data/`; H7), so the village's six chunks (`config/trees.json`:
   2623-1095, 2623-1096, 2623-1097, 2624-1095, 2624-1096, 2624-1097) could not be rebuilt at
   0.5 here and were not; the gate's `config/trees.json` check and the pipeline tests that
   build at 0.5 are unchanged and green. In a clone with `spacing_m` 1.0 in
   `config/terrain.json`: `python -m mattini trees` printed `mattini: error:
   config/terrain.json: area 'village' has spacing_m 1, but the trees take their base heights
   from the 0.5 m terrain grid (docs/SPEC.md §8, trees, item 7) and stand off the ground at any
   other spacing; set spacing_m to 0.5 (...)`, exit 1, no traceback, nothing created. `python -m
   mattini manifest` with no trees built wrote the manifest, exit 0 (decision 2). With a
   stand-in `trees/village.json` (`{"stand-in": true}`, a scratch clone only, not data) the same
   `manifest` ended `mattini: error: config/terrain.json: ...`, exit 1; with 0.5 it refused the
   stand-in for its keys, not for the spacing. So the CLI path of both commands is driven, not
   only the functions. Not driven: the whole-village manifest with real built trees at 1 m.
5. **Render step.** `tools/gate.sh` has no render step yet at this head (`grep` finds none);
   `xvfb-run` is installed on this machine. Nothing here depends on it. No
   `MATTINI_SKIP_RENDER` was set anywhere.
6. **Two first-run gate failures, both mine, both fixed before the commit:** the word `village`
   in a new docstring tripped `test_the_pipeline_code_names_no_area` (M2-01's census of
   `pipeline/mattini/`), now "the real area"; and the new test file was untracked, which
   `test_repo_tracked.py` refuses until it is staged.
7. **Decision for design to audit:** none. The refusal sits after `_area` and before the world
   check, one of two places the pinned decisions allow ("before it reads the lock, provenance or
   any input"); the other, after the world check, would also pass the pinned cases. This one
   was chosen because the spacing is a property of the two configs alone, like the area, and
   needs no input.
