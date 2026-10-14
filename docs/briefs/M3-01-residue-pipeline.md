# Brief: M3-01 — M2's residue, the pipeline
Status: OPEN

Written in the design realm; executed by one fresh builder session under
`docs/roles/BUILD.md`. Lane A of wave 1, first; M3-03 follows in this lane
(`docs/briefs/M3-plan.md`).

## Goal

The pipeline half of M2's residue (`docs/history/ARCS.md` §M2, "Carried into M3"): eight
V1 findings and three builders' follow-ups, each a P3. None changes an output byte. They
make refusals name the command that helps, prove two orders of checks, and close test gaps
that let a wrong implementation pass:

- `manifest` checks the lock's fit by the steps' own rule, right after the world (V1-P-01,
  V1-P-07);
- `download terrain` requires exactly the area's tiles (V1-P-02);
- the terrain step's world and inputs checks run before any tile is read, proven by
  recording the reads (V1-P-03);
- two docstrings name test files that exist (V1-P-04);
- `resolution_m` is required for `swissalti3d` (V1-P-05);
- no `*.part` is left in a step's output folder (V1-P-06, the pipeline half; the export
  half is M3-08's presets);
- the canonical lock form is proven against its twins (V1-P-08);
- the follow-ups: `manifest.py`'s docstring lists the terrain's shape checks (M2-06 F9);
  fiona is imported only where a FileGDB is read (M2-04's check); the reader tests compare
  triangles in order (M2-09 F8).

## Read first, in order

1. `CLAUDE.md`; `brain.md` H9, H17, H18.
2. `docs/history/ARCS.md` §M2 (D25 and the carried table); `docs/reviews/M2-V1.md`.
3. `docs/SPEC.md` §5 (the lock), §8 (the expected output, `computed_for`).
4. `pipeline/mattini/download.py`, `lock.py`, `terrain.py`, `buildings.py`, `manifest.py`,
   `datasets.py`, and their tests.
5. The pinned tests: `docs/briefs/pinning/M3-01/`.

## Decisions already made

1. **The lock's fit (V1-P-01, V1-P-07, V1-P-02).** The fit is the steps' rule, exact for
   both datasets: the entry's collection, edition and resolution are the datasets config's,
   and it pins exactly the area's tiles (terrain) or sheets (buildings), no more and no
   fewer. Its one home is a public function in `lock.py`, `fit_problem(lock, datasets, world,
   area, dataset) -> str | None`: the refusal text, naming `python -m mattini lock <x>`, or
   None when the entry fits. Download, the step and `manifest` call it (design's decision:
   M3-03 extends it to the three new datasets, M3-13's manifest calls it for the new
   blocks). Not pinned by name; name any difference in Findings.
   - The terrain step's own fit becomes exact. Measured: today it accepts an extra tile and
     then says "design recomputes".
   - `built_terrain_block` and `built_buildings_block` check in the step's order: the world,
     then the lock's fit, then the inputs (`computed_for`), then the block. An unfitting
     lock is refused with the step's own message, naming `python -m mattini lock <x>` and
     no other command. Measured: today an extra or a missing sheet gets "design recomputes",
     and another edition or no entry reaches a key-set refusal of the block first.
   - The steps check the fit before reading provenance.json, too (design's decision), so a
     changed datasets config names `lock <x>` at the step as well as at `manifest`. This
     one is not pinned: write its test.
   - `download terrain` refuses a lock pinning tiles beyond the area's before any STAC read,
     naming `lock terrain`, as `download buildings` does.
2. **The checks before reading (V1-P-03).** The terrain step's order is right today; its
   test only checked that no output exists. The pinned test records every path opened and
   proves no tile or sheet is read before both checks pass. No code change.
3. **Docstrings (V1-P-04, M2-06 F9).**
   - `test_terrain_manifest.py` and `test_buildings_manifest.py` name
     `test_computed_for_terrain.py` and `test_computed_for_buildings.py`.
   - `manifest.py`'s docstring names the box, the columns and the rows among the terrain's
     refusals.
   - The pinned census reads the docstrings and comments of `pipeline/`, `game/scripts`,
     `game/tests` and `tools/*.sh` (never code or strings): every test file they name exists.
4. **`resolution_m` (V1-P-05).** `load_datasets` refuses a `swissalti3d` entry whose
   `resolution_m` is not a positive finite number (an int or a float, not a bool), a
   `DatasetsConfigError` naming the file and the dataset. The four commands then end with one
   `mattini: error:` line instead of a KeyError's traceback. M3-03 extends the rule to
   `swissimage` and `swisssurface3d` in the same loop, after its edition rule.
5. **No `*.part` after a step (V1-P-06).** After a build that succeeds, the terrain step
   removes every `*.part` in `<out>/terrain/`, and the buildings step every `*.part` in
   `<out>/buildings/`. Each step cleans its own folder only, never `data/raw/`, where
   `download tlm` keeps its part on purpose (M3-03). A refusal removes nothing. The M2-07
   builder's test that pinned a kept `.part` changes.
6. **The canonical lock form (V1-P-08).** `entry_sha256` and `write_lock` are proven on an
   entry with every object's keys in reverse order and a non-ASCII collection; its digest
   `2cc3bd25…3111` was computed two ways (hashlib on the literal, coreutils' sha256sum on its
   bytes). No code change.
7. **fiona (M2-04's check).** Imported only inside the function that reads a FileGDB
   (`buildings.read_sheet`). The pinned test imports every module of the package, so later
   modules count too: lane D's `surfaces.py` and `trees.py` follow the same rule. Then it
   runs `write_manifest` with no fiona module loaded.
8. **The reader tests in order (M2-09 F8).** The two reader test files are replaced: they
   write clockwise, non-overlapping triangles that start at different points and compare
   them in order. Measured with fiona 1.10.1: GDAL's writer stores every ring clockwise seen
   from above, keeping its first point.
9. **Kept for M3-03** (the next brief in this lane; its pinned tests patch or match these):
   `mattini.__main__.main`, the `lock <dataset>` and `download <dataset> --out` shapes,
   `download.STAC_ITEM`, `lock.LOCK_PATH`, `lock.load_lock`, `lock.entry_sha256`,
   `load_datasets(path)`, `DatasetsConfigError`, and the refusal forms
   `"tile <t> of area '<a>': "` and `"cannot read the STAC item"`. Do not rename them.

## Scope — files you may touch

- `pipeline/mattini/download.py`, `lock.py`, `terrain.py`, `buildings.py`, `manifest.py`,
  `datasets.py`.
- `pipeline/tests/`:
  - the pinned copies, new: `one_tile.py`, `test_lock_fit.py`,
    `test_checks_before_reading.py`, `test_docstring_claims.py`, `test_fiona_import.py`,
    `test_lock_canonical.py`, `test_part_leftovers.py`;
  - the pinned copies that replace files: `test_refusals_not_tracebacks.py` (M2-07's,
    whole, plus the new cases), `test_buildings_read.py` (M2-04's pinned file),
    `test_buildings_reader.py` (M2-04's builder's file);
  - the existing tests the new rules change. Measured with design's throwaway, and no
    others: `test_buildings_manifest.py`, `test_terrain_manifest.py`,
    `test_terrain_manifest_source.py`, `test_terrain_refusals.py`, `test_buildings_step.py`.
    Each then expects `lock <x>` or the removed `.part`;
  - your own new tests, under names M3-02 does not use.

Not `__main__.py` (the pinned driver patches its `load_datasets` and `write_manifest`
names), `sheets.py`, `world.py`, `config/`, `tests/shared/`, `game/`, `tools/`.

## Depends on

None. First in lane A; M3-03 follows and starts from this brief's landing.

## Done when (gates)

- [ ] The pinned copies are in place (`cp -r docs/briefs/pinning/M3-01/. .`) and stay
      byte-identical (`cmp`).
      - does NOT prove: that they are the right tests.
- [ ] Before the fix, the pinned files fail for their findings' reasons; record the count per
      file. Design measured on the unmodified code: `test_lock_fit.py` 12,
      `test_refusals_not_tracebacks.py` 9, `test_docstring_claims.py` 2,
      `test_part_leftovers.py` 2, `test_fiona_import.py` 1. The others pass today: they close
      test gaps.
      - does NOT prove: that the fixes are minimal.
- [ ] Mutations, each failing a named pinned test, recorded:
      - the fit checked after the block, or after the inputs;
      - the terrain step's fit not exact (an extra tile accepted);
      - the terrain inputs check moved after the tile loop;
      - `entry_sha256` without `sort_keys`, or with `ensure_ascii=True`;
      - `read_sheet`'s `ring[:3]` kept as the whole ring;
      - fiona imported at module level.
      - does NOT prove: a real republish (none exists).
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that it renders or looks right.

## Forbidden

Changing an output byte (the fixtures, design's expected values), the lock, a config or a
pinned file; the export presets (M3-08); `game/` and `tools/` (M3-02).

## Findings (executor writes)
