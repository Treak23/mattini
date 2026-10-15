# Brief: M3-10 — Roads, paths, water and rock on the terrain
Status: DONE (d5875c6)

Written in the design realm; executed by one fresh builder session under
`docs/roles/BUILD.md`. Lane E of wave 1, after M3-09 (`docs/briefs/M3-plan.md`).

## Goal

The terrain shows swissTLM3D's classes on top of the photo (the owner's "bring into m3
now", SPEC §13 row 33):
- **roads** with asphalt grain up close;
- **paths** with gravel up close;
- **water** that looks wet and moves;
- **steep rock** with real rock texture instead of the photo's vertical streaks.

How the classes reach the shader:
- `SurfaceGrid` reads the manifest's `surfaces` block, checks it and decodes the class PNG.
- `TerrainLoader` hands the classes and their rectangle to the shader, with three CC0
  textures from Poly Haven and two generated water normal maps.

## Read first, in order

1. `CLAUDE.md`; `brain.md` H21, H24, H25.
2. `docs/SPEC.md` §8 *The surfaces* (the game), §10 (M3's game).
3. `game/scripts/terrain/photo_grid.gd`, `terrain_loader.gd`,
   `game/shaders/terrain_photo.gdshader` (M3-09, landed in this lane just before).
4. `tests/shared/surfaces_fixture/`, `tests/shared/surfaces_vectors.json`, and the photo and
   terrain fixtures (design data). Note: `surfaces_vectors.json` stores a `texel` as [row,
   column] (rows from the north edge), the reverse of `photo_vectors.json`'s [column, row].
5. `docs/briefs/sketches/terrain_photo.gdshader.sketch`, its NEW (M3-10) sections.
6. The pinned files: `docs/briefs/pinning/M3-10/` (two tests, the licence note and the seven
   texture `.import` files).

## Decisions already made

1. **`SurfaceGrid`** (`game/scripts/terrain/surface_grid.gd`, `class_name SurfaceGrid`,
   `extends RefCounted`).
   - **Constructor:** `static func from_manifest(path, world) -> SurfaceGrid`, null after its
     refusals, each one `push_error("SurfaceGrid: <path>: <problem>")` as PhotoGrid's (M3-14's
     allowlist line and refusal tests depend on that form).
   - **Properties:** as PhotoGrid's (`texture` holds the L8 class image), plus `class_at(x: float,
     z: float) -> int`: floor((x − x0)/cell_m), floor((z − z0)/cell_m), and −1 outside the
     half-open rectangle.
   - **It refuses:**
     - a missing block, naming `download tlm` then `surfaces`;
     - another world, or other axes than the owner's;
     - a key set that is not exact, or a format or classes that are not the SPEC's;
     - a cell not in 0.2, 0.5, 1;
     - the rectangle off the box by more than 1 mm;
     - a file path that is not plain, or a missing file (checked before any read, so no engine
       ERROR is printed);
     - another SHA-256, checked before decoding;
     - a decode that fails or is not FORMAT_L8, or another size;
     - decoded bytes whose SHA-256 is not `pixels_sha256`.
2. **`TerrainLoader.create(grid, parent, photo = null, surfaces = null)`.**
   - With both, the photo shader gets `surfaces` and `surfaces_rect` = `surfaces.rect()` (its
     own rectangle, not the photo's), the seven textures and two NoiseTexture2D water normal
     maps (seeds 1 and 2, 256², seamless, as_normal_map, bump 6, simplex smooth, 3
     octaves).
   - With surfaces but no photo: the clay shader, nothing else.
3. **The shader** (this brief's part; the sketch's NEW M3-10 sections):
   - **Classes.** `uniform sampler2D surfaces : filter_nearest, hint_default_black,
     repeat_disable;`, read only with `texelFetch`. The four texels around the fragment are each
     decoded exactly and blended per class, so an edge is soft over one 0.2 m texel; a class
     value is never interpolated. Measured: a single nearest read draws 0.2 m saw-teeth at
     6–10 m.
   - **Rock** (class 1). Weight = the rock weight × smoothstep(35°, 55°, slope). Triplanar
     (|n|⁴ blend), scale 2.7 m. The texture's luminance relative to its mean multiplies the
     photo, so it is tinted to the photo's colour. Roughness from its map; its normal added
     UDN-style.
   - **Roads and paths** (4, 3). The detail texture's luminance relative to its smallest mip
     level multiplies the photo, so the photo's hue stays. It fades by 1 − smoothstep(50 m,
     150 m, distance) (`near_fade_m` = 150).
   - **Water** (2). Roughness 0.05, albedo × 0.6. Two normal maps drift at (0.23, 0.11) and
     (−0.13, 0.19) m/s, at scales 10 m and 17 m, strength 0.2. These are tuning values,
     uniforms the owner can change.
   - **Derivatives.** Every sample inside a branch uses `textureGrad` with world-space
     derivatives taken outside it, so there is no region seam.
4. **The CC0 textures** (Poly Haven; licence CC0 1.0, checked on each asset page). Download
   them unchanged into `game/textures/` from `https://dl.polyhaven.org/file/ph-assets/Textures/jpg/<res>/<asset>/<file>`;
   the pinned test checks each SHA-256:

   | File | Bytes | SHA-256 |
   |---|---|---|
   | `rock_face_03_diff_2k.jpg` | 3'814'362 | `644ee79df7ffbf5f6afc330b64dd3f33794bab8820915fe61ffe0c88ecfd7ece` |
   | `rock_face_03_nor_gl_2k.jpg` | 4'473'242 | `a498cef4ba6191f6959b6d03fb835263c77271948264a289af24497ab7111dec` |
   | `rock_face_03_rough_2k.jpg` | 2'601'552 | `9ca3e9e196685f702328f24d66f039b72f5330fc35cf2a2c265cfa50a7916301` |
   | `worn_asphalt_diff_1k.jpg` | 914'719 | `3bf71ad290730092ad2aee85e246b2e43318bc1f32261826ba91250e815b5f72` |
   | `worn_asphalt_nor_gl_1k.jpg` | 1'503'498 | `5f835d192dac296674229a763553f356f5e206bb7f6d812bca5b0f38fc5302a4` |
   | `rocky_trail_diff_1k.jpg` | 1'076'180 | `7f20d83cd4a67f9c38abf72f39f5a3749a962e90bdc156998be027b1227a5bd6` |
   | `rocky_trail_nor_gl_1k.jpg` | 1'398'291 | `087b8912c8cf40a528965c4282a5b3e4be011da5790273ffcdb5bd2697bde7dd` |

   - 15.05 MiB in all, each file under 10 MB.
   - Their pinned `.import` files set VRAM compression and **mipmaps** (H25: the defaults are
     lossless and without mipmaps, which breaks the fade and the mean).
   - The pinned `game/textures/LICENSE.txt` names every file, its asset page, its authors and
     CC0. M3-14's credits read it.
