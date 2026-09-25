# Brief: M2-02 — M1's residue, the game and tools half
Status: OPEN

Written in the design realm; executed under `docs/roles/BUILD.md` (in M2 by an Opus agent
of the one M2 session, the owner's word of 2026-09-25, `docs/history/RULINGS.md`).

## Goal

The game and tools half of M1's review residue is closed (`docs/history/ARCS.md` §M1, the
carry-over table; the findings in `docs/reviews/M1-R1-terrain.md` T-02 and
`docs/reviews/M1-R1-game.md` G-01 to G-07):

- The loader tests read back a second shared terrain fixture. It lies north-west of its
  origin, at 2 m, across four Terrain3D regions, so a loader that is right only at 0.5 m
  south-east of the origin fails the gate (T-02).
- The clay look's settings are tested (G-01).
- `tools/export.sh` starts the exported Linux build and requires its startup line, and
  scans the export for `ERROR` lines (G-02).
- The one global gate allowlist entry is scoped to the test script that provokes it (G-03).
- The gate reads GUT's last summary line (G-04).
- The version test sees every visible text control (G-05).
- The credits carry godot-cpp's notice (G-06).
- `tools/shot.sh` describes itself truly (G-07).

## Read first, in order

1. `CLAUDE.md`: Hard Rules 2 and 4; `brain.md` §7 H1 to H4, H8, H11, H15.
2. `docs/SPEC.md` §8 (*The terrain grid*, the game part) and §10.
3. `docs/history/ARCS.md` §M1: D17, D19 and the carry-over table rows T-02, G-01 to G-07.
4. `docs/reviews/M1-R1-terrain.md` T-02; `docs/reviews/M1-R1-game.md` G-01 to G-07.
5. `tests/shared/terrain_vectors_nw.json` and `tests/shared/terrain_fixture_nw/`.
6. The pinning tests, `docs/briefs/pinning/M2-02/game/tests/`.

## Decisions already made

- **T-02:** `game/tests/test_terrain_loader_nw.gd` (pinned) loads
  `tests/shared/terrain_fixture_nw/generated/manifest.json` through `WorldConfig`,
  `TerrainGrid` and `TerrainLoader`. It reads every named vertex back from Terrain3D on
  its own local position (tolerance 0.0001 m), finds holes where the vectors list them
  and nothing outside the four regions, and checks the region size (512 at 2 m) and the
  region locations. The loader needs no change if it is right; if a test fails, the loader
  is wrong (fix it within the brief) or the fixture is (BLOCKED).
- **G-01:** a test reads, on the terrain the loader built: `material.show_checkered` false,
  `material.shader_override_enabled` true, `material.shader_override.resource_path` equal
  to `TerrainLoader.CLAY_SHADER`, and `material.world_background` equal to
  `Terrain3DMaterial.NONE`. The `height_offset_m` uniform stays a does-NOT-prove line.
- **G-02:** `tools/export.sh` gains:
  - its export step scans Godot's output for `^(ERROR|SCRIPT ERROR)` lines and fails on
    one, naming it;
  - a step 6 that starts `build/linux/mattini.x86_64 --headless --quit-after 300` (with
    `XDG_DATA_HOME` in a scratch folder, so the owner's `user://` is not touched) and
    requires the startup line `mattini <version>: terrain <area> loaded, <columns> x
    <rows> vertices at <spacing> m`, with the manifest's values, and no `ERROR` line;
  - `game/tests/test_release_settings.gd` (the live preset test) pins both presets'
    `include_filter` and `exclude_filter` exactly.
  - `docs/RELEASE.md` §C keeps its line and drops "by hand until" (design edits it at the
    close).
- **G-03, the mechanism (design's pick):** a gate allowlist entry may be scoped to one test
  script: `<text> @ res://tests/<script>.gd # <reason>`. Such an entry excepts a matching
  error line only in the GUT step, and only while that script runs: GUT prints the
  script's path on a line of its own before its tests (measured, GUT 9.6.1). An entry
  without `@` stays as it is. `WorldConfig: not read from a manifest` becomes
  `… @ res://tests/test_world_config_unbuilt.gd`. The gate refuses a scoped entry whose
  script does not exist. The gate's header comment says all of this. Prove it by
  mutation: the unbuilt error provoked from another test script fails the gate.
- **G-04:** the GUT step compares GUT's last line that starts with `---- ` with
  `---- All tests passed! ----`.
- **G-05:** the version test checks every visible `Control` that has a `text` property
  (Label, Button, RichTextLabel, LineEdit and the rest) outside `UI/PauseMenu`, and the
  window title.
- **G-06:** the credits carry godot-cpp's notice after Terrain3D's licence: the heading
  `godot-cpp (compiled into Terrain3D's library)`, then `Copyright (c) 2017-present Godot
  Engine contributors.` and the MIT licence text, from a file vendored at
  `game/credits/godot-cpp-LICENSE.txt`, outside `addons/terrain_3d/`, whose bytes stay the
  release zip's (SPEC §9) (text from
  `github.com/godotengine/godot-cpp` `LICENSE.md` at the tag Terrain3D 1.0.2 builds with;
  `git clone` works in containers; name the commit in Findings). The export's include
  filter adds that file. A test reads the credits and finds the heading and the copyright
  line.
- **G-07:** `tools/shot.sh`'s header and usage name M1-05's views (`name,E,N,above_m,
  bearing_deg,pitch_deg`, `name`, `name,pause`) and that a refused manifest captures the
  error panel.

## Scope: files you may touch

`game/tests/` · `game/scripts/main.gd` · `game/scripts/terrain/terrain_loader.gd` (only if
T-02's test proves it wrong) · `game/export_presets.cfg` (the include filter) ·
`game/credits/godot-cpp-LICENSE.txt` (new) · `tools/gate.sh` ·
`tools/gate_allowlist.txt` · `tools/export.sh` · `tools/shot.sh` · `pipeline/tests/`
only where a live test pins a file this brief changes (e.g. `test_repo_hygiene.py`).

## Depends on

None. It shares no file with M2-01, so the two can run at once.

## Done when (gates)

- [ ] The pinned copies are in place and byte-identical (`cmp`, as in M2-01).
      - does NOT prove: that the pinned tests are the right tests.
- [ ] T-02: the review's three loader mutations (L: the import position in vertices; L2:
      the first region rounded towards zero; L3: the region size fixed at 2048 vertices)
      each fail `test_terrain_loader_nw.gd`; record each run in Findings.
      - does NOT prove: that the terrain renders or looks right.
- [ ] G-02: `tools/export.sh` runs to its step 6 on a real village build (a scratch
      download; the templates may be downloaded, 1.26 GB) and passes. A mutation (a
      manifest without terrain in the exported build) fails step 6.
      - does NOT prove: that the Windows build starts (no Windows in a container).
- [ ] G-03: the mutation above fails the gate; the scoped entry passes it.
      - does NOT prove: that no other global entry hides a real error. Two remain, each
        scoped by its `user://test_` path.
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that anything renders or looks right.

## Forbidden

A version bump; a change to the terrain rule or to the fixtures' expected bytes; switching
GUT's error tracking off.

## Findings (executor writes)
