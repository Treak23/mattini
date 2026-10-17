# Brief: M4-10 — The main scene: the clock, the sky and the keys
Status: OPEN

Written in the design realm; executed by one fresh builder session under
`docs/roles/BUILD.md`. Lane I of wave 2, after wave 1 has landed and been integrated
(`docs/briefs/M4-plan.md`); lane H (M4-09) runs at the same time and shares no file.

## Goal

The game the owner starts runs on Zermatt's clock.

- **The clock:** the game starts at the photo's moment (6 September 2023, 13:40 CEST) and runs
  at 1×. Six keys move the time by 15 minutes or the date by a day, change the speed (1×, 60×,
  600×, stopped) or set the computer's clock. A label at the bottom left says the time and the
  speed for 4 s after a key, and always while the pause screen is open.
- **The sky:** every frame the sun and the moon stand where SkyClock (M4-04) puts them for the
  clock's time at the manifest's `sky` block, turned to the scene through the world config, and
  SkyRig (M4-05) lights the scene from them: M3's fixed sun, its procedural sky and its exposure
  0.54 are gone.
- **The data:** the far mountains (SurroundingsGrid and SurroundingsLoader, M4-07) and the
  photo's capture mask (CaptureShadowGrid into TerrainLoader, M4-06) are read and built; their
  refusals and the sky block's are on the error panel with their commands; in an exported build
  the missing data packs (M4-08) are too.
- **The pause screen:** the frame rate is capped at 15 while it is open; the controls list the
  time keys; the credits carry swissALTIRegio's source text whole, the sources of the sun's and
  the moon's formulas, and the star catalogue's citation when the stars are built.
- **The export:** `tools/export.sh` requires the nine blocks and two more startup lines, after
  the roofs': the far mountains' heights and the capture mask.

Measured with design's throwaway in an integration rehearsal of the whole arc (every brief's pins
and a throwaway of each, in one scratch clone): the standard gate passes, render step included.

## Read first, in order

1. `CLAUDE.md` (Hard Rules 2, 3, 4); `brain.md` H2, H3, H4, H8, H9 (`--check-only`), H12
   (software Forward+), H21, H25, H26, H28.
