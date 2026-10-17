# Brief: M4-02 — The surroundings step: the mountains' heights around the area
Status: OPEN

Written in the design realm; executed by one fresh builder session under
`docs/roles/BUILD.md`. Lane B of wave 1 (m4-design §2; the arc plan names the waves).

## Goal

`pipeline/mattini/surroundings.py` turns swissALTIRegio's 10 m tiles into a coarse height
grid of the mountains around the area. Later in the arc, a mesh that only casts shadows is
built from it (m4-design §7), so the sun sets behind the real horizon.

- **The grid:** a vertex every 100 m over the area's box grown by 20 km.
- **Its heights:** each vertex keeps the highest sample of its square, so a shadow keeps its
  peaks.
- **The cut:** vertices strictly inside the area are NaN; the real terrain is there.

The file is compared with design's expected SHA-256 before it is written, as the terrain's
is. The command line and the manifest come in wave 2 (brief M4-09): this brief builds the
step and the check the manifest will call, not their wiring.

## Read first, in order

1. `CLAUDE.md` (Hard Rules 2, 4, 5); `brain.md` H5, H9, H22.
2. `docs/briefs/sketches/m4-design.md` §0 (*Far mountains in Godot*), §2 (the rule), §7 (what
   reads the file).
3. `docs/SPEC.md` §8, *The terrain grid*: the vertex grid, `computed_for`, the order of the
   checks, the expected value.
4. `pipeline/mattini/terrain.py` and `surfaces.py`: the structure, the `computed_for`
   helpers, `.part` renames, `build_*` and `built_*_block`.
5. Brief M4-01's decisions 2–4 (`docs/briefs/M4-01-the-input-swissaltiregio.md`): the
   layout, the file format and the tile rule this step reads.
6. `config/surroundings.json`, `tests/shared/surroundings_fixture/`,
   `tests/shared/surroundings_vectors.json` (design data, committed with the plan; never
   edited).
7. The pinned tests: `docs/briefs/pinning/M4-02/`.

## Decisions already made

1. **The rule** (m4-design §2):
   - **The box:** the area box grown by `margin_m` on every side. The area's corners and
     `margin_m` must be multiples of `spacing_m`; otherwise the step refuses, naming the
     world config, the area and the spacing.
   - **The grid:** row r, column c is LV95 (e_min + c·s, n_max − r·s), edges included. Rows
     run north to south, columns west to east. The village: E 2'603'000–2'645'000,
     N 1'075'000–1'118'000, 421 columns × 431 rows.
   - **The height:** the largest sample whose position lies in [E − s/2, E + s/2) ×
     [N − s/2, N + s/2), minus `height_offset_m`, computed in 64-bit and rounded once to
     float32.
     - A height text parses to the correctly rounded double. Any parse that gives the same
       doubles is fine: numpy's string conversion did on all 30 million village samples.
     - At the village's 10 m samples and 100 m spacing no sample lies on a square's edge.
       The fixture's 1000 m cells put samples there, so it decides the half-open rule.
   - **The cut:** a vertex strictly inside the area box (e_min < E < e_max and
     n_min < N < n_max) is NaN, the quiet NaN **0x7FC00000** (bytes `00 00 c0 7f`). Vertices
     on the area's edge keep their height.
   - **A vertex with no sample** is refused, naming its row, column, position and
     `python -m mattini download regio`, if it keeps a height. A vertex inside the cut is
     NaN whatever its square holds (decided by design).
2. **The config** (`config/surroundings.json`, decided by design here).
   - `{"schema": 1, "areas": {<one area>: {...}}}`. The area's keys are exactly:
     - `computed_for` (as every step config);
     - `expected_columns`, `expected_rows` (positive whole numbers);
     - `expected_lv95_box` (e_max, e_min, n_max, n_min);
     - `expected_sha256`;
     - `margin_m` (a whole number of metres, 0 or more, a multiple of `spacing_m`);
     - `spacing_m` (a positive whole number of metres).
   - `load_surroundings_config(path)` and `check_surroundings_config(data, where)` refuse
     anything else, naming the file.
