# Review M1 R1 — lens `game` (Tier 2)

- **Lens:** `game`. It covers `tools/gate.sh` and `tools/gate_allowlist.txt`; the main scene
  (`game/main.tscn`, `game/scripts/main.gd`), the free-fly camera, the pause screen, the
  credits and the error panel; the clay shader; `tools/shot.sh` and `game/tools/shot.gd`;
  Terrain3D's vendoring, checked against its 1.0.2 release; `game/export_presets.cfg` and
  `tools/export.sh`; licence and attribution (Hard Rule 3); line endings; and the seams
  between briefs M1-02↔M1-05, M1-04↔M1-05 and M1-05↔M1-06.
- **Range:** `git diff e83a36a..6fb378d -- . ':!game/addons' ':!pipeline/uv.lock'`, plus
  `game/addons/terrain_3d/` as vendored.
- **Head reviewed:** `6fb378d`. `main` was at `303ba66` when this was written. Every change
  since `6fb378d` is under `docs/` (the board and the terrain lens's report).
- **Date:** 2026-09-25.
- **How:**
  - All gate runs and mutations were made in one detached worktree at `6fb378d` in the
    session's scratch folder, with Godot's user data in a scratch folder
    (`XDG_DATA_HOME`). One build ran at a time.
  - Each mutation was saved as a diff, applied, run through the full `tools/gate.sh`, then
    undone with `git apply -R`. `git status` was clean after each run. For a new scratch
    test file, Godot also writes a `.uid` file beside it; that byproduct was deleted after
    the run, by name.
  - The one real export ran in a second fresh worktree at `6fb378d`, with no `game/.godot`
    folder and its own Godot data folder. There I ran `download terrain`, then `terrain`,
    then `tools/export.sh` once (it downloaded the templates).
  - Later export measurements in that worktree ran step 4's Godot command and its file
    checks by hand, with the templates already installed. They never ran the script
    again.
  - Software screenshots used `tools/shot.sh` (Compatibility renderer under Xvfb).
  - Both worktrees have been removed. The main checkout was never used for a run, and
    nothing under `build/` or `data/` entered git.
  - Worked around: the exported release build ignores `--script`, so a probe cannot run
    inside it. I read the credits of the real village in the project instead, and checked
    the `.pck` bytes directly.
- **Baseline** in the fresh worktree: `tools/gate.sh` exit 0 in 63 s, including creating
  the Python environment. pytest 367 passed and 3 were deselected. GUT ran 15 scripts,
  69 tests and 1641 asserts, all passed. The log holds 65 `ERROR` lines, each one excepted
  by the allowlist. `git status` was clean afterwards.

**Result:** no P0 and no P1. The gate, the camera, the pause screen, the credits and the
export do what their briefs say. I measured it: a real export from a fresh checkout starts
and loads the village. Its `.pck` carries `© swisstopo` and Terrain3D's licence. The real
village's credits open with `swissalti3d 2024, © swisstopo`. The vendored Terrain3D is
byte-identical to its 1.0.2 release. A clone made with Windows' line-ending setting gets
the same bytes.

I found three P2s. Each is a harm the owner would see that no check can catch:
- **The terrain's look is untested.** If the checkerboard debug view is left on, or the
  clay shader is never set, the full gate still passes. The village would then show as a
  checkerboard, or solid black (G-01).
- **Nothing runs the exported build.** An export that lost its heights file passes the
  gate, `tools/export.sh` and the size check. The build then shows only an error panel
  (G-02).
- **One allowlist entry is global.** It hides the unbuilt-WorldConfig error everywhere,
  not only in the test that provokes it on purpose (G-03).

There are also five P3s. Two are gate and pinned-test edges (G-04, G-05). One is a licence
notice (G-06). Two are stale texts at brief seams (G-07, G-08).

The four known items the board lists are graded at the end: three P3s, and M1-06
Findings 9 as a P2 member of G-02.

## Findings

### M1-R1-G-01 · P2 · The clay look is not tested: the checkerboard left on, or the clay shader never set, passes the full gate

- **Where:**
  - `game/scripts/terrain/terrain_loader.gd:37-40` sets the look: `show_checkered = false`
    (`:37`), `shader_override = load(CLAY_SHADER)` (`:38`),
    `shader_override_enabled = true` (`:39`) and the `height_offset_m` uniform (`:40`).
  - `game/tests/test_terrain_loader.gd:78-80` asserts collision, `free_editor_textures`
    and `world_background`, but none of the four lines above. `grep -rn -i
    "shader\|clay\|checkered" game/tests/` finds nothing.
- **Claim:** every setting that makes the terrain look like clay can be removed with the
  gate staying green. A headless run can read three of the four: the probe printed
  `show_checkered = false`, `shader_override_enabled = true` and
  `shader_override = res://shaders/terrain_clay.gdshader`.
  The uniform cannot be read headless: it reads `<null>` there, and `1000.0` under the
  software renderer (the fixture's height offset).
- **Proof** (full `tools/gate.sh`, one mutation per run, each undone):
  - `L1`: the line `material.show_checkered = false` deleted. Exit 0 in 59 s, 69/69
    tests, `== gate: all steps passed`. A software screenshot of the fixture
    (`2601016,1199979,8,45,30`) shows the terrain as a grey-and-black checkerboard. The
    unmutated control shows the light clay, with a contour line.
  - `L2`: the two `shader_override` lines deleted. Exit 0 in 59 s, 69/69 tests. The same
    view shows the terrain solid black, as brain.md H11 predicts for Terrain3D's default
    shader with no textures.
  - `L3`, the control for the shader itself: an undeclared name in `ROUGHNESS`. Exit 1 at
    `gut`: 14 failing tests, `SHADER ERROR: Unknown identifier in expression`, and the
    scan caught `ERROR: Shader compilation failed.`. So a shader that does not compile
    is caught. A shader that is never used is not.
- **Harm:** the owner starts 0.1.0, or a later version whose change touched the loader,
  and sees a checkerboard or a black village instead of clay, with the gate green. M3
  (surfaces) and M4 (sun) are the next arcs to change this material.
- **The class** (lesson 9), the look settings no test reads:
  - `show_checkered`: proved (L1).
  - `shader_override` and `shader_override_enabled`: proved (L2).
  - The `height_offset_m` uniform: no current consumer. The village's height offset is
    0 m. The fixture's is 1000 m, a whole number of 100 m, so its contours fall in the
    same places either way. That is inferred, not rendered.
  - The scene's exposure and sky colours: tuned numbers. I do not propose pinning them.
- **Fix:** design's call.
  - Add a test that reads `show_checkered`, `shader_override_enabled` and the override's
    `resource_path` on the loaded terrain. All three read back headless (measured).
  - The uniform needs a rendering run, for example a check in `tools/shot.sh`'s
    renderer, or it stays unproved.
- **Does NOT prove:**
  - the Forward+ look: the screenshots are Compatibility renders on llvmpipe (brain.md
    H12);
  - that anything is wrong today: the unmutated screenshot shows clay.

### M1-R1-G-02 · P2 · Nothing runs the exported build: an export without its terrain passes the gate, `tools/export.sh` and the size check (extends M1-06 Findings 9)

- **Where:**
  - `tools/export.sh:121-127`: step 4 accepts an export when Godot exits 0 and both files
    are non-empty.
  - `tools/export.sh:129-138`: step 5 checks sizes only.
  - `game/scripts/main.gd:142-154`: the startup line. The M1-06 brief says it exists "so
    an exported build can be checked headless", but only M1-06's Findings ever ran it.
  - `docs/RELEASE.md` §C (`:34-35`) has no line for starting the build.
  - `game/tests/test_release_settings.gd:50` checks the include filter by substring.
- **Claim:** the release chain proves that files were written, never that the game in
  them works. The export's output is not scanned (Findings 9, known). No step starts the
  exported build. The pinned preset test accepts a narrower include filter, because
  `"assets/generated/*.json"` contains the text `assets/generated/*`.
- **Proof** (mutation `X1`: both presets' `include_filter` set to
  `"assets/generated/*.json, addons/terrain_3d/LICENSE.txt"`):
  - The full `tools/gate.sh` passed: exit 0 in 56 s, 69/69 tests. The pinned preset test
    passed.
  - In the export worktree, I ran step 4's command
    (`godot --headless --path game --export-release "Linux" <abs path>`): exit 0, no
    `ERROR` line.
  - Both files were written, so step 4's check passes: the executable at 71'075'864
    bytes, the `.pck` at 84'016 bytes. The size check passes too (84 KB is under
    100 MiB).
  - The build, `mattini.x86_64 --headless --quit-after 300`, exited 0. It printed
    `ERROR: TerrainGrid: res://assets/generated/manifest.json: the heights file
    res://assets/generated/terrain/village.f32 is missing; …` and no startup line.
  - The diff was undone, and the worktree was clean.
  - M1-06 Findings 8 run a shows the same with `export.sh` itself (exit 0).
- **Harm:** a release ships to the owner and shows only the error panel, telling them to
  run pipeline commands. Everything before it was green. The close of M1 is the first
  consumer. Its export is not required to be started by anything (RELEASE.md §C), and
  M2's buildings will change what the `.pck` holds.
- **The class** ("the release trusts that files exist, not that the build works"):
  - (a) the export's output is not scanned for `ERROR`. That is Findings 9, known. My
    fresh-checkout export printed no `ERROR` line, so a scan would hold today. It would
    not catch X1, which prints none.
  - (b) the Linux build is never started by the script. Proved above.
  - (c) the pinned filter test checks by substring. Proved above.
  - (d) RELEASE.md §C has no "the build starts" line.
  - (e) the Windows build is never started anywhere, and the Windows binaries' bytes are
    checked by no test, only their existence (`test_terrain3d_vendored.gd:20-31`). This
    is known: the owner's PC (M1-06 Findings 5–7).
- **Fix:** design's call. One shape:
  - Add an `export.sh` step 6: run `build/linux/mattini.x86_64 --headless --quit-after
    300`. Require the startup line with the manifest's columns and rows, and no `ERROR`
    line. It took 6.3 s here.
  - RELEASE.md §C gains the same line.
  - Optionally, pin the include filter exactly.
- **Does NOT prove:** that the Windows build starts; that no other way of losing data from
  an export exists (an `exclude_filter` entry such as `*.f32` is another, not run).

### M1-R1-G-03 · P2 · The allowlist entry `WorldConfig: not read from a manifest` is global: an unbuilt WorldConfig used outside a test passes the gate

- **Where:**
  - `tools/gate_allowlist.txt:2`: its reason is "test_world_config_unbuilt.gd provokes
    it on purpose".
  - `tools/gate.sh:98`: `grep -a -v -F -f`, a substring match on every scanned line, in
    every Godot step.
- **Claim:** M1-02 made engine errors outside a test fail the gate (G-03), and the C-07
  guard's `push_error` exists to make a hand-built WorldConfig visible. This entry hides
  that guard's one signal wherever it is printed, not only in the test file its reason
  names. The other two entries are scoped by a path only tests use (`user://test_`).
  This one is scoped by nothing.
- **Proof** (full gate, one scratch test file each):
  - `G2`: `before_all()` runs `WorldConfig.new().to_local(2623825.13, 1096489.75,
    1617.0)`, plus one passing test. Exit 0 in 55 s, `== gate: all steps passed`. The log
    holds `ERROR: WorldConfig: not read from a manifest (use WorldConfig.from_manifest)`,
    with a backtrace to the scratch file's `before_all`, and 66 `ERROR` lines in all.
  - `G2c`, the control: `before_all()` runs `push_error("Scratch: a refusal in
    before_all")`. Exit 1 at `gut`, `error lines in the output: ERROR: Scratch: a refusal
    in before_all`, although GUT printed `All tests passed!`.
- **Harm:** unproved today: no code path reaches it. The mechanism is live where setup
  runs once per script. The loader tests build their terrain in `before_all`, and M2's
  loaders will follow that pattern. There, a WorldConfig that never read a manifest gives
  NaN positions with the gate green.
- **Fix:** design's call. Two options:
  - drop the entry and let the unbuilt tests assert their own errors. GUT's
    `assert_push_error` handles them for GUT, but the gate's scan still sees the printed
    line, so the scan needs another way to know the line is deliberate;
  - accept, and reword the reason to say the entry is global.
- **Does NOT prove:** any current code path that reaches the guard outside a test.

### M1-R1-G-04 · P3 · The GUT step's pass check reads any line, not GUT's last line as its comment says

- **Where:** `tools/gate.sh:11` says "passes only when GUT's own last line says ---- All
  tests passed! ----". `tools/gate.sh:176` greps the whole output for that line.
- **Proof:** `G3`, a scratch test that prints `---- All tests passed! ----`, plus a
  pending test in the same file. Exit 0 in 55 s, `== gate: all steps passed`. GUT's real
  last summary line was `---- 1 pending/risky tests. ----`, which CLAUDE.md says fails
  the gate.
- **Harm:** only if a test prints that exact line. No test does. It is a comment that
  claims more than the code does (Hard Rule 2).
- **Fix:** take the last line starting with `---- ` and compare that. Unambiguous, and
  one line.
- **Does NOT prove:** any realistic trigger.

### M1-R1-G-05 · P3 · The pinned "version only on the pause screen" test checks Labels and the window title only

- **Where:** `game/tests/test_main_scene_terrain.gd:152-159` looks at
  `find_children("*", "Label", …)`. A `RichTextLabel` or a `Button` is not a `Label`.
- **Proof:**
  - `V2`: `main.gd` adds a `RichTextLabel` reading `mattini 0.1.0` to `UI`, outside the
    pause menu, with the mouse ignored. Exit 0 in 55 s, 69/69 tests.
  - (`V1`, the same without ignoring the mouse, failed only because the new text caught
    the camera test's mouse motion: not this test.)
- **Harm:** a later on-screen text (a HUD, say) could show the version against the
  owner's choice (SPEC §13 row 15), with the gate green. Nothing does today.
- **Fix:** design's call: check every visible `Control` with a `text` property outside
  the menu. Same class as M0 G-08: a pinned test whose name claims more than it checks.
- **Does NOT prove:** that anything shows the version today (M1-05's run e covers the
  window title).

### M1-R1-G-06 · P3 · Terrain3D's binary contains godot-cpp, whose MIT notice the credits do not carry

- **Where:**
  - `game/scripts/main.gd:273-291` builds the credits: Godot, its components, Terrain3D.
  - `docs/RELEASE.md:17-19` names the third-party code as "Godot, Terrain3D".
- **Claim:** Terrain3D 1.0.2 is built on godot-cpp: its `SConstruct:7` reads
  `SConscript("godot-cpp/SConstruct")`, pinned as a submodule at `6388e26`. godot-cpp's
  licence is MIT, "Copyright (c) 2017-present Godot Engine contributors". Terrain3D's own
  sources carry only Terrain3D's notice (39 files, one holder).
- **Harm:** a licence reading, not a measured harm. The credits already show Godot's MIT
  notice for the same holder ("2014-present Godot Engine contributors"). Whether that
  covers godot-cpp is for design.
- **Fix:** design's call: add godot-cpp's notice, or record in RELEASE.md §A why Godot's
  covers it.
- **Does NOT prove:** that a notice is legally required.

### M1-R1-G-07 · P3 · `tools/shot.sh` still describes M1-04's tool (seam M1-04↔M1-05)

- **Where:** `tools/shot.sh:2-16`. The header reads "Software screenshots of a manifest's
  terrain (… brief M1-04)". The usage names only the six-field view.
- **Claim:** M1-05 changed `game/tools/shot.gd` under it. It now renders `main.tscn` and
  accepts the views `name` and `name,pause`, and a refused manifest now captures the
  error panel rather than failing. `shot.sh` was outside M1-05's scope, so it kept
  M1-04's words. Lesson 8: the later brief moved under the earlier one.
- **Proof:** by reading. The script's behaviour is unchanged and right: it passes the
  views through, and its check that every `<name>.jpg` was written still holds.
- **Fix:** update the header and usage lines.

### M1-R1-G-08 · P3 · `docs/RELEASE.md` §B still calls the version's place OPEN

- **Where:** `docs/RELEASE.md:24-26`: "(where: OPEN until decided, SPEC §Open decisions;
  it must be decided before the first release)". This is outside the arc's diff, but the
  close walks it.
- **Claim:** it was decided at M1 planning (SPEC §13 row 15: only on the pause screen) and
  built in M1-05.
- **Fix:** name the pause screen there. Together with G-02's §C line, RELEASE.md then
  matches what the close ships.

## Known items, graded (the board's "Decisions for the close")

- **M1-05 Findings 1 — P3.**
  - The brief's mutation (c) passes because Terrain3D looks for the camera at its first
    physics frame, not on entering the tree. The builder's run c2 (no current camera at
    that frame) fails the gate on the `Cannot find the active camera` line. So the harm is
    guarded.
  - The scene's order is right: `main.tscn` marks the camera current, and it is ready
    before `Main._ready` builds the terrain.
  - What remains is H11's wording of the timing, for design. Graded on the builder's
    recorded runs; not re-run here.
