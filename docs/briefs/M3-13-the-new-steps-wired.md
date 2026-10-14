# Brief: M3-13 — The new steps on the command line and in the manifest
Status: OPEN

Written in the design realm; executed by one fresh builder session under
`docs/roles/BUILD.md`. Lane H of wave 2, after wave 1 has landed and been integrated
(`docs/briefs/M3-plan.md`).

## Goal

The four steps of wave 1 become commands, and their outputs reach the game through the
manifest.

- `python -m mattini photo`, `roofs`, `surfaces` and `trees` build their outputs, as
  `terrain` and `buildings` do.
- The manifest's top level becomes exactly {buildings, photo, roofs, schema, surfaces,
  terrain, trees, world, world_sha256}: each new block checked, null when its step has not
  run.
- The several-datasets rule for `computed_for` gets one home, `lock.entries_sha256`.

Measured with design's throwaway on the real village: every step from the command line
writes design's values, and the manifest is 324'359 bytes, SHA-256 `3ca0445c…`.

## Read first, in order

1. `CLAUDE.md` (Hard Rules 2, 4, 5); `brain.md` H9, H17, H18, H24.
2. `docs/SPEC.md` §5 (the lock), §8 (the manifest, the expected output and its check order,
   *The photo*, *Roof colours*, *The surfaces*, *The trees*).
3. `pipeline/mattini/__main__.py`, `manifest.py`, `lock.py`, and the wave-1 modules
   `photo.py`, `roofs.py`, `surfaces.py`, `trees.py` (their `build_*` and `built_*_block`
   functions); the briefs M3-03 to M3-07 and their Findings.
4. The pinned tests and fixture manifests: `docs/briefs/pinning/M3-13/`.

## Decisions already made

1. **The commands** `photo`, `roofs`, `surfaces`, `trees`.
   - Each loads `config/world.json`, `datasets.json`, `datasets.lock.json` and its step
     config, plus `config/terrain.json` for roofs and trees.
   - Each takes `--raw` and `--out`, as `terrain` and `buildings` do; calls
     `<module>.build_<step>(…, raw_root, out_dir, progress=…)` through the module attribute
     (the pinned Ctrl-C test patches it); then writes the manifest and prints its path.
   - A refusal is one `mattini: error: …` line and exit 1, no traceback. Ctrl-C is M3-03's
     one handler in `main()`: ``mattini: interrupted: `python -m mattini <command>` did not
     finish; run it again``, exit 130.
   - The help lists the commands in pipeline order: lock, download, terrain, buildings,
     photo, roofs, surfaces, trees, manifest.
2. **`write_manifest`.**
   - The top level is exactly {buildings, photo, roofs, schema, surfaces, terrain, trees,
     world, world_sha256}; schema stays 1; serialised as today
     (`json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"`).
   - It is written through a `.part` rename (design's decision: at 324 KB, a cut write
     would leave a manifest the game refuses as JSON).
   - A new block is null when its step has not run (its description file is absent).
   - Every step config is loaded and checked even when its step has not run, as the
     terrain's and the buildings' are today.
   - Areas: photo and surfaces from their own config's one area; roofs and trees from the
     terrain config's.
3. **The check order for a built new block, in `manifest.py`** (uniform for the four, whatever
   wave 1's block functions check themselves):
   1. `computed_for.world_sha256`, with the terrain's world text (design's step,
      `config/world.json`);
   2. the lock's fit for every dataset the step reads, in sorted order, through
      `lock.fit_problem` (M3-01, extended by M3-03), naming `python -m mattini lock <x>`;
   3. `computed_for.inputs_sha256`: `lock.entry_sha256` for one dataset, `lock.entries_sha256`
      for several, with a "design recomputes" text naming the config;
   4. roofs only: refused when no buildings are built, naming `python -m mattini buildings`;
   5. the step's `built_<step>_block`.

   Refusals use the step's error class (PhotoError, RoofsError, SurfacesError, TreesError),
   which `__main__` catches.
