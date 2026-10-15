# Brief: M3-R1-fix-4 — The trees' flat normals point the right way
Status: DONE (77e8508)

Written by the build orchestrator from review finding M3-R1-G-01 (P1;
`docs/reviews/M3-R1-game.md`), executed by one fresh builder session under
`docs/roles/BUILD.md`. Lane J of the fix round, first; M3-R1-fix-1 follows in this lane
(they share `game/tests/test_m3_11_tree_conifer.gd`).

## Goal

Every tree is lit from the right side. `game/shaders/tree_conifer.gdshader` builds its flat
normal as `cross(dFdx(VERTEX), dFdy(VERTEX))`; in Godot 4.6.3 the face normal from screen
derivatives is `cross(dFdy(VERTEX), dFdx(VERTEX))` (the terrain shader's own flat normal,
`terrain_photo.gdshader`, uses that order). The tree's `NORMAL` points into the tree, so
facets that face the sun are black and facets that face away are sunlit, in Compatibility and
in Forward+ (the lens measured both). The review's reproduction is the gate: the line's two
arguments swapped, and a test that pins the order.

## Read first, in order

1. `docs/reviews/M3-R1-game.md` finding G-01 in full (the sphere probe, the table, the
   mutation).
2. `game/shaders/tree_conifer.gdshader` (line 75 and the header's claims),
   `game/shaders/terrain_photo.gdshader` around line 358.
3. `game/tests/test_m3_11_tree_conifer.gd` (the existing `source_color` text check).
4. brain.md H21 (colours and renderers), H12 (software rendering).

## Decisions already made

1. The fix is the swap of the two `cross` arguments in the shader's `NORMAL` line; no other
   change to the shader's look (no colour, light or ambient parameter changes).
2. The order is pinned by text beside the existing `source_color` check, labelled a census
   (it proves the line, not the render, lesson 5), with its own "does NOT prove" line.
3. The render evidence goes in Findings, not into the gate (the gate runs no render:
   `docs/briefs/BLOCKED.md` §Open, M3 R1 P-03, is design's question).

## Scope — files you may touch

- `game/shaders/tree_conifer.gdshader`, `game/tests/test_m3_11_tree_conifer.gd`.
- This brief file (Status and Findings) and `docs/briefs/shots/M3-R1-fix-4-*.jpg`.

## Depends on

None.

## Done when (gates)

- [x] `NORMAL` in `tree_conifer.gdshader` is `normalize(cross(dFdy(VERTEX), dFdx(VERTEX)))`.
      - does NOT prove: that the trees look right on the owner's GPU.
- [x] Mutation: put the two arguments back; the new text test fails and names the order
      (record both runs in Findings, the saved diff undone with `git apply -R`).
      - does NOT prove: that the shader's lighting is right in any other respect (it proves
        the line).
- [x] Render evidence in Findings: the review's sphere probe (a dozen lines, in the review)
      run before and after under `xvfb-run` in Compatibility (and in Forward+ on lavapipe
      where it starts: `VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json`, `apt-get
      install mesa-vulkan-drivers` if missing): the "front" and "back" centre pixels swap
      as the report's table shows. One software screenshot of trees from the south (a view
      like `game/tools/shot.gd`'s `lookN,2623020,1095720,30,0,15` on the fixture or the
      real village) to `docs/briefs/shots/M3-R1-fix-4-*.jpg`.
      - does NOT prove: that it renders or looks right on the owner's PC (software
        rendering; Forward+ is the owner's check).
- [x] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that it renders or looks right.

## Forbidden

Any change to another shader, a colour, light or exposure value, or the loader's
parameters; a new dependency; a version bump; a model's name or id anywhere in the
repository.

## Findings (executor writes)

