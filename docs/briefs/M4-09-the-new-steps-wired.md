# Brief: M4-09 — The new steps on the command line and in the manifest
Status: OPEN

Written in the design realm; executed by one fresh builder session under
`docs/roles/BUILD.md`. Lane I of wave 2, after wave 1 has landed and been integrated (M4-01,
M4-02, M4-03; m4-design §2, §3, §4).

## Goal

The steps of wave 1 become commands, and their outputs and the sun's place reach the game
through the manifest.

- `python -m mattini surroundings` and `shadows` build their outputs, as `trees` does;
  `python -m mattini sky` writes the sun's place for the area from `config/sky.json`.
- The manifest's top level becomes exactly {buildings, photo, roofs, schema, shadows, sky,
  surfaces, surroundings, terrain, trees, world, world_sha256}: each new block checked, null
  when its step has not run.
- The swissALTIRegio tile rule and the reader of `config/surroundings.json` each get one
  home: `lock.fit_problem` (through `download.regio_tiles`) and
  `surroundings.load_surroundings_config`.

Measured with design's throwaway on the real village: every step from the command line
writes design's values, and the manifest is 327'265 bytes, SHA-256
`a0e2ec92b28da50bf24ab3982cd6058ba559b9c0f2ad93f32cc76849e77c517e`.

## Read first, in order

1. `CLAUDE.md` (Hard Rules 2, 4, 5); `brain.md` H9, H18, H22, H24, H27.
2. `docs/briefs/sketches/m4-design.md` §2, §3, §4, §9; `docs/SPEC.md` §5 (the lock), §8 (the
   manifest, the expected outputs and their check order).
3. Brief M3-13 and its Findings (the same wiring for the M3 steps: `lock.shape_problem`, the
   `.part` manifest, the check order in `manifest.py`).
4. Briefs M4-01, M4-02, M4-03 and their Findings: each names what M4-09 does (M4-01 decision
   4, the reader; M4-02 decisions 5 and 7, the fit and the command; M4-03 decision 3, the
   API). A name a wave-1 builder chose differently is recorded there; this brief's names
   are the ones its pinned tests call.
5. `pipeline/mattini/__main__.py`, `manifest.py`, `lock.py`, `download.py`,
   `surroundings.py`, `shadows.py`.
6. `config/sky.json` and its pinned test `test_m4_09_sky_config.py` (committed with M4-03).
7. The pinned tests and fixture data: `docs/briefs/pinning/M4-09/`.

## Decisions already made

1. **The commands** `surroundings`, `shadows` and `sky`.
   - `surroundings` and `shadows` take `--raw` and `--out`, as `trees` does. Each loads
     `config/world.json`, `datasets.json`, `datasets.lock.json` and its own config
     (`surroundings.load_surroundings_config()`, `shadows.load_shadows_config()`), calls
     `<module>.build_<step>(world, datasets, lock, config, raw_root, out_dir,
     progress=…)` through the module, then writes the manifest and prints its path.
   - `sky` takes `--out` only (it reads no download): `sky.build_sky(load_world(),
     sky.load_sky_config(), out_dir)` through the module, then the manifest.
   - A refusal is one `mattini: error: …` line and exit 1, no traceback: `__main__` catches
     `SurroundingsError`, `ShadowsError` and `SkyError` beside the others. Ctrl-C is M3-03's
     one handler.
   - The help lists the commands in pipeline order: lock, download, terrain, buildings,
     photo, roofs, surfaces, trees, surroundings, shadows, sky, manifest.
