# Review M0 R1 — lens `coordinates` (Tier 1)

- **Lens:** `coordinates`: `config/world.json`, both LV95 ↔ local transforms, the manifest,
  the shared vectors, the pipeline's determinism, the seams M0-02↔M0-03 and M0-02↔M0-04.
- **Range:** `git diff 366b0b5..a8cfa63 -- . ':!game/addons' ':!pipeline/uv.lock'`, plus
  `config/world.json` and `tests/shared/world_vectors.json`.
- **Head reviewed:** `a8cfa63`. `main` was at `297bce5` when this was written; the only
  change since `a8cfa63` is `docs/ROADMAP.md`.
- **Date:** 2026-09-24.
- **How:** every mutation and every Godot run was done in a separate worktree at `a8cfa63`
  in the session's scratch directory. Godot's `user://` was pointed at a scratch folder
  (`XDG_DATA_HOME`) so the GUT runs could not collide with the other lens's. One build ran
  at a time. Each mutation was saved as a diff, run, then undone with `git apply -R`; the
  tree was clean after each. Baseline in that worktree: `tools/gate.sh` exit 0, 209 pytest
  passed (2 network tests deselected), 13 GUT tests passed.

**Result:** no P0, no P1. Five P2s and four P3s. The transforms are right on both sides and
agree bit for bit on the shared vectors. The gaps are in what the tests can see:
- determinism is only checked on one machine within one run;
- the origin census misses some file types and some ways of writing the number;
- the game's inverse transform is untested for 8 of the 24 rotations;
- a Windows (CRLF) checkout changes the manifest bytes;
- the download folder can hold tiles that `provenance.json` does not list.

## Findings

### M0-R1-C-01 · P2 · The determinism tests cannot see a field that changes by day or by machine

- **Where:** `pipeline/mattini/manifest.py:218-222` and `pipeline/mattini/download.py:196-205`
  (the writers). `pipeline/tests/test_manifest.py:143-146`,
  `pipeline/tests/test_manifest_output.py:79-98`,
  `pipeline/tests/test_download_provenance.py:104-143` (the tests).
- **Claim:** every Hard Rule 5 test compares two writes made on the same machine in the same
  run. The one content check, `test_download_provenance.py:118`, looks only for a date
  followed by a time. So any field that stays the same within a run passes pytest and the
  full gate. Examples: a date without a time, the host name, the user name, the Python or
  OS version. Nothing pins the key sets of the manifest or of `provenance.json`.
- **Proof:** two mutations, each run through the full `tools/gate.sh`.
  - E1 added `"generated_on": date.today().isoformat()` and
    `"generated_by": platform.node()` to `build_manifest`. The gate exited 0 (209 pytest,
    13 GUT). The manifest it wrote contained `"generated_by": "vm"` and
    `"generated_on": "2026-09-24"`.
  - E2 added the same two fields to `_write_provenance`. The gate exited 0.
  - For comparison, the builders' full-timestamp mutations still fail: M0-02 (c) fails 3
    tests and M0-04 (d) fails 4, the same names as in the Findings.
- **Harm:** tomorrow's rebuild, or the owner's PC, writes different manifest or provenance
  bytes for the same config, and the gate stays green. This is the harm Hard Rule 5 names
  ("generated assets nobody can reproduce"). M1 will extend the manifest (chunks) and
  inherits the same blind spot.
- **Fix:** pin the exact key sets:
  - the manifest's top level is `{"schema", "world", "world_sha256"}`;
  - `provenance.json`'s top level and each tile entry match the fields in M0-04 Findings 8.

  Better still, compare against golden bytes for the committed config and the fake server.
  This fix is unambiguous and fits the own-test scopes of M0-02 and M0-04.

### M0-R1-C-02 · P2 · The Hard Rule 4 census misses some file types and some spellings

