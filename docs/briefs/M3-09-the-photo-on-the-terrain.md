# Brief: M3-09 — The photo on the terrain
Status: OPEN

Written in the design realm; executed by one fresh builder session under
`docs/roles/BUILD.md`. Lane E of wave 1, first (`docs/briefs/M3-plan.md`).

## Goal

The terrain shows the 2023 aerial photo at 0.2 m, placed through the world config.
- **The reader:** `PhotoGrid` reads the manifest's `photo` block, checks it, decodes the JPEG
  and makes a mipmapped texture.
- **The shader:** a new Terrain3D override shader, `terrain_photo.gdshader`, samples the
  texture by world position.
- **The loader:** `TerrainLoader` takes an optional PhotoGrid. With one, it uses the new shader
  and sets its rectangle; without one, it keeps M2's clay look.

Roads, paths, water and rock come next in this lane (M3-10); the main scene uses all of it
from M3-14 on.

## Read first, in order

1. `CLAUDE.md` (Hard Rules 2, 4); `brain.md` H4, H5, H11, H12, H21, H24, H25.
2. `docs/SPEC.md` §6, §8 *The terrain grid* (the game), *The photo* (the game), §10 (M3's
   game).
3. `game/scripts/terrain/terrain_grid.gd`, `terrain_loader.gd`,
   `game/shaders/terrain_clay.gdshader`, `game/scripts/world/world_config.gd`,
   `game/tests/test_terrain_loader*.gd`.
4. `tests/shared/photo_fixture/`, `tests/shared/photo_vectors.json` (design data).
5. `docs/briefs/sketches/terrain_photo.gdshader.sketch`: design's shader sketch. It compiles
   and was validated in software on the real village. You write and own the real shader;
   its NEW (M3-10) sections belong to the next brief.
6. The pinned tests: `docs/briefs/pinning/M3-09/`.

## Decisions already made

1. **`PhotoGrid`** (`game/scripts/terrain/photo_grid.gd`, `class_name PhotoGrid`, `extends
   RefCounted`).
   - **Constructor:** `static func from_manifest(path: String, world: WorldConfig) ->
     PhotoGrid`, which returns null after its refusals (push_error, as TerrainGrid does).
   - **Properties:** `texture` (ImageTexture, RGB8, columns × rows, with mipmaps; row 0 the
     north edge), `x0`, `z0` (the north-west corner, `world.to_local(e_min, n_max, h)`),
     `width_m`, `depth_m`, `columns`, `rows`, `cell_m`, `area`, `dataset`, `edition`,
     `attribution`; `rect() -> Vector4` = (x0, z0, width_m, depth_m).
   - **It refuses:**
     - a missing block, naming `python -m mattini download photo` then `python -m mattini
       photo`;
     - another `world_sha256` than the manifest's;
     - a WorldConfig that is not the manifest's, or that has other axes than the owner's;
     - a key set that is not exact;
     - a cell not in 0.2, 0.5, 1;
     - columns × cell or rows × cell off the box by more than 1 mm;
     - a file path that is not plain;
     - another SHA-256;
     - a decoded size other than columns × rows RGB8.
   - It decodes with `Image.load_jpg_from_buffer`, then `generate_mipmaps()`, then
     `ImageTexture.create_from_image()`. Measured on the village: 1.3–1.8 s, 0.3 s and
     0.7–0.9 s; about 590 MiB of texture memory. RGB8 becomes RGBA8 on most Vulkan GPUs, about
     0.8 GB. An exported build cannot compress at runtime (H21), and the owner's RTX 4090 has
     room.
2. **`TerrainLoader.create(grid, parent, photo: PhotoGrid = null, surfaces: SurfaceGrid =
   null) -> Terrain3D`.** The `surfaces` parameter is M3-10's; add it then.
   - With a photo, the material's shader is `res://shaders/terrain_photo.gdshader`, set
     **before** any parameter: Terrain3D drops a parameter set before the shader declares it.
   - Then `height_offset_m`, `photo` and `photo_rect` = `photo.rect()` are set.
   - Without a photo, the clay shader exactly as today.
3. **The shader** (this brief's part). Terrain3D's minimum shader as in
   `terrain_clay.gdshader` (vertex() and the normal code unchanged), without the contour
   lines.
   - `uniform sampler2D photo : source_color, filter_linear_mipmap_anisotropic,
     repeat_disable;` and `uniform vec4 photo_rect;`.
   - `uv = (world.xz − photo_rect.xy) / photo_rect.zw`, sampled with `texture()` outside any
     branch, so the derivatives stay valid. Outside [0, 1]², the neutral colour (0.52, 0.50,
     0.47).
   - Roughness 0.95.
   - World-space derivatives: no seam at Terrain3D's 1024 m region borders. Measured: at most
     2 grey levels across, where a region-space `textureGrad` made −27.
4. **Testing headless.** `Terrain3DMaterial.get_shader_param()` returns null headless, so the
   pinned tests read the material's `_shader_parameters` store, and the declarations through
   `Shader.get_shader_uniform_list()` (H25). The photo's texels are read through
   `texture.get_image()`, which keeps the decoded image even headless.
5. **The gate:** one scoped allowlist line, for PhotoGrid's refusal tests:
   `PhotoGrid: user://test_ @ res://tests/test_photo_grid.gd # its refusal tests write broken manifests under user://test_photo_grid on purpose (brief M3-09)`.
   Wave 1's one shared file: append at the end; on a rebase, keep every line and re-run the
   gate.

## Scope — files you may touch

- `game/scripts/terrain/photo_grid.gd` and its `.uid` (new);
  `game/scripts/terrain/terrain_loader.gd`;
- `game/shaders/terrain_photo.gdshader` and its `.uid` (new);
- `game/tests/`: the pinned `test_photo_grid.gd` and `test_terrain_loader_photo.gd` (new,
  with `.uid`), and your own new tests;
- `tools/gate_allowlist.txt` (the one appended line).

Not `main.gd` or `main.tscn` (M3-14); not `terrain_grid.gd` (M3-02 changes a refusal text
there in lane B).

## Depends on

None in this wave. It reads design's photo fixture, not the pipeline step (M3-04, lane C,
meets it at the fixture). M3-10 follows in this lane.

## Done when (gates)

- [ ] The pinned copies are in place (`cp -r docs/briefs/pinning/M3-09/. .`) and stay
      byte-identical (`cmp`).
      - does NOT prove: that they are the right tests.
- [ ] Mutations, each failing a named pinned test, recorded:
      - the photo given but ignored;
      - `photo_rect` from the terrain grid;
      - parameters set before the shader;
      - z0 from n_min;
      - the image flipped north-south.
      - does NOT prove: what a GPU draws.
- [ ] Software screenshots (`tools/shot.sh`, Compatibility) of the fixture and, with a scratch
      build of the real village (terrain from `download terrain` and `terrain`; a 0.2 m
      photo built with M3-04's function once lane C has landed, or by the rule in
      `docs/briefs/M3-04-the-photo-step.md` with Pillow in a throwaway environment): the
      start view and 60 m over the centre, under `docs/briefs/shots/M3-09-*.jpg`, named in
      Findings. They are evidence, not a gate.
      - does NOT prove: the Forward+ look on the owner's GPU.
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that it renders or looks right.

## Forbidden

Changing Terrain3D's vertex or normal code, the reader's rules, design's fixture or a pinned
file; compressing the photo; touching the main scene.

## Findings (executor writes)
