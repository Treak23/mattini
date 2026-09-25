# Brief: M2-05 — The buildings in the game
Status: BLOCKED

Written in the design realm; executed under `docs/roles/BUILD.md` (in M2 by an Opus agent
of the one M2 session, the owner's word of 2026-09-25, `docs/history/RULINGS.md`).

## Goal

Starting the game shows the village's 1'486 buildings standing on the terrain, as a white
architectural model: flat-shaded, matte, with roofs a shade darker than walls, casting
shadows in the fixed sun. Every building stands where swisstopo puts it: the same world
config places them and the terrain, and a test ties a building's corners to their LV95
coordinates. The credits name swissBUILDINGS3D. When the buildings are missing, refused or
stale, the error panel says so and names the commands, and the terrain still shows.
`tools/export.sh` refuses an export without buildings and checks that the started build
loaded them.

## Read first, in order

1. `CLAUDE.md`; `brain.md` §7 H4, H11, H12, H15.
2. `docs/SPEC.md` §8 *The buildings* (the game part), §10 *M2's game* (the look), §12.
3. `game/scripts/main.gd`, `terrain/terrain_grid.gd` (the model for the reader),
   `terrain/terrain_loader.gd`, `game/tools/shot.gd`, `tools/export.sh` as M2-02 left them.
4. `tests/shared/buildings_fixture/` and `tests/shared/buildings_vectors.json`.
5. The pinning tests, `docs/briefs/pinning/M2-05/game/tests/`.

## Decisions already made

- **`BuildingChunks`** (`game/scripts/buildings/building_chunks.gd`, `class_name
  BuildingChunks`, `extends RefCounted`), the model being `TerrainGrid`:
  - `static func from_manifest(path: String, world: WorldConfig) -> BuildingChunks` reads
    the manifest's `buildings` block. It returns null after one `push_error` naming the
    path and the problem when anything is wrong:
    - no block: "no buildings have been built: run python -m mattini download buildings,
      then python -m mattini buildings";
    - `world_sha256` not the manifest's;
    - the WorldConfig not read from this manifest (origin differs);
    - `format` not `mesh-f32-u32-le`;
    - a malformed chunk entry;
    - a file that is not a plain relative path, is missing, or has the wrong size (12 ×
      vertices + 12 × triangles) or SHA-256;
    - an index out of range.
  - Fields: `area: String`, `dataset`, `edition`, `attribution`, and `chunks: Array` of
    `{"tile": String, "buildings": int, "positions": PackedVector3Array, "indices":
    PackedInt32Array}` in the block's order.
  - It never converts a coordinate. The pipeline wrote local coordinates for the world
    config pinned by `world_sha256`, and the check ties them together (Hard Rule 4).
- **`BuildingLoader`** (`game/scripts/buildings/building_loader.gd`):
  - `static func create(chunks: BuildingChunks, parent: Node) -> Node3D` adds a `Node3D`
    named `Buildings` to `parent`, with one `MeshInstance3D` per chunk named by its tile,
    and returns it.
  - Each mesh is an `ArrayMesh` with two surfaces, 0 walls and 1 roofs, flat-shaded: every
    triangle gets its own three vertices and its own normal, `normalize((b − a) × (c − a))`
    in the file's order, which points outward (SPEC §8).
  - A triangle whose normal has y ≥ 0.5 (a slope of 60° or less) is roof, the rest wall.
  - Godot draws clockwise triangles as front faces, so each triangle goes into the arrays
    as (a, c, b). The file's counter-clockwise order drawn as it is would show the inside
    of every building.
  - Shadows are cast (the default).
- **The look (design proposes, the owner reacts through `feedback`, SPEC §13 row 17):**
  - walls: `StandardMaterial3D` albedo `Color(0.93, 0.92, 0.89)`, roughness 1.0,
    metallic 0, specular 0.25;
  - roofs: the same with albedo `Color(0.76, 0.72, 0.68)`;
  - no textures, no per-building colours (nothing invented: M2 has no data for them),
    back faces culled.

  The materials are two `.tres` files under `game/materials/` (`building_walls.tres`,
  `building_roofs.tres`), so the owner can tune them in the editor.
- **main.gd:**
  - after the terrain, `BuildingChunks.from_manifest` and `BuildingLoader.create` add
    `Buildings` as a sibling of `Terrain`;
  - a refusal opens the error panel with the refusal and `BUILDINGS_FIX` (`uv run
    --project pipeline python -m mattini download buildings`, then `… python -m mattini
    buildings`), and the terrain stays;
  - when the terrain is refused too, the panel lists both refusals, each with its
    commands. The panel's first line names what cannot be shown: "the terrain", "the
    buildings" or "the terrain and the buildings";
  - a second startup line: `mattini <version>: buildings <area> loaded, <n> buildings in
    <k> chunks, <t> triangles`;
  - the credits' data section lists each loaded dataset on its own line, `<dataset>
    <edition>, <attribution>`: the terrain's first, then the buildings'.
- **The live main-scene tests:** the shared terrain fixture has no buildings (from M2-04
  its manifest says `"buildings": null`), so every earlier test that expects no error panel
  on it (`test_main_scene_terrain.gd`, `test_main_scene.gd`) composes a complete world
  the way the pinned `test_main_scene_buildings.gd` does: the terrain fixture plus a
  buildings block the test writes. A test that means "no buildings" says so.
- **tools/export.sh:**
  - step 1 also requires a `buildings` block;
  - step 6 also requires the buildings startup line with the manifest's building count;
  - `docs/RELEASE.md` §C gains the buildings' line (design edits it at the close).
- **Screenshots** (SPEC §12): with the real village built, `tools/shot.sh` views of the
  church square from 60 m, the start view, and one looking along the main street
  (Bahnhofstrasse, north to south). They are committed as
  `docs/briefs/shots/M2-05-<view>.jpg` and named in Findings.

## Scope: files you may touch

`game/scripts/buildings/` (new) · `game/scripts/main.gd` · `game/materials/` (new) ·
`game/main.tscn` (only if needed) · `game/tests/` · `game/tools/shot.gd` ·
`tools/export.sh` · `tools/shot.sh` · `tools/gate_allowlist.txt` (a scoped entry for a
test's deliberate refusals, `BuildingChunks: user://test_`, named in Findings) ·
`docs/briefs/shots/`.

## Depends on

M2-02 (main.gd, export.sh), M2-04 (the generated buildings and the manifest block).

## Done when (gates)

- [ ] The pinned copies are in place and byte-identical (`cmp`).
      - does NOT prove: that the pinned tests are the right tests.
- [ ] The seam: `test_building_chunks.gd` finds every named vertex of
      `buildings_vectors.json` at `WorldConfig.to_local` of its LV95 point, and
      `test_building_loader.gd` finds every roof normal pointing up and every triangle
      front-facing from outside (Godot's winding, checked against `SurfaceTool`'s own
      normals). Mutations (Findings: both runs):
      - the winding left as in the file;
      - x and z swapped when reading positions;
      - the roof threshold on the normal's x instead of y.
      - does NOT prove: that the buildings render or look right.
- [x] The main scene with the real village loads 1'486 buildings in six chunks (a headless
      run's startup lines, in Findings), and the software screenshots show buildings on
      the terrain.
      - does NOT prove: the Forward+ look on the owner's PC.
- [x] `tools/export.sh` passes with the real village and buildings, including its step 6.
      - does NOT prove: that the Windows build starts.
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that it renders or looks right.

## Forbidden

A version bump (the close does it); collision or walking (M6); per-building colours or
textures; a change to the fixture's bytes.

## Findings (executor writes)

Executor: an Opus agent of the one M2 session (arc M2's run mode, RULINGS 2026-09-25), in
its own worktree and branch `worktree-wf_a50d40b2-f95-1`, 2026-09-25. Implementation commit
`e926a15`, chained on a green gate. Nothing was pushed or synced; the design session
merges the branch. **BLOCKED:** all three pinned tests fail as pinned
(`docs/briefs/BLOCKED.md` §Open, 2026-09-25 · M2-05); everything else is done.

1. **Base.** The worktree was made at `63816ac` (the M1 close); its branch was
   fast-forwarded to `18c369e` (the commit holding this brief and its pinned files) before
   any work. No other branch or worktree was touched.
2. **The pinned tests, as pinned** (copied with `cp -r docs/briefs/pinning/M2-05/. .`;
   `cmp` identical, all three, before they were moved out of the tree):
   - `test_building_chunks.gd`: `SCRIPT ERROR: Parse Error: The function signature doesn't
     match the parent. Parent signature is "_set(StringName, Variant) -> bool".` (line
     154), then GUT's `Ignoring script … because it does not extend GutTest`.
   - `test_building_loader.gd`: 3/5 tests, 633/823 asserts: 96 of the fixture's 110
     triangles miss the 1e-5 tolerance of line 147 (Godot stores normals as 16-bit
     octahedral pairs: (0, 1, 0) reads back (0, 1, -1.5e-5)); 93 miss "Godot's front face"
     (SurfaceTool smooths normals over shared positions unless the smooth group is -1);
     `test_a_flat_roof_faces_the_sky` fails.
   - `test_main_scene_buildings.gd`: 4/5 tests, 27/28 asserts:
     `test_without_terrain_and_buildings_the_panel_names_both`, `Unexpected Errors: [1]
     <push_error>BuildingChunks: …` (two readers log one refusal each; one
     `assert_push_error` handles one).
   - With the six-line corrections BLOCKED.md proposes (scratch copies, never in the live
     tree), against `e926a15`: 10/10 tests (101 asserts), 5/5 (823), 5/5 (28); the whole
     suite 20 scripts, 98 tests, 2'692 asserts, `---- All tests passed! ----`. Their
     deliberate refusals print 8 (`test_building_chunks.gd`) and 3
     (`test_main_scene_buildings.gd`) `BuildingChunks: user://test_…` ERROR lines, for
     which the closing needs two scoped allowlist entries (BLOCKED.md).
3. **The gates, each with its evidence.**
   - Pinned copies: not ticked. Identical when copied; left out of the tree for
     `e926a15` because they fail (item 2).
   - The seam: not ticked. The mutations fail the corrected copies and pass the gate at
     `e926a15` (item 6): with the pinned copies out, that gate cannot see the seam.
   - The real village (ticked): `python -m mattini terrain --raw …` wrote `village.f32`
     with the expected `b6334c1f…` in 8.8 s; `python -m mattini buildings --raw …`: `1486
     buildings in 6 chunks: 92594 vertices, 178910 triangles, 3258048 bytes`, `the 6
     chunks have the SHA-256s config/buildings.json expects`, 7.4 s. The main scene
     headless at `e926a15` (`godot --headless --path game --quit-after 300`, user:// in a
     scratch folder): exit 0 in 5.7 s, printing Terrain3D's deprecation `WARNING`, `mattini
     0.1.0: terrain village loaded, 4001 x 6001 vertices at 0.5 m` and `mattini 0.1.0:
     buildings village loaded, 1486 buildings in 6 chunks, 178910 triangles`, no ERROR
     line. Screenshots: item 5.
   - `tools/export.sh` (ticked), at `e926a15`: exit 0 in 21 s (templates installed). No
     ERROR line in either export; 80 `Storing File` lines per export (M2-02: 65), the six
     `.bin` chunks, `buildings/village.json`, both scripts and both materials (as
     remapped resources) among them. Step 5:

     | File | Bytes | MiB |
     |---|---|---|
     | `build/linux/libterrain.linux.release.x86_64.so` | 3'251'016 | 3.10 |
     | `build/linux/mattini.pck` | 99'407'468 | 94.80 |
     | `build/linux/mattini.x86_64` | 71'075'864 | 67.78 |
     | `build/windows/libterrain.windows.release.x86_64.dll` | 3'549'184 | 3.38 |
     | `build/windows/mattini.exe` | 104'659'456 | 99.81 |
     | `build/windows/mattini.pck` | 99'407'468 | 94.80 |

     Step 6 expected and found both lines (`started: mattini 0.1.0: terrain village
     loaded, 4001 x 6001 vertices at 0.5 m`, `started: mattini 0.1.0: buildings village
     loaded, 1486 buildings in 6 chunks, 178910 triangles`). The two `.pck` files are
     identical (SHA-256 `b1324e0db83b40dd…`). The `.pck` grew by 3'281'944 bytes over
     M2-02's 96'125'524 and has 5'450'132 bytes left under GitHub's 104'857'600 (SPEC §13
     row 23 foresaw 3.1 MiB).
   - Standard gate: not ticked, since the brief's includes its pinned tests. At
     `e926a15` (`tools/gate.sh > gate-M2-05.log && git commit …`): exit 0, `== gate: all
     steps passed`; pytest 623 passed, 4 deselected; GUT 17 scripts, 78 tests, 1'741
     asserts, `---- All tests passed! ----`; gdlint clean, gdformat 26 files unchanged; 67
     `ERROR` lines, all excepted: 44 `WorldConfig: user://test_`, 19 `TerrainGrid:
     user://test_`, 2 `WorldConfig: not read from a manifest` (scoped), 2 `BuildingChunks:
     user://test_` in `test_building_chunks_indices.gd` (the new scoped entry, item 7).
4. **Numbers.** On the real village, measured with a probe script: BuildingChunks reads
   the six chunks in 0.047 s, BuildingLoader builds the meshes in 0.121 s; 146'458 wall
   and 32'452 roof triangles. Normals read back from the meshes differ from the computed
   ones by at most 1.04e-4 per component (fixture: 5.0e-5); no triangle of either lies
   within 1e-4 of the roof threshold. The headless start took 5.7 s (M2-02, terrain only:
   5.3 s).
5. **Screenshots** (`tools/shot.sh`, Xvfb, Compatibility renderer on llvmpipe; evidence,
   not the Forward+ look): `docs/briefs/shots/M2-05-start.jpg`, `M2-05-church.jpg`,
   `M2-05-street.jpg`. All three show the white buildings standing on the clay terrain,
   casting shadows; the walls are near white in full sun (albedo 0.93) in this renderer.
   - start: the scene's own start view (150 m above the grid's centre, bearing 235°, 20°
     down): the village along the valley, gabled roofs, a church spire lower right.
   - church, `2623906,1096422,60,315,35`: 60 m above the terrain, 86 m south-east of the
     church, looking at it and its square. The church is the building swissBUILDINGS3D
     classes `Sakrales Gebaeude` with its bounding-box centre at E 2'623'845.0 N
     1'096'483.1 (46.5 × 31.4 m, its highest point 53 m above its lowest), the larger of
     the only two such buildings in the six sheets, 21 m from M1-04's Kirchplatz point
     (E 2'623'825.25 N 1'096'489.75). The prompt's point (E 2'624'140 N 1'096'640) has
     no sacral building within 60 m (the two are 334 and 368 m away); it lies about 65 m
     east of the river's lowest line.
   - street, `2624290,1097350,40,200,15`: 40 m above the valley floor west of the river,
     facing bearing 200 (down the valley towards the church), 15° down: a street between
     flat-roofed blocks, running south. The prompt's Bahnhofstrasse line (E 2'624'600 N
     1'097'350 to E 2'624'350 N 1'096'700) lies on the east slope, its ends at 1'672.5
     and 1'656.2 m, 85 and 58 m above the river's lowest line at those northings
     (terrain profiles); the view takes the same line 310 m west, on the valley floor.
     swissBUILDINGS3D names no street, so that this is Bahnhofstrasse is not proven.
