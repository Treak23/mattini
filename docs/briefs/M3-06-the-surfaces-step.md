# Brief: M3-06 — The surfaces step: roads, paths, water and rock from swissTLM3D
Status: OPEN

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
2. **The API** (signatures in SPEC §8 *The surfaces*):
   - `SurfacesError`;
   - `read_tlm(path, layers, box)`, public, also for M3-07: features as plain dicts sorted
     by UUID, integer-mm coordinates;
   - `class_grid(features, box, cell_m)`;
   - `png_l8(pixels)` and `read_png_l8(data)`: standard-library zlib, no Pillow (the lane
     adds no dependency);
   - `load_surfaces_config`, `check_surfaces_config`, `write_surfaces(...)`;
   - `build_surfaces(world, datasets, lock, surfaces_config, raw_root, out_dir, *,
     progress=None)`;
   - `built_surfaces_block(out_dir, surfaces_config, world, world_sha256, datasets, lock)`,
     where the lock is a dict or a path (M3-03's lock lands at the same time).
3. **Inputs:** `<raw_root>/swisstlm3d/2026-02/swisstlm3d_2026-02_2056_5728.gdb.zip` and its
   flat provenance (M3-03's layout). The checks run in SPEC's order:
   - the world, then the lock entry, then the inputs `computed_for`;
   - the provenance;
   - **the file's size against the provenance's `size_bytes` before hashing** (an early,
     cheap refusal, decided by design);
   - the file's SHA-256 against the lock's;
   - the read, after which (size, mtime_ns, inode) must be unchanged (a 2.88 GB file is read
     through its path, not from bytes in memory).
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
