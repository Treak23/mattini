# Brief: M3-11 — Trees in the game
Status: DONE (ce5e845)

Written in the design realm; executed by one fresh builder session under
`docs/roles/BUILD.md`. Lane F of wave 1 (`docs/briefs/M3-plan.md`).

## Goal

The village's trees stand where the LiDAR found them, as procedural conifers.

- **The reader:** `TreeChunks` reads the manifest's `trees` block and its chunk files, and
  checks them.
- **The loader:** `TreeLoader` builds one MultiMesh per 250 m cell of one procedural
  conifer. Each tree is scaled to its height and crown radius, turned about the vertical,
  and its crown is coloured from the photo at its position.
- A generic conifer, labelled: the data gives where and how tall, not the species.

The main scene uses it from M3-14 on.

## Read first, in order

1. `CLAUDE.md` (Hard Rules 2, 4); `brain.md` H5, H16, H21 (colour), H25 (MultiMesh
   headless, hung scripts).
2. `docs/SPEC.md` §8 *The trees* (the file and the game), §10 (M3's game).
3. `game/scripts/buildings/building_chunks.gd` and `building_loader.gd` (the reader
   pattern: the world check, the file checks), `game/scripts/world/world_config.gd`.
4. `tests/shared/trees_fixture/`, `tests/shared/trees_vectors.json` (design data).
5. The pinned tests: `docs/briefs/pinning/M3-11/`.

## Decisions already made

1. **`TreeChunks`** (`game/scripts/trees/tree_chunks.gd`, `class_name TreeChunks`, `extends
   RefCounted`).
   - **Constructor:** `static func from_manifest(path: String, world: WorldConfig) ->
     TreeChunks`, which returns null after its refusals (`push_error("TreeChunks: <path>:
     <problem>")`, as BuildingChunks does).
   - **Properties:** `chunks: Array[Dictionary]`, each {tile, trees, positions:
     PackedVector3Array, heights: PackedFloat32Array, radii: PackedFloat32Array}, in the
     block's order; `area`, `attribution`, `dataset` ("swisssurface3d"); `edition`: the
     first and last of the distinct editions of the block's swisssurface3d tiles, joined by
     "-" ("2021-2022"), one alone when all tiles share it.
   - **It refuses:**
     - a missing block, naming `python -m mattini trees`;
     - another `world_sha256` than the manifest's; a WorldConfig not the manifest's, or
       other axes than the owner's;
     - key sets that are not exact; another format;
     - a file path that is not plain, or a missing file (checked before any read, so no
       engine ERROR is printed);
     - a size other than 20 × trees; another SHA-256.
   - It never converts a coordinate: x, y and z in the file are local already.
2. **`TreeLoader.create(chunks: TreeChunks, parent: Node, photo: Texture2D = null,
   photo_rect: Vector4 = Vector4.ZERO) -> Node3D`** (`game/scripts/trees/tree_loader.gd`).
   It takes a texture and a rectangle, not a PhotoGrid, so this lane needs nothing from
   M3-09; M3-14 passes `photo.texture` and `photo.rect()`.
   - A node "Trees" holding one MultiMeshInstance3D per 250 m cell, named `"%d_%d" %
     [floori(x / 250), floori(z / 250)]` of the trees' local x and z.
   - Per instance: `Basis(Vector3.UP, yaw).scaled(Vector3(r, h, r))` at (x, y, z); the yaw is
     an integer hash of round(2x) and round(2z), in 4096 steps.
   - Each MultiMesh is filled with ONE `buffer` assignment, 12 floats per instance, with no
     custom data and no instance colour (H21, H25: headless, `set_instance_transform` is
     dropped).
   - One ShaderMaterial, `res://shaders/tree_conifer.gdshader`, as each instance's
     `material_override`. With a photo, its uniforms `photo` and `photo_rect` are set; without
     one, neither is bound.
   - Shadows on; `visibility_range_end` 3000 m (a tuning value, not pinned).
   - `const TREES_NOTE` for the credits (M3-14), exactly "Trees: one generic conifer shape,
     placed and sized from swissSURFACE3D; the data gives no species." (pinned in
     `test_tree_loader.gd`). One line is over gdlint's 100 characters; measured clean: two
     joined strings in brackets, `const TREES_NOTE := (`, then `"Trees: one generic conifer
     shape, placed and sized from swissSURFACE3D;"`, then `+ " the data gives no species."`,
     then `)`.
3. **The conifer:** procedural, built once in code.
   - Six drooping tiers with jittered rims (a fixed seed per variant) and a hexagonal trunk:
     138 vertices, 192 triangles; at most 256 (pinned).
   - Normalised: the top at y = 1, the widest rim at radius 1, so the instance scale gives
     the data's height and crown radius.
   - Three variants with the same topology: variant 0 in VERTEX, 1 and 2 in CUSTOM0 and
     CUSTOM1, picked in the shader by a hash of the instance's origin; `custom_aabb` the unit
     cylinder.
