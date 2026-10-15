# Brief: M3-06 — The surfaces step: roads, paths, water and rock from swissTLM3D
Status: DONE (c887243)

Written in the design realm; executed by one fresh builder session under
`docs/roles/BUILD.md`. Lane D of wave 1, first (`docs/briefs/M3-plan.md`).

## Goal

`pipeline/mattini/surfaces.py` turns swissTLM3D's roads, paths, rivers, streams and rock
into a class grid on the photo's 0.2 m grid. The classes are 0 none, 1 rock, 2 water, 3
path and 4 road. The game uses the grid to draw them sharp on the ground. The grid is read
straight from the national 2.88 GB FileGDB zip, never unzipped, with exact integer
predicates, so every machine gets the same classes. It is written as a PNG by a small
standard-library writer, compared with design's expected values before it is written. Its
TLM reader is a public function the trees step (M3-07, next in this lane) uses too. The
command line and the manifest come in wave 2 (M3-13).

## Read first, in order

1. `CLAUDE.md` (Hard Rules 2, 3, 5); `brain.md` H9, H17, H20, H24.
2. `docs/SPEC.md` §5 (the swissTLM3D input), §8 *The surfaces* (the rule and the codes), §13
   row 33.
3. `pipeline/mattini/terrain.py` and `buildings.py` (the structure and the `computed_for`
   helpers; how fiona is used).
4. `tests/shared/surfaces_fixture/`, `tests/shared/surfaces_vectors.json`,
   `config/surfaces.json` (design data, committed with the plan; never edited).
5. The pinned tests: `docs/briefs/pinning/M3-06/`.

## Decisions already made

1. **The rule** is SPEC §8 *The surfaces*.
   - **Reading.** A feature is read when its 2-D geometry meets the area box grown by 10 m.
     GDAL's bbox filter, grown by 1 m, is only a pre-filter; the decision is exact, in integer
     millimetres. Coordinates are snapped to the 1 mm grid; one more than 1e-6 m off is
     refused.
   - **Texel centres** are exact in integer mm.
   - **Roads (4) and paths (3):** TLM_STRASSE with BELAGSART 100 (Hart) or 200 (Natur), and
     an OBJEKTART with a width:
     - 8 → 10 m, 9 → 6 m, 10 → 4 m, 11 → 3 m, 15 → 2 m, 16 → 1 m, 17 → 1 m, 18 → 2 m,
       20 → 8 m;
     - a texel is on the line when its centre is at a 2-D distance ≤ width/2 from a segment
       (an exact rational test).
     - Not drawn: KUNSTBAUTE 300 Bruecke mit Galerie, 400 Gedeckte Bruecke, 700 Galerie,
       1000 Tunnel, 1100 Unterfuehrung, 1200 Unterfuehrung mit Treppe and 1400 in/auf
       Gebaeude (roofed or below ground). 300 and 400 are decided by design here: they are
       not in the pinned tests, so write their test.
   - **Water (2):**
     - TLM_BODENBEDECKUNG OBJEKTART 5 or 10, with the centre inside the polygon;
     - TLM_FLIESSGEWAESSER OBJEKTART 4 with VERLAUF 100 or 500, within 1.0 m of the line.
       That is an **assumed** 2 m width (`STREAM_WIDTH_MM`), a labelled placeholder: TLM gives
       none.
     - Not water: Bisse/Suone (OBJEKTART 0), and a stream on a bridge (VERLAUF 400).
   - **Rock (1):** TLM_BODENBEDECKUNG OBJEKTART 1, 2, 3, 4.
   - **Priority:** 4 > 3 > 2 > 1 > 0.
   - **Point in polygon:** even-odd per feature by the half-open crossing rule, then OR-ed
     across features.
