# Brief: M3-R1-fix-2 — The trees tie the terrain to 0.5 m, and refuse any other spacing
Status: OPEN

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