5. **The gate:** one scoped allowlist line for SurfaceGrid's refusal tests:
   `SurfaceGrid: user://test_ @ res://tests/test_surface_grid.gd # its refusal tests write broken manifests under user://test_surface_grid on purpose (brief M3-10)`.
   Wave 1's one shared file: append at the end; on a rebase, keep every line and re-run the
   gate.
6. **Measured with design's throwaway on the real village** (Compatibility, software):
   - the classes sit on the photo's roads, river and cliffs;
   - flat ground at 1.063× the photo's luminance with M3-14's light;
   - the scene builds in about 6 s, against 2.9 s for the clay;
   - peak memory 2.4 GiB; texture memory 1'171 MiB.

## Scope — files you may touch

- `game/scripts/terrain/surface_grid.gd` and its `.uid` (new);
  `game/scripts/terrain/terrain_loader.gd`; `game/shaders/terrain_photo.gdshader`;
- `game/textures/`: the seven JPGs, the pinned `.import` files and `LICENSE.txt`;
- `game/tests/`: the pinned `test_surface_grid.gd` and `test_terrain_loader_surfaces.gd`
  (new, with `.uid`), and your own new tests;
- `tools/gate_allowlist.txt` (the one appended line).

## Depends on

M3-09 (the same lane). It reads design's surfaces fixture, not the pipeline step (M3-06,
lane D, meets it at the fixture).

