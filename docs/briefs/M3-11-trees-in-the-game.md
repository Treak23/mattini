# Brief: M3-11 — Trees in the game
Status: OPEN

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
   - `const TREES_NOTE` for the credits (M3-14), for example "Trees: one generic conifer
     shape, placed and sized from swissSURFACE3D; the data gives no species."
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
- [ ] Software screenshots (`tools/shot.sh`, Compatibility) of the fixture's trees and, with
      the real village built in scratch, an isolated tree and a forest edge at 30 m and the
      village from 120 m, under `docs/briefs/shots/M3-11-*.jpg`, named in Findings. They are
      evidence, not a gate.
      - does NOT prove: the Forward+ look on the owner's GPU.
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that it renders or looks right.

## Forbidden

A tree mesh or texture from elsewhere (procedural only); colours through instance data;
touching the main scene; editing a pinned file or the fixture.

## Findings (executor writes)