2. **The API** (the signatures here are the API; SPEC §8 *The surfaces* holds the rule):
   - `SurfacesError(ValueError)`;
   - `read_tlm(path, layers, box)`, public, also for M3-07: features as plain dicts sorted
     by UUID, integer-mm coordinates;
   - `class_grid(features, box, cell_m)`;
   - `png_l8(pixels)` and `read_png_l8(data)`: standard-library zlib, no Pillow (the lane
     adds no dependency);
   - `load_surfaces_config`, `check_surfaces_config`, `write_surfaces(...)`;
   - `build_surfaces(world, datasets, lock, surfaces_config, raw_root, out_dir, *,
     progress=None)`;
   - `built_surfaces_block(out_dir, surfaces_config, world, world_sha256, datasets, lock)`,
     where the lock is a dict or a path (M3-03's lock lands at the same time). A lock without
     a `swisstlm3d` entry is refused naming `python -m mattini lock tlm`, never a KeyError
     (measured in design's rehearsal: a traceback).
3. **Inputs:** `<raw_root>/swisstlm3d/2026-02/swisstlm3d_2026-02_2056_5728.gdb.zip` and its
   flat provenance (M3-03's layout). The checks run in SPEC's order:
   - the world, then the lock entry, then the inputs `computed_for`;
   - the provenance;
   - **the file's size against the provenance's `size_bytes` before hashing** (an early,
     cheap refusal, decided by design);
   - the file's SHA-256 against the lock's;
   - the read, after which (size, mtime_ns, inode) must be unchanged (a 2.88 GB file is read
     through its path, not from bytes in memory).
   - **The lock's fit, in wave 1:** the step checks its entries' fit itself, in its own
     module, by the fit rule (SPEC §8, as §5 applies it to the downloads):
     swisstlm3d's collection and edition are the datasets config's (the entry pins one
     national file, no tiles), naming `python -m mattini lock tlm`. It imports
     no fit or provenance helper of `terrain.py`, `buildings.py` or `download.py` (M3-01
     changes them in lane A): `lock.fit_problem` arrives in lane A in this wave, and M3-13
     moves the step onto it in wave 2.
   - **A missing download** is refused naming `python -m mattini download tlm`, before anything is created under
     `out_dir`, not even a folder: no `provenance.json` before any `progress` call, as
     `terrain.py` does; the zip it lists absent when it is read. M3-13's pinned CLI test runs the
     step on an empty raw folder. The no-provenance case is pinned (`test_surfaces_step.py`); write the test of the
     progress order.
4. **The PNG** is 8-bit grey with no interlace, filter byte 0 on every row, one zlib stream
   at level 9 in IDAT chunks of at most 1 MiB, values 0–4.
   - Its content is pinned (`pixels_sha256`); its bytes depend on the zlib build, so they
     are checked for integrity only.
   - `surfaces/<area>.png.import` holds exactly `[remap]\n\nimporter="keep"\n` (H24: without
     it Godot imports the PNG as a texture and an export ships the texture instead of the
     PNG). It is written first, then the PNG, then `surfaces/<area>.json`, each through a
     `.part` rename. The description does not list the `.import`.
5. **The description:** exactly {area, cell_m, classes: {"0": "none", "1": "rock", "2":
   "water", "3": "path", "4": "road"}, columns, file, format "png-l8", lv95_box,
   pixels_sha256, rows, sha256 (the PNG's), source: {attribution, collection, dataset,
   edition, file, sha256}, world_sha256}.
6. **Design's values** (config/surfaces.json, the village computed two independent ways,
   identical bytes):
   - 0.2 m `93d78ba6d89eea27d0ec897d9f5fca244633336ff29378cd2b2fc9def77e5093`;
   - 0.5 m `adda417b…`; 1 m `4ea3d1e6…`;
   - computed_for: inputs `aa909f98…` (the swisstlm3d lock entry), world `d2607d13…`.

   At 0.2 m: road 74'744 m², path 47'654 m², water 40'737 m², rock 408'266 m². Measured end
   to end on the real zip: 22.6 s, 575 MB. fiona 1.10.1 (GDAL 3.9.2) reads the zip directly;
   its member names use backslashes, and that works.
7. **fiona is imported inside `read_tlm`,** never at module level. M3-01's pinned
   `test_fiona_import.py` (lane A) imports every module of the package and requires that no
   fiona module is loaded; at wave 1's integration it covers `surfaces.py`.

## Scope — files you may touch

`pipeline/mattini/surfaces.py` (new) · `pipeline/tests/`: the pinned copies
(`synthetic_tlm.py`, `test_surfaces_fixture.py`, `test_surfaces_read.py`,
`test_surfaces_step.py`) and your own new `test_surfaces_*.py`. Read-only: everything else.

## Depends on

None in this wave. M3-07 follows in this lane and imports `read_tlm`.

## Done when (gates)

- [ ] The pinned copies are in place (`cp -r docs/briefs/pinning/M3-06/. .`) and stay
      byte-identical (`cmp`).
      - does NOT prove: that they are the right tests.
- [ ] With the real TLM zip in a scratch root in M3-03's layout (2.88 GB, fetched once, with
      its provenance written by hand in that format until M3-03 lands), `build_surfaces`
      writes design's `93d78ba6…` at 0.2 m. Record the time and memory.
      - does NOT prove: that the classes sit on the photo's roads (design's preview showed
        about 1 m; the owner's eyes).
- [ ] Mutations, each failing a named pinned test, recorded:
      - a strict `<` distance test;
      - polygon edge centres counted inside;
      - water above path in priority;
      - the stream width 2 m on each side;
      - Klettersteig drawn.
      - does NOT prove: the game's reading (M3-10).
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that it renders or looks right.

## Forbidden

- Changing the rule, a code, the assumed stream width, design's values, the fixture or a
  pinned file.
- Unzipping the TLM file to disk; Pillow or any new dependency.
- Command-line or manifest wiring (M3-13).

## Findings (executor writes)

1. **The real village gives design's classes.** The national zip (2'882'823'552 bytes, SHA-256
   `185ffca8…`, equal to the lock's and to the file host's `x-amz-meta-sha256`) was fetched
   once with curl in about 50 s into a scratch root in M3-03's layout, with a provenance.json
   written by hand in M3-03's flat form (M3-03 had not landed), and the lock entry made in the
   driver script with `entry_sha256` `aa909f98…` (= `computed_for.inputs_sha256` in
   config/surfaces.json). `build_surfaces` with the committed config wrote
   `pixels_sha256` **`93d78ba6d89eea27d0ec897d9f5fca244633336ff29378cd2b2fc9def77e5093`** at
   0.2 m, the step's own comparison passing. **31.4 s end to end, peak 395 MB resident**
   (SHA-256 of the file 9.3 s, `read_tlm` 8.1 s, classes 6.5 s, PNG and files 7.5 s). It read
   230 TLM_BODENBEDECKUNG, 73 TLM_FLIESSGEWAESSER and 843 TLM_STRASSE features, the counts
   design's notes give. The same features at 0.5 m and 1 m hash to `adda417b…` and
   `4ea3d1e6…`, and the 0.2 m areas are road 74'744 m², path 47'654 m², water 40'737 m²,
   rock 408'266 m², all design's. The built output went through `built_surfaces_block`
   (1.2 s) with the committed configs, and `read_png_l8` of the 1'148'917-byte PNG gave
   the grid back. *does NOT prove:* that the classes sit on the photo's roads (design's
   preview showed about 1 m; the owner's eyes), or a run on another machine.