1. **The change.** `tree_conifer.gdshader`'s `NORMAL` is now
   `normalize(cross(dFdy(VERTEX), dFdx(VERTEX)))`, with a two-line comment above it saying why
   (a comment only: no colour, light or ambient value moved). The new test
   `test_the_flat_normal_is_built_as_cross_dfdy_dfdx` (`test_m3_11_tree_conifer.gd`, beside the
   `source_color` check) reads the shader's text: exactly one statement starting with `NORMAL`,
   and it is that line. It is labelled a census in a comment and in the file's header, whose
   "Does NOT prove" now names the lighting. It also fails a second `NORMAL` statement added
   after the line, or `NORMAL` replaced (the review's s3, `vec3(0, 1, 0)`).
2. **Mutation** (a throwaway `git clone` of the repository, the fix applied from a saved diff,
   the mutation from its own saved diff: the two arguments back):
   - fix applied, `test_m3_11_tree_conifer.gd`: `Tests 10, Passing Tests 10, Asserts 3073`,
     `---- All tests passed! ----`;
   - mutation applied: `Passing Tests 9, Failing Tests 1`, `test_the_flat_normal_is_built_as_cross_dfdy_dfdx`
     `[Failed]`, `["NORMAL = normalize(cross(dFdx(VERTEX), dFdy(VERTEX)));"] !=
     ["NORMAL = normalize(cross(dFdy(VERTEX), dFdx(VERTEX)));"]`, message "one NORMAL statement,
     with dFdy first: dFdx first points into the tree";
   - undone with `git apply -R`: 10 of 10 again. The clone was deleted after.
   - Owner-visible harm it reproduces: every tree lit from the inside (G-01).
3. **Render evidence** (software; not the owner's GPU). Mesa 25.2.8's lavapipe was installed with
   `apt-get update` then `apt-get install mesa-vulkan-drivers vulkan-tools` (the package list
   was empty until `apt-get update`); Forward+ ran with
   `VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json xvfb-run -a godot --rendering-driver
   vulkan --rendering-method forward_plus`. The review's sphere probe, run unchanged but for the
   shader's line chosen by an argument, centre pixel (r, g, b of 0 to 1):

   | `NORMAL = normalize(…)` | renderer | front | back |
   |---|---|---|---|
   | `cross(dFdx, dFdy)` (shipped before) | Compatibility | (0, 0, 0) | (0.9137, 0.8157, 0.7529) |
   | `cross(dFdy, dFdx)` (this fix) | Compatibility | (0.6078, 0.4157, 0.2275) | (0, 0, 0) |
   | `cross(dFdx, dFdy)` (shipped before) | Forward+ on lavapipe | (0, 0, 0) | (1.0, 0.9569, 0.8588) |
   | `cross(dFdy, dFdx)` (this fix) | Forward+ on lavapipe | (0.8039, 0.6745, 0.498) | (0, 0, 0) |

   The "before" rows equal the review's measured values exactly; the two "front" and "back"
   columns trade places, as the report's table has it. The shipped shader itself, the
   fixture's 19 trees through `TreeLoader.create` (no photo: the placeholder crown), the sun
   along the view ("front") and towards the camera ("back"), mean RGB (0 to 255) of every
   non-background pixel, 2287 pixels:

   | | Compatibility front / back | Forward+ front / back |
   |---|---|---|
   | before | (0, 0, 0) / (71, 73, 69) | (0, 0, 0) / (71, 75, 70) |
   | after | (30, 41, 22) / (0, 0, 0) | (34, 47, 26) / (0, 0, 0) |

   Two software screenshots, 1280 x 720, Compatibility on llvmpipe, the fixture's 19 trees on a
   bare plane under the main scene's sun (azimuth 183°, elevation 52°, through the world config)
   and its sky and exposure copied, the camera south of the trees looking north (the sun-facing
   side): `docs/briefs/shots/M3-R1-fix-4-trees-south-before.jpg` (black silhouettes, a shipped
   shader with the arguments back) and `docs/briefs/shots/M3-R1-fix-4-trees-south-after.jpg`
   (faceted dark green crowns). The crowns stay dark because they carry the labelled
   placeholder green (no photo bound, as in M3-11's shots), not because of the normal. The
   probe and shot scripts were throwaways in the scratch folder, never committed.
4. **Not done, by the brief:** the real village (no swisstopo data in a container) was not
   rendered; the G-01 report's village views are the review's. brain.md H12's "Forward+ on
   lavapipe crashes" does not hold here either (Mesa 25.2.8, the review's note): it is the
   orchestrator's to correct, not this brief's scope.

