# Brief: M2-01 — M1's residue, the pipeline half
Status: OPEN

Written in the design realm; executed under `docs/roles/BUILD.md` (in M2 by an Opus agent
of the one M2 session, the owner's word of 2026-09-25, `docs/history/RULINGS.md`).

## Goal

The pipeline half of M1's review residue is closed (`docs/history/ARCS.md` §M1, the
carry-over table; the full findings in `docs/reviews/M1-R1-terrain.md`). Five changes:

- `terrain` knows the heights it must produce. The expected SHA-256 of each built terrain
  (the village at 0.5 m, 1 m and 2 m) is design data in `config/terrain.json`. `terrain`
  compares its output with it before writing anything, and `manifest` refuses any other
  file (T-01 b).
- A gate test builds a terrain from 2 × 2 synthetic tiles cut by the area, pinned to exact
  bytes (T-01 a). It also pins `build_terrain`'s own description bytes (T-03).
- `manifest` checks the terrain block's `source` against the lock and the datasets config
  (T-04), with exact key sets (T-03).
- The download and the lock serve the area named by `config/terrain.json` (T-06).
- The origin census, the tracked-files test and a docstring are tightened (T-05, T-07,
  T-08).

The pipeline also reproduces the second shared terrain fixture (`tests/shared/
terrain_fixture_nw/`) that M2-02's game tests load: the seam, as for the first fixture.

## Read first, in order

1. `CLAUDE.md`: Hard Rules 2, 4 and 5.
2. `docs/SPEC.md` §5 (the lock) and §8 (*The terrain grid*, including the expected
   SHA-256 paragraph added at M2 planning).
3. `docs/history/ARCS.md` §M1: D19 and the carry-over table rows T-01, T-03 to T-08.
4. `docs/reviews/M1-R1-terrain.md`: T-01, T-03 to T-08 (the harm, the proof, the fix).
5. `config/terrain.json` (its new shape), `config/world.json`, `config/datasets.json`,
   `config/datasets.lock.json`.
6. `tests/shared/terrain_fixture/` and `tests/shared/terrain_fixture_nw/` with
   `tests/shared/terrain_vectors.json` and `tests/shared/terrain_vectors_nw.json`.
7. The pinning tests, `docs/briefs/pinning/M2-01/pipeline/tests/`.

## Decisions already made

- **The expected SHA-256 (T-01 b; SPEC §8).** Each area in `config/terrain.json` carries
  `expected_sha256`, an object from a spacing, as swisstopo writes it (`format(s, "g")`:
  `"0.5"`, `"1"`, `"2"`), to the SHA-256 of the heights file at that spacing: 64
  lower-case hex digits. It must hold the configured spacing, and holds no key but these
  three. The key set of an area is exactly `{"expected_sha256", "spacing_m"}`. The
  village's three values were computed by design two independent ways at M2 planning (the
  pipeline's own code and an exact area-overlap implementation, identical bits):
  - 0.5 m: `b6334c1fdc992f0576bc59efd51484db2178cbe399ad46512a4bf510abb9411a` (96'040'004 bytes),
  - 1 m: `71bd4f174dfc3d07a3becace073c62bdf6b5cc010072a5e483a484210e8bc333` (24'020'004 bytes),
  - 2 m: `d6c1d558fee28c91472f2fea9c5db06d9b74480dd22f77554bf7037beec794ce` (6'010'004 bytes).

  `build_terrain` computes the heights, then compares their SHA-256 with the expected
  value *before* writing anything. A difference is a `TerrainError` naming the area, the
  spacing, both values and `config/terrain.json`, and says that design computed the
  expected value two independent ways, so this machine or this code produces other
  heights. Nothing is written then. `built_terrain_block` (so `manifest`) refuses a built
  block whose `sha256` is not the expected value for its spacing, naming
  `python -m mattini terrain`. The two shared fixtures' `terrain.json` carry their own
  value (0.5 m `fd02c744…` and 2 m `31096e50…`).
- **The 2 × 2 build test (T-01 a, T-03)** is pinned in `test_terrain_build_tiles.py`: four
  synthetic 0.5 m GeoTIFF tiles (2623-1095, 2624-1095, 2623-1096, 2624-1096) written by the
  test from a formula, and an area E 2'623'250–2'624'750 / N 1'095'500–1'096'500 that cuts
  all four. Built at 2 m and at 0.5 m, the heights file has design's exact SHA-256. The
  description `terrain/village.json` has exactly the bytes the test renders from the
  inputs (T-03: no date, host or path can enter it).