- **M1-04 Findings 1 — P3.** Two more fresh checkouts here did not abort:
  - the baseline gate, with the extension-list step;
  - the export worktree, where `tools/export.sh`'s export was the first Godot run to
    open the project (only `godot --version` ran before it), and nothing wrote
    `extension_list.cfg` first. Godot wrote the file itself; exit 0, no `Aborted`.
  - The step costs nothing. H11's first bullet claims an abort nobody has reproduced
    since, and wants the re-measure the board names.
- **M1-06 Findings 2 — P3.** A build without its heights file still says what is missing
  and names the fix. X1 (G-02) reproduces the same outcome through a filter the pinned
  test accepts. The filter is needed. What is missing is a check that the build runs
  (G-02).
- **M1-06 Findings 9 (no scan of the export's output) — P2, as member (a) of G-02.**
  - On its own it would catch little: my fresh-checkout export printed no `ERROR` line,
    and X1 prints none either.
  - Its stated risk, an export that "prints errors and still writes both files", is real
    only together with the missing run check, which is where G-02 puts the fix.

## Tier 1 territory

None found from this lens. The terrain placement and transforms were read only where the
main scene uses them: the start view and the sun through `WorldConfig`, and `shot.gd`'s
bearing.

## Checked and clean

- **Gate runs, one mutation each** (full `tools/gate.sh`, each undone; the tree was clean
  after each):

  | Run | Mutation | Exit, step | Evidence |
  |---|---|---|---|
  | baseline | none (fresh worktree) | 0 | pytest 367 passed, 3 deselected; GUT 15 scripts, 69 tests, 1641 asserts; 65 excepted `ERROR` lines |
  | L1 | `show_checkered = false` deleted | **0** | G-01 |
  | L2 | the two `shader_override` lines deleted | **0** | G-01 |
  | L3 | an undeclared name in the clay shader | 1, `gut` | 14 failing; `SHADER ERROR: Unknown identifier …`, `ERROR: Shader compilation failed.` |
  | G1 | a test that asserts nothing | 1, `gut` | `---- 1 pending/risky tests. ----`, so CLAUDE.md's "a test with no assert" claim holds |
  | G2 | an unbuilt WorldConfig in `before_all` | **0** | G-03 |
  | G2c | another `push_error` in `before_all` | 1, `gut` | the scan names it although GUT says `All tests passed!` (M0 G-03 is fixed) |
  | G3 | a printed pass line plus a pending test | **0** | G-04 |
  | X1 | include filter `assets/generated/*.json` | **0** | G-02 |
  | V1 | the version in a `RichTextLabel` outside the menu | 1, `gut` | an unrelated camera test (the label caught the mouse) |
  | V2 | V1 with the mouse ignored | **0** | G-05 |

  A zero in bold is a mutation the gate lets through.

- **The shader compiles in the gate.** The headless renderer compiles the clay shader when
  the loader tests use it (L3). That corrects the M0 round's guess that it "probably never
  compiles shaders". Its `#if CURRENT_RENDERER == RENDERER_COMPATIBILITY` block was not
  mutated.
- **Terrain3D's vendoring against its 1.0.2 release.**
  - The zip from the brief's store URL has SHA-256 `a0718502…84a2`, as pinned.
  - Every vendored file except the 20 `icons/*.svg.import` is byte-identical to the zip:
    the four binaries, `LICENSE.txt`, `README.md`, `terrain.gdextension` and its `.uid`,
    and the 20 icons.
  - The 20 `.import` files differ only by the six keys Godot 4.6.3 adds.
  - Not vendored, as the brief says: the editor plugin (`src/`, `menu/`, `tools/`,
    `utils/`, `brushes/`, `extras/`, `plugin.cfg`), the demo, and the other platforms'
    binaries.
  - The licence is MIT, 2023-2026 Cory Petkovsek, Roope Palmroos and Contributors. The
    version test asserts `get_version() == "1.0.2"` and passes.
- **The clay shader against its source.** Terrain3D's `extras/shaders/minimum.gdshader` is
  identical in the zip and at git tag `v1.0.2-stable`. `terrain_clay.gdshader` differs
  from it in exactly what its header says: the comment, the `height_offset_m` uniform and
  the albedo and roughness lines. The upstream copyright line is kept.
- **The export from a fresh checkout** (the one `tools/export.sh` run):
  - `download terrain`: 6 tiles, 6 fetches. `terrain`: `village.f32` begins `b6334c1f`,
    SPEC §8's value. The two took 14 s.
  - `tools/export.sh`: exit 0 in 73 s. It downloaded the templates, 1'255'918'323 bytes,
    which passed the pinned SHA-256 check, and installed the seven files.
  - The six files in `build/` have exactly M1-06 Findings 6's sizes. `mattini.exe` is
    104'659'456 bytes, under the limit. The export printed no `ERROR` line.
  - `mattini.x86_64 --headless --quit-after 300`: exit 0 in 6.3 s, with the deprecation
    `WARNING` and `mattini 0.1.0: terrain village loaded, 4001 x 6001 vertices at 0.5 m`.
  - The two `.pck` files are identical to each other. They differ in bytes from the
    builder's (`a4138fae…` here, `44950109…` there) at the same size. Nothing claims the
    export is byte-reproducible, and the dist commit records the `main` sha.
- **Attribution (Hard Rule 3, RELEASE §A).**
  - The exported `.pck` holds `"attribution": "© swisstopo"` twice (the manifest and the
    terrain description) and Terrain3D's licence text.
  - In the project, with the real village manifest, the pause screen's credits (a probe
    reading the scene) read `Credits / Data / swissalti3d 2024, © swisstopo`, then
    Godot's licence, its components and licences, and `Terrain3D 1.0.2` with its licence:
    1'867 lines. The version label reads `mattini 0.1.0`, and the error panel is hidden.
