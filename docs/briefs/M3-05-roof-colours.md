# Brief: M3-05 — Roof colours from the photo
Status: OPEN

Written in the design realm; executed by one fresh builder session under
`docs/roles/BUILD.md`. Lane C of wave 1, after M3-04 (`docs/briefs/M3-plan.md`).

## Goal

`pipeline/mattini/roofs.py` gives each of the village's 1'486 buildings the colour of its
roof as the 2023 photo shows it. That colour is the per-channel lower median of the photo's
0.1 m pixels inside the building's roof triangles, exactly reproducible. The result is
written as `roofs/<area>.json`, the same bytes on every machine, compared with design's
expected value before it is written. Each building also gets its id (UUID) and its triangle
and vertex counts in its chunk, so the game can tell which triangles are whose. This is also
the first piece of what FB-002's builder idea would need (board, Ideas). The command line and
the manifest come in wave 2 (M3-13).

## Read first, in order

1. `CLAUDE.md` (Hard Rules 2, 4, 5); `brain.md` H16, H17, H20.
2. `docs/SPEC.md` §8 *The buildings* (selection, snapping, orientation, chunks, order),
   *Roof colours* (the rule), *The photo* (the tiles).
3. `pipeline/mattini/buildings.py`, `pipeline/mattini/photo.py` (M3-04, landed in this lane
   just before), `pipeline/mattini/terrain.py` (the `computed_for` helpers).
4. `tests/shared/roofs_fixture/`, `tests/shared/roofs_vectors.json`, `config/roofs.json`
   (design data, committed with the plan; never edited).
5. The pinned tests: `docs/briefs/pinning/M3-05/`.

## Decisions already made

1. **The rule** is SPEC §8 *Roof colours*. Arithmetic is in integer units of 0.1 mm.
   - **Roof triangles:** `n_H > 0` and `4·n_H² ≥ n_E² + n_N² + n_H²` (the game's rule;
     measured to agree with the game's float32 rule on all 178'910 village triangles).
   - **Roof pixels:** the photo's 0.1 m pixels whose centre lies inside or on the boundary of
     a roof triangle's plan projection.
   - **Colour:** the lower median per channel (index floor((n − 1)/2)), null when there is no
     pixel. Roof parts outside the photo have no pixels and are not refused (one village
     building has 22 such pixel centres).
2. **The API** (the signatures here are the API; SPEC §8 *Roof colours* holds the rule):
   - `RoofsError(ValueError)`, as BuildingsError (M3-13's pinned manifest test catches a
     ValueError), `load_roofs_config`, `check_roofs_config`;
   - `build_roof_chunks(features, world, area, photo)`, where `photo` is an iterable of
     non-overlapping rasters `(west_dm, north_dm, pixels)` consumed once, so that one tile is
     decoded at a time;
   - `write_roofs(out_dir, area, chunks, box, world_sha256, source)`;
   - `build_roofs(world, datasets, lock, roofs_config, terrain_config, raw_root, out_dir, *,
     progress=None)` (specified, not pinned: no committed fixture can hold 1 km tiles);
   - `built_roofs_block(out_dir, roofs_config, terrain_config, world, world_sha256, datasets,
     lock, buildings_block)`.
3. **The selection** is the buildings step's own (selection, snapping, welding, solid check,
   orientation, UUID order), and `buildings.py` stays read-only in this lane: lane A changes
   it in this wave (M3-01). `roofs.py` repeats the selection loop and imports only names
   M3-01 keeps (its decision 10): `build_chunks`, `read_sheet`, `BuildingsError` and the rule
   helpers `_snapped`, `_weld`, `_check_solid`, `_signed_volume`. The pinned roofs fixture
   guards that the selection is the buildings step's (the chunks' counts and the UUID order).
   A public per-building derivation in `buildings.py` is left for later (the plan's
   DEFERRED). The photo tiles come through `photo.py`'s checked tile reader.