4. **The shader** (`tree_conifer.gdshader`):
   - `cull_disabled`; flat facets from screen-space derivatives;
   - the crown colour: `textureLod(photo, (origin.xz − photo_rect.xy) / photo_rect.zw,
     log2(max(2r / texel, 1)))` in the vertex shader, × 1.25 (a look value), from a
     `source_color` sampler (H21: colours never through instance data);
   - without a photo, a placeholder green (0.17, 0.23, 0.13) and a trunk brown, both
     labelled in the shader.
5. **The gate:** one scoped allowlist line, for TreeChunks' refusal tests:
   `TreeChunks: user://test_ @ res://tests/test_tree_chunks.gd # its refusal tests write broken manifests under user://test_tree_chunks on purpose (brief M3-11)`.
   Wave 1's one shared file: append at the end; on a rebase, keep every line and re-run the
   gate.
6. **Measured with design's throwaway** (headless, the real village):
   - TreeChunks 13.1 ms; TreeLoader 61.4 ms for 34'412 trees in 90 cells (at most 937 in a cell);
   - 192 triangles per tree: 6.6 M triangles if every tree were drawn. GPU time is
     unmeasured here (the owner's PC).

## Scope — files you may touch

- `game/scripts/trees/tree_chunks.gd`, `tree_loader.gd` and their `.uid` (new);
- `game/shaders/tree_conifer.gdshader` and its `.uid` (new);
- `game/tests/`: the pinned `test_tree_chunks.gd`, `test_tree_loader.gd`,
  `test_tree_loader_photo.gd` (new, with `.uid`), and your own new tests;
- `tools/gate_allowlist.txt` (the one appended line).

## Depends on

None in this wave. It reads design's trees fixture, not the pipeline step (M3-07, lane D,
meets it at the fixture).

## Done when (gates)

- [ ] The pinned copies are in place (`cp -r docs/briefs/pinning/M3-11/. .`) and stay
      byte-identical (`cmp`).
      - does NOT prove: that they are the right tests.
- [ ] Mutations, each failing a named pinned test, recorded:
      - 200 m cells;
      - no shadows;
      - no turn;
      - height and radius swapped;
      - the edition from the datasets config's list;
      - z mirrored in the reader;
      - `set_instance_transform` instead of `buffer`;
      - `photo_rect`'s width and depth swapped.
      - does NOT prove: the look, the colour encoding (H21) or GPU time.
- [ ] Optional: software screenshots (Compatibility) of the fixture's trees and, with
      the real village built in scratch, an isolated tree and a forest edge at 30 m and the
      village from 120 m, under `docs/briefs/shots/M3-11-*.jpg`, named in Findings. They are
      evidence, not a gate. `tools/shot.sh` renders
      the main scene, which uses this brief's code only from M3-14: render with a throwaway
      scene kept in scratch (never committed), or skip the shots and say so in Findings.
      - does NOT prove: the Forward+ look on the owner's GPU.
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that it renders or looks right.

## Forbidden

A tree mesh or texture from elsewhere (procedural only); colours through instance data;
touching the main scene; editing a pinned file or the fixture.

## Findings (executor writes)