- **Line endings.** A clone with `core.autocrlf=true` checked out all 484 tracked files
  byte-identical to the Linux worktree. `git ls-files --eol`: 440 LF text files, 40
  binaries (the arc's `.so`, `.dll`, `.jpg` by rule; GUT's `.ttf` and `.fnt` by git's own
  detection), 4 empty files. `tools/export.sh` and `tools/shot.sh` are committed
  executable, like `tools/gate.sh`.
- **The seams.**
  - **M1-02↔M1-05:** all 65 `ERROR` lines in the baseline are deliberate refusals under
    `user://test_…` or the unbuilt-config test. The main scene's tests set
    `manifest_path`, so their refusals fall under the existing entries (no entry added).
    Every test that adds a Terrain3D in a test body absorbs H4's warning. The main
    scene's `Logger` coexists with GUT's.
  - **M1-04↔M1-05:** `TerrainLoader.create` needs its parent in the tree and a current
    camera. `main.gd` calls it from `_ready`, after the camera marked `current` in the
    scene is ready, and `shot.gd` waits one frame first. The pinned loader tests still
    build in `before_all`.
  - **M1-05↔M1-06:** the startup line prints after the start view is set. The version
    shows in the pause menu. The Windows executable keeps Godot's own file properties
    (`modify_resources=false`, by reading), so mattini's version is not there either.
    The exported build loads the village (above).
