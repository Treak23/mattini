# SPEC.md — mattini, design of record (v0, 2026-09-24; amended at the M0 close, at M1 planning, at the M1 close, at M2 planning and at M2's review, 2026-09-25, and at M3 planning, 2026-10-14)

Written by the design realm with the owner from `docs/start.md` Part 1 / 1A and the
owner's day-one answers. Only the design realm edits this file. `CLAUDE.md` holds the
rules; this file holds what is built and why. Markers: **OPEN** = not decided (asked,
never picked silently); **PROPOSED** = suggested, not yet confirmed by the owner.

## 1. What and why

A desktop game set in Zermatt (Mattertal, Valais), built on swisstopo's open geodata, in a
realistic look made from that data: the aerial photo on the ground, roof colours from it,
trees where the LiDAR found them (the owner, 2026-10-14, FB-001: "it's definitely too
white"; until then the look was a stylised "diorama / architectural model", §13 row 29).
What the data does not give (walls, tree species) is a labelled placeholder, never
invented as if it were data. It is the owner's learning project (game development, and
what real open Swiss geodata makes possible), shared later with a few people who have
powerful PCs. A commercial release is undecided and not ruled out, so everything stays
licence-clean.

## 2. v1 scope

**In v1** (owner, start.md Part 1 and day one):

- A sandbox of the real terrain and the real village buildings from swisstopo data, in the
  realistic look made from the data (§1; the owner, 2026-10-14), with a free-fly camera.
- Walking.
- The day/night cycle (real solar position for Zermatt, time control, sky, shadows).
- Weather effects. The weather source is **OPEN** (§12).

**Not in v1:** browser and mobile builds; photorealism beyond what the data gives (hand-made
or procedural detail everywhere: the owner chose the data-made look, option (a), not (c),
2026-10-14); any game mode; Google Maps / Google 3D Tiles data (its licence forbids
shipping or deriving from it); hand-modelled façades for every building.

**Milestones** (order confirmed by the owner on day one): M0 Setup · M1 Terrain · M2
Buildings · M3 Surfaces and trees · M4 Sun cycle · M5 Scale up · M6 Weather and walking.
v1 ships when M6 is done; M5 falls inside v1 because it comes before M6 in the confirmed
order. Later: a first game-mode prototype (type **OPEN**).

## 3. Platforms and machines

Desktop only: Windows and Linux (owner's machines: Windows and EndeavourOS, RTX 4090).
macOS is **OPEN**. Browser and mobile are dropped.

## 4. Stack (pinned)

| Part | Pin | Source (reachable from a cloud container) | Why |
|---|---|---|---|
| Engine | Godot **4.6.3-stable**, standard build (not .NET) | `downloads.godotengine.org` mirror; Linux zip SHA-256 `d0bc2113065e481c9c2c2b2c37daa4e8be3fe9e27f0ab9ab0b6096e9a37907f3` | Owner's choice; Terrain3D 1.0.2 officially supports 4.4–4.6 |
| Language | GDScript | — | Owner's choice |
| Terrain | **Terrain3D 1.0.2** (MIT, C++ GDExtension) | Godot Asset Store: `store.godotengine.org/asset/tokisangames/terrain3d/`, download `https://store.godotengine.org/asset/tokisangames/terrain3d/download/1377/`, file `Terrain3D_v1.0.2-stable-2.zip`, SHA-256 `a071850250ec5e596aa54da61c01d75768774eb379ee997584d426a45f4884a2` (re-measured 2026-09-25) | Owner's choice |
| Renderer | Forward+ (Godot's desktop default) | — | Design (reversible): the owner's GPUs are desktop RTX-class |
| Game tests | **GUT 9.6.1** (MIT) | git tag `v9.6.1` of `github.com/bitwes/Gut` (commit `c80954f47bed74a0a2c471d472c0389f98e0a8f6`); `git clone` works in containers | Design, delegated by the owner (§13) |
| GDScript lint | gdtoolkit **4.5.0** (`gdlint`, `gdformat`) | PyPI, as a pipeline dev dependency | One tool environment for all linting |
| Pipeline | Python **3.13** via **uv**, lockfile committed | uv installs Python itself (works in containers) | Design, delegated by the owner (§13) |
| Python checks | pytest, ruff | PyPI | — |
| Raster reading | **rasterio** (bundles GDAL) and **numpy**, the versions uv resolves, locked (confirmed by design at M1 planning, 2026-09-25) | PyPI wheels for Python 3.13 on Linux and Windows | Reads swisstopo's GeoTIFF tiles with their georeference, which the terrain step checks; measured: rasterio 1.5.1 (GDAL 3.12.4) and numpy 2.5.3 read the real 2024 tiles |
| Vector reading | **fiona** (bundles GDAL), the version uv resolves, locked (confirmed by design at M2 planning, 2026-09-25) | PyPI wheels for Python 3.13 on Linux and Windows (`fiona-1.10.1-cp313-cp313-win_amd64.whl` exists) | Reads swissBUILDINGS3D 3.0's zipped FileGDB from memory (`fiona.io.ZipMemoryFile`); measured: fiona 1.10.1 (GDAL 3.9.2) reads the layer `Building_solid` as MultiPolygon Z triangles, and works beside rasterio's GDAL 3.12.4 in one process. pyogrio cannot: it refuses the layer's geometry type, TIN Z (measured) |

Measured on 2026-09-24 in a cloud container: Godot 4.6.3 runs headless; GUT 9.6.1 runs
headless with a non-zero exit on a failing test; Terrain3D 1.0.2 loads headless in 4.6.3
and heights imported through its API read back exactly; gdlint/gdformat run; `uv python
install 3.13` works. Binary wheels exist for Python 3.12 and 3.13 on Linux and Windows for
numpy, rasterio (bundles GDAL), pyproj (bundles PROJ), shapely (bundles GEOS), pyogrio,
laspy + lazrs and trimesh; rasterio and numpy were confirmed at M1 planning (the table
above), the others not yet (CLAUDE.md §Stack: each is confirmed by the design realm before
it is added). The hazards found while measuring are
in brain.md §Hazards.

github.com release downloads and codeload are refused inside cloud containers (HTTP 403);
`git clone` of public repositories works. That is why Godot comes from its mirror and
Terrain3D from the Asset Store.

## 5. Data sources and licence

**Terms:** "Terms of use for free geodata and geoservices (OGD) from swisstopo", version
1.3.2021 (published 26 August 2022): the data may be used, distributed, made accessible,
enriched, processed and used commercially; a reference to the source is mandatory
(`©swisstopo` or "Federal Office of Topography swisstopo" among the accepted wordings).
Different wording is required only for swissALTIRegio and swissEO. mattini uses swissALTIRegio
from M4 (the mountains around the area, for the sun; SPEC §13 row 42): its own source text, which
names swisstopo and the foreign height models it includes, is printed whole in the credits
(`docs/briefs/sketches/m4-design.md` §1a; brief M4-01). The credits carry `© swisstopo` for the
other datasets (CLAUDE.md Hard Rule 3).

Access: the STAC API at `https://data.geo.admin.ch/api/stac/v1/` (STAC 1.0.0, no key).
Items are addressed by id; assets carry `file:checksum` as a multihash (`1220` + SHA-256).

| Dataset | STAC collection | What we measured (2026-09-24) | Used for |
|---|---|---|---|
| swissALTI3D | `ch.swisstopo.swissalti3d` | 1 km tiles, editions 2019 and 2024 for all six village tiles; COG GeoTIFF at 0.5 m (18.1 MB per tile) and 2 m (1.2 MB); EPSG:2056 + EPSG:5728 (LN02 heights) | Terrain (M1) |
| swissSURFACE3D | `ch.swisstopo.swisssurface3d` / `…-raster` | LAZ point cloud 169–287 MB per tile; the 0.5 m surface-model COG per tile, 15.5–16.9 MB, one edition per tile (2623-1095 2022, the five others 2021; flown 2021–2022) | The trees (M3): the raster, not the LAZ |
| swissBUILDINGS3D 3.0 | `ch.swisstopo.swissbuildings3d_3_0` | Current edition (2026) only as ONE national FileGDB of 14.1 GB; per-map-sheet items exist for 2015/2016 and 2020 (sheet 1348-11: 9.1 MB GDB zip; the village's six sheets 14.2 MB together, 14'210'379 bytes, measured 2026-09-25). 2.0 (`ch.swisstopo.swissbuildings3d_2`) has per-sheet DXF up to 2024-05, but 1'272 of its 2'376 village parts are open meshes (measured) | Buildings (M2): the 2020 edition per map sheet, the owner's choice (§8 *The buildings*; §13 row 22) |
| SWISSIMAGE 10 cm | `ch.swisstopo.swissimage-dop10` | 1 km tiles, editions 2017, 2020, 2023; 2023 flown 6–7 Sep 2023 (~11:30 UTC), its real detail over Zermatt 25 cm published at 10 cm; 43–45 MB per tile (0.1 m, JPEG-in-COG), 0.2 MB (2 m) | The photo on the terrain and the roof colours (M3): edition 2023 at 0.1 m, the owner's choice (§13 rows 29, 30) |
| swissTLM3D | `ch.swisstopo.swisstlm3d` | National only (2026-02): 2.88 GB FileGDB zip (per-table deflated members), 4.8 GB GeoPackage zip (one deflated 10.8 GB member, unreadable in part) | Roads, paths, water, rock on the terrain and the trees' cleaning (M3): the FileGDB, read from its zip (§13 row 33) |
| swissNAMES3D | `ch.swisstopo.swissnames3d` | National (2026): CSV/GDB/GPKG/SHP | Place names |

Pinned editions live in `config/datasets.json`; the pipeline never asks for "the latest"
(Hard Rule 5: same inputs, same outputs). A new edition is a deliberate config change.
swisstopo can also republish a tile inside an edition (its STAC item carries an `updated`
time); the M0 download would then fetch the new file and `provenance.json` would change,
visibly but without anyone deciding it. Decided at the M0 close, built in M1: the
repository pins the SHA-256 of every tile the pipeline uses, and the download refuses a
published checksum that differs from the pinned one, so a republished tile is a deliberate
change like a new edition.

**The lock** (form chosen at M1 planning, 2026-09-25, brief M1-01; the buildings' entry
since M2-03): `config/datasets.lock.json`, written only by `python -m mattini lock terrain`
and `python -m mattini lock buildings` from the checksums swisstopo publishes (STAC items
only, no file is downloaded) and committed, like `uv.lock`. Each command replaces its own
entry and keeps the other. `{"schema": 1, "datasets": {"swissalti3d": {"collection",
"edition", "resolution_m", "tiles": {"<tile>": {"file", "sha256"}}}, "swissbuildings3d":
{"collection", "edition", "sheets": {"<sheet>": {"file", "sha256"}}}}}`, exact key sets,
sorted keys, 2-space indent, LF. `download terrain` and `download buildings` compare every
published checksum with the lock before they fetch or delete anything, and refuse a
difference, naming the tile or sheet, both values and the command. A lock written by a
command (rather than checksums typed into `datasets.json`) scales to M5's many tiles. The
six 2024 village tiles' checksums were re-read from the live STAC items on 2026-09-25 and
equal those brief M0-04 recorded; the six 2020 village sheets' were read at M2 planning
and again by the M2 review (identical). Adopting a new edition or a republished file is a
design change, not a command: after `lock`, design recomputes the expected values in
`config/terrain.json` and `config/buildings.json` and their `computed_for` (§8), and until
it does, the steps and `manifest` refuse, saying so (M2 R1 P-02, I-01).

**The photo, the surface model and swissTLM3D (M3 planning, 2026-10-14; brief M3-03).**

*Datasets.* `config/datasets.json` gains `swissimage` (`ch.swisstopo.swissimage-dop10`,
edition `2023`, `resolution_m` 0.1), `swisssurface3d` (`ch.swisstopo.swisssurface3d-raster`,
`editions` `["2021", "2022"]`, `resolution_m` 0.5) and `swisstlm3d` (`ch.swisstopo.swisstlm3d`,
edition `2026-02`), each `© swisstopo`. A dataset names its collection, its attribution and
exactly one of `edition` (a year `YYYY`, or `YYYY-MM` with the month 01 to 12, as the
national products are named) or `editions` (a non-empty list of distinct years in ascending
order: the editions a tile may be published in, exactly one per tile; swissSURFACE3D covers
the village with two flights, 2623-1095 in 2022 and the five others in 2021, measured).
Both or neither is refused as "exactly one of edition and editions", naming the file and
the dataset. A command or step that needs one edition refuses a list, and the other way
round, naming config/datasets.json (a refusal, not a traceback; M2 R1 I-05).

*Items and assets.* Items are addressed by id: `swissimage-dop10_<edition>_<tile>`,
`swisssurface3d-raster_<year>_<tile>`, `swisstlm3d_<edition>`; the asset is the one whose key
ends `_<resolution>_2056.tif` (the photo; not the 2 m one), `_<resolution>_2056_5728.tif` (the
surface; not the `.xyz.zip`) or `_2056_5728.gdb.zip` (the TLM; not the GeoPackage, Shapefile
or INTERLIS zip). A surface item that answers HTTP 404 is absent; any other failure to read
an item is "cannot read the STAC item", never an absence. `file:checksum` comes in
upper-case hex (all 28 assets read); the lock stores lower-case.

*The lock.* Three more entries, exact key sets: `swissimage` {collection, edition,
resolution_m, tiles: {<tile>: {file, sha256}}}; `swisssurface3d` {collection, resolution_m,
tiles: {<tile>: {edition, file, sha256}}}; `swisstlm3d` {collection, edition, file, sha256}.
They are written only by `python -m mattini lock photo`, `lock surface` and `lock tlm`,
from the STAC items only (no request to the file host, not even a HEAD), each replacing its
own entry and keeping every other, sorted, 2-space indent, LF. `lock surface` reads, for
every tile of the area, the item of every year in `editions`; exactly one must exist, else
it refuses naming the tile and the years found (`found none`, `found ['2021', '2022']`) and
writes nothing. A malformed lock is refused naming the file and the five lock commands.

*The downloads.* `download photo`, `download surface` and `download tlm` (`--out`, default
data/raw) write `swissimage/<edition>/`, `swisssurface3d/<editions joined by "-">/`
(`2021-2022`) and `swisstlm3d/<edition>/` under the root, each holding the files under
swisstopo's names and a provenance.json like the terrain's: swissimage with exactly the
terrain's keys; swisssurface3d with `editions` (the config's list) for `edition` and each
tile's `edition` added; swisstlm3d flat, exactly {attribution, collection, dataset,
edition, file, item, schema, sha256, size_bytes, url}. The command prints the provenance
path. Each first checks that the lock's entry is for the config (collection, edition or
editions, resolution; exactly the area's tiles; every surface tile's edition one of
`editions`), naming its lock command; then it compares every published file name and
SHA-256 with the lock before any request for a file and before anything on disk changes,
and refuses a difference naming the tile (`swisstlm3d <edition>` for the TLM), both
checksums and "nothing was fetched", then "A republished tile (file) is adopted only on
purpose: `python -m mattini lock <x>`, then commit the lock, then design recomputes the
expected values in <configs> (docs/SPEC.md §8)", the configs being those whose expected
values record the entry: photo config/photo.json and config/roofs.json, surface
config/trees.json, tlm config/surfaces.json and config/trees.json. `download surface` reads,
for each tile, only the item of the edition the lock pins: choosing the edition is the
lock's, so an edition swisstopo publishes later stops no download of the pinned files (the
next `lock surface` refuses it, and design decides). The photo's and the surface's files
download as the terrain's: `.part`, verified, renamed, one retry, a verified file kept.

