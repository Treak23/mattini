# Brief: M3-04 — The photo step: SWISSIMAGE 2023 at 0.2 m
Status: OPEN

Written in the design realm; executed by one fresh builder session under
`docs/roles/BUILD.md`. Lane C of wave 1, first (`docs/briefs/M3-plan.md`).

## Goal

`pipeline/mattini/photo.py` builds the village's aerial photo from the six SWISSIMAGE 2023
tiles. It is a 10'000 × 15'000 grid of 0.2 m texels and a 50 MB JPEG, the same bytes on every
machine, each compared with design's expected values before it is written. It also checks a
built photo for the manifest's future `photo` block. The command line and the manifest come in
wave 2 (M3-13): this brief exposes the functions they will call, exactly as named below.

## Read first, in order

1. `CLAUDE.md` (Hard Rules 2, 4, 5); `brain.md` H9, H20, H21, H24.
2. `docs/SPEC.md` §5 (the paragraph on the photo, the surface model and swissTLM3D), §8
   *The photo* (the rule), §13 rows 30, 35.
3. `pipeline/mattini/terrain.py` (its structure is the model: config loader, pure grid
   function, writer, `build_terrain`, `built_terrain_block`, `computed_for` refusals).
4. `tests/shared/photo_fixture/`, `tests/shared/photo_vectors.json`, `config/photo.json`
   (design data, committed with the plan; never edited).
5. The pinned tests: `docs/briefs/pinning/M3-04/`.

## Decisions already made

1. **The rule** is SPEC §8 *The photo*.
   - Each texel is the k × k block of 0.1 m source pixels counted from the area's north-west
     corner (k = 2, 5, 10 for cell 0.2, 0.5, 1 m), per channel round-half-to-even of the
     exact integer sum / k².
   - The raw grid's SHA-256 is `pixels_sha256`.
   - JPEG by Pillow: `quality=92, subsampling=2, optimize=False, progressive=False`.
   - Box arithmetic is in integer decimetres: an edge off the 0.1 m grid by more than 1e-6 m
     is refused, and the sides must be whole cells.
   - The tiles are those the area box meets (`download.area_tiles`).
2. **The API.** The pinned tests import `PhotoError`, `load_photo_config`, `photo_grid`,
   `encode_jpeg`, `write_photo`, `build_photo` and `built_photo_block`; the other three are
   named for your own tests and follow `terrain.py`'s pattern:
   - `PhotoError(ValueError)`, `load_photo_config`;
   - `check_photo_config(data, where="the photo config") -> None`, raising PhotoError, as
     `check_terrain_config` does;
   - `cell_key(cell_m) -> str`: "0.2", "0.5" or "1", the keys of `expected_pixels_sha256` and
     `expected_sha256`, written in `photo.py` as `terrain.spacing_key` is (`format(cell_m,
     "g")`), not imported: M3-01 does not keep that name;
   - `photo_grid(mosaic, box, cell_m)` (pure);
   - `encode_jpeg(pixels)`; `jpeg_encoder() -> str`, "Pillow <version>, libjpeg-turbo
     <version>", the text the JPEG refusal names;
   - `write_photo(out_dir, area, pixels, box, cell_m, world_sha256, source)`;
   - `build_photo(world, datasets, lock, photo_config, raw_root, out_dir, *, progress=None)`;
   - `built_photo_block(out_dir, photo_config, world, world_sha256, datasets,
     lock=LOCK_PATH)`, where `lock` is a dict or a path. Until M3-03 lands, `lock.validate_lock`
     refuses a `swissimage` entry, so the tests pass the dict.