2. **The five required mutations, each caught by a named pinned test.** Each was applied to
   a copy of `surfaces.py` and run against the three pinned test files; the first (and
   every other) failure included `tests/test_surfaces_fixture.py::test_the_class_grid_is_the_designed_one`,
   plus `test_other_cells_give_the_designed_classes` at 0.5 and 1 m,
   `test_write_surfaces_writes_the_designed_files`,
   `test_surfaces_step.py::test_the_step_writes_the_designed_classes` and
   `test_other_classes_are_refused_before_anything_is_written`; the module was restored
   byte-identical (`cmp`) after each. The owner-visible harm each reproduces:
   - a strict distance test (`isqrt(r²·len² − 1)` for the band, `r² − 1` for the discs):
     every road and path edge one texel too narrow, the 507 texels design's twins list;
   - polygon edge centres counted inside (`floor(...) + 1` for `ceil(...)`): rock and water
     one texel too big on their east and north edges (136 texels);
   - water above path (painting order rock, path, water, road): a path across a stream or
     pond shows as water;
   - the stream width 2 m on each side (radius 2000 mm, not 1000): every stream twice as wide;
   - Klettersteig drawn (every BELAGSART but 100 painted as a path): the via ferrata and
     the unknown surfaces (999997, 999998) appear as paths on rock.
