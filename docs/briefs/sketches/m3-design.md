# m3-design.md — design's working notes for M3 (2026-10-14)

Committed with the plan because the pinned tests and the shared vectors cite these notes as
"m3-design §N" for the reasons behind their decisions. They are the notes the preparation
agents worked from, kept as they were. **Where they differ, `docs/SPEC.md` (§5, §8, §10,
§11) and the briefs `docs/briefs/M3-*.md` outrank them.** Decided after these notes, and
so not in them:

- Trees (§5): crown radius clamp(min(d / 2, height / 4), 1.0, 6.0) m with d = +∞ when a
  tree has no other (not "6.0 when none"); tops whose chm is below 3 m are dropped;
  TLM_GEBAEUDE_FOOTPRINT OBJEKTART 16 (underground) is not masked; the description's
  `parameters` gains `crown_radius`; 34'412 village trees.
- Game API (§9): `TreeLoader.create(chunks, parent, photo: Texture2D = null, photo_rect:
  Vector4 = Vector4.ZERO)`, no PhotoGrid type; `TreeLoader.TREES_NOTE` and
  `BuildingLoader.WALLS_NOTE` exact texts (briefs M3-11, M3-12).
- The lock's fit has one home, `lock.fit_problem` (M3-01, M3-03); the several-datasets
  rule `lock.entries_sha256` (M3-13); one Ctrl-C handler in `main()` (M3-03).
- The scene (§8): the sun's 183° and 52° come from the photo's shadows (the flight time
  gives 181° and 50°); the startup lines, credits and error panel are brief M3-14's.

---

# M3 design rules (draft for SPEC §5, §8, §10, §11; design realm, 2026-10-14)

The owner's answers (2026-10-14): the realistic look (a): the aerial photo on the terrain,
roof colours from the photo, 3D trees where the LiDAR found them, rock texture on steep rock,
procedural conifers, the fixed sun moved to the photo's sun, lighting calibrated to the
photo; the photo at 0.2 m; walls one neutral plaster (a labelled placeholder); delivery by
data packs beside the executable; swissTLM3D in M3 for water and paths (and the forest
outline cleaning... see trees: rock and building footprints); FB-002: game type stays open.

Conventions shared by every new step (as terrain and buildings, SPEC §8): the area is the
one area of the step's config; the step checks world and inputs (`computed_for`) before any
output; verifies every input file's SHA-256 against the lock; compares its output with the
expected values in its config before writing anything; writes through a `.part` rename;
descriptions are JSON with sorted keys, 2-space indent, UTF-8, LF, a final newline; no
times, no absolute paths. Refusals name the file and the command that fixes it.
`computed_for` = exactly {inputs_sha256, world_sha256}: world_sha256 = SHA-256 of
config/world.json's bytes; inputs_sha256 = for a step with ONE dataset, `lock.entry_sha256`
of that dataset's lock entry (as terrain/buildings); for a step with SEVERAL datasets, the
SHA-256 of `json.dumps({dataset: entry, ...}, sort_keys=True, separators=(",", ":"),
ensure_ascii=False)` encoded UTF-8, over exactly the step's datasets.

Tiles: an area's 1 km tiles are those whose square lies in the area box, named
`<floor(E/1000)>-<floor(N/1000)>` of the square's south-west corner (as swissALTI3D).

## 1. New datasets (config/datasets.json, written by brief M3-03 with datasets.py)

```
"swissimage":     {"collection": "ch.swisstopo.swissimage-dop10", "edition": "2023",
                   "resolution_m": 0.1, "attribution": "© swisstopo"}
"swisssurface3d": {"collection": "ch.swisstopo.swisssurface3d-raster",
                   "editions": ["2021", "2022"], "resolution_m": 0.5, "attribution": "© swisstopo"}
"swisstlm3d":     {"collection": "ch.swisstopo.swisstlm3d", "edition": "2026-02",
                   "attribution": "© swisstopo"}
```
A dataset has `collection`, `attribution` and exactly one of `edition` (a year `YYYY`, or
`YYYY-MM` for a national product) or `editions` (a non-empty, sorted list of distinct years:
the editions accepted per tile when a tile is published in one edition only).