*The TLM file* (2'882'823'552 bytes, national). A verified file already there is kept with
no request to the file host. Otherwise the download asks the file host first (HEAD): its
Content-Length is the size, and an `x-amz-meta-sha256` that is present and not the lock's
is refused before any GET, naming the URL and both checksums ("nothing was fetched"; the
file host and the STAC item disagree, try again later). The file downloads to
`<file>.part`. Each GET asks `Range: bytes=<part size>-` once the part holds bytes; a 206
must start there (else the part is deleted), a 200 is the whole file and rewrites the part.
Python's urllib ends a cut body without an error (brain.md H9), so the part's size, not an
exception, shows a cut: a short part is resumed, up to five GETs per round. A part that
reaches the size is verified: equal to the lock's SHA-256 it takes the file's name;
otherwise it is deleted and fetched again once, in a second round with five GETs of its own
(ten at most per run; M3-03 Findings 4, kept 2026-10-15, §13 row 40), then refused. A run that cannot finish
keeps its part and says so, naming `python -m mattini download tlm`, which resumes it; a
Ctrl-C or a crash keeps it too. provenance.json is removed before the first change on disk
and written at the end, as the terrain's. Measured: the host answers Range with 206 and
Content-Range (its HEAD sends no Accept-Ranges) and a range at the end with 416; a real
download stopped at 1.08 GB (Ctrl-C, and `kill -9`) resumed with one Range request and
verified.

*Measured entries (2026-10-14):* `entry_sha256` swissimage 415ed9bc…, swisssurface3d
f73033b1…, swisstlm3d aa909f98… (every file's SHA-256 is in brief M3-03's pinned `test_measured_photo_surface_tlm.py`,
which compares the committed lock with them, and in design's notes
`docs/briefs/sketches/m3-design.md` §1; the entries', the lock's and the provenance files'
SHA-256s are in the brief's decision 7).

*Decided at M3 planning with the measurements:* `resolution_m` is required for `swissimage` and
`swisssurface3d`, as for `swissalti3d` (M3-01); the terrain's and the buildings' republish
refusals name their new dependants too (swissalti3d: config/terrain.json and
config/trees.json; swissbuildings3d: config/buildings.json, config/roofs.json and
config/trees.json); a Ctrl-C in `download tlm` keeps the part and says how to resume, with no
traceback.

## 6. Coordinates (confirmed by the owner on day one)

- Source: Swiss LV95 (EPSG:2056) with LN02 heights (EPSG:5728).
- **Local origin: E 2'623'000 / N 1'096'000** (owner: option c), the south-west corner of
  swissALTI3D tile 2623-1096, which holds the church square. Game chunks line up with
  swisstopo's 1 km tiles and every offset is a whole number.
- 1 Godot unit = 1 m. Godot is Y-up, −Z forward: **x = E − 2'623'000, y = H (real LN02
  metres, no vertical offset), z = −(N − 1'096'000).** This mapping is a rotation, not a
  mirror (east × north = up holds after mapping).
- `height_offset_m` in `config/world.json` is the vertical part of the origin:
  y = H − height_offset_m, and H = y + height_offset_m back, as both halves compute it and
  their tests pin (ruled at the M0 close). It is 0.0, which gives y = H as above; a
  non-zero value lowers the whole world in Godot by that many metres and is a design
  change.
- The one home is `config/world.json` (CLAUDE.md Hard Rule 4). The pipeline reads it; the
  pipeline copies it verbatim into the generated manifest with its SHA-256; the game reads
  the origin and axes only from the manifest (an exported game cannot read files outside
  its own project). A test ties the manifest's copy to `config/world.json`.
- Precision: Godot's `Vector3` is 32-bit; an LV95 coordinate near 2.6 million loses about
  0.25 m in 32 bits. The origin is always subtracted in 64-bit (`float` in GDScript, Python
  floats) before a `Vector3` is built. 32-bit floats keep about 2 mm at 20 km from the
  origin; the Matterhorn summit is 8.3 km from the church square.
- Shared test vectors: `tests/shared/world_vectors.json`, read by the pipeline's and the
  game's tests (the seam between the two halves).

## 7. Areas

**Village area (the M1 test area):** "The entire village" (owner, day one), measured as the
tile-aligned box **E 2'623'000–2'625'000 / N 1'095'000–1'098'000** (2 km × 3 km, six
swissALTI3D tiles: 2623-1095 … 2624-1097). Local coordinates: x 0 … 2000, z −2000 … +1000.

How it was measured: the Federal Register of Buildings and Dwellings (BFS public extract
for Valais, 23 September 2026) lists 1'913 existing buildings in the municipality of
Zermatt (BFS no. 6300). Grouping buildings that lie within 60–100 m of each other gives
one main village cluster of 1'455–1'500 buildings spanning E 2'623'222–2'624'857 /
N 1'095'445–1'097'750; the hamlets (Furi, Zmutt, Findeln and others) form separate
clusters. The box holds the whole main cluster and 1'524 of the 1'913 buildings (80%).
The register was used only to measure the box; it is not a game input.

**Backdrop and the larger area (M5):** extents and resolutions **OPEN**.
**In-game terrain resolution for the village: 0.5 m** (owner, 2026-09-25: "just do 0.5
first for the demo at least, I want to see the capabilities, then I can still soften it
later if needed"). It is one value in `config/terrain.json`; for the terrain, 1 or 2 m is a
config change and a pipeline re-run, no code change. The trees tie it to 0.5 m: they take
their base heights from the 0.5 m grid and refuse any other spacing (the owner, 2026-10-15,
§13 row 37), so softening the terrain first needs the trees step to take its heights at that
spacing, built when it is wanted. Measured at 0.5 m: 4001 × 6001 vertices, a 96 MB
heights file, 2.9 s to load into Terrain3D and about 540 MB of memory in a headless run.

## 8. Architecture (confirmed by the owner on day one)

```
swisstopo STAC API
  → pipeline/  (Python package `mattini`, offline, re-runnable)
       download → crop → re-origin → terrain for Terrain3D (+ LODs where needed)
       → buildings per 1 km chunk (a raw mesh file) → splat maps (SWISSIMAGE + land cover)
       → tree points (surface model − terrain) → vectors (paths, rivers, rail, lifts)
       → manifest
  → game/assets/generated/   chunks + manifest.json
  → game/  Godot: chunk loading, Terrain3D terrain, buildings, materials from the data,
           sun/moon cycle, sky, weather, free-fly camera, walking
```

The game reads only `game/assets/generated/` and its manifest. Start with the village area
end to end before scaling up.

**The manifest** (`game/assets/generated/manifest.json`) is written by the pipeline and is
the game's only source of generated data. It carries at least: `schema` (1), `world` (a
verbatim copy of `config/world.json`) and `world_sha256`; later the datasets used (each
with its edition, inputs' checksums and attribution) and the chunk lists. The credits
screen is generated from it. From M1 its top level is exactly `schema`, `terrain`,
`world` and `world_sha256`; from M2 `buildings` joins them (null until built); from M3 (brief
M3-13) it is exactly `buildings`, `photo`, `roofs`, `schema`, `surfaces`, `terrain`, `trees`,
`world` and `world_sha256`, each block null until built.

**The terrain grid (M1; designed at M1 planning, 2026-09-25).** Tier 1 territory: it
places heights in the world (WORKFLOW §Review policy).

- *Config:* `config/terrain.json`, `{"schema": 1, "areas": {"village": {"computed_for":
  {…}, "expected_sha256": {"0.5": …, "1": …, "2": …}, "spacing_m": 0.5}}}`: one area,
  which is also the area the download, the lock and the buildings serve (M2-01, M1 R1
  T-06); spacing 0.5, 1 or 2 m (the source is 0.5 m); the expected output per spacing and
  what it was computed for (below).
- *Inputs:* the tiles listed in the download's `provenance.json` only (D9), refused
  unless its edition, resolution and tile list match the config; every file's SHA-256
  equal to the lock's; every tile where its id says (EPSG:2056, 2000 × 2000 pixels of
  0.5 m, its 1 km square); no nodata and no non-finite value. Each refusal names the tile
  and the command that fixes it.
- *The grid:* a vertex every `spacing_m` from the area's north-west corner, its edges
  included: `(e_max − e_min) / s + 1` columns by `(n_max − n_min) / s + 1` rows (the village
  at 0.5 m: 4001 × 6001). Row r, column c is the vertex at LV95 (e_min + c·s, n_max − r·s),
  which is local x = x_min + c·s, z = z_min + r·s. Only the owner's mapping (x = +e,
  y = +h, z = −n) is supported for terrain; both halves refuse another, so a rotated world
  cannot be mis-placed silently.
- *The heights:* each vertex's height is the area-weighted mean of the source pixels under
  the s × s square centred on it, clipped to the area, minus `height_offset_m` (so local
  y), computed in 64-bit and rounded once to 32-bit. For 0.5 and 1 m that is the mean of
  the 2 × 2 pixels around the vertex; for 2 m of the 4 × 4; at the area's edges only the
  pixels inside count. Why: swissALTI3D pixels are areas whose centres lie 0.25 m off the
  metre grid, while Terrain3D's vertices sit at whole multiples of the spacing (measured
  2026-09-24). The sums of up to 16 32-bit heights are exact in 64-bit, and so is the
  subtraction of every offset in use (0, 1000 and −12.25 m; an offset with many binary
  fraction digits would round twice, by at most one 32-bit step, M1 R1 T-08), so every
  correct implementation gives the same bits on every machine: the village at 0.5 m is
  `b6334c1fdc992f0576bc59efd51484db2178cbe399ad46512a4bf510abb9411a` (96'040'004 bytes),
  measured with two independent implementations; seven flat and sloped points agree with
  swisstopo's height service within 0.19 m.
