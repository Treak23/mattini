# Brief: M3-09 — The photo on the terrain
Status: DONE (e6a6ed2)

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
     PhotoGrid`, which returns null after its refusals, each one `push_error("PhotoGrid:
     <path>: <problem>")` as TerrainGrid does. M3-14's allowlist line and refusal tests
     depend on that form, the colon after the path included.
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
- [ ] Optional: software screenshots (Compatibility) of the fixture and, with a scratch
      build of the real village (terrain from `download terrain` and `terrain`; a 0.2 m
      photo built with M3-04's function once lane C has landed, or by the rule in
      `docs/briefs/M3-04-the-photo-step.md` with Pillow in a throwaway environment): the
      start view and 60 m over the centre, under `docs/briefs/shots/M3-09-*.jpg`, named in
      Findings. They are evidence, not a gate. `tools/shot.sh` renders
      the main scene, which uses this brief's code only from M3-14: render with a throwaway
      scene kept in scratch (never committed), or skip the shots and say so in Findings.
      - does NOT prove: the Forward+ look on the owner's GPU.
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that it renders or looks right.

## Forbidden

Changing Terrain3D's vertex or normal code, the reader's rules, design's fixture or a pinned
file; compressing the photo; touching the main scene.

## Findings (executor writes)

Landed as `e6a6ed2` on `main`. Standard gate on that head: exit 0, pytest 766 passed (4
deselected), GUT 32 scripts, 161 tests, 4678 asserts, `GUT version:  9.6.1`.

1. **The pinned copies** (`test_photo_grid.gd`, `test_terrain_loader_photo.gd`) are in place and
   `cmp`-identical to `docs/briefs/pinning/M3-09/` (checked again after the last rebase). The
   auto-mode classifier refused the brief's `cp -r docs/briefs/pinning/M3-09/. .` (it copies
   into the repository root), so the two new files were copied one by one to their exact
   paths with `cp -n`; same result.
2. **Mutations**, each applied to the committed file, run against the two pinned scripts plus
   my census test, reverted by `git apply -R` of the saved diff (the tree was clean after
   each). Failing tests are GUT's own Run Summary list.

   | # | Mutation | Failing test(s) | Owner-visible harm reproduced |
   |---|---|---|---|
   | 1 | the photo given but ignored (`photo = null` first in `create`) | `test_terrain_loader_photo::test_with_a_photo_the_terrain_uses_the_photo_shader`, `::test_the_photo_and_its_rectangle_reach_the_shader` | the village stays clay with a photo built |
   | 2 | `photo_rect` from the terrain grid | `test_terrain_loader_photo::test_the_photo_and_its_rectangle_reach_the_shader` | the photo stretched over the terrain's box, off the ground |
   | 3 | the photo's parameters set before the shader | `test_terrain_loader_photo::test_the_photo_and_its_rectangle_reach_the_shader` | Terrain3D drops them: the shader samples an unset texture (no photo) |
   | 4 | z0 from n_min | `test_photo_grid::test_the_fixture_photo_is_read_as_designed`, `::test_the_named_points_read_their_texels`, and `test_terrain_loader_photo::test_the_photo_and_its_rectangle_reach_the_shader` | the photo shifted a whole depth to the south |
   | 5 | the image flipped north-south | `test_photo_grid::test_the_named_points_read_their_texels` | the village mirrored north to south |
   | 6 | (my census) one constant in Terrain3D's `vertex()` changed | `test_m3_09_photo_shader::test_the_vertex_and_terrain_normal_code_is_terrain3ds` | Terrain3D's code silently edited |

   My first run of mutation 3 was not caught, and that was the mutation's fault, not the
   tests': it added an early copy of the parameters and left the real ones after the shader,
   so the values were set correctly the second time. The faithful mutation moves the block;
   it fails the named test. My first failure parser also listed one passing census test in
   every run (GUT repeats the failing tests in its Run Summary and prints details under the
   last test name); the table above uses the Run Summary list, and each row's count equals
   GUT's "N failing tests".
3. **Software render** (evidence, not a gate): `docs/briefs/shots/M3-09-fixture.jpg`, the terrain
   fixture wearing the photo fixture, rendered with Compatibility on llvmpipe under Xvfb from a
   scratch probe script that is not committed (the probe moves the photo's rectangle over the
   terrain fixture, since the two fixtures are different worlds). It shows that
   `terrain_photo.gdshader` compiles (no shader ERROR; the only ERROR line is ALSA's audio
   device), that the grey blocks and the single coloured corner block land with the coloured
   block in the north-east, and that outside the photo the neutral colour shows. The real
   village was not rendered: it needs `download terrain` and `terrain` and a 0.2 m photo
   from M3-04, and the plan lets this brief skip it. Does NOT prove the Forward+ look.
4. **What PhotoGrid checks beyond the brief's list** (all inside "key set not exact" and
   "another SHA-256"): the nested key sets of `jpeg`, `source` and `lv95_box`, the digests being
   64 hex digits, `source.dataset` being `swissimage`, and the JPEG's bytes read once and
   hashed from those same bytes. A missing file is refused before any read, so no engine ERROR
   is printed for it. The refusal text for a missing block names `python -m mattini download
   photo` then `python -m mattini photo`.
5. **Not refused, said out loud:** a photo wider or taller than 16384 texels draws black under
   Compatibility with no error (H21). The brief's refusal list has no such rule and the reader's
   rules are not mine to change; the village's 0.2 m photo is 10000 by 15000, so it fits. A
   finer cell than 0.2 m is refused anyway (cells are 0.2, 0.5, 1). Design may want the guard
   if the area grows.
6. **The shader** is `terrain_clay.gdshader` with only the header, the photo's uniforms and the
   closing albedo and roughness replaced; Terrain3D's private uniforms, varyings, `vertex()`
   and the terrain normals are the same text (`test_m3_09_photo_shader`, a census: it proves
   the text, not that anything draws). It keeps a `height_offset_m` uniform, unused, so the
   loader's value is stored as in the clay shader. Roughness 0.95 is a literal here; M3-10
   brings the constants.
7. **The allowlist:** one line appended, `PhotoGrid: user://test_ @
   res://tests/test_photo_grid.gd`. My first rebase conflicted with lane G's
   `BuildingRoofs` line at the end of the file; I kept both, in that order, and re-ran the
   gate (the diff against `origin/main` is that one added line). The head was rebased twice
   more (lane G's DONE line, then lane B's M3-02, which tightened the gate) and re-gated each
   time; the last gate ran under M3-02's rules.
8. **For the next builders of this wave:** `pipeline/tests/test_repo_tracked.py` fails the gate's
   pytest step when a new file the game depends on is not in git's index, so `git add` the new
   files, and the `.uid` files a Godot import writes, before the first gate run (a bare
   `godot --headless --path game --import` writes them without the gate). gdlint's
   `max-returns` is 6 per function (one reader function had to be split).
9. **Does NOT prove:** that it renders or looks right on the owner's GPU, what the photo
   costs there (about 0.8 GB of texture memory expected), or anything about the real village's
   photo: the pipeline step (M3-04) meets this reader at the shared fixture, and M3-14 puts
   both in the main scene.