STAC items and assets (exactly one asset whose key ends with the suffix):
- swissimage: item `swissimage-dop10_<edition>_<tile>`, suffix `_0.1_2056.tif`.
- swisssurface3d: for each tile, item `swisssurface3d-raster_<year>_<tile>` for every year
  in `editions`; exactly one of them must exist (HTTP 404 = absent), else refused naming
  the tile and the years found; suffix `_0.5_2056_5728.tif`.
- swisstlm3d: item `swisstlm3d_<edition>`, suffix `_2056_5728.gdb.zip`.

Lock entries (config/datasets.lock.json; exact key sets):
- `swissimage`: {collection, edition, resolution_m, tiles: {<tile>: {file, sha256}}}
- `swisssurface3d`: {collection, resolution_m, tiles: {<tile>: {edition, file, sha256}}}
- `swisstlm3d`: {collection, edition, file, sha256}
Commands: `lock photo`, `lock surface`, `lock tlm`; `download photo`, `download surface`,
`download tlm` (raw files under data/raw/<dataset>/..., with a provenance.json like the
terrain's). The TLM file is 2.88 GB: the download resumes a cut transfer with an HTTP Range
request and retries; the file is used only after its SHA-256 equals the lock's.

Measured 2026-10-14 (design's agents): SWISSIMAGE 2023 0.1 m tiles
2623-1095 49397f69d28bbab566fd6618090a088d0661f64551aca8b7d98da55ca16bd47b,
2623-1096 9fb6d0cfcbcb4119e602821ae1a88da9d027bf477a807784bd7068dc1877335a,
2623-1097 e491d7198993a5f515b886f6f3234efeebdad958afffe6a7b8643e2189c594d0,
2624-1095 0913fdfc65ea5a1468d6d7ee857ad800040afb3516754570aec270b3756bb285,
2624-1096 adf3ef9d934c3947a1c12b5e45a4dc48b7b2655b6aa8ecb11785d6ec281c817d,
2624-1097 b911565192a58e408e9dc9bdad33f93ba30ac8022294bc727eb0c8919bb41d5b.
swissSURFACE3D raster 0.5 m: 2623-1095 (2022) 5cb9ad15b887de6b15c3371119c276b00ae75053ad27a5ee2e9ae19d3276b3d0,
2623-1096 (2021) 34657277bb0380973aab9b6abedec3e9946228fbadebd7192a00cd910c3c8771,
2623-1097 (2021) d20fc78b1fbf096da544c91a6536d74cf911ce793dfe1ca5c8cf1a016dce464f,
2624-1095 (2021) 575090d21fb3a1fd1676bd030d825610fcbee75bc129eec9afe5726e1ecab391,
2624-1096 (2021) 17d6ba7e75b972c2abcb014563760a435cc992f1e2a8c274936b0c291c67e582,
2624-1097 (2021) 62d4b06901dc900f00c31cc230cda614f78913aa1e84c19cfa2e5ac054497571.
swissTLM3D 2026-02 FileGDB zip: 185ffca883e7a2d6be4ea3d1f62ee4d1a09f07fe90e381738fdcb3a849df28da
(2,882,823,552 bytes).

## 2. The photo (step `photo`, module pipeline/mattini/photo.py, brief M3-04)

Inputs: the area's swissimage tiles. Each is refused unless: SHA-256 equal to the lock;
GeoTIFF, EPSG:2056, 10000 × 10000 pixels, 3 bands uint8, affine transform exactly
(0.1, 0, E0, 0, −0.1, N0 + 1000) with (E0, N0) the tile's south-west corner.
Grid: `cell_m` from config/photo.json, one of 0.2, 0.5, 1 (k = cell_m / 0.1 = 2, 5, 10).
columns = (e_max − e_min) / cell_m, rows = (n_max − n_min) / cell_m (whole numbers, else
refused). Texel (r, c), r from north, c from west, is the k × k block of 0.1 m source pixels
whose global indices from the area's north-west corner are rows r·k … r·k + k − 1 and
columns c·k … c·k + k − 1; per channel its value is round-half-to-even(S / k²) of the exact
integer sum S. Raw grid bytes: rows north to south, columns west to east, RGB interleaved,
uint8: `pixels_sha256` is their SHA-256.
Encoding: Pillow, `Image.frombuffer("RGB", (columns, rows), raw, "raw", "RGB", 0, 1)
.save(f, "JPEG", quality=92, subsampling=2, optimize=False, progressive=False)` (4:2:0,
baseline, no EXIF or ICC). Pillow is a new pipeline dependency (design confirmed,
2026-10-14); its JPEG output was measured byte-identical across Pillow 10.4.0, 11.0.0,
12.3.0 and with libjpeg-turbo's SIMD off.
Files: `photo/<area>.jpg`, `photo/<area>.json` = exactly {area, cell_m, columns, file
("photo/<area>.jpg"), format ("jpeg"), jpeg: {quality: 92, subsampling: "4:2:0"},
lv95_box: {e_max, e_min, n_max, n_min} (floats), pixels_sha256, rows, sha256 (of the .jpg),
source: {attribution, collection, dataset: "swissimage", edition, resolution_m: 0.1,
tiles: [{sha256, tile}] sorted by tile}, world_sha256}.
Expected values: config/photo.json = {"schema": 1, "areas": {<area>: {"cell_m": 0.2,
"computed_for": {...}, "expected_pixels_sha256": {"0.2": …, "0.5": …, "1": …},
"expected_sha256": {"0.2": …, "0.5": …, "1": …}}}} (keys as swisstopo writes a resolution:
format(cell_m, "g")). The step compares the pixels first ("this machine or this code
computes other pixels than design's …"), then the JPEG ("the pixels are design's; this
machine's JPEG encoder writes other bytes: Pillow <v>, libjpeg-turbo <v>").
Game (PhotoGrid, brief M3-09): reads the `photo` block, checks its exact key set, its
world_sha256 against its manifest, file path, size and SHA-256, columns × cell = box width
and rows × cell = box depth; decodes with Image.load_jpg_from_buffer and checks the decoded
size (columns × rows, RGB8); makes an ImageTexture with mipmaps. Placement through
WorldConfig only: the rectangle's north-west corner is to_local(e_min, n_max, h) (x0, z0);
only the owner's axes (x = +e, z = −n) are accepted, others refused (as terrain); the
rectangle spans x0 … x0 + columns·cell, z0 … z0 + rows·cell. Shader: uv = (world.xz −
(x0, z0)) / (columns·cell, rows·cell); texel (c, r) is centred at uv ((c + 0.5)/columns,
(r + 0.5)/rows).

## 3. Roof colours (step `roofs`, module pipeline/mattini/roofs.py, brief M3-05)

Inputs: the buildings' sheets (swissbuildings3d lock entry) and the photo's tiles
(swissimage lock entry); inputs_sha256 over both entries.
Buildings: exactly the buildings step's selection, snapping, orientation, chunks and order
(SPEC §8, the buildings; reuse its functions). For each building, in integer units of
0.1 mm (E_u = round(E' · 10000), N_u, H_u likewise; exact since E', N' are on the 1 mm grid
and H' on the 0.1 mm grid):
- roof triangle: with a, b, c in triangle order (counter-clockwise from outside after the
  orientation rule), n = (b − a) × (c − a) in (E, N, H) integer components; roof if
  n_H > 0 and 4·n_H² ≥ n_E² + n_N² + n_H² (the unit normal's up component ≥ 0.5, the
  game's rule, building_loader.gd).
- roof pixels: the 0.1 m source pixels of the photo whose centre (E = E0 + 0.05 + 0.1 i,
  in units E_u = E0·10000 + 500 + 1000 i; N likewise from the tile's top) lies inside or on
  the boundary of the plan projection (E, N) of at least one roof triangle whose projected
  area is non-zero; exact integer orientation tests.
- colour: per channel the lower median of the roof pixels' values (sorted ascending, the
  element at index floor((n − 1) / 2)); with n = 0 the building has no roof colour (null).
File: `roofs/<area>.json` = exactly {area, chunks: [{buildings: [{roof: "rrggbb" (lower-case
hex) or null, roof_pixels: n, triangles: t, uuid, vertices: v}, ...] in chunk order, tile}]
sorted by tile, format: "roofs-v1", lv95_box, source: {buildings: <the buildings block's
source>, photo: <the photo block's source>}, world_sha256}; `triangles` and `vertices` are
the building's counts in its chunk file, so each chunk's sums equal the chunk's.
Expected values: config/roofs.json = {"schema": 1, "areas": {<area>: {"computed_for": …,
"expected_sha256": <SHA-256 of roofs/<area>.json>}}}.
Game (BuildingRoofs, brief M3-12): reads the `roofs` block; checks key sets, world_sha256,
file SHA-256, that its chunks are BuildingChunks' chunks in order and per chunk the sums of
triangles and vertices equal the chunk's; BuildingLoader colours each building's roof
triangles (the game's own normal.y ≥ 0.5 rule) with its colour as vertex colour; a building
with roof null keeps the neutral roof material. Walls: one neutral plaster for every wall,
albedo (0.78, 0.76, 0.72), roughness 0.9, labelled a placeholder in code and credits (no
wall data exists).

## 4. Surfaces (step `surfaces`, module pipeline/mattini/surfaces.py, brief M3-06)

Input: the swisstlm3d FileGDB zip (lock: file, sha256), read with fiona through GDAL's zip
access, never unzipped to disk. Layers: TLM_STRASSE, TLM_BODENBEDECKUNG,
TLM_FLIESSGEWAESSER. A feature is used when its 2-D bounding box intersects the area box
grown by 10 m. Coordinates (E, N) are snapped to the 1 mm grid in 64-bit (as the buildings:
round(v · 1000) / 1000, half-to-even; a coordinate more than 1e-6 m off is refused).
Grid: the photo's grid with `cell_m` from config/surfaces.json (0.2): texel (r, c) centre
E_c = e_min + cell/2 + c·cell, N_c = n_max − cell/2 − r·cell, computed exactly in integer mm.
Classes (uint8), highest wins: 4 road > 3 path > 2 water > 1 rock > 0 none.
- 4 road: TLM_STRASSE with BELAGSART 100 (Hart); 3 path: BELAGSART 200 (Natur). Only
  OBJEKTART with a width: 8 (10m Strasse) 10 m, 9 (6m Strasse) 6 m, 10 (4m Strasse) 4 m,
  11 (3m Strasse) 3 m, 15 (2m Weg) 2 m, 16 (1m Weg) 1 m, 17 (1m Wegfragment) 1 m (codes to
  be confirmed from the FileGDB's subtype table by design's agent before pinning). Not
  drawn: KUNSTBAUTE 700 Galerie, 1000 Tunnel, 1100 Unterfuehrung, 1200 Unterfuehrung mit
  Treppe, 1400 in/auf Gebaeude; BELAGSART other than 100/200. A texel is on the line if the
  2-D distance from its centre to a segment of the line is ≤ width/2 (exact rational test
  in integer mm).
- 2 water: TLM_BODENBEDECKUNG OBJEKTART 5 (Fliessgewaesser) or 10 (Stehende Gewaesser):
  centre inside the polygon (even-odd over all its rings, half-open crossing rule below);
  and TLM_FLIESSGEWAESSER OBJEKTART 4 (Fliessgewaesser) with VERLAUF 100 (Oberirdisch) or
  500 (Wasserfall): distance ≤ 1.0 m (an assumed width of 2 m: TLM gives none; labelled).
- 1 rock: TLM_BODENBEDECKUNG OBJEKTART 1, 2, 3, 4 (Fels, Fels locker, Felsbloecke,
  Felsbloecke locker): centre inside the polygon.
Point in polygon (exact, integer mm): for every edge (x1, y1)–(x2, y2) of every ring, the
edge counts when (y1 > yc) ≠ (y2 > yc) and xc < x1 + (yc − y1)(x2 − x1)/(y2 − y1) (compared
exactly as integers, minding the sign of y2 − y1); inside when the count is odd.
Files: `surfaces/<area>.png` (written WITHOUT Pillow by a minimal stdlib writer: 8-bit greyscale, no interlace, filter byte 0 on every row, one zlib stream at level 9 in IDAT chunks of at most 1 MiB; values 0–4),
`surfaces/<area>.json` = exactly {area, cell_m, classes: {"0": "none", "1": "rock",
"2": "water", "3": "path", "4": "road"}, columns, file, format: "png-l8", lv95_box,
pixels_sha256 (raw class bytes, rows north to south), rows, sha256 (the .png's),
source: {attribution, collection, dataset: "swisstlm3d", edition, file, sha256},
world_sha256}. Determinism is pinned on the content (pixels_sha256); the PNG's bytes depend
on the zlib build and are checked for integrity only.
Expected values: config/surfaces.json = {"schema": 1, "areas": {<area>: {"cell_m": 0.2,
"computed_for": …, "expected_pixels_sha256": {"0.2": …}}}}.
Game (SurfaceGrid, brief M3-10): reads the block, checks key sets, world_sha256, file SHA-256,
decodes the PNG (Image.load_png_from_buffer → L8), checks size and the decoded bytes'
SHA-256 against pixels_sha256; the same rectangle rule as the photo.

## 5. Trees (step `trees`, module pipeline/mattini/trees.py, brief M3-07)

Inputs: swisssurface3d (DSM), swissalti3d (DTM; the terrain's tiles), swissbuildings3d
(sheets), swisstlm3d (TLM_BODENBEDECKUNG, TLM_GEBAEUDE_FOOTPRINT); inputs_sha256 over the
four entries. DSM and DTM tiles: 2000 × 2000 float32, 0.5 m, transform exactly
(0.5, 0, E0, 0, −0.5, N0 + 1000), no nodata value present.
Pixel grid: the area's 0.5 m pixels, (i, j) from the north-west; centre E = e_min + 0.25 +
0.5 j, N = n_max − 0.25 − 0.5 i.
1. chm = DSM − DTM per pixel (64-bit; exact for float32 inputs).
2. Masks (pixel centre rules, exact integer mm): footprint pixels F = centre inside or on the
   boundary of the plan projection of a non-degenerate triangle of a selected-or-not
   building of the area's sheets (every building whose bounding box meets the area, not only
   the selected ones), or inside a TLM_GEBAEUDE_FOOTPRINT polygon (even-odd rule above);
   B = pixels within 2.0 m of a pixel of F, centre to centre (di² + dj² ≤ 16);
   R = centre inside a TLM_BODENBEDECKUNG polygon of OBJEKTART 1, 2, 3, 4 (rock).
3. v = chm where chm > 0 and the pixel is not in B, else 0. Each v must be a whole multiple
   of 2^−13 m (true for float32 heights in [1024, 4096) m); otherwise refused. V = v · 2^13
   as integers.
4. Smoothing: S = K ⊛ V with K = outer([1, 4, 6, 4, 1], [1, 4, 6, 4, 1]) (weights sum 256),
   pixels outside the area counted 0; S in units of 2^−13 / 256 m (integers, exact).
5. Tops: pixel p (not on the area's outermost ring of pixels, not in B, not in R) with
   S(p) ≥ 3 m (S ≥ 3 · 2^21) is a top when, within the disc of radius ρ = 3 + floor(s/10 m)
   pixels (s = S(p) in metres; di² + dj² ≤ ρ², inside the area), every other q has
   S(q) < S(p), or S(q) = S(p) and q after p in raster order (rows from north, then columns
   from west).
6. Drop a top whose chm > 40 m (cliffs: the DSM takes a face's top, the DTM its foot) or whose
   DTM slope is ≥ 60°: gx = DTM(i, j+1) − DTM(i, j−1), gy = DTM(i+1, j) − DTM(i−1, j) (per
   1 m), dropped when gx² + gy² ≥ 3 (64-bit, exact).
7. A tree: E, N = the top pixel's centre; base height = the mean of the four terrain-grid
   vertices around the pixel centre (SPEC §8, the terrain grid at 0.5 m spacing: vertices
   (j, i), (j+1, i), (j, i+1), (j+1, i+1) of the 4001 × 6001 grid; heights already minus
   height_offset_m), in 64-bit, rounded once to float32 (local y); x, z = to_local(E, N) in
   64-bit then float32; height = chm at the top, float32; crown radius = clamp(d/2, 1.0,
   6.0) m with d the 2-D distance (64-bit, correctly rounded sqrt) to the nearest other kept
   tree of the area (6.0 when none), float32.
8. Chunks: the 1 km tile of (E, N); within a chunk, raster order of the top pixels.
File per chunk `trees/<tile>.bin`: per tree x, y, z, height_m, crown_radius_m as
little-endian float32 (20 bytes), no header. `trees/<area>.json` = exactly {area, chunks:
[{file, sha256, tile, trees}] sorted by tile, format: "trees-f32x5-le", lv95_box,
parameters: {building_margin_m: 2.0, max_height_m: 40.0, max_slope_deg: 60.0,
min_height_m: 3.0, smoothing: "binomial-5x5", window: "3 + floor(h / 10 m) pixels"},
source: {swissalti3d: …, swissbuildings3d: …, swisssurface3d: …, swisstlm3d: …} (each as
that dataset's source in its own block), world_sha256}.
Expected values: config/trees.json = {"schema": 1, "areas": {<area>: {"computed_for": …,
"expected_sha256": {<tile>: …}}}}.
Game (TreeChunks + TreeLoader, brief M3-11): reads the block and files (size = 20 × trees,
SHA-256, world_sha256), never converts a coordinate; one MultiMeshInstance3D per 250 m cell
of procedural conifers (a generic conifer, labelled: the data gives where and how tall, not
the species), each scaled to its height and crown radius, turned about +y by a hash of its
position; the crown colour sampled in the tree shader from the photo texture at the tree's
position (uniforms photo, photo_rect), at a mip level matching the crown's size; shadows on.

## 6. Data packs (brief M3-08)

tools/export.sh, after both exports: generated files under assets/generated/ of 10 MiB or
more go into one pack per folder, `mattini-<folder>.pck` (terrain, photo), written with
Godot's PCKPacker by a tool script run with the editor binary headless, files added in
sorted path order (measured deterministic); the presets' exclude_filter keeps those files
and `*.part` out of mattini.pck; each pack is written next to both executables and must be
under 100 MiB (step 5). An autoload, `res://scripts/data_packs.gd`, loads in `_init()` of an
exported build every `mattini-*.pck` beside the executable, in name order, and prints one
line per pack; step 6 starts the Linux build with its packs and requires every startup line.

## 7. The terrain look (briefs M3-09, M3-10)

A new Terrain3D override shader `res://shaders/terrain_photo.gdshader` (the clay shader's
structure without contour lines): albedo = the photo; roughness 0.95; rock class: a
triplanar CC0 rock texture blended with weight smoothstep(35°, 55°, slope), tinted to the
photo's colour; road and path: CC0 detail textures (asphalt, gravel) multiplied into the
photo, normalised to mean 1 so the photo's colour stays, fading out by 150 m from the
camera; water: roughness 0.05, albedo the photo darkened, normals from two scrolling noise
textures (Godot NoiseTexture2D, no file). CC0 textures from Poly Haven, pinned by name,
resolution and SHA-256 in the brief, under game/textures/ with their licence note.

## 8. The scene (brief M3-14)

Sun at azimuth 183°, elevation 52° (the photo's sun, measured from its shadows and the
flight time, 7 Sep 2023 ~11:30 UTC); environment exposure 0.54 and sky ambient contribution
0.25 (the prototype's calibration: flat sunlit ground at the photo's brightness, under
the Compatibility renderer); credits add swissimage 2023, swisssurface3d 2021–2022,
swisstlm3d 2026-02 (© swisstopo each), the CC0 textures by name, and the placeholder note
for walls and trees.

## 9. Game API names (fixed by design so lanes can be built at once)

New readers, each `class_name`, `extends RefCounted`, a static `from_manifest(path: String,
world: WorldConfig, ...) -> <Class>` returning null after logging its refusals with
push_error (the pattern of TerrainGrid and BuildingChunks):
- `PhotoGrid` (game/scripts/terrain/photo_grid.gd): from_manifest(path, world); properties
  `texture: ImageTexture`, `x0: float`, `z0: float`, `width_m: float`, `depth_m: float`,
  `columns: int`, `rows: int`, `cell_m: float`, `area`, `dataset`, `edition`,
  `attribution`; `rect() -> Vector4` = (x0, z0, width_m, depth_m).
- `SurfaceGrid` (game/scripts/terrain/surface_grid.gd): the same shape; `texture` holds the
  L8 class image (sampled with filter nearest); `class_at(x: float, z: float) -> int`.
- `TreeChunks` (game/scripts/trees/tree_chunks.gd): from_manifest(path, world); `chunks:
  Array[Dictionary]` each {tile, trees, positions: PackedVector3Array, heights:
  PackedFloat32Array, radii: PackedFloat32Array}; `area`, `attribution`, `dataset`
  ("swisssurface3d"), `edition` (e.g. "2021-2022").
- `BuildingRoofs` (game/scripts/buildings/building_roofs.gd): from_manifest(path, world,
  chunks: BuildingChunks); `chunks: Array[Dictionary]` each {tile, buildings:
  Array[Dictionary] {uuid, triangles, vertices, roof: Color or null}}.
Loaders:
- `TerrainLoader.create(grid, parent, photo: PhotoGrid = null, surfaces: SurfaceGrid =
  null) -> Terrain3D`: with a photo, the shader is res://shaders/terrain_photo.gdshader
  and its uniforms `photo`, `photo_rect`, `surfaces`, `surfaces_rect` are set; without,
  the clay shader as before (M2's look stays the fallback).
- `TreeLoader.create(chunks: TreeChunks, parent, photo: PhotoGrid = null) -> Node3D`
  (node "Trees", one MultiMeshInstance3D per 250 m cell named "<cx>_<cz>").
- `BuildingLoader.create(chunks, parent, roofs: BuildingRoofs = null)`.
- Autoload `DataPacks` (res://scripts/data_packs.gd) with a static `load_from(dir: String)
  -> PackedStringArray` (the packs loaded) used by `_init()` in exported builds.


## 10. Additions after the data-packs agent (2026-10-14)

- Every step that writes an image under game/assets/generated/ writes beside it `<file>.import`
  holding exactly "[remap]\n\nimporter=\"keep\"\n" (through the same .part rename), so Godot
  neither imports it as a texture (43.6 s, 5.2 GiB for the photo) nor ships an imported copy
  instead of the file (brain.md H24): photo/<area>.jpg.import, surfaces/<area>.png.import. The
  descriptions do not list them.
- Data packs: the packed folders are a fixed list, `photo` and `terrain` (whole folders, but
  names starting with "." or ending ".part"/".import"); export.sh refuses a generated file of
  10 MiB or more outside them (step 4c). Pack tool game/tools/pack.gd, static
  write_pack(pack_path, source_dir, target_dir) -> String. Autoload `DataPacks` =
  "*res://scripts/data_packs.gd" (no class_name: it would hide the singleton), static
  load_from(dir) -> PackedStringArray, `mattini-*.pck` in sort() order with
  load_resource_pack(path, false), one line per pack "mattini <version>: data pack <name>
  loaded", push_error("DataPacks: cannot load the data pack <path>") for one that fails.
  Presets exclude_filter = "tests/*, addons/gut/*, tools/*, *.part, assets/generated/photo/*,
  assets/generated/terrain/*". export.sh steps 4b (write packs) and 4c (every generated file
  ships once, unchanged); step 6 expects the pack lines first.
- The exported build's error panel names pipeline commands a player cannot run: M3-14 makes
  it say, in an exported build, to keep mattini.pck and the mattini-*.pck packs beside the
  executable and to download the release folder again.