- **Where:** `pipeline/tests/test_world.py:22` (`CODE_SUFFIXES`), `:101` (the pattern) and
  `:104` (the three folders it scans).
- **Claim:**
  - It scans only files with the suffixes `.py .gd .tscn .tres .cfg .json .sh`, and only
    under `pipeline/mattini/`, `game/` and `tools/`.
  - So `game/project.godot`, any `.gdshader`, and any file in `pipeline/` outside
    `mattini/` are never read.
  - The pattern also misses literal spellings that are not "an origin computed from other
    numbers": `2.623e6`, `1096e3`, and the origin in kilometres (`Vector2i(2623, 1096)`).
  - The brief's own "does NOT prove" line covers only the computed case.
- **Proof:** mutation G2 added five second homes for the origin:
  - `[mattini] world/origin_e=2623000.0` in `game/project.godot`;
  - `const float ORIGIN_E = 2623000.0;` in a new `game/shaders/terrain.gdshader`;
  - `const ORIGIN_KM := Vector2i(2623, 1096)`, `const ORIGIN_E := 2.623e6` and
    `const ORIGIN_N := 1096e3` in a new `game/scripts/world/chunk_grid.gd`;
  - `ORIGIN_E = 2.623e6` and `ORIGIN_N = 1_096e3` at the end of
    `pipeline/mattini/download.py`;
  - `ORIGIN = (2623000.0, 1096000.0)` in a new `pipeline/scripts/place.py`.

  Result: `tools/gate.sh` exit 0, with `test_origin_numbers_live_only_in_config` passing
  among the 209 pytest tests and 13 GUT tests passing. For contrast, the builder's
  mutation (d), `ORIGIN_E = 2623000.0` in `world.py`, still fails that test (re-run: 1
  failed).
- **Harm:** a second origin in a shader, in the project settings or in chunk-grid code
  drifts away from `config/world.json` without any test noticing, and the world ends up
  silently shifted. That is the harm Hard Rule 4 names. M1 (terrain shaders, Terrain3D
  settings, chunks on the 1 km grid) is the arc most likely to write exactly these files.
- **Fix:**
  - Scan every file from `git ls-files` except `config/`, `tests/`, `docs/`,
    `game/addons/` and `pipeline/uv.lock`, whatever its suffix.
  - Add the e-notation spellings to the pattern.

  Both parts are unambiguous and fit M0-02's own-test scope (`pipeline/tests/test_world_*.py`).
  Catching the kilometre spelling (a `2623 … 1096` pair) is design's call. A census stays
  text-only (lesson 5).

### M0-R1-C-03 · P2 · The game's `to_lv95` is untested for 8 of the 24 rotations, while the pipeline tests all 24

- **Where:** `game/scripts/world/world_config.gd:61-67`. The only rotation test that reaches
  `to_lv95` is on the pipeline side (`pipeline/tests/test_world_rotations.py:81-82`). The
  game's 48-mapping test (`game/tests/test_world_config_refusals.gd:83-111`) calls only
  `to_local`. The game's other `to_lv95` tests use the owner's mapping, whose permutation is
  its own inverse (it swaps n and h).
- **Claim:** a `to_lv95` that applies the permutation where it should apply the inverse gives
  the right answer for the owner's mapping and every self-inverse mapping. It gives the wrong
  answer for the 8 cyclic rotations, and no game test notices.
- **Proof:**
  - Mutation H4 replaced `source[_source_index[axis]] = _sign[axis] * p[axis]` with
    `source[axis] = _sign[_source_index[axis]] * p[_source_index[axis]]`. GUT: exit 0,
    13/13 tests passed. The full `tools/gate.sh`: exit 0.
  - Under H4, with axes `x=+n, y=+h, z=+e`, a Godot probe turned Kirchplatz 1
    (2623825.25, 1096489.75, 1600) into `to_local` = (489.75, 1600, 825.25) and back into
    `to_lv95` = (2624600.000, 1096825.250, 489.750). That is about 1.1 km off, and the
    height is wrong.
  - The same mutation on the pipeline side (`source[axis] = self.mapping[index][0] *
    float(values[index])`) fails 8 tests: `test_rotations_accepted_mirrors_refused` for
    `[+n,+h,+e]`, `[+n,-h,-e]`, `[-n,+h,-e]`, `[-n,-h,+e]`, `[+h,+e,+n]`, `[+h,-e,-n]`,
    `[-h,+e,-n]` and `[-h,-e,+n]`.
