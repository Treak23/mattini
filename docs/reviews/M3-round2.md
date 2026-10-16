# M3 round R2 — adjudication

The build orchestrator, 2026-10-16. Head reviewed `a6779f3` (placement: diff `410dbba..a6779f3`, the
fixes fix-1, fix-4, fix-5, fix-2 and fix-3; surfaces: diff `d8d2471..da8914f`, fix-6). The two lens
reports are `M3-R2-placement.md` (`f72fe38`) and `M3-R2-surfaces.md` (`4aa4828`), each committed alone.
Tiers per the plan: placement Tier 1; surfaces Tier 2 with Hard Rule 5's full discipline. Each lens ran in
its own session and fresh clones, built the real village from the pinned inputs (manifest `3ca0445c…`,
324'359 bytes, in both and in the orchestrator's own build) and, for placement, ran the standard gate at
the head: exit 0 (pytest 2228, GUT 47 scripts, 261 tests, 9760 asserts, the render step run).

**Counts:** placement 0 P0, 0 P1, 0 P2, 4 P3; surfaces 0 P0, 0 P1, 0 P2, 3 P3. No grade was changed.

**Result:** the Tier 1 round is **clean** (no P2 or above); **fix-6 is verified**. No fix brief is written,
and no lens re-runs.

## Dispositions

| id | grade | what | disposition |
|---|---|---|---|
| P-01 | P3 | the trees check passes with no tree drawn (`VISIBILITY_END_M := 0.5`, a `discard`, a zero draw count all leave the whole gate at exit 0), and its PASS line says "over 20 trees" | residue. Graded P3 because "that anything renders" is the owner's check (BUILD.md rule 2b, amended 2026-10-15; the step's header limits it to where the crowns' colour is read). The lens's fix is a few lines in `render_trees.gd` (a presence clause: every crown disc differs from the bare ground by at least 15 luminance units, measured minimum 30) |
| P-02 | P3 | the render world is 16 m wide, flat, positive coordinates only: `abs()` of `xz`, `puv` or `origin`, a scale of 1.002 and a horizontal shift of the terrain's own vertices pass; the same step in a north-west world catches the `abs()` edits | residue (nine edits move the world; the lens's Appendix D) |
| P-03 | P3 | the classes check reads the water class only; rock, road and path and the class codes pass the render (fix-1's text pins see the class-specific edits) | residue; the wording is design's: CLAUDE.md, SPEC §12 and the `tools/gate.sh` header say "the surface classes" |
| P-04 | P3 | the 0.1 m decision of the classes check rests on three samples in one direction (`class_at` half a texel east passes; `test_surface_grid.gd` fails it) | residue (decide by the agreement at no shift, not by the argmax) |
| V1-2, V1-3 | P3 | carried from V1 and still open: fix-4's normal census counts lines that begin with `NORMAL`; the scene-level tree tests see one cell south-east of the origin | residue (V1-1 is closed in behaviour by the render step) |
| S-01 | P3 | no test gives a 40 to 63 digit lower-case hex string to the SHA-256 check of `expected_png_sha256` or `expected_pixels_sha256` (the regex `{64}` loosened to `{40,64}` keeps pytest green; only the message naming the key is lost, the comparison still refuses) | residue (two parametrised cases) |
| S-02 | P3 | RELEASE.md §C's new box prints nothing and exits 1 on a manifest of the wrong size, so "its output in the release record" would record nothing | handled in the release walk, not by editing RELEASE.md: the record carries `wc -c` and the `sha256sum -c` line with the exit status, from the checkout's root. The box's wording is for design |
| S-03 | P3 | SPEC §8's line for the shape of `config/surfaces.json` omits `expected_png_sha256` (a design session that rebuilds the config from it writes one the check refuses) | residue, design's file (with `tests/shared/surfaces_vectors.json`'s stale "about", already listed) |

## What the round proved (the must-proves)

- **fix-2:** the trees step and the manifest's trees block refuse every terrain spacing but 0.5, naming
  `config/terrain.json`: 17 mutations of the refusals, their messages and their order, 16 fail a named case
  (the survivor is a position the pinned decision allows); the commands at 1 m and 2 m end `mattini: error:`
  with no traceback and change no file; with the trees directory absent the manifest still writes at 1 m. The
  real village's 34'412 trees stand on Terrain3D's ground (0 more than 5 cm off, worst 0.244 mm), in the
  owner's world and in a scratch world with another origin, a height offset and the grid north-west of it.
- **fix-3:** the render step alone fails every named misplacement of the photo, the classes and the crowns'
  colour (a flip, a half texel, 0.1 m, swapped axes, a second assignment to `puv`, `xz`, `origin` or `uv`);
  ten clean runs give the same numbers (photo 0.9761, trees 0.9380, classes 83090 to 83092 of 83427); the
  whole `tools/gate.sh` over three mutations that passed the gate in R1 and V1 now exits 1 at its render
  step. The refusal where `xvfb-run` is missing and the skip are as the brief says; nothing sets
  `MATTINI_SKIP_RENDER`. The lens judged both of the builder's choices (the 0.4 m disc estimator with the
  threshold 0.6 unchanged; the variable excusing only a machine without `xvfb-run`) right, with margins
  measured on five other photos.
- **fix-6:** the step and the manifest refuse a PNG another deflate writes (zlib-ng 2.2.5 through a shim,
  mattini untouched): `surfaces` ends `mattini: error:` naming the machine's zlib, both SHA-256s and the
  config, and writes nothing; `manifest` names `python -m mattini surfaces`; the full pytest fails with nine
  named cases and the gate exits 1 at pytest. Terrain, buildings, photo, roofs and trees never call a Python
  deflate (all 24 output files byte-identical under the shim). The village's three PNG values equal what
  design's pixels give through an independent encoder, on zlib 1.3, uv's managed 1.3.2 and vanilla 1.2.11,
  1.2.13 and 1.3.1. 23 of 26 mutations fail a named test (the three survivors are S-01 and the restored
  allowance, which cannot show on the machine that wrote the value; eight other cases fail it under the shim).
- **The pairs (lesson 8):** `trees.py` imports none of the helpers fix-6 changed; `surfaces` and `trees`
  give the same 24 files in either order; fix-4's lighting under fix-3's estimator (the reason for the disc);
  fix-1's text pins beside fix-3's render (they cover different gaps); fix-5's guards under fix-3's worlds.

## Not proven, said out loud

That anything renders or looks right on the owner's GPU; Forward+, the colour encoding (H21); the Windows
build starting; **Windows' zlib** (not measured: CPython 3.14's Windows builds move to zlib-ng, and the
project's `requires-python = ">=3.13,<3.14"` keeps that out until the pin is raised, when the step refuses
naming the machine's zlib); an empty forest (P-01); the render step's blind zones (P-02 to P-04); the game on
a 1 m terrain.

## Two honesty items for the release record (Hard Rule 2)

The render step's PASS line "over 20 trees" counts the trees in the render world, not the trees drawn (P-01),
and the docs say it gates "the surface classes" where it reads the water class (P-03). Neither is a placement
fault, and the release record's *does NOT prove* list says both plainly.
