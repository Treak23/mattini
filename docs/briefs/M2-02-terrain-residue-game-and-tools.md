# Brief: M2-02 — M1's residue, the game and tools half
Status: DONE (2cf5660)

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

- [x] The pinned copies are in place and byte-identical (`cmp`, as in M2-01).
      - does NOT prove: that the pinned tests are the right tests.
- [x] T-02: the review's three loader mutations (L: the import position in vertices; L2:
      the first region rounded towards zero; L3: the region size fixed at 2048 vertices)
      each fail `test_terrain_loader_nw.gd`; record each run in Findings.
      - does NOT prove: that the terrain renders or looks right.
- [x] G-02: `tools/export.sh` runs to its step 6 on a real village build (a scratch
      download; the templates may be downloaded, 1.26 GB) and passes. A mutation (a
      manifest without terrain in the exported build) fails step 6.
      - does NOT prove: that the Windows build starts (no Windows in a container).
- [x] G-03: the mutation above fails the gate; the scoped entry passes it.
      - does NOT prove: that no other global entry hides a real error. Two remain, each
        scoped by its `user://test_` path.
- [x] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that anything renders or looks right.

## Forbidden

A version bump; a change to the terrain rule or to the fixtures' expected bytes; switching
GUT's error tracking off.

## Findings (executor writes)

