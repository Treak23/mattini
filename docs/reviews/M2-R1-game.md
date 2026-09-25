# Review M2 R1 — lens `game`, game and tools (Tier 2)

- **Range:** `git diff 63816ac..88678e2 -- . ':!game/addons' ':!pipeline/uv.lock'`; head reviewed `88678e2`.
- **Date:** 2026-09-25.
- **How:** one Opus agent of the M2 session in its own worktree (the owner's run mode, RULINGS 2026-09-25); every P0 to P2 finding then put to three skeptic agents told to refute it. Reproduced here from the agents' structured reports, unedited except for layout.
- **Standard gate at the head:** exit 0.

## Findings

### M2-R1-G-01 · P2 · The buildings' look is untested: unshaded walls, back faces drawn and near-black roofs pass the full gate (M1-R1-G-01's class, one layer out)

- **Where:** game/materials/building_walls.tres:1-8 and building_roofs.tres:1-8 (the look: shading and culling are left at their defaults, never pinned); game/tests/test_building_loader.gd:109-113 (the only test that reads the materials checks resource_path and nothing else); game/scripts/buildings/building_loader.gd:31-32,89 (loads and assigns them)
- **Claim:** Brief M2-05 and SPEC §10 decide the look: lit and flat-shaded, back faces culled, roofs darker than walls. No test reads any material property. M1's review found the same class for the terrain (G-01, P2). M2-02 fixed that instance, and the new materials repeat the pattern (lesson 9). The seam gate's line 'does NOT prove: that the buildings render or look right' covers settings that can be read headless, as M2-02's clay-look test does.
- **Proof:** Mutation M: `cull_mode = 2` and `shading_mode = 0` (unshaded) added to building_walls.tres, and the roofs' albedo set to Color(0.1, 0.1, 0.1). The full `tools/gate.sh` exited 0 with 98/98 tests and 2692 asserts, ending `== gate: all steps passed` (scratchpad review-R1/G/gate-mut-M.log). The mutation was undone with `git apply -R` of mut-M.diff. A software screenshot of the real village with M (`tools/shot.sh … close,2623800,1096440,25,90,20`, shots-M/close.jpg) shows flat white walls with no facet shading and black roofs. The unmutated shot of the same view shows shaded white buildings. `grep` finds no test that mentions cull_mode, shading_mode or albedo.
- **Harm:** The owner starts a build whose buildings are unlit cut-outs, drawn inside out where culling is off, or black-roofed, and the gate was green. M3 (surfaces) and M4 (sun) are the next arcs likely to touch these materials.
- **Fix:** Design's call. Pin the structure, not the tunable numbers. On a mesh the loader built, read each surface's material and check shading_mode per-pixel, cull_mode back, transparency off and no albedo texture. Optionally check that the roofs' albedo is darker than the walls'. Leave the exact colours to the owner's tuning (SPEC §10).
- **Verification:** Upheld by 3 of 3 skeptics (grades P2, P2, P2).

  - Skeptic 1: holds, P2. The finding holds at P2. I checked each part of it at 88678e2 and could not refute it.

1. **The look is decided.** SPEC §10 (M2's game) and brief M2-05 set it: flat-shaded facets, matte, casting shadows in the sun, back faces culled, roofs a shade darker than walls.

2. **The materials pin none of it.** Each .tres sets only resource_name, albedo_color, metallic, metallic_specular and roughness. cull_mode and shading_mode are left at their defaults (back-face culling and per-pixel shading).

3. **No test reads a material property.** `git grep` over game/tests and tools at 88678e2 finds no cull, shading_mode or albedo. The one line that reads a material, test_building_loader.gd:109-113, only checks that it exists and asserts its resource_path. So editing the .tres itself cannot fail any test.

4. **The line references are right.** building_loader.gd lines 31-32 load the two materials and line 89 assigns them. In Godot's BaseMaterial3D enums, cull_mode 2 is CULL_DISABLED and shading_mode 0 is SHADING_MODE_UNSHADED, so the mutation means what the finding says.

5. **The proof checks out.** In the reviewer's scratchpad:
   - mut-M.diff is exactly the mutation described.
   - gate-mut-M.log ends with 20 scripts, 98/98 tests, 2692 asserts, `---- All tests passed! ----` and `== gate: all steps passed`.
   - shots-M/close.jpg shows flat white walls with no facet shading and near-black roofs. The unmutated shots/close.jpg of the same view shows shaded buildings.

6. **It is the same class as an accepted finding.** M1-R1-G-01 (P2) was the terrain's look settings with no test reading them. M2-02 fixed that instance by reading the settings headless on the loaded object. The buildings' materials repeat the pattern one layer out, which is what lesson 9 warns about. The board (ROADMAP) does not list this as known.

**Refutation attempts, and why they fail:**
- *The look was scoped out on purpose.* The pinned test's header says it does not prove "the look itself (the owner's to judge)", and the .tres files are the owner's tuning surface. But that line covers the tunable numbers. Culling and lit shading are structure the SPEC decides, and the same reasoning did not stop G-01 being accepted.
- *Albedo is a tunable number.* True, but it is only one of the three mutations, and the proposed fix already leaves colours unpinned (the roofs-darker check is optional).
- *Nothing is wrong today.* True: the unmutated render is correct. That is why this is P2 (a weak gate, harm only after a future change such as M3's surfaces or M4's sun) and not P1. It is not P3, because the harm is buildings drawn unlit, inside out or black-roofed with the gate green, which is more than cosmetic.

Evidence is in /tmp/claude-0/-home-user-mattini/bea2be16-f780-5dd6-9dd8-5304b8b207c1/scratchpad/review-R1/G/ (mut-M.diff, gate-mut-M.log, shots-M/close.jpg, shots/close.jpg).
  - Skeptic 2: holds, P2. The finding holds. I could not refute its core; two parts of it are overstated.

What I checked at 88678e2:
- Both `.tres` files set only resource_name, albedo_color, metallic, metallic_specular and roughness. shading_mode, cull_mode and transparency are left at Godot's defaults and never pinned.
- The only test that touches the materials is `test_building_loader.gd`'s `test_roofs_and_walls_by_the_normal`. It checks assert_not_null plus resource_path and nothing else.
- `git grep` for shading_mode, cull_mode or albedo in `game/tests` finds nothing. It also finds no roughness check, and the only clay hit is the terrain's `test_the_clay_look_is_set`.
- Brief M2-05 and SPEC §10 do decide the structure: "flat-shaded facets, casting shadows in the fixed sun, back faces culled".
- The proof artefacts exist in the scratchpad:
  - `mut-M.diff` adds `cull_mode = 2` and `shading_mode = 0` to the walls, and sets the roofs' albedo to 0.1.
  - `gate-mut-M.log` ends `== gate: all steps passed`, with 98/98 tests, 2692 asserts and `---- All tests passed! ----`.
  - `shots-M/close.jpg` shows unlit flat-white walls and near-black roofs.
- In Godot 4, `shading_mode = 0` is SHADING_MODE_UNSHADED and `cull_mode = 2` is CULL_DISABLED, so the mutation is what it claims to be.

Why P2 stands:
- It fits the given definition: a weak gate against a future change (M3 or M4 editing these materials).
- It matches the project's own precedent. M1-R1-G-01 was a P2 for the same class on the terrain, and RULINGS kept the P2 grades.
- The seam gate's "does NOT prove: look right" line discloses the gap but does not close it. Lesson 10 treats that line as a list of what remains to check.
- The settings can be read headless, just as M2-02's clay test reads the terrain's settings.

What is overstated (these narrow the finding but do not refute it):
1. **The culling harm is wrong for the mutation used.** The harm says buildings are "drawn inside out where culling is off". But cull_mode = 2 draws both sides. A closed mesh seen from outside looks the same, because the depth test keeps the outer faces. Only CULL_FRONT (1) would draw a building inside out. Culling off costs overdraw and changes what you see from inside a building, which the collision-free camera can reach. The screenshot's visible harm comes from the unshaded walls and the dark roof albedo, not from culling. The fix, which pins cull_mode to back, still covers both cases.
2. **The near-black roofs are outside the class.** The roof colour is a tuned number. SPEC §10 leaves colours to the owner's tuning, and M1-R1-G-01 explicitly declined to pin tuned numbers. The finding's own optional check, "roofs darker than walls", would pass with 0.1 roofs. So one third of the mutation M is not a defect the proposed fix catches, and "near-black roofs" in the title overstates the class.
3. **The same layer on the terrain is also unguarded.** The clay test checks only the shader's resource_path, so a `render_mode unshaded` in `terrain_clay.gdshader` would pass as well. This extends the class rather than refuting it.

What remains is a real, reproducible P2 at the low end: an unlit or back-face-wrong building material passes the full gate.
  - Skeptic 3: holds, P2. I could not refute the finding. The claim and the proof both hold at 88678e2:
- Both .tres files set only albedo, metallic, specular and roughness. Culling, shading and transparency are left at StandardMaterial3D's defaults.
- The only test that reads the materials, test_roofs_and_walls_by_the_normal in game/tests/test_building_loader.gd, checks resource_path and nothing else.
- `git grep` for cull, shading and albedo finds nothing in game/tests.
- The M2-05 brief and SPEC §10 both decide the look in writing: flat-shaded, back faces culled, roofs darker than walls.
- M2-02's test_the_clay_look_is_set shows that settings like these can be read headless. It is the precedent for fixing M1-R1-G-01, which was graded P2 and whose grade a ruling kept.

I checked the reviewer's own artifacts in the scratchpad:
- mut-M.diff is exactly the mutation described: walls get `cull_mode = 2` and `shading_mode = 0`, roofs get `albedo_color = Color(0.1, 0.1, 0.1, 1)`.
- gate-mut-M.log ends with 98/98 tests, 2692 asserts, `---- All tests passed! ----` and `== gate: all steps passed`.
- shots-M/close.jpg shows flat, unlit white walls and black roofs.

Three points weaken the finding, but none refutes it:
1. It is weaker than M1's G-01. There, the engine defaults were wrong, so deleting one line broke the look. Here the defaults are right, so the look breaks only if someone actively writes a non-default value into the .tres, for example an agent in M3 or M4, or a stray editor toggle.
2. The harm line says the buildings are "drawn inside out where culling is off". That overstates it: with culling disabled and the winding correct, the depth test still hides the back faces. Only cull_mode = 1 (cull front faces) turns the buildings inside out.
3. The proposed fix leaves colours to the owner. Its optional "roofs darker than walls" check would still pass roofs at 0.1, so the "near-black roofs" part of the title is not closed by the fix.

This fits P2 as defined ("a future change or a weak gate"), not P3, because it concerns the look of the game's main deliverable, not wording. It sits at the low end of P2.

### M2-R1-G-02 · P3 · With the terrain refused, the buildings load but the camera stays at the local origin, 1.6 km below them: the owner sees only sky and the panel

- **Where:** game/scripts/main.gd:10-11 (the header comment says what can be shown still is, 'and the other way round'); main.gd:157-163 (buildings built without a terrain); main.gd:180-184 (_start_view and height_at are set only in _show_terrain); game/main.tscn:34 (Camera with no transform)
- **Claim:** When TerrainGrid refuses and BuildingChunks accepts, main.gd builds the Buildings node and prints 'buildings village loaded'. Nothing then places the camera, so it stays at local (0,0,0), which is LV95 E 2'623'000 N 1'096'000 at 0 m, about 1'600 m below the village, facing north. The header's claim is true of the scene tree but not of what the owner sees.
- **Proof:** A probe script (scratch panel_probe.gd) on the real village with terrain null printed `terrain=false buildings=true panel_visible=true` and `camera at (0.0, 0.0, 0.0)`. With both blocks present the camera is at (1000.0, 1754.064, -500.0). `tools/shot.sh <terrain_null manifest> … start` exited 0 after the build printed `mattini 0.1.0: buildings village loaded, 1486 buildings in 6 chunks, 178910 triangles`. The shot (shots-tnull/start.jpg) shows the error panel over an empty sky and horizon, with no building in view.
- **Harm:** The panel is honest. But the 'buildings still shown' mode, which the tests assert (test_main_scene.gd:233, test_main_scene_terrain.gd:109), gives the owner nothing to see without flying 1.6 km up, about 53 s at the default 30 m/s.
- **Fix:** Either start the view over the buildings' bounds when there is no terrain (the manifest's lv95_box through WorldConfig), or drop 'and the other way round' from main.gd's header and say that the camera starts at the origin.
- **Verification:** P3: not put to the skeptics.

