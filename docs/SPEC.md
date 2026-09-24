# SPEC.md — mattini, design of record (v0, 2026-09-24; amended at the M0 close)

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
| Terrain | **Terrain3D 1.0.2** (MIT, C++ GDExtension) | Godot Asset Store: `store.godotengine.org/asset/tokisangames/terrain3d/`, file `Terrain3D_v1.0.2-stable-2.zip`, SHA-256 `a071850250ec5e596aa54da61c01d75768774eb379ee997584d426a45f4884a2` | Owner's choice |
| Renderer | Forward+ (Godot's desktop default) | — | Design (reversible): the owner's GPUs are desktop RTX-class |
| Game tests | **GUT 9.6.1** (MIT) | git tag `v9.6.1` of `github.com/bitwes/Gut` (commit `c80954f47bed74a0a2c471d472c0389f98e0a8f6`); `git clone` works in containers | Design, delegated by the owner (§13) |
| GDScript lint | gdtoolkit **4.5.0** (`gdlint`, `gdformat`) | PyPI, as a pipeline dev dependency | One tool environment for all linting |
| Pipeline | Python **3.13** via **uv**, lockfile committed | uv installs Python itself (works in containers) | Design, delegated by the owner (§13) |
| Python checks | pytest, ruff | PyPI | — |

Measured on 2026-09-24 in a cloud container: Godot 4.6.3 runs headless; GUT 9.6.1 runs
headless with a non-zero exit on a failing test; Terrain3D 1.0.2 loads headless in 4.6.3
and heights imported through its API read back exactly; gdlint/gdformat run; `uv python
install 3.13` works. Binary wheels exist for Python 3.12 and 3.13 on Linux and Windows for
numpy, rasterio (bundles GDAL), pyproj (bundles PROJ), shapely (bundles GEOS), pyogrio,
laspy + lazrs and trimesh — none confirmed yet as dependencies (CLAUDE.md §Stack: each is
confirmed by the design realm before it is added). The hazards found while measuring are
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
change like a new edition (the form of the pin is M1's).

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
**In-game terrain resolution for the village** (0.5 m source; 0.5, 1 or 2 m in the game):
**OPEN**, asked when M1 is planned.

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
screen is generated from it.

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
  above; only the Linux and Windows x86_64 binaries, about 15 MB, plus what the plugin
  needs to load) and `game/addons/gut/` (about 3 MB). Each vendoring commit names the
  source and checksum.
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
the first shared build); a version line (where it shows: **OPEN**).

## 11. Delivery (owner, day one: option b)

Exported Windows and Linux builds on a `dist` shelf branch (orphan, never merged, never
deleted), previous version kept as `*-previous.*` for rollback (`docs/RELEASE.md` §C).
Consequences: Godot 4.6.3 export templates are downloaded from the mirror at release time;
the pipeline regenerates the assets from pinned inputs before export; binaries accumulate
in the `dist` history. GitHub rejects files over 100 MB: the first release measures the
export size, and a larger export is a design question (split the pack file, or LFS on
`dist`) — **OPEN** until then.

**Version scheme — PROPOSED:** `0.<n>.<patch>` for releases before v1; `1.0.0` when the v1
scope (§2) is complete. The version lives in `game/project.godot`
(`application/config/version`).

**The first version** is planned for M1's close, the first milestone with something to
look at; M0 closed without one, because it had nothing to play (the main scene is empty)
(ruled at the M0 close). Where the version shows and the version scheme are asked when M1
is planned.

## 12. What cloud sessions can and cannot verify

Builders and reviewers run in containers without a GPU. They prove the pipeline, data
transforms, coordinate maths, scene loading and game logic headless. They cannot prove
that anything renders or looks right: every brief that changes what is drawn carries
*"does NOT prove: that it renders or looks right"*, and the owner's PC is the visual test
(bugs return through `feedback`). Software rendering in the container for smoke
screenshots is **OPEN**.

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

Readings the design realm took from those answers (the owner may reverse any):
"soft rule" = the licence rule is an ordinary rule (the owner's word can override it), not
an absolute; it is enforced by a test and the release checklist and reviewed at Tier 2
(WORKFLOW §Review policy). With no never-happen rule, Tier 1 review covers
`config/world.json` and the coordinate transforms, and full discipline (mutation proofs)
covers those plus the pipeline's determinism (Hard Rules 4 and 5).

## 14. Open decisions

Asked when the milestone that needs them is planned; each is also on the board.

- macOS builds.
- Whether the owner designs screens or visuals (`docs/design/`).
- Where the game shows its version (must be decided before the first release).
- Licence of mattini's own code (the repository is private; without a licence file it is
  all rights reserved by default).
- Weather: simulated, or real data (MeteoSwiss open data, Open-Meteo) — M6.
- In-game terrain resolution for the village — M1.
- Backdrop and larger-area extents and resolutions — M5.
- Access route for swissBUILDINGS3D (14.1 GB national file) — M2; for swissTLM3D (national
  only) — M3.
- A committed sample of real swisstopo data as a test fixture.
- Software rendering in containers for smoke screenshots.
- Export over 100 MB on `dist` — at the first release.
- Version scheme (PROPOSED in §11).
- Game type — later.
