# Brief: M3-12 — Roof colours and walls in the game
Status: DONE (fb30619)

Written in the design realm; executed by one fresh builder session under
`docs/roles/BUILD.md`. Lane G of wave 1 (`docs/briefs/M3-plan.md`).

## Goal

The buildings stop being a white model.
- **Roofs:** each roof is drawn in the colour the 2023 photo gives it. A new reader,
  `BuildingRoofs`, reads the manifest's `roofs` block and checks it against the building
  chunks; `BuildingLoader` puts each building's colour on its own roof triangles.
- **Walls:** every wall becomes one neutral plaster. This is the owner's choice and a
  labelled placeholder, since no open data shows façades.
- **The look test:** it reads what each building node actually draws (M2's V1-G-04).

The main scene uses this from M3-14 on; this brief gives the reader and the loader's new
parameter.

## Read first, in order

1. `CLAUDE.md` (Hard Rules 2, 4); `brain.md` H16.
2. `docs/SPEC.md` §8 *The buildings* (the game) and *Roof colours* (the file and the game),
   §10 (M3's game), §13 row 31.
3. `game/scripts/buildings/building_chunks.gd`, `building_loader.gd`,
   `game/materials/building_walls.tres`, `building_roofs.tres`,
   `game/tests/test_building_*.gd`, `game/scripts/terrain/terrain_grid.gd` (the reader
   pattern).
4. `tests/shared/roofs_fixture/` and `tests/shared/roofs_vectors.json` (design data).
5. The pinned tests: `docs/briefs/pinning/M3-12/`.

## Decisions already made

1. **`BuildingRoofs`** (`game/scripts/buildings/building_roofs.gd`, `class_name
   BuildingRoofs`, `extends RefCounted`).
   - **Constructor:** `static func from_manifest(path: String, world: WorldConfig, chunks:
     BuildingChunks) -> BuildingRoofs`. On a refusal it returns null after one
     `push_error("BuildingRoofs: <path>: <problem>")`.
   - **Properties:** `area`, `dataset` (`swissimage`), `edition` (`2023`), `attribution`, and
     `chunks`: an Array of {tile, buildings: [{uuid, triangles, vertices, roof: Color or
     null}]} in BuildingChunks' order.
   - **It refuses** (P = pinned):
     - no block, naming `python -m mattini roofs` (P);
     - key sets that are not exact;
     - a `world_sha256` other than the manifest's (P), or a WorldConfig not the manifest's;
     - the format and the area;
     - chunks that are not BuildingChunks' chunks in order (P);
     - per chunk, the building count; and the sums of triangles (P) and of vertices (P),
       naming the tile;
     - UUIDs that do not ascend;
     - a building whose triangles index vertices outside its own range (P; the sums alone
       would accept counts moved between two buildings, colouring the wrong one);
     - a `roof` that is neither `rrggbb` nor null, or null when `roof_pixels` is not 0;
     - a block whose `source.buildings` differs from the manifest's `buildings.source`.
       The block is the data itself, embedded in the manifest, so there is no file
       SHA-256 to check.
2. **`BuildingLoader.create(chunks, parent, roofs: BuildingRoofs = null) -> Node3D`.**
   - Without roofs it draws M2's look with the new walls.
   - With roofs, each roof triangle (the game's own rule, normal.y ≥ 0.5; measured to agree
     with the pipeline's exact rule on all 178'910 village triangles) of a building with a
     colour carries that colour as its vertex colour, under a material with
     `vertex_color_use_as_albedo = true` and `vertex_color_is_srgb = true` (P: the photo's
     bytes are sRGB; read as linear the roofs wash out) and white albedo.
   - Roof triangles of a building with no colour use `res://materials/building_roofs.tres`
     (P).
   - Every wall uses `res://materials/building_walls.tres`, now albedo (0.78, 0.76, 0.72)
     and roughness 0.9 (P; the owner's "neutral", SPEC §13 row 31).
   - No `material_override` and no surface override material on any node (P, V1-G-04).
3. **The placeholder label.** Godot drops a comment from a `.tres` when the editor re-saves
   it. So the label lives in BuildingLoader's doc comment and in a constant the credits will
   read (M3-14), with this text: "Walls: one neutral plaster colour, a placeholder: no open
   data shows the façades." On one line it is 104 characters, over gdlint's 100, and gdformat
   joins a bracketed single string back onto one line. Measured clean with both: two joined
   strings in brackets, on three lines: `const WALLS_NOTE := (`, then
   `"Walls: one neutral plaster colour, a placeholder:" + " no open data shows the façades."`
   (indented), then `)`. The pinned `test_building_materials.gd` checks the text.
4. **The surfaces** may be named as you choose (the pinned tests find triangles by their
   vertices). For example "walls", "roofs" and "roofs_photo" with a new
   `res://materials/building_roofs_photo.tres`.
5. **The gate:** one scoped allowlist line, for the refusal tests' deliberate errors:
   `BuildingRoofs: user://test_ @ res://tests/test_building_roofs.gd # its refusal tests write broken manifests under user://test_building_roofs on purpose (brief M3-12)`.
   This is wave 1's one shared file (the plan's integration notes): append your line at the
   end of `tools/gate_allowlist.txt`. If a rebase brings other lanes' lines, keep every
   line, re-run the gate and record it.
6. **Measured with design's throwaway on the real village:** BuildingRoofs 0.07 s; the
   loader 0.10 s with roofs; 32'452 roof triangles with vertex colours, 146'458 wall
   triangles.

## Scope — files you may touch

- `game/scripts/buildings/building_roofs.gd` and its `.uid` (new);
  `game/scripts/buildings/building_loader.gd`.
- `game/materials/building_walls.tres` (the plaster) and a new roofs material if you add
  one. `building_roofs.tres` stays as it is: it is the fallback.
- `game/tests/`: the pinned `test_building_roofs.gd` and `test_building_roof_colours.gd`
  (new, with `.uid`) and `test_building_materials.gd` (replaces M2-08's live file), plus your
  own new tests.
- `tools/gate_allowlist.txt`: the one appended line.

## Depends on

None in this wave. It reads design's roofs fixture, not the pipeline's step (M3-05 lands in
lane C at the same time; they meet at the fixture).

## Done when (gates)

- [ ] The pinned copies are in place (`cp -r docs/briefs/pinning/M3-12/. .`) and stay
      byte-identical (`cmp`).
      - does NOT prove: that they are the right tests.
- [ ] Mutations, each failing a named pinned test, recorded:
      - colours ignored;
      - colours applied in reversed building order;
      - `vertex_color_is_srgb` off;
      - M2's walls kept;
      - an unshaded `material_override`;
      - the reader without the vertex-range check.
      - does NOT prove: that the colours look right.
- [ ] Optional: a software screenshot of the fixture's buildings, or of the real village if
      you build it in scratch, committed under `docs/briefs/shots/M3-12-*.jpg` and named in
      Findings. It is evidence, not a gate. `tools/shot.sh` renders
      the main scene, which draws the new walls at once but the roof colours only from M3-14: render with a throwaway
      scene kept in scratch (never committed), or skip the shots and say so in Findings.
      - does NOT prove: the Forward+ look on the owner's GPU.
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that it renders or looks right.

## Forbidden

- Touching `main.gd` or `main.tscn` (M3-14); changing BuildingChunks' checks or the chunk
  format.
- Changing the roof fallback colour; a texture on the walls.
- Editing a pinned file or the fixture.

## Findings (executor writes)

1. **Pinned copies.** `cp -r docs/briefs/pinning/M3-12/. .` done first; `cmp` of `test_building_roofs.gd`, `test_building_roof_colours.gd` and `test_building_materials.gd` against `docs/briefs/pinning/M3-12/game/tests/` is identical at the commit. They passed on the first run against the first implementation (42 of 42 with the M2 building tests).
2. **Built.** `BuildingRoofs` (`building_roofs.gd`, `from_manifest` as the brief writes it, plus `_read`, which returns the problem as text), `BuildingLoader.create(chunks, parent, roofs = null)` with the surfaces "walls", "roofs" and "roofs_photo", the new `building_roofs_photo.tres` (white albedo, vertex colour as albedo, `vertex_color_is_srgb`), `building_walls.tres` now (0.78, 0.76, 0.72) at roughness 0.9, and `BuildingLoader.WALLS_NOTE` with the brief's text. `building_roofs.tres` is untouched. `main.gd`, `main.tscn` and BuildingChunks are untouched: the main scene still calls `create(chunks, self)` and so draws the new walls and M2's neutral roofs until M3-14.
3. **Mutations** (the six the brief names, plus five of my own; each run mutates one thing, runs the six building test scripts, and the file is put back afterwards; the harm is what the owner would see):

   | Mutation | Harm | Fails (named test) |
   |---|---|---|
   | colours ignored (`create` never passes them on) | every roof the neutral grey | `test_building_roof_colours.gd`: `test_the_named_triangles_are_drawn_as_the_pipeline_says`, `test_every_triangle_is_drawn_by_its_building_s_colour` |
   | colours applied in reversed building order | each roof wears another building's colour | the same two |
   | `vertex_color_is_srgb` off | roofs washed out on the owner's PC | the same two |
   | M2's walls kept | the white model again | `test_building_materials.gd`: `test_the_walls_are_the_plaster_placeholder`; and the same two of the colours test |
   | an unshaded `material_override` | flat, unlit buildings | `test_building_materials.gd`: `test_nothing_overrides_what_the_meshes_draw`, `test_every_surface_is_lit_culled_opaque_and_untextured`; `test_building_roof_colours.gd`: `test_nothing_overrides_what_the_meshes_draw` |
   | the reader without the vertex-range check | counts moved between two buildings colour another building's roof | `test_building_roofs.gd`: `test_counts_moved_between_two_buildings_are_refused` |
   | no uuid order check (own) | a block with its buildings out of order read | `test_m3_12_roofs_checks.gd`: `test_the_uuids_must_ascend` |
   | any text as a colour (own) | a colour that is not a photo byte triple read | `test_a_roof_is_a_lower_case_rrggbb_or_null` |
   | no `source.buildings` check (own) | colours measured on other buildings read | `test_the_buildings_source_must_be_the_manifests` |
   | a null roof with photo pixels read (own) | a roof the photo did cover left grey | `test_a_null_roof_and_the_photo_pixels_must_agree` |
   | no sums check (own) | a building short of its triangles read | `test_the_sums_must_be_the_chunk_files` |

   The last row found a gap: with the sums check removed, no pinned test failed. The pinned sums cases add a triangle or take a vertex away from the last building, which the vertex-range check refuses first. A building with one triangle too few, or one vertex too many, keeps every index inside its range and only the sums tell, so `test_m3_12_roofs_checks.gd` has both cases. The mutation runs' logs are not committed.
4. **Refusals beyond the brief's list** (stricter, nothing the pipeline writes): a non-null `roof` with `roof_pixels` 0 is refused as well as a null one with pixels (SPEC: "null when n = 0"); a colour must be six lower-case hex digits with no sign (`String.is_valid_hex_number` accepts a sign, so the check reads the digits); `lv95_box` must be an object but is not compared with the buildings' (no brief line asks for it; BuildingChunks does not keep the box). UUIDs must ascend strictly within a chunk, not across chunks (the fixture's chunks restart).
5. **`BuildingLoader.roofs_problem(chunks, roofs)`** is an addition: `create` takes the two objects separately, so a caller could pass colours of other chunks. It returns the first difference as text (the tiles in order, and per chunk the sum of the buildings' triangles), and `create` refuses with one `push_error("BuildingLoader: the roof colours do not fit the buildings: …")` and draws without colours. `roofs_problem` is tested (`test_m3_12_loader.gd`); the `push_error` branch of `create` is not, because the Scope allows exactly one allowlist line and a test that provokes that error needs its own. Said out loud rather than allowlisted.
6. **Allowlist.** The one line is appended at the end of `tools/gate_allowlist.txt`, exactly as decision 5 writes it. My refusal checks beyond the pinned file call `_read`, which returns text and prints nothing, so they need no line.
7. **Not measured.** The container holds no village data, so BuildingRoofs' and the loader's times on the real 1'486 buildings (design: 0.07 s and 0.10 s) are not re-measured here; the vertex-range check reads each building's indices through a native sort, and the loader makes one colour list per chunk. The fixture runs in milliseconds. No software screenshot: the main scene draws roof colours only from M3-14 (plan hint), and a throwaway scene was not built.
8. **Whole-directory GUT runs without the generated manifest.** A run of `-gdir=res://tests` before `python -m mattini manifest` has written `game/assets/generated/manifest.json` fails twelve `test_world_config*` tests in every run, mutated or not; the gate writes the manifest first. Not a finding about this brief; named so nobody reads those twelve lines in the mutation logs as caused by a mutation.
9. **Staging.** `pipeline/tests/test_repo_tracked.py` fails the gate while new files are untracked: stage them (`git add`) before the gate.
10. **The gate** (`tools/gate.sh`, exit 0 on the tree of the landing commit; origin/main had not moved, so the rebase brought nothing in and no second run was needed): GUT 27 scripts, 139 tests, 4463 asserts, all passed; pytest 742 passed, 4 deselected (a first run failed only `test_repo_tracked` until the new files were staged). Does NOT prove: that anything renders or looks right; the owner's PC is the check.
