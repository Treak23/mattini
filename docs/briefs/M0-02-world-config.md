# Brief: M0-02 — World config and coordinate transforms, pipeline side
Status: DONE (1d53a00)

Written in the design realm; executed by one fresh executor session. Executor rules:
`docs/roles/BUILD.md`. Review tier: **Tier 1** (WORKFLOW §Review policy).

## Goal

The pipeline reads `config/world.json` (the one home of the origin, the axis mapping and
the areas), refuses a malformed, mirroring or scrambled config with an error that names the
file, converts LV95 + LN02 heights to Godot local coordinates and back exactly as the
shared vectors say, and writes the manifest `game/assets/generated/manifest.json`, whose
`world` block is `config/world.json` verbatim with its SHA-256. The manifest is the only
way the game learns the origin. `python -m mattini manifest` is the command the gate runs.

## Read first, in order

1. `CLAUDE.md` — Hard Rules 2, 4 and 5.
2. `docs/SPEC.md` §6 Coordinates, §7 Areas, §8 (the manifest, determinism).
3. `config/world.json` — the ground truth.
4. `tests/shared/world_vectors.json` — the conversions both halves must agree on.
5. `docs/briefs/pinning/M0-02/pipeline/tests/test_world.py` and `test_manifest.py`.

## Decisions already made

- Origin E 2'623'000 / N 1'096'000; heights unchanged (LN02 metres); x = +E, y = +H,
  z = −N; 1 unit = 1 m (owner, day one; SPEC §6 and §13).
- The axis mapping is read from `config/world.json` (`axes`), never hard-coded: each game
  axis names one signed source axis (`+e`, `-n`, `+h` …). The loader refuses anything that
  is not a proper rotation: a mirror, a repeated axis or a missing axis (Hard Rule 4).
- The CRS must be exactly EPSG:2056 horizontal and EPSG:5728 vertical; `schema` must be 1;
  every area must be a non-empty box. Every refusal raises `WorldConfigError` with the
  file's path in the message (Hard Rule 2).
- The API the pinning tests use:
  `mattini.world.load_world(path=<repo>/config/world.json)` returns an object with
  `origin_e`, `origin_n`, `height_offset`, `to_local(e, n, h) -> (x, y, z)`,
  `to_lv95(x, y, z) -> (e, n, h)` and `area(name) -> (e_min, e_max, n_min, n_max)`;
  `mattini.manifest.write_manifest(out_dir=<repo>/game/assets/generated) -> Path` writes
  `manifest.json`; `python -m mattini manifest [--out DIR]` does the same and prints the
  path.