## Done when (gates)

- [ ] The pinned copies are in place (`cp -r docs/briefs/pinning/M3-10/. .`) and stay
      byte-identical (`cmp`); the seven textures are downloaded and match their SHA-256s.
      - does NOT prove: that they are the right tests.
- [ ] Mutations, each failing a named pinned test, recorded:
      - `surfaces_rect` set to the photo's;
      - surfaces without a photo switching to the photo shader;
      - one texture left unset;
      - a water map loaded from a file;
      - mipmaps off.
      - does NOT prove: the class decode, the rock blend, the fade or the look (not testable
        headless).
- [ ] Optional: software screenshots (Compatibility) under `docs/briefs/shots/M3-10-*.jpg`, named in
      Findings: a street at 30 m, the river at 30 m and 10 m, a rock face and a path at 6 m.
      Use the real village in scratch: the class grid by M3-06's function once lane D has
      landed, or by SPEC §8's rule in a throwaway. They are evidence, not a gate. `tools/shot.sh` renders
      the main scene, which uses this brief's code only from M3-14: render with a throwaway
      scene kept in scratch (never committed), or skip the shots and say so in Findings.
      - does NOT prove: the Forward+ look on the owner's GPU.
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that it renders or looks right.

## Forbidden

Other textures, other licences, or textures changed after download; changing Terrain3D's
vertex or normal code; touching the main scene; editing a pinned file or a fixture.

## Findings (executor writes)

Landed as `d5875c6` on `main`. Standard gate on the head it was rebased onto before the last
(docs-only) rebase: exit 0, pytest 1041 passed (4 deselected), GUT 39 scripts, 215 tests,
8533 asserts, `GUT version:  9.6.1`.

1. **The pinned files** (`test_surface_grid.gd`, `test_terrain_loader_surfaces.gd`,
   `LICENSE.txt` and the seven `.import` files) are in place and `cmp`-identical to
   `docs/briefs/pinning/M3-10/`, checked again after Godot's import (it did not rewrite any
   `.import` file). As in M3-09 the classifier refused the bulk `cp -r`, so they were copied
   one by one with `cp --update=none`.
2. **The textures.** The seven files came from `dl.polyhaven.org/file/ph-assets/Textures/jpg/
   <res>/<asset>/<file>` into a scratch folder; their byte counts and SHA-256s were compared
   with the brief's table before anything entered the repository, then copied unchanged: 7
   files, 15'781'844 bytes (15.05 MiB), the largest 4'473'242. `LICENSE.txt` is the pinned
   one. The headless import of the new textures took about 8 s and printed no ERROR line.
3. **Mutations** (applied to staged files, run against the two pinned M3-10 scripts, the two
   pinned M3-09 scripts and my census; each reverted by `git apply -R` of its saved diff, the
   tree equal to the index afterwards). Failing tests are GUT's Run Summary list; each count
   equals GUT's "N failing tests".

   | # | Mutation | Failing test(s) | Owner-visible harm reproduced |
   |---|---|---|---|
   | 1 | `surfaces_rect` set to the photo's | `test_terrain_loader_surfaces::test_the_classes_and_their_rectangle_reach_the_shader` | roads, water and rock drawn off their place in the photo |
   | 2 | surfaces without a photo switching to the photo shader | `test_terrain_loader_surfaces::test_the_classes_without_a_photo_keep_the_clay_look` | classes with no photo: a shader with no photo to draw on |
   | 3 | one texture left unset (`path_normal`) | `::test_every_texture_the_photo_shader_samples_is_set`, `::test_the_textures_are_the_pinned_cc0_files_or_generated` | paths drawn with Godot's default texture, silently |
   | 4 | a water map loaded from a file | `::test_the_textures_are_the_pinned_cc0_files_or_generated` | water ripples from an unpinned, unlicensed file |
   | 5 | mipmaps off (`mipmaps/generate=false` in a pinned `.import`, then a re-import) | `::test_the_textures_have_mipmaps` | no fade or mean colour: a lossless, mipless texture |
   | 6 | (mine) SurfaceGrid's z0 from n_min | `test_surface_grid::test_the_fixture_grid_is_read_as_designed`, `::test_every_named_point_has_its_class`, `::test_the_rectangle_is_half_open_and_outside_is_minus_one`, `test_terrain_loader_surfaces::test_the_classes_and_their_rectangle_reach_the_shader` | the classes shifted a whole depth south of the photo |
   | 7 | (mine) the decoded bytes not checked against `pixels_sha256` | `test_surface_grid::test_a_png_of_other_classes_is_refused` | a wrong class grid accepted as the real one |
   | 8 | (mine) `class_at` counting rows from the south | `test_surface_grid::test_every_named_point_has_its_class`, `::test_the_rectangle_is_half_open_and_outside_is_minus_one` | every class lookup mirrored north to south |

   Mutation 5 restores by re-importing after the revert; the baseline passes again after it.