4. **Inputs:**
   - `<raw_root>/swissbuildings3d/2020/` and `<raw_root>/swissimage/2023/` with their
     provenance (SPEC §5);
   - every file checked against provenance and lock, and read from the very bytes hashed;
   - `computed_for`: the world first, then both lock entries' fit, then the inputs, whose
     SHA-256 is that of the canonical `{"swissbuildings3d": …, "swissimage": …}` object;
     write a small helper for it (M3-13 moves it into `lock.py`).
   - **The lock's fit, in wave 1:** the step checks its entries' fit itself, in its own
     module, by the fit rule (SPEC §8, as §5 applies it to the downloads):
     swissbuildings3d's collection and edition are the config's and it pins exactly the
     area's sheets (`download.area_sheets`); swissimage's collection, edition and
     `resolution_m` are the config's and it pins exactly the area's tiles, naming `python -m mattini lock buildings` or `lock photo`. It imports
     no fit or provenance helper of `terrain.py`, `buildings.py` or `download.py` (M3-01
     changes them in lane A): `lock.fit_problem` arrives in lane A in this wave, and M3-13
     moves the step onto it in wave 2.
   - **A missing download** is refused naming `python -m mattini download buildings` or `download photo`, the first missing in sorted dataset order, before anything is created under
     `out_dir`, not even a folder: no `provenance.json` before any `progress` call, as
     `terrain.py` does; a file it lists absent when it is read. M3-13's pinned CLI test runs the
     step on an empty raw folder. Not pinned in this lane: write its test.
5. **The file:** `roofs/<area>.json` (sorted keys, 2-space indent, UTF-8, LF, final newline,
   through a `.part` rename) = exactly {area, chunks: [{buildings: [{roof, roof_pixels,
   triangles, uuid, vertices}] in chunk order, tile}] by tile, format `roofs-v1`, lv95_box,
   source: {buildings, photo}, world_sha256}.
   - `roof` is lower-case `rrggbb` or null.
   - The manifest carries this file verbatim as its `roofs` block, as it does the buildings'
     description: the block is the data.
