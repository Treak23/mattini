# Brief: M4-07 — The far mountains in the game
Status: OPEN

Written in the design realm; executed by one fresh builder session under
`docs/roles/BUILD.md`. Lane G of wave 1 (m4-design §7; the arc plan names the waves).

## Goal

The mountains around the area can cast their shadows into the village, so the sun rises and
sets behind the real horizon (m4-design §0 *Horizon*: with the 2 × 3 km box alone the times are
off by 11 to 62 minutes).

- **The reader:** `SurroundingsGrid` reads the manifest's `surroundings` block and its heights
  file, checks them, and places the grid through the world config.
- **The loader:** `SurroundingsLoader` builds one mesh of the grid that only casts shadows:
  nothing of it is drawn (the far mountains are drawn in M5). The squares where the real
  terrain is (the cut, NaN) get no triangles.

The main scene uses both from M4-10 on.

## Read first, in order

1. `CLAUDE.md` (Hard Rules 2, 4); `brain.md` H3, H5, H8, H9, H16, H26.
2. `docs/briefs/sketches/m4-design.md` §0 *Far mountains in Godot*, §2 (the grid and its file),
   §7 (this brief), §9 (how M4-10 uses it).
3. `docs/briefs/M4-02-the-surroundings-step.md` decisions 1, 6 and 9: the file, its
   description, the fixture.