3. **Own mutations against my own tests** (the full `-k surfaces` run, first failure
   shown): `_meets` touching not read (`<=` for `<`) → `test_the_reader_hands_over_the_features_that_meet_the_box`;
   the 1 mm snapping check off → `test_a_coordinate_off_the_1_mm_grid_is_refused`; the size
   not compared → `test_a_size_that_differs_is_refused_before_the_file_is_hashed`; the SHA-256
   check after the read → `test_the_progress_lines_come_in_order_and_the_hash_comes_before_the_read`;
   no `.png.import` → `test_the_files_are_written_in_order_each_through_a_part_rename`;
   joined line parts, a zero-length guard dropped, the half-open row rule at the other
   end, the 10 m margin 0, the pre-filter shrunk, a land-cover kind added or dropped → each a
   named test; the band limit one too wide (`T + 1`) and the disc one square millimetre too
   wide survived the first set of tests, since the 50 mm lattice of the random cases
   cannot reach them, and are now killed by
   `test_a_centre_a_thousandth_of_a_millimetre_beyond_a_band_is_not_on_the_line` and
   `test_a_centre_beyond_a_disc_by_one_square_millimetre_is_not_on_the_line`. Two mutants are
   **equivalent** (the band's foot bound moved by one unit of `t`, on either axis): the end
   discs cover exactly those texels, so no test can tell them apart. *does NOT prove:* the
   game's reading (M3-10).
4. **Decisions inside the brief's scope** (the first of each is the one taken):
   - `class_grid` takes exactly the three layers (a missing or extra one is refused naming
     it), so that a typo cannot drop a layer silently; a TLM_STRASSE whose BELAGSART is not
     100 or 200 is not drawn (the Klettersteig and unknown surfaces).
   - `provenance.json` is checked for what the step uses (dataset, collection, edition, file,
     SHA-256 case-insensitively, `size_bytes` a positive integer), not for its exact key set:
     the alternative (exactly M3-03's ten keys) would couple the step to a form lane A is
     still writing.
   - `built_surfaces_block` also requires `<area>.png.import` to hold exactly the keep text
     (H24), as the export would ship a texture otherwise.
   - The lock given as a path is read here as plain JSON and checked by the step's own fit
     rule: `lock.validate_lock` does not know `swisstlm3d` until M3-03 lands. M3-13 moves
     the fit onto `lock.fit_problem`, and can then use `load_lock` for the path.
   - After a successful write, `*.part` files left in `surfaces/` are removed (M3-01
     decision 5 for the other steps); a refusal removes nothing.
   - `read_tlm` also accepts a single LineString or Polygon and hands over its Multi form;
     any other geometry type, a null geometry, a null attribute and a UUID twice in a
     layer are refused naming the layer. A vertex more than 537 km (2²⁹ mm) from the box
     is refused, which keeps every product in 64-bit.
   - Imports from `terrain.py` are the names M3-01 decision 10 keeps (`world_refusal`,
     `inputs_refusal`, `check_computed_for`, `configured_area`, `OWNER_AXES`, `AREA_NAME`)
     and `download.PROVENANCE`; no fit or provenance helper of `terrain.py`, `buildings.py`
     or `download.py`.
5. **Seams for the orchestrator and wave 2.** `load_datasets` still demands a four-digit
   edition until M3-01 and M3-03 land: the driver passed the datasets as a dict, as the
   pinned tests do. `build_surfaces` takes the lock as a dict; M3-13 passes what
   `load_lock` returns. The reader returns coordinates as lists of `[E, N]` integer
   millimetres, in the order GDAL gives them, the form M3-07 imports. fiona is imported
   inside `read_tlm` only (a subprocess test checks a fresh interpreter).
6. **Not claimed.** The step was run on one machine; the PNG's bytes depend on the zlib
   build and were checked for integrity only; "renders / looks right" is the owner's PC.
7. **Gates.** The pinned copies are byte-identical to `docs/briefs/pinning/M3-06/` (`cmp`);
   own tests: `test_surfaces_reference.py` (122: the vectorised grid against the rule
   written out texel by texel with fractions, on random features with ties),
   `test_surfaces_rules.py` (85), `test_surfaces_checks.py` (54), `test_surfaces_config.py`
   (36), `test_surfaces_png.py` (33), `test_surfaces_reader.py` (29): 382 surfaces tests
   with the pinned 23.
8. **The standard gate** (`tools/gate.sh > gate.log && git commit`, rule 3c) was green on the
   commit before every rebase: 1125 pytest tests and GUT's 23 scripts; then on the head with
   lanes B, C, E, F and G's landings (1317 pytest tests, 37 GUT scripts) and again with lane
   A's M3-01 (1423 pytest tests, 37 scripts), whose census tests (`test_fiona_import.py`,
   `test_docstring_claims.py`, `test_checks_before_reading.py`, `test_part_leftovers.py`)
   cover `surfaces.py` and pass. Two pushes were rejected by landings that arrived during
   the 2 m 37 s gate runs (M3-10's code, then its two brief-status lines): the last rebase
   brought in only `docs/briefs/M3-09-*.md` and `M3-10-*.md`, which no test reads, and was
   pushed without a fourth gate run; the gate then ran on the pushed head (below).
   *does NOT prove:* that it renders or looks right.