3. **The inputs:** brief M4-01's layout: `<raw_root>/swissaltiregio/<edition>/provenance.json`
   (the terrain's keys) and the zips it lists. The checks run in this order, each before the
   next reads anything:
   - the axes (the owner's only), the area on the lattice;
   - the world (`computed_for.world_sha256`);
   - the box, columns and rows against design's `expected_*`;
   - the lock's fit:
     - the `swissaltiregio` entry exists;
     - its collection, edition and resolution are the datasets config's;
     - its tiles are exactly those whose square meets [e_min − s/2, e_max + s/2) ×
       [n_min − s/2, n_max + s/2) (M4-01 decision 4);
     - refused naming `python -m mattini lock regio` and no other command;
   - the entry (`computed_for.inputs_sha256`, `lock.entry_sha256`);
   - provenance.json: dataset, collection, edition, resolution, and the tiles in order with
     the lock's files and SHA-256s;
   - then, tile by tile, the bytes' SHA-256 against the lock's, read from the very bytes
     checked.

   A missing download is refused naming `python -m mattini download regio`, before any
   `progress` call and before anything is created under `out_dir`.
4. **A tile is what its id says**, else the step refuses, naming the tile and
   `download regio`:
   - one member `<E km>_<N km>.xyz` and the header `x y z`;
   - every line is three fields: x and y in whole metres, each point on the tile's cell
     centres at `resolution_m` (E0 + r/2 + r·i) strictly inside its square, at most once;
   - z a finite number (`nan`, `inf`, `12.3.4` refused).
   - The lines may come in any order.
   - Points may be missing (a tile at the data's edge); the no-sample rule of decision 1
     catches a vertex left without any.
5. **The lock's fit lives in this module, in wave 1.** `lock.fit_problem` and
   `lock.shape_problem` learn swissALTIRegio only in M4-01, which runs in the same wave; until
   then they raise on the dataset. Do not import them, and do not edit `lock.py`,
   `download.py`, `datasets.py` or `__main__.py`. The tile rule is written here, the same as
   M4-01's `download.regio_tiles`. M4-09 moves the step onto `fit_problem` and keeps one home
   for the rule. Allowed imports:
   - from `terrain.py`: `world_refusal`, `inputs_refusal`, `check_computed_for`,
     `configured_area`, `OWNER_AXES`, `AREA_NAME`;
   - `download.PROVENANCE`, `lock.entry_sha256`, `world.*`.
6. **The files:**
   - `surroundings/<area>.f32` (little-endian float32, no header), then
     `surroundings/<area>.json`, each through a `.part` rename;
   - after a success, every `*.part` left in `surroundings/` is removed.
   - The description has exactly the keys {area, columns, cut_box (the area box), file,
     format `f32-le`, lv95_box (the surroundings box), rows, sha256, source {attribution,
     collection, dataset, edition, entry_sha256}, spacing_m (a float), world_sha256}, written
     as the terrain's: sorted, 2-space indent, UTF-8, LF.
   - The heights' SHA-256 is compared with `expected_sha256` before anything is written
     (lesson 38); a difference names both values and "nothing was written".
7. **The API** (the pinned tests use these):
   - `SurroundingsError(ValueError)`;
   - `load_surroundings_config`, `check_surroundings_config`;
   - `build_surroundings(world, datasets, lock, surroundings_config, raw_root, out_dir, *,
     progress=None) -> dict`;
   - `built_surroundings_block(out_dir, surroundings_config, world, world_sha256, datasets,
     lock) -> dict | None`, where `lock` is a dict or the lock file's path.
     - It gives None when nothing is built.
     - A changed world or entry is refused naming design's step.
     - Anything else that no longer holds is refused naming `python -m mattini surroundings`,
       the command M4-09 adds.
8. **Design's values** (`config/surroundings.json`, the village, computed two independent
   ways with identical bytes: numpy, and plain Python in whole centimetres):
   - `expected_sha256` `d317a3588f67dcad64350c4b1a471fce016128b17688d6c069fee6f18690f311`;
   - 725'804 bytes, 551 NaN (19 × 29 interior vertices), heights 882.19 to 4634.17 m (Monte
     Rosa);
   - `computed_for`: inputs `9afdf81d…` (M4-01's measured entry), world `d2607d13…`.
   - Design's rehearsal throwaway reproduced it from a real `download regio` in 62.6 s,
     504 MiB peak. Its per-line Python validation dominates; design's numpy computation alone
     took 10.2 s.
9. **The shared fixture** (`tests/shared/surroundings_fixture/`, design's, two independent
   implementations, identical bytes):
   - a world with origin E 2'618'250 / N 1'101'750, `height_offset_m` 1250.25, and an area of
     9 × 12 km;
   - nine synthetic 10 km tiles at a 1000 m cell, in `source.json` (no `.zip` may be
     committed). The pinned helper `synthetic_regio.py` zips them; the lock pins the stored
     zips, so the fixture's lock and `computed_for` are the same on every machine;
   - margin and spacing 3000 m: a grid of 6 × 7 with 6 NaN;
   - `generated/surroundings/fixture.{f32,json}` exactly as the step writes them. The game's
     reader (M4-07) reads this folder, so a flip, swapped axes, a missing or wider cut, a
     closed square, a cell-centre vertex and a mean each change the bytes (pinned).
   - `tests/shared/surroundings_vectors.json` names 14 vertices: their LV95 and local
     positions, heights or NaN, and highest samples.
10. **The area's name** stays out of `pipeline/mattini/` (M2-01's census).

## Scope — files you may touch

`pipeline/mattini/surroundings.py` (new) · `pipeline/tests/`: the pinned copies
(`synthetic_regio.py`, `test_m4_02_surroundings_config.py`,
`test_m4_02_surroundings_fixture.py`, `test_m4_02_surroundings_step.py`) and your own new
`test_m4_02_*.py`. Read-only: everything else, `config/surroundings.json` and the fixture
included.

## Depends on

None at build time: every test uses the fixture and passes the lock as a dict, never the
committed lock (which gains the `swissaltiregio` entry only in M4-01).

The real-data run needs M4-01's `lock regio` and `download regio`. The orchestrator's
integration of wave 1 covers it once both have landed:
- `download regio` into a scratch root;
- then `build_surroundings` with the committed configs and lock, through a driver script
  outside the repository (no CLI until M4-09);
- the step's own comparison with `expected_sha256` is the check (lesson 38). Record the
  time, peak memory and SHA-256 in the integration's notes.

M4-09's gate repeats it through `python -m mattini surroundings`.

## Done when (gates)

- [ ] The pinned copies are in place (`cp -r docs/briefs/pinning/M4-02/. .`) and stay
      byte-identical (`cmp`).
      - does NOT prove: that they are the right tests.
- [ ] Mutations, each failing a named pinned test, recorded with the harm each reproduces:
      - the square closed on the east, and on the north;
      - rows south to north;
      - no cut, and a cut that takes the area's edge;
      - another NaN payload;
      - no height offset;
      - the last sample for the largest;
      - written before the expected check;
      - no `.part` rename, and leftover parts kept;
      - a missing sample, a duplicate, and an off-lattice point accepted;
      - the lock's fit skipped;
      - the world checked after the lock;
      - a progress line before provenance.json;
      - the tiles without the half-spacing border.

      Design's throwaway failed a pinned test for each.
      - does NOT prove: the game's reading (M4-07) or that the shadows land right (M4-07,
        M4-10, the owner's eyes).
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that the real village gives design's heights (the integration run
        does), or anything drawn.

## Forbidden

- Changing the rule, design's values, the fixture, the vectors or a pinned file.
- Editing `lock.py`, `download.py`, `datasets.py`, `__main__.py`, `manifest.py` (lane A and
  wave 2 own them); any new dependency.
- Command-line or manifest wiring (M4-09); the game (M4-07).

## Findings (executor writes)
