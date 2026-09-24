# Brief: M0-04 — Terrain download for the village area (the first M1 step)
Status: OPEN

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