- *The files:* `game/assets/generated/terrain/<area>.f32`, little-endian 32-bit floats,
  row-major, rows north to south (+z), columns west to east (+x), no header; its
  description `terrain/<area>.json` next to it, which `manifest` copies verbatim into the
  manifest's `terrain` block: exactly `area`, `columns`, `file` (relative to the manifest's
  folder), `format` (`float32-le`), `lv95_box`, `rows`, `sha256`, `source` (`attribution`,
  `collection`, `dataset`, `edition`, `resolution_m`, `tiles` [`sha256`, `tile`]),
  `spacing_m`, `world_sha256`. `terrain` is null until a terrain is built.
  `python -m mattini terrain` builds it and rewrites the manifest; `manifest` refuses a
  built terrain whose `world_sha256`, spacing, edition, resolution or heights file no
  longer match, naming `python -m mattini terrain` (a changed height offset would
  otherwise lift or sink the world, Hard Rule 4). From M2 it also refuses a `source` that
  is not exactly the datasets config's attribution, collection, edition and resolution
  and, in order, the tiles covering the area with the SHA-256s the lock pins (exact key
  sets; M1 R1 T-03, T-04).
- *The expected output (M2 planning, 2026-09-25; lesson 38):* the SHA-256 of every
  heights file the configured area can be built to is design data in
  `config/terrain.json`, keyed by spacing as swisstopo writes it (`"0.5"`, `"1"`, `"2"`).
  The village: 0.5 m `b6334c1f…` (above), 1 m
  `71bd4f174dfc3d07a3becace073c62bdf6b5cc010072a5e483a484210e8bc333` (24'020'004 bytes),
  2 m `d6c1d558fee28c91472f2fea9c5db06d9b74480dd22f77554bf7037beec794ce` (6'010'004 bytes),
  each computed two independent ways (the pipeline's code and an exact area-overlap
  implementation that shares none of it). `terrain` compares its output with the value
  for its spacing before writing anything and refuses a difference, naming both;
  `manifest` refuses any other file. So the owner's switch to 1 or 2 m (§7) stays a
  config change for the terrain (the trees refuse it, §7), and a machine or a code change that computes other heights says so
  itself (M1 R1 T-01). A gate test builds a terrain from 2 × 2 synthetic tiles cut by
  its area, pinned to exact bytes at 2 m and 0.5 m.
  Each area also records what its values were computed for (M2 R1 P-02, I-01; brief
  M2-07): `computed_for`, exactly `{"inputs_sha256", "world_sha256"}`, the SHA-256 of
  `config/world.json`'s bytes and of the lock's entry for the dataset rendered canonically
  (`json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`, UTF-8).
  The step and `manifest` compare both before any output, and refuse a difference as what
  it is: a changed world or adopted new inputs, a design change after which design
  recomputes the expected values, never a fault of the machine or the code. Their order
  (from brief M3-01, M2 V1-P-01 and P-07): the world, then the lock's fit, then the inputs,
  then provenance and files (the step) or the block (`manifest`). The fit is one rule for
  download, step and `manifest`: the entry's collection, edition and resolution are the
  datasets config's, and it pins exactly the area's tiles or sheets; an unfitting lock is
  refused naming `python -m mattini lock <x>` and no other command. A missing download is
  refused naming `python -m mattini download <x>`, before anything is written: no
  provenance before any progress line, a file it lists absent when that file is read. An area's keys are
  exactly `computed_for`, `expected_sha256` and `spacing_m`.