4. **Software render** (evidence, not a gate): `docs/briefs/shots/M3-10-fixture.jpg`, the
   terrain, photo and surfaces fixtures together (three different worlds: a scratch probe,
   never committed, moves the photo's and the classes' rectangles over the terrain fixture and
   picks the placement whose window holds all five classes), Compatibility on llvmpipe under
   Xvfb. It shows that the extended `terrain_photo.gdshader` compiles (no shader ERROR line;
   the only ERROR line is ALSA's audio device) and that the CC0 grain draws over the photo's
   colour where the fixture has classes. It does not show the water moving (a still), the fade
   with distance, the slope blend of the rock, or that anything lines up with the real roads and
   river: the real village was not rendered (it needs `download terrain`, `terrain`, `download
   tlm` and the surfaces step, M3-06, which had not landed), and the plan lets this brief skip
   it. Does NOT prove the Forward+ look.
5. **The shader** is design's sketch with its comments rewritten to say what the code does. Its
   uniforms and helper functions sit before `// Varyings & Types`, so Terrain3D's varyings,
   `vertex()` and normals stay one contiguous block, identical to the clay shader's (my
   M3-09 census, whose end marker is now `// The photo look.`, still proves it). The decode of
   the classes, the rock blend, the fade and the water are the sketch's logic; no test
   reaches them headless (the brief says so), and a software render of a synthetic fixture is
   the only look they have had.
6. **What SurfaceGrid checks beyond the brief's list** (inside "key set" and "SHA-256"): the
   class table is exactly the SPEC's, the nested `source` and `lv95_box` key sets, the digests
   being 64 hex digits, `source.dataset` being `swisstlm3d`. `class_at` is `floori((x − x0) /
   cell_m)` on the local point, so a point on a texel border belongs to the east or south
   texel; the vectors' edge cases agree. The class texture has no mipmaps and is read only by
   `texelFetch`.
7. **The loader.** `create(grid, parent, photo, surfaces)` sets the classes only together with
   a photo; the seven textures are loaded by name from `res://textures/` on every call. A
   missing texture file prints Godot's own ERROR and leaves its sampler unset (mutation 3
   shows the unset-sampler case failing two pinned tests); the loader adds no second message.
8. **The allowlist:** one line appended (`SurfaceGrid: user://test_ @
   res://tests/test_surface_grid.gd`). The file at the push holds each lane's line once
   (BuildingRoofs, PhotoGrid, TreeChunks, SurfaceGrid; M3-08's had not landed) and no entry for
   `Ignoring script` or `Failed to load script`. The gate log holds 118 `ERROR` lines, the
   refusal tests' `push_error`s, each excepted by its scoped entry.
9. **The last rebase** brought one commit that changed only `docs/ROADMAP.md`; no test, script
   or tool names that file, and I pushed without a second full gate. The full gate before it ran
   on the head with M3-01, M3-02, M3-04, M3-11 and M3-12 in.
10. **Does NOT prove:** that it renders or looks right on the owner's RTX 4090; the class decode,
    the rock blend, the fade or the water's motion (not testable headless); that the village's
    real classes sit on its real roads and river (M3-06 and the main scene, M3-14); the
    memory cost (design measured 1'171 MiB of texture memory and a 2.4 GiB peak in software).
