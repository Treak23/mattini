# Brief: M2-05 — The buildings in the game
Status: OPEN

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
- [ ] The main scene with the real village loads 1'486 buildings in six chunks (a headless
      run's startup lines, in Findings), and the software screenshots show buildings on
      the terrain.
      - does NOT prove: the Forward+ look on the owner's PC.
- [ ] `tools/export.sh` passes with the real village and buildings, including its step 6.
      - does NOT prove: that the Windows build starts.
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that it renders or looks right.

## Forbidden

A version bump (the close does it); collision or walking (M6); per-building colours or
textures; a change to the fixture's bytes.

## Findings (executor writes)