- *The game:* `TerrainGrid` reads the block and the file, checks the file's size and
  SHA-256 and the block against its own manifest (not the box against the world config's
  area: `manifest` is the one check of the box, rows and columns, M2-06, and every
  manifest the game reads is written by it), and places the grid through
  `WorldConfig` (x_min, z_min from the box's north-west corner), never by subtracting an
  origin itself. `TerrainLoader` builds the Terrain3D node: vertex spacing = the grid's
  spacing; regions 1024 m wide (region size 1024 / spacing vertices; with Terrain3D's 32 × 32
  region map that allows ±16 km around the origin); the heights imported as region-aligned
  images, because `import_images` snaps an image to the corner of its region; vertices of
  the loaded regions outside the grid are holes; world background none and no collision in
  M1; the ordering Terrain3D needs (brain.md H11).
- *Shared fixture:* `tests/shared/terrain_fixture/` and `tests/shared/terrain_vectors.json`
  (a synthetic world with a different origin and a 1000 m height offset, a 23 × 40 pixel
  source and the expected output, computed by design two independent ways): the pipeline
  must reproduce it byte for byte and the game must read its heights back from Terrain3D
  on their own vertices. That is the seam between the halves (lesson 3). A second one
  since M2 (M1 R1 T-02): `tests/shared/terrain_fixture_nw/` and
  `tests/shared/terrain_vectors_nw.json`, a world whose grid lies north-west of its origin
  (x −1036 … −1012, z −1034 … −1008), at 2 m, across the edges of four Terrain3D regions,
  with a height offset of −12.25 m, where the village's placement differs from the first
  fixture's. Each fixture folder holds a `datasets.lock.json` pinning its source as the
  1 km tile it lies in (M2-01, for T-04's check).

**The buildings (M2; designed at M2 planning, 2026-09-25, on the source of §13 row 22,
which the owner chose).** Tier 1 territory: it places buildings in the world (WORKFLOW §Review
policy).

- *Source:* swissBUILDINGS3D 3.0 beta, edition 2020, per map sheet: STAC collection
  `ch.swisstopo.swissbuildings3d_3_0`, item `swissbuildings3d_3_0_2020_<sheet>`, asset
  `swissbuildings3d_3_0_2020_<sheet>_2056_5728.gdb.zip`, a zipped FileGDB holding one
  folder `<name>.gdb`; its layer `Building_solid` holds one closed triangle solid per
  building (an Esri MultiPatch, which fiona reads as a MultiPolygon Z whose every polygon
  is one triangle), EPSG:2056 with LN02 heights, attributes including `UUID` and
  `OBJEKTART`.
- *Sheets:* the LK25 sheet `1000 + 20 r + c` covers E 2'480'000 + 17'500 c to
  2'480'000 + 17'500 (c + 1), N 1'302'000 − 12'000 (r + 1) to 1'302'000 − 12'000 r. Its
  sixteenth `<sheet>-<q><s>` is quadrant q (1 north-west, 2 north-east, 3 south-west,
  4 south-east; 8'750 m × 6'000 m), then sub-quadrant s of it (same order;
  4'375 m × 3'000 m). Example: 1348-11 is E 2'620'000–2'624'375, N 1'095'000–1'098'000.
  The buildings step uses every sheet whose box comes within 100 m of the area's box
  (distance ≤ 100 m, touching included), sorted by sheet id as text, and selects buildings
  by the area, never by their sheet. Measured at M2 planning: the grid matches all 34
  sheets of the 2020 edition around Zermatt within 7 mm; buildings overhang their sheet by
  up to about 12 m; three of the 2'134 in the village's six sheets have their bounding-box
  centre up to 3.6 m outside their own sheet; no building is in two sheets. The grid
  places only the sheets 1000 to 1999 and nothing east of E 2'830'000: `sheet_box` refuses
  an id of 2000 or above, and `sheets_near` a box within the margin of that edge, since
  other ids follow another scheme (M2 R1 I-06). The lock's `swissbuildings3d` entry pins
  exactly the area's sheets: `download buildings` and the step refuse another set, naming
  `python -m mattini lock buildings`, and `manifest` refuses it too (I-04). The download's refusal of
  a republished file adds design's step: after the lock, design recomputes the expected
  values (P-02, I-01).
- *Reading:* each zip is opened from the very bytes whose SHA-256 was checked against the
  lock; its one `.gdb` folder, layer `Building_solid`. Every feature must have a
  non-empty text `UUID`, and a geometry that is a MultiPolygon Z whose every polygon is
  exactly one ring of four points with the first equal to the last (a triangle), else the
  feature is refused (naming sheet and UUID).
- *Snapping:* every coordinate is snapped to the file's storage grid in 64-bit:
  E' = round(E × 1000) / 1000, N' = round(N × 1000) / 1000 (1 mm), H' = round(H × 10000) /
  10000 (0.1 mm), where round is round-half-to-even to an integer and the division is the
  correctly rounded 64-bit division. A coordinate whose |v − v'| exceeds 1e-6 m is refused
  (a finer grid is a design change).
- *Which buildings:* those whose bounding-box centre ((E'min + E'max) / 2, (N'min +
  N'max) / 2), over all its snapped vertices, in 64-bit, lies in the area box with the
  west and south edges included and the east and north edges excluded:
  e_min ≤ Ec < e_max and n_min ≤ Nc < n_max. A UUID seen twice among the selected
  buildings is refused.
- *Each building:*
  1. Its vertices are welded by exact equality of (E', N', H') and numbered from 0 in the
     order of their first appearance, reading the triangles in the order fiona gives them
     and each triangle's three points in ring order (the ring's closing point dropped).
  2. It must be a closed, consistently oriented triangle mesh: no triangle repeats a
     vertex number, and every directed edge (a, b) of its triangles occurs exactly once and
     its reverse (b, a) exactly once. Otherwise it is refused (naming sheet and UUID).
  3. Its signed volume V = Σ over triangles (a, b, c) of a · (b × c) / 6, computed in
     64-bit on the vertices minus the building's vertex 0, in triangle order, left to
     right. V = 0 is refused. If V < 0, every triangle (a, b, c) becomes (a, c, b); the
     vertex numbering does not change. So the output is counter-clockwise seen from outside:
     (b − a) × (c − a) points out of the building. (swisstopo's 2020 solids all read V < 0,
     measured.)
- *Placement:* each vertex's local (x, y, z) is the world config's to_local(E', N', H') in
  64-bit (x = E' − origin_e, y = H' − height_offset_m, z = −(N' − origin_n) for the
  owner's axes; generally the configured rotation), then each component rounded once to
  32-bit float (round-half-to-even).
- *Chunks:* a building belongs to the 1 km tile holding its bounding-box centre:
  `<floor(Ec / 1000)>-<floor(Nc / 1000)>`. Within a chunk, buildings are ordered by UUID,
  compared as text (Python string order). A tile with no building has no chunk.
- *The chunk file* `buildings/<tile>.bin`: the chunk's vertex positions, then its triangles,
  no header. Vertices: each building's vertices in their numbering order, buildings in
  chunk order, each vertex as x, y, z little-endian float32 (12 bytes). Triangles: each
  building's triangles in their order, buildings in chunk order, each as three
  little-endian uint32 indices into the chunk's vertex list (a building's vertex number
  plus the count of vertices of the buildings before it in the chunk) (12 bytes). File size
  = 12 × vertices + 12 × triangles.
- *The description* `buildings/<area>.json` (sorted keys, 2-space indent, UTF-8, LF, final
  newline, like the terrain's), exactly: `area`; `chunks`, a list sorted by tile, each
  exactly `{"buildings": <count>, "file": "buildings/<tile>.bin", "sha256": <hex>, "tile":
  <tile>, "triangles": <count>, "vertices": <count>}`; `format`: `"mesh-f32-u32-le"`;
  `lv95_box`: `{"e_max", "e_min", "n_max", "n_min"}` of the area (floats); `source`:
  `{"attribution": "© swisstopo", "collection": "ch.swisstopo.swissbuildings3d_3_0",
  "dataset": "swissbuildings3d", "edition": "2020", "sheets": [{"sha256": <zip's sha256>,
  "sheet": <sheet id>} … sorted by sheet]}`; `world_sha256`: the SHA-256 of the world
  config's bytes.
- *Expected output (lesson 38):* `config/buildings.json`, `{"schema": 1, "areas":
  {"village": {"computed_for": {…}, "expected_sha256": {"<tile>": "<sha256>", …}}}}`, the
  one area being the terrain config's, `computed_for` as the terrain's (above, for the
  `swissbuildings3d` entry). The village's six chunks were computed by design two
  independent ways at M2 planning (identical bytes): 1'486 buildings, 92'594 vertices,
  178'910 triangles, 3'258'048 bytes in all. The buildings step compares every chunk with it before writing
  anything; `manifest` refuses any other file. `manifest` also refuses a block whose key
  sets are not exact, whose `world_sha256` is not the world config's, whose `source` is not
  the datasets config's attribution, collection and edition and the lock's sheets with
  their SHA-256s in order, or whose chunk files' sizes or SHA-256s differ; each refusal
  names `python -m mattini buildings`. It also refuses a `lv95_box` other than the world
  config's box for the area (M2 R1 P-03). A build removes the chunk files of an earlier
  build that its block no longer lists (M2 R1 G-06).
- *The game:* `BuildingChunks` reads the block and the files, checks each file's path, size
  and SHA-256, the indices, and the block's `world_sha256` against its manifest, and that
  the `WorldConfig` it is given was read from that manifest (the same origin, height
  offset, and local vectors for one metre east, north and up; M2 R1 P-04), and never
  converts a coordinate: the pipeline wrote local coordinates for the world config that
  `world_sha256` pins. `BuildingLoader` makes one flat-shaded mesh per chunk under a
  `Buildings` node. Each triangle's normal is `normalize((b − a) × (c − a))` in the file's
  order, pointing out. The triangle goes into Godot's arrays as (a, c, b), because Godot's
  front faces are clockwise (measured: `SurfaceTool.generate_normals` gives (0, 1, 0) for
  the triangle (0,0,0), (1,0,0), (0,0,1), whose right-hand normal is (0, −1, 0)). A
  triangle whose normal has y ≥ 0.5 is roof, the rest wall.
- *How the buildings meet the terrain (measured on the real village, 2026-09-25):* every
  solid has a flat floor (spread under 1 cm) below the terrain around it, typically 2.4 m
  below its lowest corner. So no building floats and nothing is added under them. Twelve
  of 1'486 stand above the 2024 terrain at a corner, by up to 4.1 m (four by more than
  1 m, two of them marked *Im Bau*). The terrain is 2024, the buildings' survey mostly
  2012. The other way round, eight have their roof below the 2024 ground at their
  bounding-box centre, so the game shows them barely or not at all (M2 R1 P-05): one is
  *Gebaeude unsichtbar* (swisstopo's own invisible class,
  `{B7632268-A860-45C7-B4F7-8A5A24657354}`), one *Im Bau*
  (`{CEB91F2C-E78C-4334-885C-6E386C2E6B8B}`), and six *Gebaeude Einzelhaus*
  (`{051BEC10-3D8E-4FE3-8B36-F759B9BFE607}`, `{0D9071AA-1931-406C-B945-635254849B3F}`,
  `{2CA4128A-BFC7-4E4B-859D-8BE908BFD458}`, `{366C806F-F781-43DD-A7E5-6F46D0D0A1F5}`,
  `{93962B42-C282-4FB5-A849-802A203901F1}`, `{E4B87A5D-EEC6-4C07-B910-622D217D1EC7}`).
  In all, 1'475 of the 1'486 have the ground at their centre between floor and roof, the
  same count in the game with Terrain3D loaded and on the pipeline's grid. They are shown
  as the data has them (Hard Rule 2), and the release record names both groups for the
  owner to look at.
- *Shared fixture:* `tests/shared/buildings_fixture/` and
  `tests/shared/buildings_vectors.json`: a synthetic world (origin E 2'650'000 /
  N 1'150'000, height offset 500 m) with eleven buildings as the reader hands them over.
  They cover a solid to reverse and one to keep, centres exactly on the area's west, east
  and north edges and on a tile boundary, and a building whose vertex mean lies in
  another tile than its bounding-box centre. Its expected output was computed two
  independent ways. The pipeline must reproduce it byte for byte, and the game must find
  its named vertices at `WorldConfig.to_local` of their LV95 points: the seam (lesson 3).

**The photo (M3; designed at M3 planning, 2026-10-14; the owner's 0.2 m, §13 row 30).** Tier 1
territory where it places the photo in the world (the rectangle), Tier 2 elsewhere.

- *Inputs:* the area's SWISSIMAGE 2023 tiles at 0.1 m (§5), the tiles the area box meets,
  read from `<raw>/swissimage/2023/` and its provenance; each file's SHA-256 equal to the
  provenance's and the lock's, read from the very bytes hashed; refused unless EPSG:2056,
  10'000 × 10'000 pixels, 3 uint8 bands and the transform exactly (0.1, 0, E0, 0, −0.1,
  N0 + 1000) for its tile. Measured: three JPEG decoders give the tiles' pixels identically.
- *The grid:* `cell_m` from `config/photo.json`, one of 0.2, 0.5, 1 (k = 2, 5, 10). Box
  arithmetic in integer decimetres: an edge off the 0.1 m grid by more than 1e-6 m, or a side
  not a whole number of cells, is refused. Texel (r, c), r from the north, c from the west, is
  the k × k block of 0.1 m source pixels from the area's north-west corner (rows r·k … r·k +
  k − 1, columns c·k … c·k + k − 1); per channel its value is round-half-to-even(S / k²) of
  the exact integer sum S. The raw grid (rows north to south, columns west to east, RGB
  interleaved, uint8) hashes to `pixels_sha256`. A step may compute it in strips of whole
  texel rows; the bytes are the same.
- *The JPEG:* Pillow, `Image.frombuffer("RGB", (columns, rows), raw, "raw", "RGB", 0, 1)
  .save(f, "JPEG", quality=92, subsampling=2, optimize=False, progressive=False)`: baseline,
  4:2:0, no EXIF or ICC. Measured byte-identical across Pillow 10.4.0, 11.0.0, 12.3.0 and with
  libjpeg-turbo's SIMD off; Godot 4.6.3's decoder (libjpeg-turbo 3.1.0) gives the same pixels
  as Pillow's for the village.
- *The files:* `photo/<area>.jpg`, then `photo/<area>.jpg.import` holding exactly
  `[remap]\n\nimporter="keep"\n` (brain.md H24), then `photo/<area>.json`, each through a
  `.part` rename. The description is exactly {area, cell_m, columns, file
  (`photo/<area>.jpg`), format (`jpeg`), jpeg: {quality: 92, subsampling: "4:2:0"}, lv95_box,
  pixels_sha256, rows, sha256 (the JPEG's), source: {attribution, collection, dataset
  (`swissimage`), edition, resolution_m (0.1), tiles: [{sha256, tile}] by tile},
  world_sha256}; it does not list the `.import`.
- *The expected output (lesson 38):* `config/photo.json`, `{"schema": 1, "areas": {<area>:
  {"cell_m", "computed_for", "expected_pixels_sha256": {"0.2", "0.5", "1"},
  "expected_sha256": {"0.2", "0.5", "1"}}}}`, computed two independent ways for the village
  (identical bytes, and a third time by another agent): 0.2 m pixels `00533bc6…`, JPEG
  `cf83c705…` (50'222'573 bytes); 0.5 m `1e105d47…`, `5035fe52…`; 1 m `b99f0710…`,
  `db1d1b78…`. The step compares `computed_for` (world, then inputs once the lock fits), then
  the pixels ("this machine or this code computes other pixels than design's"), then the
  JPEG ("the pixels are design's; this machine's JPEG encoder writes other bytes: Pillow <v>,
  libjpeg-turbo <v>"), before it writes anything; `manifest` refuses any other file, a
  `.import` missing or different, or a description that does not fit the configs and the
  lock, naming `python -m mattini photo`.
- *The API (brief M3-04):* `pipeline/mattini/photo.py`: `photo_grid(mosaic, box, cell_m)`,
  `encode_jpeg(pixels)`, `write_photo(...)`, `build_photo(world, datasets, lock,
  photo_config, raw_root, out_dir, *, progress=None)`, `built_photo_block(out_dir,
  photo_config, world, world_sha256, datasets, lock=LOCK_PATH)`.
- *The game (brief M3-09):* `PhotoGrid.from_manifest(path, world)` reads the `photo` block
  and checks its key set, its `world_sha256` against its manifest, that the WorldConfig is the
  manifest's with the owner's axes (another mapping is refused, as the terrain's), the cell,
  columns × cell and rows × cell against the box within 1 mm, the file's path and SHA-256, and the decoded size (columns ×
  rows, RGB8); it makes an `ImageTexture` with mipmaps (RGB8: about 0.8 GB of GPU memory as
  RGBA8 on Vulkan; an exported build cannot compress at runtime, H21). The rectangle comes
  from WorldConfig only: its north-west corner is `to_local(e_min, n_max, h)` (x0, z0); it
  spans x0 … x0 + columns·cell, z0 … z0 + rows·cell; the shader's uv is (world.xz − (x0, z0))
  / (columns·cell, rows·cell), texel (c, r) centred at ((c + 0.5)/columns, (r + 0.5)/rows).
  Measured: decoding the village JPEG takes 1.3–1.6 s headless, mipmaps 0.3 s; a 16384-wide
  texture draws, a 16385-wide one is black with no error (H21).
- *Shared fixture:* `tests/shared/photo_fixture/` and `tests/shared/photo_vectors.json`: a
  synthetic world (origin E 2'610'000 / N 1'170'000, height offset 250 m), a 16 m × 8 m area
  whose north-west corner is off the 0.2 m lattice from the origin, a synthetic 0.1 m source
  of grey 8 × 8-texel blocks (lossless through the JPEG) and one coloured 16 × 16 corner (a
  channel swap shows), with designed rounding ties; the expected output at all three cells,
  computed two ways; 13 named points that catch half a texel, flips, swapped axes and the
  wrong corner. The pipeline reproduces it byte for byte; the game reads the named texels.

**Roof colours (M3; designed at M3 planning, 2026-10-14; brief M3-05, the game M3-12).** Each
selected building's roof colour from the 2023 photo, and its id and counts in its chunk.

- *Inputs:* the buildings' sheets and the photo's 0.1 m tiles (§5), each checked as their
  own steps check them; `computed_for.inputs_sha256` is the SHA-256 of the canonical
  `{"swissbuildings3d": <entry>, "swissimage": <entry>}` object (json.dumps with sorted keys,
  separators "," and ":", UTF-8; the same for every step with several datasets).
- *Buildings:* exactly the buildings step's selection, snapping, orientation, chunks and
  order (above). In integer units of 0.1 mm (E_u = round(E' · 10000), likewise N and H; exact
  on the snapped grids):
  - a *roof triangle*, with a, b, c in triangle order (counter-clockwise from outside) and
    n = (b − a) × (c − a): n_H > 0 and 4·n_H² ≥ n_E² + n_N² + n_H² (the unit normal's up
    component at least 0.5, the game's rule; an exact 60° cannot occur with integer normals);
  - its *roof pixels*: the photo's 0.1 m pixels whose centre (E0 + 0.05 + 0.1 i, likewise N
    from the tile's top) lies inside or on the boundary of the plan projection of at least one
    roof triangle, by exact integer orientation tests; pixels outside the photo are not
    counted, never refused;
  - its *colour*: per channel the lower median of its roof pixels (sorted ascending, the
    element at floor((n − 1) / 2)); null when n = 0.
- *The file* `roofs/<area>.json` (sorted keys, 2-space indent, UTF-8, LF, final newline): exactly
  {area, chunks: [{buildings: [{roof: "rrggbb" (lower-case) or null, roof_pixels, triangles,
  uuid, vertices}] in chunk order, tile}] by tile, format "roofs-v1", lv95_box, source:
  {buildings, photo}, world_sha256}; `triangles` and `vertices` are the building's counts in
  its chunk file, so each chunk's sums equal the chunk's. The manifest carries it verbatim as
  its `roofs` block (the block is the data, as the buildings' block is their description);
  `manifest` refuses it when no buildings are built or its chunks do not match theirs.
- *The expected output:* `config/roofs.json`, `{"schema": 1, "areas": {<area>:
  {"computed_for", "expected_sha256"}}}`; the village computed two independent ways:
  `8d9664b6…` (290'006 bytes), every one of the 1'486 buildings coloured, 32'452 roof
  triangles, 30'392'135 roof pixels. Measured: the 2020 outlines sit 1–2 m off the 2023
  photo in places; the median tolerates most of it.
- *The game:* `BuildingRoofs.from_manifest(path, world, chunks)` checks the block against
  BuildingChunks (the chunks in order, per chunk the building count and the sums of
  triangles and vertices, every building's triangles inside its own vertex range, UUIDs
  ascending) and against the manifest's buildings source. `BuildingLoader.create(chunks,
  parent, roofs)` gives each roof triangle (normal.y ≥ 0.5) of a coloured building its colour
  as an sRGB vertex colour; a building without a colour keeps `building_roofs.tres`. Every
  wall is one neutral plaster, albedo (0.78, 0.76, 0.72), roughness 0.9: a placeholder,
  labelled in the loader and the credits (the owner's "neutral", §13 row 31).
- *Shared fixture:* `tests/shared/roofs_fixture/` and `tests/shared/roofs_vectors.json`: the
  buildings fixture's world and eleven buildings, plus six built to tell the slope rule, the
  orientation, the pixel-centre and boundary rules and the median from their likeliest wrong
  twins; a synthetic photo in four `.u8` windows; the expected `roofs/fixture.json`
  computed two ways.

**The surfaces (M3; designed at M3 planning, 2026-10-14; the owner's "bring into m3 now", §13 row
33; brief M3-06, the game M3-10).** Roads, paths, water and rock from swissTLM3D as a class grid
on the photo's grid. Tier 1 where it places the grid (the rectangle), Tier 2 elsewhere.

- *Input:* the swisstlm3d FileGDB zip (§5), read with fiona straight from the zip (GDAL
  3.9.2 reads its backslash member names; measured), never unzipped; its size against the
  provenance's `size_bytes`, then its SHA-256 against the lock's, then the read, after which
  its (size, mtime_ns, inode) must be unchanged. Layers TLM_STRASSE, TLM_BODENBEDECKUNG,
  TLM_FLIESSGEWAESSER. A feature is read when its 2-D geometry meets the area box grown by
  10 m (GDAL's box filter, grown by 1 m, only pre-filters; the decision is exact).
  Coordinates are integer millimetres (the file's own grid; measured within 1.86e-9 m); one
  more than 1e-6 m off is refused. The codes are read from the FileGDB's own subtypes and
  domains.
- *The grid:* `cell_m` from `config/surfaces.json` (0.2, 0.5 or 1); texel centres exact in
  integer mm. Classes, highest wins: **4 road** > **3 path** > **2 water** > **1 rock** > 0:
  - road and path: TLM_STRASSE with BELAGSART 100 (Hart) → road, 200 (Natur) → path, whose
    OBJEKTART has a width (8 → 10 m, 9 → 6, 10 → 4, 11 → 3, 15 → 2, 16 → 1, 17 → 1, 18 → 2,
    20 → 8), drawn where a texel's centre lies within width/2 of a segment (exact rational
    test); not drawn: KUNSTBAUTE 300, 400 (roofed bridges), 700 (gallery), 1000 (tunnel),
    1100, 1200 (underpasses), 1400 (in or on a building);
  - water: TLM_BODENBEDECKUNG OBJEKTART 5 (Fliessgewaesser) or 10 (Stehende Gewaesser), the
    centre inside; and TLM_FLIESSGEWAESSER OBJEKTART 4 with VERLAUF 100 (above ground) or 500
    (waterfall), within 1.0 m of the line: an **assumed** width of 2 m (TLM gives none), a
    labelled placeholder; not water: Bisse/Suone (0), a stream on a bridge (VERLAUF 400);
  - rock: TLM_BODENBEDECKUNG OBJEKTART 1–4 (Fels, Fels locker, Felsbloecke, Felsbloecke
    locker), the centre inside.

  Point in polygon: per feature, even-odd over its rings by the half-open crossing rule (an
  edge counts when (y1 > yc) ≠ (y2 > yc) and xc lies left of the crossing, compared
  exactly); OR-ed across features.
- *The PNG:* written without Pillow, by the standard library: 8-bit grey, no interlace,
  filter 0 on every row, one zlib stream at level 9 in IDAT chunks of at most 1 MiB, values
  0–4. Its content is pinned (`pixels_sha256`); its bytes depend on the zlib build (zlib 1.3 and
  1.3.2 write the same bytes, zlib-ng does not: measured 2026-10-15), so they are design's
  too: `expected_png_sha256` in the surfaces config, per cell, and the step refuses another
  PNG before writing, naming the machine's zlib (§13 row 39; brief M3-R1-fix-6). Files: `surfaces/<area>.png.import` (the keep file, H24), then
  `surfaces/<area>.png`, then `surfaces/<area>.json`, each through a `.part` rename; the
  description is exactly {area, cell_m, classes: {"0": "none", "1": "rock", "2": "water",
  "3": "path", "4": "road"}, columns, file, format "png-l8", lv95_box, pixels_sha256, rows,
  sha256 (the PNG's), source: {attribution, collection, dataset, edition, file, sha256},
  world_sha256}.
- *The expected output:* `config/surfaces.json`, `{"schema": 1, "areas": {<area>: {"cell_m",
  "computed_for", "expected_pixels_sha256": {"0.2", "0.5", "1"}}}}`, the village computed
  two independent ways: 0.2 m `93d78ba6…`, 0.5 m `adda417b…`, 1 m `4ea3d1e6…`; at 0.2 m
  road 74'744 m², path 47'654 m², water 40'737 m², rock 408'266 m². `manifest` decodes the
  PNG (standard library), checks its content and refuses anything else, naming `python -m
  mattini surfaces`.
- *The game (M3-10):* `SurfaceGrid.from_manifest(path, world)`: the photo's checks (the
  rectangle within 1 mm, the owner's axes), the file's SHA-256 before decoding,
  `Image.load_png_from_buffer` to L8 (the village's 1.15 MB PNG decodes in 277 ms), the
  decoded bytes' SHA-256 against `pixels_sha256`; `class_at(x, z)` gives the class, −1
  outside the half-open rectangle. The texture is sampled with nearest filtering.
- *Shared fixture:* `tests/shared/surfaces_fixture/` and `tests/shared/surfaces_vectors.json`:
  40 synthetic features in the reader's form covering every class and priority, the not-drawn
  cases, holes, overlaps, a two-part line, features outside reaching in and deliberate ties;
  the expected PNG at all three cells, computed two ways; 53 named points.

**The trees (M3; designed at M3 planning, 2026-10-14; the owner's look (a), §13 row 29; brief
M3-07, the game M3-11).** Where the LiDAR surface model shows a tree, its position, base
height, height and crown radius. Tier 1 where it places a tree (position and base height),
Tier 2 elsewhere.

- *Inputs:* swisssurface3d (the DSM), swissalti3d (the DTM: the terrain's tiles),
  swissbuildings3d (the sheets) and swisstlm3d (TLM_GEBAEUDE_FOOTPRINT and
  TLM_BODENBEDECKUNG), each checked as its own step checks it; `computed_for.inputs_sha256`
  over the four entries (the several-datasets rule, as roof colours). DSM and DTM tiles are
  2000 × 2000 float32 at 0.5 m, the transform exactly (0.5, 0, E0, 0, −0.5, N0 + 1000), no
  nodata pixel. TLM features reach the rule as {uuid, objektart, polygons} (MultiPolygon
  coordinates as read, rings closed), through the surfaces step's reader; E and N snapped to
  1 mm, one more than 1e-6 m off is refused. Only the owner's axes: the base height is the
  terrain grid's, defined for them only.
- *The rule,* on the area's 0.5 m pixels, (i, j) from the north-west, centre E = e_min +
  0.25 + 0.5 j, N = n_max − 0.25 − 0.5 i; exact integer arithmetic throughout:
  1. chm = DSM − DTM per pixel, in 64-bit (exact for float32 inputs).
  2. Masks by pixel centres, exact in integer mm. F: inside or on the boundary of the plan
     projection of a non-degenerate triangle of any building of the area's sheets whose
     bounding box meets the area (selected or not), or inside a TLM_GEBAEUDE_FOOTPRINT polygon
     of any OBJEKTART but 16 (underground buildings have no roof above ground). B: within
     2.0 m of a pixel of F, centre to centre (di² + dj² ≤ 16), over the area's pixels only.
     R: inside a TLM_BODENBEDECKUNG polygon of OBJEKTART 1–4 (rock). Inside: even-odd by the
     half-open crossing rule, OR-ed across features (as the surfaces').
  3. v = chm where chm > 0 and the pixel is not in B, else 0. Each v must be a whole multiple
     of 2⁻¹³ m (true for float32 heights in [1024, 4096) m; measured on every village value);
     otherwise refused, naming the pixel's LV95 centre and both heights. V = v · 2¹³.
  4. S = K ⊛ V, K = outer([1, 4, 6, 4, 1], [1, 4, 6, 4, 1]) (weights sum 256), pixels outside
     the area counted 0: integers in units of 2⁻²¹ m.
  5. A top: a pixel p not on the area's outermost ring, not in B, not in R, with S(p) ≥ 3 m,
     such that within the disc of radius ρ = 3 + floor(S(p) / 10 m) pixels (di² + dj² ≤ ρ²,
     inside the area) every other q has S(q) < S(p), or S(q) = S(p) and q after p in raster
     order (rows from the north, then columns from the west).
  6. Dropped: a top whose chm is above 40 m (a cliff: the DSM takes a face's top, the DTM
     its foot) or below 3 m (a gap in a crown), or where the DTM's slope is 60° or more (gx =
     DTM(i, j+1) − DTM(i, j−1), gy = DTM(i+1, j) − DTM(i−1, j), dropped when gx² + gy² ≥ 3).
  7. A tree: E, N the top's centre; x, z = `to_local(E, N)` in 64-bit, then float32; y = the
     mean of the four vertices of the 0.5 m terrain grid around the centre (heights minus
     `height_offset_m`), in 64-bit, rounded once to float32; the trees step and the manifest's trees
     block refuse a terrain config whose spacing is not 0.5, naming `config/terrain.json`
     (§7, §13 row 37; brief M3-R1-fix-2); height = chm at the top; crown radius = clamp(min(d / 2, height / 4), 1.0,
     6.0) m, d the 2-D distance to the nearest other tree kept in the area (+∞ when none),
     in 64-bit with a correctly rounded square root, then float32.
  8. Chunks: the 1 km tile of (E, N); within a chunk, the top pixels' raster order. A tile
     without a tree has no chunk.
- *The files:* `trees/<tile>.bin`, per tree x, y, z, height_m, crown_radius_m as
  little-endian float32 (20 bytes), no header; then `trees/<area>.json`, exactly {area,
  chunks: [{file, sha256, tile, trees}] by tile, format "trees-f32x5-le", lv95_box,
  parameters: {building_margin_m 2.0, crown_radius "min(d / 2, height / 4), clamped to 1.0-6.0 m; d to the nearest other tree, infinite when none", max_height_m 40.0,
  max_slope_deg 60.0, min_height_m 3.0, smoothing "binomial-5x5", window "3 + floor(h / 10
  m) pixels"}, source: {swissalti3d, swissbuildings3d, swisssurface3d, swisstlm3d},
  world_sha256}, each through a `.part` rename; a stale chunk is removed. The sources are
  each dataset's own block's (the terrain's, the buildings', the surfaces'); swisssurface3d's
  is {attribution, collection, dataset, editions, resolution_m 0.5, tiles: [{edition,
  sha256, tile}] by tile}.
- *The expected output:* `config/trees.json`, `{"schema": 1, "areas": {<area>:
  {"computed_for", "expected_sha256": {<tile>: …}}}}`; the village computed two independent
  ways (identical bytes): 34'412 trees in six chunks, 688'240 bytes; the height / 4 cap decides 6'781 crowns (19.7 %), the median radius 2.69 m. Measured on the village:
  every DSM and DTM value on the 2⁻¹³ m grid; the building masks remove 4'539 trees, rock
  1'465, the TLM footprints 1'690 beyond swissBUILDINGS3D's; 987 tops dropped (27 above
  40 m, 952 too steep, 12 below 3 m, some for two reasons). Known residue, kept as data (Hard
  Rule 2): a few false trees where neither building dataset has a structure (vehicles and
  train cars in the 2021 surface, a canopy newer than both); the margin stops at the area's
  edge (it matters when areas tile, M5).
- *The game (M3-11):* `TreeChunks.from_manifest(path, world)` checks the block's key sets,
  format, `world_sha256` against its manifest, that the WorldConfig is the manifest's with
  the owner's axes, each file's path, its size (20 × trees) and SHA-256; it never converts a
  coordinate. Its `edition` is the first and last of the tiles' editions ("2021-2022").
  `TreeLoader.create(chunks, parent, photo, photo_rect)`: node "Trees", one
  MultiMeshInstance3D per 250 m cell "<cx>_<cz>" (floor(x / 250), floor(z / 250)), each
  instance Basis(up, yaw).scaled(r, h, r) at (x, y, z), the yaw a hash of the position, the
  MultiMesh filled through one `buffer` assignment (brain.md H25); one procedural conifer of
  at most 256 triangles, three variants picked in the shader by a hash of the instance's
  origin; the crown colour from the photo at the tree's position, at the mip level of its
  crown; without a photo, a labelled placeholder green; shadows on.
- *Shared fixture:* `tests/shared/trees_fixture/` and `tests/shared/trees_vectors.json`: a
  synthetic world, 96 × 96-pixel DSM and DTM, buildings and TLM features; 35 named cases
  giving 19 trees in three chunks, a tile with crowns but no tree (so no chunk), and an
  area across both tile and 250 m cell boundaries; computed two ways; 53 of 54 likely
  wrong implementations change its bytes (the one left cannot differ by construction).

**The surroundings, the capture shadows and the sky (M4; designed at M4 planning, 2026-10-17;
§13 rows 41–43; briefs M4-01 to M4-03, M4-09).** Three steps, each with design's expected values
and `computed_for` like every step above; their rules in full are `docs/briefs/sketches/m4-design.md`
§1 to §4 and the briefs' Decisions:
- `surroundings`: swissALTIRegio's 10 km XYZ tiles (30 for the village, edition 2026-06, locked by
  `lock regio`, fetched by `download regio`) to a 100 m grid of local heights over the area grown by
  20 km, each vertex the highest sample of its square, the area box cut out as NaN;
  `surroundings/<area>.f32` and `.json` (`config/surroundings.json`).
- `shadows`: where the photo was in shadow when flown (the flight's sun, grid azimuth 184.67°,
  elevation 50.1°), marched over swissSURFACE3D on a 1 m grid, written at 0.5 m with a 0.5 m inset;
  `shadows/<area>.png` (8-bit, the surfaces' zlib rule) and `.json` (`config/shadows.json`).
- `sky`: the area's latitude, longitude and true-to-grid angle (−0.2258° for the village: a grid
  azimuth is the true azimuth minus 0.2258) from `config/sky.json`, for the game's sun;
  `sky/<area>.json`.
The manifest gains the `surroundings`, `shadows` and `sky` blocks (twelve keys at the top).

**Determinism (Hard Rule 5):** pinned editions and checksummed inputs; outputs carry no
wall-clock times and no absolute paths; stable ordering; running a step twice on the same
inputs gives identical bytes, and tests say so.

## 9. Storage

- **Raw downloads:** `data/` (git-ignored). Checked against swisstopo's published
  checksums; a provenance file per dataset edition records what was fetched.
- **Generated assets:** `game/assets/generated/` (git-ignored), regenerated on each machine
  by running the pipeline (owner, day one: option b). The owner's PCs and every cloud
  container run the pipeline themselves; determinism makes the results identical.
- **Vendored plugins (committed):** `game/addons/terrain_3d/` (from the Asset Store zip
  above) and `game/addons/gut/` (about 3 MB). Each vendoring commit names the source and
  checksum. Terrain3D's runtime part only, bytes unchanged from the zip (decided at M1
  planning, 2026-09-25): `LICENSE.txt`, `README.md`, `terrain.gdextension` and its `.uid`,
  `icons/`, and the Linux and Windows x86_64 binaries, debug and release (about 15 MB).
  Not its other platforms' binaries, and not its editor plugin (`plugin.cfg`, `src/`,
  `menu/`, `tools/`, `utils/`, `brushes/`, `extras/`): enabled, the plugin makes every
  headless import print leak ERROR lines at exit (measured), and mattini's terrain comes
  from data, not from sculpting.
- **Generated terrain:** `game/assets/generated/terrain/` (git-ignored, like all generated
  assets), written by `python -m mattini terrain` (§8).
- **Generated buildings:** `game/assets/generated/buildings/` (git-ignored), written by
  `python -m mattini buildings` (§8): about 3.1 MiB for the village, which the export's
  `.pck` holds beside the heights.
- **Detail textures (committed, from M3-10):** `game/textures/`, seven CC0 JPGs from Poly
  Haven (15.05 MiB, each under 10 MB), unchanged, pinned by SHA-256, with `LICENSE.txt`
  naming every file, its author and asset page; their `.import` files are committed too
  (mipmaps).
- **Screenshots:** software-rendered evidence from builders of visual briefs (§12) in
  `docs/briefs/shots/<brief>-<view>.jpg`, JPEG, 1280 × 720, a few per brief.
- **Test data:** synthetic data generated inside the tests, and the small shared files in
  `tests/shared/`. One file of real swisstopo data, by the owner's word (§13 row 24):
  `tests/shared/buildings_sample/`, sheet 1328-33 of swissBUILDINGS3D 3.0, edition 2020,
  45'668 bytes, © swisstopo, with a README naming its source and terms (brief M2-09).
- Nothing over 10 MB is committed without a design decision naming it; GitHub rejects any
  file over 100 MB.

## 10. Game (outline; each milestone's briefs refine it)

Free-fly camera (M1); walking with collision against terrain and buildings (M6);
Terrain3D terrain with triplanar or separate rock for near-vertical faces (the Matterhorn
faces cannot be a heightmap overhang); buildings from swissBUILDINGS3D (plain shapes, the
model look of M1–M2 read that as intentional; from M3 the look is realistic, made from the
data); real sun position for
Zermatt with time control (M4); weather (M6); a credits screen from the manifest (before
the first shared build); the version on the pause screen.

**M1's game (planned 2026-09-25; the owner does not design screens or visuals, so the
design realm proposes and the owner reacts through `feedback`):**

- *Look:* the terrain as a light, warm-grey clay surface, rough (no shine), with thin
  contour lines every 10 m of real height and stronger ones every 100 m, like a relief
  model; it invents no surface types (the real ones come from swisstopo data in M3).
  Nothing is drawn where there is no data: no ground plane, and a neutral sky below the
  horizon. One fixed sun (elevation 35°, from azimuth 150°, with shadows) and a procedural
  sky; the real sun is M4's. Reference: `docs/briefs/shots/M1-look-proposal-*.jpg`, design's
  software-rendered prototype on the real village heights.
- *Camera:* like the Godot editor's fly mode (owner kept the proposal): hold the right
  mouse button to look; W/S fly along the view, A/D sideways, E/Q straight up and down;
  Shift five times faster; the mouse wheel changes the speed by 1.25 per notch between 2 and
  1000 m/s, starting at 30 m/s; pitch stops at 89°; the camera stays 1.5 m above the ground
  where there is ground (no physics in M1). It starts 150 m above the centre of the
  terrain, facing bearing 235° (towards the Matterhorn), 20° down. Every control is an
  InputMap action; Escape is `pause`.
- *Pause screen (Escape):* the version (the only place it shows, owner's choice
  2026-09-25), the controls, the credits (every dataset's attribution from the manifest,
  the licences of Godot and its components and of Terrain3D), Resume and Quit.
- *Errors on screen:* a missing, refused or stale manifest or terrain opens a message
  naming the command that fixes it (Hard Rule 2).

**M2's game (planned 2026-09-25; design proposes, the owner reacts through `feedback`):**

- *Look:* the buildings as a white architectural model. Walls matte off-white
  (0.93, 0.92, 0.89), roofs a shade darker and warmer (0.76, 0.72, 0.68); roughness 1,
  no metal, flat-shaded facets, casting shadows in the fixed sun, back faces culled. No
  textures and no per-building colours: M2 has no data for them, and nothing is invented.
  The two materials are `.tres` files the owner can tune in the editor.
- *Loading:* after the terrain; a refusal opens the error panel with the refusal and the
  commands (`download buildings`, then `buildings`) while the terrain stays; the panel
  names what cannot be shown. A second startup line counts the buildings. With the
  terrain refused and the buildings loaded, the camera starts over the centre of the
  buildings' bounds, 150 m above the highest vertex, at the same bearing and pitch (M2 R1
  G-02; brief M2-08).
- *Tests of the look (M2 R1 G-01):* on the meshes the loader built, every surface is
  lit per pixel, back faces culled, opaque and untextured, and the roofs' luminance lies
  below the walls' and above 0.3. The colours themselves stay the owner's to tune.
- *Credits:* one line per loaded dataset (`swissalti3d 2024, © swisstopo`,
  `swissbuildings3d 2020, © swisstopo`), then the software licences, godot-cpp's included
  (D17).
- *Not in M2:* collision and walking (M6), names or picking of buildings.

**M3's game (planned 2026-10-14; the owner's look (a), §13 rows 29–34; briefs M3-09 to
M3-12, M3-14):**

- *Look:* realistic, from data.
  - The terrain shows the 2023 aerial photo at 0.2 m (`PhotoGrid`, the override shader
    `terrain_photo.gdshader`: uv from the world position, roughness 0.95, a neutral colour
    outside the photo).
  - On it, swissTLM3D's classes (`SurfaceGrid`): roads with a CC0 asphalt grain and paths
    with gravel, both fading out by 150 m; water darker (albedo × 0.6), smooth (roughness
    0.05), with two drifting noise normal maps; steep rock (blended in between 35° and 55°)
    with a triplanar CC0 rock texture tinted to the photo's colour.
  - Roofs in the colour the photo gives each building (an sRGB vertex colour). Walls one
    neutral plaster (0.78, 0.76, 0.72), roughness 0.9: a labelled placeholder (§13 row 31).
  - Trees: one procedural conifer per tree the LiDAR found, scaled to its height and crown
    radius, its crown coloured from the photo at its position. A generic conifer, labelled:
    the data gives no species.
  - Colours enter only through `source_color` samplers and uniforms, or vertex colours
    marked sRGB, never as raw instance data (brain.md H21).
- *Light:* the sun at azimuth 183°, elevation 52°, measured from the photo's shadows, so the
  photo's baked shadows agree with the game's. The flight time (7 September 2023, about
  11:30 UTC) gives 181° and 50° by the solar position formulas, within the shadows'
  measuring error; the shadows' values are kept. Tonemap exposure 0.54 and sky ambient
  contribution 0.25 (Filmic, as M2's): calibrated under the Compatibility renderer so that
  flat sunlit ground renders at the photo's brightness (measured 1.06×). Forward+ on the
  owner's GPU is the real check.
- *Loading:* after the terrain and the buildings come the photo, the surfaces, the trees and
  the roof colours, each read by its own reader and checked against its manifest and
  world. A refused or missing block opens the error panel with the refusal and the commands
  that fix it, and the rest still shows: the terrain falls back to M2's clay without its
  photo, the trees take a placeholder green, the roofs M2's roof colour. In an exported
  build the panel says instead to keep `mattini.pck` and the `mattini-*.pck` packs beside
  the executable and to download the release folder again. One startup line per block,
  after the packs' lines.
- *Credits:* the dataset lines from the blocks (`swissalti3d 2024`, `swissbuildings3d
  2020`, `swissimage 2023`, `swisssurface3d 2021-2022`, `swisstlm3d 2026-02`, each
  `© swisstopo`), the CC0 textures by name and author (`game/textures/LICENSE.txt`), the
  placeholder notes (the walls, the trees, the streams' assumed width), then the software
  licences.
- *Cost, measured in software:* the village scene builds in about 6 s (2.9 s in M2) and
  peaks at about 2.4 GiB, with 1'171 MiB of texture memory; the trees are about 34'000
  instances of 192 triangles in 250 m cells, each cell drawn to 3 km. GPU time is the
  owner's PC's to measure.
- *Not in M3:* close-range detail for meadows, scree and forest floor (option b), façades,
  species, railways, cable cars, names; the moving sun (M4); walking (M6).

**M4's game (planned 2026-10-17; §13 rows 41–46; briefs M4-04 to M4-08, M4-10; the details are
`docs/briefs/sketches/m4-design.md` §5 to §9):**

- *Time:* the game starts at the photo's moment, 6 September 2023, 13:40 CEST, running at 1×.
  Comma and period move it 15 minutes, [ and ] a day, T cycles 1×, 60×, 600× and stopped, N sets
  the computer's clock; a label shows the date and time after a key and while paused. Swiss time
  (CET, CEST by the EU rule). Pausing stops the time.
- *Sun, moon, stars:* the sun by NOAA's solar position, the moon by Paul Schlyter's method with its
  phase, the local sidereal time, all for the manifest's `sky` site; directions turned from true to
  grid north and through the world config's axes (Hard Rule 4). The stars (the owner's catalogue
  answer) turn with the sky.
- *Light:* Godot's physical sky as a sky shader with a twilight, a night-sky glow and the sun's
  disk; the sun light fades below 10° and hides below −1°, sharp shadows; a moon light by phase;
  exposure 0.70 by day (measured in software Forward+), 4.0 at night, between them by the sun's
  height. No auto exposure.
- *The far mountains:* a shadows-only mesh from the `surroundings` block casts the mountains'
  shadows (Forward+; Compatibility draws none); nothing of it is visible until M5.
- *The photo's baked shadows* lifted 3× inside the capture mask (§13 row 41); *the water* in the
  photo's colour × 0.9, roughness 0.3, turbulent ripples, a soft bank.
- *The machine:* a frame cap of 60 (15 while paused), the log flushed per line, MSAA 4×; in an
  export a missing data pack is named, and the readers say to download the release folder again.
- *Not in M4:* the far mountains drawn (M5), weather and snow (M6), lit windows, bridges.

## 11. Delivery (owner, day one: option b)

Exported Windows and Linux builds on a `dist` shelf branch (orphan, never merged, never
deleted): `windows/` and `linux/` hold the current version under fixed names,
`mattini-<version>/` each version under its own name (the last three kept; the one before
the current is the rollback), and a `README.md` says how to download, start and roll back
(`docs/RELEASE.md` §C; ruled at the M1 close, D15: files cannot be renamed per version,
since an executable finds its `.pck` by its own name and Terrain3D's library has a fixed
one).
Consequences: Godot 4.6.3 export templates are downloaded from the mirror at release time;
the pipeline regenerates the assets from pinned inputs before export; binaries accumulate
in the `dist` history, which a plain `git clone` or `git fetch` of every branch downloads
too (about 140 MB per release; `--single-branch --branch main` avoids it). GitHub rejects
files over 100 MiB: the first release measured the export size, and a larger export is a
design question (split the pack file, or LFS on `dist`) — **OPEN** until M5 (the owner,
2026-09-25). Measured at 0.1.0: nothing over; the largest file is `mattini.exe`, Godot's
own Windows template, 198 KB under the limit, and each `.pck` had 8.3 MiB of room (D16).
At 0.2.0, with the buildings: each `.pck` is 99'405'400 bytes, 5.2 MiB of room.

**Data packs (the owner, 2026-10-14, §13 row 32; brief M3-08).** `tools/export.sh` writes
the generated folders `terrain/` and `photo/` (whole folders, but names starting with `.` or
ending `.part` or `.import`) each into `mattini-<folder>.pck` with Godot's PCKPacker
(`game/tools/pack.gd`; the files in code-point order, so the same files give the same bytes:
measured) beside each executable; the presets keep those folders and every `*.part` out of
`mattini.pck`; the autoload `DataPacks` (`res://scripts/data_packs.gd`) loads every
`mattini-*.pck` beside the executable of an exported build, in name order and never
replacing a file already loaded, before the main scene, and prints one line per pack; step
4c checks that every generated file ships once, unchanged, and that no generated file of
10 MiB or more stays in `mattini.pck`. Measured on the village with a 0.2 m photo:
`mattini.pck` 3.4 MB before M3-10's textures (21'267'996 bytes with them and M3's other
generated files, in design's M3-14 rehearsal), `mattini-terrain.pck`
96'041'728 bytes (8.4 MiB under the limit), `mattini-photo.pck` about 50.2 MB (50'224'444
bytes in design's last rehearsal, with the final photo description); the Linux build starts
as fast and as large as without packs. Linux's and Windows' packs are the same bytes, and stay the same across
releases while the data does not change, so `dist`'s history stores them once.

**Version scheme (confirmed by the owner, 2026-09-25):** `0.<n>.<patch>` for releases
before v1; `1.0.0` when the v1 scope (§2) is complete. The version lives in
`game/project.godot` (`application/config/version`). **Where it shows:** only on the pause
screen (owner, 2026-09-25: option b), so a screenshot sent to `feedback` shows the version
only when the pause screen is open.

**The first version, 0.1.0,** shipped at M1's close (2026-09-25; `docs/releases/v0.1.0.md`),
the first milestone with something to look at; M0 closed without one, because it had
nothing to play (ruled at the M0 close). **0.2.0** shipped at M2's close (2026-09-26;
`docs/releases/v0.2.0.md`): the village's buildings.
Exports go to `build/` (git-ignored) through `tools/export.sh` (brief M1-06): Linux and
Windows x86_64 with the `.pck` beside the executable. At 0.5 m the village heights alone
are 96 MB, so the `.pck` sits just under GitHub's 100 MB file limit; the script measures
every file and the close decides if one is over.

## 12. What cloud sessions can and cannot verify

Builders and reviewers run in containers without a GPU. They prove the pipeline, data
transforms, coordinate maths, scene loading and game logic headless. They cannot prove
that anything renders or looks right: every brief that changes what is drawn carries
*"does NOT prove: that it renders or looks right"*, and the owner's PC is the visual test
(bugs return through `feedback`).

**Software screenshots (owner, 2026-09-25: yes, as evidence, never as a gate).** Measured
2026-09-25 in a cloud container: Godot's Compatibility renderer on Mesa's llvmpipe under
Xvfb (both preinstalled in the container image) renders Terrain3D and saves a 1280 × 720
screenshot in a few seconds; the Forward+ renderer on Mesa's lavapipe crashes as soon as
Terrain3D draws. So builders of visual briefs render a few views with the Compatibility
renderer (`tools/shot.sh`, brief M1-04) and commit them with their Findings under
`docs/briefs/shots/`. They show that something is drawn, and where; not how it looks in
Forward+ on the owner's RTX 4090. The "does NOT prove: that it renders or looks right"
line stays on every visual gate.

**The render step (owner, 2026-10-15: §13 row 38).** Where an image lies on the ground is a
number, not a look. From brief M3-R1-fix-3 on, `tools/gate.sh` renders the complete test
world under the Compatibility renderer (Mesa llvmpipe under Xvfb) and asserts, by
correlation against flipped and shifted alternatives, where the photo shader puts the photo
and the surface classes and where the tree shader reads the crowns' colour. It refuses where
`xvfb-run` is missing unless `MATTINI_SKIP_RENDER=1`, which it prints. It gates placement
only: not the look, not the colour encoding (brain.md H21), not Forward+, not the owner's
GPU.

## 13. Decision record (day one, 2026-09-24)

| # | Question | Answer | Source |
|---|---|---|---|
| 0 | Work on `main`? | Yes, push to `main` | Owner |
| 1 | Never-happen rule | None; the licence attribution (b) as a soft rule | Owner |
| 2 | GDScript or C# | GDScript | Owner |
| 3 | Godot version, terrain | 4.6.3, Terrain3D plugin | Owner |
| 4 | Godot test framework | GUT 9.6.1: GDScript-only project, simplest, clean headless runner with a failing exit code (measured) | Design, delegated by the owner |
| 5 | Python tooling | uv, Python 3.13, lockfile: identical environments on the container and both PCs (Hard Rule 5); uv installs Python itself (measured) | Design, delegated by the owner |
| 6 | Local origin | E 2'623'000 / N 1'096'000 (tile corner) | Owner |
| 7 | Generated assets | Git-ignored, regenerated on each machine | Owner |
| 8 | Delivery | Exported builds on a `dist` shelf | Owner |
| 9 | Owner-implemented briefs | None | Owner |
| 10 | v1 scope | Walking, day/night cycle and weather are in v1 | Owner |
| 11 | Test area | The entire village (measured box in §7) | Owner; box measured by design |
| 12 | PROPOSED items (Python pipeline, architecture, coordinates, milestone order) | Confirmed | Owner |
| 13 | Working-style defaults (testing, pace, no day rule, models and effort) | Accepted | Owner |
| 14 | In-game terrain resolution for the village (M1 planning, 2026-09-25) | 0.5 m, "for the demo at least"; 1 or 2 m later is a config change | Owner |
| 15 | Where the game shows its version | Only on the pause screen (option b) | Owner |
| 16 | Version scheme | `0.<n>.<patch>` until v1, `1.0.0` at v1; 0.1.0 at M1's close (confirmed) | Owner |
| 17 | Does the owner design screens or visuals? | No; the design realm proposes, the owner reacts through `feedback` | Owner |
| 18 | Software rendering in containers for smoke screenshots | Yes, as evidence in Findings, never as a gate; amended by row 38 (a render gates placement) | Owner |
| 19 | Camera controls (the design's proposal) | Kept as proposed (Godot editor fly mode) | Owner (no change asked) |
| 20 | Form of the tile pin (D7) | `config/datasets.lock.json`, written by `python -m mattini lock terrain` | Design (M0 close: "M1 planning picks the form") |
| 21 | Raster libraries | rasterio and numpy confirmed | Design, delegated (CLAUDE.md §Stack) |
| 22 | swissBUILDINGS3D access route (M2 planning, 2026-09-25) | (a) swissBUILDINGS3D 3.0, edition 2020, per map sheet (the village's six sheets, 14.2 MB: closed solids with attributes), as design proposed. Not taken: (b) 2.0, 2024-05, per sheet (DXF; 1'272 of the village's 2'376 parts are open meshes, measured); (c) the 3.0 national file, 2026 (14.1 GB for about 1'500 buildings) | Owner ("a", 2026-09-25) |
| 23 | An export over 100 MiB (D16) | Stays open until M5 (§14), as design proposed: the village's buildings add 3.1 MiB to a `.pck` with 8.3 MiB of room, and `tools/export.sh` refuses any file over 100 MiB | Owner ("later", 2026-09-25) |
| 24 | A committed sample of real swisstopo data | Yes: sheet 1328-33 of the 2020 edition (45'668 bytes, three buildings, © swisstopo) in `tests/shared/buildings_sample/` as the buildings reader's fixture, the one file of raw geodata in git, named with its SHA-256 by `test_repo_hygiene.py` (brief M2-09). Hard Rule 3's "never enter git history" is overridden for that one file | Owner ("yes", 2026-09-25) |
| 25 | Vector library | fiona confirmed (pyogrio cannot read the layer) | Design, delegated (CLAUDE.md §Stack) |
| 26 | The buildings' file format | A raw mesh per 1 km chunk (`.bin`, float32 vertices then uint32 triangles), not glTF: Godot imports a `.glb` under `res://` and an export ships the imported copy, not the file (measured), while a `.bin` ships as it is, like the terrain's `.f32`, and the game checks its SHA-256 | Design (the architecture's "glTF" was a sketch; the owner may reverse) |
| 27 | How M2 is run | In one session: design, build, review and close with in-session agents; no spawned waker, ticks or builders. The session pushes to `main` as usual | Owner (RULINGS 2026-09-25; "push to main") |
| 28 | The process (2026-10-14) | No model named in the repo: the one the owner picks for the chat applies, spawns inherit it (replaces row 13's models). No supervisor. Design is everything before the build and plans each arc for parallel sessions; the `ultracode build` orchestrator spawns builders per wave, integrates, runs the design's review plan and ships. No limit of two builders | Owner (RULINGS 2026-10-14) |
| 29 | The look (FB-001; M3 planning, 2026-10-14) | (a) the realistic look made from the data: the aerial photo (SWISSIMAGE) on the terrain, a colour per roof from it, 3D trees where the LiDAR found them, a rock texture on steep rock, procedural conifers, the fixed sun moved to the photo's sun, the lighting matched to the photo's brightness; it replaces the stylised diorama (§1, §10). Read back to the owner as (a) with the slope rock and the conifers; not corrected. Not taken: (b) textured materials for walls and close-range ground everywhere; (c) photorealism beyond what the data gives | Owner ("a", 2026-10-14) |
| 30 | The photo's resolution | 0.2 m (the 2023 photo's real detail over Zermatt is 25 cm), a separate texture over the area (§8, the photo), not Terrain3D's 0.5 m colour map; about 0.6–0.8 GB of GPU memory. Not taken: 0.5 m | Owner ("0.2") |
| 31 | Walls | One neutral plaster for every wall, a labelled placeholder (no open wall data exists). Not taken: a rule-based chalet look (stone base, larch wood above), which would be invented | Owner ("neutral") |
| 32 | An export over 100 MiB (row 23, D16) | Data packs beside the executable, each file under 100 MiB (§11). Not taken: Git LFS on `dist` (its free quota counts every download, over it downloads give pointer files, its objects cannot be deleted short of the repository, and cloud pushes through the proxy are unmeasured), GitHub Releases, terrain and photo at 1 m. M5's larger area revisits delivery | Owner ("do packs", after design's list of LFS's costs) |
| 33 | swissTLM3D's access route and use (§14) | The national FileGDB, edition 2026-02 (2.88 GB), pinned by SHA-256 in the lock, downloaded once per machine and read straight from its zip (§5); used in M3 for water, roads, paths and rock on the terrain (§8, the surfaces) and to clean the trees (rock, building footprints). Not taken: the REST API (no edition, 2-D, 0.1 m), the GeoPackage (one deflated 10.8 GB member, unreadable in part) | Owner ("bring into m3 now"); the route measured by design |
| 34 | The game type (FB-002, a collaborative builder) | Stays OPEN: "keep open, lets just build the map first. i want it as detailed and beautiful as possible". The idea is on the board | Owner |
| 35 | An image library for the pipeline | Pillow, for the photo's JPEG (the surfaces' PNG is written with Python's own zlib, so the lane that builds it needs no new dependency); its JPEG output measured byte-identical across Pillow 10.4.0, 11.0.0 and 12.3.0 and with libjpeg-turbo's SIMD off | Design, delegated (CLAUDE.md §Stack) |
| 36 | M2's residue | M3's first two briefs (M3-01 pipeline, M3-02 game and tools), as D25 decided; V1-G-04 (the buildings' look test) moves to M3-12, which rewrites that test | Design |
| 37 | The trees on a 1 m or 2 m terrain (M3 R1 P-01; 2026-10-15) | (b) the trees step and the manifest's trees block refuse a terrain spacing other than 0.5, naming `config/terrain.json`; row 14's "1 or 2 m later is a config change" holds for the terrain, and softening needs the trees step first (§7; brief M3-R1-fix-2). Not taken: (a) the trees' heights interpolated at the terrain's spacing, with expected chunks per spacing | Owner ("I follow your recommendations", design recommended b) |
| 38 | A software render in the gate (M3 R1 P-03) | (a) the gate's render step asserts the placement of the photo, the surface classes and the crowns' colour (§12; brief M3-R1-fix-3); amends row 18 and BUILD.md rule 2b for placement only. Not taken: (b) the shaders' placement expressions pinned by text alone | Owner (same answer, design recommended a) |
| 39 | The surfaces PNG's bytes and zlib (M3 R1 I-01) | `expected_png_sha256` per cell in the surfaces config; the step refuses another PNG before writing, naming the zlib; the manifest compares it; RELEASE.md §C compares the manifest (brief M3-R1-fix-6). Not taken: dropping the PNG's SHA-256 from the description (a schema and game change), a deflate of mattini's own | Design (put to the owner 2026-10-15, no objection) |
| 40 | The build's decisions of M3 for design to audit (the board's list, 2026-10-15) | All ten kept; SPEC §5 reworded for the TLM's GETs per round (§5) | Design (put to the owner, no objection; RULINGS 2026-10-15) |
| 41 | The photo's baked shadows under a moving sun (M4 planning, 2026-10-17) | (b) soften them: a capture-time shadow mask (the sun of the flight, az 184.9°, el 50.1°, ray-cast on swissSURFACE3D) and a capped lift of the photo inside it, so the moving sun's shadows read and the photo's do not darken a second time; an experiment the owner judges from design's comparison images before the GO, falling back to (a) if rejected. Not taken: (a) the photo unchanged; (c) full removal (measured: shadows are about 20× darker than lit ground and JPEG 4:2:0 noise turns lifted grass into speckle, `docs/briefs/sketches/M4-deshadow/`) | Owner ("i follow your recommendation", 2026-10-17) |
| 42 | The mountains outside the area and the sun (M4) | (b) the sun hides behind the real mountains: heights from swissALTIRegio 10 m (it covers the Italian side) over a 40 × 40 km window shade the village; the mechanism is chosen at planning from measurements. The far mountains are not drawn until M5. Not taken: (a) only the 2 × 3 km terrain casts shadows (measured: the sun appears or leaves 10 to 62 minutes wrong) | Owner (same answer) |
| 43 | When the game starts (M4) | The photo's moment, 6 September 2023 at 13:40 CEST (11:40 UTC), where the photo's shadows agree; one key sets the computer's real date and time in Zermatt; date and time change by keys. Not taken: the real time at start; a clock kept between runs | Owner (same answer) |
| 44 | Night (M4) | Stars and the moon at their real positions, the moon lighting the scene by its phase. No lit windows: no data says which windows are lit, so they would be invented | Owner (same answer) |
| 45 | The 0.3.0 test's fixes (FB-003, FB-005 to FB-007) | All in M4: a frame cap (60, 15 while the pause screen is open), the log flushed line by line, the log naming the missing pack, anti-aliasing on, and the water reworked (the photo's own colour, less mirror, a visible flow, a soft bank edge) | Owner (same answer) |
| 46 | The church's pale green nave roof (FB-004 item 6) | Correct: the roof is green in reality (the owner). The roofs step stays as built; no tree mask on roofs | Owner ("the churches roof is actually green", 2026-10-17) |
| 47 | The softened photo shadows (row 41's experiment) | Kept: G = 3 with the inset feather, as design's comparisons showed (`docs/briefs/sketches/M4-soften/`); `shadow_lift` 3.0 in M4-06 | Owner ("1 ok g=3 seems fine", 2026-10-24) |
| 48 | The star catalogue (m4-design §10) | (a) the Yale Bright Star Catalogue (BSC5, CDS V/50), with its citation (Hoffleit & Warren 1991): M4-05's section S and M4-10's credit line are built. Its licence is stated nowhere authoritative: the question is on the board, to settle before any commercial release. Not taken: (b) no stars until a clean source is confirmed | Owner ("2a", 2026-10-24) |

Readings the design realm took from those answers (the owner may reverse any):
"soft rule" = the licence rule is an ordinary rule (the owner's word can override it), not
an absolute; it is enforced by a test and the release checklist and reviewed at Tier 2
(WORKFLOW §Review policy). With no never-happen rule, Tier 1 review covers
`config/world.json` and the coordinate transforms, and full discipline (mutation proofs)
covers those plus the pipeline's determinism (Hard Rules 4 and 5).

## 14. Open decisions

Asked when the milestone that needs them is planned; each is also on the board.

- macOS builds.
- Licence of mattini's own code (the repository is private; without a licence file it is
  all rights reserved by default).
- Weather: simulated, or real data (MeteoSwiss open data, Open-Meteo) — M6.
- Backdrop and larger-area extents and resolutions — M5. With them: the 2020 per-sheet
  buildings have gaps near Zermatt (1348-22, -32, -34, -43 have no item), and `lock
  buildings` refuses a sheet without one as a failed read; M5 decides whether such a
  sheet means "no buildings" (M2 R1 I-07).
- Delivery when the data outgrows packs on `dist` — M5 (§13 rows 23, 32).
- Game type — later (§13 row 34).

Answered at M1 planning (2026-09-25; §13 rows 14–19): the terrain resolution, where the
version shows, the version scheme, whether the owner designs visuals, software rendering
in containers. Answered in M2 (2026-09-25; §13 rows 22–24, 27): the access route for
swissBUILDINGS3D, the committed real sample, where the session pushes. Answered at M3 planning
(2026-10-14; §13 rows 29–34): the look, the photo's resolution, the walls, an export over
100 MiB (data packs), swissTLM3D's access route and its use in M3.
