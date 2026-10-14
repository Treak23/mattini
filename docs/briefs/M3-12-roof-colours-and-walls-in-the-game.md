# Brief: M3-12 — Roof colours and walls in the game
Status: OPEN

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
   strings in brackets,
   `const WALLS_NOTE := (` / `"Walls: one neutral plaster colour, a placeholder:"` /
   `+ " no open data shows the façades."` / `)`, on three lines.
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
- [ ] A software screenshot (`tools/shot.sh`) of the fixture's buildings, or of the real
      village if you build it in scratch, committed under `docs/briefs/shots/M3-12-*.jpg` and
      named in Findings. It is evidence, not a gate.
      - does NOT prove: the Forward+ look on the owner's GPU.
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that it renders or looks right.

## Forbidden

- Touching `main.gd` or `main.tscn` (M3-14); changing BuildingChunks' checks or the chunk
  format.
- Changing the roof fallback colour; a texture on the walls.
- Editing a pinned file or the fixture.

## Findings (executor writes)
