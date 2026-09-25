# Review M2 R1 — lens `placement`, placement (Tier 1: coordinates and determinism)

- **Range:** `git diff 63816ac..88678e2 -- . ':!game/addons' ':!pipeline/uv.lock'`; head reviewed `88678e2`.
- **Date:** 2026-09-25.
- **How:** one Opus agent of the M2 session in its own worktree (the owner's run mode, RULINGS 2026-09-25); every P0 to P2 finding then put to three skeptic agents told to refute it. Reproduced here from the agents' structured reports, unedited except for layout.
- **Standard gate at the head:** exit 0.

## Findings

### M2-R1-P-01 · P2 · Nothing gates where the Buildings node puts the meshes in the scene: every building can move 1 km off its terrain and the full gate stays green

- **Where:** game/scripts/buildings/building_loader.gd:28-39 (create); game/tests/test_building_loader.gd:52-64; game/tests/test_main_scene_buildings.gd:177-187; the claim at game/scripts/main.gd:14
- **Claim:** The seam tests stop at the reader's arrays (test_building_chunks.gd) and at the mesh-local arrays (test_building_loader.gd). No test checks the transform of the Buildings node or its MeshInstance3D children, and no test checks that the composed box in complete_world.gd stands on the terrain in the scene. main.gd:14 says 'the buildings stand where the pipeline placed them for the world config the manifest pins (Hard Rule 4)', and no test backs that at scene level. M2-05's does-NOT-prove lines leave this out.
- **Proof:** Mutation: added `buildings.position = Vector3(1000.0, 0.0, 0.0)` after building_loader.gd:30. The full tools/gate.sh then exited 0 (pytest 662 passed; GUT 20 scripts, 98/98, '---- All tests passed! ----'; '== gate: all steps passed'; log scratchpad/review-R1-placement-mut-nodeshift.log). It was undone with `git apply -R` of mut-g-nodeshift.diff and git status is clean. The startup line that tools/export.sh checks holds only counts (main.gd:203-207). Size of the harm, from the real village (seam_terrain.py): with the buildings shifted 1 km east, the ground at the centre lies between floor and roof for 1 of 1486 buildings. As placed, the same is true for 1475.
- **Harm:** A future change that positions the Buildings node or a node above it (a chunk-streaming offset, or a transform on Main in main.tscn) gives the owner a village whose buildings float or are buried away from their terrain. The build still passes every gate. This is the Hard Rule 4 harm, and the one Tier-1 step on the game side has no gate at all.
- **Fix:** Add a main-scene test on complete_world.gd's box. It should check that the Buildings node and each chunk MeshInstance3D have global_transform == Transform3D.IDENTITY. It should also check that the box's floor corner, as mesh global_transform * vertex, equals WorldConfig.to_local of its LV95 point, and that main._ground_height at the box's footprint lies between its floor and roof. Mutation-prove the test with the 1 km node shift, and add the scene transform to M2-05's does-NOT-prove enumeration.
- **Verification:** Upheld by 3 of 3 skeptics (grades P2, P2, P2).

  - Skeptic 1: holds, P2. The finding holds, and P2 is the right grade.

1. No test checks the node's position. At 88678e2, I searched every script under game/tests for position, transform, global_transform, global_position, to_global and aabb. Nothing reads the transform of the Buildings node or of its MeshInstance3D children. test_building_loader.gd:52-64 checks only the node's name, its parent, the child names and cast_shadow. test_main_scene_buildings.gd:177-187 checks only that the node exists, has one child, that child is a MeshInstance3D and no error panel shows. The file's own header (lines 15-16) passes placement to test_building_chunks.gd. That test checks the reader's arrays against WorldConfig.to_local and never looks at the scene graph.

2. I reproduced the mutation. I extracted 88678e2 with git archive into my scratchpad and added `buildings.position = Vector3(1000.0, 0.0, 0.0)` after building_loader.gd:30. I wrote the generated manifest with `python -m mattini manifest` and ran the full GUT suite: 20 scripts, 98/98 passed, '---- All tests passed! ----', exit 0. My first run failed only because the git-ignored manifest was missing, which has nothing to do with the mutation. pytest and lint do not touch this code, so the gate stays green, as the reviewer found. The main checkout was not touched and the scratch copy has been removed.

3. The other claims are correct. main.gd:14 claims the buildings stand where the pipeline placed them (Hard Rule 4) with no scene-level test behind it. The does-NOT-prove lines of M2-05's seam gate name only render/look. main._ground_height (main.gd:222) exists, so the proposed fix can be built.

Two small overstatements, neither of which refutes the finding:
- A transform on Main would move Terrain as well as Buildings. It separates them only if Terrain3D ignores its node transform, which I did not check.
- 'The one Tier-1 step on the game side has no gate at all' overstates the gap. The reader's seam is gated (mutation X fails it). What has no gate is the scene transform, which is identity by default and set by no line of code.

Why P2, not P1: no current code is wrong. Nothing sets the transform today, so the harm needs a future change: a streaming offset, or a transform set in main.tscn or the loader. That is P2 as defined ('a future change or a weak gate'). It is not P1: no normal use hits a defect, and no existing gate over current Tier-1 code is unable to fail, since the seam test does fail on its own mutations. It is not P3 either, because the escaped harm is the Hard Rule 4 harm: buildings shifted off their terrain with every gate green. That falls within the no-hard-coded-offsets part of the rule and the requirement that Tier-1 code be mutation-proved.
  - Skeptic 2: holds, P2. I could not refute the finding. The claim holds at 88678e2 and P2 is the right grade.

Why the claim holds:
- building_loader.gd:28-39 never sets a transform. It relies on Node3D's default identity.
- No game test reads the position or global_transform of "Buildings" or its MeshInstance3D children. A search of game/tests for transform, global_position, .position, IDENTITY and aabb finds only camera and sun checks.
- Every test that touches "Buildings" checks only presence, name, child count or null: test_building_loader.gd:56-63, test_main_scene_buildings.gd:180-184, test_main_scene_terrain.gd:69/109 and test_main_scene.gd:211/233.
- test_building_loader.gd compares only mesh-local arrays (surface_get_arrays). test_building_chunks.gd stops at the reader's PackedVector3Array.
- tools/export.sh checks only the count-only startup line (main.gd:203-207).
- So `buildings.position = Vector3(1000,0,0)` leaves every assertion unchanged. The reported green gate is what the code predicts, even though I did not re-run it.
- M2-05's does-NOT-prove lines (brief lines 111-138) never mention the scene transform.
- The software-screenshot gate in M2-05 was a one-off at the brief, not part of tools/gate.sh, so it does not guard future changes.

Points that weaken the finding but do not refute it:
- The headline "the one Tier-1 step on the game side has no gate at all" overstates things. The reader's placement is gated and mutation-proved (run X, test_every_named_vertex_lies_where_the_world_config_puts_it). Only the last step, the node transform in the scene, is ungated.
- main.gd:14 is not false today. The comment is true of the current code; the gap is that no scene-level test backs it.
- The harm needs a future change. A whole-village 1 km shift would also be obvious to the owner on sight, so it is not silent to a human. A few-metre shift would be far less visible and would pass the same way, so this is a real hole in the gate.
- The Main-transform variant of the harm depends on whether Terrain3D follows its parent's transform. The Buildings-node offset (a streaming offset, for example) is the clean case, and it is enough on its own.

Why P2 and not P1: no code today does this wrong. What is missing is a regression guard on the identity transform, which sits in the chain of Hard Rule 4. That fits P2's "a future change or a weak gate". It is not P1, because the Tier-1 transform code (WorldConfig, the reader) does have mutation-proved gates. It is not P3, because the risk is a shifted world, which is not cosmetic.

The proposed fix is sound: assert that the Buildings node and each chunk mesh have global_transform == IDENTITY, map the box's floor corner through WorldConfig.to_local, check the ground at the footprint lies between floor and roof, prove the test with the node-shift mutation, and add the scene transform to M2-05's does-NOT-prove list.
  - Skeptic 3: holds, P2. The finding holds, and I would keep it at P2.

1. The claim is true at 88678e2. `git grep` over game/tests and game/scripts finds no test that reads the position or transform of the Buildings node or of its MeshInstance3D children. The only transform assertions are on the camera (its local `position` and its basis) and on the sun's basis.
   - test_building_loader.gd pins the mesh-local vertices to the chunk's positions. test_normals_face_out keys each triangle on (a, c, b).
   - test_building_chunks.gd ties those positions to `WorldConfig.to_local`.
   - test_main_scene_buildings.gd checks only that the nodes exist and what they are named. Its header says outright: "The buildings' placement is test_building_chunks.gd's subject, not this file's."
   - The loader's does-NOT-prove line names only rendering and the look. main.gd:14's Hard Rule 4 sentence has no scene-level test behind it.

2. I reproduced the proof independently, without touching the main checkout. I extracted 88678e2 with `git archive` into scratchpad/sk3-p01 and added `buildings.position = Vector3(1000.0, 0.0, 0.0)` after `buildings.name = NODE_NAME`. I then ran the import, `python -m mattini manifest` and the full GUT command from CLAUDE.md. Result: gut exit 0, Scripts 20, Tests 98, Passing 98, Asserts 2692, "---- All tests passed! ----", no SCRIPT ERROR. A first run without the generated manifest failed only the four test_world_config* scripts, which do not touch the buildings.

3. Where I would refute it:
   - "The one Tier-1 step on the game side has no gate at all" overstates it. The array-level seam is gated and mutation-proved (the X and W mutations in the brief). What is ungated is the scene-graph transform, which today is the default identity that no code sets. The code is correct now.
   - The "mutation" adds a line rather than changing an existing one.
   - The SPEC plans no chunk streaming or floating origin, so the harm needs a future change.
   - For these reasons P1 is too high: no gate here "cannot fail over Tier-1 code", because there is no transform code to fail over.

4. Why it is still not P3 or a non-finding:
   - The composed placement of a building is its node transform times its mesh vertices. That is the Hard Rule 4 harm (a village shifted off its terrain), in Tier-1 territory.
   - WORKFLOW's Tier-1 policy asks that every does-NOT-prove be enumerated, and this one is not.
   - A transform on Main in main.tscn would also slip through. The terrain gives no cross-check: test_main_scene_terrain compares the camera's local position against the terrain's data heights, and nothing compares the buildings' global placement with the terrain.
   - This fits P2 exactly ("a future change or a weak gate").

5. The proposed fix is sound and cheap, and would be mutation-provable with the 1 km shift. It checks the global_transform of the Buildings node and its children, compares the box's global floor corner with `WorldConfig.to_local` of its LV95 point, and checks that `_ground_height` lies between the box's floor and roof.

Files: /home/user/mattini at 88678e2 (game/scripts/buildings/building_loader.gd:28-39, game/tests/test_building_loader.gd, game/tests/test_main_scene_buildings.gd:177-187, game/tests/complete_world.gd, game/scripts/main.gd:14). Mutation run: /tmp/claude-0/-home-user-mattini/bea2be16-f780-5dd6-9dd8-5304b8b207c1/scratchpad/sk3-p01/gut2.log

### M2-R1-P-02 · P2 · The expected-hash checks are silently bound to config/world.json: after a world change they blame 'this machine or this code' and point to a command that cannot succeed

- **Where:** pipeline/mattini/buildings.py:570-583 and 728-734; pipeline/mattini/terrain.py:369-377 and 473-478; config/buildings.json; config/terrain.json; docs/SPEC.md:332 (Expected output)
- **Claim:** config/buildings.json's chunk SHA-256s encode the origin, the height offset, the axes and the area of config/world.json. config/terrain.json's values encode the height offset and the area. Neither config records which world config its values were computed for, and neither refusal names the world config as a possible cause. So a change to world.json, the file CLAUDE.md calls the one home, is reported as a machine or code fault.
- **Proof:** worlds.py ran with scratch world copies. (1) Origin moved to E 2624000 / N 1097000: in a fresh folder the terrain builds (b6334c1f…) and `buildings` refuses with 'chunk 2623-1095: the buildings built here give SHA-256 4a5eb2d8…, config/buildings.json expects 85273add…. Design computed the expected chunks two independent ways, so this machine or this code produces other buildings than the design's'. In the owner's existing folder, `manifest` refuses (stale terrain). `terrain` rewrites its files, then its manifest step refuses the stale buildings, naming `python -m mattini buildings`, which refuses as above. (2) height_offset_m set to 1000: `terrain` refuses with '…so this machine or this code produces other heights than the design's', and `buildings` refuses the same way. (3) Axes x=-n, y=+h, z=-e: `buildings` gives the same message. A headless main scene over the shifted-world output shows the terrain and logs 'BuildingChunks: …: no buildings have been built: run python -m mattini download buildings, then python -m mattini buildings'.
- **Harm:** The owner or design edits config/world.json, the place the rules send them for the world. The pipeline then says the machine or the code is wrong. The game's panel and the manifest's refusal both name `python -m mattini buildings`, which refuses too. Nothing says the expected values belong to the previous world config, so no manifest can be written until someone guesses to revert world.json or delete buildings/.
- **Fix:** Record in config/buildings.json the world_sha256 its chunks were computed for. For config/terrain.json, record the height offset and box its heights were computed for. Check that first, before comparing hashes, with its own refusal: 'the expected values were computed for another world config; changing the world is a design change: design recomputes them'. At minimum, name config/world.json as a possible cause in all four messages. Add a test that shifts the fixture's origin and asserts the message.
- **Verification:** Upheld by 3 of 3 skeptics (grades P2, P2, P2).

  - Skeptic 1: holds, P2. I could not refute it; reading the code at 88678e2 confirms the finding.

1. The two expected-hash configs do not record the world they were computed for. config/buildings.json holds only the tile to SHA-256 map, and config/terrain.json holds only the spacing to SHA-256 map. Neither carries a world_sha256, an origin, an offset or a box.

2. The buildings bytes depend on the world config. Per SPEC §8, each vertex goes through the world config's to_local (origin, height_offset_m, axes), and the area box comes from world.json too. So a changed origin, offset or axes gives other chunk bytes.

3. The terrain bytes also depend on the world config. The terrain heights are the source heights minus height_offset_m, on a grid taken from the area box in world.json. The origin does not affect them, which is why the finding's origin-shift terrain still gives b6334c1f.

4. The refusal messages blame the machine or the code, never the world config. buildings.py:570-583 (_compare_with_expected) and terrain.py:369-377 hard-code "Design computed the expected ... two independent ways, so this machine or this code produces other ...". The manifest-side checks (buildings.py:728-734, terrain.py:473-478) name neither cause and send the reader to the build command through fail(), which cannot succeed.

5. No document supplies the missing link. SPEC §8 says only that "a machine or a code change that computes other heights says so itself". Nothing in SPEC, brain.md, WORKFLOW or DESIGN.md says a change to world.json requires recomputing expected_sha256.

6. The dead end is real. The manifest's world_sha256 refusal (buildings.py:695, terrain.py:428) names `python -m mattini buildings` or `terrain`, and that command then refuses as above. The game panel (building_chunks.gd:70) names the same command.

Two points soften it:
- In an existing folder, the first manifest refusal does say "it was built for the world config with SHA-256 X, the world config now has Y". That hints the world changed, but it speaks of the built output, not of the expected values. In a fresh folder there is no hint at all.
- SPEC treats a world change as a design change (§6: a non-zero offset "is a design change"). So the realistic trigger is design or the owner editing world.json without recomputing the hashes.

The harm is not P1: nothing wrong is written, the refusal is loud, and the old manifest and game stay valid. It is also more than a cosmetic wording issue (P3). The message asserts a false cause (against the honesty that Hard Rule 2 asks of errors), and the command it names cannot fix the problem, triggered by a future change to the one-home file. That matches P2 ("a future change").
  - Skeptic 2: holds, P2. I could not refute the finding. The code at 88678e2 matches the claim, and I reproduced the misleading message.

1. **The configs do not record their world.** `build_buildings` (buildings.py:479-553) reads the world, checks only that the configured area exists and that world.json did not change during the run, then calls `_compare_with_expected`. config/buildings.json holds only `{schema, areas.village.expected_sha256}`. config/terrain.json holds only the spacing and the hashes per spacing. Neither records the world_sha256, origin, offset or box its values were computed for.

2. **Both refusals blame the machine or the code.** The buildings refusal (570-583) and the terrain refusal (369-377) both end with "Design computed the expected ... two independent ways, so this machine or this code produces other ...". Neither mentions world.json.

3. **Reproduced on the shared fixture.** I extracted the commit to the scratchpad with git archive and ran `build_buildings` on tests/shared/buildings_fixture with a copy of its world.json. With the origin E moved by 1 m, and separately with height_offset_m raised by 1, the step refuses: "chunk 2650-1149: the buildings built here give SHA-256 6f9eb8dd… / 5b237f34…, config/buildings.json expects c92aa635…. Design computed the expected chunks two independent ways, so this machine or this code produces other buildings than the design's".

4. **The recovery path is a dead end.** `built_buildings_block` (728-734) refuses a block whose world_sha256 differs and names `python -m mattini buildings`, which then refuses as in point 3.

5. **Nothing in the docs covers it.** docs/SPEC.md, docs/roles/DESIGN.md, WORKFLOW, brain.md and LESSONS.md never say that the expected hashes belong to one world config. SPEC §8 even says the terrain check exists so that "a machine or a code change that computes other heights says so itself". Design only considered spacing changes, which are keyed.

**Why P2 and not higher:** the check fails closed, so no wrong world ships and nothing is lost. The owner's existing manifest and game keep working with the old world. SPEC §6 calls a world change (height offset) a design change, which makes this "a future change". The owner confirmed the origin, and the file is Tier-1, so it rarely changes.

**Why not P3:** the text is more than cosmetic. It states a false cause, the machine or the code (against the spirit of Hard Rule 2, honest states), and it points to a command that cannot succeed. The fix is small: record which world the values belong to, or at least name config/world.json as a possible cause, and test it with a shifted fixture origin.
  - Skeptic 3: holds, P2. I could not refute it. The claim is true, and P2 fits as "a future change", though at the low end.

**What I checked:**
- At 88678e2, `_compare_with_expected` (buildings.py:570-583) and the build check at terrain.py:369-377 hard-code the wording "this machine or this code produces other buildings/heights than the design's".
- The manifest-side comparisons (buildings.py:728-734, terrain.py:473-478) only say "the buildings/terrain config expects …" and name the rebuild command.
- config/buildings.json and config/terrain.json hold only `expected_sha256` (and `spacing_m`). Neither records a world hash, offset or box. SPEC §8 fixes exactly that shape.
- CLI flow in `__main__.py`: `terrain` and `buildings` each rebuild and then call `write_manifest`. `built_buildings_block` refuses a `world_sha256` mismatch and names `python -m mattini buildings`, and that command then fails the hash check. So the dead end the finding describes is real.
- I ran a probe on a `git archive` extract of 88678e2 in scratch, using the repo's venv and the shared buildings fixture. I built the fixture's chunks, took their hashes as the expected values, moved the fixture world's origin by 1000 m and rebuilt. `_compare_with_expected` refused with "…config/buildings.json expects c92aa635… Design computed the expected chunks two independent ways, so this machine or this code produces other buildings than the design's; nothing was written". That is the misattribution the finding describes.
- Terrain heights depend on `height_offset_m` and the area box, not on the origin. Buildings depend on origin, offset, axes and the area. Both match the claim.

**Why it is not higher than P2:**
- The refusal is fail-safe: no wrong world, no lost data.
- Every world value is pinned by `pipeline/tests/test_world.py::test_config_holds_the_owners_decisions` and by `game/tests/test_world_config.gd`. SPEC §6 calls a non-zero offset a design change. So a world change goes through design and edits pinned tests.
- In an existing output folder, the first `manifest` refusal ("built for the world config with SHA-256 X, the world config now has Y") does name the world config.
- An axes change is also refused earlier by terrain, whose message is honest: it names the unsupported mapping.
- M5 adding areas to world.json would not hit this. The village chunk bytes don't change and the rebuild succeeds.

**Why it is not P3 (cosmetic):**
- The message makes a false causal claim in a project that stresses honest states.
- The only command it offers cannot succeed.
- In a fresh folder, nothing points to world.json.
- No gate ties the expected values to the world config. The gate has no real data, so a design session that changes world.json and forgets to recompute them passes the gate. Only the owner's run would find it, and it would blame his machine. That is the lesson-38 pattern.

The fix is sound: record the world hash (or the offset and box) next to the expected values and check it first with its own message, or at minimum name config/world.json in all four messages. It needs a SPEC change by design.

### M2-R1-P-03 · P3 · manifest accepts a buildings block whose lv95_box is not the world's area (the class M2-06 closed for the terrain)

- **Where:** pipeline/mattini/buildings.py:700-706 (built_buildings_block checks only the box's shape)
- **Claim:** built_buildings_block checks that lv95_box has exactly four finite numbers but never compares them with world.area(area). It receives no world. M2-06 added this comparison for the terrain block only; its does-NOT-prove line says 'anything about the buildings' block'.
- **Proof:** box.py copied the real built folder and set buildings/village.json's lv95_box to E 2624000-2626000 / N 1096000-1099000, 1 km off in both axes. write_manifest wrote the manifest with that box beside the terrain's correct 2623000-2625000 / 1095000-1098000.
- **Harm:** None today: the game ignores buildings.lv95_box, and the chunk hashes pin the positions. A later consumer, such as chunk loading by distance, would trust a wrong box, and the manifest would never have said so.
- **Fix:** Pass the parsed world to built_buildings_block and compare lv95_box with world.area(area) as floats, the way terrain._check_shape does. Otherwise drop the field from the block. Add a test with the 1 km shifted box.
- **Verification:** P3: not put to the skeptics.

### M2-R1-P-04 · P3 · BuildingChunks._check_world is untested and only partly matches its own claim

- **Where:** game/scripts/buildings/building_chunks.gd:10-13 and 88-100
- **Claim:** The header says 'the WorldConfig given must be read from the same manifest (Hard Rule 4)'. The check compares only the origin and the height offset, not the axes, as M2-05 Findings item 7 records. No test makes it refuse. The reader never uses the world, so the check guards nothing that the reader computes.
- **Proof:** Mutation: `if true: return ""` at the top of _check_world. The whole GUT suite still passed 98/98 with '---- All tests passed! ----' (review-R1/P/gut-g-checkworld.log). Undone with `git apply -R`, and git status is clean.
- **Harm:** No owner-visible harm today: main.gd passes the same manifest's WorldConfig. It is a check that looks wired and that nothing proves, which is the lesson 1 pattern.
- **Fix:** Either test it with a WorldConfig from another manifest (another origin, and another axis mapping once the axes are compared), or remove it and the header's claim, since the reader converts nothing.
- **Verification:** P3: not put to the skeptics.

### M2-R1-P-05 · P3 · SPEC's measurement of how the buildings meet the terrain misses the buried class: 8 buildings have their roof below the 2024 ground at their centre

- **Where:** docs/SPEC.md:351-358 (How the buildings meet the terrain) and the release record's list it feeds
- **Claim:** The SPEC names the 12 buildings that stand above the terrain at a corner, for the owner to look at. It says nothing about buildings that the 2024 terrain covers. Those buildings will look missing in the game.
- **Proof:** buried.py (bilinear terrain from the built village.f32, building ranges from an independent derivation) lists 8 buildings whose roof is below the ground at their bounding-box centre. {B7632268-A860-45C7-B4F7-8A5A24657354}: OBJEKTART 'Gebaeude unsichtbar', 3 of 42 vertices above ground, by at most 0.18 m. {CEB91F2C-E78C-4334-885C-6E386C2E6B8B}: 'Im Bau', 22 x 21 m. {93962B42-C282-4FB5-A849-802A203901F1}: 23 x 26 m, 2 of 50 vertices above ground. The other five are 'Gebaeude Einzelhaus': 051BEC10…, 0D9071AA…, 2CA4128A…, 366C806F…, E4B87A5D…. Terrain3D in the game gives the same picture: 1475 of 1486 have the ground between floor and roof, and |Terrain3D - grid| max is 0.000 m. The SPEC's own count reproduces exactly: 12 buildings above at a floor corner, 4 by more than 1 m, max 4.09 m.
- **Harm:** The owner can meet a building from the data that is invisible or nearly invisible in the game, with no record saying it is the data (2012/2015 survey against 2024 terrain, or swisstopo's own 'invisible' class) and not a placement bug.
- **Fix:** Add the buried class, with its 8 UUIDs, to SPEC §8's measurement and to the release record's list for the owner, beside the 12 that stand above the terrain.
- **Verification:** P3: not put to the skeptics.

### M2-R1-P-06 · P3 · The buildings fixture's terrain config borrows the other fixture's heights hash, unlabelled

- **Where:** tests/shared/buildings_fixture/terrain.json:6
- **Claim:** The buildings fixture's terrain.json gives area 'fixture' the 0.5 m expected heights fd02c744…, which is the first terrain fixture's heights file (tests/shared/terrain_fixture/terrain.json:6). The buildings fixture has another world and box and no terrain source, so no correct value exists. Nothing labels this one as a placeholder: buildings_vectors.json's 'about' never mentions terrain.json.
- **Proof:** grep: fd02c744… appears in tests/shared/terrain_fixture/{terrain.json, generated/…} and pipeline/tests/test_terrain_expected.py:32 as that fixture's heights, and again in tests/shared/buildings_fixture/terrain.json:6.
- **Harm:** None in the game. A later test that builds a terrain for the buildings fixture would be refused by P-02's misleading message. It is also an unlabelled placeholder value, which Hard Rule 2 forbids.
- **Fix:** Say in the fixture's documentation (buildings_vectors.json 'about') that terrain.json exists only to name the area and that its hash is a placeholder no terrain can match.
- **Verification:** P3: not put to the skeptics.

## Checked and clean

- Real village buildings from the real sheets (`python -m mattini buildings --raw <scratch>/raw`, exit 0, 7.2 s): the six chunk SHA-256s equal config/buildings.json (85273add…, e2c657fd…, 7484d4bf…, 72155f75…, 32068ec6…, 5d64e30f…); 1486 buildings, 92594 vertices, 178910 triangles, 3258048 bytes; village.json cfddb51d… and manifest ebd3fdef…, the same as M2-04's Findings.
- Real village terrain at 0.5 m: b6334c1f… (village.json ea6e6c90…). Also built at 1 m (71bd4f17…, 2001 x 3001) and at 2 m (d6c1d558…, 1001 x 1501). Both equal config/terrain.json, and manifest accepts each.
- A third independent derivation of the chunks reproduces all six hashes byte for byte. It shares no code with mattini.buildings: fiona.open('zip://…'), Python round(v,3) and round(v,4), a numpy volume, and the owner's mapping applied by hand from config/world.json.
- 17 real buildings placed by hand through config/world.json, at least 2 per tile plus the one nearest a km line in each tile, from sheets 1348-11 and 1348-12, compared with what the game returns (headless probe over BuildingChunks, WorldConfig and TerrainGrid). Every source triangle is in the chunk as exact float32, and all are reversed from swisstopo's inward order as the LV95 volume sign requires. The volume in game coordinates is positive (outward). WorldConfig.to_local of the first LV95 vertex equals the hand conversion. The ground lies between floor and roof for all 17.
- Buildings against terrain across the whole village. In the game with Terrain3D loaded headless: 1475 of 1486 have the ground at their centre between floor and roof, and Terrain3D's height equals the grid's bilinear value (max difference 0.000 m). The pipeline side gives the same 1475. The check can tell a wrong placement: a 1 km east shift gives 1, a north-south mirror gives 185.
- All 1486 buildings have a positive signed volume in the file's own order and float32 positions, for the owner's world and for a rotated one. BuildingLoader: all 178,910 triangles are appended in the order opposite their normal (Godot's clockwise front). SurfaceTool.generate_normals gives (0,1,0) for (0,0,0),(1,0,0),(0,0,1), as SPEC measured.
- SPEC §8's count reproduces exactly: 12 buildings stand above the terrain at a floor corner, 4 by more than 1 m, max 4.09 m.
- Rotated world (x=-n, y=+h, z=-e) in a scratch copy: `terrain` refuses at build ('supports only the axes x = +e, y = +h, z = -n') and TerrainGrid refuses in the game; `buildings` refuses on the hashes. With the expected hashes recomputed as design would, the game places all 17 hand-rotated buildings exactly and outward.
- Shifted world (origin E 2624000 / N 1097000) and height offset 1000: no wrong world is ever written or shown. Every path refuses, and the game keeps or shows only consistent data (see P-02 for the messages).
- The shared fixtures. buildings_vectors.json's 16 named vertices all appear in source.json, at their stated index in the chunk bytes, equal to float32(to_local). The NW terrain fixture: 182/182 vertices equal an independent exact-rational area-overlap mean, with x_min -1036 and z_min -1034.
- sheets.py: 1348-11 is E 2620000-2624375 / N 1095000-1098000 as in the SPEC. The six sheets within 100 m of the village box, derived by hand, equal the lock's six.
- Mutations, each undone with `git apply -R` and git status clean after each. (1) LV95 narrowed to float32 before subtracting the origin (buildings.py:292) fails test_buildings_fixture.py::test_the_chunks_hold_the_designed_buildings; harm: every vertex up to 0.125 m off, SPEC §6's precision rule. (2) The step's expected-chunk comparison skipped fails 3 cases of test_chunks_that_are_not_the_expected_ones_are_refused_before_writing; harm: another machine's chunks written silently (lesson 38). (3) The manifest's buildings world_sha256 check dropped fails test_buildings_built_for_another_world_are_refused and test_a_description_that_does_not_match_is_refused[world]; harm: buildings of an old world config shipped against a new one. (4) The manifest's expected-heights check dropped (terrain.py:473) fails test_manifest_refuses_a_terrain_that_is_not_the_expected_one and test_manifest_refuses_the_2_m_value_exchanged_for_the_0_5_m_value; harm: a terrain other than design's reaches the game.
- Determinism: the descriptions and manifests hold no time, path or host. Order is fixed (sheets sorted, tiles sorted, UUIDs as text), the byte layout matches SPEC, and an independent implementation gives identical bytes.
- The standard gate at 88678e2 exits 0: pytest 662 passed, 4 deselected; GUT 20 scripts, 98 tests, 2692 asserts; log scratchpad/review-R1-placement.log.

## Notes

Worktree detached at 88678e2 and confirmed with `git log --oneline -1`. git status is clean at the end: every mutation was undone with `git apply -R` of its saved diff. game/assets/generated was put back to the gate's manifest (it is git-ignored).

Scratch outputs are under /tmp/claude-0/-home-user-mattini/bea2be16-f780-5dd6-9dd8-5304b8b207c1/scratchpad/review-R1/P/ and nothing was committed:
- Real build: out/.
- Independent derivation: indep.py, picks.json, indep-ranges.json.
- Game probes: probe.gd, probe_rot.gd, probe_t3d.gd, all run headless with /opt/godot/godot --path game -s <abs path>.
- World experiments: worlds.py, worlds/, out-shift, owned-*, out-rotate-game.
- Seam scripts: seam_terrain.py, above.py, buried.py, volumes.py, nw.py, box.py, spacings.py.
- Mutation diffs and GUT logs: mut-*.diff, gut-g-*.log.
- Gate logs: scratchpad/review-R1-placement.log (clean) and review-R1-placement-mut-nodeshift.log (node shifted 1 km, gate exit 0).

Placement verdict: the owner's real village is placed correctly end to end, with no P0 or P1 found. That covers the pipeline bytes, a third independent implementation, 17 hand-placed buildings through the game's reader, and all 1486 against Terrain3D in the game.

The two P2s are gaps that need a future change to bite:
- P-01: the scene-level transform of the Buildings node has no gate at all; a full-gate mutation run proves it.
- P-02: the expected-hash configs are bound to config/world.json without recording it, so a world change is misreported as a machine or code fault and blocks every manifest.

Not reported, but worth design's eye:
- The pipeline accepts any proper rotation, including one where y is not +h. BuildingLoader classifies roofs by normal.y without checking the world's up. Only an absurd sideways world would hit it, and the terrain refuses such a world anyway.
- Building selection does not filter OBJEKTART, so swisstopo's 'Gebaeude unsichtbar' solids enter the chunks. This is Tier-2 content, a design choice.
