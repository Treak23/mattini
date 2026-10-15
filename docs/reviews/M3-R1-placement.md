# Review M3 R1 — lens `placement`, placement (Tier 1: config/world.json and the coordinate transforms, pipeline and game)

- **Range:** `git diff 9a9612e..410dbba -- . ':!game/addons' ':!pipeline/uv.lock'`; head reviewed `410dbba` (212 files, +28'256 −820).
- **Date:** 2026-10-15.
- **How:** one review session (the lens `placement` of round R1), its own fresh `git clone` per role under its scratchpad, each with its own `XDG_DATA_HOME`: one clean head with the real village built from the pinned inputs (`download terrain|buildings|photo|surface|tlm`, then the seven steps from the command line, the gate on it), one for read-only probes (the render checks of two mutations also ran there, undone the same way), three for mutations (each mutation a saved diff, undone with `git apply -R`, `git status` clean after every one; the driver asserts it), one for the terrain at 1 m and 2 m, one for a scratch world (origin at the box's south-east corner, height offset 1000 m, so the whole grid lies north-west of its origin). Scratch scripts are named in the Appendix; the clones are removed.
- **Standard gate at the head:** exit 0 in 222 s (`tools/gate.sh > log`): `uv lock --check`, pytest `2169 passed, 5 deselected` in 140.78 s, ruff check and format, `manifest`, Godot import and parse, GUT `Scripts 44 / Tests 236 / Passing 236 / Asserts 8745`, `GUT version:  9.6.1`, `---- All tests passed! ----`, gdlint, gdformat; last line `== gate: all steps passed`.
- **The real village:** the manifest is `3ca0445c9109eec4696d654d1c7536f50220f4db04503fab836412f5b0c01065`, 324'359 bytes, design's (steps from the command line, each exit 0: terrain 7 s, buildings 9 s, photo 62 s, roofs 29 s, surfaces 24 s, trees 30 s, manifest 1 s; the first `download photo` here ended clean, no SHA-256 mismatch).
- **Result:** no P0, no P1. Three P2 (P-01 to P-03: a config change SPEC calls "no code change" puts thousands of trees off the ground with nothing refusing; no gate sees where the Trees node puts the trees; no gate runs the shaders that place the photo, the classes and the crowns' colour, and six placements of them leave the whole gate green). One P3 (P-04). The placement of the data itself is right: the photo, the surface classes, the trees, the roof colours and the buildings land where `config/world.json` and the data say, in the owner's world and in a scratch world with another origin, a height offset and the grid north-west of its origin (see "Checked and clean").

## Findings

### M3-R1-P-01 · P2 · The trees' base heights are taken from a 0.5 m terrain grid whatever config/terrain.json's spacing: at the 1 m or 2 m that SPEC calls a config change, nothing refuses and thousands of trees float or sink

- **Where:** pipeline/mattini/trees.py:485 (`terrain = resample(dtm, box, SOURCE_M, world.height_offset)`), trees.py:32 and docs/SPEC.md:706 ("whatever the terrain config's spacing"), trees.py:821-831 (`_area` reads only the area's name from the terrain config), pipeline/mattini/manifest.py (accepted the 1 m and 2 m terrain with the unchanged trees block), game/scripts/trees/tree_chunks.gd (`y` is read as written, never against the terrain); docs/SPEC.md:249 and :334 ("1 or 2 m is a config change and a pipeline re-run, no code change"; "the owner's switch to 1 or 2 m (§7) stays a config change").
- **Claim:** A tree's y is the mean of the four vertices of the 0.5 m grid around its centre, which is Terrain3D's height at the tree only when the game's terrain is that 0.5 m grid. `config/terrain.json` allows 0.5, 1 and 2 m and holds design's expected heights for all three; `terrain`, `manifest` and the game accept 1 m and 2 m with the same trees block. The module says "whatever the terrain config's spacing" as a choice; no text says the trees then stand off the ground, no check refuses it, and the trees' `computed_for` does not bind the spacing (lesson 41).
- **Proof:** In a clone with the real village built (probe_trees.gd is in the Appendix: it instantiates main.tscn on the manifest and compares every instance origin in the Trees MultiMesh buffers with `Terrain3D.data.get_height(x, 0, z)`).
  - As shipped (0.5 m): `godot --headless --path game -s probe_trees.gd` prints `trees total=34412 nan_ground=0 off>1cm=0 off>5cm=0 worst=0.000244 … mean_abs=0.000035`.
  - At 1 m: `sed -i 's/"spacing_m": 0.5/"spacing_m": 1.0/' config/terrain.json`, then `python -m mattini terrain --raw <raw>` (exit 0: "the heights have the SHA-256 config/terrain.json expects, 71bd4f17…") and `python -m mattini manifest` (exit 0), then the probe: `trees total=34412 nan_ground=0 off>1cm=23083 off>5cm=3542 worst=1.052246 at (1828.25, 2173.189, 962.25) mean_abs=0.024562`; buckets ≤1 mm / ≤1 cm / ≤5 cm / ≤20 cm / ≤1 m / >1 m: 1338 / 9991 / 19541 / 3368 / 173 / 1. No ERROR line, no error panel.
  - At 2 m (same two commands, `2.0`, 1001 × 1501 vertices): `off>1cm=31005 off>5cm=18932 worst=4.394897 at (448.75, 1847.513, -953.25) mean_abs=0.090587`; buckets 375 / 3032 / 12073 / 15974 / 2804 / 154.
- **Harm:** The owner does what SPEC §7 offers to soften the terrain (1 m or 2 m): with 2 m, 18'932 of the 34'412 trees stand more than 5 cm off the ground, 154 more than 1 m, the worst 4.4 m, floating or sunk on slopes; every gate, the pipeline's expected-value checks and the manifest stay green, and the game shows no panel.
- **Fix:** Design chooses one of two, both small. (a) The trees step reads `spacing_m` from the terrain config and takes y by bilinear interpolation, at the tree's centre, of the grid at that spacing (what Terrain3D draws), with the spacing in the trees' `computed_for` and design's expected chunks per spacing as the terrain's are. (b) `build_trees` and `built_trees_block` refuse a terrain config whose spacing is not 0.5, naming config/terrain.json, and SPEC §7 and §8 say that the trees tie the terrain to 0.5 m. Either way add a pytest that runs the step against a terrain config at 1 m, and a game test of a tree standing on a 1 m fixture terrain (see P-02).

### M3-R1-P-02 · P2 · Nothing gates where the Trees node puts the trees in the scene or that they stand on Terrain3D's ground, and main.gd says test_scene_placement.gd does

- **Where:** game/scripts/main.gd:24-26 (the claim), :241-246 (`_show_trees`), game/tests/test_scene_placement.gd (its header and its five tests name and check "Buildings" only), game/tests/complete_world.gd:16-18 (its trees "stand beside and below this terrain, not on it"), pipeline/tests/test_docstring_claims.py (checks only that a named test file exists).
- **Claim:** M2 R1 P-01 put the Buildings node and its meshes under a global_transform test and a "stands on its terrain" test (M2-08, M3-02). M3-14 extended main.gd's header to "the Buildings and Trees nodes and their meshes sit at the scene's origin, unturned and unscaled (test_scene_placement.gd)", and the tree shader depends on it (it reads each instance's world-space origin against a rectangle in local coordinates). No test reads the Trees node's transform, and none compares a tree in the scene with Terrain3D's ground: the complete world's trees are the trees fixture's, written for another world. The seam the lens names, "each tree's base height against Terrain3D's get_height and its position against to_local", has a per-reader test (`TreeChunks`: `to_local`, `test_tree_chunks.gd:81`) and no test at the scene.
- **Proof:** Mutation `GM-main-trees-offset` (`muts/GM-main-trees-offset.diff`): in `_show_trees`, `var trees_node := TreeLoader.create(chunks, self, texture, rect)`, `trees_node.position = Vector3(1000.0, 0.0, 0.0)`, `move_child(trees_node, _ui.get_index())`. Full pytest `2169 passed, 5 deselected`, full GUT `Tests 236 / Passing 236`, `---- All tests passed! ----`: the named tests (`test_scene_placement.gd`, `test_tree_chunks.gd`, `test_tree_loader.gd`, `test_tree_loader_photo.gd`, `test_main_scene_data.gd`) all pass. The whole `tools/gate.sh` with the mutation applied (own clone, own `XDG_DATA_HOME`): `== gate: all steps passed`, `gate exit 0 after 219s` (pytest `2169 passed, 5 deselected`, GUT `Scripts 44 / Passing 236`, gdlint and gdformat clean).
  Contrast, same clone, root node moved instead (`GM-main-root-offset`: `transform = Transform3D(1,0,0,0,1,0,0,0,1, 1000,0,0)` on `Main` in main.tscn): `test_scene_placement.gd::test_the_buildings_sit_at_the_scene_origin` and two more fail — only because the Buildings are under it.
- **Harm:** A future change that positions the Trees node or an ancestor of only it (a streaming offset, a transform), or changes what the trees stand on (P-01), gives the owner a forest floating or buried away from the terrain with every gate green. This is Hard Rule 4's harm for the one Tier-1 object M2's fix did not reach; the comment at main.gd:25 claims a protection nobody wired (lesson 2).
- **Fix:** In test_scene_placement.gd assert `Trees` and each MultiMeshInstance3D child have `global_transform == Transform3D.IDENTITY` on the complete world; give complete_world.gd a trees chunk that stands on its own terrain (a few trees at their terrain's bilinear height, as the pipeline computes it; `render_trees.gd` in the Appendix writes such a chunk) and assert that each instance origin in the MultiMesh buffer has y within 1 mm of `main._ground_height(x, z)`; mutation-prove with the 1 km node shift and a 1 m terrain. Correct the comment at main.gd:25 until the test exists.

### M3-R1-P-03 · P2 · No gate runs the shaders that place the photo, the surface classes and the tree crowns' colour, or compares the surface texture with its class bytes: six placements of them leave the whole gate green, and a software render shows each

- **Where:** game/shaders/terrain_photo.gdshader:375 (`puv`), :130-150 (`class_weights`: the `- 0.5` of the texel centre, the row direction, `texelFetch`), game/shaders/tree_conifer.gdshader:67 (`uv = (origin.xz - photo_rect.xy) / photo_rect.zw`), game/scripts/terrain/surface_grid.gd:320 and :323 (`texture = ImageTexture.create_from_image(image)` beside `_classes = pixels`), game/tests/test_m3_09_photo_shader.gd:44-49 (the one placement test: a substring of line 375), test_terrain_loader_photo.gd and test_terrain_loader_surfaces.gd (uniform values, "Does NOT prove: what the shader does with the photo"), test_surface_grid.gd:102-105 (the texture's size and format only), test_m3_11_tree_conifer.gd and test_tree_loader_photo.gd (uniform declarations and values).
- **Claim:** The shaders are the last link between the data and the screen, and Tier 1 where they place the photo and the classes (SPEC §8: "texel (c, r) centred at ((c + 0.5)/columns, (r + 0.5)/rows)", "rows from the north"). No test runs any of their arithmetic. BUILD.md rule 2b accepts that "renders / looks right" is not gated in a container; where an image lies on the ground is a number, and this container measures it: a Compatibility render on Mesa's llvmpipe under Xvfb (the `tools/shot.sh` machinery the briefs already use) of the complete test world puts the photo and the classes where the readers say, to the 0.05 m step of the measurement, in 19 s (`render_check.gd`, Appendix).
- **Proof:** Six mutations (diffs in `muts/`), each run through the full pytest (`2169 passed, 5 deselected`) and the full GUT (`236/236`, all passed), none fails; then `render_check.gd` on each. The clean shader: photo corr(rendered luminance, expected texel luminance) 0.9761 at shift 0 in x and z (the maximum of the 17-step scans), north-south flipped 0.0547, east-west flipped −0.2240; water mask (the ratio of the render with the classes to the render without) agrees with `SurfaceGrid.class_at` on 83'095 of 83'427 samples (best x-shift 0.00 m; best z-shift +0.05 m with 83'100), with the data north-south flipped on 70'468.
  - `SH-photo-uv-flip` (`puv.y = 1.0 - puv.y;` after line 375, which keeps the substring the one test looks for): corr(correct) **0.0554**, north-south flipped **0.9749**: the photo is drawn upside down.
  - `SH-photo-uv-shift` (`puv.x -= 0.1 / photo_rect.z;`): best-fit x-shift **+0.10 m** (corr 0.9759; at 0: 0.9352).
  - `SH-class-half-texel` (`- 0.5` removed from `class_weights`): the water mask's best shift of the data is −0.15 m (83'021 against 82'610 at 0).
  - `SH-class-ns-flip` (`texelFetch(surfaces, ivec2(p.x, size.y - 1 - p.y), 0)`): agreement with the data 69'896 of 83'427, with the data flipped 82'747.
  - `GM-surf-texture-flip` (`image.flip_y()` before `ImageTexture.create_from_image(image)` in `SurfaceGrid`, so the texture the shader reads differs from `_classes`, which `class_at` and its tests read): render: `render_only` 12'846, agreement with the data flipped 82'727 of 83'427.
  - `SH-tree-uv-zx` (`origin.zx`): `render_trees.gd` (20 synthetic trees on the photo fixture, written there, labelled test data): corr(rendered crown luminance, photo luminance under the tree) **0.7513** as shipped, **0.1495** mutated.
  The one mutation that is caught, `SH-photo-uv-wz` (`photo_rect.wz`), is caught by that single substring (`test_the_photo_is_sampled_in_world_space`). The whole `tools/gate.sh` with `SH-photo-uv-flip` applied: `== gate: all steps passed`, `gate exit 0 after 221s`.
- **Harm:** The owner's first run would show a photo drawn upside down at once; but a class grid half a texel (0.1 m) off, mirrored roads and water, a texture that disagrees with `class_at`, and crowns tinted from another place are changes a shader edit makes while the gate stays green, in the one place Hard Rule 4's harm (a silently shifted world) cannot otherwise be caught.
- **Fix:** Put `render_check.gd` (a flat terrain, the photo fixture, the classes, a straight-down camera; it asserts corr(correct) ≥ 0.95 and above every flipped or shifted alternative, and the water mask's best shift is 0) into the gate as a step that is skipped with a named line where `xvfb-run` is missing, as `tools/shot.sh` already needs it; add the tree version (`render_trees.gd`, corr ≥ 0.6 and the maximum). Cheaper and weaker (lesson 5, a census proves text): pin each placement expression of the three shaders by substring as line 375 is. Add to test_surface_grid.gd a test that the texture's bytes equal the class bytes, row by row.

### M3-R1-P-04 · P3 · The game's roof/wall split runs on float32 local coordinates, so it depends on the world's origin: in another world one triangle of the village changes class

- **Where:** game/scripts/buildings/building_loader.gd:127 and :138 (`normal.y >= ROOF_MIN_NORMAL_Y` on `(b - a).cross(c - a).normalized()` of float32 positions), docs/SPEC.md §8 ("the unit normal's up component at least 0.5, the game's rule; an exact 60° cannot occur with integer normals"), pipeline/mattini/roofs.py:499 (the exact rule the colours are measured with).
- **Claim:** The pipeline measures each building's colour from the photo pixels under its roof triangles in exact integers; the game paints those triangles with the colour by a float32 rule. The two agree in the owner's world and are described as one rule; they are one formula, not one result.
- **Proof:** Exact flags per triangle from the buildings step's own helpers on the source sheets (`exact_roof_flags.py`: 1486 buildings, 178'910 triangles, 32'452 roof triangles, as SPEC), the game's flags from the chunk files in each world (`probe_roofflags.gd`): in the owner's world `game roof triangles 32452 … disagreements 0`; in a scratch world with `origin_lv95` E 2625000 / N 1095000 and `height_offset_m` 1000.0 (every step re-run with its expected values recomputed as design would; `buildings` `8542678c…`, `171518e4…`, `4d3bca7e…`, `83551c84…`, `d20dbcda…`, `a5191d46…`; roofs `b60fa6a9…`): `game roof triangles 32451 … disagreements 1, index 87572, game says 0, exact says 1`. `probe_roofs.gd` there: `roof triangles 32451, painted 32451, wrong 0`, against 32'452 in the owner's world.
- **Harm:** After a change of the world's origin (a design change), one roof triangle of the village is drawn in the wall plaster instead of its building's measured colour. No owner would see it; it shows that nothing pins the equality of the two rules beyond formula, and that the 60° limit's slivers decide by the world.
- **Fix:** Name it in SPEC §8 and the loader's comment, or make the game take the decision from the data (the pipeline's `roofs.py:499` already decides per triangle: ship the flag) or compute the normal from differences taken relative to the building's first vertex.

## Checked and clean

Everything below was probed on the real village in the owner's world unless it says otherwise; "scratch world" is the one of P-04 (all coordinates negative, offset 1000 m).

- **The inputs and the steps.** The five downloads verified; `terrain`, `buildings`, `photo`, `roofs`, `surfaces`, `trees`, `manifest` from the command line, each exit 0, each step's own expected-value check passed before it wrote; manifest `3ca0445c…`, 324'359 bytes. The three rasters the grids rest on carry `AREA_OR_POINT=Area` and the transform (0.1 or 0.5, 0, E0, 0, −0.1 or −0.5, N0 + 1000), as the steps' pixel-centre rules assume (rasterio).
- **The photo's grid (pipeline).** An independent derivation (`photo_independent.py`: each tile placed by rasterio's GDAL transform, not by the pipeline's tile-name arithmetic; 2 × 2 block means, round-half-to-even, 10'000 × 15'000 texels) has the pixels' SHA-256 `00533bc6d6c2326c7625e09cadd35707f50573b95d33c2072d0aaf80053d35c0`: equal to the step's `pixels_sha256` and to `config/photo.json`. The four corner texels are the four corner squares of the box: (0, 0) is E 2623000.0–2623000.2 / N 1097999.8–1098000.0, (0, 9999) E 2624999.8–2625000.0 / N 1097999.8–1098000.0, (14999, 0) E 2623000.0–2623000.2 / N 1095000.0–1095000.2, (14999, 9999) E 2624999.8–2625000.0 / N 1095000.0–1095000.2; their colours (144, 141, 119), (78, 94, 64), (97, 116, 91), (25, 33, 34).
- **The photo in the game.** `PhotoGrid` on the real manifest: `rect (0.0, -2000.0, 2000.0, 3000.0)`, equal to `to_local` of the box's north-west and south-east corners (`(0, 0, -2000)`, `(2000, 0, 1000)`); decoded image 10'000 × 15'000, format RGB8, with mipmaps. 8'008 samples (the four corner texels and their neighbours, 6'000 random, 2'000 along the four edges) taken by the shader's own rule, `uv = ((x, z) − (x0, z0)) / (width, depth)`, texel `(floor(u·columns), floor(v·rows))`, from the texel's LV95 centre through `WorldConfig.to_local`: every one lands on its texel (no `texel mismatch` line); the Godot-decoded pixel differs from the independent grid's by a mean `|ΔR|+|ΔG|+|ΔB|` of 8.38 (worst 39: JPEG quality 92, 4:2:0), against 19.95 one texel east, 20.97 one texel south, 167.85 with the rows flipped. The scratch world: `rect (-2000, -3000, 2000, 3000)`, the same 8.38.
- **The surfaces against the data and against the photo.** `surfaces_independent.py` (fiona on the zip, shapely buffers by the SPEC's width table, priorities, no code of `mattini.surfaces`): the PNG is 10'000 × 15'000 L8 (the photo's box and cell, so texel (r, c) is the same square in both) and for 800'000 texel centres (half of them drawn from classed texels) the classes agree on 99.9999 %, on 100.000 % of the 437'742 texels with a class on either side; the PNG read one texel east or south agrees on 98.5 %/98.6 % (97.3 %/97.5 % of the classed), rows flipped 42.6 %, the geometry read at the texel's corner (half a texel off) 98.8 %. `SurfaceGrid.class_at` through `WorldConfig.to_local` on 114'122 points whose class does not change within 0.25 m (`surfaces_points.py`, `probe_surface_points.gd`): 0 wrong, in the owner's world and in the scratch world (`rect (-2000, -3000, 2000, 3000)`).
- **The trees on the ground.** The whole main scene on the real manifest (probe_trees.gd): 34'412 trees, every instance origin read from the MultiMesh buffers, `Terrain3D.data.get_height` at its x and z: **0 more than 5 cm off, 0 more than 1 mm**, worst 0.000244 m, mean 0.000035 m; the `Trees` node has the identity transform. The scratch world: 0 more than 1 mm, worst 0.000122 m. Region seams of Terrain3D are inside that.
- **The trees' positions.** Every tree and every building vertex of the owner's world and of the scratch world, taken back to LV95 through the game's own `WorldConfig.to_lv95` (`probe_tree_lv95.gd`): the largest difference between the two worlds is 0.000244 m (float32 at 2000 m) over 381'018 values, and the terrain's four corner vertices have the same LV95 heights (2615.7549, 1730.8745, 1718.7294, 2186.4849 m). Against the buildings (118'174 plan triangles from the chunk files): 0 of 34'412 trees stand inside one. Against the photo: the photo under the trees is greener and darker (green excess 17.07, luminance 78.3) than at 200'000 random points (11.37, 96.2) and than under the same trees mirrored north-south (11.12, 95.3), mirrored east-west (11.60, 93.8) or moved 5 m (9.16, 63.0): positions are within about a metre, no mirror or swap. Against the surfaces (`probe_tree_classes.gd`): under the trees as placed 34'120 none, 7 rock, 66 water, 172 path, 47 road; mirrored north-south 2'497 rock. (The 66 on water are trees at the edge of an assumed-width stream, SPEC's 2 m.)
- **The roof colours against the buildings' order and counts.** `roofs_independent.py` takes only what the game reads (each chunk's float32 positions and indices) and the roofs block's per-building counts, finds the 0.1 m photo pixels whose centres lie in the plan projection of each building's roof triangles and takes the per-channel lower median from the source tiles: **1486 of 1486 buildings have the block's colour**; 1370 also have its pixel count and 116 differ by at most 4 of up to 943'294 pixels (the float32 positions move exact ties). The building boundaries recovered from the index structure alone (a building starts where a triangle's smallest index exceeds every index seen) are unions of the block's buildings in every chunk (6 of 6 chunks; 8'325 components for 1'486 buildings: the buildings are made of several solids). In the game (`probe_roofs.gd`: `BuildingChunks`, `BuildingRoofs`, `BuildingLoader.create` on the real manifest; each coloured roof triangle's vertex colour compared with the colour of the building whose vertex range holds its first index, a different route from the loader's triangle counts): `roof triangles 32452, painted 32452, wrong 0, wall triangles 146458`. The roof footprints against the photo (`roofs_alignment.py`, pixel-weighted mean absolute deviation of roof luminance from the roof median, 30'392'132 pixels): 27.09 as placed, 27.03 shifted 0.5 m east, 27.2–28.1 within 1 m, 29.0–30.8 at 2 m, 36.9–43.5 at 5 m, 38.2 and 42.0 at 20 m: the buildings and the photo agree in LV95 to about a metre (the 2020 outlines against the 2023 photo, as the SPEC says).
- **The scratch world end to end.** `config/world.json` with origin E 2625000 / N 1095000 and `height_offset_m` 1000: every step refused naming design's step until `computed_for.world_sha256` and the expected values were recomputed as design would (14 values: terrain 1, buildings 6, roofs 1, trees 6; the photo's and the surfaces' pixel hashes are world-independent and held); then all seven steps and the game agree: trees on the ground to 0.000122 m, photo rectangle at the corners, 0 wrong class points, the LV95 round trip above. Hard Rule 4 holds for every new step: nothing but `config/world.json` moved.
- **The gate's mutation coverage of every other seam.** 52 mutations in the table below; 45 fail a named test, `GM-main-trees-offset` (P-02) and the six of P-03 do not. Among them: half a texel (`PL-photo-half-texel`, `PL-surf-centre`, `GM-photo-x0-half-texel`, `GM-photo-z0-half-texel`, `GM-surf-x0-half-texel`, `GM-surf-z0-half-texel`, `GM-surf-class-at-round`, `PL-tree-centre-e`, `PL-tree-centre-n`, `PL-roofs-centre-e`, `PL-roofs-centre-n`), a transposed index (`PL-tree-transpose`), a flipped axis (`PL-photo-ns-flip`, `PL-photo-ew-flip`, `PL-surf-ns-flip`, `PL-surf-ew-flip`, `GM-photo-texture-flip`, `PL-world-sign`, `GM-world-z-sign`), a swapped origin (`GM-photo-sw-origin`, `GM-photo-ne-origin`, `PL-world-origin-swap`, `GM-world-origin-swap`, `PL-tree-axes`), the height offset (`PL-tree-offset`, `PL-world-offset`, `GM-world-offset`) and a building order off by one (`PL-roofs-order-off-by-one`, `PL-roofs-sort`, `PL-buildings-sort`, `GM-roofs-shift`). The fixtures tell the right code from its likeliest wrong twin where it matters: the trees fixture has a 1250 m offset and an origin off the kilometre lattice, the photo fixture a 250 m offset and a north-west corner off the 0.2 m lattice from its origin.
- **Reading and decode.** `TreeChunks` reads the file's float32 records unchanged (`GM-tree-read-yz` fails `test_every_named_tree_is_where_the_world_config_puts_it`); `TreeLoader`'s 12-float rows put the origin in the last column (`GM-tree-buffer-z`); cells use `floori` (`GM-tree-cell`, `GM-tree-cell-int` both fail `test_one_multimesh_per_250_m_cell`); the photo's JPEG decodes top row north (`GM-photo-texture-flip`).
- **Docs and the plan's carried items.** The plan's deferred "two copies of the selection loop" between `roofs.py` and `buildings.py` hold on the real village (the independent check above) and are held equal by the frozen fixtures' bytes: a reorder in `roofs.py` fails `test_roofs_fixture.py` (`PL-roofs-sort`), a reorder in `buildings.py` fails `test_buildings_fixture.py` and, from the roofs side, `test_roofs_fixture.py::test_each_chunk_adds_up_to_its_chunk_file` (`PL-buildings-sort`). The items in the board's "Decisions for design to audit" are not repeated here.

## Mutations

Each row: one mutation in a throwaway clone, the named tests run (pytest files or GUT scripts), and, when none of them failed, the full pytest and the full GUT run. The diffs are `muts/<id>.diff` in the scratchpad; the edits are listed in Appendix F. The harm is what the owner or the build would see if the change were real (lesson 4). "FAILS n" counts failing pytest cases; GUT lists the script and its failing tests.

| Mutation | Harm it reproduces | Result |
|---|---|---|
| `PL-photo-ns-flip` | photo rows within each strip written south to north: the village photo upside down by strip | FAILS 13 (`test_photo_build_tiles.py::test_design_s_pixels_with_another_jpeg_name_the_encoder`, `test_photo_build_tiles.py::test_four_tiles_build_to_design_s_bytes`) |
| `PL-photo-ew-flip` | photo columns mirrored: east and west exchanged | FAILS 16 (`test_photo_build_tiles.py::test_design_s_pixels_with_another_jpeg_name_the_encoder`, `test_photo_build_tiles.py::test_four_tiles_build_to_design_s_bytes`) |
| `PL-photo-half-texel` | photo shifted one 0.1 m source pixel (half a 0.2 m texel) east | FAILS 16 (`test_photo_build_tiles.py::test_design_s_pixels_with_another_jpeg_name_the_encoder`, `test_photo_build_tiles.py::test_four_tiles_build_to_design_s_bytes`) |
| `PL-photo-box-swap` | photo block states a box with east and west exchanged: the game places the photo from it | FAILS 3 (`test_photo_build_tiles.py::test_four_tiles_build_to_design_s_bytes`, `test_photo_fixture.py::test_write_photo_writes_the_fixture_files`) |
| `PL-surf-centre` | surface classes read at the texel's north-west corner, half a texel (0.1 m) off | FAILS 40 (`test_surfaces_fixture.py::test_other_cells_give_the_designed_classes`, `test_surfaces_fixture.py::test_the_class_grid_is_the_designed_one`) |
| `PL-surf-ns-flip` | surface grid written south to north | FAILS 40 (`test_surfaces_fixture.py::test_other_cells_give_the_designed_classes`, `test_surfaces_fixture.py::test_the_class_grid_is_the_designed_one`) |
| `PL-surf-ew-flip` | surface grid mirrored east to west | FAILS 40 (`test_surfaces_fixture.py::test_other_cells_give_the_designed_classes`, `test_surfaces_fixture.py::test_the_class_grid_is_the_designed_one`) |
| `PL-tree-centre-e` | every tree half a DSM pixel (0.25 m) west of where the LiDAR shows it | FAILS 27 (`test_trees_fixture.py::test_each_case_has_its_outcome`, `test_trees_fixture.py::test_every_named_tree_is_in_its_chunk_at_its_index`) |
| `PL-tree-centre-n` | every tree half a DSM pixel (0.25 m) north of where the LiDAR shows it | FAILS 27 (`test_trees_fixture.py::test_each_case_has_its_outcome`, `test_trees_fixture.py::test_every_named_tree_is_in_its_chunk_at_its_index`) |
| `PL-tree-base-corner` | tree base height taken from one terrain vertex instead of the mean of four | FAILS 3 (`test_trees_fixture.py::test_every_named_tree_is_in_its_chunk_at_its_index`, `test_trees_fixture.py::test_the_chunks_are_the_fixture_s_bytes`) |
| `PL-tree-offset` | tree base height ignores height_offset_m: trees float or sink by the offset in a world with one | FAILS 3 (`test_trees_fixture.py::test_every_named_tree_is_in_its_chunk_at_its_index`, `test_trees_fixture.py::test_the_chunks_are_the_fixture_s_bytes`) |
| `PL-tree-axes` | tree positions with east and north exchanged | FAILS 27 (`test_trees_fixture.py::test_each_case_has_its_outcome`, `test_trees_fixture.py::test_every_named_tree_is_in_its_chunk_at_its_index`) |
| `PL-tree-tile-swap` | tree chunks named with kilometres exchanged | FAILS 13 (`test_trees_checks.py::test_a_chunk_that_is_missing_short_or_changed_is_refused`, `test_trees_checks.py::test_a_chunk_that_is_not_the_configs_expected_one_is_refused`) |
| `PL-tree-mosaic` | DSM and DTM tiles placed one pixel east in the area mosaic | FAILS 39 (`test_trees_checks.py::test_a_chunk_that_is_missing_short_or_changed_is_refused`, `test_trees_checks.py::test_a_chunk_that_is_not_the_configs_expected_one_is_refused`) |
| `PL-roofs-centre-e` | roof pixels read at the pixel's west edge instead of its centre | FAILS 12 (`test_roofs_fixture.py::test_no_roof_pixel_means_no_colour`, `test_roofs_fixture.py::test_the_rule_gives_the_fixture_s_roofs`) |
| `PL-roofs-centre-n` | roof pixels read at the pixel's north edge instead of its centre | FAILS 12 (`test_roofs_fixture.py::test_no_roof_pixel_means_no_colour`, `test_roofs_fixture.py::test_the_rule_gives_the_fixture_s_roofs`) |
| `PL-roofs-order-off-by-one` | every roof colour on the next building's roof | FAILS 8 (`test_roofs_fixture.py::test_no_roof_pixel_means_no_colour`, `test_roofs_fixture.py::test_the_rule_gives_the_fixture_s_roofs`) |
| `PL-roofs-sort` | roofs listed in another order than the buildings step lists them | FAILS 4 (`test_roofs_fixture.py::test_the_rule_gives_the_fixture_s_roofs`, `test_roofs_fixture.py::test_write_roofs_writes_the_fixture_s_bytes`) |
| `PL-world-offset` | height offset ignored by the pipeline's to_local | FAILS 2 (`test_world_transforms.py::test_height_offset_is_subtracted_from_heights`, `test_world.py::test_origin_numbers_live_only_in_config`) |
| `PL-world-sign` | z not negated: the pipeline's world mirrored north-south | FAILS 38 (`test_world.py::test_load_world_reads_the_given_file`, `test_world.py::test_mapping_is_a_rotation_not_a_mirror`) |
| `GM-photo-sw-origin` | photo's rectangle starts at the south-west corner: 3 km off to the south | FAILS (`test_photo_grid.gd`: `test_the_fixture_photo_is_read_as_designed`, `test_the_named_points_read_their_texels`) |
| `GM-photo-ne-origin` | photo's rectangle starts at the north-east corner: 2 km off to the east | FAILS (`test_photo_grid.gd`: `test_the_fixture_photo_is_read_as_designed`, `test_the_named_points_read_their_texels`) |
| `GM-photo-rect-swap` | photo's width and depth exchanged in the shader's rectangle | FAILS (`test_photo_grid.gd`: `test_the_fixture_photo_is_read_as_designed`, `test_jpegs_that_do_not_match_are_refused`) |
| `GM-surf-class-at-round` | class_at reads the texel half a texel off (round instead of floor) | FAILS (`test_surface_grid.gd`: `test_every_named_point_has_its_class`, `test_the_rectangle_is_half_open_and_outside_is_minus_one`) |
| `GM-surf-rect-shift` | the surfaces' rectangle given to the shader half a texel east | FAILS (`test_terrain_loader_surfaces.gd`: `test_the_classes_and_their_rectangle_reach_the_shader`, `test_the_classes_without_a_photo_keep_the_clay_look`) |
| `GM-tree-read-yz` | tree reader exchanges base height and z | FAILS (`test_tree_chunks.gd`: `test_every_named_tree_is_where_the_world_config_puts_it`, `test_a_chunk_file_of_another_size_is_refused`) |
| `GM-tree-buffer-z` | tree instances placed at the mirror of their z | FAILS (`test_tree_loader.gd`: `test_every_named_tree_stands_at_its_position_scaled_to_its_size`, `test_the_credits_note_says_the_conifer_is_generic`) |
| `GM-tree-cell` | trees filed into the cell of their mirrored z | FAILS (`test_tree_loader.gd`: `test_one_multimesh_per_250_m_cell`, `test_every_named_tree_stands_at_its_position_scaled_to_its_size`) |
| `GM-main-trees-rect` | the trees get the photo's rectangle with x0 and z0 exchanged: crown colours sampled elsewhere | FAILS (`test_main_scene_data.gd`: `test_every_loader_receives_its_block`, `test_the_credits_name_every_dataset_texture_and_placeholder`) |
| `GM-main-trees-offset` | the Trees node 1 km east of the terrain | **NOT CAUGHT**: full pytest 2169 passed, 5 deselected; full GUT 236/236 passed |
| `GM-main-terrain-photo-rect` | terrain gets the surfaces' rectangle as its photo rectangle (photo and surfaces exchanged) | FAILS (`test_main_scene_data.gd`: `test_every_loader_receives_its_block`, `test_the_credits_name_every_dataset_texture_and_placeholder`) |
| `GM-roofs-shift` | game paints every roof in the previous building's colour | FAILS (`test_m3_12_loader.gd`: `test_each_surface_holds_the_triangles_of_its_kind`, `test_the_colours_belong_to_the_chunks`) |
| `GM-world-offset` | height offset ignored by the game's to_local | FAILS (`test_world_config_transforms.gd`: `test_height_offset_is_subtracted_from_heights`) |
| `GM-world-z-sign` | z not negated in the game's to_local: north-south mirror | FAILS (`test_world_config.gd`: `test_to_local_matches_shared_vectors`, `test_to_lv95_matches_shared_vectors`) |
| `SH-photo-uv-wz` | photo uv divided by (depth, width): the photo squeezed and mislaid | FAILS (`test_m3_09_photo_shader.gd`: `test_the_photo_is_sampled_in_world_space`) |
| `SH-photo-uv-flip` | photo drawn north-south mirrored on the terrain | **NOT CAUGHT**: full pytest 2169 passed, 5 deselected; full GUT 236/236 passed |
| `SH-photo-uv-shift` | photo drawn half a texel (0.1 m) east of where it belongs | **NOT CAUGHT**: full pytest 2169 passed, 5 deselected; full GUT 236/236 passed |
| `SH-class-half-texel` | surface classes drawn half a texel (0.1 m) off | **NOT CAUGHT**: full pytest 2169 passed, 5 deselected; full GUT 236/236 passed |
| `SH-class-ns-flip` | surface classes drawn north-south mirrored on the terrain | **NOT CAUGHT**: full pytest 2169 passed, 5 deselected; full GUT 236/236 passed |
| `SH-tree-uv-zx` | tree crowns sample the photo with x and z exchanged | **NOT CAUGHT**: full pytest 2169 passed, 5 deselected; full GUT 236/236 passed |
| `GM-main-root-offset` | the whole scene root 1 km east: Terrain3D and the shaders (world space) no longer agree with the data's local coordinates | FAILS (`test_scene_placement.gd`: `test_the_buildings_sit_at_the_scene_origin`, `test_every_named_vertex_lies_in_the_scene_where_the_world_config_puts_it`) |
| `GM-surf-texture-flip` | surface texture (what the shader reads) flipped north-south while class_at still reads the unflipped bytes | **NOT CAUGHT**: full pytest 2169 passed, 5 deselected; full GUT 236/236 passed |
| `GM-photo-texture-flip` | photo texture decoded upside down | FAILS (`test_photo_grid.gd`: `test_the_named_points_read_their_texels`, `test_jpegs_that_do_not_match_are_refused`) |
| `GM-photo-x0-half-texel` | photo rectangle starts half a texel (0.1 m) east of the box corner | FAILS (`test_photo_grid.gd`: `test_the_fixture_photo_is_read_as_designed`, `test_the_named_points_read_their_texels`) |
| `GM-photo-z0-half-texel` | photo rectangle starts half a texel (0.1 m) south of the box corner | FAILS (`test_photo_grid.gd`: `test_the_fixture_photo_is_read_as_designed`, `test_the_named_points_read_their_texels`) |
| `GM-surf-x0-half-texel` | surface rectangle starts half a texel (0.1 m) east of the box corner | FAILS (`test_surface_grid.gd`: `test_the_fixture_grid_is_read_as_designed`, `test_every_named_point_has_its_class`) |
| `GM-surf-z0-half-texel` | surface rectangle starts half a texel (0.1 m) south of the box corner | FAILS (`test_surface_grid.gd`: `test_the_fixture_grid_is_read_as_designed`, `test_every_named_point_has_its_class`) |
| `GM-tree-cell-int` | trees filed with truncation instead of floor (cells merge across zero) | FAILS (`test_tree_loader.gd`: `test_one_multimesh_per_250_m_cell`, `test_every_named_tree_stands_at_its_position_scaled_to_its_size`) |
| `PL-world-origin-swap` | the pipeline's origin easting and northing exchanged | FAILS 38 (`test_world.py::test_load_world_reads_the_given_file`, `test_world.py::test_to_local_matches_shared_vectors`) |
| `GM-world-origin-swap` | the game's origin easting and northing exchanged | FAILS (`test_world_config.gd`: `test_to_local_matches_shared_vectors`, `test_to_lv95_matches_shared_vectors`) |
| `PL-buildings-sort` | the buildings step lists the buildings of a chunk in another order than the roofs step does | FAILS 12 in `test_buildings_fixture.py::test_the_chunks_hold_the_designed_buildings`, `test_buildings_step.py` and, from the roofs side, `test_roofs_fixture.py::test_each_chunk_adds_up_to_its_chunk_file` |
| `PL-tree-transpose` | tree base height read from the transposed terrain index (rows and columns exchanged) in a square test area | FAILS 3 (`test_trees_fixture.py::test_every_named_tree_is_in_its_chunk_at_its_index`, `test_trees_fixture.py::test_the_chunks_are_the_fixture_s_bytes`) |

Not caught is not the same as not wrong: the owner's first run on a GPU would show a flipped photo at once; the rows say what no test or gate would.

## Notes

- **What this lens does not prove.** That anything renders or looks right on the owner's Forward+ (the render checks are Compatibility on llvmpipe, a flat synthetic terrain, and measure *where* the photo, the classes and the crowns are, not how they look); the exported build and the Windows build; the tree shader on the real village (only on 20 synthetic trees); how Terrain3D 1.0.2 treats a transform on its own node (the root-node mutation of the table is caught only through the Buildings' transform tests); the MultiMesh bounds and `visibility_range_end` of the tree cells (headless draws nothing); the data packs and the export (the game-and-tools lens).
- **The render checks.** `render_check.gd` writes the complete test world with a flat terrain (one level, so the ray of a pixel meets the ground by a plane), removes the buildings, roofs and trees blocks, puts the camera 9 m above the photo's centre looking straight down, finds for every third pixel the world point under it, and compares the rendered luminance with the luminance of the photo texel the *data* put there (`PhotoGrid`'s rectangle and decoded image), under shifts of the data of ±0.4 m, and the water mask (the ratio of the render with the classes to the render without, below 0.85) with `SurfaceGrid.class_at`. It reads nothing of the shader. A mutation that moves a sampling position by 0.1 m moves the best fit by 0.1 m; the soft one-texel edge of the classes limits the class test to about 0.05 m. 19 s a run.
- **The 2020 buildings against the 2023 photo.** The roof footprints' luminance spread is lowest at about +0.5 m east of the LV95 positions (27.03 against 27.09), flat within 1 m, rising beyond: a property of the data (a relief-displaced orthophoto against a 2020 model, SPEC's "1–2 m"), not of a transform.
- **Trees over streams.** 66 trees stand on texels of the surfaces' water class: trees at the edge of a stream drawn with the assumed 2 m width; 7 on rock texels at a rock boundary. The trees step excludes rock by pixel centres at 0.5 m, the surfaces classify texel centres at 0.2 m; nothing wrong; said so that the numbers are not read as a defect.
- **Process, said openly.** (1) The first run of the game-side mutation driver named GUT scripts as pytest paths; it was stopped, its clone restored with `git apply -R` of the saved diff, the driver corrected and rerun; no result of the first run is used. (2) The `mut` clone's generated data, and at first the `render` clone's, sat in `game/assets/` instead of `game/assets/generated/` (a `cp -r` into a directory that did not exist yet); `mut` was used only for pytest mutations whose named tests do not read the data, and the `render` clone's first full-suite result for `GM-surf-texture-flip` (which failed on the missing manifest, not on the mutation) was discarded and rerun after the layout was fixed; the other full-suite proofs come from `mut2`, whose layout the green full suites themselves confirm (the world-config tests fail without it). (3) A first whole-gate run over `GM-main-trees-offset` failed at two `test_repo_hygiene.py` cases because the clone's `data` was a symlink (`git check-ignore` refuses a path beyond one); it was discarded and rerun in a clone without it (the `manifest` step needs no raw data).
- **For design.** The rehearsal on the scratch world (6 min 28 s to recompute 14 expected values and rebuild every step, then the probes) found P-04 and nothing else; every fixture of the four new steps lies east of its origin (local x from 12 m to 1100 m; only the terrain's own north-west fixture has x below 0), so a sign error that only a negative x shows (a truncating `int()` where `floori` is meant, for instance) is caught for z (`GM-tree-cell-int` fails on the trees at z < 0) and would not be for x. A fixture world with the area north-west of its origin for photo, surfaces, trees and roofs is the cheap gate for it; the scratch world of P-04 is such a rehearsal, once.
- **Placement verdict.** No P0 and no P1: the village's photo, surface classes, trees and roof colours are placed where `config/world.json` and the data say, in the owner's world and in a scratch world with another origin, a height offset and the grid north-west of its origin, down to 0.25 mm, and the independent derivations (rasterio, shapely, the chunk files and the source tiles) agree with the pipeline's outputs and the game's readers. The three P2 are gaps in what is gated, not wrong data: a config change that puts trees off the ground (P-01), the scene transform of the Trees (P-02), the shaders (P-03).

## Appendix: the scratch scripts that reproduce the findings

Everything below ran from the session's scratchpad, never from the repository, and is not committed. `\n` and `\t` in Appendix F are a line feed and a tab.

### A. probe_trees.gd (P-01, P-02; "The trees on the ground")

`godot --headless --path game -s <path>/probe_trees.gd` in a clone with the real village's `game/assets/generated/`.

```gdscript
extends SceneTree
## Probe: the real village's trees against Terrain3D's ground, through the whole main scene.
## Reads every instance's origin from its MultiMesh buffer (the scene's final placement).


func _initialize() -> void:
	await process_frame
	var t0 := Time.get_ticks_msec()
	var main: Node3D = load("res://main.tscn").instantiate()
	main.manifest_path = "res://assets/generated/manifest.json"
	root.add_child(main)
	for i in 8:
		await process_frame
	print("PROBE main loaded in %d ms" % (Time.get_ticks_msec() - t0))
	var trees: Node3D = main.get_node_or_null("Trees")
	var terrain: Terrain3D = main.get_node_or_null("Terrain")
	print("PROBE trees node: %s terrain node: %s" % [trees, terrain])
	if trees == null or terrain == null:
		quit(1)
		return
	print("PROBE Trees global_transform == IDENTITY: %s" % (trees.global_transform == Transform3D.IDENTITY))
	var total := 0
	var off5 := 0
	var off1 := 0
	var nan_count := 0
	var worst := 0.0
	var sum_abs := 0.0
	var min_x := INF
	var max_x := -INF
	var min_z := INF
	var max_z := -INF
	var worst_at := Vector3.ZERO
	var buckets := [0, 0, 0, 0, 0, 0]  # <=1mm, <=1cm, <=5cm, <=20cm, <=1m, >1m
	for child in trees.get_children():
		var mm := (child as MultiMeshInstance3D).multimesh
		var b := mm.buffer
		assert(child.global_transform == Transform3D.IDENTITY)
		for k in b.size() / 12:
			var o := 12 * k
			var x := b[o + 3]
			var y := b[o + 7]
			var z := b[o + 11]
			var ground: float = terrain.data.get_height(Vector3(x, 0.0, z))
			total += 1
			min_x = minf(min_x, x)
			max_x = maxf(max_x, x)
			min_z = minf(min_z, z)
			max_z = maxf(max_z, z)
			if is_nan(ground):
				nan_count += 1
				continue
			var d := absf(y - ground)
			sum_abs += d
			if d > worst:
				worst = d
				worst_at = Vector3(x, y, z)
			if d > 0.05:
				off5 += 1
			if d > 0.01:
				off1 += 1
			if d <= 0.001:
				buckets[0] += 1
			elif d <= 0.01:
				buckets[1] += 1
			elif d <= 0.05:
				buckets[2] += 1
			elif d <= 0.2:
				buckets[3] += 1
			elif d <= 1.0:
				buckets[4] += 1
			else:
				buckets[5] += 1
	print("PROBE trees total=%d nan_ground=%d off>1cm=%d off>5cm=%d worst=%.6f at %s mean_abs=%.6f" % [total, nan_count, off1, off5, worst, worst_at, sum_abs / maxf(1.0, total - nan_count)])
	print("PROBE buckets <=1mm,<=1cm,<=5cm,<=20cm,<=1m,>1m: %s" % [buckets])
	print("PROBE x range %.3f..%.3f z range %.3f..%.3f" % [min_x, max_x, min_z, max_z])
	quit(0)
```

### B. render_check.gd (P-03)

`xvfb-run -a godot --path game --rendering-method gl_compatibility --resolution 1280x720 -s <path>/render_check.gd`, with the `OUT` constant set to an existing folder.

```gdscript
extends SceneTree
## Software-render check of where the photo shader puts the photo and the surface classes.
## Evidence only (Compatibility renderer on llvmpipe, brain.md H12). A flat synthetic terrain
## (the complete test world, heights replaced by one level, buildings/roofs/trees removed), a camera
## straight above it; for sample pixels the world point under the pixel is found by intersecting the
## pixel's ray with the flat ground, then the rendered pixel is compared with what the DATA says is at
## that point: the photo texel (PhotoGrid's rectangle and decoded image) and the surface class
## (SurfaceGrid.class_at).
const CompleteWorld := preload("res://tests/complete_world.gd")
const LEVEL := 605.0
const STEP := 3
const OUT := "/tmp/shots"


func _lum(c: Color) -> float:
	return 255.0 * (0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b)


func _initialize() -> void:
	await process_frame
	var heights := PackedFloat32Array()
	heights.resize(41 * 24)
	heights.fill(LEVEL)
	var bytes := heights.to_byte_array()
	var path := CompleteWorld.write(
		"user://render_check",
		func(m: Dictionary) -> void:
			m["terrain"]["sha256"] = CompleteWorld.sha256(bytes)
			m["buildings"] = null
			m["roofs"] = null
			m["trees"] = null,
		bytes
	)
	var main: Node3D = load("res://main.tscn").instantiate()
	main.manifest_path = path
	root.add_child(main)
	for i in 4:
		await process_frame
	var world := WorldConfig.from_manifest(path)
	var photo := PhotoGrid.from_manifest(path, world)
	var surfaces := SurfaceGrid.from_manifest(path, world)
	var terrain: Terrain3D = main.get_node("Terrain")
	main.get_node("UI/ErrorPanel").hide()
	var camera: FreeFlyCamera = main.get_node("Camera")
	var centre := Vector3(1025.0, LEVEL + 9.0, 16.25)
	camera.set_view(centre, 0.0, -deg_to_rad(89.0))
	var cam: Camera3D = camera
	var image_a := await _capture()
	image_a.save_png(OUT.path_join("render_with_surfaces.png"))
	# the same view with every class removed: the lighting and the photo alone
	var black := ImageTexture.create_from_image(Image.create_empty(1, 1, false, Image.FORMAT_L8))
	terrain.material.set_shader_param("surfaces", black)
	var image_b := await _capture()
	image_b.save_png(OUT.path_join("render_without_surfaces.png"))
	var source_image := photo.texture.get_image()

	var samples := []
	for py in range(0, image_a.get_height(), STEP):
		for px in range(0, image_a.get_width(), STEP):
			var o := cam.project_ray_origin(Vector2(px + 0.5, py + 0.5))
			var d := cam.project_ray_normal(Vector2(px + 0.5, py + 0.5))
			if d.y >= -0.01:
				continue
			var t := (LEVEL - o.y) / d.y
			var p := o + d * t
			if p.x < 1015.0 or p.x > 1035.0 or p.z < 10.5 or p.z > 22.0:
				continue
			samples.append([px, py, p.x, p.z])
	print("RENDER samples over the terrain: %d" % samples.size())

	# ---- the photo: corr(rendered luminance, expected texel luminance) under hypotheses
	var inside := []
	for s in samples:
		var u: float = (s[2] - photo.x0) / photo.width_m
		var v: float = (s[3] - photo.z0) / photo.depth_m
		if u > 0.03 and u < 0.97 and v > 0.03 and v < 0.97:
			# stay off water/road/path pixels: the photo alone is under test
			if surfaces.class_at(s[2], s[3]) == 0:
				inside.append(s)
	print("RENDER pixels inside the photo and on class 0: %d" % inside.size())
	var rendered := PackedFloat64Array()
	for s in inside:
		rendered.append(_lum(image_a.get_pixel(s[0], s[1])))
	var table := []
	for dx in range(-8, 9):
		table.append(_corr_shift(rendered, inside, photo, source_image, dx * 0.05, 0.0, false, false))
	print("RENDER corr by x-shift (-0.40..0.40 m step 0.05): %s" % [table])
	table = []
	for dz in range(-8, 9):
		table.append(_corr_shift(rendered, inside, photo, source_image, 0.0, dz * 0.05, false, false))
	print("RENDER corr by z-shift (-0.40..0.40 m step 0.05): %s" % [table])
	print("RENDER corr correct=%.4f ns-flipped=%.4f ew-flipped=%.4f" % [
		_corr_shift(rendered, inside, photo, source_image, 0.0, 0.0, false, false),
		_corr_shift(rendered, inside, photo, source_image, 0.0, 0.0, true, false),
		_corr_shift(rendered, inside, photo, source_image, 0.0, 0.0, false, true)])

	# ---- the classes: water darkens the photo (x0.6): ratio of the two renders against class_at
	var counts := {"both": 0, "render_only": 0, "data_only": 0, "neither": 0}
	var tab_dx := []
	for dxi in range(-6, 7):
		var dx := dxi * 0.05
		var agree := 0
		var total := 0
		for s in samples:
			var lb := _lum(image_b.get_pixel(s[0], s[1]))
			if lb < 8.0:
				continue
			var ratio := _lum(image_a.get_pixel(s[0], s[1])) / lb
			var render_water := ratio < 0.85
			var data_water := surfaces.class_at(s[2] - dx, s[3]) == 2
			total += 1
			if render_water == data_water:
				agree += 1
			if dxi == 0:
				if render_water and data_water:
					counts["both"] += 1
				elif render_water:
					counts["render_only"] += 1
				elif data_water:
					counts["data_only"] += 1
				else:
					counts["neither"] += 1
		tab_dx.append("%.2f:%d/%d" % [dx, agree, total])
	print("RENDER water mask vs class_at at dx=0: %s" % [counts])
	print("RENDER water-mask agreement by x-shift of the data: %s" % [tab_dx])
	var tab_dz := []
	for dzi in range(-6, 7):
		var dz := dzi * 0.05
		var agree := 0
		var total := 0
		for s in samples:
			var lb := _lum(image_b.get_pixel(s[0], s[1]))
			if lb < 8.0:
				continue
			var ratio := _lum(image_a.get_pixel(s[0], s[1])) / lb
			total += 1
			if (ratio < 0.85) == (surfaces.class_at(s[2], s[3] - dz) == 2):
				agree += 1
		tab_dz.append("%.2f:%d/%d" % [dz, agree, total])
	print("RENDER water-mask agreement by z-shift of the data: %s" % [tab_dz])
	var flip := 0
	var flip_total := 0
	for s in samples:
		var lb := _lum(image_b.get_pixel(s[0], s[1]))
		if lb < 8.0:
			continue
		var ratio := _lum(image_a.get_pixel(s[0], s[1])) / lb
		var zf: float = 2.0 * (surfaces.z0 + surfaces.depth_m / 2.0) - s[3]
		flip_total += 1
		if (ratio < 0.85) == (surfaces.class_at(s[2], zf) == 2):
			flip += 1
	print("RENDER water-mask agreement with the data north-south flipped: %d/%d" % [flip, flip_total])
	quit(0)


func _capture() -> Image:
	for i in 10:
		await process_frame
	await RenderingServer.frame_post_draw
	return root.get_texture().get_image()


## Pearson correlation between the rendered luminance and the luminance of the photo texel the data
## puts under each pixel's world point, the texel looked up after moving the point by (dx, dz) metres.
func _corr_shift(rendered: PackedFloat64Array, pts: Array, photo: PhotoGrid, source: Image, dx: float, dz: float, ns_flip: bool, ew_flip: bool) -> float:
	var n := pts.size()
	var expected := PackedFloat64Array()
	expected.resize(n)
	for i in n:
		var col := floori((pts[i][2] - dx - photo.x0) / photo.cell_m)
		var row := floori((pts[i][3] - dz - photo.z0) / photo.cell_m)
		if ns_flip:
			row = photo.rows - 1 - row
		if ew_flip:
			col = photo.columns - 1 - col
		col = clampi(col, 0, photo.columns - 1)
		row = clampi(row, 0, photo.rows - 1)
		expected[i] = _lum(source.get_pixel(col, row))
	var mr := 0.0
	var me := 0.0
	for i in n:
		mr += rendered[i]
		me += expected[i]
	mr /= n
	me /= n
	var sxy := 0.0
	var sxx := 0.0
	var syy := 0.0
	for i in n:
		var a := rendered[i] - mr
		var b := expected[i] - me
		sxy += a * b
		sxx += a * a
		syy += b * b
	return snappedf(sxy / sqrt(maxf(sxx * syy, 1e-12)), 0.0001)
```

### C. render_trees.gd (P-03, the tree shader; P-02's fix sketch)

Same command.

```gdscript
extends SceneTree
## Software-render check of where the TREE shader reads the photo: a flat terrain with the photo fixture on it and 40 synthetic
## trees (their own chunk, written here, labelled test data) standing on it at block centres of the photo; a camera straight above. For each
## tree the rendered crown luminance at its apex is compared with the photo's luminance (the data) around the tree's position.
const CompleteWorld := preload("res://tests/complete_world.gd")
const LEVEL := 605.0
const OUT := "/tmp/shots"
const TILE := "2601-1199"


func _lum(c: Color) -> float:
	return 255.0 * (0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b)


func _initialize() -> void:
	await process_frame
	var heights := PackedFloat32Array()
	heights.resize(41 * 24)
	heights.fill(LEVEL)
	var bytes := heights.to_byte_array()
	# 5 x 10 photo blocks of 1.6 m: the photo rectangle is (1017, 11.5, 16, 8); a tree at the centre of every block but the first row's
	var trees := PackedFloat32Array()
	var count := 0
	for bz in range(1, 5):
		for bx in range(0, 10, 2):
			trees.append_array(PackedFloat32Array([1017.0 + 1.6 * bx + 0.8, LEVEL, 11.5 + 1.6 * bz + 0.8, 4.0, 0.7]))
			count += 1
	var chunk := trees.to_byte_array()
	var dir := "user://render_trees"
	var path := CompleteWorld.write(
		dir,
		func(m: Dictionary) -> void:
			m["terrain"]["sha256"] = CompleteWorld.sha256(bytes)
			m["buildings"] = null
			m["roofs"] = null
			var f := FileAccess.open(dir.path_join("trees/" + TILE + ".bin"), FileAccess.WRITE)
			f.store_buffer(chunk)
			f.close()
			m["trees"]["chunks"] = [{"file": "trees/" + TILE + ".bin", "sha256": CompleteWorld.sha256(chunk), "tile": TILE, "trees": count}],
		bytes
	)
	var main: Node3D = load("res://main.tscn").instantiate()
	main.manifest_path = path
	root.add_child(main)
	for i in 4:
		await process_frame
	var world := WorldConfig.from_manifest(path)
	var photo := PhotoGrid.from_manifest(path, world)
	var surfaces := SurfaceGrid.from_manifest(path, world)
	main.get_node("UI/ErrorPanel").hide()
	var terrain: Terrain3D = main.get_node("Terrain")
	# the photo alone under the trees: no classes
	terrain.material.set_shader_param("surfaces", ImageTexture.create_from_image(Image.create_empty(1, 1, false, Image.FORMAT_L8)))
	var camera: FreeFlyCamera = main.get_node("Camera")
	camera.set_view(Vector3(1025.0, LEVEL + 22.0, 15.5), 0.0, -deg_to_rad(89.0))
	var cam: Camera3D = camera
	for i in 12:
		await process_frame
	await RenderingServer.frame_post_draw
	var image := root.get_texture().get_image()
	image.save_png(OUT.path_join("render_trees.png"))
	var source := photo.texture.get_image()
	var rendered := PackedFloat64Array()
	var expected := {"correct": PackedFloat64Array(), "swapped x/z": PackedFloat64Array(), "mirrored north-south": PackedFloat64Array(), "mirrored east-west": PackedFloat64Array()}
	for k in count:
		var x: float = trees[5 * k]
		var z: float = trees[5 * k + 2]
		var s := 0.0
		var n := 0
		for height in [1.6, 2.0, 2.4]:
			var at := cam.unproject_position(Vector3(x, LEVEL + height, z))
			for dy in range(-2, 3):
				for dx in range(-2, 3):
					s += _lum(image.get_pixel(int(at.x) + dx, int(at.y) + dy))
					n += 1
		rendered.append(s / n)
		expected["correct"].append(_block_lum(source, photo, x, z))
		# hypotheses about where the crown colour might have been read
		expected["swapped x/z"].append(_block_lum(source, photo, photo.x0 + (z - photo.z0) * photo.width_m / photo.depth_m, photo.z0 + (x - photo.x0) * photo.depth_m / photo.width_m))
		expected["mirrored north-south"].append(_block_lum(source, photo, x, 2.0 * photo.z0 + photo.depth_m - z))
		expected["mirrored east-west"].append(_block_lum(source, photo, 2.0 * photo.x0 + photo.width_m - x, z))
	for key: String in expected:
		print("RENDERTREES corr(rendered crown luminance at the apex, photo luminance at the %s position) over %d trees: %.4f" % [key, count, _corr(rendered, expected[key])])
	quit(0)


func _block_lum(source: Image, photo: PhotoGrid, x: float, z: float) -> float:
	var col := floori((x - photo.x0) / photo.cell_m)
	var row := floori((z - photo.z0) / photo.cell_m)
	var s := 0.0
	var n := 0
	for dr in range(-3, 4):
		for dc in range(-3, 4):
			s += _lum(source.get_pixel(clampi(col + dc, 0, photo.columns - 1), clampi(row + dr, 0, photo.rows - 1)))
			n += 1
	return s / n


func _corr(a: PackedFloat64Array, b: PackedFloat64Array) -> float:
	var n := a.size()
	var ma := 0.0
	var mb := 0.0
	for i in n:
		ma += a[i]
		mb += b[i]
	ma /= n
	mb /= n
	var sab := 0.0
	var saa := 0.0
	var sbb := 0.0
	for i in n:
		sab += (a[i] - ma) * (b[i] - mb)
		saa += (a[i] - ma) * (a[i] - ma)
		sbb += (b[i] - mb) * (b[i] - mb)
	return snappedf(sab / sqrt(maxf(saa * sbb, 1e-12)), 0.0001)
```

### D. exact_roof_flags.py and probe_roofflags.gd (P-04)

`uv run --project pipeline python -I exact_roof_flags.py <clone> flags.bin` in the clone with the raw sheets, and `godot --headless --path game -s probe_roofflags.gd -- <out>` in each world's clone; the two byte files are compared per triangle.

```python
"""The pipeline's exact roof/wall decision for every triangle of every chunk in chunk-file order (the buildings
step's own helpers on the source sheets; integer arithmetic), written as one byte per triangle."""
import sys, json
from pathlib import Path
import numpy as np
base = Path(sys.argv[1]); raw = base / "data/raw/swissbuildings3d/2020"
from mattini.buildings import read_sheet, _weld, _signed_volume
from mattini.roofs import _snapped, _roof_triangle, UNITS_PER_M, TILE_M
from mattini.world import load_world
import math
world = load_world(base / "config/world.json")
e_min, e_max, n_min, n_max = world.area("village")
prov = json.loads((raw / "provenance.json").read_text())
features = []
for entry in prov["sheets"] if "sheets" in prov else prov["files"]:
    name = entry["file"]
    features += read_sheet((raw / name).read_bytes(), entry.get("sheet", name))
cands = []
for f in features:
    sn = _snapped(f)
    es = [p[0] for t in sn for p in t]; ns = [p[1] for t in sn for p in t]
    ce, cn = (min(es) + max(es)) / 2, (min(ns) + max(ns)) / 2
    if e_min <= ce < e_max and n_min <= cn < n_max:
        cands.append((f"{math.floor(ce / TILE_M)}-{math.floor(cn / TILE_M)}", f["uuid"], sn))
cands.sort(key=lambda c: (c[0], c[1]))
flags = {}
for tile, uuid, sn in cands:
    vertices, triangles = _weld(sn)
    if _signed_volume({"uuid": uuid}, vertices, triangles) < 0:
        triangles = [(a, c, b) for a, b, c in triangles]
    units = [tuple(round(v * UNITS_PER_M) for v in vx) for vx in vertices]
    flags.setdefault(tile, []).extend(1 if _roof_triangle(units[a], units[b], units[c]) is not None else 0 for a, b, c in triangles)
out = np.concatenate([np.array(flags[t], np.uint8) for t in sorted(flags)])
out.tofile(sys.argv[2])
print("buildings", len(cands), "triangles", len(out), "exact roof triangles", int(out.sum()), {t: (len(v), sum(v)) for t, v in sorted(flags.items())})
```

```gdscript
extends SceneTree
## Writes the game's roof decision (normal.y >= 0.5 in float32, BuildingLoader's rule) per triangle, chunk order.
func _initialize() -> void:
	await process_frame
	var out_path: String = OS.get_cmdline_user_args()[0]
	var manifest := "res://assets/generated/manifest.json"
	var world := WorldConfig.from_manifest(manifest)
	var chunks := BuildingChunks.from_manifest(manifest, world)
	var flags := PackedByteArray()
	var edge := []
	for chunk: Dictionary in chunks.chunks:
		var p: PackedVector3Array = chunk["positions"]
		var idx: PackedInt32Array = chunk["indices"]
		for t in idx.size() / 3:
			var a := p[idx[3 * t]]
			var b := p[idx[3 * t + 1]]
			var c := p[idx[3 * t + 2]]
			var ny := (b - a).cross(c - a).normalized().y
			flags.append(1 if ny >= 0.5 else 0)
			if absf(ny - 0.5) < 1e-6:
				edge.append([chunk["tile"], t, ny])
	var f := FileAccess.open(out_path, FileAccess.WRITE)
	f.store_buffer(flags)
	f.close()
	print("PROBE triangles %d, game roof triangles %d; triangles within 1e-6 of the 60 degree limit: %s" % [flags.size(), flags.count(1), edge])
	quit(0)
```

### E. recompute_expected.py (P-04's scratch world)

Run in a clone whose `config/world.json` has `origin_lv95` E 2625000.0 / N 1095000.0 and `height_offset_m` 1000.0, with `--raw` pointing at the downloads: it sets every step config's `computed_for.world_sha256` and replaces each expected value the step refuses with the one the step built, as design would.

```python
"""As design would for a changed world: set computed_for.world_sha256 in every step's config, then run
each step; when it refuses with 'built X, config expects Y', put X in place of Y and run again."""
import hashlib, json, re, subprocess, sys
from pathlib import Path
clone = Path(sys.argv[1]).resolve(); raw = Path(sys.argv[2]).resolve()
new = hashlib.sha256((clone / "config/world.json").read_bytes()).hexdigest()
old = "d2607d1362f3c7ec26b7e00c38d873b36d29db83aa169eebf60e0dd6f299509b"
for name in ("terrain", "buildings", "photo", "roofs", "surfaces", "trees"):
    p = clone / "config" / f"{name}.json"
    t = p.read_text()
    assert t.count(old) == 1, name
    p.write_text(t.replace(old, new))
print("world sha", new)
def run(step):
    extra = [] if step == "manifest" else ["--raw", str(raw)]
    r = subprocess.run(["uv", "run", "--project", "pipeline", "python", "-m", "mattini", step, *extra], cwd=clone, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr
for step in ("terrain", "buildings", "photo", "roofs", "surfaces", "trees"):
    for attempt in range(14):
        rc, out = run(step)
        if rc == 0:
            print(step, "ok after", attempt, "corrections"); break
        sha = re.findall(r"\b([0-9a-f]{64})\b", out)
        cfg = (clone / "config" / f"{step}.json")
        m = re.search(r"mattini: error: (.*)", out)
        msg = m.group(1) if m else out[-400:]
        # the message names what was built and what the config expects: the first two 64-hex strings after 'SHA-256'
        pair = re.search(r"(?:SHA-256|give|has|have)[^0-9a-f]*([0-9a-f]{64}).*?expects ([0-9a-f]{64})", msg)
        if not pair:
            print(step, "REFUSED, no pair found:", msg[:600]); sys.exit(1)
        built, expected = pair.groups()
        t = cfg.read_text()
        assert t.count(expected) == 1, (step, expected, t.count(expected))
        cfg.write_text(t.replace(expected, built))
        print(f"{step}: replaced {expected[:8]}.. by {built[:8]}..  ({msg[:90]})")
    else:
        print(step, "did not converge"); sys.exit(1)
rc, out = run("manifest")
print("manifest", rc, out[-300:])
```

### F. The mutations' edits

One line per edit: the file, the exact text replaced (it occurred once) and its replacement.

- `PL-photo-ns-flip`: `pipeline/mattini/photo.py`: `grid[first:last] = _block_means(mosaic, k)` → `grid[first:last] = _block_means(mosaic, k)[::-1]`
- `PL-photo-ew-flip`: `pipeline/mattini/photo.py`: `mosaic[r0 - top : r1 - top, c0:c1] = part.transpose(1, 2, 0)` → `mosaic[r0 - top : r1 - top, c0:c1] = part.transpose(1, 2, 0)[:, ::-1]`
- `PL-photo-half-texel`: `pipeline/mattini/photo.py`: `mosaic[r0 - top : r1 - top, c0:c1] = part.transpose(1, 2, 0)` → `mosaic[r0 - top : r1 - top, c0:c1] = np.roll(part.transpose(1, 2, 0), 1, axis=1)`
- `PL-photo-box-swap`: `pipeline/mattini/photo.py`: `"lv95_box": {"e_max": e_max, "e_min": e_min, "n_max": n_max, "n_min": n_min},` → `"lv95_box": {"e_max": e_min, "e_min": e_max, "n_max": n_max, "n_min": n_min},`
- `PL-surf-centre`: `pipeline/mattini/surfaces.py`: `self.e0, self.n1, self.cell, self.half = e_min, n_max, cell, cell // 2` → `self.e0, self.n1, self.cell, self.half = e_min, n_max, cell, 0`
- `PL-surf-ns-flip`: `pipeline/mattini/surfaces.py`: `            _paint(grid, frame, code, *(np.concatenate(p) for p in zip(*spans[code], strict=True)))\n    return grid\n` → `            _paint(grid, frame, code, *(np.concatenate(p) for p in zip(*spans[code], strict=True)))\n    return grid[::-1]\n`
- `PL-surf-ew-flip`: `pipeline/mattini/surfaces.py`: `            _paint(grid, frame, code, *(np.concatenate(p) for p in zip(*spans[code], strict=True)))\n    return grid\n` → `            _paint(grid, frame, code, *(np.concatenate(p) for p in zip(*spans[code], strict=True)))\n    return grid[:, ::-1]\n`
- `PL-tree-centre-e`: `pipeline/mattini/trees.py`: `east = e_min + SOURCE_M / 2 + SOURCE_M * tj` → `east = e_min + SOURCE_M * tj`
- `PL-tree-centre-n`: `pipeline/mattini/trees.py`: `north = n_max - SOURCE_M / 2 - SOURCE_M * ti` → `north = n_max - SOURCE_M * ti`
- `PL-tree-base-corner`: `pipeline/mattini/trees.py`: `        + terrain[ti + 1, tj + 1]\n` → `        + terrain[ti, tj]\n`
- `PL-tree-offset`: `pipeline/mattini/trees.py`: `terrain = resample(dtm, box, SOURCE_M, world.height_offset)  # the 0.5 m terrain grid` → `terrain = resample(dtm, box, SOURCE_M, 0.0)  # the 0.5 m terrain grid`
- `PL-tree-axes`: `pipeline/mattini/trees.py`: `local = [world.to_local(e, n, 0.0) for e, n in zip(east.tolist(), north.tolist(), strict=True)]` → `local = [world.to_local(n, e, 0.0) for e, n in zip(east.tolist(), north.tolist(), strict=True)]`
- `PL-tree-tile-swap`: `pipeline/mattini/trees.py`: `chunks.append({"tile": f"{e_km}-{n_km}", "trees": len(chosen), "data": chosen.tobytes()})` → `chunks.append({"tile": f"{n_km}-{e_km}", "trees": len(chosen), "data": chosen.tobytes()})`
- `PL-tree-mosaic`: `pipeline/mattini/trees.py`: `c0 = round((west + j0 * SOURCE_M - e_min) / SOURCE_M)` → `c0 = round((west + j0 * SOURCE_M - e_min) / SOURCE_M) + 1`
- `PL-roofs-centre-e`: `pipeline/mattini/roofs.py`: `"east0 = west_dm * PIXEL_UNITS + HALF_PIXEL_UNITS  # E of column 0's centre"` → `"east0 = west_dm * PIXEL_UNITS  # E of column 0's centre"`
- `PL-roofs-centre-n`: `pipeline/mattini/roofs.py`: `"north0 = north_dm * PIXEL_UNITS - HALF_PIXEL_UNITS  # N of row 0's centre"` → `"north0 = north_dm * PIXEL_UNITS  # N of row 0's centre"`
- `PL-roofs-order-off-by-one`: `pipeline/mattini/roofs.py`: `"roof": _lower_median(counts[number], int(pixels[number])),\n                "roof_pixels": int(pixels[number]),` → `"roof": _lower_median(counts[number - 1], int(pixels[number - 1])),\n                "roof_pixels": int(pixels[number - 1]),`
- `PL-roofs-sort`: `pipeline/mattini/roofs.py`: `return sorted(buildings, key=lambda building: (building["tile"], building["uuid"]))` → `return sorted(buildings, key=lambda building: (building["tile"], building["uuid"][::-1]))`
- `PL-world-offset`: `pipeline/mattini/world.py`: `float(h) - self.height_offset)` → `float(h))`
- `PL-world-sign`: `pipeline/mattini/world.py`: `x, y, z = (sign * source[index] for sign, index in self.mapping)` → `x, y, z = (source[index] for sign, index in self.mapping)`
- `GM-photo-sw-origin`: `game/scripts/terrain/photo_grid.gd`: `var north_west := world.to_local(box["e_min"], box["n_max"], world.height_offset)` → `var north_west := world.to_local(box["e_min"], box["n_min"], world.height_offset)`
- `GM-photo-ne-origin`: `game/scripts/terrain/photo_grid.gd`: `var north_west := world.to_local(box["e_min"], box["n_max"], world.height_offset)` → `var north_west := world.to_local(box["e_max"], box["n_max"], world.height_offset)`
- `GM-photo-rect-swap`: `game/scripts/terrain/photo_grid.gd`: `return Vector4(x0, z0, width_m, depth_m)` → `return Vector4(x0, z0, depth_m, width_m)`
- `GM-surf-class-at-round`: `game/scripts/terrain/surface_grid.gd`: `var column := floori((x - x0) / cell_m)` → `var column := roundi((x - x0) / cell_m)`
- `GM-surf-rect-shift`: `game/scripts/terrain/terrain_loader.gd`: `material.set_shader_param("surfaces_rect", surfaces.rect())` → `material.set_shader_param("surfaces_rect", surfaces.rect() + Vector4(0.1, 0.0, 0.0, 0.0))`
- `GM-tree-read-yz`: `game/scripts/trees/tree_chunks.gd`: `positions[k] = Vector3(values[at], values[at + 1], values[at + 2])` → `positions[k] = Vector3(values[at], values[at + 2], values[at + 1])`
- `GM-tree-buffer-z`: `game/scripts/trees/tree_loader.gd`: `buffer.append(at.z)` → `buffer.append(-at.z)`
- `GM-tree-cell`: `game/scripts/trees/tree_loader.gd`: `floori(at.z / CELL_M))` → `floori(-at.z / CELL_M))`
- `GM-main-trees-rect`: `game/scripts/main.gd`: `var rect := photo.rect() if photo != null else Vector4.ZERO` → `var rect := Vector4(photo.rect().y, photo.rect().x, photo.rect().z, photo.rect().w) if photo != null else Vector4.ZERO`
- `GM-main-trees-offset`: `game/scripts/main.gd`: `\tmove_child(TreeLoader.create(chunks, self, texture, rect), _ui.get_index())` → `\tvar trees_node := TreeLoader.create(chunks, self, texture, rect)\n\ttrees_node.position = Vector3(1000.0, 0.0, 0.0)\n\tmove_child(trees_node, _ui.get_index())`
- `GM-main-terrain-photo-rect`: `game/scripts/terrain/terrain_loader.gd`: `material.set_shader_param("photo_rect", photo.rect())` → `material.set_shader_param("photo_rect", photo.rect() if surfaces == null else surfaces.rect())`
- `GM-roofs-shift`: `game/scripts/buildings/building_loader.gd`: `\tvar colours := []\n\tfor building: Dictionary in buildings:\n\t\tvar roof: Variant = building["roof"]\n\t\tfor k in building["triangles"]:\n\t\t\tcolours.append(roof)\n\treturn colours` → `\tvar colours := []\n\tvar previous: Variant = null\n\tfor building: Dictionary in buildings:\n\t\tvar roof: Variant = previous\n\t\tprevious = building["roof"]\n\t\tfor k in building["triangles"]:\n\t\t\tcolours.append(roof)\n\treturn colours`
- `GM-world-offset`: `game/scripts/world/world_config.gd`: `var source := PackedFloat64Array([e - origin_e, n - origin_n, h - height_offset])` → `var source := PackedFloat64Array([e - origin_e, n - origin_n, h])`
- `GM-world-z-sign`: `game/scripts/world/world_config.gd`: `_sign[2] * source[_source_index[2]],\n\t)\n\n\n## Godot local` → `source[_source_index[2]],\n\t)\n\n\n## Godot local`
- `SH-photo-uv-wz`: `game/shaders/terrain_photo.gdshader`: `vec2 puv = (v_vertex.xz - photo_rect.xy) / photo_rect.zw;` → `vec2 puv = (v_vertex.xz - photo_rect.xy) / photo_rect.wz;`
- `SH-photo-uv-flip`: `game/shaders/terrain_photo.gdshader`: `vec2 puv = (v_vertex.xz - photo_rect.xy) / photo_rect.zw;\n` → `vec2 puv = (v_vertex.xz - photo_rect.xy) / photo_rect.zw;\n\tpuv.y = 1.0 - puv.y;\n`
- `SH-photo-uv-shift`: `game/shaders/terrain_photo.gdshader`: `vec2 puv = (v_vertex.xz - photo_rect.xy) / photo_rect.zw;\n` → `vec2 puv = (v_vertex.xz - photo_rect.xy) / photo_rect.zw;\n\tpuv.x -= 0.1 / photo_rect.z;\n`
- `SH-class-half-texel`: `game/shaders/terrain_photo.gdshader`: `vec2 t = (xz - surfaces_rect.xy) / surfaces_rect.zw * vec2(size) - 0.5;` → `vec2 t = (xz - surfaces_rect.xy) / surfaces_rect.zw * vec2(size);`
- `SH-class-ns-flip`: `game/shaders/terrain_photo.gdshader`: `int c = int(texelFetch(surfaces, p, 0).r * 255.0 + 0.5);` → `int c = int(texelFetch(surfaces, ivec2(p.x, size.y - 1 - p.y), 0).r * 255.0 + 0.5);`
- `SH-tree-uv-zx`: `game/shaders/tree_conifer.gdshader`: `vec2 uv = (origin.xz - photo_rect.xy) / photo_rect.zw;` → `vec2 uv = (origin.zx - photo_rect.xy) / photo_rect.zw;`
- `GM-main-root-offset`: `game/main.tscn`: `[node name="Main" type="Node3D"]\nscript = ExtResource("1_main")` → `[node name="Main" type="Node3D"]\ntransform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 1000, 0, 0)\nscript = ExtResource("1_main")`
- `GM-surf-texture-flip`: `game/scripts/terrain/surface_grid.gd`: `texture = ImageTexture.create_from_image(image)` → `image.flip_y()\n\ttexture = ImageTexture.create_from_image(image)`
- `GM-photo-texture-flip`: `game/scripts/terrain/photo_grid.gd`: `image.generate_mipmaps()` → `image.flip_y()\n\timage.generate_mipmaps()`
- `GM-photo-x0-half-texel`: `game/scripts/terrain/photo_grid.gd`: `\tx0 = north_west.x\n` → `\tx0 = north_west.x + 0.1\n`
- `GM-photo-z0-half-texel`: `game/scripts/terrain/photo_grid.gd`: `\tz0 = north_west.z\n` → `\tz0 = north_west.z + 0.1\n`
- `GM-surf-x0-half-texel`: `game/scripts/terrain/surface_grid.gd`: `\tx0 = north_west.x\n` → `\tx0 = north_west.x + 0.1\n`
- `GM-surf-z0-half-texel`: `game/scripts/terrain/surface_grid.gd`: `\tz0 = north_west.z\n` → `\tz0 = north_west.z + 0.1\n`
- `GM-tree-cell-int`: `game/scripts/trees/tree_loader.gd`: `var key := Vector2i(floori(at.x / CELL_M), floori(at.z / CELL_M))` → `var key := Vector2i(int(at.x / CELL_M), int(at.z / CELL_M))`
- `PL-world-origin-swap`: `pipeline/mattini/world.py`: `source = (float(e) - self.origin_e, float(n) - self.origin_n, float(h) - self.height_offset)` → `source = (float(e) - self.origin_n, float(n) - self.origin_e, float(h) - self.height_offset)`
- `GM-world-origin-swap`: `game/scripts/world/world_config.gd`: `var source := PackedFloat64Array([e - origin_e, n - origin_n, h - height_offset])` → `var source := PackedFloat64Array([e - origin_n, n - origin_e, h - height_offset])`
- `PL-buildings-sort`: `pipeline/mattini/buildings.py`: `buildings = sorted(buildings, key=lambda building: building[0])` → `buildings = sorted(buildings, key=lambda building: building[0][::-1])`
- `PL-tree-transpose`: `pipeline/mattini/trees.py`: `terrain[ti, tj].astype(np.float64)\n        + terrain[ti, tj + 1]\n        + terrain[ti + 1, tj]\n        + terrain[ti + 1, tj + 1]` → `terrain[tj, ti].astype(np.float64)\n        + terrain[tj + 1, ti]\n        + terrain[tj, ti + 1]\n        + terrain[tj + 1, ti + 1]`