6. **Mutation runs**, one per run, each undone with `git apply -R` of its saved diff
   (`git diff` against the index empty after each). "Gate" is the full `tools/gate.sh` in
   the commit state (pinned copies out); "corrected" is the whole GUT suite in a scratch
   copy of the project with the corrected pinned copies (from the second run on with
   `config/` in the copy; the first run's one other failure,
   `test_manifest_matches_config_world_json`, was that copy lacking `config/`).

   | Run | Mutation | Gate | Corrected | Owner-visible harm it reproduces |
   |---|---|---|---|---|
   | W | `building_loader.gd`: triangles into the arrays as (a, b, c), the file's order | exit 0, 78/78 | `test_normals_face_out_and_front_faces_are_godot_s` fails: all 110 triangles "is a file triangle as (a, c, b)" and "Godot's front face" | every building drawn inside out (back faces culled: its far inner walls instead of its outside) |
   | X | `building_chunks.gd`: x and z of each position swapped after reading | exit 0, 78/78 | `test_every_named_vertex_lies_where_the_world_config_puts_it` fails for all 16 named vertices, "as written" and "to_local", e.g. `[(31.783, 1021.482, 931.474)] expected to equal [(931.474, 1021.482, 31.783)]`; 97/98 | the village mirrored across a diagonal, off its terrain |
   | R | `building_loader.gd`: `normal.x >= 0.5` for `normal.y` | exit 0, 78/78 | `test_roofs_and_walls_by_the_normal` (21 triangles' up-facing normals on the walls surface, 19 non-up on the roofs, e.g. `2650-1149: wall normal (0.13119, 0.77171, 0.622297)`) and `test_a_flat_roof_faces_the_sky` fail; 96/98 | east walls in the roof colour, roofs in the wall colour |
   | I (mine) | `building_chunks.gd`: the index check's former `bad == -1` sentinel restored | exit 1 at `gut`: `test_an_index_of_2_to_the_31_or_more_is_refused`: `Expected [<RefCounted#…>(building_chunks.gd)] to be NULL: the index 4294967295 is refused`, `[0] expected to equal [1]: one push_error names the chunk and the index 4294967295`; 77/78, 1'739/1'741 | — | a chunk holding index 0xFFFFFFFF read as -1, a triangle to the chunk's last vertex, no error |
   | E (mine) | `main.gd`: `_show_buildings(buildings)` deleted (read, never shown) | `tools/export.sh` exit 1 at step 6, after the terrain's line started: `export: the Linux build did not print its startup line: mattini 0.1.0: buildings village loaded, 1486 buildings in 6 chunks, 178910 triangles` | — | a release with no buildings and no error |
   | S (mine) | the generated manifest's `buildings` set to null (restored after, `cmp`) | `tools/export.sh` exit 1 at step 1: `… has no buildings block: run uv run --project pipeline python -m mattini download buildings, then uv run --project pipeline python -m mattini buildings` | — | an export without buildings |

   - does NOT prove: that these are the only wrong twins; W, X and R were run against the
     corrected copies, which are not the pinned ones.
7. **Choices inside the brief's scope** (reversible):
   - BuildingChunks refuses, beyond the brief's list: a block whose `area` or `source`'s
     `attribution`, `dataset`, `edition` is not text, `chunks` empty or not a list, an
     entry whose key set is not exactly the SPEC's six, a tile id not `<int>-<int>`, a
     tile twice (two nodes of one name), counts not whole from 1 to 2^31-1. It reuses
     `TerrainGrid._load_manifest` and `TerrainGrid._is_plain_relative_path` (one home for
     the manifest reading and the path rule). The WorldConfig check compares origin and
     height offset, as TerrainGrid's does; the axes are not compared (the reader converts
     nothing, and the pipeline wrote positions for any rotation).
   - The index check sorts a copy (native) and names the first bad index, as the file
     holds it: a uint32 of 2^31 or more reads as a negative int32 and is refused. The
     first version used -1 as "none found" and so accepted 0xFFFFFFFF; the live
     `test_building_chunks_indices.gd` pins it (run I), with a scoped allowlist entry
     `BuildingChunks: user://test_ @ res://tests/test_building_chunks_indices.gd`. The
     brief names "a scoped entry"; since an entry is scoped to one script, closing needs
     two more (BLOCKED.md).
   - BuildingLoader skips a surface with no triangle (Godot refuses an empty one), so a
     chunk without roofs would have one surface; none of the village's or the fixture's
     does.
   - main.gd: one ErrorCatcher per reader, so each refusal shows its own messages and
     commands; with two refusals each fix line reads "To fix the terrain, …" / "To fix
     the buildings, …", with one "To fix it, …" as before; a refused manifest names "the
     terrain and the buildings" with the manifest command. The credits with nothing
     loaded read "No generated data is loaded, so no dataset is shown." (was "No terrain
     is loaded …"). The terrain's credits line takes `dataset` and `edition` from the
     manifest's terrain source as before, the attribution from TerrainGrid.
   - The live main-scene tests read `game/tests/complete_world.gd` (not a test script: no
     `test_` prefix), the terrain fixture plus the pinned test's 2 m box, written once per
     script into its user:// folder. Their "no terrain" cases keep the buildings, so they
     also check that the buildings stay; the not-JSON case checks that neither is shown
     and the credits' "No generated data" line. So no live test but the new one provokes
     a BuildingChunks refusal.
   - The materials set `metallic` and `roughness` to their defaults explicitly, for the
     owner's reading; Godot's editor may drop default values when it saves the file.
   - `tools/export.sh` computes both expected lines in one Python call (the buildings'
     counts summed over the manifest's chunks) and requires each exactly (`grep -x -F`).
8. **Out-of-scope touches:** none. `game/tools/shot.gd` and `tools/shot.sh` changed their
   header comments only (they name the buildings). The new scripts' `.uid` files are under
   `game/scripts/buildings/` and `game/tests/`.
9. **Follow-up candidates** (for design; none built):
   - brain.md §Hazards could gain two measured Godot facts: SurfaceTool smooths
     `generate_normals` over shared positions unless the smooth group is -1; an
     ArrayMesh gives normals back through 16-bit octahedral storage (worst 1.04e-4 per
     component on the village).
   - `docs/RELEASE.md` §C's buildings line (design at the close, per the brief).
   - The prompt's church-square and Bahnhofstrasse coordinates do not match the data
     (item 5); M1-04's Kirchplatz point does.
   - The screenshots' walls are near white in full sun; the owner judges the look in
     Forward+ (SPEC §13 row 17).
   - Not measured: the twelve buildings standing above the 2024 terrain (SPEC §8), which
     the release record names; memory of the full scene with buildings (the probe without
     terrain: 37.5 MB static).