- **Harm:** none with today's mapping. If design ever changes `axes` to a cyclic rotation,
  the game's world→LV95 answers (a coordinate readout, placing something at an address)
  are up to kilometres off, while the pipeline's are right. The two halves split silently.
- **Fix:** in the game's rotation loop, also assert
  `to_lv95(to_local(point)) ≈ point` for each accepted rotation, as the pipeline test does.
  Unambiguous, and inside M0-03's test scope.

### M0-R1-C-04 · P2 · A CRLF checkout changes `world_sha256`, and so the manifest bytes (extends: the board's `.gitattributes` follow-up)

- **Where:** `pipeline/mattini/manifest.py:221` hashes the raw bytes of
  `config/world.json`. The repository has no `.gitattributes`.
  `pipeline/tests/test_manifest_output.py:3` claims "the same config gives the same bytes on
  every platform".
- **Claim:** with `core.autocrlf=true`, `config/world.json` is checked out with CRLF line
  endings. That is Git for Windows' default installer choice; I have not measured it on the
  owner's PC. With CRLF endings the file's SHA-256 changes, and so does the manifest.
  Every test still passes, because each side hashes the same local file. The board's
  follow-up names only `*.sh`. The same mechanism reaches the coordinate data.
- **Proof:**
  - Cloned the repository with `git -c core.autocrlf=true clone`, then checked out
    `a8cfa63`. `config/world.json` there has 25 `\r` bytes. Its SHA-256 is `fbc5b597…2388`;
    the LF checkout's is `d2607d13…509b`.
  - `python -m mattini manifest` in each checkout: the two manifests differ only on line 28,
    the `world_sha256` line (whole-file SHA-256 `afee8296…` against `a1d1bfe5…`).
  - The CRLF checkout still passes: pytest 209, Godot import 0 error lines, GUT 13/13.
  - `tools/gate.sh` itself cannot run there
    (`line 13: set: pipefail: invalid option name`; that part is the known `.sh` item).
- **Harm:** the owner's Windows PC and Linux write different manifest bytes from the same
  commit, against Hard Rule 5 and against the claim in that docstring. No test fails, and
  nothing compares manifests across machines yet. Anything that later records
  `world_sha256` (M1 chunks, a release record) inherits the split.
