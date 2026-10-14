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
