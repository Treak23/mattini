# Brief: M0-02 — World config and coordinate transforms, pipeline side
Status: OPEN

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
