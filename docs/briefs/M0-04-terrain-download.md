# Brief: M0-04 — Terrain download for the village area (the first M1 step)
Status: DONE (a383cff)

Written in the design realm; executed by one fresh executor session. Executor rules:
`docs/roles/BUILD.md`.

## Goal

`uv run --project pipeline python -m mattini download terrain` fetches the six swissALTI3D
tiles that cover the village area (edition and resolution from `config/datasets.json`)
into `data/raw/swissalti3d/<edition>/`, checks every file against swisstopo's published
SHA-256, never fetches a verified file again, and writes a deterministic `provenance.json`
recording what was fetched and its attribution. Every machine that runs the pipeline then
starts from byte-identical terrain inputs.

## Read first, in order

1. `CLAUDE.md` — Hard Rules 2, 3 and 5.
2. `docs/SPEC.md` §5 Data sources, §7 Areas, §9 Storage.
3. `config/datasets.json` and `config/world.json`.
4. `docs/briefs/pinning/M0-04/pipeline/tests/test_download.py` — the pinning tests.
5. The live STAC item, the ground truth for asset keys and `file:checksum`:
   https://data.geo.admin.ch/api/stac/v1/collections/ch.swisstopo.swissalti3d/items/swissalti3d_2024_2623-1096

## Decisions already made

- Tiles: the 1 km tiles covering `areas.village`, six of them, 2623-1095 to 2624-1097
  (SPEC §7).
- STAC items are addressed by id:
  `https://data.geo.admin.ch/api/stac/v1/collections/<collection>/items/swissalti3d_<edition>_<tile>`.
  The asset used is the one whose key ends `_<resolution>_2056_5728.tif` (resolution 0.5
  gives `_0.5_`). Never "the latest" edition (Hard Rule 5).
- `file:checksum` is a multihash: only `1220` followed by 64 hex digits (SHA-256) is
  accepted, compared without regard to case.
- Each file downloads to a temporary `.part` file, is verified, then renamed. A mismatch
  deletes the temporary file and raises `DownloadError` naming the tile and the URL; one
  retry is allowed before failing.
- Python standard library only (urllib, hashlib, json); no new dependencies.
- The API the pinning tests use: `mattini.datasets.load_datasets()` returns the `datasets`
  object of `config/datasets.json`; `mattini.download.village_tiles(world)`,
  `parse_multihash_sha256(text)`, and `download_terrain(world, datasets, out_root,
  fetch_json, fetch_file)`, which returns the provenance list (one dict per tile, in tile
  order, with at least `tile`, `file` and `sha256`), plus `DownloadError`. The command line
  wires real urllib fetchers; tests inject fakes.
- `provenance.json` is sorted, carries no times and no absolute paths, and includes the
  attribution string from the config.
- Network tests are opt-in: a `network` pytest marker, excluded by default in the pytest
  configuration.

## Scope — files you may touch

`pipeline/mattini/datasets.py` · `pipeline/mattini/download.py` ·
`pipeline/mattini/__main__.py` (adding the `download terrain` subcommand) ·
`pipeline/pyproject.toml` (pytest marker configuration only) ·
`pipeline/tests/test_download.py` (the pinned copy, unchanged) · your own tests in
`pipeline/tests/test_download_*.py`

## Depends on

M0-01, M0-02.

## Done when (gates)

- [ ] The pinned copy is in place and unchanged (`cmp` against
      `docs/briefs/pinning/M0-04/pipeline/tests/test_download.py`).
      - does NOT prove: that the pinned tests are right (verified by the design realm
        against a scratch implementation, 2026-09-24).
- [ ] `uv run --project pipeline --frozen pytest pipeline/tests` passes without network.
      - does NOT prove: that the real server behaves like the fake (next gate).
- [ ] One real run, recorded in Findings: the command downloads six files into
      `data/raw/swissalti3d/2024/` (names, sizes and SHA-256 from `provenance.json`, total
      MB, time taken); a second run fetches nothing and leaves `provenance.json`
      byte-identical (`sha256sum` before and after).
      - does NOT prove: that other editions or tiles use the same asset naming.
