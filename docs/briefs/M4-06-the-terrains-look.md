# Brief: M4-06 — The terrain's look: the photo's softened shadows and the water
Status: OPEN

Written in the design realm; executed by one fresh builder session under
`docs/roles/BUILD.md`. Lane F of wave 1 (`docs/briefs/sketches/m4-design.md` §8).

## Goal

The terrain shader lifts the photo where it lay in shadow when it was flown, and draws the water
as m4-design §8 sets it (SPEC §13 row 41, FB-003):

- **The reader.** `CaptureShadowGrid` (`game/scripts/terrain/shadow_grid.gd`) reads the
  manifest's `shadows` block and its 0.5 m mask PNG (brief M4-03's files), checks them as
  `SurfaceGrid` checks the classes, and places the mask's rectangle through `WorldConfig`.
- **The loader.** `TerrainLoader.create` takes the mask as an optional fifth argument and hands
  its texture and rectangle to the photo shader; without one, nothing is lifted.
- **The shader.** The photo's colour × (1 + (shadow_lift − 1)·m), clipped at 1, as the first rule
  on the photo; the water a little darker (× 0.9), less mirror-like (roughness 0.3), its ripples
  at 2 m and 3.4 m drifting apart at 0.8 m/s, its edge eased over 1 m at the bank.
- **The gate.** The render step gains `RENDER lift` (a new script, `render_lift.gd`): where the
  lift lands, by correlation against flipped, transposed, unfiltered and shifted alternatives,
  and its strength. The `classes` check is rewritten for the new water (its albedo, where it
  lies, its eased bank).

The main scene does not read the mask yet: brief M4-10 (wave 2) wires it, with its refusal on
the error panel and its startup line.

## Read first, in order

