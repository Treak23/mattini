# SPEC.md — mattini, design of record (v0, 2026-09-24; amended at the M0 close and at M1 planning, 2026-09-25)

Written by the design realm with the owner from `docs/start.md` Part 1 / 1A and the
owner's day-one answers. Only the design realm edits this file. `CLAUDE.md` holds the
rules; this file holds what is built and why. Markers: **OPEN** = not decided (asked,
never picked silently); **PROPOSED** = suggested, not yet confirmed by the owner.

## 1. What and why

A desktop game set in Zermatt (Mattertal, Valais), built on swisstopo's open geodata, in a
stylised "diorama / architectural model" look, not photorealistic. It is the owner's
learning project (game development, and what real open Swiss geodata makes possible),
shared later with a few people who have powerful PCs. A commercial release is undecided
and not ruled out, so everything stays licence-clean.

## 2. v1 scope

**In v1** (owner, start.md Part 1 and day one):

- A sandbox of the real terrain and the real village buildings from swisstopo data, in the
  stylised look, with a free-fly camera.
- Walking.
- The day/night cycle (real solar position for Zermatt, time control, sky, shadows).
- Weather effects. The weather source is **OPEN** (§12).

**Not in v1:** browser and mobile builds; photorealism; any game mode; Google Maps / Google
3D Tiles data (its licence forbids shipping or deriving from it); hand-modelled façades
for every building.

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
Different wording is required only for swissALTIRegio and swissEO, which mattini does not
use. The credits carry `© swisstopo` (CLAUDE.md Hard Rule 3).

Access: the STAC API at `https://data.geo.admin.ch/api/stac/v1/` (STAC 1.0.0, no key).
Items are addressed by id; assets carry `file:checksum` as a multihash (`1220` + SHA-256).

| Dataset | STAC collection | What we measured (2026-09-24) | Used for |
|---|---|---|---|
| swissALTI3D | `ch.swisstopo.swissalti3d` | 1 km tiles, editions 2019 and 2024 for all six village tiles; COG GeoTIFF at 0.5 m (18.1 MB per tile) and 2 m (1.2 MB); EPSG:2056 + EPSG:5728 (LN02 heights) | Terrain (M1) |
| swissSURFACE3D | `ch.swisstopo.swisssurface3d` / `…-raster` | LAZ point cloud 213 MB per tile (2021); 0.5 m surface-model COG per tile | Canopy height, steep rock (M3) |
| swissBUILDINGS3D 3.0 | `ch.swisstopo.swissbuildings3d_3_0` | Current edition (2026) only as ONE national FileGDB of 14.1 GB; per-map-sheet items exist for 2015 and 2020 (sheet 1348-11: 9.1 MB GDB) | Buildings (M2) — access route **OPEN** |
| SWISSIMAGE 10 cm | `ch.swisstopo.swissimage-dop10` | 1 km tiles, 2023 edition: 43.2 MB (0.1 m), 0.2 MB (2 m) | Surface classification (M3) |
| swissTLM3D | `ch.swisstopo.swisstlm3d` | National only (2026-02): 2.9 GB GDB / 4.8 GB GPKG | Paths, roads, rivers, rail, lifts, land cover (M3) — access route **OPEN** |
| swissNAMES3D | `ch.swisstopo.swissnames3d` | National (2026): CSV/GDB/GPKG/SHP | Place names |

Pinned editions live in `config/datasets.json`; the pipeline never asks for "the latest"
(Hard Rule 5: same inputs, same outputs). A new edition is a deliberate config change.
swisstopo can also republish a tile inside an edition (its STAC item carries an `updated`
time); the M0 download would then fetch the new file and `provenance.json` would change,
visibly but without anyone deciding it. Decided at the M0 close, built in M1: the
repository pins the SHA-256 of every tile the pipeline uses, and the download refuses a
published checksum that differs from the pinned one, so a republished tile is a deliberate
change like a new edition.

**The tile lock** (form chosen at M1 planning, 2026-09-25; brief M1-01):
`config/datasets.lock.json`, written only by `python -m mattini lock terrain` from the
checksums swisstopo publishes (STAC items only, no file is downloaded) and committed, like
`uv.lock`: `{"schema": 1, "datasets": {"swissalti3d": {"collection", "edition",
"resolution_m", "tiles": {"<tile>": {"file", "sha256"}}}}}`, sorted keys, 2-space indent, LF.
`download terrain` compares every published checksum with the lock before it fetches or
deletes anything, and refuses a difference, naming the tile, both values and the command.
A lock written by a command (rather than checksums typed into `datasets.json`) scales to
M5's many tiles. The six 2024 village tiles' checksums were re-read from the live STAC
items on 2026-09-25 and equal those brief M0-04 recorded.

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
later if needed"). It is one value in `config/terrain.json`; 1 or 2 m is a config change
and a pipeline re-run, no code change. Measured at 0.5 m: 4001 × 6001 vertices, a 96 MB
heights file, 2.9 s to load into Terrain3D and about 540 MB of memory in a headless run.