4. `game/scripts/terrain/terrain_grid.gd` and `surface_grid.gd` (the reader pattern: the world
   check, the block's key set, the file checks), `game/scripts/trees/tree_chunks.gd`
   (`_check_world`: BuildingChunks' check plus the owner's axes),
   `game/scripts/world/world_config.gd`, `game/scripts/world/manifest_value.gd`.
5. `tests/shared/surroundings_fixture/generated/` (the manifest, the description and the
   heights), `tests/shared/surroundings_vectors.json` (design data).
6. The pinned tests: `docs/briefs/pinning/M4-07/`.

## Decisions already made

1. **`SurroundingsGrid`** (`game/scripts/terrain/surroundings_grid.gd`, `class_name
   SurroundingsGrid`, `extends RefCounted`).
   - **Constructor:** `static func from_manifest(path: String, world: WorldConfig) ->
     SurroundingsGrid`. On every problem it returns null after one
     `push_error("SurroundingsGrid: <path>: <problem>")`, as every reader does.
   - **Properties:** `area`; `columns`, `rows` (int); `spacing_m` (float); `x_min`, `z_min`:
     the local x of column 0 and z of row 0, `WorldConfig.to_local` of the box's north-west
     corner (e_min, n_max), never an origin subtracted here; `heights`: the file's
     `PackedFloat32Array`, row-major, rows north to south, NaN in the cut; `cut_box`: the
     block's `cut_box` as {e_max, e_min, n_max, n_min} floats (M5 and M4-10 may use it);
     `dataset` ("swissaltiregio"), `edition`, `attribution` (the block's source).
   - **`func height(column: int, row: int) -> float`:** `heights[row * columns + column]`.
   - **It refuses, in this order:**
     - no WorldConfig; a manifest that cannot be read or is not a JSON object;
     - a null block: "no surroundings have been built: run python -m mattini download regio,
       then python -m mattini surroundings"; a block that is not an object;
     - a `world_sha256` that is not text or not the manifest's, naming `python -m mattini
       surroundings`;
     - a WorldConfig not read from this manifest (origin or height offset), or axes other than
       the owner's (x = +e, y = +h, z = −n): reuse `BuildingChunks._check_world` and add the
       axes, as `TreeChunks._check_world` does, with this reader's own wording (never "the
       surfaces need …");
     - a key set other than exactly {area, columns, cut_box, file, format, lv95_box, rows,
       sha256, source, spacing_m, world_sha256}; a `source` other than exactly {attribution,
       collection, dataset, edition, entry_sha256}, its dataset not "swissaltiregio", its texts
       empty; `lv95_box` and `cut_box` other than exactly {e_max, e_min, n_max, n_min} of
       finite numbers;
     - an area that is not a name; a format other than "f32-le"; a `spacing_m` that is not a
       positive finite number; `columns` or `rows` not a whole number of at least 2; a
       `sha256` not 64 hex digits;
     - columns and rows that do not fit `lv95_box` at `spacing_m`, computed in 64 bits from
       the box: (e_max − e_min) / s + 1 and (n_max − n_min) / s + 1;
     - a `cut_box` not inside `lv95_box`;
     - a file path that is not plain and relative (TerrainGrid's rule); a missing file
       (checked before any read, so no engine ERROR is printed); a size other than
       columns × rows × 4; another SHA-256. These three end "; python -m mattini surroundings
       rebuilds it" (decision 4).
   - Every value read from the manifest is compared through `ManifestValue.differs` or a type
     check first (H26: `!=` across types is a runtime error that lets the block through).
   - It does not look at the heights' values: the SHA-256 ties them to the step, which wrote
     NaN exactly in the cut (M4-02 decision 1).
2. **`SurroundingsLoader.create(grid: SurroundingsGrid, parent: Node) -> MeshInstance3D`**
   (`game/scripts/terrain/surroundings_loader.gd`, `class_name SurroundingsLoader`, `extends
   RefCounted`, static).
   - A MeshInstance3D named "Surroundings", added to `parent` and returned; its transform the
     identity: unturned, unscaled, at the scene's origin (the parent too, in M4-10: the main
     scene's root is).
   - `cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_SHADOWS_ONLY`: it casts and draws
     nothing. No material is needed.
   - Its mesh: an `ArrayMesh` of one `PRIMITIVE_TRIANGLES` surface, `ARRAY_VERTEX` and
     `ARRAY_INDEX`.
     - Only finite vertices go in the vertex array: a NaN vertex would make the mesh's AABB NaN.
     - For each grid square whose four corners are finite, two triangles of those four corners
       sharing a diagonal; a square with a NaN corner has none.
     - Front faces up: clockwise seen from above (H16). With a the north-west, b the
       north-east, c the south-west and d the south-east corner, (a, b, c) and (b, d, c) are
       design's throwaway's; the other diagonal is the builder's choice.
   - The vertex of column c, row r: `Vector3(x_min + c·s, height, z_min + r·s)`, the sums in
     GDScript's 64-bit float and narrowed once (H5); y exactly the grid's height.
   - No normals, no collision, no visibility range: a shadow caster needs none, and Godot keeps
     casters towards the light (m4-design §0). Not pinned; do not add what M5 decides.
3. **The fixture's manifest** (`tests/shared/surroundings_fixture/generated/manifest.json`,
   design data committed with this brief, SHA-256 `a42c5a91…`): the M4 top level (M3's keys
   plus `shadows`, `sky` and `surroundings`), `surroundings` the step's description verbatim,
   `world` the fixture's world.json, every other block null. The pinned
   `test_m4_07_surroundings_manifest.py` checks it against the fixture's files. M4-09 owns the
   manifest's writer and may rewrite this file's other blocks; the game reads only `world`,
   `world_sha256` and `surroundings`.
4. **The rebuild hint stays the pipeline's here.** M4-08 adds `ReleaseBuild.file_hint` in the
   same wave; this brief cannot depend on it. M4-08's census names `surroundings_grid.gd` as
   its one exception, and M4-10 moves the three file messages onto the seam.
5. **The trap world** (pinned, H5): the loader's test writes the fixture with its origin moved
   to E 2'618'250.13 / N 1'101'750.44, which float32 holds only as 2'618'250.25 / 1'101'750.5,
   so a 32-bit subtraction puts every vertex 0.12 m east and 0.06 m south; the test's tolerance
   is 1 mm.
6. **The gate:** one scoped allowlist line, appended at the end of `tools/gate_allowlist.txt`:
   `SurroundingsGrid: user://test_ @ res://tests/test_m4_07_surroundings_grid.gd # its refusal tests write broken manifests under user://test_m4_07_surroundings_grid on purpose (brief M4-07)`.
   M4-08 does not touch this file in wave 1.
7. **Measured with design's throwaway** (headless, a synthetic grid of the village's size,
   421 × 431 with 551 NaN; not the real file, which is 725'804 bytes): `create` 187 to 248 ms
   (three runs) for 180'900 vertices and 360'000 triangles. GPU cost: m4-design §0 (software
   only, +40–60 % frame time on llvmpipe); the owner's PC is the measure.

## Scope — files you may touch

- `game/scripts/terrain/surroundings_grid.gd`, `surroundings_loader.gd` and their `.uid` (new);
- `game/tests/`: the pinned `test_m4_07_surroundings_grid.gd`, `test_m4_07_surroundings_loader.gd`
  (new, with `.uid`), and your own new `test_m4_07_*.gd`;
- `pipeline/tests/test_m4_07_surroundings_manifest.py` (pinned, new);
- `tools/gate_allowlist.txt` (the one appended line).

Read-only: everything else, the fixture (its manifest included) and the vectors. Not
`main.gd`, `main.tscn`, `terrain_loader.gd`, `terrain_photo.gdshader`, any sky file,
`game/project.godot` or `release_build.gd` (M4-08's in this wave).

## Depends on

None at build time. It reads design's surroundings fixture (committed with the plan), not
the pipeline step: M4-02 (lane B, same wave) meets it at the fixture, whose bytes M4-02's
pinned tests compare with what the step writes.

## Done when (gates)

- [ ] The pinned copies are in place (`cp -r docs/briefs/pinning/M4-07/. .`) and stay
      byte-identical (`cmp`).
      - does NOT prove: that they are the right tests.
- [ ] Mutations, each failing a named pinned test, recorded with the owner-visible harm each
      reproduces (the shadow of a mountain in the wrong place, or no far shadow at all).
      Design's throwaway failed the named tests:
      - rows flipped in the loader (row r at the south): `test_m4_07_surroundings_loader.gd`
        `test_every_vertex_stands_where_the_world_config_puts_it_at_its_height`,
        `test_every_named_vertex_is_in_the_mesh_or_in_the_cut`, `test_every_front_faces_up`;
      - rows flipped in the reader (z_min from n_min): `test_m4_07_surroundings_grid.gd`
        `test_the_fixture_grid_is_read_as_designed` and four loader tests;
      - x and z swapped: the loader's `test_two_triangles_per_finite_square_and_none_in_the_cut`
        and four more;
      - the cut ignored (NaN vertices turned into triangles):
        `test_two_triangles_per_finite_square_and_none_in_the_cut` ("no vertex of the mesh is
        NaN"), `test_every_named_vertex_is_in_the_mesh_or_in_the_cut`;
      - every vertex half a spacing east: `test_every_vertex_stands_where_…`,
        `test_the_trap_world_is_placed_in_64_bits` and two more;
      - a 32-bit subtraction (`Vector3(e, 0, n) − Vector3(origin)` in the reader):
        `test_the_trap_world_is_placed_in_64_bits` alone (the fixture's own origin is exact in
        float32, so only the trap shows it: lesson 34);
      - the winding reversed: `test_every_front_faces_up`;
      - casting visibly (`SHADOW_CASTING_SETTING_ON`):
        `test_the_node_casts_shadows_only_and_is_unturned_at_the_origin`;
      - one triangle per square: `test_two_triangles_per_finite_square_and_none_in_the_cut`;
      - the node turned: `test_the_node_casts_shadows_only_and_is_unturned_at_the_origin`;
      - `!=` instead of the guarded compare on `world_sha256`:
        `test_a_world_sha256_of_another_type_is_refused`;
      - no size check, no SHA-256 check, no fit check, no dataset check, no world check, no
        cut-box check: `test_a_file_of_another_size_is_refused`, `test_a_damaged_file_is_refused`,
        `test_columns_…`/`test_rows_that_do_not_fit_the_box_are_refused`,
        `test_another_dataset_is_refused`, `test_a_rotated_world_is_refused` and
        `test_a_world_config_of_another_manifest_is_refused`,
        `test_a_cut_box_outside_the_box_is_refused`.
      - does NOT prove: that Godot draws the shadows these triangles cast or that they land
        right in the village (no GPU; m4-design §0 measured it in Forward+ on lavapipe;
        Compatibility shows no far shadow; M4-10 wires it and the owner's PC is the test).
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: anything drawn, nor the real village's file (M4-10's main scene reads
        it headless; the owner's eyes).

## Forbidden

A visible mesh, a material, collision; touching the main scene, the terrain loader or the
shaders; reading the heights' values to "fix" them; an origin subtracted in the reader or the
loader; editing a pinned file, the fixture or the vectors.

## Findings (executor writes)
