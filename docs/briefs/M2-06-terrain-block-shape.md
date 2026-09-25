# Brief: M2-06 — The terrain block's shape, and three test gaps (M2-01's check)
Status: OPEN

Written in the design realm; executed under `docs/roles/BUILD.md` (in M2 by an Opus agent
of the one M2 session, the owner's word of 2026-09-25, `docs/history/RULINGS.md`).

## Goal

`manifest` refuses a terrain description whose box, rows or columns are not the ones the
world config's area and the terrain config's spacing give. Three gaps that M2-01's
independent check found are closed with tests:
- the lock comparison beyond the first tile;
- the expected value chosen by the configured spacing;
- a refused build that leaves a good terrain on disk untouched.

Today a description with its box shifted 1 km, or with its rows and columns swapped, passes
every check (measured by M2-01's checker). The game would then place the village 1 km off,
or refuse it, and the manifest would never have said so.

## Read first, in order

1. `CLAUDE.md`: Hard Rules 2, 4 and 5.
2. `docs/SPEC.md` §8, *The terrain grid*.
3. `docs/briefs/M2-01-terrain-residue-pipeline.md`, its Findings (item 9 in particular).
4. `pipeline/mattini/terrain.py` (`built_terrain_block`, `check_terrain_config`),
   `pipeline/mattini/manifest.py`, `pipeline/tests/test_terrain_manifest_source.py`,
   `pipeline/tests/test_terrain_build_tiles.py`.

## Decisions already made

- **The shape (the checker's P2):**
  - `built_terrain_block` requires `lv95_box` to equal the world config's box for the
    area, as floats;
  - it requires `columns` = (e_max − e_min) / s + 1 and `rows` = (n_max − n_min) / s + 1
    for the configured spacing s.

  Each refusal names the field, both values and `python -m mattini terrain`. The world
  config it compares with is the one the manifest is written from (the function takes
  the parsed world, or the manifest passes its box in: the builder's choice, recorded in
  Findings).
- **Test gaps (the checker's P3s):**
  - (a) A test whose area has at least two tiles changes the lock's SHA-256 of a tile other
    than the first, and `manifest` refuses (mutation: compare only the first tile, and see
    it fail).
  - (b) A config holding all three expected values, set to 2 m, builds and passes
    `manifest`; the same config with the 2 m value exchanged for the 0.5 m value is
    refused (mutation: take the first value, and see it fail).
  - (c) A good terrain in place, then a build refused by its expected value: the good
    files are byte for byte unchanged (mutation: write, then compare, then delete on a
    mismatch, and see it fail).
- **Wording:** `test_repo_tracked.py`'s does-NOT-prove line says what it means (M2-01's
  checker: "is missed" should read "is caught"), and its positive control asserts all four
  Terrain3D binaries.

## Scope: files you may touch

`pipeline/mattini/terrain.py` · `pipeline/mattini/manifest.py` (only to pass the world
config's box, if that is the choice) · `pipeline/tests/`.

## Depends on

M2-04 (it changes `manifest.py`; this brief comes after it, beside M2-05, with which it
shares no file).

## Done when (gates)

- [ ] The shape check refuses a box shifted by 1 km and rows and columns swapped (tests on
      the first fixture), and the three mutations above each fail a named test (Findings:
      both runs of each).
      - does NOT prove: anything about the buildings' block (M2-04 has its own checks).
- [ ] The real village at 0.5 m still builds and passes `manifest`, and its terrain block
      and `village.json` are byte for byte M1-03's (`ea6e6c90…`; Findings).
      - does NOT prove: that it renders.
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that the game places the terrain right (M2-02's two fixtures do).

## Forbidden

A change to the rule, to any fixture's bytes or to the expected values.

## Findings (executor writes)