## 8. Architecture (confirmed by the owner on day one)

```
swisstopo STAC API
  → pipeline/  (Python package `mattini`, offline, re-runnable)
       download → crop → re-origin → terrain for Terrain3D (+ LODs where needed)
       → buildings per chunk (glTF) → splat maps (SWISSIMAGE + land cover)
       → tree points (surface model − terrain) → vectors (paths, rivers, rail, lifts)
       → manifest
  → game/assets/generated/   chunks + manifest.json
  → game/  Godot: chunk loading, Terrain3D terrain, buildings, stylised materials,
           sun/moon cycle, sky, weather, free-fly camera, walking
```

The game reads only `game/assets/generated/` and its manifest. Start with the village area
end to end before scaling up.

**The manifest** (`game/assets/generated/manifest.json`) is written by the pipeline and is
the game's only source of generated data. It carries at least: `schema` (1), `world` (a
verbatim copy of `config/world.json`) and `world_sha256`; later the datasets used (each
with its edition, inputs' checksums and attribution) and the chunk lists. The credits
screen is generated from it. From M1 its top level is exactly `schema`, `terrain`,
`world` and `world_sha256`.

**The terrain grid (M1; designed at M1 planning, 2026-09-25).** Tier 1 territory: it
places heights in the world (WORKFLOW §Review policy).

- *Config:* `config/terrain.json`, `{"schema": 1, "areas": {"village": {"spacing_m":
  0.5}}}`: one area in M1; spacing 0.5, 1 or 2 m (the source is 0.5 m).
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
  2026-09-24). The sums of up to 16 32-bit heights are exact in 64-bit, so every correct
  implementation gives the same bits on every machine: the village at 0.5 m is
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
  otherwise lift or sink the world, Hard Rule 4).
- *The game:* `TerrainGrid` reads the block and the file, checks the file's size and
  SHA-256 and the block against its own manifest, and places the grid through
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
  on their own vertices. That is the seam between the halves (lesson 3).

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
- **Screenshots:** software-rendered evidence from builders of visual briefs (§12) in
  `docs/briefs/shots/<brief>-<view>.jpg`, JPEG, 1280 × 720, a few per brief.
- **Test data:** synthetic data generated inside the tests, and the small shared files in
  `tests/shared/`. A committed sample of real swisstopo data is **OPEN**.
- Nothing over 10 MB is committed without a design decision naming it; GitHub rejects any
  file over 100 MB.

## 10. Game (outline; each milestone's briefs refine it)

Free-fly camera (M1); walking with collision against terrain and buildings (M6);
Terrain3D terrain with triplanar or separate rock for near-vertical faces (the Matterhorn
faces cannot be a heightmap overhang); buildings from swissBUILDINGS3D (plain shapes, the
diorama style reads that as intentional); stylised materials; real sun position for
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

## 11. Delivery (owner, day one: option b)

Exported Windows and Linux builds on a `dist` shelf branch (orphan, never merged, never
deleted), previous version kept as `*-previous.*` for rollback (`docs/RELEASE.md` §C).
Consequences: Godot 4.6.3 export templates are downloaded from the mirror at release time;
the pipeline regenerates the assets from pinned inputs before export; binaries accumulate
in the `dist` history. GitHub rejects files over 100 MB: the first release measures the
export size, and a larger export is a design question (split the pack file, or LFS on
`dist`) — **OPEN** until then.

**Version scheme (confirmed by the owner, 2026-09-25):** `0.<n>.<patch>` for releases
before v1; `1.0.0` when the v1 scope (§2) is complete. The version lives in
`game/project.godot` (`application/config/version`). **Where it shows:** only on the pause
screen (owner, 2026-09-25: option b), so a screenshot sent to `feedback` shows the version
only when the pause screen is open.

**The first version, 0.1.0,** ships at M1's close, the first milestone with something to
look at; M0 closed without one, because it had nothing to play (ruled at the M0 close).
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
| 18 | Software rendering in containers for smoke screenshots | Yes, as evidence in Findings, never as a gate | Owner |
| 19 | Camera controls (the design's proposal) | Kept as proposed (Godot editor fly mode) | Owner (no change asked) |
| 20 | Form of the tile pin (D7) | `config/datasets.lock.json`, written by `python -m mattini lock terrain` | Design (M0 close: "M1 planning picks the form") |
| 21 | Raster libraries | rasterio and numpy confirmed | Design, delegated (CLAUDE.md §Stack) |

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
- Backdrop and larger-area extents and resolutions — M5.
- Access route for swissBUILDINGS3D (14.1 GB national file) — M2; for swissTLM3D (national
  only) — M3.
- A committed sample of real swisstopo data as a test fixture (M1 tests with a synthetic
  fixture instead).
- Export over 100 MB on `dist` — at the first release (M1's close; §11).
- Game type — later.

Answered at M1 planning (2026-09-25; §13 rows 14–19): the terrain resolution, where the
version shows, the version scheme, whether the owner designs visuals, software rendering
in containers.
