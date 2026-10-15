# Brief: M3-R1-fix-4 — The trees' flat normals point the right way
Status: OPEN

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

- [ ] `NORMAL` in `tree_conifer.gdshader` is `normalize(cross(dFdy(VERTEX), dFdx(VERTEX)))`.
      - does NOT prove: that the trees look right on the owner's GPU.
- [ ] Mutation: put the two arguments back; the new text test fails and names the order
      (record both runs in Findings, the saved diff undone with `git apply -R`).
      - does NOT prove: that the shader's lighting is right in any other respect (it proves
        the line).
- [ ] Render evidence in Findings: the review's sphere probe (a dozen lines, in the review)
      run before and after under `xvfb-run` in Compatibility (and in Forward+ on lavapipe
      where it starts: `VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json`, `apt-get
      install mesa-vulkan-drivers` if missing): the "front" and "back" centre pixels swap
      as the report's table shows. One software screenshot of trees from the south (a view
      like `game/tools/shot.gd`'s `lookN,2623020,1095720,30,0,15` on the fixture or the
      real village) to `docs/briefs/shots/M3-R1-fix-4-*.jpg`.
      - does NOT prove: that it renders or looks right on the owner's PC (software
        rendering; Forward+ is the owner's check).
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that it renders or looks right.

## Forbidden

Any change to another shader, a colour, light or exposure value, or the loader's
parameters; a new dependency; a version bump; a model's name or id anywhere in the
repository.

## Findings (executor writes)