### M2-R1-G-03 · P3 · export.sh step 1 checks the manifest before step 2 rewrites it: a block that step 2 drops is caught only at step 6, by a Python traceback, after both exports

- **Where:** tools/export.sh:130-142 (step 1 has_block, then step 2 `mattini manifest`); tools/export.sh:114-118 (expected_startup_lines subscripts manifest["buildings"] unguarded; the terrain's line at :111-112 likewise)
- **Claim:** Step 1 reads the manifest as it was on disk. Step 2 then rewrites it, and writes buildings null when no buildings are built in the folder (manifest.py docstring). Steps 3-5 export both presets. Step 6 then crashes in its inline Python and says only 'no startup lines to expect (see above)', naming no command.
- **Proof:** Mutation E5: game/assets/generated/buildings/village.json moved away, the manifest still holding its buildings block. `tools/export.sh` passed steps 1-5 and wrote both builds, with a .pck of 99'402'028 bytes and no buildings in the manifest. Step 6 printed `TypeError: 'NoneType' object is not subscriptable` at `chunks = buildings["chunks"]`, then `export: no startup lines to expect (see above)`, exit 1. Afterwards the manifest read `buildings: None`. Both files were restored and `cmp` found them identical.
- **Harm:** The run fails closed, but late: two exports (plus a 1.26 GB template download on a fresh machine) and a traceback instead of step 1's message with the two commands. The same holds for the terrain block.
- **Fix:** Run step 1's block checks after step 2, on the rewritten manifest, or run them in both places.
- **Verification:** P3: not put to the skeptics.

### M2-R1-G-04 · P3 · The scoped allowlist window depends on GUT's per-script 'passed.' line, and the gate pins Godot's version but not GUT's: that format change fails open

- **Where:** tools/gate.sh:131-134 (the window ends at `^[0-9]+/[0-9]+ passed\.$`); tools/gate.sh:15-16,195-210 (only Godot 4.6.3 is required); game/addons/gut/plugin.cfg:6 (version 9.6.1, pinned by no check); gut.gd:873-875
- **Claim:** The gate's own header says its scans are only as good as the output formats they were measured on, and so it requires Godot 4.6.3. GUT's formats carry the scoped window too. A heading change fails closed. A change to the 'passed.' line re-opens the escape that M2-02 Findings 7 closed (G2z + S): a test-less script's before_all error falls into the previous script's window.
- **Proof:** GS2: a Godot wrapper that indents GUT's `res://tests/…` headings. The gate exited 1 at `gut`, naming all 15 scoped lines (fail closed). GS3: a wrapper that drops the final '.' from `<n>/<m> passed.`, plus a scratch test-less `test_building_chunks_b.gd` whose before_all calls `BuildingChunks.from_manifest("user://test_scratch_b/manifest.json", null)`. The gate exited 0, `== gate: all steps passed`. Its line `ERROR: BuildingChunks: user://test_scratch_b/…` (log line 317, after `10/10 passed` and before test_building_chunks_indices.gd's heading) was excepted by test_building_chunks.gd's scoped entry. Unmutated, GS1 (the same script) fails the gate at `gut`, naming that line. Each run was undone and git status was clean.
- **Harm:** After a vendored GUT upgrade, a helper script's refusal in before_all would pass the gate. It needs a future change.
- **Fix:** Require GUT 9.6.1 as the gate requires Godot 4.6.3: check the `GUT version:  9.6.1` line or addons/gut/plugin.cfg. Or fail the GUT step when no `passed.` line was seen for a script heading.
- **Verification:** P3: not put to the skeptics.