- **The session-start hook's extension-list block** writes the same line the gate writes
  (`res://addons/terrain_3d/terrain.gdextension`).
- **Pause screen and camera, by reading and the tests' runs.** Opening the pause screen
  turns the controls off and frees the mouse (`input_enabled` setter). The wheel and the
  fly keys are ignored while paused (tests). Resume gives the controls back. The error
  panel ignores the mouse (`mouse_filter = 2`), so right-drag works over it. The camera
  reads the fly keys by polling `Input`, not through the menus, so a focused button
  cannot swallow them.
- **Scripts:** `bash -n` passes on all three `tools/*.sh` (no shellcheck in the
  container).

## Does NOT prove

- **Rendering.** That anything renders or looks right in Forward+ on the owner's PC. The
  screenshots here are Compatibility renders on llvmpipe (brain.md H12), evidence of what
  is drawn, not of the look.
- **Windows.** That the Windows build starts, that `export.sh`'s Windows templates path is
  right, or that the gate behaves the same under Git Bash. Nothing ran on Windows.
- **The credits inside the exported build itself.** The release template ignores
  `--script`. The credits were read in the project from the same manifest, and the
  `.pck`'s bytes were checked separately.
- **The `height_offset_m` uniform's effect.** Only its read-back under the software
  renderer was measured; no contour was compared.
- **The Compatibility-only block of the clay shader.** Not mutated. The headless renderer
  may not compile it.
- **Other classes not tried:** an `exclude_filter` that drops data; a stale
  `village.f32.part` left in `game/assets/generated/terrain/` by an interrupted
  `terrain` run, which the include filter would ship; how the controls feel; the mouse
  after the window loses focus while looking.
- **The fixes.** Every fix above is unimplemented and unmeasured, except that G-01's two
  headless read-backs were measured.