3. **Inputs.**
   - The tiles are read from `<raw_root>/swissimage/2023/` and the `provenance.json` beside
     them (exactly the terrain's keys; M3-03 writes them).
   - Each file's SHA-256 is checked against provenance and lock, and read from the very bytes
     hashed.
   - Refused unless EPSG:2056, 10'000 × 10'000 pixels, 3 uint8 bands, and the transform
     exactly (0.1, 0, E0, 0, −0.1, N0 + 1000).
4. **The order of refusals.**
   - `computed_for`'s world first, then the lock's fit, then its inputs, the world and the
     inputs as design changes.
   - **The lock's fit, in wave 1:** the step checks its entries' fit itself, in its own
     module, by the fit rule (SPEC §8, as §5 applies it to the downloads):
     swissimage's collection, edition and `resolution_m` are the datasets config's, and it
     pins exactly the area's tiles, naming `python -m mattini lock photo`. It imports
     no fit or provenance helper of `terrain.py`, `buildings.py` or `download.py` (M3-01
     changes them in lane A): `lock.fit_problem` arrives in lane A in this wave, and M3-13
     moves the step onto it in wave 2.
   - **A missing download** is refused naming `python -m mattini download photo`, before anything is created under
     `out_dir`, not even a folder: no `provenance.json` before any `progress` call, as
     `terrain.py` does; a file it lists absent when it is read. M3-13's pinned CLI test runs the
     step on an empty raw folder. Not pinned in this lane: write its test.
   - Then the pixels: "this machine or this code computes other pixels than design's …".
   - Then the JPEG: "the pixels are design's; this machine's JPEG encoder writes other bytes:
     Pillow <v>, libjpeg-turbo <v> …".
   - Both name the two SHA-256s. Only then are the files written.
5. **The files,** each through a `.part` rename:
   - `photo/<area>.jpg`;
   - `photo/<area>.jpg.import`, exactly `[remap]\n\nimporter="keep"\n` (25 bytes; brain.md
     H24: without it Godot imports the JPEG as a 170 MB texture and an export ships that
     instead of the file);
   - `photo/<area>.json`, the description, which does not list the `.import`.
6. **`built_photo_block`** refuses, naming `python -m mattini photo`:
   - a description whose key sets, area, file, format, jpeg, cell, world, box, columns, rows or
     source differ from what the configs and the lock give;
   - a JPEG whose SHA-256 is not the block's and design's;
   - a `pixels_sha256` that is not design's;
   - **a missing or different `.import` file beside the JPEG** (not pinned: write its test).
7. **Memory: under 2 GB on the village.** `build_photo` runs `photo_grid` on strips of whole
   texel rows (100 m strips: the rule counts from the north-west corner, so the bytes are the
   same), each strip reading only its windows of the verified tiles. Measured: a whole-area
   mosaic peaks at 10.5 GB (design's wave-1 rehearsal), strips at 1.6 GB with the same JPEG;
   design's two ways peaked at 1.45–1.79 GB. Seven lanes run at once on one machine, so the
   limit is a gate.
8. **Design's values** (config/photo.json, computed two independent ways, identical bytes):
   - 0.2 m: pixels `00533bc6…`, JPEG `cf83c705…` (50'222'573 bytes);
   - 0.5 m: pixels `1e105d47…`, JPEG `5035fe52…`;
   - 1 m: pixels `b99f0710…`, JPEG `db1d1b78…`;
   - computed_for: inputs `415ed9bc…` (the swissimage lock entry), world `d2607d13…`.

   A third independent build (the data-packs agent's) gave the same 0.2 m values. Godot's
   JPEG decoder gives the same pixels as Pillow's for this file.
9. **Pillow** is the new dependency: `uv add pillow` in `pipeline/` (12.3.0 resolved on
   2026-10-14; `pillow>=12.3.0`), with the matching `uv.lock` (the gate refuses one out of
   step). The JPEG bytes were the same with Pillow 10.4.0, 11.0.0 and 12.3.0, and with
   libjpeg-turbo's SIMD off.

## Scope — files you may touch

`pipeline/mattini/photo.py` (new) · `pipeline/pyproject.toml` and `pipeline/uv.lock`
(Pillow only) · `pipeline/tests/`: the three pinned copies (`test_photo_fixture.py`,
`test_photo_build_tiles.py`, `test_photo_expected.py`) and your own new `test_photo_*.py`.
Read-only: everything else, including `terrain.py` and `download.py`: import only the names
M3-01 keeps (its decision 10); change none.

## Depends on

None in this wave (M3-03's lock and download land in lane A at the same time; the tests use
the fixture's own lock and provenance). M3-05 follows in this lane and imports `photo.py`'s
tile reader: keep it a public function (`read_tiles` or as you name it, documented).

## Done when (gates)

- [ ] The pinned copies are in place (`cp -r docs/briefs/pinning/M3-04/. .`) and stay
      byte-identical (`cmp`).
      - does NOT prove: that they are the right tests.
- [ ] With the real inputs in a scratch checkout (`download photo` exists only once M3-03 lands;
      until then fetch the six tiles yourself into `<scratch>/swissimage/2023/` and write the
      provenance in the terrain's format), `build_photo` at 0.2 m writes design's JPEG and
      pixels, and at 0.5 m and 1 m (config edited in scratch only) theirs. Record the times and
      the peak memory, which must stay under 2 GB at 0.2 m (the process's `VmHWM` in
      `/proc/<pid>/status`, or `resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss` after
      running it as a child; the container has no `/usr/bin/time`).
      - does NOT prove: that the owner's Windows machine decodes the tiles to the same pixels.
        If it does not, the step refuses with the pixels message, and design decides (a
        decoder without GDAL is the measured fallback).
- [ ] Mutations, each failing a named pinned test, recorded:
      - round-half-up;
      - the JPEG compared before the pixels;
      - no transform check;
      - BGR into the JPEG;
      - no `.import` file.
      - does NOT prove: anything about the game's reading (M3-09).
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that it renders or looks right.

## Forbidden

- Changing the rule, a JPEG setting, design's values, the fixture or a pinned file.
- Any command-line or manifest wiring (M3-13).
- A dependency other than Pillow.

## Findings (executor writes)