### M2-R1-G-05 · P3 · The allowlist refuses only an empty text: a one-word global entry such as 'ERROR' silences every scan in every Godot step (M0-R1-G-01's class)

- **Where:** tools/gate.sh:91-97 (only an empty or blank text is refused); tools/gate.sh:138 (index($0, text) on every scanned line)
- **Claim:** Every line the scans select begins with ERROR, SCRIPT ERROR or [ERROR], so a global entry whose text is a common prefix works like the empty text the gate refuses.
- **Proof:** Mutation GA: `ERROR # review mutation: one word` appended to tools/gate_allowlist.txt, plus the scratch test-less script from GS1. The gate exited 0, `== gate: all steps passed`, with `ERROR: BuildingChunks: user://test_scratch_b/…` in the log (line 317). Undone and git status clean.
- **Harm:** One careless allowlist line turns off the error scans, and only the Findings review stands between it and a green gate. Today's six entries are all specific, so nothing is hidden now.
- **Fix:** Refuse texts shorter than a floor (say 12 characters) or equal to a scan prefix (ERROR, SCRIPT ERROR, [ERROR]), or require a global entry to name its reader ('<Name>: ').
- **Verification:** P3: not put to the skeptics.

### M2-R1-G-06 · P3 · The export filters ship more than the game reads: unlisted stale files under assets/generated/ and the screenshot tool