- [ ] Mutation proofs recorded in Findings: (a) skip the checksum check → the bad-checksum
      test fails; (b) always re-download → the no-refetch test fails.
      - does NOT prove: behaviour when the network drops mid-file, beyond the `.part`
        handling the tests cover.
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`; `git status` shows
      nothing under `data/`.
      - does NOT prove: that the terrain looks right in the game (M1).

## Forbidden

Committing anything from `data/`; new dependencies; asking the API for "the latest"
edition; editing `config/` or `tests/shared/` (design data); changing the pinned copy.

## Findings (executor writes)

Executor session, 2026-09-24.

1. **Pinned copy:** `cmp docs/briefs/pinning/M0-04/pipeline/tests/test_download.py
   pipeline/tests/test_download.py` exits 0.
2. **pytest without network:** 209 passed, 2 deselected: 144 from M0-01/02, 5 pinned here,
   60 of my own: `test_download_refusals.py` (28: the one retry, fetch errors, malformed
   STAC items, unsafe asset names, a damaged file on disk; after every failure no `.part`,
   no file under its final name and no `provenance.json`), `test_download_provenance.py`
   (6: the exact STAC URLs, edition and resolution taken from the config, tiles following
   the village box, the provenance bytes), `test_download_datasets_config.py` (21: the
   loader's refusals, the file named) and `test_download_cli.py` (5: a local HTTP server on
   127.0.0.1 stands in for swisstopo, so the command line and the real urllib fetchers run
   end to end offline, including a 404 and a body cut short).
3. **Network tests, opt-in** (`pytest -m network`, `test_download_network.py`): 2 passed in
   11.4 s. The live 2024 items of all six tiles each carry exactly one
   `_0.5_2056_5728.tif` asset with a `1220…` checksum; a real download of the six 2 m tiles
   verifies end to end. The default run and the gate exclude them
   (`addopts = "--strict-markers -m 'not network'"`); `--strict-markers` makes a misspelt
   marker an error instead of a network test running in the gate.
4. **Real run** (`uv run --project pipeline --frozen python -m mattini download terrain`,
   cloud container, 2026-09-24): exit 0, "6 tiles verified, 6 fetches", 9.2 s wall-clock
   including uv start-up, 108'304'972 bytes (108.3 MB) in `data/raw/swissalti3d/2024/`:

   | File | Bytes | SHA-256 (from `provenance.json`) |
   |---|---|---|
   | `swissalti3d_2024_2623-1095_0.5_2056_5728.tif` | 17'418'044 | `a6ea488ecbb54b97100f22d867c38b8cd1efc37b68d61f175c98e53fb2c810ca` |
   | `swissalti3d_2024_2623-1096_0.5_2056_5728.tif` | 18'073'992 | `0e251928c93b53107618d576cf11a52299352d08532f50e3f764c635e72cc581` |
   | `swissalti3d_2024_2623-1097_0.5_2056_5728.tif` | 18'565'626 | `294bb2c6420f191dbf15d5104d130d982117528ce3fe3b271548a1e008d6ac24` |
   | `swissalti3d_2024_2624-1095_0.5_2056_5728.tif` | 18'007'501 | `57f12bcf71d823f32a3186667f8d7dbbfac80e2335454fd4d505dd17ce6e08aa` |
   | `swissalti3d_2024_2624-1096_0.5_2056_5728.tif` | 18'145'643 | `cdc98b65fccf96f1eeb2ba65009bf12cd41716d8bd2ba18260f4a072a8921f59` |
   | `swissalti3d_2024_2624-1097_0.5_2056_5728.tif` | 18'094'166 | `b6a322f4039431ba0805a4a4a19ae2b2603a2a0d0701a4cb280bb42ec09e032e` |

   The second run: exit 0, "6 tiles verified, 0 fetches", 1.7 s; `sha256sum` of all seven
   files before and after is identical (`provenance.json`
   `28523b17e7cb733f9ea09387a6ce261f9692f279466d6d97ab19636d6c7a559f` both times). The live
   item of 2623-1096 publishes `12200E251928…E72CC581`, the file's SHA-256 above.
   `git status` then shows nothing under `data/` (`.gitignore:2`, `/data/`).
5. **Mutation proofs**, one per run of `uv run --project pipeline --frozen pytest
   pipeline/tests` (the gate's first step), each applied and undone with `git apply` /
   `git apply -R` of its saved diff and `cmp` against the saved original; unmutated:
   209 passed.

   | Run | Mutation | Failing tests | Owner-visible harm |
   |---|---|---|---|
   | a (brief) | skip the checksum check: `if actual == sha256:` → `if True:` | 5 failed: pinned `test_bad_checksum_is_a_visible_error`; mine: `test_a_file_cut_short_fails_naming_tile_and_url`, `test_one_corrupt_fetch_is_retried_once`, `test_two_corrupt_fetches_fail_naming_tile_and_url`, `test_a_damaged_file_that_cannot_be_refetched_is_removed` | a corrupt or cut-short tile kept as valid terrain; two machines build different worlds from "the same" inputs |
   | b (brief) | always re-download: `if not dest.exists():` → `if True:` | 4 failed: pinned `test_download_verifies_files_and_writes_deterministic_provenance`; mine: `test_download_then_rerun_fetches_nothing`, `test_a_second_run_fetches_nothing_and_rewrites_identical_bytes`, `test_a_damaged_file_on_disk_is_fetched_again` | every pipeline run pulls 108 MB again |
   | c | no retry: `ATTEMPTS = 1` | 6 failed: `test_a_missing_file_fails_naming_tile_and_url`, `test_one_corrupt_fetch_is_retried_once`, `test_two_corrupt_fetches_fail_naming_tile_and_url`, 3× `test_a_failed_fetch_is_retried_then_reported` | one dropped connection fails the whole run |
   | d | a time in `provenance.json`: `"written": time.time()` | 4 failed: pinned `test_download_verifies_files_and_writes_deterministic_provenance`; mine: `test_download_then_rerun_fetches_nothing`, `test_provenance_does_not_depend_on_where_it_is_written`, `test_a_second_run_fetches_nothing_and_rewrites_identical_bytes` | provenance that differs on every run (Hard Rule 5) |
   | e | the `.part` file kept after a failure | 7 failed: `test_a_file_cut_short_fails_naming_tile_and_url`, `test_two_corrupt_fetches_fail_naming_tile_and_url`, 3× `test_a_failed_fetch_is_retried_then_reported`, `test_an_unexpected_error_propagates_and_leaves_no_part_file`, `test_a_damaged_file_that_cannot_be_refetched_is_removed` | unverified bytes left beside the data after a failed run |
   | f | a damaged file on disk kept: `dest.unlink()` → `pass` | 2 failed: `test_a_damaged_file_on_disk_is_fetched_again`, `test_a_damaged_file_that_cannot_be_refetched_is_removed` | a damaged tile used, and `provenance.json` claiming the published SHA-256 for it |
   | g | `load_datasets` accepts any edition (the year check removed) | 3 failed: `test_a_malformed_config_is_refused_with_the_file_named[… pinned year0–2]` ("latest", "current", "20245") | the pipeline asking for an unpinned edition (Hard Rule 5) |

6. **Measured: a body cut short is caught only by the checksum.** With Python 3.13's
   urllib, a response that stops before its `Content-Length` ends
   `shutil.copyfileobj` silently (no `IncompleteRead`): run a shows
   `test_a_file_cut_short_fails_naming_tile_and_url` failing once the checksum is skipped.
   `ConnectionResetError`, timeouts and `http.client.HTTPException` are retried once like a
   mismatch; any other exception removes the `.part` and propagates.
7. **For design to know: the second run is not offline.** It fetches the six STAC items
   again (six small JSON requests) to verify the files against the checksum swisstopo
   publishes now. If swisstopo republished a tile inside an edition (items carry an
   `updated` time; 2623-1096: 2024-12-19), the run would fetch it again and
   `provenance.json` would change: visible in its bytes, never silent, but "same inputs"
   then rests on swisstopo not republishing within an edition.
8. **Choices inside the brief's scope** (reversible):
   - `load_datasets` refuses an edition that is not a four-digit year, which makes "the
     latest" inexpressible in the config (lesson 5); every dataset needs non-empty string
     `collection`, `edition` and `attribution`; the top level is exactly `schema`,
     `terms`, `datasets`. A future dataset with a non-year edition would need that check
     changed.
   - A file on disk whose SHA-256 does not match the published one is deleted before it is
     fetched again, so a damaged file never keeps its final name even when the re-fetch
     fails.
   - The STAC item's `id` must equal the id asked for; the asset key becomes the file name
     only when it is a plain name (`[A-Za-z0-9][A-Za-z0-9._-]*`). STAC item fetches are
     not retried: a failure is a `DownloadError` naming the tile and URL, and a re-run
     resumes (verified files are kept).
   - `provenance.json`: `attribution`, `collection`, `dataset`, `edition`, `resolution_m`,
     `schema` 1 and `tiles` (`file`, `item`, `sha256`, `size_bytes`, `tile`, `url`). The
     URLs are swisstopo's; no local paths. The config's `terms` string is not in it,
     because the pinned `load_datasets()` returns only the `datasets` object.
   - The command prints progress (`fetching <url>`, `6 tiles verified, N fetches`) on
     stderr and the provenance path on stdout, as `manifest` prints its path; `--out`
     overrides `data/raw`. User-Agent `mattini-pipeline`, 60 s socket timeout.
9. **Environment:** in the cloud container urllib reached `data.geo.admin.ch` through the
   agent proxy with no code change (it honours `HTTPS_PROXY` and `SSL_CERT_FILE`). Not
   measured on the owner's PC or on Windows.