Executor: an Opus agent of the one M2 session (arc M2's run mode, RULINGS 2026-09-25), in
its own worktree and branch, 2026-09-25. Implementation commit `2cf5660`, chained on a
green gate. Nothing was pushed or synced; the design session merges the branch.

1. **Base.** The worktree was made at `63816ac` (the M1 close), which does not hold this
   brief. Its branch was fast-forwarded to `8a713b5` (the M2 planning commit that holds
   the brief, its pinning test and the second fixture) before any work. No other branch
   or worktree was touched.
2. **The gates, each with its evidence** (the boxes above are ticked from these).
   - Pinned copy: `cmp docs/briefs/pinning/M2-02/game/tests/test_terrain_loader_nw.gd
     game/tests/test_terrain_loader_nw.gd`: identical after the copy, before the
     implementation commit and before this one.
   - T-02: L, L2 and L3 each fail `test_terrain_loader_nw.gd`, and only it (item 5). The
     loader passed the pinned test unchanged on the first run, so `terrain_loader.gd` is
     untouched.
   - G-02: `tools/export.sh` ran to step 6 on the real village and passed, twice (item 4);
     the X1 mutation (the exported build without its heights) fails step 6 (item 5).
   - G-03: G2 fails the gate (item 5); unmutated, the scoped entry excepts the two lines
     `test_world_config_unbuilt.gd` provokes and the gate passes (next line).
   - Standard gate: `tools/gate.sh > gate-M2-02.log && git commit …` for `2cf5660`: exit
     0, `== gate: all steps passed`. pytest 367 passed, 3 deselected; GUT 16 scripts, 76
     tests, 1726 asserts, `---- All tests passed! ----`; gdlint and gdformat clean (22
     files). 65 `ERROR` lines, all excepted: 44 `WorldConfig: user://test_` and 19
     `TerrainGrid: user://test_` (the two global entries), 2 `WorldConfig: not read from a
     manifest` inside `test_world_config_unbuilt.gd` (the scoped entry). Before this
     brief: 15 scripts, 69 tests, 1641 asserts (brain.md §4); with only the pinned test
     added: 16, 75, 1720.
3. **What changed, per finding.**
   - T-02 and G-01: the pinned test only; its `test_the_clay_look_is_set` is G-01's test.
     The `height_offset_m` uniform stays unproved (the pinned test's does-NOT-prove line).
   - G-02: `tools/export.sh` step 4 captures Godot's output, prints it without ANSI
     colours, and fails on any `^(ERROR|SCRIPT ERROR)` line, naming it, then on a non-zero
     exit, then on a missing file. Step 6 is new; the header says what it requires. The
     live `test_release_settings.gd` pins both presets' `include_filter` and
     `exclude_filter` exactly.
   - G-03: `tools/gate.sh` reads the allowlist into global texts and scoped entries and
     scans with one `awk` program instead of `grep -a -E … | grep -a -v -F -f`. The entry
     is now `WorldConfig: not read from a manifest @
     res://tests/test_world_config_unbuilt.gd # it provokes the unbuilt-config refusal on
     purpose, and only it may`.
   - G-04: the GUT step takes GUT's last line starting with `---- `, trims trailing
     whitespace, compares it with `---- All tests passed! ----` and names the line found.
   - G-05: the live version test (`test_main_scene_terrain.gd`) and its twin with no
     terrain (`test_main_scene.gd`, the same Label-only loop; lesson 9) look at every
     `Control` whose `text` is a String outside `UI/PauseMenu`, and count what they find,
     so neither loop can be empty unnoticed.
   - G-06: `game/credits/godot-cpp-LICENSE.txt` (item 6), shown after Terrain3D's licence
     under `godot-cpp (compiled into Terrain3D's library)`. `main.gd`'s
     `_terrain3d_licence()` became `_licence(path)` for both files, with the same
     `push_error` and sentence when a file cannot be read. Both include filters add
     `credits/godot-cpp-LICENSE.txt`. The new `test_the_credits_carry_godot_cpp_after_terrain3d`
     finds the heading, the copyright line, the whole file after the heading, its place
     after Terrain3D's licence, and the file's SHA-256.
   - G-07: `tools/shot.sh`'s header and usage (item 8).
4. **The real run (G-02).**
   - `python -m mattini terrain --raw <the six verified tiles>`: 7.6 s; `village.f32`
     96'040'004 bytes, SHA-256
     `b6334c1fdc992f0576bc59efd51484db2178cbe399ad46512a4bf510abb9411a`, SPEC §8's value.
   - `tools/export.sh`, first run: exit 0 in 73 s. The templates were missing and were
     downloaded once: 1'255'918'323 bytes, the pinned SHA-256 passed, the seven files
     installed in `~/.local/share/godot/export_templates/4.6.3.stable/`. No `ERROR` line
     in either export. Step 5:

     | File | Bytes | MiB |
     |---|---|---|
     | `build/linux/libterrain.linux.release.x86_64.so` | 3'251'016 | 3.10 |
     | `build/linux/mattini.pck` | 96'125'524 | 91.67 |
     | `build/linux/mattini.x86_64` | 71'075'864 | 67.78 |
     | `build/windows/libterrain.windows.release.x86_64.dll` | 3'549'184 | 3.38 |
     | `build/windows/mattini.exe` | 104'659'456 | 99.81 |
     | `build/windows/mattini.pck` | 96'125'524 | 91.67 |

     Step 6 printed `expecting: mattini 0.1.0: terrain village loaded, 4001 x 6001
     vertices at 0.5 m`; the build printed Terrain3D's deprecation `WARNING`, Godot's
     banner and that line; then `started: …`.
   - The same on the committed head `2cf5660`: exit 0 in 22 s (templates installed), the
     same sizes and line. The two `.pck` files are identical (SHA-256 `2ed16aad…0100`);
     each export logged 65 `Storing File` lines, `res://credits/godot-cpp-LICENSE.txt`
     among them.
   - The `.pck` grew by 1'416 bytes (0.1.0: 96'124'108), leaving 8'732'076 bytes under
     GitHub's 104'857'600 (D16).
   - A headless start by hand with `XDG_DATA_HOME` in a scratch folder: 5.3 s, and Godot
     wrote its log under that folder (`godot/app_userdata/mattini/logs`).
5. **Mutation runs**, one per run, each undone with `git apply -R` of its saved diff (for a
   new scratch file the same, plus removing the `.uid` Godot wrote for it); `git status`
   showed only the brief's changes after each. Gate runs are the full `tools/gate.sh`;
   export runs are `tools/export.sh` on the real village.

   | Run | Mutation | Result | Owner-visible harm it reproduces |
   |---|---|---|---|
   | L | `terrain_loader.gd`: `import_images(…, corner / s, …)` (the position in vertices) | gate exit 1 at `gut`, 58 s: 4 failing tests, all in `test_terrain_loader_nw.gd`: regions `(-1,-1) (-1,0) (0,-1) (0,0)` for `(-2,-2) … (-1,-1)`, all 17 vertices NaN, holes and regions wrong; 1692/1726 asserts | a village 2 km off or missing, with no error (M1 R1 T-02) |
   | L2 | `first` rounded with `int()` for `floori()` | exit 1 at `gut`, 53 s: 3 failing tests, all in `test_terrain_loader_nw.gd`: regions `[(-1,-1)]` only, 9 vertices NaN, 6 holes wrong; 1710/1726 | a village with its northern kilometre missing, no error |
   | L3 | `region_vertices := 2048` | exit 1 at `gut`, 53 s: 3 failing tests, all in `test_terrain_loader_nw.gd`: `[2048] expected to equal [512]: 1024 m regions at 2 m`, regions `(-1,-1) … (0,0)`, all 17 vertices NaN and holes, regions where none should be; 1686/1726. The first fixture's tests (0.5 m) pass, as the review found | the owner's switch to 1 or 2 m moves or cuts the village |
   | C1 | `material.show_checkered = false` deleted | exit 1 at `gut`, 53 s: `test_the_clay_look_is_set`: `the checkerboard debug view is off`; 1725/1726 | a checkerboard village (M1 R1 G-01, its L1) |
   | C2 | the two `shader_override` lines deleted | exit 1 at `gut`, 55 s: `the override shader is on`, `an override shader is set` (NULL); 1723/1725 | a black village (G-01, its L2) |
   | G2 | new `test_scratch_unbuilt.gd`: `before_all()` runs `WorldConfig.new().to_local(…)`, plus one passing test | exit 1 at `gut`, 55 s, although GUT printed `---- All tests passed! ----` (17 scripts, 77 tests): `== gate: error lines in the output: ERROR: WorldConfig: not read from a manifest (use WorldConfig.from_manifest)`, the line right after GUT's `res://tests/test_scratch_unbuilt.gd`, backtrace `before_all (res://tests/test_scratch_unbuilt.gd:7)`; the unbuilt test's own two lines stayed excepted | NaN positions from a hand-built WorldConfig in a loader's setup, gate green (G-03) |
   | G2z (mine) | new `test_world_config_unbuilt_a.gd`: no test, the same `before_all()`; GUT runs it right after `test_world_config_unbuilt.gd` | exit 1 at `gut`, 56 s, the same line named. It printed after the unbuilt test's `3/3 passed.` and before the next script's line, with no line of its own: GUT prints no path for a script with no test (measured here; `gut.gd:784-786`) | the same, from a helper script |
   | G2z + S (mine) | G2z, and the gate's `passed.` rule deleted (a scope ends only at the next script's line) | **exit 0**, 56 s, `== gate: all steps passed` | why the scope ends at `passed.` (item 7) |
   | R (mine) | the entry scoped to `res://tests/test_world_config_unbuilt_gone.gd` | exit 1 at `godot import`, 22 s: `gate allowlist entry scoped to a test script that does not exist: …` | an entry whose script was renamed away |
   | G3 | new `test_scratch_pass_line.gd`: one test prints `---- All tests passed! ----`, one is pending | exit 1 at `gut`, 53 s: `== gate: GUT's last '---- ' line is not '---- All tests passed! ----': ---- 1 pending/risky tests. ----` (the printed line was log line 298, GUT's 903) | a pending test passing the gate (G-04) |
   | V2 | `main.gd` adds a `RichTextLabel` reading `mattini <version>` to `UI`, mouse ignored | exit 1 at `gut`, 54 s: 2 failing tests: `…/Main/UI/@RichTextLabel@124 shows no version` (`test_the_version_shows_only_in_the_pause_menu`) and the no-terrain twin; 1726/1728 | the version on screen against the owner's choice (G-05) |
   | N (mine) | `main.gd`: the godot-cpp `append_array` line deleted | exit 1 at `gut`, 55 s: `test_the_credits_carry_godot_cpp_after_terrain3d`: heading and copyright line not found, `the whole file after the heading`, `[-1] expected to be > than [87418]`; 1722/1726 | a shared build without godot-cpp's notice (D17) |
   | X1 | both include filters `assets/generated/*.json, …` (the review's X1) | `tools/export.sh` exit 1 at step 6, the `.pck` 85'432 bytes: `export: the Linux build printed error lines: ERROR: TerrainGrid: res://assets/generated/manifest.json: the heights file res://assets/generated/terrain/village.f32 is missing; python -m mattini terrain rebuilds it`. The gate with X1: exit 1 at `gut`, 54 s, `… include filter, exactly` for both presets | a release that shows the owner only the error panel (G-02) |
   | X2 (mine) | `credits/godot-cpp-LICENSE.txt` dropped from the Linux include filter | exit 1 at step 6 although the startup line printed: `ERROR: Main: cannot read res://credits/godot-cpp-LICENSE.txt (File not found)` | a build whose credits lack a licence |
   | X3 (mine) | `GODOT` set to a wrapper that runs Godot and, for `--export-release`, also prints `ERROR: Scratch: an error printed during the export` (exit 0, files written) | exit 1 at step 4, Linux preset: `export: Godot's export of Linux printed error lines: ERROR: Scratch: …` | an export that printed errors and passed (M1-06 Findings 9) |

   - does NOT prove: that these are the only wrong twins; X3's line is simulated, not a
     real export error.
6. **godot-cpp's notice (G-06), its source.** The prompt named Terrain3D's tag `v1.0.2`;
   the repository has no such tag, only `v1.0.2-rc1` and `v1.0.2-stable` (tag object
   `4b4c4117`, commit `0077405b52e353c5e5dc3a094e7ede49833ba6fe`, "Bump version to
   1.0.2", read with `git clone --branch v1.0.2-stable`). Its `godot-cpp` submodule is
   commit **`6388e26dd8a42071f65f764a3ef3d9523dda3d6e`** ("Merge pull request #1745 from
   dsnopek/4.4-cherrypicks-1", 2025-03-18, on godot-cpp's `4.4` branch, contained in tag
   `godot-4.4.1-stable`), which Terrain3D's `SConstruct:7` builds. Its `LICENSE.md` is
   blob `eb446fe72ce5c705f70413394200f10f67a123cd`, 1'093 bytes, SHA-256
   `26a5b210d90760156ce886267ce9df235787dcc6cebfd7ecd95ef5b6fdcc95bf` (the same bytes at
   `godot-4.4.1-stable`), vendored unchanged as `game/credits/godot-cpp-LICENSE.txt`
   (`git hash-object` gives the same blob). Its first line is the Markdown heading
   `# MIT License`, which the credits show as it is, between the heading and the
   copyright line.
7. **For design: where a scoped entry's window ends (G-03).** The brief gives the start
   (GUT's line naming the script, before its tests) and "only while that script runs".
   Ending the window only at the next script's line lets a script with no test borrow the
   previous script's entry: GUT prints no path for it but still runs its `before_all` and
   `after_all` (G2z + S passed the gate). So the window also ends at that script's own
   `<n>/<m> passed.` line, which GUT prints after `after_all` whenever the script made an
   assert (a script that made none has only risky tests and fails the gate anyway), and
   at `= Run Summary`, after which GUT names failing scripts again. Lines between a
   script's `passed.` line and the next path (a freed node's error, say) are excepted by
   no scoped entry: they fail closed. Reversible; the alternative is the heading-only
   reading, with G2z's escape. An inner class's line (`res://tests/x.gd.Inner`) ends the
   file's window and matches no entry, since an entry names a file.
8. **G-07, measured** (`tools/shot.sh`, Xvfb and llvmpipe). A manifest with `terrain`
   null and the views `refused;refused_pause,pause`: exit 0, both JPEGs written, the
   first showing the error panel with TerrainGrid's refusal and the two commands. A
   missing manifest in an existing folder, view `missing`: exit 0, the panel with
   WorldConfig's `cannot read the manifest (File not found)`. The refused manifest with a
   six-field view: exit 1, `shot: view over: the scene has no terrain (see its error
   panel)`. The second fixture with a six-field view: exit 0 (a clay patch with a contour
   line; a Compatibility render, evidence only). A manifest in a folder that does not
   exist stops at `realpath` before Godot starts (exit 1): the header says the folder must
   exist; the behaviour is unchanged. With no arguments it prints the two usage lines and
   exits 2.
9. **Choices inside the brief's scope** (reversible):
   - A scope is accepted only as `res://tests/*.gd` naming an existing file under `game/`;
     anything else after ` @ ` is refused. The last ` @ ` of an entry separates its text
     from its scope.
   - The scan is one `awk` program (`mawk` here; Git Bash ships `gawk`), which reads a NUL
     byte as any other byte. A harness that extracts the gate's three allowlist functions
     checked 13 cases: the live list's parse, seven refusals, the scoped window (before any
     script, another script, after `passed.`, a script with no test, an inner class, a
     repeated path, after the summary), the other steps ignoring scoped entries, a line
     with a NUL byte, and empty output.
   - `export.sh` step 6: killed after `START_TIMEOUT_S=300` s (`timeout --kill-after=10`);
     on another system than Linux it fails, naming it, rather than skipping; the expected
     line comes from the pipeline's Python reading `game/project.godot`'s `[application]
     config/version` and the manifest, the spacing formatted as `main.gd`'s `_number`; it
     requires the line exactly (`grep -x -F`), exit 0 and no error line, and checks the
     error lines first so that a failing run names them. Step 4 does the same order.
   - The credits test pins the vendored file's SHA-256, so an edit to it fails the gate.
   - The G-05 loops read `control.get("text")` and keep Strings: a control without the
     property (a `Panel`) is skipped, any class with one (`Button`, `LineEdit`,
     `TextEdit`) is included.
10. **Out-of-scope touches:** none. The new test's `.uid` is under `game/tests/`.
    `pipeline/tests/test_repo_tracked.py` lists no file of this brief and was not
    changed; M2-01's T-07 rewrites it by exclusion over `game/`, which will cover
    `game/credits/`.
11. **Follow-up candidates** (for design; none built):
    - CLAUDE.md's gate paragraph ("unless GUT prints `---- All tests passed! ----`";
      benign lines "excepted only in `tools/gate_allowlist.txt`") is still true; it could
      name the last `---- ` line and the scoped entries. brain.md H9 describes the scans'
      `grep -a`; the gate's Godot scans now use `awk` (the export's still use `grep -a`).
    - `docs/RELEASE.md` §C's "by hand until `tools/export.sh` does it" can go (design edits
      it at the close, per the brief).
    - On Windows (Git Bash) `tools/export.sh` now fails at step 6 after exporting; if the
      owner ever exports there, design may want step 6 to start the Windows build instead.
    - The credits show godot-cpp's `# MIT License` line as Markdown source (item 6).
    - Not tried: an `exclude_filter` that drops data (the pinned exact filters now fail on
      any change); a real `ERROR` during an export (X3 simulates one); step 6 on a system
      other than Linux.