- **Where:** game/export_presets.cfg:7-8,22-23 (include `assets/generated/*`, exclude `tests/*, addons/gut/*`), pinned exactly by game/tests/test_release_settings.gd:17-20,59-61
- **Claim:** Every file in assets/generated/ ships, including chunk files no manifest lists. res://tools/shot.gd ships in every release too.
- **Proof:** A 1 MiB stale `game/assets/generated/buildings/2622-1095.bin` beside the real chunks: `tools/export.sh` exited 0, logged `Storing File: res://assets/generated/buildings/2622-1095.bin` for both presets, and the .pck grew from 99'407'628 to 100'456'284 bytes (removed afterwards; the manifest was unchanged). The unmutated export log stores `res://tools/shot.gd.remap` and `res://tools/shot.gdc`. This reproduces M2-04's check residue on the board.
- **Harm:** Wasted size, with 5.2 MiB left under GitHub's limit: an earlier build's leftovers can push the .pck over, and step 5 then fails visibly. A dev tool ships to players. No licence harm, since the data is swisstopo's.
- **Fix:** Either have `mattini buildings` remove chunk files that its block does not list, or narrow the include filter to the manifest's files. Add `tools/*` to the exclude filter and its pin.
- **Verification:** P3: not put to the skeptics.

### M2-R1-G-07 · P3 · tools/shot.sh's header says a six-field view fails on a refused manifest; with only the buildings refused it succeeds