- **The manifest checks the source (T-04, T-03).** `built_terrain_block` also requires the
  following, else it refuses naming `python -m mattini terrain`:
  - `source` has exactly the keys `attribution`, `collection`, `dataset`, `edition`,
    `resolution_m`, `tiles`, and each entry of `tiles` exactly `sha256`, `tile`;
  - `source.dataset` is `swissalti3d`;
  - `attribution`, `collection`, `edition` and `resolution_m` equal `config/datasets.json`'s;
  - `tiles` equals, in order, the tiles covering the area, each with the SHA-256 the lock
    pins for it (`config/datasets.lock.json`).

  `build_manifest` and `write_manifest` take a `lock_path` keyword (default the committed
  lock). Consequence for the fixtures: their `source.tiles` name the real tile ids their
  boxes lie in (`2601-1199` for the first fixture, `2698-1101` for the second), not
  `synthetic`, and each fixture folder holds a `datasets.lock.json` pinning that tile's
  SHA-256 (the SHA-256 of its `source.f32`) with the file name `source.f32`. Design
  prepared both fixtures accordingly; their heights files are unchanged. The first
  fixture's changed files (`terrain.json`, `datasets.lock.json`,
  `generated/terrain/fixture.json`, `generated/manifest.json`) and the new
  `config/terrain.json` travel with the pinning tests
  (`docs/briefs/pinning/M2-01/config/`, `…/tests/shared/terrain_fixture/`), because the
  code M1 left refuses them; the pinned copy step puts them in place.
- **The area served (T-06).** `download terrain` and `lock terrain` take the area from
  `config/terrain.json` (its one area). The API: `village_tiles(world)` becomes
  `download.area_tiles(world, area)`; `published_assets`, `download_terrain` and
  `lock.build_lock` take a keyword-only `area`. The command line reads the area from the
  terrain config and passes it on. Nothing in `pipeline/mattini/` names `"village"` any
  more; the download's refusals name the area.
- **T-05, T-07, T-08:** as in the carry-over table.
  - T-05: the census also catches the kilometre pair reversed (`1096 … 2623`), the pair on
    lines up to three apart in either order, and a mantissa with trailing zeros
    (`2.6230e6`, `2.62300E+06`). It proves text only, and its docstring says so.
  - T-07: `test_repo_tracked.py` scoped by exclusion. Every file the gate or the game
    depends on under `config/`, `tests/shared/`, `tools/`, `game/` (vendored Terrain3D
    binaries included) and `pipeline/` must be tracked, minus named exclusions
    (`game/.godot/`, `game/assets/generated/`, caches).
  - T-08: `test_terrain_rules.py`'s docstring states SPEC §8's condition: one rounding
    while the height offset subtracts exactly.
- **The second fixture's pipeline half:** `test_terrain_fixture_nw.py` (pinned) reproduces
  `tests/shared/terrain_fixture_nw/generated/` byte for byte, as `test_terrain_fixture.py`
  does for the first.

## Scope: files you may touch

`pipeline/mattini/terrain.py` · `pipeline/mattini/manifest.py` ·
`pipeline/mattini/download.py` · `pipeline/mattini/lock.py` · `pipeline/mattini/__main__.py`
· `pipeline/tests/` (the pinned copies, your own tests, and the live copies of earlier
tests the changes touch) · the pinned design data put in place by the copy step
(`config/terrain.json`, `tests/shared/terrain_fixture/`), never edited: a pinned test that
proves one wrong is a BLOCKED question.

## Depends on

None. It shares no file with M2-02, so the two can run at once.

## Done when (gates)

- [ ] The pinned copies are in place and byte-identical:
      `cmp` each file under `docs/briefs/pinning/M2-01/` with its live copy.
      - does NOT prove: that the pinned tests are the right tests (design's job).
- [ ] `terrain` refuses a mismatching output before writing anything. Mutation: change one
      height rule (e.g. the window) and watch `test_terrain_build_tiles.py` and the
      expected-SHA test fail; record both runs in Findings.
      - does NOT prove: that the owner's Windows PC computes the same bytes (only its first
        run shows it, and now `terrain` says so itself).
- [ ] With the real tiles (downloaded to a scratch folder, never committed),
      `python -m mattini terrain --raw <scratch>` writes `village.f32` `b6334c1f…` and
      exits 0. A copy of `config/terrain.json` set to 1 m or 2 m reproduces design's value
      (Findings: the three runs).
      - does NOT prove: that it renders or looks right.
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that the game places the terrain right (M2-02's second fixture).

## Forbidden

A new dependency; a change to the rule (SPEC §8) or to any fixture's expected bytes; a
version bump.

## Findings (executor writes)
