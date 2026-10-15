# Brief: M3-R1-fix-1 — Gates for where the trees, the photo and the classes are placed
Status: OPEN

Written by the build orchestrator from review findings M3-R1-P-02 and, as its interim half,
M3-R1-P-03 (P2, Tier 1; `docs/reviews/M3-R1-placement.md`), executed by one fresh builder
session under `docs/roles/BUILD.md`. Lane J of the fix round, second, after M3-R1-fix-4 (they
share `game/tests/test_m3_11_tree_conifer.gd`).

## Goal

Hard Rule 4's harm, a silently shifted world, can no longer reach the trees, the photo or the
classes with the whole gate green. Seven mutations the placement lens applied leave the full
pytest and GUT green today; after this brief each fails a named test, or is named in Findings
as a mutation that no text or data check can catch (it is not hidden):

| id | mutation | what it misplaces |
|---|---|---|
| `GM-main-trees-offset` | `trees_node.position = Vector3(1000, 0, 0)` in `main.gd`'s `_show_trees` | every tree, 1 km east |
| `SH-photo-uv-flip` | `puv.y = 1.0 - puv.y;` after `terrain_photo.gdshader` line 375 | the photo, north-south |
| `SH-photo-uv-shift` | `puv.x -= 0.1 / photo_rect.z;` | the photo, 0.1 m |
| `SH-class-half-texel` | the `- 0.5` removed from `class_weights` | the classes, half a texel |
| `SH-class-ns-flip` | `texelFetch(surfaces, ivec2(p.x, size.y - 1 - p.y), 0)` | the classes, north-south |
| `GM-surf-texture-flip` | `image.flip_y()` before `ImageTexture.create_from_image(image)` in `SurfaceGrid` | the texture against `class_at`'s bytes |
| `SH-tree-uv-zx` | `origin.zx` in `tree_conifer.gdshader` | the crowns' colour, from another place |

(Each mutation's exact edit is in the report's Appendix F.) This is the interim half of P-03:
the render step the lens proposes is design's question (`docs/briefs/BLOCKED.md` §Open, M3 R1
P-03); the checks below are the ones the record already permits and are labelled a census
where they are one (lesson 5: a census proves text, never behaviour).

## Read first, in order

1. `docs/reviews/M3-R1-placement.md`: findings P-02 and P-03 in full, the Mutations table and
   Appendix F.
2. `game/scripts/main.gd` (the header's claim at lines 24 to 26, `_show_trees`,
   `_ground_height`), `game/tests/test_scene_placement.gd`, `game/tests/complete_world.gd`.
3. `game/shaders/terrain_photo.gdshader` (the `puv` line and `class_weights`),
   `game/shaders/tree_conifer.gdshader`, `game/scripts/terrain/surface_grid.gd`,
   `game/tests/test_m3_09_photo_shader.gd`, `game/tests/test_surface_grid.gd`.
4. brain.md H21, H25, lesson 34 (test data that can tell the right code from its likeliest
   wrong twin: an asymmetric case).

## Decisions already made

1. **The Trees node.** `test_scene_placement.gd` asserts that `Trees` and each
   `MultiMeshInstance3D` child have `global_transform == Transform3D.IDENTITY` on the complete
   world (as M2 R1 P-01's test does for the Buildings).
2. **The trees stand on the ground.** `complete_world.gd` gets a trees chunk that stands on its
   own terrain (a few trees at their terrain's bilinear height, as `docs/SPEC.md` §8 item 7
   computes it from the 0.5 m grid: the pipeline's rule, written in the fixture's own words and
   labelled test data); a test asserts that each instance origin in the MultiMesh buffer has y
   within 1 mm of `main._ground_height(x, z)`. The fixture's header comment ("stand beside and
   below this terrain, not on it") and every claim of `complete_world.gd` you change are
   re-read and corrected (Hard Rule 2, lesson 42).
3. **The surface texture.** `test_surface_grid.gd` gains a test that the texture's bytes equal
   the class bytes, row by row (not the size and format only).
4. **The shaders' placement expressions** are pinned as text, in `test_m3_09_photo_shader.gd`
   (the photo's uv, `class_weights`, the row direction) and `test_m3_11_tree_conifer.gd` (the
   tree's photo lookup), as line 375 is pinned today. A pin that is one line's substring does
   not catch a statement added after it (`SH-photo-uv-shift`): pin the count of assignments to
   `puv` and the exact text of each placement expression, so that each table row above fails.
   These tests say in a comment and in their "does NOT prove" line that they are a census:
   they prove the text, and a render would prove the behaviour (design's question).
5. A mutation that none of these can catch is not weakened to pass: name it in Findings with
   the reason.

## Scope — files you may touch

- `game/tests/test_scene_placement.gd`, `game/tests/complete_world.gd`,
  `game/tests/test_surface_grid.gd`, `game/tests/test_m3_09_photo_shader.gd`,
  `game/tests/test_m3_11_tree_conifer.gd` (shared with M3-R1-fix-4: build that brief first).
- New test files named `test_m3_r1_fix1_*`, only where an existing file cannot hold a test.
- `game/scripts/main.gd` only for comment corrections that a changed test makes true or false
  (the claim at lines 24 to 26), never behaviour.
- This brief file (Status and Findings).

## Depends on

M3-R1-fix-4 (same lane, built first).

## Done when (gates)

- [ ] Each of the seven mutations in the table, applied in a throwaway clone from a saved diff,
      fails a named test (or is named in Findings as uncatchable, with why); the diff is undone
      with `git apply -R` and the failing output of each is recorded in Findings.
      - does NOT prove: that the shaders place the photo and the classes where the readers say
        (the text checks prove text; only a render proves it), nor that the fix covers a
        mutation outside the table.
- [ ] The trees fixture stands on its own terrain, and every game test that uses
      `complete_world.gd` stays green.
      - does NOT prove: that the real village's trees stand on Terrain3D's ground (the
        placement lens measured 0 of 34'412 more than 5 cm off at the 0.5 m terrain).
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`; GUT's script count equals the
      `test_*.gd` files; the allowlist keeps every line.
      - does NOT prove: that it renders or looks right.

## Forbidden

Any change to a shader, a loader's behaviour, `tools/gate.sh`, `tools/export.sh` or a pipeline
module; a render step in the gate (design's question); a version bump; a new dependency; a
model's name or id anywhere in the repository.

## Findings (executor writes)

