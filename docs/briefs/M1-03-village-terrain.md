# Brief: M1-03 — The village terrain from the downloaded tiles
Status: OPEN

Written in the design realm; executed by one fresh executor session. Executor rules:
`docs/roles/BUILD.md`.

## Goal

`uv run --project pipeline python -m mattini terrain` turns the six downloaded,
lock-verified swissALTI3D tiles into `game/assets/generated/terrain/village.f32`, 4001 ×
6001 heights at 0.5 m, with its description `village.json` beside it, and rewrites the
manifest, whose new `terrain` block carries that description. The file is the same, bit for
bit, on every machine that runs the step on the pinned tiles (SHA-256
`b6334c1fdc992f0576bc59efd51484db2178cbe399ad46512a4bf510abb9411a`), and `manifest` refuses a
terrain that no longer matches the config, naming the command that rebuilds it.

## Read first, in order

1. `CLAUDE.md` — Hard Rules 2, 4 and 5.
2. `docs/SPEC.md` §8 *The terrain grid* (the whole design of this brief), §5 (the lock), §7
   (the owner chose 0.5 m), §9.
3. `docs/history/ARCS.md` §M0: D7 and D9, the carry-over table row C-05/D7.
4. `config/terrain.json`, `config/world.json`, `config/datasets.json`, and
   `config/datasets.lock.json` (written by M1-01).
5. `tests/shared/terrain_vectors.json` and `tests/shared/terrain_fixture/`: the fixture this
   brief must reproduce byte for byte (read its `about`).
6. The pinning tests, `docs/briefs/pinning/M1-03/pipeline/tests/`:
   `test_terrain_fixture.py`, `test_terrain_rules.py`, `test_terrain_manifest.py`,
   `test_terrain_build.py`.
7. The live STAC items and swisstopo's height service, the ground truth for the real run:
   `https://api3.geo.admin.ch/rest/services/height?easting=<E>&northing=<N>&sr=2056`
   (returns `{"height": "<m, 0.1 m>"}`; measured 2026-09-25 to agree with the 2024 tiles).

## Decisions already made

- **The rule, the file and the block:** SPEC §8, exactly; the pinning tests are its
  executable form. Everything in 64-bit, one rounding to 32-bit at the end: the sums of up
  to 16 32-bit heights are exact in 64-bit, so the result does not depend on the order or
  the machine. A vectorised form is expected (design's scratch took 9 s and about 1.5 GB for
  the village, using a 64-bit integral image).
- **Dependencies:** rasterio and numpy, confirmed by design (SPEC §4, §13 row 21): `uv add
  --project pipeline rasterio numpy`, lockfile committed. rasterio's `from_origin` prints a
  `PendingDeprecationWarning`; warnings do not fail the gate.
- **API** (the pinning tests use these names): `mattini.terrain.SPACINGS` (0.5, 1.0, 2.0),
  `TerrainError` (a `ValueError`), `load_terrain_config(path=config/terrain.json)` (schema
  1, exactly one area in M1, spacing in `SPACINGS`; errors name the file),
  `resample(mosaic, box, spacing_m, height_offset_m)` (mosaic: 32-bit, north-up, 0.5 m
  pixels covering `box` = (e_min, e_max, n_min, n_max) exactly; returns 32-bit rows ×
  columns), `write_terrain(out_dir, area, heights, box, spacing_m, world_sha256, source)`
  (writes `terrain/<area>.f32` through a `.part` rename, then `terrain/<area>.json`;
  returns the block), `build_terrain(world, datasets, lock, terrain_config, raw_root,
  out_dir)`. `mattini.manifest.write_manifest(out_dir, config_path, *,
  terrain_config_path=…, datasets_path=…)`, defaults the committed configs.