2. **The sky is a step** (design's decision; m4-design §4 left it open). `config/sky.json`
   is design data with `computed_for` {world_sha256}, like every expected value; the block
   follows M3-13's rule for every block: null until its step has run in the folder.
   - Why not computed by `manifest` alone: the block would then exist for every world.
     Design's rehearsal measured both variants. Always computed: 150 tests failed beyond the
     key-set edits below (every fixture's world differs from the one `config/sky.json` was
     computed for). Computed only
     when the world has the config's area: 42 tests in 8 files still failed, each building a
     terrain for a world of its own named `village` (test_terrain_manifest_source.py 24,
     test_m3_13_manifest_checks.py 5, test_computed_for_terrain.py 4,
     test_terrain_expected_spacing.py 4, test_lock_fit.py 2, and one each in
     test_download_area.py, test_manifest_output.py, test_terrain_cli.py), refused for the
     sky where nothing about the sky was under test; and that variant writes null for a world
     whose area was renamed. A step keeps M3-13's one rule for every block.
   - `pipeline/mattini/sky.py`: `SkyError(ValueError)`, `SKY_CONFIG_PATH`,
     `load_sky_config(path)`, `check_sky_config(data, where)` (the exact shape of
     `test_m4_09_sky_config.py`, the three values floats, finite, |lat| ≤ 90, |lon| ≤ 180,
     |true_to_grid| ≤ 10), `build_sky(world, sky_config, out_dir, *, progress=None)` and
     `built_sky_block(out_dir, sky_config, world, world_sha256)`.
   - The checks, in order: the config; `computed_for.world_sha256` against the world config's
     bytes (`terrain.world_refusal`: design's step, naming config/sky.json); the area in the
     world config. Then `sky/<area>.json` through a `.part` rename: exactly {area,
     latitude_deg, longitude_deg, true_to_grid_deg, world_sha256}, the config's values
     verbatim, written as the other descriptions (`indent=2, sort_keys=True,
     ensure_ascii=False`, an LF).
   - `built_sky_block`: None when `sky/<area>.json` is absent; else the same checks, then the
     description must be exactly that block (keys, values, JSON types), or it is refused
     naming `python -m mattini sky`.
3. **`write_manifest`.**
   - The top level is exactly the twelve keys of the Goal; schema stays 1; serialised and
     written as today (M3-13: sorted, indent 2, LF, through `manifest.json.part`).
   - New keyword arguments, beside the others and passed through by `write_manifest`:
     `surroundings_config_path`, `shadows_config_path`, `sky_config_path`.
   - Every step config is loaded and checked even when its step has not run (the three new
     ones too). Areas: each new block from its own config's one area.
4. **The check order for a built `surroundings` or `shadows` block, in `manifest.py`** (M3-13's
   `_Step`, uniform):
   1. `computed_for.world_sha256` against the world (design's step, naming the step's config);
   2. the lock's fit through `lock.fit_problem`: `swissaltiregio` for the surroundings (with
      `surroundings=` the surroundings config given), `swisssurface3d` for the shadows,
      naming `python -m mattini lock regio` or `lock surface` and no other command;
   3. `computed_for.inputs_sha256` against `lock.entry_sha256` of that entry (design's step);
   4. the step's `built_<step>_block`.

   Refusals use the step's error class. The sky block has no lock: world, area, block
   (decision 2).
5. **One home for the tile rule** (M4-01's decision on the duplication, M4-02 decision 5):
   - `lock.fit_problem(lock, datasets, world, area, dataset, *, surroundings=None)`. For
     `swissaltiregio` the tiles are `download.regio_tiles(world, area, margin_m=…,
     spacing_m=…)`, looked up through the module at call time, with the area's `margin_m`
     and `spacing_m` from the `surroundings` config it is given; without one it raises a
     TypeError (a caller's bug, not a refusal). Every other dataset ignores the keyword.
   - `surroundings.py` keeps no tile rule: its fit check becomes `fit_problem`, then
     `lock.shape_problem` (as M3-13's steps), raised as `SurroundingsError` with
     fit_problem's text as the whole refusal; a `DownloadError` from fit_problem (a
     datasets config without the dataset) becomes a `SurroundingsError` with its text. The
     tile reader's own 10 km square check stays (it reads `download.REGIO_TILE_M` or its
     equivalent: the tile's size, not which tiles an area needs).
   - If M4-01 landed `fit_problem` reading `config/surroundings.json` itself, or with other
     keyword names, change it to this decision: the manifest checks the surroundings
     fixture's lock against its own config (area `fixture`), which the committed file does
     not hold.
6. **One reader of `config/surroundings.json`**: `surroundings.load_surroundings_config`
   (M4-01 decision 4: "M4-09 may move the reader onto it"; it moves). M4-01's small reader in
   `download.py` is deleted; `lock regio` (`lock.regio_entry` or M4-01's name) and `download
   regio` (`download.download_regio`) take the surroundings config as an argument, which
   `__main__` loads through the module. Their texts and behaviour stay M4-01's.
7. **The fixtures' manifests** (`cp -r docs/briefs/pinning/M4-09/. .`), design's pinned
   copies, each made two ways (a text edit, and design's throwaway `write_manifest`;
   identical):
   - the seven M2/M3 fixtures' `generated/manifest.json` (terrain_fixture, terrain_fixture_nw,
     buildings_fixture, photo_fixture, roofs_fixture, surfaces_fixture, trees_fixture): the
     M3-13 file plus `"shadows": null`, `"sky": null`, `"surroundings": null`;
   - new: `tests/shared/surroundings_fixture/` and `shadows_fixture/` gain `sky.json` (their
     world's centre, computed with pyproj 3.8.0 / PROJ 9.8.1 exactly as `config/sky.json` was:
     design's script reproduced the committed file byte for byte), `generated/sky/fixture.json`
     and `generated/manifest.json` (the step's block and the sky block; the game's readers of
     M4-06, M4-07 and M4-10 can read them from the manifest).
8. **The real run's manifest is design's value.** Every block of the real manifest is a
   description whose values design pinned (config/*.json, compared by each step before it
   writes), so its bytes are determined: 327'265 bytes,
   `a0e2ec92b28da50bf24ab3982cd6058ba559b9c0f2ad93f32cc76849e77c517e` (design's throwaway,
   two runs into two fresh folders, every output byte-identical). A second way: the same
   manifest with its `shadows`, `sky` and `surroundings` keys removed and serialised the
   same way is M3's `3ca0445c…` (324'359 bytes), byte for byte.
   - The builder measures it on the real village (gate 2), records it in Findings and writes
     it into `docs/RELEASE.md` §C's line, replacing M3's pair in the size test, the
     `sha256sum` line and the words "(M3: 324'359 bytes, `3ca0445c…`)" by "(M4: 327'265
     bytes, `a0e2ec92…`)".
   - Design's per-step values are the oracle: a different manifest with every step at exit
     0 is a BLOCKED question (which block differs, by `diff` of the two manifests), never a
     new value adopted.
9. **Known and accepted.**
   - `tools/export.sh` is not changed here: its step 2 and the startup lines learn the new
     blocks with the game's readers (M4-10). The new files are small and ship in
     `mattini.pck`; step 4c's rules accept them (measured: `surroundings/village.f32`
     725'804 B, `shadows/village.png` 854'622 B, each under its 10 MiB limit; the
     `.png.import` is excluded from 4c as the surfaces' is).
   - `shadows` before `download surface` names `download surface`; `surroundings` before
     `download regio` names `download regio` (the steps' own refusals).
   - `test_manifest_m3.py` and `test_refusals_m3.py` are M3-13's live copies of pinned tests
     (WORKFLOW §Brief lifecycle: a DONE brief's live copies may evolve): this brief edits them.
10. **Design's rehearsal** (2026-10-17, a scratch clone of this plan's head with throwaway
    wave-1 implementations of M4-01, M4-02 and M4-03 that pass their pins, then a throwaway
    M4-09, never committed):
    - the pins of M4-01, M4-02, M4-03 and M4-09 in place: the standard gate
      (`tools/gate.sh`, exit 0, `== gate: all steps passed`): pytest 2585 passed, `ruff check`
      and `ruff format --check` green; GUT 47 scripts, 261 tests, 9760 asserts, reading the
      nine changed fixture manifests; the render step's three PASS lines;
    - without the M4-09 wiring (wave 1 alone, the pins and fixture data in place) every new
      pinned file fails: `test_m4_09_commands.py` 9 of 9, `test_m4_09_manifest.py` 14
      (the 7 that pass check the fixture files' own text), `test_m4_09_manifest_checks.py` 26
      of 26, `test_m4_09_one_home.py` 7 of 7, `test_m4_09_sky_step.py` a collection error;
    - each mutation of the gate list below failed a named pinned test (16 mutations; the
      manifest's own fit check skipped failed 5 surroundings cases, the world after the fit
      2, `download regio` reading the file itself 1);
    - the real run of gate 2: downloads 3.55 GB in about 100 s (regio 34.3 s, provenance
      `52e95dc7…` as M4-01 measured); terrain 6.0 s / 994 MB, buildings 6.0 s / 346 MB,
      photo 58.3 s / 1213 MB, roofs 25.5 s / 1301 MB, surfaces 24.1 s / 441 MB, trees 29.3 s
      / 1304 MB, surroundings 64.6 s / 595 MB, shadows 167.8 s / 545 MB, sky 1.1 s, manifest
      1.6 s (wall time, peak resident memory of the process); the largest file the terrain's
      96'040'004 B.

## Scope — files you may touch

- `pipeline/mattini/__main__.py`, `manifest.py`, `sky.py` (new);
- `pipeline/mattini/lock.py` (`fit_problem`'s keyword; `regio_entry`'s argument),
  `download.py` (the reader deleted; `download_regio`'s argument), `surroundings.py` (its
  tile rule and fit replaced by decision 5; no other change);
- the pinned copies (`cp -r docs/briefs/pinning/M4-09/. .`): `pipeline/tests/`
  `test_m4_09_manifest.py`, `test_m4_09_manifest_checks.py`, `test_m4_09_commands.py`,
  `test_m4_09_one_home.py`, `test_m4_09_sky_step.py` (`test_m4_09_sky_config.py` is already
  in place); the nine fixture manifests, the two fixtures' `sky.json` and
  `generated/sky/fixture.json`;
- the existing tests the twelve-key manifest changes (measured in design's rehearsal: 16
  failures in 7 files, and `test_repo_tracked` until the new files are staged; each edit a key
  set, a list or a SHA-256):
  - `test_golden_outputs.py`: the key set; `MANIFEST_SHA256` cf4b939c… →
    `a44cc3d5473058ed41a61e1f5e4d0bd73d9a4652e5d0cff35aed8513e40f82fd` (M3-13's bytes with
    the three null lines, computed two ways) and its comment;
  - `test_terrain_manifest.py`: two key sets, `MANIFEST_WITHOUT_TERRAIN_SHA256` → a44cc3d5…,
    its comment and docstring's top level;
  - `test_buildings_manifest.py`: two key sets and its docstring's top level;
  - `test_buildings_fixture.py`: the key set;
  - `test_roofs_fixture.py`: the key set and the list of null blocks (+ shadows, sky,
    surroundings);
  - `test_manifest_m3.py`: `TOP_LEVEL`, and the seven fixture SHA-256s → M4-09's (those of
    `test_m4_09_manifest.py`);
  - `test_refusals_m3.py`: `PIPELINE_ORDER` (+ surroundings, shadows, sky before manifest);
  - wave 1's own tests if they call `surroundings.regio_tiles`, M4-01's reader or a changed
    signature of decision 5 or 6 (record each in Findings);
- `docs/RELEASE.md` §C: the manifest line only (decision 8);
- your own new tests `test_m4_09_*.py`.

Not `shadows.py`, `terrain.py`, `buildings.py`, the M3 steps, the configs, `game/`, `tools/`,
or any fixture file but those named.

## Depends on

M4-01, M4-02, M4-03 landed and integrated (the `swissaltiregio` lock entry and
`download regio`; `surroundings.py`; `shadows.py`). M4-10 (the game) reads this brief's
manifest; the game's readers of the new blocks (M4-06, M4-07) read the fixtures' folders.

## Done when (gates)

- [ ] The pinned copies are in place (`cp -r docs/briefs/pinning/M4-09/. .`) and stay
      byte-identical (`cmp`, before every commit); they and `test_m4_09_sky_config.py` pass.
      - does NOT prove: that they are the right tests.
- [ ] **The real village end to end, from the command line,** in a scratch `git clone`
      (H22) with your source over it: `download` terrain, buildings, photo, surface, regio,
      tlm into a scratch root (about 3.55 GB; design: 1 min 40 s), then `terrain`,
      `buildings`, `photo`, `roofs`, `surfaces`, `trees`, `surroundings`, `shadows`, `sky`,
      `manifest` into a scratch `--out`. Each exits 0, its own comparison with design's
      values passing (surroundings `d317a358…`, shadows `203cae73…`/`918dfdf6…`). The
      manifest is 327'265 bytes, `a0e2ec92…`, on two runs (a second `--out`, from scratch;
      `cmp`), and without its three new keys it is `3ca0445c…` (decision 8). Record each
      step's wall time and peak memory (design: surroundings 64.6 s, 595 MB; shadows 167.8 s,
      545 MB; sky 1.1 s; the M3 steps as M3-13 measured), every generated file's size (each
      under 100 MiB), the manifest's pair in Findings and in `docs/RELEASE.md` §C (decision
      8); then delete the downloads and outputs.
      - does NOT prove: that the game reads it (M4-06, M4-07, M4-10), or that an export ships
        it (the arc's close runs `tools/export.sh`).
- [ ] Mutations, each failing a named pinned test, recorded with the harm it reproduces:
      - a new block left out of the manifest, or written as `{}` when not built;
      - the sky block computed by `manifest` from the config when `sky` has not run;
      - the manifest's fit check of the surroundings skipped, or after the inputs; the
        world after the fit;
      - `fit_problem` reading the committed `config/surroundings.json` instead of the config
        it is given;
      - `surroundings.py` keeping its own tile rule (a copy of `regio_tiles`) for its fit;
      - `download regio` reading `config/surroundings.json` itself;
      - the sky block not compared with the config (a stale `sky/<area>.json` accepted), or
        `true_to_grid_deg`'s sign flipped;
      - `sky` not refusing a config computed for another world;
      - a new command that does not write the manifest, or given another step's config; the
        commands out of pipeline order in the help; Ctrl-C not caught in `sky`.
      - does NOT prove: that these are the only ways to break it (lesson 4).
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …` (the GUT run reads the
      changed fixture manifests).
      - does NOT prove: that it renders or looks right; anything about the sun in the game.

## Forbidden

Changing a step's rule, design's values, `config/*.json`, a pinned file, or a fixture other
than those of decision 7; any game or `tools/` change; a new dependency (pyproj is design's
tool, never the pipeline's).

## Findings (executor writes)
