# Brief: M3-R1-fix-6 — The surfaces PNG's bytes are design's, so the manifest is the same everywhere
Status: OPEN

Written in the design realm from review finding M3-R1-I-01 (P2, Tier 2 with Hard Rule 5's full
discipline; `docs/reviews/M3-R1-inputs.md`) and design's answer of 2026-10-15 (SPEC §13 row 39);
executed by one fresh builder session under `docs/roles/BUILD.md`. Lane F-C of the fix wave
(`docs/briefs/M3-plan.md` §Fix wave).

## Goal

On a machine whose deflate writes other bytes than design's, `python -m mattini surfaces` refuses
before writing anything and names the machine's zlib, instead of exiting 0 with a PNG and a
manifest that differ from design's `3ca0445c…`. The gate on such a machine fails too. Today the
PNG's SHA-256 goes into `surfaces/<area>.json` and from there into `manifest.json`, and only its
pixels are compared (`pipeline/mattini/surfaces.py:578`, `:690`, `:908`).

Measured by design (2026-10-15): zlib 1.3 (the container's system Python) and zlib 1.3.2 (uv's
managed CPython 3.13.14, what a machine without a system 3.13 gets) write the same bytes for the
fixture at every cell and for a 2500 × 4000 class-like grid; zlib-ng 2.2.5 writes other bytes for
the fixture at 0.2 m (960 bytes, not 955) and for the village (the lens: 950'236, not 1'148'848),
and the same bytes for the fixture at 0.5 and 1 m (small grids can compress alike). Windows was
not measured.

## Read first, in order

1. `docs/reviews/M3-R1-inputs.md` §M3-R1-I-01.
2. `docs/SPEC.md` §8, the surfaces, *The PNG* (amended 2026-10-15).
3. `pipeline/mattini/surfaces.py`: `check_surfaces_config`, `build_surfaces`, `write_surfaces`,
   `built_surfaces_block`, `png_l8`.
4. `pipeline/tests/test_surfaces_fixture.py` (line 150's allowance), `test_surfaces_config.py`,
   `test_surfaces_checks.py`.
5. The pinned test: `docs/briefs/pinning/M3-R1-fix-6/pipeline/tests/test_m3_r1_fix6_png_bytes.py`.

## Decisions already made

1. **The config** gains `expected_png_sha256` in each area, keyed by cell exactly as
   `expected_pixels_sha256` (same key set), 64 lower-case hex digits each;
   `check_surfaces_config` requires it (exact key sets stay exact). SPEC §8 already says so.
2. **The fixture's values** are design's and are in the pinned test (`FIXTURE_PNG_SHA256`); write
   them into `tests/shared/surfaces_fixture/surfaces.json`.
3. **The village's values**: the 0.2 value is the PNG of the classes design pinned
   (`expected_pixels_sha256["0.2"]`), which the R1 inputs lens built independently: 1'148'917
   bytes, SHA-256 starting `8922edf9`. You compute all three (0.2, 0.5, 1) from the real run, on
   the container's Python (record `zlib.ZLIB_RUNTIME_VERSION`), with the cell changed in a scratch
   copy of the config, each run's pixels first equal to design's `expected_pixels_sha256` for that
   cell (so the step's own content check is the oracle); the 0.2 value must match the lens's size
   and prefix, or the brief is BLOCKED. These values pin the encoder, not the classes (JSON holds
   no comment): Findings and the step's refusal say so.
4. **Where the step refuses:** after the classes match `expected_pixels_sha256` and before
   anything is written (no `.part`, no folder). The message is a `SurfacesError` naming
   `zlib.ZLIB_RUNTIME_VERSION`, both SHA-256s, the config, and the remedy: a Python whose zlib
   writes design's bytes (zlib 1.3.x was measured to; uv's managed CPython, e.g. `uv python
   install 3.13 --managed-python` with `UV_PYTHON_PREFERENCE=only-managed`). Encode the PNG once
   (it is about 150 MB of scanlines): pass it to the writer rather than compressing twice.
5. **The manifest side:** `built_surfaces_block` refuses a built PNG whose SHA-256 is not the
   config's for the block's cell, naming `python -m mattini surfaces` (a test of yours, with a
   mutation).
6. **The allowance goes:** `test_surfaces_fixture.py`'s "only the PNG's own SHA-256 may differ"
   becomes an exact comparison with the committed block, so the gate fails on a machine whose
   zlib writes other bytes (the pinned `test_this_machine_writes_the_designed_png_bytes` too).
7. **The release walk:** `docs/RELEASE.md` §C's list says the surfaces compare by pixels and PNG
   (`config/surfaces.json`) and gains one box: the fresh checkout's `manifest.json` has the
   SHA-256 the arc plan names (M3: `3ca0445c…`, 324'359 bytes), compared by a command, its
   output in the release record.

## Scope — files you may touch

- `pipeline/mattini/surfaces.py`.
- `config/surfaces.json` (the new key only), `tests/shared/surfaces_fixture/surfaces.json` (the
  new key only).
- `pipeline/tests/test_m3_r1_fix6_png_bytes.py` (the pinned copy, byte-identical),
  `pipeline/tests/test_surfaces_config.py`, `test_surfaces_fixture.py`,
  `test_surfaces_checks.py`, and any other test that pins the surfaces config's exact key set
  (design's throwaway run: four cases in the first two files).
- `docs/RELEASE.md` §C (decision 7 only).
- This brief file (Status and Findings).

## Depends on

None.

## Done when (gates)

- [ ] `cmp` of the pinned and live `test_m3_r1_fix6_png_bytes.py` exits 0 and its nine cases
      pass.
      - does NOT prove: that every other deflate is refused by the fixture alone (the real run's
        refusal covers the village).
- [ ] Mutation proof in a throwaway clone (saved diffs, `git apply -R`): (1) the step's PNG
      comparison removed; (2) the manifest's removed; (3) the config check accepting a missing
      key; (4) the step's comparison moved after the write (a `.part` left); (5) zlib-ng in place
      of zlib (`sitecustomize.py` on `PYTHONPATH`, as the lens did) with mattini untouched: the
      full pytest fails (name the case) and `surfaces` on the real inputs refuses naming
      zlib-ng's version. Each fails a named test; output and owner-visible harm in Findings.
      - does NOT prove: Windows' bundled zlib (not measured; the owner's run there is the
        check, and the refusal names it if it differs).
- [ ] The real village from the command line, fresh clone, pinned inputs: `surfaces` and
      `manifest` exit 0, `manifest.json` is 324'359 bytes with SHA-256 `3ca0445c9109eec4696d654d
      1c7536f50220f4db04503fab836412f5b0c01065` (the descriptions do not change).
      - does NOT prove: another machine's bytes.
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`.
      - does NOT prove: that it renders or looks right.

## Forbidden

A deflate of mattini's own; renaming or changing the helpers `trees.py` imports from
`surfaces.py` (lane F-A builds beside you); dropping the PNG's SHA-256 from the description; any change to the
description's or the manifest's key sets, the PNG's format, the game, `tools/`; a version bump;
a new dependency; a model's name or id anywhere in the repository.

## Findings (executor writes)