- **Where:** tools/shot.sh:16-18 (and :13-14, 'the scene's start view when it comes first'); game/tools/shot.gd:17-19
- **Claim:** Since M2-05 a manifest can be refused in part. With the buildings refused and the terrain accepted, a six-field view works and captures the panel over the terrain. With the terrain refused, the 'name' view is not the start view but the origin (G-02).
- **Proof:** `tools/shot.sh <buildings_null manifest> … "over,2623906,1096422,60,315,35"` exited 0 and wrote over.jpg after `ERROR: BuildingChunks: …: no buildings have been built`.
- **Harm:** A builder reading the header expects a failure that does not come. Wording only.
- **Fix:** Say that a six-field view fails when the terrain is refused, and that with the buildings refused the view is taken with the panel over the terrain.
- **Verification:** P3: not put to the skeptics.

## Checked and clean

- Baseline: tools/gate.sh at 88678e2, exit 0 in 90 s: pytest 662 passed; GUT 20 scripts, 98 tests, 2692 asserts, `---- All tests passed! ----`; 79 ERROR lines, all excepted (13 BuildingChunks in the three scoped scripts, 2 unbuilt WorldConfig in test_world_config_unbuilt.gd, the rest under the two global user://test_ entries). Log: scratchpad/review-R1-game-tools.log.
- Real village: `mattini terrain --raw` wrote village.f32 with SPEC's b6334c1f… in 7.5 s. `mattini buildings --raw` built 1486 buildings in 6 chunks (92594 vertices, 178910 triangles, 3258048 bytes), matching config/buildings.json. Main scene headless (`godot --headless --path game --quit-after 300`): exit 0, the deprecation WARNING and both startup lines, `terrain village loaded, 4001 x 6001 vertices at 0.5 m` and `buildings village loaded, 1486 buildings in 6 chunks, 178910 triangles`, no ERROR.
- Error panel, every combination, probed on the real village (panel_probe.gd). Refused manifest (not JSON or missing): 'the terrain and the buildings' plus the manifest command. Terrain null: 'the terrain', 'To fix it', both terrain commands; buildings shown. Buildings null, no buildings key (a 0.1.0 manifest) or stale world_sha256: 'the buildings', 'To fix it', both buildings commands; terrain shown. Both null, or both files missing: 'the terrain and the buildings', each refusal with 'To fix the terrain' / 'To fix the buildings'. The credits' Data lines follow what is loaded, the terrain's first, or 'No generated data is loaded…'.
- Credits: godot-cpp's notice follows Terrain3D's licence. The vendored file matches upstream: SHA-256 26a5b210… equals raw.githubusercontent LICENSE.md at 6388e26d, and `git clone --branch v1.0.2-stable` of Terrain3D shows godot-cpp submodule 6388e26dd8a42071f65f764a3ef3d9523dda3d6e.
- T-02: the review's three loader mutations each fail test_terrain_loader_nw.gd and only it (test_terrain_loader.gd 5/5 each). L (import at corner / s): 4 failing tests, regions (-1,-1)… for (-2,-2)…, vertices NaN. L2 (int() for floori()): 3 failing, regions [(-1,-1)] only. L3 (region_vertices 2048): 3 failing, `[2048] expected to equal [512]`. Each was undone with git apply -R.
- BuildingLoader winding: W (triangles as (a, b, c)) fails test_normals_face_out_and_front_faces_are_godot_s (1 of 10 tests across test_building_loader.gd and test_main_scene_buildings.gd).
- export.sh on the real village: exit 0 in 23 s, 80 Storing File lines per preset, both .pck identical (325e7b99…, 99'407'628 bytes, 5'449'972 under the limit). Step 6 found both lines. A by-hand start of build/linux/mattini.x86_64 --headless --quit-after 300 (XDG_DATA_HOME in scratch) exited 0 with both lines and no ERROR.
- export.sh mutations. E1 (manifest terrain null) and E2 (buildings null) fail at step 1, naming the commands. E3 (exclude assets/generated/buildings/*) fails at step 6: `ERROR: BuildingChunks: … 2623-1095.bin is missing`. E4 (exclude assets/generated/terrain/*) fails at step 6: `ERROR: TerrainGrid: … village.f32 is missing`.
- Scoped allowlist. GS1: a test-less script's BuildingChunks: user://test_ refusal between two scoped scripts fails the gate at gut, naming it; the window closes at the 'passed.' line. GS2: a heading-format change fails closed. The parse refuses a scope that is not an existing res://tests/*.gd, and an entry with ' @ ' but a non-test scope. The two global user://test_ entries hide nothing today: every before_all that calls a reader reads a repo fixture path, not user://test_.
- Software screenshots (tools/shot.sh, Compatibility on llvmpipe, evidence only): start, church and street are byte-identical to the committed docs/briefs/shots/M2-05-*.jpg. They and an extra close view show white buildings standing on the clay terrain, casting shadows, with the church spire where the data puts it.
- The pck size difference from M2-05's Findings (+160 bytes) is uid_cache.bin listing the three pinned test scripts added at 86d764c. That is deterministic, not a leak.
- git status clean at the end; every mutation was undone with git apply -R of its saved diff (scratch test scripts removed with their .uid); generated data and build/ removed from the worktree.

## Notes

Lens: game and tools (Tier 2), M2-02 and M2-05, at 88678e2 (worktree checked out detached, confirmed with git log). No P0, no P1. One P2: the buildings' look is not tested, M1-R1-G-01's class one layer out. Six P3s.

Known items on the board, graded:
- "Gate fooled by a test that prints the pass line and quits": NOT reproduced here. My variant (test_aaa_quit.gd prints the line, then get_tree().quit(0) and awaits) failed the gate at gut on `ERROR: 3 resources still in use at exit`. Ungraded, since the check's variant was not re-run.
- "Scoped allowlist line ends on Windows": unmeasurable here (no Windows). .gitattributes forces LF on the allowlist, so only Godot's own output could carry CR.
- "Credits show godot-cpp's `# MIT License` raw": P3, read at game/credits/godot-cpp-LICENSE.txt:1 and main.gd:365.
- "Earlier build's chunk files ship": P3, reproduced, folded into G-06.

The M2-05 'does NOT prove: that the buildings render or look right' line hides G-01: the materials' structural settings can be read headless, as M2-02's clay-look test reads the terrain's.

Does NOT prove:
- the Forward+ look (screenshots are Compatibility/llvmpipe);
- the Windows build starting;
- the gate's awk on gawk (Git Bash);
- that G-04's GUT format change will ever occur.

Scratch evidence is under /tmp/claude-0/-home-user-mattini/bea2be16-f780-5dd6-9dd8-5304b8b207c1/scratchpad/review-R1/G/:
- logs: gate-*.log, export-*.log, main-headless.log, shot-*.log;
- saved diffs: mut-*.diff;
- screenshots: shots/, shots-M/, shots-tnull/, shots-bnull/;
- probe: panel_probe.gd, cases/.

The baseline gate log is scratchpad/review-R1-game-tools.log.
