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

- [x] Each of the seven mutations in the table, applied in a throwaway clone from a saved diff,
      fails a named test (or is named in Findings as uncatchable, with why); the diff is undone
      with `git apply -R` and the failing output of each is recorded in Findings.
      - does NOT prove: that the shaders place the photo and the classes where the readers say
        (the text checks prove text; only a render proves it), nor that the fix covers a
        mutation outside the table.
- [x] The trees fixture stands on its own terrain, and every game test that uses
      `complete_world.gd` stays green.
      - does NOT prove: that the real village's trees stand on Terrain3D's ground (the
        placement lens measured 0 of 34'412 more than 5 cm off at the 0.5 m terrain).
- [x] Standard gate: `tools/gate.sh > gate.log && git commit …`; GUT's script count equals the
      `test_*.gd` files; the allowlist keeps every line.
      - does NOT prove: that it renders or looks right.

## Forbidden

Any change to a shader, a loader's behaviour, `tools/gate.sh`, `tools/export.sh` or a pipeline
module; a render step in the gate (design's question); a version bump; a new dependency; a
model's name or id anywhere in the repository.

## Findings (executor writes)

1. **The change** (tests and the fixture only; no shader, loader, `main.gd` or pipeline line
   moved):
   - `complete_world.gd`: the trees are one chunk written here, in the box's tile, standing on
     the world's own terrain: five trees (`TREES`, test data, labelled), each at the centre of one
     pixel of the 0.5 m grid placed through `WorldConfig` (to_local of the box's north-west
     corner, as `TerrainGrid` does), `y` the mean of the pixel's four vertices (SPEC §8, trees,
     item 7, written again in the fixture's words). `tree_records()` is public so a test can
     recompute them; `read_manifest()` is a public wrapper of `_parse`. The header's "they stand
     beside and below this terrain, not on it" is gone: it said the opposite of what is now true
     (lesson 42). The shared trees fixture's block (source, parameters) is still the base of the
     block; its three chunk files are no longer copied (they are for another world).
   - `test_scene_placement.gd`: `test_the_trees_sit_at_the_scene_origin` (the `Trees` node and
     each cell's `global_transform` is the identity) and
     `test_every_tree_stands_on_the_terrain_where_the_fixture_put_it` (one instance per tree; each
     recomputed record's `y` is `main._ground_height(x, z)` within 1 mm, and an instance origin,
     read from the MultiMesh buffer with the cell's global transform applied, lies within 1 mm of
     (x, ground, z)). Header and "Does NOT prove" extended.
   - `test_surface_grid.gd`: `test_the_texture_holds_the_class_bytes_row_by_row`: the texture's
     bytes hash to the block's `pixels_sha256`, and every texel's byte is `class_at`'s class at
     the texel's centre.
   - `test_m3_09_photo_shader.gd`: `test_the_photo_and_the_classes_are_placed_by_the_pinned_expressions`
     (the code lines naming `puv`, `photo_rect`, `surfaces_rect`, `texture(photo`, `class_weights(`
     or `vec2 xz =` as an exact list; `class_weights` as an exact function body) and
     `test_exactly_one_statement_assigns_the_photo_uv` (the count and the text of assignments to
     `puv` or a part of it). Comments are cut before comparing, so an edit to a comment does not
     fail them.
   - `test_m3_11_tree_conifer.gd`:
     `test_the_crown_colour_is_read_from_the_photo_at_the_origin_by_the_pinned_lines` (the six code
     lines naming `uv`, `photo_rect`, `textureLod(photo` or `vec3 origin =`).
   - Every shader test above says in a comment and in the file's header that it is a census:
     the text, never the render (lesson 5; design's question stays open in BLOCKED.md).
   - `main.gd` is untouched: its claim (lines 24 to 26, "the Buildings and Trees nodes and their
     meshes sit at the scene's origin, unturned and unscaled (test_scene_placement.gd)") is now
     true, which is the correction the brief allowed.
2. **The seven mutations** (a throwaway `git clone` of the repository with this brief's tests
   committed locally as a baseline; each mutation a saved diff applied, its named test script run,
   the diff undone with `git apply -R`, `git status` clean after every one; the edits are
   Appendix F's of the placement review, copied exactly). Baseline: each named script green.

   | id | named script | failing test | the failure |
   |---|---|---|---|
   | `GM-main-trees-offset` | `test_scene_placement` | `test_the_trees_sit_at_the_scene_origin`, `test_every_tree_stands_on_the_terrain_where_the_fixture_put_it` | `Transform3D(…, O: (1000, 0, 0))` expected the identity, twice; every tree's instance 985 to 1000 m from its place |
   | `SH-photo-uv-flip` | `test_m3_09_photo_shader` | `test_the_photo_and_the_classes_are_placed_by_the_pinned_expressions`, `test_exactly_one_statement_assigns_the_photo_uv` | two assignments to puv: `puv.y = 1.0 - puv.y;` after the pinned one |
   | `SH-photo-uv-shift` | `test_m3_09_photo_shader` | the same two | two assignments: `puv.x -= 0.1 / photo_rect.z;` |
   | `SH-class-half-texel` | `test_m3_09_photo_shader` | `test_the_photo_and_the_classes_are_placed_by_the_pinned_expressions` | the `t` line (and so the placement list and `class_weights`) without `- 0.5` |
   | `SH-class-ns-flip` | `test_m3_09_photo_shader` | the same | the `class_weights` body with `ivec2(p.x, size.y - 1 - p.y)` |
   | `GM-surf-texture-flip` | `test_surface_grid` | `test_the_texture_holds_the_class_bytes_row_by_row` | the texture's bytes hash `143b4a73…`, not the block's `c11c39de…`; the first wrong row is 0 |
   | `SH-tree-uv-zx` | `test_m3_11_tree_conifer` | `test_the_crown_colour_is_read_from_the_photo_at_the_origin_by_the_pinned_lines` | the `uv` line with `origin.zx` |

   Seven of seven fail a named test; none is left as uncatchable. Owner-visible harm each
   reproduces: every tree 1 km east of the terrain (`GM-main-trees-offset`); the photo upside down
   or 0.1 m off (`SH-photo-uv-*`); the surface classes half a texel off or mirrored on the ground
   (`SH-class-*`, `GM-surf-texture-flip`); the crowns coloured from another place
   (`SH-tree-uv-zx`). Two more, beyond the table, to show the new ground test is sensitive to its
   own subject: `X-tree-base-sunk-5cm` (`buffer.append(at.y - 0.05)` in `TreeLoader._cells`) and
   `X-tree-z-from-x` (`at.z + 0.01` in the same buffer): `test_every_tree_stands_on_the_terrain…`
   fails on all five trees each (0.0499 m and 0.0100 m from their places).
   - does NOT prove what the brief says it does not: the shaders place the photo and the classes
     where the readers say (the text checks prove text); nor a mutation outside the table. A
     census by line cannot see a placement change made through something it does not name: a
     uniform's value is `test_terrain_loader_*`'s; Terrain3D's own `vertex()` is the existing
     clay-equality test's, which a coordinated edit of both shaders would pass.
3. **The fixture stands on its terrain, measured.** The five trees' `y` (the mean of four
   vertices) equals Terrain3D's `get_height` there within 1 mm (the new test asserts it; measured
   on the fixture's heights: the five bases differ from each other by 0.47 m at least, and each
   mean differs from its pixel's north-west vertex by about 0.094 m, so a tree set from one vertex
   or from the wrong pixel fails the test by far more than 1 mm). The complete world's other tests that
   count trees (`test_main_scene_data`'s startup line: count above the chunk count) read the
   manifest, so they follow the new chunk (5 trees in 1 chunk).
   - does NOT prove: that the real village's trees stand on Terrain3D's ground (the placement
     lens measured 0 of 34'412 more than 5 cm off, at the 0.5 m terrain; at 1 m or 2 m they do
     not, M3 R1 P-01, which is design's).
4. **Not done, by the brief:** no render step in the gate (BLOCKED.md §Open, P-03); P-01's fix (a
   config change to 1 m or 2 m) untouched. Test-count effect: five new tests (two in
   `test_scene_placement`, one each in `test_surface_grid`, `test_m3_11_tree_conifer`, two in
   `test_m3_09_photo_shader`), no new test script, so GUT's script count is unchanged.