6. **`built_roofs_block`** checks:
   - `computed_for`, the key sets, area, format, world_sha256 and lv95_box;
   - the source against the datasets config and both lock entries;
   - the file's SHA-256 against `expected_sha256`;
   - its chunks against `buildings_block`: the same tiles in order, and per chunk the building
     count and the sums of triangles and vertices.

   It refuses roof colours when no buildings are built, naming `python -m mattini
   buildings` (M3-13's manifest checks this first); its other refusals name `python -m
   mattini roofs`. A lock without one of the two entries is refused naming its lock command,
   never a KeyError (measured in design's rehearsal: a traceback).
7. **Design's value** (config/roofs.json, computed two independent ways, identical bytes):
   - SHA-256 `8d9664b643173eaee7d1980438600c7bcb7dd8d1921346466ec72b716c480db5` (290'006
     bytes);
   - every building coloured, none null; 32'452 roof triangles; 30'392'135 roof pixels;
   - computed_for: inputs `e66bee6e…`, world `d2607d13…`.

   Design's two ways took about 45 s and 1.1–1.4 GB each.

## Scope — files you may touch

`pipeline/mattini/roofs.py` (new) · `pipeline/mattini/photo.py` (only to expose its tile
reader, if M3-04 left it private) · `pipeline/tests/`: the two pinned copies
(`test_roofs_fixture.py`, `test_roofs_expected.py`) and your own new `test_roofs_*.py`.
Read-only: everything else, `buildings.py` included.

## Depends on

M3-04 (the same lane: `photo.py`'s tile reader). Nothing in the other lanes; the names it
imports from lane A's modules are the ones M3-01 keeps. In wave 1,
M3-03's lock does not hold a `swissimage` entry yet: tests use the fixture's own lock, and
`built_roofs_block` takes the lock as a dict.

## Done when (gates)

- [ ] The pinned copies are in place (`cp -r docs/briefs/pinning/M3-05/. .`) and stay
      byte-identical (`cmp`).
      - does NOT prove: that they are the right tests.
- [ ] With the real inputs in a scratch checkout (the six sheets with `download buildings`;
      the six photo tiles fetched as M3-04's gate says), `build_roofs` writes design's
      `8d9664b6…`, and the per-chunk sums equal the chunk files `buildings` writes. Record
      the time and peak memory.
      - does NOT prove: that the colours look right (the owner's eyes; the 2020 outlines sit
        1–2 m off the 2023 photo in places).
- [ ] Mutations, each failing a named pinned test, recorded:
      - the upper median;
      - the boundary excluded;
      - `n_H > 0` alone as the roof rule;
      - pixel corners in place of centres;
      - null written as "".
      - does NOT prove: the game's use (M3-12).
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that it renders or looks right.

## Forbidden

Changing the rule, the buildings step's bytes, design's value, the fixture or a pinned file;
any command-line or manifest wiring (M3-13); a new dependency.

## Findings (executor writes)

Lane builder of lane C, wave 1, 2026-10-15, on `main` after M3-04 (`3c1b8d5`).

1. **Pinned copies.** `cp -r docs/briefs/pinning/M3-05/. .` placed `test_roofs_fixture.py` and
   `test_roofs_expected.py`; all 16 pass against the first version of `roofs.py` and stay
   byte-identical (`cmp` before the commit). `photo.py` is unchanged by this brief.
2. **Gate 2, the real village.** The six sheets came from `python -m mattini download
   buildings` (6 fetched, verified, 13.9 MB), the six tiles from M3-04's scratch folder; the
   lock was the committed one plus the `swissimage` entry of M3-04's scratch run, whose
   two-entry hash `inputs_sha256(lock)` is `e66bee6e…`, design's. `build_roofs` wrote
   `roofs/village.json` with SHA-256 `8d9664b643173eaee7d1980438600c7bcb7dd8d1921346466ec72b716c480db5`,
   290'006 bytes (the step compared it with config/roofs.json before writing): 1'486 buildings
   in 6 chunks, every one coloured (no null), 30'392'135 roof pixels, 178'910 triangles and
   92'594 vertices, which are the buildings step's totals. Two runs, the second on the final
   code with identical bytes: 28.3 s and 26.9 s (sheets 6 s, tiles about 22 s), peak resident
   memory (`ru_maxrss` of the child) 1'267 MB and 1'452 MB. The peak is the 300 MB raster, its
   300 MB transposed copy in `photo.read_tiles`, the features and GDAL's cache; reading the
   bands one by one into the final array would save about 300 MB (not done: M3-05's Scope
   lets `photo.py` change only to expose its reader).
3. **The seam to the buildings' chunk files**, measured on the real village: `python -m mattini
   buildings` into the same output, then `built_roofs_block` with its description accepted
   the roofs, and per chunk 12 · vertices + 12 · triangles equals the chunk file's size:

   | tile | buildings | triangles | vertices | file bytes |
   |---|---|---|---|---|
   | 2623-1095 | 369 | 41'688 | 21'595 | 759'396 |
   | 2623-1096 | 489 | 62'348 | 32'252 | 1'135'200 |
   | 2623-1097 | 2 | 646 | 331 | 11'724 |
   | 2624-1095 | 24 | 2'396 | 1'246 | 43'704 |
   | 2624-1096 | 323 | 37'938 | 19'648 | 691'032 |
   | 2624-1097 | 279 | 33'894 | 17'522 | 616'992 |

   Does NOT prove: that the colours look right (the owner's eyes; the 2020 outlines sit 1–2 m
   off the 2023 photo in places).
4. **Mutations**, each in `roofs.py` alone, the roofs tests run, the file restored from a
   saved copy (`cmp` identical after each batch). "Harm" is the owner-visible harm the
   mutation reproduces (lesson 4):

   | mutation | failing pinned tests | harm |
   |---|---|---|
   | the upper median | `test_the_rule_gives_the_fixture_s_roofs`, `test_no_roof_pixel_means_no_colour`, `test_write_roofs_writes_the_fixture_s_bytes` (14 fail in all) | on an even pixel count every roof's colour is the higher of the two middle values: a shade lighter than design's |
   | the boundary excluded | the same three (9 fail) | pixels centred on a roof's edge are left out: each colour is read from a slightly smaller area |
   | `n_H > 0` alone as the roof rule | the same three (11 fail) | faces steeper than 60° (a tower's, a gable's) count as roof and pull the median |
   | pixel corners in place of centres | the same three (12 fail) | every roof read half a pixel (5 cm) off its place: pixels of the ground or the next roof count instead of its own |
   | null written as "" | the same three (11 fail) | the game gets an empty string where it must get null and keep the neutral roof |

   More mutations (all fail named tests): the slope limit at 45°; 64-bit squares in the roof
   test (`test_a_roof_triangle_at_the_slope_limit_in_numbers_beyond_64_bits` and the
   pinned three); a pixel counted per roof triangle; a row or a column off by one; no
   orientation by the signed volume; the selection's edges swapped (west and south out); the
   chunk order by tile alone; upper-case hexadecimal written; no overlap check (4 fail);
   `built_roofs_block` without its SHA-256 check, without its comparison with the buildings,
   or without refusing roofs when no buildings are built; `build_roofs` without its comparison
   with `expected_sha256`, with its inputs check before the world's, or with the photo's
   errors not made RoofsErrors.
5. **My tests**, 136 in three files and two helpers: the rule (44: the roof triangle in
   numbers beyond 64 bits and at the 60° limit; a right triangle of 11 × 11 pixel centres by
   hand, 66 inside or on, and its edge moved 1 mm inward (56) and outward (66); a roof of
   three triangles that share edges counted once (not 70); a scalar oracle over the fixture's
   buildings turned and moved at random under noise cut into windows at random, three seeds;
   the rasters: any cutting or order, overlap refused, malformed refused, none at all;
   the median against sorted lists; the selection's edges, a UUID twice, an open solid);
   the step (28: the fixture's buildings over four noise GeoTIFF tiles read for real, the file
   equal to the bytes the test assembled, twice the same; every refusal in its order, nothing
   created and no progress call before the downloads are vouched for, no sheet or tile read
   before the world and inputs checks pass, with a positive control); `built_roofs_block`
   (64: every description edit, the SHA-256, the buildings' own chunks, the lock as a
   path, each lock entry missing or not fitting). `roofs_oracle.py` holds the scalar oracle,
   `roofs_inputs.py` lays the fixture out as the downloads leave it.
6. **Decisions inside the brief.**
   - A FileGDB that fiona writes does not give back a solid's triangles (M2-04's Findings: the
     writer re-winds and regroups rings), so the step's tests take the sheet file to be the
     fixture's own `source.json`, as the fixture's lock pins it, through a stand-in for
     `read_sheet`; the real `read_sheet` is the buildings tests' and the real run's.
   - The photo of the step's tests is noise over the area grown by 60 m, not design's
     windows: a window's missing pixels are no photo, a tile's are zeros, so a roof that
     reaches past the windows (two of the fixture's do) would count differently through a
     GeoTIFF tile. The expected colours there are the oracle's; design's chunks give the
     buildings' order, tiles and counts.
   - `build_roof_chunks` refuses overlapping rasters (RoofsError): a pixel in two rasters
     would count twice and the median would move without a word. Not in the brief; no
     producer overlaps today (tiles do not).
   - The photo's errors (`PhotoError`: tile, lock, provenance) reach the caller as
     RoofsErrors with the same message, so the manifest and the command line catch one class
     per step. `inputs_sha256(lock)` is public here until M3-13 moves it into the lock module.
   - A missing download names `download buildings` before `download photo` (the datasets'
     names in order); the lock's buildings entry is checked before the photo's.
   - `roofs.py` imports from lane A's modules only names M3-01 keeps: `BuildingsError`,
     `read_sheet`, `_snapped`, `_weld`, `_check_solid`, `_signed_volume`, `area_sheets`,
     `area_tiles`, `PROVENANCE`, `load_lock`, and from `terrain.py` `AREA_NAME`,
     `check_computed_for`, `check_terrain_config`, `configured_area`, `world_refusal`;
     `BUILDINGS` is defined in `roofs.py` (it is not on that list).