- The manifest holds `schema` 1, `world` (config/world.json parsed) and `world_sha256`
  (SHA-256 of the file's bytes), written deterministically: sorted keys, fixed formatting,
  no times, no absolute paths (Hard Rule 5).
- Python floats are 64-bit; no numeric libraries are needed.

## Scope — files you may touch

`pipeline/mattini/world.py` · `pipeline/mattini/manifest.py` · `pipeline/mattini/__main__.py`
· `pipeline/tests/test_world.py` and `pipeline/tests/test_manifest.py` (pinned copies,
unchanged) · further tests of your own in `pipeline/tests/test_world_*.py` and
`pipeline/tests/test_manifest_*.py`

## Depends on

M0-01.

## Done when (gates)

- [ ] Both pinned copies are in place and unchanged (`cmp` each against
      `docs/briefs/pinning/M0-02/…`).
      - does NOT prove: that the pinned tests are right (verified by the design realm
        against a scratch implementation, 55 tests, 2026-09-24).
- [ ] `uv run --project pipeline --frozen pytest pipeline/tests` passes.
      - does NOT prove: that the game side agrees (M0-03 runs the same vectors in GDScript).
- [ ] Mutation proofs (Tier 1), each recorded in Findings with the failing tests' names and
      the owner-visible harm it reproduces: (a) ignore the sign in the axis mapping →
      the vector tests fail (harm: the world mirrored north–south); (b) remove the rotation
      check → the mirror test fails (harm: a mirrored config accepted silently); (c) add a
      timestamp to the manifest → the determinism test fails (harm: assets nobody can
      reproduce byte for byte); (d) write the origin number into a code file → the census
      fails.
      - does NOT prove: that the census catches every way to smuggle an offset (it reads
        text; an origin computed from other numbers passes it).
- [ ] `uv run --project pipeline python -m mattini manifest` from the repository root writes
      `game/assets/generated/manifest.json` (git-ignored) and prints its path.
      - does NOT prove: that the game reads it (M0-03).
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: anything about rendering; nothing here is drawn.

## Forbidden

Any change to `config/world.json` or `tests/shared/world_vectors.json` (design data: a
disagreement goes to Findings or BLOCKED.md); new dependencies; changing a pinned copy.

## Findings (executor writes)

Executor session, 2026-09-24 (same session as M0-01).

1. **Pinned copies:** `cmp` of `test_world.py` and `test_manifest.py` against
   `docs/briefs/pinning/M0-02/pipeline/tests/` exits 0 for both.
2. **pytest:** 144 passed: 21 hygiene (M0-01), 29 pinned here, 94 of my own in
   `test_world_rotations.py` (all 48 signed axis mappings: the 24 rotations accepted,
   right-handed and round-tripping, the 24 mirrors refused), `test_world_refusals.py`
   (27 malformed configs, each refused with the file named), `test_world_transforms.py`
   (round trips, the height offset, the 32-bit trap point) and `test_manifest_output.py`
   (LF bytes, sorted keys, independence from the working directory, a refused config
   writes nothing, the command exits 1 naming the file).
3. **Command:** `uv run --project pipeline python -m mattini manifest` from the repository
   root printed `/home/user/mattini/game/assets/generated/manifest.json`, exit 0; the file
   is git-ignored (`.gitignore:5`); `world_sha256` =
   `d2607d1362f3c7ec26b7e00c38d873b36d29db83aa169eebf60e0dd6f299509b`.
4. **Mutation proofs (Tier 1)**, one per run through `tools/gate.sh`, each undone with
   `git apply -R` of its saved diff; the restored run exits 0 (144 passed):

   | Run | Mutation | Exit, step | Failing tests | Owner-visible harm |
   |---|---|---|---|---|
   | a | `to_local` and `to_lv95` ignore the sign of each axis | 1, `pytest` (39 failed) | pinned: `test_to_local_matches_shared_vectors` and `test_to_lv95_matches_shared_vectors` (7 of 8 vectors each; the origin vector passes), `test_mapping_is_a_rotation_not_a_mirror`, `test_load_world_reads_the_given_file`; mine: 21 of the 24 rotations in `test_world_rotations.py`, 2 in `test_world_transforms.py` | the world mirrored north–south: the village drawn with the Matterhorn to its north-west |
   | b | the determinant check in `_rotation` removed | 1, `pytest` (26 failed) | pinned: `test_bad_config_is_refused_with_the_file_named[mirror]`; mine: the 24 mirrors in `test_world_rotations.py`, `test_a_refused_config_writes_no_manifest` | a mirrored config accepted silently, and a mirrored manifest written for the game |
   | c | `"written_at": datetime.now().isoformat()` in the manifest | 1, `pytest` (3 failed) | pinned: `test_writing_twice_gives_identical_bytes`, `test_cli_writes_the_same_manifest`; mine: `test_cli_output_does_not_depend_on_the_working_directory` | generated assets nobody can reproduce byte for byte |
   | d | `ORIGIN_E = 2623000.0` appended to `pipeline/mattini/world.py` | 1, `pytest` (1 failed) | pinned: `test_origin_numbers_live_only_in_config` | a second home for the origin that drifts from `config/world.json` |

5. **A reading taken (design to confirm):** nothing defines what `height_offset_m` does;
   it is 0.0 today, where every reading gives the same numbers. I read it as the vertical
   part of the origin, subtracted like the easting and northing: y = H − height_offset_m,
   and H = y + height_offset_m back. `test_world_transforms.py::
   test_height_offset_is_subtracted_from_heights` pins that reading so a change to it is
   deliberate; the game side (M0-03) must read it the same way, or a non-zero offset
   would split the two halves by twice the offset.
6. **Strictness beyond the pinned refusals** (all refused with the file named): unknown or
   missing keys at every level, duplicate JSON keys (Python's `json` would otherwise keep
   the last one silently), `NaN` and `Infinity` literals, booleans where numbers are
   expected (`true == 1` in Python), and `area()` asked for an unknown name.
7. **Where the defaults point:** `mattini.world.REPO` is derived from the module's own
   location (`Path(__file__).parents[2]`), which is the repository because `uv sync`
   installs the package editable; a non-editable install would point elsewhere.
8. **Line endings:** the manifest is written with `write_bytes` and `\n` endings, because
   `Path.write_text` on Windows turns `\n` into `\r\n` and the owner's Windows PC would
   then write different bytes from Linux (Hard Rule 5). Not measured on Windows.
9. The census (`test_origin_numbers_live_only_in_config`) proves text only: it does not
   see an origin computed from other numbers, and it skips every path with a `tests`,
   `addons`, `generated` or `.godot` part.