- **Fix:** a `.gitattributes` with `* text=auto eol=lf`, or at least `config/** text eol=lf`
  and `tests/shared/** text eol=lf`. Fold it into the board's `.sh` item. The fix itself is
  unambiguous, but no M0 brief has `.gitattributes` in its Scope, so design decides where it
  goes. Hashing a canonical form instead would change SPEC §6 ("SHA-256 of the file's
  bytes"), which is also design's call.

### M0-R1-C-05 · P2 · The download folder can hold tiles that `provenance.json` does not list

- **Where:** `pipeline/mattini/download.py:86-107` looks only at the tiles on the current
  list. `:196-205`: `provenance.json` records neither the village box nor the world config's
  SHA-256.
- **Claim:** when the village box shrinks or moves, or `resolution_m` changes, the old
  files stay in `data/raw/swissalti3d/<edition>/` under their final, verified-looking names.
  `provenance.json` lists only the new set, and the command's message ("N tiles verified,
  M fetches") says nothing about the others. The edition gets its own folder; a change of
  box or resolution does not.
- **Proof** (the fake STAC server from `test_download_provenance.py`, real
  `download_terrain`):
  - Six-tile run, then the box shrunk to `e_max=2624000, n_max=1096000`: provenance lists
    `['2623-1095']`, and 6 `.tif` files are still on disk.
  - Six-tile run at 0.5 m, then `resolution_m=2.0`: provenance lists 6 files, all `2` m,
    and 12 `.tif` files are on disk at resolutions `['0.5', '2']`.
- **Harm:** an M1 terrain step that lists the folder rather than reading `provenance.json`
  builds terrain outside the configured village, or mixes 0.5 m and 2 m tiles. Two
  machines with different download histories hold different input folders for the same
  config, against brief M0-04's goal ("every machine … starts from byte-identical terrain
  inputs"). The village resolution (0.5, 1 or 2 m) is an open M1 decision, so this trigger
  is plausible. The finding becomes P1 if M1 reads the folder.
- **Fix:** design's call; it is not unambiguous. One option: M1's brief makes
  `provenance.json` the only tile list, pinned by a test. The other: `download_terrain`
  removes or reports `.tif` files that are not in the current list, and records the box it
  served.

### M0-R1-C-06 · P3 · The game's random round-trip test never exercises the 32-bit narrowing it describes

- **Where:** `game/tests/test_world_config_transforms.gd:118-131`. M0-03 Findings 2 says
  "200 random round trips within 2 mm at up to 20 km".
- **Claim:** `RandomNumberGenerator.randf_range` returns 32-bit values, so all 200 offsets
  fit a `Vector3` exactly. The round trip is then exact, and the 2 mm tolerance and the
  comment ("32-bit Vector3 in between: about 2 mm at 20 km") are never tested.
- **Proof:** a Godot probe replayed the test's seed and ranges:
  - worst round-trip error `0.000000000000 m`;
  - 200 of 200 offsets exact in 32 bits.

  The same round trip with 64-bit offsets (millimetre grid plus a sub-millimetre fraction)
  has a worst error of `0.000927 m`. The 32-bit-origin mutation (M0-03 e, re-run as H1) is
  still caught, by the pinned trap vector and by this test through its absolute input.
- **Harm:** a reader believes the game side measures its narrowing budget. It does not; only
  the pinned vectors do.
- **Fix:** build the offsets in 64-bit, for example
  `rng.randi_range(-20000000, 20000000) / 1000.0 + rng.randf() * 0.001`. Unambiguous, and
  in M0-03's test scope.

### M0-R1-C-07 · P3 · A `WorldConfig` built with `new()` maps every point to the origin, with no error

- **Where:** `game/scripts/world/world_config.gd:20-25` (the zero defaults) and `:50-67`.
- **Claim:** `WorldConfig.new()` (instead of `from_manifest`) leaves the signs at 0 and the
  origin at 0. `to_local` then returns `(0, 0, 0)` for every input and `to_lv95` returns
  `[0, 0, 0]`. Nothing is pushed as an error. The result looks plausible: the origin
  (lesson 1).
- **Proof:** Godot probe output:
  `WorldConfig.new().to_local(2623825.13, 1096489.77, 1606.37) = (0.0, 0.0, 0.0);`
  `to_lv95(Vector3(825,1600,-489)) = [0.0, 0.0, 0.0]`. No `ERROR` line.
- **Harm:** none today, since nothing in the game uses `WorldConfig` yet. An M1 script that
  builds one by hand would put everything at the church square without a word.
- **Fix:** design's call. One option: a `_valid` flag set by `_read_manifest`, with a
  `push_error` in `to_local`/`to_lv95` while it is unset. The other: NaN defaults, which are
  visibly wrong rather than plausibly wrong.

### M0-R1-C-08 · P3 · An empty manifest is refused with the reason "(OK)"

- **Where:** `game/scripts/world/world_config.gd:31-35`.
- **Claim:** a manifest file that exists but is empty is refused, which is correct. The
  message reads `cannot read the manifest (OK)`, because the open succeeded. The refusal is
  visible; the reason is wrong.
- **Proof:** Godot probe output:
  `ERROR: WorldConfig: …/probe_empty.json: cannot read the manifest (OK)`, and
  `from_manifest` returned `<null>`.
- **Harm:** a truncated manifest (for example, a pipeline run that was interrupted) is
  reported as unreadable, which sends the owner looking for a missing file.
- **Fix:** when `FileAccess.get_open_error() == OK`, report "the manifest is empty".
  Unambiguous, and inside M0-03's scope.

### M0-R1-C-09 · P3 · The "Matterhorn summit name point" vector is rounded to the metre

- **Where:** `tests/shared/world_vectors.json:11` (design data).
- **Claim:** the vector says E 2617049.0. swisstopo's gazetteer point for the Matterhorn
  ("Alpiner Gipfel") is E 2617048.75, N 1091673.0. The northing matches; the easting is
  rounded by 0.25 m. The two address vectors match swisstopo exactly (see the clean list).
- **Proof:** `api3.geo.admin.ch/rest/services/api/SearchServer?searchText=Matterhorn&type=locations&origins=gazetteer&sr=2056`
  returned `Matterhorn Mont Cervin|Monte Cervino E= 2617048.75 N= 1091673.0`.
- **Harm:** none to the transforms, since the value is a test input. The label claims a
  measured point that has been rounded (Hard Rule 2, clarity only).
- **Fix:** design's call. Either use 2617048.75 (the local x becomes −5951.25) or add
  "(rounded)" to the name.

## Checked and clean

1. **The mapping is a rotation, and it faces the right way.**
   - `x=+e, y=+h, z=−n` has determinant +1, and east × north = up after mapping.
   - The Matterhorn, which is south-west of the village in reality, lands at x = −5951,
     z = +4327: west, and south (+z = back, so −z = north = forward, SPEC §6).
2. **The shared vectors are self-consistent.** Every `local` value equals SPEC §6's formula
   applied to its `lv95` value (recomputed).
   - Kirchplatz 1 (2623825.25, 1096489.75) and Bahnhofplatz 1 (2623923.5, 1096921.5) match
     swisstopo's address search exactly.
   - The church square lies in tile 2623-1096, as SPEC §6 says.
3. **The two halves agree bit for bit on all 8 vectors.** A Godot probe printed each
   `to_local` component to 10 decimals. Each equals Python's 64-bit result narrowed to
   32 bits; for the trap point both give 825.1300048828, 1606.3699951172 and
   −489.7699890137. Godot's JSON parser reads the origin and every vector number to the
   same doubles as Python (2623825.13 is 2623825.1299999999 on both sides).
4. **The origin is subtracted in 64-bit on both sides:** `world.py:45` and
   `world_config.gd:52`. Mutation H1 (a `Vector3` subtraction, M0-03 e) fails the pinned
   `test_to_local_matches_shared_vectors`: the trap point's x = 825.25 (want 825.13) and
   z = −489.75 (want −489.77). It also fails `test_round_trips_stay_within_a_millimetre`.
5. **The builders' load-bearing mutation proofs were re-run, and each fails what the Findings
   say.**
   - M0-02: (a) signs ignored, 39 failed. (b) determinant check removed, 26 failed.
     (c) full timestamp, 3 failed. (d) origin in `world.py`, 1 failed.
   - M0-03: (e) 32-bit subtraction, 2 GUT tests. (f) config changed without regenerating
     the manifest: GUT alone exits 1 with `manifest is current`, and `config/world.json`
     afterwards is `d2607d13…` again.
   - M0-04: (d) time in provenance, 4 failed.
6. **New mutations, each caught.**
   - Game determinant check removed: 1 test, 48 failed asserts (24 mirrors × 2).
   - Game `to_local` ignores the z sign: 5 tests.
   - Game `to_lv95` ignores signs: 3 tests (n wrong: 1095510.25 against 1096489.75).
   - The tile range includes the tile past a km line (`floor(max)+1`): 15 failed, the pinned
     six-tile test among them.
7. **Hard Rule 4 in production code.** `git grep` for every spelling of the origin numbers
   (`2[' _]?623`, `1[' _]?096`, `2.623`, `1.096`) finds only `config/world.json` and test
   oracles. No `.gd`, `.py`, `.sh`, `.tscn` or `project.godot` holds an origin or offset.
   The game learns the origin only through `WorldConfig.from_manifest(path)`.
8. **Seam M0-02 ↔ M0-03.**
   - The pipeline writes `game/assets/generated/manifest.json` and the game tests read
     `res://assets/generated/manifest.json`: the same file.
   - Both sides read `origin_lv95`, `height_offset_m` and `axes` with the same meaning: each
     game axis = sign × the named source axis. That is checked on both sides by unit vectors
     for all 48 mappings.
   - The manifest's world block equals the parsed config (pinned `test_world_block_is_config_verbatim`).
   - Staleness is caught by the pinned GUT SHA-256 test.
   - Duplicate keys cannot reach the game, because the manifest is re-serialised from a
     Python dict.
9. **Seam M0-02 ↔ M0-04.**
   - `village_tiles` uses floor(min) and ceil(max) on the LV95 box and never the origin,
     which gives exactly the six tiles.
   - A max edge on a kilometre line is exclusive: `test_tiles_follow_the_village_box…` uses
     `n_max=1096000.0` exactly and `e_max=2624000.5`.
   - Dividing a whole multiple of 1000 by 1000 is exact in 64-bit floats.
10. **The mechanics of manifest and provenance bytes.**
    - Sorted keys, 2-space indent, `\n` written by `write_bytes`, UTF-8 with
      `ensure_ascii=False`.
    - Floats are written by Python's shortest round-trip `repr`, which does not depend on
      the platform.
    - No absolute paths.
    - The CLI output does not depend on the working directory.
    - Provenance is replaced atomically through a `.part` file and holds names, not paths.
11. **Refusals are visible on both sides.**
    - The pipeline raises `WorldConfigError` naming the file; the CLI exits 1 with the path
      on stderr.
    - The game calls `push_error` with the path and returns null for 48 mappings, 15
      malformed manifests, a missing manifest and an infinite offset (the builders' tests,
      green at baseline).
12. **Design data is untouched.** The pinned copies of `test_world.py`, `test_manifest.py`,
    `test_world_config.gd` and `test_download.py` are byte-identical to
    `docs/briefs/pinning/`. The arc did not change `config/` or `tests/shared/`.

## Does NOT prove

Nothing here shows:

- **Rendering.** That anything renders, or renders in the right place: there is no GPU.
- **M1 rasters.** That M1's rasters map north-up rows to +z (south) without a flip: there is
  no consumer yet.
- **Windows.** How the owner's Windows PC behaves: CRLF was simulated on Linux with
  `core.autocrlf=true`, and the owner's actual git settings were not read.
- **Narrowing by callers.** That future callers pass 64-bit values: both `to_local`
  functions accept a value that is already narrowed, such as a numpy `float32` or a
  `Vector3` component, and cannot detect the loss.
- **Godot's JSON parser in general.** It was compared on only the origin and the 8 vectors.
- **The census after its fix.** Even with C-02's fix, a census proves text only.
- **Real swisstopo.** The network path to swisstopo was not re-run.
- **An exported game.** That it contains the generated manifest: no export exists.
- **Every mutation.** The mutations are a sample, not a proof that no other mutation
  survives.
- **Known items.** The two known items on the board's "Decisions for the close" were not
  re-filed: the `height_offset_m` reading, and swisstopo republishing within an edition.