1. **Built, as the brief decides:** `TreeChunks` (`game/scripts/trees/tree_chunks.gd`),
   `TreeLoader` (`tree_loader.gd`) and `game/shaders/tree_conifer.gdshader`, with their
   `.uid` files. The pinned tests are in place and byte-identical to
   `docs/briefs/pinning/M3-11/` (`cmp` on all three): 12 of 12 pass. Two test files of my
   own, `test_m3_11_tree_chunks_checks.gd` (10 tests) and `test_m3_11_tree_conifer.gd` (9).
   The first reaches every refusal the pinned tests leave open through `TreeChunks._read`,
   which returns the problem and prints no ERROR line, so the one allowlist line the brief
   names is enough. The conifer is 138 vertices and 192 triangles (six tiers of an apex, ten
   shoulders and ten rim points, and a hexagonal trunk), three variants, one `custom_aabb`
   (x and z from −1 to 1, y from the trunk's foot, −0.06, to 1).
2. **The gate:** `tools/gate.sh` exit 0 on the tree before the commit: pytest 743 passed
   (4 deselected), GUT 28 scripts, 141 tests, 6387 asserts, `---- All tests passed! ----`, gdlint
   and `gdformat --check` clean. The allowlist's line is appended at the end, verbatim from
   decision 5. Four rebases followed, because three other lanes landed while the gate ran
   (M3-12, M3-02 and M3-09, plus M3-12's status commit); each brought commits in, so the gate
   was re-run on every rebased tree. The allowlist conflicted twice (each lane appends at the
   end): resolved by keeping every line, so it holds `BuildingRoofs`, `PhotoGrid` and
   `TreeChunks` once each, none with `Ignoring script` or `Failed to load script`. The gate of
   the pushed tree (`ce5e845`): pytest 766 passed (4 deselected), GUT 37 scripts, 192 tests,
   8265 asserts, `---- All tests passed! ----`, exit 0, with M3-02's stricter gate (script
   count equal to the `test_*.gd` files, GUT's version line) in force.
3. **Mutations,** each applied alone, the tree tests run, then undone with `git apply -R`
   of its saved diff (`git status` showed only the staged tree afterwards). The harm each
   reproduces is the owner's: the village's trees in the wrong place, wrong size or without
   their shadows.
   - 200 m cells (`CELL_M`): `test_tree_loader.gd` `test_one_multimesh_per_250_m_cell` (the
     names `4_-1 4_0 5_-1`, not `3_-1 3_0 4_-1`) and
     `test_every_named_tree_stands_at_its_position_scaled_to_its_size`.
   - No shadows (`SHADOW_CASTING_SETTING_OFF`): `test_one_multimesh_per_250_m_cell`
     ("casts shadows").
   - No turn (yaw 0): `test_every_named_tree_stands_at_its_position_scaled_to_its_size`
     ("the turns differ from tree to tree").
   - Height and radius swapped (`Vector3(height, radius, height)`): the same test, every
     named tree, height and crown radius.
   - The edition from the datasets config's list (`editions[0]-editions[-1]`, "2019-2022"):
     `test_tree_chunks.gd` `test_the_fixture_chunks_are_read_as_designed`.
   - z mirrored in the reader (`−z`): `test_every_named_tree_is_where_the_world_config_puts_it`
     ("as written" and "to_local" for every tree).
   - `set_instance_transform` instead of `buffer`: `test_one_multimesh_per_250_m_cell` (the
     buffer reads 0 floats) and the position test ("an instance at the file's position").
   - `photo_rect`'s width and depth swapped: `test_tree_loader_photo.gd`
     `test_the_photo_is_bound_to_the_trees_material`.
   - Mine, each failing a named test of `test_m3_11_*`: a flipped winding (outward
     faces), a shader uniform renamed or a syntax error in the shader (the declared
     `photo` and `photo_rect`), `source_color` removed from the photo's declaration, a
     custom AABB half as wide, the owner's-axes check removed, the plain-path check removed,
     the missing-file check removed (the size message and an engine ERROR instead), the
     duplicate-tile check removed, a turn that ignores z, the block's key-set check removed.
   - **Does NOT prove:** the look, the colour encoding (H21) or GPU time.
4. **Software screenshots** (evidence, never a gate; not the Forward+ look):
   `docs/briefs/shots/M3-11-fixture-trees-photo.jpg` and `M3-11-fixture-trees-placeholder.jpg`.
   The fixture's 19 trees in a bare scene (a flat plane, a sun with shadows), made with a
   throwaway script kept in scratch and never committed, under Compatibility on Mesa's
   llvmpipe (Xvfb). The first binds a **synthetic gradient** as the photo (red grows with x,
   blue with z), not the real photo: the crowns' colours differ by position, so the vertex
   shader samples the photo at the tree. The second binds none: the placeholder green, which
   reads nearly black there. They show that the shader compiles and draws under a software
   GL, not what the owner's GPU shows. The real village was not built here (no swisstopo
   data in a container), so there is no shot of an isolated tree, a forest edge or the
   village.
5. **Timing,** headless, on 34'412 synthetic trees (random positions in a 2.5 × 3.5 km box,
   six chunks of one file each, so 140 cells, at most 287 in one; design's village has 90
   cells, at most 937): `TreeChunks.from_manifest` 7 to 12 ms, `TreeLoader.create` 40 to
   50 ms, `conifer()` 0.3 to 0.6 ms (three runs). Design measured 13.1 and 61.4 ms on the
   real village. GPU time and GPU memory are unmeasured here (the owner's PC).
6. **Stricter than the brief's list, on purpose:** the reader checks the exact key sets of
   the block, `lv95_box`, `parameters`, `source` (the four datasets, each named by its
   `dataset`), swisssurface3d's block and its tiles, and each chunk's entry. The brief says
   "key sets that are not exact" without the list; these are design's fixture's own. A seam
   for M3-07 (lane D): its written block must carry exactly these keys, which its pinned
   tests against the same fixture already require.
7. **Reuse and limits:** `TreeChunks._check_world` calls `BuildingChunks._check_world` (the
   one home of "this WorldConfig is the manifest's") and adds the owner's axes, as
   `TerrainGrid` does. The reader does not look at a tree's values (finite, positive): the
   SHA-256 of the file is the check, and the pipeline wrote them. The shader reads a tree's
   position in world space, so `photo_rect` must be in world space and the trees' parent at
   the origin, unturned and unscaled (the main scene's root is; both comments say so). A
   photo given with a rectangle of no width or depth leaves the placeholder, as no photo:
   M3-14 passes a validated PhotoGrid's rectangle.
8. **Not done:** the main scene does not use the loader (M3-14); no screenshot of the real
   village (see 4).