4. **`lock.entries_sha256(lock, names) -> str`**: the SHA-256 of `json.dumps({name: entry
   for name in names}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)` in
   UTF-8, the one home of the rule. roofs.py and trees.py call it instead of their own
   copies. A name the lock lacks is a LockError naming its lock command, not a KeyError.
5. **The M2 fixtures' manifests** (`tests/shared/terrain_fixture`, `terrain_fixture_nw`,
   `buildings_fixture`: `generated/manifest.json`) take the 9-key shape: design's pinned
   copies, each the M2 file plus four `"<block>": null` lines, made two ways.
6. **Known and accepted** (design's answers to the wiring agent's questions):
   - `roofs` run before `buildings` writes its file; `manifest` then refuses it, naming
     `buildings`.
   - `tests/shared/roofs_fixture/photo.json` describes the synthetic photo's windows, not a
     photo config; the pinned test says so.
   - The terrain file is 91.6 MiB, 8.4 MiB under GitHub's limit; M3-08's packs check it.

## Scope — files you may touch

- `pipeline/mattini/__main__.py`, `manifest.py`, `lock.py` (`entries_sha256`; the fit
  function's use).
- `pipeline/mattini/roofs.py` and `trees.py`: their `inputs_sha256` call
  `lock.entries_sha256`, that change only.
- The pinned copies (`cp -r docs/briefs/pinning/M3-13/. .`): `pipeline/tests/`
  `test_manifest_m3.py`, `test_manifest_lock_fit_m3.py`, `test_lock_entries.py`,
  `test_refusals_m3.py`; the three M2 fixture manifests.
- The existing tests the 9-key manifest breaks (measured: 9 failures, no others):
  - `test_golden_outputs.py`: the key set; `MANIFEST_SHA256` ba8383ff… →
    `cf4b939c6e4a89bf202081c365f22b338180c7d7141d34189af69cf709e20081` (computed two ways)
    and its comment;
  - `test_terrain_manifest.py`: two key sets, `MANIFEST_WITHOUT_TERRAIN_SHA256` → cf4b939c…,
    and its docstring's top level;
  - `test_buildings_manifest.py`: two key sets and its docstring's top level;
  - `test_buildings_fixture.py`: the key set.
- Your own new tests.

Not `photo.py`, `surfaces.py`, `download.py`, `terrain.py`, `buildings.py`, the configs,
the other fixtures, `game/`, `tools/`.

## Depends on

Wave 1 landed and integrated: M3-01 and M3-03 (`lock.fit_problem`, the Ctrl-C handler),
M3-04 to M3-07 (the four steps). Lane I (M3-14) runs at the same time and shares no file.

## Done when (gates)

- [ ] The pinned copies are in place (`cp -r docs/briefs/pinning/M3-13/. .`) and stay
      byte-identical (`cmp`).
      - does NOT prove: that they are the right tests.
- [ ] The real village end to end in a scratch checkout, from the command line: `download`
      for every dataset (the TLM zip may be copied from a scratch root where it is verified,
      never fetched twice), then `terrain`, `buildings`, `photo`, `roofs`, `surfaces`,
      `trees`, `manifest`. Each writes design's values; the manifest is `3ca0445c…`
      (324'359 bytes) on two runs. Record each step's time and peak memory (design: photo
      1.6 GB in strips, trees 2.6 GB) and every generated file's size (each under 100 MiB).
      - does NOT prove: that the game reads it (M3-14 and the integration after wave 2).
- [ ] Mutations, each failing a named pinned test, recorded:
      - null blocks left out, or written as `{}`;
      - roofs not refused without buildings;
      - no fit check in `manifest`, or the fit after the inputs;
      - `entries_sha256` hashing the entries one by one;
      - Ctrl-C not caught.
      - does NOT prove: a real republish.
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that it renders or looks right.

## Forbidden

Changing a step's rule, design's values, a fixture other than the three M2 manifests, or a
pinned file; any game change.

## Findings (executor writes)
