# Brief: M2-04 — The village buildings from the downloaded sheets
Status: OPEN

Written in the design realm; executed under `docs/roles/BUILD.md` (in M2 by an Opus agent
of the one M2 session, the owner's word of 2026-09-25, `docs/history/RULINGS.md`).

## Goal

`uv run --project pipeline python -m mattini buildings` turns the downloaded,
lock-verified swissBUILDINGS3D sheets into the village's building chunks and rewrites the
manifest, whose new `buildings` block describes them. That is one mesh file per 1 km tile
under `game/assets/generated/buildings/`, in local coordinates, oriented outward, plus
their description `buildings/village.json`. The files are the same, bit for bit, on every
machine that runs the step on the pinned sheets: design's six SHA-256s, which the step
checks before writing anything. `manifest` refuses buildings that no longer match their
inputs, naming the command that rebuilds them.

## Read first, in order

1. `CLAUDE.md`: Hard Rules 2, 4 and 5; `docs/LESSONS.md` 33, 34, 38.
2. `docs/SPEC.md` §8 *The buildings* (the whole design of this brief) and *The terrain
   grid* (the pattern this step follows), §4 (fiona), §9.
3. `pipeline/mattini/terrain.py` and `manifest.py` as M2-01 left them: the step, its
   refusals, its description and `built_terrain_block` are the model.
4. `config/buildings.json` (the expected SHA-256 of each chunk), `config/world.json`,
   `config/terrain.json` (the area), `config/datasets.json`, `config/datasets.lock.json`.
5. `tests/shared/buildings_fixture/` and `tests/shared/buildings_vectors.json`: the
   fixture this brief must reproduce byte for byte.
6. `tests/shared/buildings_sample/` if it exists: one real sheet (1328-33, 2020, three
   buildings, 45'668 bytes, © swisstopo), committed only on the owner's word (SPEC §13 row
   24), with its pinned test `test_buildings_read_sample.py`.
7. The pinning tests, `docs/briefs/pinning/M2-04/pipeline/tests/`.

## Decisions already made

- **The rule, the files and the block:** SPEC §8 *The buildings*, exactly; the pinning
  tests are its executable form.
- **Dependency:** fiona, confirmed by design (SPEC §4, §13): `uv add --project pipeline
  fiona`, lockfile committed. pyogrio cannot read the layer at all: it refuses its geometry
  type, TIN Z (measured). fiona 1.10.1 bundles GDAL 3.9.2 and has wheels for Python 3.13
  on Linux and Windows. It works beside rasterio's GDAL 3.12.4 in one process (measured).
- **API** (the pinning tests use these names), in `pipeline/mattini/buildings.py`:
  - `BuildingsError` (a `ValueError`) and `FORMAT = "mesh-f32-u32-le"`;
  - `load_buildings_config(path=config/buildings.json)`: schema 1; exactly one area whose
    key set is `{"expected_sha256"}`; each tile id `<e km>-<n km>` maps to 64 lower-case
    hex digits; errors name the file;
  - `read_sheet(data: bytes, sheet: str) -> list[dict]`: the features of the zipped
    FileGDB in `data` (opened with `fiona.io.ZipMemoryFile`; its one `.gdb` folder; layer
    `Building_solid`), in reading order. Each is `{"uuid", "objektart", "triangles"}`, the
    triangles as tuples of three `(E, N, H)` float tuples as read (not snapped). It
    refuses what SPEC §8 *Reading* refuses, naming the sheet and UUID;
  - `build_chunks(features, world, area) -> list[dict]`: snapping, selection, welding,
    checks, orientation, placement and chunking per SPEC §8. It returns the chunks sorted
    by tile, each `{"tile", "buildings", "vertices", "triangles", "data"}`, `data` being
    the file's bytes. `features` is one list in reading order (sheets in sheet order,
    each in its own order);
  - `write_buildings(out_dir, area, chunks, box, world_sha256, source) -> dict`: writes
    each `buildings/<tile>.bin` through a `.part` rename, then `buildings/<area>.json`, and
    returns the block;
  - `build_buildings(world, datasets, lock, buildings_config, terrain_config, raw_root,
    out_dir, *, progress=None) -> dict`;
  - `built_buildings_block(out_dir, buildings_config, terrain_config, world_sha256,
    datasets, lock) -> dict | None`.
- **Inputs** (as the terrain's):
  - `provenance.json` of the pinned edition is the only sheet list. It must match the
    config's dataset, collection and edition, and the sheets `sheets_near(area box)`
    gives, else refuse naming `python -m mattini download buildings`;
  - every zip's SHA-256 must equal its provenance entry and the lock's, and the bytes
    hashed are the bytes read.
- **Expected output (lesson 38):** `build_buildings` compares the set of chunk tiles and
  each chunk's SHA-256 with `config/buildings.json` before writing anything. A difference
  refuses, naming the tile, both values and the file, and says design computed them two
  independent ways. The village (design, M2 planning, two implementations, identical
  bytes):

  | Tile | Buildings | Vertices | Triangles | SHA-256 of `buildings/<tile>.bin` |
  |---|---|---|---|---|
  | 2623-1095 | 369 | 21'595 | 41'688 | `85273add6ae6a3f8968b4e78944a2ea5113e401f7eedbb40130b9b5b202adb96` |
  | 2623-1096 | 489 | 32'252 | 62'348 | `e2c657fd0c3550fe11ddcf211781a1da3ba40210b545452a05acb8ff846a2c5d` |
  | 2623-1097 | 2 | 331 | 646 | `7484d4bfbad6325c304dfd1d4b6a694688ba490a7e7f08b221cd431e38e6dd00` |
  | 2624-1095 | 24 | 1'246 | 2'396 | `72155f75dcb0b44a1bb49f06a041ee0e2157b185d0d3fcc5395356fb00e320db` |
  | 2624-1096 | 323 | 19'648 | 37'938 | `32068ec65f52078bf668209cb95c24234d3eb8aaeed0a452f1a876fba1004d0e` |
  | 2624-1097 | 279 | 17'522 | 33'894 | `5d64e30f6e52d78134c567d313d9bbea53fe5b0aabf20e11891459f5885c05f3` |

  Totals: 1'486 buildings (1'236 from sheet 1348-11, 250 from 1348-12), 92'594 vertices,
  178'910 triangles, 3'258'048 bytes. Every one of the 2'134 solids of the six sheets reads
  closed, consistently oriented and negative; snapping moves no coordinate by more than
  1.9e-9 m.
- **The manifest** gains the key `buildings` (null until built; the block verbatim after).
  Its top level is exactly `buildings`, `schema`, `terrain`, `world`, `world_sha256`.
  `manifest` refuses a built block, naming `python -m mattini buildings`, and writes
  nothing, when:
  - its key sets are not exact;
  - its `world_sha256` differs from the world config's;
  - its `source` differs from the datasets config (attribution, collection, edition) or
    the lock (the sheets and their SHA-256s, in order);
  - a chunk file's size or SHA-256 differs from its entry;
  - the chunks differ from `config/buildings.json`.

  `build_manifest` and `write_manifest` take a keyword `buildings_config_path` (default
  the committed `config/buildings.json`). The buildings' area is the terrain config's one
  area (T-06), and a manifest built in a folder without `buildings/<area>.json` has
  `"buildings": null` whatever the buildings config says. The live golden manifest test
  takes the new key set. The two terrain fixtures'
  `generated/manifest.json` gain `"buildings": null`, the one change to their bytes
  (design's decision; their heights and descriptions stay as they are).
- **Command line:** `python -m mattini buildings [--raw data/raw] [--out
  game/assets/generated]` builds, then writes the manifest; prints the manifest's path on
  stdout, progress on stderr (per sheet: how many features read, how many selected; the
  totals); errors `mattini: error: …`, exit 1.
- **The reader's tests:** `test_buildings_read.py` (pinned) tests reading and the
  refusals on synthetic FileGDBs that fiona writes in the test. Those hold MultiPolygon Z,
  not MultiPatch: GDAL cannot write a MultiPatch (measured). So swisstopo's real format is
  tested only by the real run, whose chunks must equal design's hashes, and, if the owner
  agrees to commit a real sample, by `test_buildings_read_sample.py` over it. Then
  `test_repo_hygiene.py` names that one file as the only raw file allowed in git.

## Scope: files you may touch

`config/buildings.json` (the pinned copy, never edited) ·
`pipeline/mattini/buildings.py` (new) · `pipeline/mattini/manifest.py` ·
`pipeline/mattini/__main__.py` · `pipeline/pyproject.toml`, `pipeline/uv.lock` (fiona) ·
`pipeline/tests/` · `tests/shared/terrain_fixture/generated/manifest.json` and
`tests/shared/terrain_fixture_nw/generated/manifest.json` (the new key only).

## Depends on

M2-01, M2-03.

## Done when (gates)

- [ ] The pinned copies are in place and byte-identical (`cmp`).
      - does NOT prove: that the pinned tests are the right tests.
- [ ] With the real sheets (downloaded to a scratch folder, never committed),
      `python -m mattini buildings --raw <scratch>` writes design's six chunks and exits 0;
      the step prints 1'486 buildings (Findings: the run's output).
      - does NOT prove: that the owner's Windows PC reads the same numbers (its GDAL is its
        wheel's; the snapping is meant to absorb that, and the step's own check says so if
        it does not).
- [ ] Mutations, each run through the full gate (Findings: both runs):
      - the orientation step skipped;
      - the snapping skipped;
      - the chunk rule using the first vertex instead of the bounding-box centre;
      - the axis mapping bypassed (x = E − origin_e hard-coded).

      Each fails a named test. State the owner-visible harm each one reproduces.
      - does NOT prove: that the game draws the buildings where the terrain is (M2-05).
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that anything renders or looks right.

## Forbidden

A change to the rule or to the fixture's or config's expected bytes (BLOCKED instead); a
second new dependency; writing glTF.

## Findings (executor writes)