- **Inputs** (D9, D7): `provenance.json` of the pinned edition is the only tile list; it
  must match the config's edition, resolution and tiles, else `TerrainError` naming `python
  -m mattini download terrain`. Every file's SHA-256 must equal its provenance entry and the
  lock's. Every tile: EPSG:2056, 2000 × 2000 32-bit pixels of 0.5 m, top-left corner at
  (e_km × 1000, (n_km + 1) × 1000), one band; no nodata value and no non-finite value
  (named: tile and pixel). The mosaic is assembled from these checks only; stray files are
  never read.
- **Only the owner's axes** (x=+e, y=+h, z=−n) are supported for terrain: refuse another
  mapping with `TerrainError`. The area's north-west corner must be on the vertex lattice
  (`(e_min − origin_e) / s` and `(n_max − origin_n) / s` whole), else refuse.
- **The manifest** gains the `terrain` key (null until built; the block verbatim after);
  `manifest` refuses a built terrain whose `world_sha256`, spacing, edition, resolution or
  heights file (size and SHA-256) no longer match, naming `python -m mattini terrain`, and
  writes nothing then. The live copy of M1-01's `test_golden_outputs.py` takes the new key
  set and the golden `a04c269d19ba62f7600733abf52defb4817da419bfa1ed7adfa42b33bd8c8828`
  (the same value `test_terrain_manifest.py` pins).
- **Command line:** `python -m mattini terrain [--raw data/raw] [--out
  game/assets/generated]` builds the terrain, then writes the manifest, and prints the
  manifest's path on stdout, progress on stderr; errors as `mattini: error: …`, exit 1.

## Scope — files you may touch

`pipeline/mattini/terrain.py` (new) · `pipeline/mattini/manifest.py` ·
`pipeline/mattini/__main__.py` · `pipeline/pyproject.toml` and `pipeline/uv.lock` (the two
dependencies) · `pipeline/tests/` (the pinned copies, your own tests, and the live copies of
earlier tests the new manifest key set changes)

## Depends on

M1-01 (the lock and the goldens). Shares no file with M1-04: the two may run at once.

## Done when (gates)

- [ ] The four pinned files are in place and unchanged (`cmp`).
      - does NOT prove: that the pinned tests are right (design ran them against a scratch
        implementation, 2026-09-25: 54 passed; float32 sums, a half-pixel shift, an ignored
        height offset and a missing nodata check each fail 4 to 15 of them).
- [ ] `uv run --project pipeline --frozen pytest pipeline/tests` passes without network.
      - does NOT prove: the real tiles' behaviour (next gate).
- [ ] One real run in the container, recorded in Findings: `download terrain`, then
      `terrain`; `sha256sum game/assets/generated/terrain/village.f32` equals `b6334c1f…`
      (above), 96'040'004 bytes; wall-clock and peak memory (`/proc/<pid>/status` VmHWM or
      `resource.getrusage`); the manifest's `terrain` block; a second `terrain` run gives
      identical bytes; `git status` clean. A different SHA-256 is a BLOCKED question with
      both values, never a new pin.
      - does NOT prove: that the owner's Windows PC computes the same bytes (the owner's
        first run is the check: the SHA-256 in this brief).
- [ ] The seven check points, recorded in Findings: each height read from `village.f32`
      (row = (1098000 − N) / 0.5, column = (E − 2623000) / 0.5) equals design's value
      exactly, and differs from swisstopo's height service, re-queried, by at most 0.25 m:

      | Point | E | N | Height (float32) | Service, 2026-09-25 |
      |---|---|---|---|---|
      | Bahnhofplatz 1 address point | 2623923.5 | 1096921.5 | 1605.63916015625 | 1605.6 |
      | tile 2623-1095, flat | 2623379.0 | 1095670.0 | 1625.824951171875 | 1625.8 |
      | tile 2623-1096, flat | 2623598.5 | 1096301.5 | 1632.9407958984375 | 1632.9 |
      | tile 2623-1097, slope 0.27 | 2623366.0 | 1097479.5 | 2244.98681640625 | 2244.8 |
      | tile 2624-1095, slope 0.29 | 2624538.5 | 1095660.5 | 2015.10009765625 | 2015.2 |
      | tile 2624-1096, flat | 2624301.5 | 1096692.0 | 1646.32763671875 | 1646.3 |
      | tile 2624-1097, flat | 2624300.5 | 1097366.5 | 1593.6585693359375 | 1593.7 |

      - does NOT prove: sub-decimetre agreement with swisstopo on steep ground (the service
        interpolates its own way); a half-pixel shift (the fixture tests catch that).
- [ ] Mutation proofs, one per pytest run, each undone with `git apply -R`, each row naming
      the owner-visible harm: (a) 32-bit sums → the fixture and rule tests fail; (b) the
      pixel south-east of each vertex instead of the mean → fail; (c) `height_offset_m`
      ignored → fail; (d) the tile list read from the folder instead of `provenance.json` →
      `test_a_stray_tif_in_the_folder_is_not_read` fails; (e) `manifest` without its
      `world_sha256` check → `test_terrain_built_for_another_world_is_refused` fails.
      - does NOT prove: that no other mutation survives.
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`; nothing under `data/` or
      `game/assets/generated/` committed.
      - does NOT prove: that the terrain renders or sits right in the game (M1-04, M1-05).

## Forbidden

Committing raw or generated data; any dependency other than rasterio and numpy; reading
the download folder's listing; a tolerance in place of the exact rule; changing `config/`,
`tests/shared/` or a pinned copy; touching `game/` or `tools/` (M1-04's).

## Findings (executor writes)

