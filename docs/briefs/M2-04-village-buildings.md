# Brief: M2-04 — The village buildings from the downloaded sheets
Status: DONE (b980214)

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

- [x] The pinned copies are in place and byte-identical (`cmp`).
      - does NOT prove: that the pinned tests are the right tests.
- [x] With the real sheets (downloaded to a scratch folder, never committed),
      `python -m mattini buildings --raw <scratch>` writes design's six chunks and exits 0;
      the step prints 1'486 buildings (Findings: the run's output).
      - does NOT prove: that the owner's Windows PC reads the same numbers (its GDAL is its
        wheel's; the snapping is meant to absorb that, and the step's own check says so if
        it does not).
- [x] Mutations, each run through the full gate (Findings: both runs):
      - the orientation step skipped;
      - the snapping skipped;
      - the chunk rule using the first vertex instead of the bounding-box centre;
      - the axis mapping bypassed (x = E − origin_e hard-coded).

      Each fails a named test. State the owner-visible harm each one reproduces.
      - does NOT prove: that the game draws the buildings where the terrain is (M2-05).
- [x] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that anything renders or looks right.

## Forbidden

A change to the rule or to the fixture's or config's expected bytes (BLOCKED instead); a
second new dependency; writing glTF.

## Findings (executor writes)

Executor: an Opus agent of the one M2 session, in its own worktree (branch
`worktree-wf_4de6848a-f86-2`, fast-forwarded to 7abf9e1 first). Implementation commit
b980214. Nothing pushed, no Routine fired (the owner's M2 ruling, RULINGS 2026-09-25).

**The gates, with their evidence**

1. *Pinned copies.* `cp -r docs/briefs/pinning/M2-04/. .`, then `cmp` of the four files
   (`config/buildings.json`, `test_buildings_fixture.py`, `test_buildings_read.py`,
   `test_buildings_rules.py`) against their pinned copies: identical before each commit.
   All 27 pinned tests passed at the new module's first run.
2. *The real run.* `uv run --project pipeline python -m mattini buildings --raw
   <scratch>/raw --out <scratch>/m204/out` over the six 2020 sheets and their
   provenance.json in the session's scratchpad (never in the repository): exit 0, 7.2 s.
   Its stderr, verbatim but for the scratch path:

   ```
   reading <scratch>/raw/swissbuildings3d/2020/swissbuildings3d_3_0_2020_1328-33_2056_5728.gdb.zip
   … (the same line for 1328-34, 1348-11, 1348-12, 1348-13, 1348-14)
   sheet 1328-33: 3 features read, 0 selected
   sheet 1328-34: 68 features read, 0 selected
   sheet 1348-11: 1359 features read, 1236 selected
   sheet 1348-12: 440 features read, 250 selected
   sheet 1348-13: 229 features read, 0 selected
   sheet 1348-14: 35 features read, 0 selected
   1486 buildings in 6 chunks: 92594 vertices, 178910 triangles, 3258048 bytes
   the 6 chunks have the SHA-256s config/buildings.json expects
   wrote <scratch>/m204/out/buildings (6 chunks and village.json)
   ```

   Its stdout: the manifest's path. `sha256sum` of the six chunk files gives the brief's
   six values, and the block's counts are the table's (369 / 21'595 / 41'688 … 279 /
   17'522 / 33'894). `buildings/village.json` is byte-identical (`cmp`) to the description
   of design's second implementation (`cfddb51d…`, scratchpad `f2/real/`). The manifest is
   `ebd3fdef…`, its top level `buildings, schema, terrain, world, world_sha256`, and
   `python -m mattini manifest` over the same folder rewrites the same bytes. `python -m
   mattini terrain` into the same folder afterwards (heights `b6334c1f…`, as expected)
   wrote a manifest holding both blocks. The step's own comparison of the six hashes runs
   before anything is written (lesson 38), so the owner's first run carries the check.
3. *Mutations*, each through the full gate (`tools/gate.sh`, logs in the scratchpad), each
   undone with `git apply -R` of its saved diff; after each, `buildings.py` was back to
   SHA-256 `eb18a978…` and `git status` showed only the intended changes. The second run of
   every row is the commit's gate (green, below), whose `buildings.py` is that same file.

   | Mutation | Gate | What failed: named test, message | Same code on the real sheets |
   |---|---|---|---|
   | 1. orientation skipped (the reversal → `pass`) | exit 1 at pytest, 12 failed | `test_buildings_rules.py::test_a_negative_solid_is_reversed_and_placed`: `assert [(0, 1, 2), …] == [(0, 2, 1), …]`; `test_buildings_fixture.py::test_the_chunks_hold_the_designed_buildings`: `2650-1149` differs at byte 460; the step tests: `config/buildings.json expects c92aa635…` | the step refuses: chunk 2623-1095 `18562d4a…`, expected `85273add…`; nothing written |
   | 2. snapping skipped (`snapped = value`) | exit 1 at pytest: 3 failed at its first run, 5 at its second | first run: `test_buildings_rules.py::test_a_coordinate_off_the_storage_grid_is_refused[e]`, `[n]`, `[h]`: `DID NOT RAISE BuildingsError`. Second run, once `test_buildings_snapping.py` existed (item 7): those three, `test_one_noisy_reading_of_a_corner_still_welds` (`not a closed, consistently oriented triangle mesh`) and `test_noise_does_not_move_a_centre_off_the_west_edge` (the building dropped) | six float32 values of chunk 2623-1095 one step off (z −0.015 → −0.015000001), so the step refuses |
   | 2b. added: the grid checked, the raw value kept (`return value`), snapping's likeliest twin | exit 1 at pytest: 2 failed, 621 passed | only the two new snapping tests: without them the whole gate passed this twin | as 2 |
   | 3. the chunk by the first vertex, not the bounding-box centre | exit 1 at pytest, 10 failed | `test_buildings_fixture.py::test_the_chunks_hold_the_designed_buildings`: tiles `'2651-1149' != '2651-1150'` (building c's vertex 0 lies east of E 2'651'000); `test_buildings_rules.py::test_chunks_follow_the_bounding_box_centre_and_uuid_order` | the step refuses: chunk 2623-1095 `ae998d84…`, expected `85273add…` |
   | 4. axis mapping bypassed (x = E − origin_e, y = H − offset, z = −(N − origin_n) hard-coded) | exit 1 at pytest, 1 failed | `test_buildings_rules.py::test_placement_follows_any_rotation_of_the_world`: `(950.47…, 1020.12…, 19.875) != (-19.875, 1020.12…, 950.47…)` | exit 0, the six chunks design's: on the owner's axes the hard-coded mapping writes the same bytes |

   The owner-visible harm each reproduces. (1) All of swisstopo's solids read V < 0, so
   every building would be written wound inward, and the game takes the file's order as
   outward (SPEC §8, M2-05): walls and roofs facing inside, culled or lit from behind seen
   from outside. (2, 2b) The chunks would follow the last bits of GDAL's decoding, which
   the owner's Windows GDAL may produce differently: other chunks than design's on his
   PC, refused there by the step's check, so no buildings; a corner read two ways would
   not weld (the building refused); a centre on the area's edge could drop out of the
   village. (3) A building astride a kilometre line filed under the tile of whichever
   corner swisstopo lists first: once chunks load by distance, it appears or vanishes with
   the wrong tile. (4) A second home for the axis mapping (Hard Rule 4): the day
   config/world.json's axes change, the game follows the manifest while the buildings keep
   the old mapping, the village silently rotated or mirrored against everything else. Only
   the rotation test sees it; the real run cannot.
4. *Standard gate.* `tools/gate.sh > <scratch>/gate-M2-04.log 2>&1 && git commit -F …` →
   b980214. The log: `uv lock --check` passed; pytest `623 passed, 4 deselected`; ruff
   check and format clean; the manifest step; Godot 4.6.3 import and parse check; GUT
   `---- All tests passed! ----` (16 scripts, 76 tests, 1726 asserts); gdlint and
   gdformat; `== gate: all steps passed`. This Findings commit is chained on the gate too.

**Numbers and surprises**

5. *fiona.* `uv add --project pipeline fiona` locked fiona 1.10.1 (bundling GDAL 3.9.2,
   `fiona.__gdal_version__`, measured) with its cp313 wheels for manylinux x86_64, macOS
   and **`fiona-1.10.1-cp313-cp313-win_amd64.whl`** (sha256 `15751c90…`, 24'461'486 bytes)
   in `pipeline/uv.lock`. It brought two packages of its own, click-plugins 1.1.1.2 and
   cligj 0.7.2 (attrs, certifi and click were locked already); nothing else was added. It
   runs beside rasterio 1.5.1 in one process (the gate's pytest and the real runs import
   both).
6. *Snapping on the real sheets (measured).* It moves 2'120'072 of the 2'259'594
   coordinates read, by at most 1.86e-9 m in E and N and 7.3e-12 m in H (fiona hands over
   `2622709.7309999987` for 2'622'709.731). All 2'134 features pass the reader's checks and
   the 1e-6 m tolerance; the 1'486 selected are closed, consistently oriented and all
   reversed (V < 0), as design measured.
7. *The pinned noise test cannot see a missing snap* (lesson 34).
   `test_reader_noise_is_snapped_to_the_storage_grid` moves every reading of a corner by
   the same 64-bit step, which the float32 rounding absorbs and which welds anyway: it
   passed under mutation 2, and mutation 2b passed every pinned test. Added
   `test_buildings_snapping.py`: one reading of a corner off by 1e-9 m must still weld, and
   a building whose centre is on the west edge once snapped (1e-9 m west of it as read,
   which the test asserts) must stay in. Both fail under 2 and 2b.
8. *A FileGDB that fiona writes cannot stand in for a sheet end to end* (measured). GDAL
   regroups a MultiPolygon's rings by their orientation seen from above when it reads the
   layer back (two of the fixture's eleven buildings came back with four-ring polygons,
   all eleven with their triangles in another order), and its writer re-winds each ring
   (clockwise seen from above). `CREATE_MULTIPATCH=YES` changed nothing through fiona's
   OpenFileGDB (the layer stays 3D MultiPolygon). So `test_buildings_step.py` stands the
   fixture's `source.json` in for sheet 1249-42, as the fixture's own lock pins it, with a
   stand-in reader that records the bytes it is handed (they must be the bytes hashed); it
   reproduces the fixture's `generated/` files and manifest byte for byte. The real reader
   runs inside the step in one refusal test (a quad, naming sheet and UUID) and in the
   pinned and added reader tests; swisstopo's own format is proved by the real run alone,
   as the brief says.
9. *Golden manifest.* The live golden (`test_golden_outputs.py`, and the same value in
   `test_terrain_manifest.py`) moves from `a04c269d…` to `ba8383ff…`: the old bytes with
   the one line `  "buildings": null,` inserted (removing that line gives `a04c269d…`
   again, measured). The two terrain fixtures' manifests gained that line and nothing else.

**Readings taken where the brief left a choice** (reversible; none changes the rule, the
fixture or the config)

10. `build_buildings` requires the lock's buildings entry to pin exactly the area's sheets,
    not the superset `download buildings` accepts: `manifest` checks a block's sheets
    against the lock's, in order, and `built_buildings_block` has no world from which to
    derive the area's sheets, so a lock pinning more would yield buildings the manifest
    refuses. The committed lock pins exactly the six.
11. `built_buildings_block(…, lock)` takes the lock or its path; the manifest passes the
    path, read only when buildings are built (the terrain's rule: a manifest with nothing
    built depends on no lock). The manifest always loads and validates the buildings config,
    as it does the terrain config, but compares its area only once a block is built
    ("whatever the buildings config says": the terrain fixtures run with the committed
    config, area village).
12. `read_sheet` returns exactly `{uuid, objektart, triangles}`; `build_buildings` adds a
    `sheet` key to each feature, so that `build_chunks`' refusals name sheet and UUID as
    SPEC §8 asks (without it they name the UUID).
13. Refusals the rule implies without listing them, each naming the UUID: a null or empty
    geometry (reader); a non-finite coordinate, a feature without triangles, a face that is
    not three points (rule). None occurs in the six sheets. The per-building checks (weld,
    closed, volume) run on the selected buildings only, snapping and its tolerance on every
    feature read ("every coordinate is snapped"). Entries of a zip beside its one `.gdb`
    folder are not read.
14. Pipeline code may not name an area (`test_download_area.py` counts the word "village"
    in `pipeline/mattini/`): the module's first line and a parser variable are worded
    around it.

**Out-of-scope touches:** none. Every changed file is on the brief's list
(`pipeline/tests/` holds `test_repo_tracked.py`, whose REQUIRED list now also names
`config/buildings.json` and `tests/shared/buildings_vectors.json`).

**Follow-up candidates**

- `write_buildings` does not remove chunk files that an earlier build wrote and the new
  description no longer lists (after a changed area or config); an export would ship them.
- CLAUDE.md §Layout does not list `config/buildings.json`.
- SPEC §8 could record items 7 and 8, and brain.md §Hazards item 8 (a fiona-written
  FileGDB does not give back the triangles it was given).
- The real reader's format becomes a gate only with the owner's sample (SPEC §13 row 24);
  today the real run's hashes prove it.