1. `CLAUDE.md` (Hard Rules 2 and 4, the gate's paragraph); `brain.md` H3, H11, H12, H21, H24–H28.
2. `docs/briefs/sketches/m4-design.md` §0 and §8; `docs/briefs/sketches/M4-soften/README.md`
   (the prototype the owner judged: inset feather, lift in linear light, clipped).
3. `docs/briefs/M4-03-the-capture-shadows-step.md` (Decisions 1, 6, 7: the mask, its files, its
   description) and `tests/shared/shadows_fixture/`, `tests/shared/shadows_vectors.json`
   (design data, never edited).
4. `game/scripts/terrain/surface_grid.gd` (the reader to follow), `terrain_loader.gd`,
   `game/shaders/terrain_photo.gdshader`; `docs/briefs/M3-10-roads-paths-water-rock-on-the-terrain.md`
   and `docs/briefs/M3-R1-fix-3-render-step-in-the-gate.md` (the analogues).
5. `game/tests/render/` (the render step's scripts), `game/tests/complete_world.gd`,
   `tools/gate.sh` (`render_step`), `pipeline/tests/test_gate_render.py`.
6. The pinned files: `docs/briefs/pinning/M4-06/` (below, Scope).

## Decisions already made

1. **`CaptureShadowGrid`** (`class_name CaptureShadowGrid`, `extends RefCounted`).
   - **Constructor:** `static func from_manifest(path: String, world: WorldConfig) ->
     CaptureShadowGrid`, null after its refusals, each one
     `push_error("CaptureShadowGrid: <path>: <problem>")`.
   - **Properties:** `area`, `cell_m` (0.5), `columns`, `rows`, `x0`, `z0`, `width_m`,
     `depth_m`, `dataset`, `editions` (PackedStringArray), `attribution`, `texture`
     (ImageTexture, L8, no mipmaps, image row 0 the north edge); `rect() -> Vector4` (x0, z0,
     width_m, depth_m); `value_at(x: float, z: float) -> int`, the texel's byte (0 or 255) at
     column floor((x − x0)/cell_m), row floor((z − z0)/cell_m), −1 outside the half-open
     rectangle. Keep the sun's two numbers too if useful; nothing reads them in this brief.
   - **The block** is the step's description as M4-03 writes it (brief M4-03 Decision 7); brief
     M4-09 copies it into the manifest under `shadows`. Exactly the keys area, cell_m, columns,
     file, format, lv95_box, pixels_sha256, rows, sha256, source, sun, world_sha256; `source`
     exactly {attribution, collection, dataset, editions, entry_sha256}; `sun` exactly
     {azimuth_grid_deg, elevation_deg, note}.
   - **It refuses**, as `SurfaceGrid` does, every compare typed (`ManifestValue.differs`,
     brain.md H26): a missing or null block (naming `python -m mattini download surface`, then
     `python -m mattini shadows`); another world (`world_sha256`, naming `python -m mattini
     shadows`), a WorldConfig not read from this manifest, other axes than the owner's; a key set
     that is not exact; format not `png-l8`; cell_m not 0.5; columns or rows not whole; a digest
     not 64 hex digits; `source.dataset` not `swisssurface3d`; `editions` not a non-empty list of
     texts; a sun value not a finite number; the box off columns × 0.5 and rows × 0.5 by more than
     1 mm; a file path that is not plain; a missing PNG (checked before any read); another
     SHA-256 (before decoding); a decode that fails or is not L8 of columns × rows; decoded bytes
     whose SHA-256 is not `pixels_sha256`. Each refusal a PNG rebuild fixes names `python -m
     mattini shadows`.
2. **`TerrainLoader.create(grid, parent, photo = null, surfaces = null, shadows:
   CaptureShadowGrid = null)`.**
   - With a photo and a mask: `capture_shadow` = the grid's own `texture`,
     `capture_shadow_rect` = its `rect()`.
   - With a photo and no mask: `capture_shadow` = a 1 × 1 L8 texture of 0 (no lift; every
     sampler the shader declares is set, M3-10's rule), `capture_shadow_rect` (0, 0, 1, 1).
   - Without a photo: the clay shader, no mask, as today. The photo, the classes and their
     rectangles are set as before.
3. **The lift** (m4-design §8, design's decisions where it was open). In the photo shader:
   ```glsl
   group_uniforms capture_shadow;
   uniform sampler2D capture_shadow : hint_default_black, filter_linear, repeat_disable;
   uniform vec4 capture_shadow_rect = vec4(0.0, 0.0, 1.0, 1.0);
   uniform float shadow_lift = 3.0;
   ...
   	vec3 albedo = texture(photo, puv).rgb;
   	vec2 muv = (v_vertex.xz - capture_shadow_rect.xy) / capture_shadow_rect.zw;
   	float m = texture(capture_shadow, muv).r;
   	if (any(lessThan(muv, vec2(0.0))) || any(greaterThan(muv, vec2(1.0)))) {
   		m = 0.0;
   	}
   	albedo = min(albedo * (1.0 + (shadow_lift - 1.0) * m), vec3(1.0));
   	if (any(lessThan(puv, vec2(0.0))) || any(greaterThan(puv, vec2(1.0)))) {
   		albedo = outside_albedo;
   	}
   ```
   - **The mask is data:** no `source_color`; `hint_default_black`, so an unset sampler lifts
     nothing (the default white would lift the whole photo); `filter_linear` between the 0.5 m
     texel centres is the feather (M4-03's inset keeps it inside the shadow); `repeat_disable`
     clamps to the edge texel, so the explicit 0 outside the rectangle.
   - **Linear light:** `photo` is a `source_color` sampler, so under Forward+ `albedo` is
     linear here and the lift multiplies linear colour, as the prototype did. Nothing converts
     it around the lift.
   - **Order:** the lift is the first rule on the photo: before the neutral colour outside the
     photo (which is never lifted) and before rock, road, path and water.
   - **Clipped at 1** per channel, as the prototype the owner judged (M4-soften/README.md: "2 %
     clipped inside the mask (village)").
4. **The water** (m4-design §8; replaces M3-10's `water_scale_m`, `water_drift_a`,
   `water_drift_b`, `water_darken` and roughness 0.05):
   ```glsl
   uniform float water_scale_a_m = 2.0;
   uniform float water_scale_b_m = 3.4;
   uniform vec2 water_drift = vec2(0.48, 0.64); // m/s
   uniform float water_normal_strength = 0.35;
   uniform float water_albedo = 0.9;
   const float WATER_ROUGHNESS = 0.3;
   ...
   	float w_water = water_weight(xz);
   	if (w_water > 0.0) {
   		vec2 ua = (xz - TIME * water_drift) / water_scale_a_m;
   		vec2 ub = (xz + TIME * water_drift) / water_scale_b_m;
   		... (na, nb, ripple, bump as M3-10's, with the two scales)
   		albedo *= mix(1.0, water_albedo, w_water);
   		roughness = mix(roughness, WATER_ROUGHNESS, w_water);
   	}
   ```
   - **The drift:** one vector of 0.8 m/s, (0.48, 0.64) in (x, z): map a's pattern moves along
     it, map b's against it (design's choice: not along a world axis, and no single direction
     for the water as a whole).
   - **The ease at the bank, `water_weight(xz)`:** the share of water among the 5 × 5 class
     texels (1 m at 0.2 m) around the point, each read with `texelFetch`; the boxes of the four
     nearest texel centres blended bilinearly, so 6 × 6 texels with the outer row and column
     weighted by the fraction (texel coordinates t = (xz − rect.xy)/rect.zw · size − 0.5, as
     `class_weights`); then `smoothstep(0.0, 1.0, share / 25.0)`. On a straight bank the weight is
     0.5 on the class edge, 0 from 0.5 m outside it, 1 from 0.5 m inside; a channel narrower than
     1 m never reaches full weight. The pinned `test_m4_06_terrain_look.gd` holds the function
     line by line. Rock, road and path keep `class_weights` (M3-10).
   - Water draws at every distance, as today.
5. **The render check `RENDER lift`** (`game/tests/render/render_lift.gd`, pinned): the complete
   world with a flat terrain built by `TerrainLoader` with the world's photo, classes and mask (the
   main scene does not read the mask before M4-10), one light from straight above with no
   highlight, no ambient light, a linear tone map; the photo replaced by one grey of 0.2 in both
   views so that no texel clips under the lift. The ratio of the render with the mask to the
   render with one texel of 0, on class 0 inside the photo, against the data's mask (bilinear
   between texel centres, 0 outside): correlation at least 0.95, above the mask mirrored
   north-south, mirrored east-west, transposed and read at the nearest texel; the best of the
   0.05 m shifts (±0.4 m, x and z) within one step of none and every shift of 0.1 m or more below
   none; the median ratio 3.0 ± 5 % where the 3 × 3 texels around are all 255, 1 ± 0.05 where all
   0.
6. **The `classes` check, rewritten** (`render_photo.gd`, pinned): the water's ripples (strength
   0), the sun's highlight, the sky's reflection and ambient light off, the tone map linear (the
   photo check reads this view too); the second view removes only the water class. On samples
   0.6 m inside the terrain: the full-water ratio (the data's 1 m box all water) 0.90 ± 0.03; the
   rendered weight above 0.5 agrees with `class_at`'s water on 98 % of the samples, better than
   mirrored, best shift within 0.05 m; on the bank the rendered weight correlates at least 0.95
   with the data's eased weight and better than with every twin (not eased, the box without the
   smoothstep, a 0.6 m box, a 1.4 m box).
7. **The complete test world** (`game/tests/complete_world.gd`, pinned) gains the shared shadows
   fixture's description and PNG as its `shadows` block, moved to `SHADOWS_BOX` (E 2'601'019 –
   2'601'051, N 1'199'956.5 – 1'200'004.5: local (1019, −4.5, 32, 48)): the photo then lies over
   the mask's rows 32 to 47, the block's shadow under its middle, its north edge 0.5 m inside the
   photo. The change is exactly: the doc comment's new item, `SHADOWS_FIXTURE`, `SHADOWS_BOX`,
   `"shadows"` added to `write()`'s folder list, one line in `write()`
   (`manifest["shadows"] = _moved_description(...)`, after the surfaces' line) and the new
   function `_moved_description`. No other line changes.
8. **The gate** (the one `tools/gate.sh` edit of the arc's wave 1): `render_step` runs
   `render_script res://tests/render/render_lift.gd lift || return 1` between the photo's and the
   trees' scripts; `RENDER_SKIP_LINE` reads "… where the photo, the classes, the lift and the
   crowns' colour land is not checked"; the header and the `render_script` comment say three
   scripts and name the lift. The pinned `pipeline/tests/test_gate_render.py` and
   `fake_tools.py` hold exactly that. `tools/gate_allowlist.txt` gains one line at its end:
   `CaptureShadowGrid: user://test_ @ res://tests/test_m4_06_capture_shadow_grid.gd # its refusal tests write broken manifests under user://test_m4_06_capture_shadow_grid on purpose (brief M4-06)`.
9. **Live tests that change** (pinned here, M3's pinned copies stay as the record):
   `test_m3_09_photo_shader.gd` (its placement census gains `water_weight`'s texel line, and its
   puv check names `PLACEMENT_LINES[6]`); `test_terrain_loader_surfaces.gd` (the mask's texture is
   data, not a CC0 file: skipped in the file census).
10. **Design's rehearsal** (a throwaway implementation in a scratch clone, never committed;
    2026-10-17): see the gate list below for the mutations and their killing tests. Numbers at
    that head: `RENDER lift` correlation 1.0000 (north-south 0.19, east-west 0.0, transposed
    0.0, nearest 0.98), lift 3.06 over 6'244 samples, 1.00 over 15'717, 29'688 samples, 9 to 12 s;
    `RENDER classes` agreement 69'990 of 70'180 (mirrored 58'953), full water 0.896 over 3'639,
    bank 0.985 against 0.948 (not eased), 0.979 (no smoothstep), 0.975 (0.6 m), 0.979 (1.4 m) over
    5'993 (five runs, the same numbers: the ripples are off, so nothing moves with `TIME`);
    `RENDER photo` 0.9754 (M3: 0.9761). The standard gate with the pinned copies and the
    throwaway: exit 0, pytest 2'231 passed, GUT 49 scripts, 284 tests, 10'060 asserts, the render
    step's four PASS lines. Against a stub that parses (the API, nothing implemented; M3's loader
    taking a fifth argument; M3's shader): the reader's 16 tests and the look's 7 all fail, no
    script skipped (H3); `RENDER lift` and `RENDER classes` fail. Each mutation below failed a
    named pinned test or check, recorded in the gate list.

## Scope — files you may touch

- `game/scripts/terrain/shadow_grid.gd` and its `.uid` (new);
  `game/scripts/terrain/terrain_loader.gd`; `game/shaders/terrain_photo.gdshader` (its header
  comment too: say what the lift and the water do);
- the pinned copies (`cp -r docs/briefs/pinning/M4-06/. .`), byte-identical for the whole brief:
  `game/tests/test_m4_06_capture_shadow_grid.gd`, `game/tests/test_m4_06_terrain_look.gd`,
  `game/tests/render/render_lift.gd` (new, with the `.uid` files Godot writes);
  `game/tests/render/render_photo.gd`, `game/tests/complete_world.gd`,
  `game/tests/test_m3_09_photo_shader.gd`, `game/tests/test_terrain_loader_surfaces.gd`,
  `pipeline/tests/fake_tools.py`, `pipeline/tests/test_gate_render.py` (changed);
- `tools/gate.sh`: exactly Decision 8; `tools/gate_allowlist.txt`: the one appended line;
- your own new `game/tests/test_*.gd`; `docs/briefs/shots/M4-06-*.jpg`.

Wave 1's shared files: `complete_world.gd`, `render_photo.gd`, `fake_tools.py`,
`test_gate_render.py`, `tools/gate.sh` and the allowlist. Design checked them against the other wave-1 briefs (2026-10-17): M4-08, after this brief
in lane F, replaces `fake_tools.py` with a copy that keeps this brief's lines, and M4-07 appends
its own allowlist line; if another lane's landing changed one, rebase,
keep both changes and re-run the gate (the allowlist: append, keep every line).

## Depends on

None: the shadows fixture is on `main` (brief M4-03's plan commit). M4-08 follows in the same
lane (F): it replaces `pipeline/tests/fake_tools.py` with a copy that keeps this brief's lines. M4-09 (wave 2) writes the
manifest's `shadows` block in this brief's form; M4-10 (wave 2) wires the mask in the main scene.

## Done when (gates)

- [ ] The pinned copies are in place and stay byte-identical (`cmp` each against
      `docs/briefs/pinning/M4-06/`); they pass.
      - does NOT prove: that they are the right tests.
- [ ] Mutations, each failing a named pinned test or render check, recorded with the
      owner-visible harm (design's rehearsal killed each as shown; G = `test_m4_06_capture_shadow_grid`,
      L = `test_m4_06_terrain_look`):

      | Mutation | Killed by | Harm |
      |---|---|---|
      | texture made after a row flip | G `test_every_texel_reads_back_where_lv95_puts_it` | the lift mirrored north-south |
      | `value_at` rows from the south | G `…every_texel…`, `…every_named_cell…`, `…half_open…` | lookups mirrored |
      | the rectangle half a texel east | G `…every_named_cell…`, `…fixture_is_read…`, `…complete_world…`, `…half_open…` (`RENDER lift` passes: it reads the reader's rectangle too) | the lift 0.25 m off |
      | the rectangle from the south-west corner | G (4 tests), `RENDER lift` | the lift 48 m off |
      | no `world_sha256` compare | G `test_shadows_built_for_another_world_are_refused` | another world's mask accepted |
      | untyped `world_sha256` compare (H26) | G `test_values_of_another_type_are_refused_not_a_runtime_error` | a numeric digest lets the block through |
      | no `pixels_sha256` check | G `test_a_png_of_another_mask_is_refused` | a wrong mask accepted |
      | no axes check | G `test_a_rotated_world_is_refused` | a rotated world's mask misplaced |
      | the photo's rectangle for the mask's (loader) | L `test_the_mask_and_its_rectangle_reach_the_shader` | the lift off its place |
      | no mask: sampler left unset (loader) | L `test_without_a_mask_nothing_is_lifted_and_every_sampler_is_set`, `test_terrain_loader_surfaces::test_every_texture_the_photo_shader_samples_is_set` | a default texture lifts or not, silently |
      | `source_color` on the mask | L `test_the_lift_is_the_first_rule_on_the_photo`, `test_the_shader_declares_the_mask_and_the_lift` (render: no difference on a 0/255 mask) | the feather bent by a colour curve |
      | mask rows flipped / columns flipped / transposed | L `…first_rule…`, `RENDER lift` (correlation 0.19 / 0.00 / −0.01) | the lift mirrored or turned |
      | mask half a texel off | L `…first_rule…`, `RENDER lift` (best fit −0.25 m) | the lift 0.25 m off |
      | mask 0.1 m east / south | L `…first_rule…`, `RENDER lift` (best fit +0.10 m) | the lift 0.1 m off |
      | the lift after the water rule | L `…first_rule…` (render: the rules multiply, no difference) | order of rules |
      | the lift on sRGB values | L `…first_rule…`, `RENDER lift` (lift 5.10) | shadows lifted far too much |
      | the photo sampler without `source_color` | L `…first_rule…` (render: no difference under Compatibility, H21) | the lift on sRGB values in Forward+ |
      | no 0 outside the mask's rectangle | L `…first_rule…` (render: the edge texels under the photo are 0) | the edge texel smeared beyond the mask |
      | mask filtered nearest | L (2 tests), `RENDER lift` (nearest reads better) | 0.5 m stair steps, no feather |
      | the lift unclipped | L `…first_rule…` (render: grey 0.2 never clips) | albedo above 1 |
      | lift 2 instead of 3 | L (2 tests), `RENDER lift` (lift 2.04) | shadows stay darker |
      | no `hint_default_black` | L (2 tests) (render: the mask is always set) | an unset mask lifts everything |
      | M3's water albedo 0.6 | L `test_the_water_is_the_pinned_one`, `RENDER classes` (0.578) | the old dark water |
      | M3's roughness 0.05; one drift direction; strength 0.2 | L `…water_is_the_pinned_one` (render: off or cancelled) | the old mirror; a uniform drift; weaker ripples |
      | no easing at the bank | L `…water…`, `RENDER classes` (the 0.2 m blend reads better, 0.991) | a hard bank |
      | the box without the smoothstep | L `…water…`, `RENDER classes` (best z fit +0.25 m; the twins read better) | another bank |
      | the box half a texel off | L `…water…`, `test_m3_09_photo_shader`, `RENDER classes` (best fit −0.10 m x, −0.30 m z) | the water 0.1 m off |
      | a 0.6 m box | L `…water…`, `RENDER classes` (the 0.6 m twin 0.989) | a narrower bank |
      | `gate.sh` without `render_lift.gd` | `test_gate_render.py` (5 tests) | the lift unchecked |
      | the complete world without the mask | G `test_the_complete_world_carries_the_mask_at_its_own_box`, `RENDER lift` (refused) | no render of the lift |

      - does NOT prove: the look; the lift's linear arithmetic under Forward+ (Compatibility
        shows no colour conversion, H21: only the census pins it); the water's roughness,
        ripples and drift on screen (census only); that M4-09's block has this form.
- [ ] Software Forward+ screenshots (lavapipe, H12) under `docs/briefs/shots/M4-06-*.jpg`, named
      in Findings: the lift on the complete world (the mask wired by a throwaway scene in scratch,
      never committed: the main scene does not read it before M4-10), with and without the mask
      from the same camera; the water at the bank and looking towards the sun (design's two, from a
      synthetic scene: `docs/briefs/sketches/M4-soften/water-*.jpg`). The real village if you can
      build it in scratch (`download surface`, M4-03's `build_shadows` in a throwaway): a crop of
      M4-soften's A or B with and without the mask.
      - does NOT prove: the owner's GPU or look (a software render is not the owner's PC).
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`, with the render step (three
      scripts; record its wall time).
      - does NOT prove: that it renders or looks right. The render step proves where the lift and
        the water land and their strength on a flat 16 m test world under Compatibility, not the
        colour encoding (H21), not Forward+, not distance, not the real village's mask.

## Forbidden

- Changing the lift, its order, its clip, the water's values or formula, a pinned file, a
  fixture or design data; another gate.sh edit than Decision 8.
- Touching `game/scripts/main.gd`, `main.tscn` or the credits (M4-10); the pipeline (M4-03,
  M4-09).
- A new dependency; a version bump.

## Findings (executor writes)