2. `docs/briefs/sketches/m4-design.md` §0, §4, §6, §7, §9 (this brief), §10; SPEC §13 rows 41 to
   45; `docs/briefs/M4-plan.md` (the integration notes, the review plan's placement lens).
3. The wave-1 briefs this one wires, their Decisions and Findings: M4-04 (`SkyClock`), M4-05
   (`SkyRig`, section S), M4-06 (`CaptureShadowGrid`, `TerrainLoader`'s fifth argument, risk 3 of
   its render step), M4-07 (`SurroundingsGrid`, `SurroundingsLoader`, decision 4), M4-08
   (`ReleaseBuild`, `DataPacks.missing_pack_errors`, the census), and M4-09 decision 2 (the sky
   block's shape).
4. `docs/briefs/M3-14-the-main-scene.md` (the analogue: how the main scene reads, refuses, prints
   and credits).
5. `game/scripts/main.gd`, `game/main.tscn`, `game/project.godot`, `tools/export.sh`;
   `game/tests/test_main_scene*.gd`, `test_scene_placement.gd`, `complete_world.gd`,
   `render/render_photo.gd`; `pipeline/tests/fake_tools.py`, `test_export_startup_lines.py`.
6. The pinned tests: `docs/briefs/pinning/M4-10/`.

## Decisions already made

1. **The sun's place: `SkySite`** (`game/scripts/sky/sky_site.gd`, `class_name SkySite`,
   `extends RefCounted`; the manifest's `sky` block, M4-09 decision 2).
   - `static func from_manifest(path: String, world: WorldConfig) -> SkySite`: null after one
     `push_error("SkySite: <path>: <problem>")`; `func _read(path, world) -> String` returns the
     problem without logging it (the pinned test calls it). Properties `area`, `latitude_deg`,
     `longitude_deg`, `true_to_grid_deg` (float).
   - It refuses, in this order: no WorldConfig; a manifest that cannot be read or is not an
     object; a null block: `the sun's place has not been written: run python -m mattini sky`; a
     block that is not an object; a `world_sha256` that is not text or not the manifest's
     (naming `python -m mattini sky`); a WorldConfig not read from this manifest
     (`BuildingChunks._check_world`: any axes are accepted, the directions go through the world
     config); a key set other than exactly {area, latitude_deg, longitude_deg, true_to_grid_deg,
     world_sha256}; an area that is not one of the manifest's world areas; a latitude, longitude
     or convergence that is not a finite number (an int is a number, a bool is not) or larger in
     size than 90, 180 and 10. Every compare typed (H26); every refusal but the world's names
     `python -m mattini sky`.
2. **The clock** (`main.gd`).
   - `var time_unix := SkyClock.START_UNIX` (Unix seconds UTC, public: the tests and a probe set
     it); each `_process(delta)` adds `delta × SPEEDS[speed]` unless the pause screen is open;
     `const SPEEDS := [1.0, 60.0, 600.0, 0.0]`, starting at 1×.
   - The six InputMap actions in `game/project.godot`, after `pause`, each one physical key in
     the form of the existing actions: `time_earlier` Comma (44), `time_later` Period (46),
     `day_earlier` BracketLeft (91), `day_later` BracketRight (93), `time_speed` T (84),
     `time_now` N (78). In `_unhandled_input`, after the pause action: ∓900 s, ∓86 400 s, the
     next speed (1×, 60×, 600×, stopped, 1×…), `Time.get_unix_time_from_system()` (the speed
     unchanged). The four moving keys repeat when held (`is_action_pressed(action, true)`);
     speed and now do not. While the pause screen is open the time keys do nothing.
   - `func clock_text() -> String`: `"<SkyClock.local_text(time_unix)> · <speed>"`, the speed
     `1×`, `60×`, `600×` (main's `_number` and `×`) or `stopped`: `6 Sep 2023 13:40 CEST · 1×`.
   - `UI/Clock`, a Label after `UI/PauseMenu` (drawn over it), anchored bottom left (48 px from
     the left, from −56 to −24 px), white with a black outline, hidden at the start; shown for
     `CLOCK_SHOWN_S` 4 s of real time after a time key (the countdown runs while stopped) and
     always while the pause screen is open. The pause screen's Resume and Quit buttons move up
     40 px (top −112, bottom −72) and the Controls and Credits labels' bottoms to −136, so the
     label meets neither button (pinned by rectangle).
   - `toggle_pause()`: opening sets `Engine.max_fps = 15`, closing sets it back to
     `ProjectSettings.get_setting("application/run/max_fps")` (60, M4-08); `_exit_tree` sets it
     back too, so a scene freed while paused leaves no cap (measured: without it every later test
     runs at 15 fps, and `test_m4_08_project_settings`' `Engine.max_fps == 60` fails by order).
   - The pause screen's `CONTROLS` gain, after `fly_look` and before `pause`: "the time 15
     minutes earlier", "the time 15 minutes later", "the date one day earlier", "the date one day
     later", "the time's speed: 1×, 60×, 600×, stopped", "the time and date now, this computer's
     clock" (headless: `Comma: …`, `Period: …`, `BracketLeft: …`, `BracketRight: …`, `T: …`,
     `N: …`).
3. **The sky** (m4-design §9; Tier 1).
   - `main.tscn`: the ProceduralSkyMaterial and its Sky removed; the Environment keeps
     background 2, ambient source 3, contribution 0.25, Filmic, its exposure 0.7 (the rig sets it
     every frame); a new `Moon` DirectionalLight3D after `Sun` (hidden, energy 0, colour (0.8,
     0.85, 1), shadows on, `sky_mode = 1`); `Sun` as M3's.
   - `_create_sky()`, once the readers have run: `SkyRig.create($Sun, $Moon, environment,
     frame, latitude, stars)`. **The frame is the true-north frame at the site**:
     `Basis(_bearing(ttg + 90), _bearing(ttg), _up)` with `ttg` the block's `true_to_grid_deg`
     (true north lies at grid azimuth `ttg`), because the rig uses its frame's north only for
     the stars' pole (M4-05 decision 9); with the grid frame the pole stands 0.23° off true
     north. Without a world config the owner's axes stand in (so the placeholder has a
     direction; nothing else is built then).
   - `_place_sky()`, from `_ready` and every `_process` and time key: `sun = SkyClock.sun(t, lat,
     lon)`, `moon = SkyClock.moon(t, lat, lon)`; each direction `_direction(azimuth +
     true_to_grid_deg, elevation)` = `_bearing(A)·cos e + _up·sin e`, `_bearing` and `_up`
     measured through WorldConfig as M3's sun was; `rig.apply(to_sun, to_moon, moon.z,
     SkyClock.sidereal_deg(t, lon))`. M3's `SUN_*` constants and `_place_sun` are deleted.
   - **Tier 1, measured with SkyClock** (M4-04's throwaway, which meets its vectors): at the
     start, at the village's site (46.0196233 N, 7.7485397 E, convergence −0.2258), the sun's
     true azimuth is 184.8759°, so the light stands at grid azimuth **184.6501°** and elevation
     **50.3355°** (the review plan's 184.66°/50.33° are within its 0.05°; m4-design §0 NOAA/SPA:
     184.9° − 0.226°, 50.3°). Pinned to 184.65° and 50.34° ± 0.05° on the complete world, whose
     sky block carries the village's values as test data, and exactly (1e-4) against SkyClock at
     the block's site; a turned world (x = +n, z = +e) and a convergence of +5° in two more tests.
   - **Without a sky block** the sun stands still at a labelled placeholder,
     `FALLBACK_SUN_AZIMUTH_GRID_DEG` 184.67 and `FALLBACK_SUN_ELEVATION_DEG` 50.1 (the flight's
     mean sun, `config/shadows.json`), the moon below the horizon (`apply(still, −still, 0, 0)`);
     the clock and its label still run.
   - **The stars** (M4-05 section S) are built exactly when `res://sky/stars.csv` is there (the
     same switch as M4-05: the section's files): `SkyRig.star_image` is called by name on the
     loaded script (`load("res://scripts/sky/sky_rig.gd").star_image(...)`, so `main.gd` parses
     without section S) and its Image kept in a `static var`, built once per process (4096 ×
     2048 texels; every main-scene test would otherwise rebuild it).
4. **Reading and building.** After BuildingRoofs, `main.gd` reads `SurroundingsGrid`,
   `CaptureShadowGrid` and `SkySite`, each through `_caught`, then creates the sky.
   - `TerrainLoader.create(grid, self, photo, surfaces, mask)`; without a photo the loader
     ignores the mask (M4-06), which is still read (one cause, one panel entry, as M3-14 read
     the surfaces without the photo).
   - `SurroundingsLoader.create(far, self)`, moved before `UI`: "Surroundings" at the scene's
     origin, unturned (the scene's root is).
   - What cannot be shown, after M3's six, in this order: `the mountains' shadows`, `the
     photo's softened shadows`, `the sun's and the moon's course`. Their fixes, `RUN` as M3's:
     SURROUNDINGS_FIX download regio, surroundings; SHADOWS_FIX download surface, shadows;
     SKY_FIX sky. A refused manifest names all nine.
5. **The panel in an exported build.** `_show_error` takes the exported flag from
   `ReleaseBuild.is_exported()` (M4-08's one home), not `OS.has_feature("template")`. Before the
   manifest is read, in an exported build only, main asks `DataPacks.missing_pack_errors(<the
   executable's folder>)` through `const DATA_PACKS := preload("res://scripts/data_packs.gd")`
   (the autoload has no `class_name`, and `--check-only`, the gate's parse step, does not know
   autoloads: naming `DataPacks` there failed the gate, measured). `static func
   error_text(refusals, path, exported, packs := PackedStringArray())`: the messages follow the
   first line, after a blank line; with no refusal the first line is `mattini cannot find every
   data pack.` and the fix `To fix it, ` + EXPORTED_FIX. The panel opens when either is there.
   Main logs nothing more (DataPacks logged them at start).
6. **The far mountains' and the mask's file messages move onto `ReleaseBuild.file_hint`**
   (M4-07 decision 4): SurroundingsGrid's one `rebuild` line and CaptureShadowGrid's two (its
   PNG and its decoding) become `ReleaseBuild.file_hint(<COMMAND>)`; nothing else in the readers
   changes. M4-08's census then has no exception (decision 9's replacement). (The integration
   rehearsal found CaptureShadowGrid spelling `"; %s rebuilds it"` after M4-06, as SurfaceGrid
   did, so M4-08's census failed on wave 1 until it named `shadow_grid.gd` beside
   `surroundings_grid.gd`; design's fix of M4-08's pin is a separate commit.)
7. **The startup lines,** printed after M3's six, one per block its reader accepted (the sky
   prints none):
   ```
   mattini <v>: surroundings <area> loaded, <columns> x <rows> heights at <spacing> m
   mattini <v>: shadows <area> loaded, <columns> x <rows> cells at <cell> m
   ```
   The real village (measured by M4-02 and M4-03 and their rehearsals): `surroundings village
   loaded, 421 x 431 heights at 100 m`, `shadows village loaded, 4000 x 6000 cells at 0.5 m`.
8. **The credits.** "Data" gains the far mountains' line `swissaltiregio <edition>,
   <attribution>` (the block's `source.attribution`: for the real village swissALTIRegio's
   source text from `config/datasets.json`, whole, m4-design §1a) and the mask's `swisssurface3d
   <first>-<last edition>, <attribution>` (the same line as the trees': listed once). After
   "Placeholders" a heading "Sky" and, exactly:
   `Sun: NOAA's solar position calculations (Meeus, Astronomical Algorithms), https://gml.noaa.gov/grad/solcalc/calcdetails.html`
   `Moon: Paul Schlyter, How to compute planetary positions, https://stjarnhimlen.se/comp/ppcomp.html`
   and, only when `res://sky/stars.csv` is there, M4-05 decision 6's citation `Stars: The Bright
   Star Catalogue, 5th Revised Ed. (Hoffleit, D., Warren, W. H. Jr., 1991), NASA/ADC, CDS V/50.`
   (main.gd's `SUN_NOTE`, `MOON_NOTE`, `STARS_NOTE`). The switch is an argument,
   `_credits_text(datasets: PackedStringArray, stars: bool)`, `_ready` passing whether the star
   image was built, so the pinned test reads both forms whichever option the tree holds.
   Godot's sky shader is MIT and already in
   the credits (Godot's licence).
9. **Pinned replacements of other briefs' files** (each changes only what this brief makes
   fail, measured with design's throwaway; each says so in a "Since brief M4-10" paragraph):
   - `game/tests/test_main_scene_light.gd` (M3-14's): the whole file, decision 3's tests;
   - `test_main_scene_data.gd` (M3-14's): the two lines, the credits' list, two credit tests;
   - `test_main_scene_refusals.gd` (M3-14's): a refused manifest names all nine;
   - `test_scene_placement.gd` (M3-14's): the three new readers' refusals of the buildings
     fixture absorbed;
   - `test_m4_08_release_hints.gd` (M4-08's): the census without exceptions, and the far
     mountains' and the mask's sites tested in and out of an export;
   - `game/tests/complete_world.gd` (M4-06's): a `surroundings` block (the shared fixture's
     description and heights, its box `SURROUNDINGS_BOX` around this world's area, its `cut_box`
     the area, its NaN corners around the terrain) and a `sky` block (`SKY`: config/sky.json's
     village values under this world's area and hash), test data said so;
   - `game/tests/render/render_photo.gd` (M4-06's, M4-06 risk 3): both views set `shadow_lift`
     to 1. Measured: with the main scene handing the terrain the mask, `RENDER photo` fell to
     correlation 0.6584 (FAIL); with the override 0.9752. The clock is not stopped: the sun moves
     about 0.004° a second between the two captures, and every check passed;
   - `pipeline/tests/fake_tools.py` and `test_export_startup_lines.py` (M4-08's): nine blocks,
     two more lines, their cases.
10. **Your own edits:** `game/tests/test_main_scene.gd`, the not-JSON case's first line naming
    all nine (`… the trees, the roof colours, the mountains' shadows, the photo's softened
    shadows and the sun's and the moon's course.`) and its message. `tools/export.sh`: `BLOCKS`
    gains `surroundings|download regio|surroundings`, `shadows|download surface|shadows`,
    `sky|sky`; `expected_startup_lines` prints the two lines; step 6 expects 8 + the packs'
    lines (the throwaway first kept `6 +` and failed `test_export_checks.py`, measured); the
    header comment, step 2's names ("all nine blocks") and the function's comment say so.
11. **The gate:** three lines appended at the end of `tools/gate_allowlist.txt`:
    ```
    SurroundingsGrid: user://test_ @ res://tests/test_m4_10_refusals.gd # its missing far mountains are refused on purpose (brief M4-10)
    CaptureShadowGrid: user://test_ @ res://tests/test_m4_10_refusals.gd # its damaged capture mask is refused on purpose (brief M4-10)
    SkySite: user://test_ @ res://tests/test_m4_10_refusals.gd # its missing and stale sun's places are refused on purpose (brief M4-10)
    ```
12. **Measured with design's throwaway** (the integration rehearsal, 2026-10-17): every pin
    passed on the first full run after two fixes of the throwaway (decision 5's preload,
    decision 10's count); the standard gate on the whole arc: pytest 2'608 passed, GUT 61
    scripts, 393 tests, 16'571 asserts, `RENDER photo` 0.9752, `RENDER classes` agreement 70'039
    of 70'180, bank 0.9957, `RENDER lift` 1.0000 and 3.060, `RENDER trees` 0.8533 (0.9387 under
    M3's light: the trees' check now reads the rig's sun; its floor is 0.6). The mutations of
    the gate list below each failed a named pinned test (two survived a first version of the
    pins and were closed: the exported flag, now also read with a refusal; the catalogue's
    switch, now called both ways through `_credits_text(datasets, stars)`).
    The real village in the same clone: every step from the command line (surroundings 69.8 s,
    596 MiB; shadows 181.2 s, 537 MiB; sky 1.1 s), the manifest 327'265 bytes, `a0e2ec92…`
    (M4-09's value); `tools/export.sh` exit 0 in 71 s: the started build printed the two pack
    lines and the eight lines in order (`surroundings village loaded, 421 x 431 heights at 100
    m`, `shadows village loaded, 4000 x 6000 cells at 0.5 m`), no ERROR line; `mattini.pck`
    23'034'132 bytes (0.3.0: 21'280'420; `sky/stars.csv` ships in it), `mattini.exe` still the
    largest file, 104'659'456.
    **Software Forward+ on the real village** (lavapipe, 1280 × 720, design's probe, 21 min):
    - **MSAA 4× (M4-08) crashed it**: signal 11 at the first frame, with and without
      "Surroundings"; with `root.msaa_3d = 0` set by the probe it ran. The small complete test
      world with MSAA 4× renders 30 frames in the same renderer. Not known to be lavapipe's
      alone: the owner's GPU is the test (the plan's release list names MSAA). The probe of gates
      3 and 4 sets `root.msaa_3d = Viewport.MSAA_DISABLED` before it adds the scene, and says so.
    - The far mountains' shadow at the village centre (E 2'624'000, N 1'096'500), a camera 300 m
      over it looking straight down, the mean linear luminance of the centre 64 × 64 px: 17:30
      CEST 0.0897 (0.0896 without "Surroundings"): lit; 17:45 **0.0033** (0.0768 without): in the
      far mountains' shadow. The same with a 10° view from 300 m (0.0023 against 0.0666) and from
      1000 m (0.0023 against 0.0724): M4-05's risk 4d did not show here.
    - At 08:00 and 18:00 the start view's village lies in the mountains' shadow with the slopes
      above it lit; at 22:00 the sky shows the stars and the ground is dark but visible
      (exposure 4.0). The physical sky reads grey-blue by day in this renderer.

## Scope — files you may touch

- `game/scripts/main.gd`, `game/main.tscn` (decisions 2, 3), `game/project.godot` (the six
  actions only), `game/scripts/sky/sky_site.gd` and its `.uid` (new);
- `game/scripts/terrain/surroundings_grid.gd` and `shadow_grid.gd`: the hint lines only
  (decision 6);
- `tools/export.sh` (decision 10), `tools/gate_allowlist.txt` (the three lines);
- `game/tests/test_main_scene.gd` (decision 10);
- the pinned copies (`cp -r docs/briefs/pinning/M4-10/. .`): new `game/tests/test_m4_10_clock.gd`,
  `test_m4_10_refusals.gd`, `test_m4_10_sky_site.gd` (with `.uid`); the replacements of decision
  9;
- your own new tests `test_m4_10_*`; `docs/briefs/shots/M4-10-*.jpg`; this brief.

Not the pipeline (`pipeline/mattini/`), `tests/shared/`, `config/`, `docs/RELEASE.md` or any
`pipeline/tests/` file but the two named (lane H's, M4-09, at the same time; checked: the two
Scopes share no file); not SkyClock, SkyRig, the shaders, the loaders or any reader beyond
decision 6; not `game/export_presets.cfg`.

## Depends on

Wave 1 landed and integrated (M4-01 to M4-08). Lane H (M4-09) runs at the same time: no pinned
file of this brief reads M4-09's fixture manifests (the cases are the complete test world's),
so the pins pass before or after its landing; the real village needs its commands (gate 4).

## Done when (gates)

- [ ] The pinned copies are in place (`cp -r docs/briefs/pinning/M4-10/. .`) and stay
      byte-identical (`cmp`).
      - does NOT prove: that they are the right tests.
- [ ] Mutations, each applied alone, each failing a named pinned test, recorded with the harm it
      reproduces (design's throwaway failed each as named):
      - the convergence's sign flipped, or left out (the sun 0.45° or 0.23° off):
        `test_main_scene_light.gd` (4 tests);
      - the owner's axes hard-coded in `_direction` (any other world mirrored or turned):
        `test_the_light_turns_with_the_world_config`;
      - latitude and longitude swapped: four light tests;
      - the moon at the sun's azimuth: `test_the_moon_and_the_night_follow_the_clock`;
      - the rig's frame at grid north (the stars' pole 0.23° off): `test_the_stars_pole_stands_at_true_north`;
      - the start 2 h late (local time as UTC): the clock tests and the Tier 1 test;
      - the clock running while paused; no cap while paused; the cap not given back by
        `_exit_tree`; the label never timing out; the speeds in another order; time_earlier
        moving later; time keys working while paused; a held key not repeating:
        `test_m4_10_clock.gd`, each by name;
      - the shadows' line before the surroundings': `test_the_startup_lines_name_every_block_in_order`;
      - the mask not handed to the terrain; "Surroundings" not built or under the camera; the
        packs not on the panel; the exported flag from the OS; the moon shown without a sky
        block: `test_m4_10_refusals.gd`, each by name;
      - the catalogue cited without its table, or never; the far mountains not credited; the
        mask's editions written as a list: `test_main_scene_data.gd`;
      - SurroundingsGrid or CaptureShadowGrid spelling its own hint: `test_m4_08_release_hints.gd`;
      - SkySite's untyped world compare, no area check, no range check, no world check:
        `test_m4_10_sky_site.gd`;
      - `render_photo.gd` without the lift's override: `RENDER photo` FAIL;
      - `export.sh` without the sky block, with `6 +`, or the two lines swapped:
        `test_export_startup_lines.py`, `test_export_checks.py`.
      - does NOT prove: what a GPU draws; that these are the only ways to break it (lesson 4).
- [ ] Software screenshots in **Forward+ on lavapipe** (H12; `tools/shot.sh` is Compatibility
      and has no time: a SceneTree probe in scratch, never committed, that sets
      `root.msaa_3d = Viewport.MSAA_DISABLED` (decision 12: MSAA 4× crashed lavapipe on the real
      village), opens `main.tscn` on the real village, stops its `_process`, sets `time_unix`,
      calls `_place_sky()`, places the camera, waits 40 frames and saves): the start
      view at 13:40, the same view at 08:00, 18:00 and 22:00 CEST on 6 September 2023, and the
      river at 30 m at 13:40; under `docs/briefs/shots/M4-10-*.jpg`, named in Findings. Evidence,
      not a gate.
      - does NOT prove: the owner's GPU, colours or look.
- [ ] **The real village, exported:** M4-09's commands and manifest (`a0e2ec92…`, 327'265 bytes)
      in a scratch `git clone` (H22): if lane H has landed when your pins pass, rebase on it and
      build the village; otherwise say so in Findings and the orchestrator's after-wave-2 step
      runs it. `tools/export.sh` exit 0; the started Linux build prints the two pack lines and the
      eight lines in order, with `surroundings village loaded, 421 x 431 heights at 100 m` and
      `shadows village loaded, 4000 x 6000 cells at 0.5 m`, and no ERROR line; every file under
      100 MiB.
      - does NOT prove: the Windows build; what the panel shows without the packs (the release
        template ignores `--script`).
- [ ] **The far mountains' shadow, a recorded measurement** (software Forward+, lavapipe, the
      real village, the probe of gate 3): on 2023-09-06 at 17:30 CEST the village centre is lit
      and at 17:45 it is in the far mountains' shadow (design's horizon at the centre: the sun
      leaves it at 17:41; SkyClock: grid azimuth 252.25°, elevation 24.76° at 17:30; 255.26°,
      22.25° at 17:45). Record the view (a camera over the centre looking down, and the start
      view), the luminance of the ground at the centre at both times, and the same with
      "Surroundings" hidden (lit at both: the 2 × 3 km terrain alone does not shade it then).
      Also M4-05 risk 4d: a view from 300 m and more looking straight down with a narrow field of
      view: is the far shadow there? Record what you see.
      - does NOT prove: the owner's GPU; the minute (the frame's shadow map resolution at 20 km).
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`, render step included.
      - does NOT prove: that it renders or looks right.

## Forbidden

A version bump; changing SkyClock, SkyRig, a shader, a loader, or a reader beyond decision 6;
auto exposure; `Engine.time_scale` or `get_tree().paused` for the clock; another time zone rule
than SkyClock's; reading the system clock anywhere but `time_now`; editing a pinned file,
`tests/shared/` or `config/`; an allowlist entry beyond the three; a new dependency.

## Findings (executor writes)
