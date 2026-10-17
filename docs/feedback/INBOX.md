# Feedback inbox

Filed by the clerk (`docs/roles/FEEDBACK.md`); drained by the design realm. Entries move
to `docs/feedback/ARCHIVE.md` with a disposition, never deleted. Ids `FB-NNN` are
sequential across both files. Pull --rebase before every commit.

## Open

### FB-006 · 2026-10-17 · bug · Log / output held back until the game exits
Machine: linux (the owner's laptop: RTX 3060 Laptop GPU 6 GB plus AMD Vega iGPU, game on the NVIDIA GPU via prime-run; EndeavourOS, KDE Plasma on Wayland, NVIDIA driver 610.57.04, 1920x1080 at 300 Hz)
Build: 0.3.0 (dist 5f08379)
Impact: degraded
Owner's words: not stated (tester's observation)
What happened: During ~3 minutes of running, godot.log and stdout showed only the first 2 "mattini" lines (the two data pack lines); the other 6 appeared only when the game quit. A crash would likely lose them, the moment they are needed. The tester notes Godot's project setting application/run/flush_stdout_on_print is off by default in release builds, likely relevant (the tester's guess).
Expected: not stated.
Repro / where exactly: 0.3.0 dist build on Linux; watch godot.log or stdout while the game runs.
Screenshots: none
Possibly same as: FB-004 (other observations)

### FB-005 · 2026-10-17 · bug · Errors / missing photo pack message names the pipeline, not the pack
Machine: linux (the owner's laptop: RTX 3060 Laptop GPU 6 GB plus AMD Vega iGPU, game on the NVIDIA GPU via prime-run; EndeavourOS, KDE Plasma on Wayland, NVIDIA driver 610.57.04, 1920x1080 at 300 Hz)
Build: 0.3.0 (dist 5f08379)
Impact: degraded
Owner's words: not stated (the owner declined this test: "no i dont want to do that. if there are real errors i will screenshot them, i wont fabricate them"; found by the tester, MEASURED)
What happened: With mattini-photo.pck moved aside, the game did not crash and kept running; the log carries "ERROR: PhotoGrid: res://assets/generated/manifest.json: the photo res://assets/generated/photo/village.jpg is missing; python -m mattini photo rebuilds it". The message gives a developer hint (run the pipeline) and never names mattini-photo.pck, which is what a player of the shipped build would be missing. Whether an error panel appeared on screen: unknown (nobody looked; the tester closed the game after ~30 s). The pack was restored, checksum OK.
Expected: not stated.
Repro / where exactly: 0.3.0 dist build, start with mattini-photo.pck removed from the game folder. Log: /home/reto/mattini-test-0.3.0/mattini-0.3.0-no-photo.log on the owner's laptop.
Screenshots: none
Possibly same as: FB-004 (item 9)

### FB-004 · 2026-10-17 · design · Whole game / 0.3.0 owner test results (the M3 release's test list)
Machine: linux (the owner's laptop, not the RTX 4090 PC: RTX 3060 Laptop GPU 6 GB plus AMD Vega iGPU, game on the NVIDIA GPU via prime-run, Vulkan 1.4.341, Forward+; EndeavourOS, KDE Plasma on Wayland, NVIDIA driver 610.57.04, 15 GB RAM, 1920x1080 at 300 Hz, windowed, on AC, performance profile)
Build: 0.3.0 (dist 5f08379, all 10 files match the README's SHA-256 block; pause screen shows "mattini 0.3.0")
Impact: degraded
Owner's words: "done the screenshots. water moves but very slightly and looks weird.otherwise fluid and looks not bad. we will skip windows testing if&until im ready to share it to others, not a priority" / "1 yes credit scrolls and i quit" / on item 9, the error-path test: "no i dont want to do that. if there are real errors i will screenshot them, i wont fabricate them" / "i did most of the tests that were asked for at the last build, log the results"
What happened: The tester's report (REPORT.txt, on the owner's laptop at /home/reto/mattini-test-0.3.0/) keeps three kinds apart: OWNER (verbatim, above), MEASURED (logs, resource sampling) and READ (Claude's reading of the shots, not the owner's verdict). Shot-to-item matching is inferred from the order taken; camera heights are the handoff's targets, not measured.
- Log, PASS (MEASURED): the 8 expected lines: data pack mattini-photo.pck loaded / data pack mattini-terrain.pck loaded / terrain village loaded, 4001 x 6001 vertices at 0.5 m / buildings village loaded, 1486 buildings in 6 chunks, 178910 triangles / photo village loaded, 10000 x 15000 texels at 0.2 m / surfaces village loaded, 10000 x 15000 cells at 0.2 m / trees village loaded, 34412 trees in 6 chunks / roofs village loaded, 1486 of 1486 buildings coloured. No ERROR lines; only the known Terrain3D WARNING (instance_reset_physics_interpolation() is deprecated).
- 1 Start view, "too white" (FB-001): OWNER "looks not bad" (general). READ: not too white; if anything flat and grey: dull grey-blue sky, mid-grey buildings, forest on the shaded slope near-black.
- 2 Photo sharpness: READ: ~150 m good (cemetery graves readable); ~60 m acceptable; ~30 m soft. On steep terrain (the river's walls) the photo is visibly stretched.
- 3 Shadows vs the photo's baked shadows: READ: appear to fall to the same side; angle not measurable from shots. Some baked shadows belong to real trees that have no 3D tree. Not judged by the owner.
- 4 Ground: water: OWNER complaint, filed as FB-003. READ: road grain (asphalt detail) visible on the road; rock grain on steep slopes not captured in any shot.
- 5 Trees: READ: stand on the ground, trunks visible; near-black from a distance; dark green close up with a slightly lighter side towards the sun.
- 6 Roofs and walls: READ: some roof colour variety, mostly greys and blue-greys; walls plain; no roof flat on the ground without a building seen. The church's nave roof comes out pale green; possibly crown colour bleeding into the roof's sampled colour, unconfirmed.
- 7 Exposure: OWNER "looks not bad" (general). READ: not blown out; somewhat dull and grey rather than too dark.
- 8 Esc menu, PASS: version "mattini 0.3.0"; credits swissalti3d 2024, swissbuildings3d 2020, swissimage 2023, swisssurface3d 2021-2022, swisstlm3d 2026-02 (each "© swisstopo"); CC0 textures Rock Face 03, Worn Asphalt, Rocky Trail (Poly Haven); placeholders further down. OWNER "yes credit scrolls"; Resume and Quit work, OWNER "i quit"; the game exited normally.
- 9 Error path (photo pack missing): not checked on screen, the owner declined (quoted above). MEASURED from a run the tester started without the owner watching: filed as FB-005.
- 10 Frame rate, memory: OWNER "fluid". MEASURED (432 samples every 2 s over ~15 min): peak GPU memory 1763 MiB (41 MiB idle before; desktop on the iGPU); RAM peak 3115 MiB while loading, about 2.2 GB steady; GPU utilisation 94 % average, 100 % peak, also while paused; 87 C and 111 W at peak. No frame rate measured (no counter in the game, no MangoHud). The uncapped-GPU observation is filed as FB-007.
- Windows: not tested, deferred by the owner (quoted above).
- Tester's other observations (READ, not the owner's): jagged edges on trees and buildings, no visible anti-aliasing; close to the ground the photo and terrain are very blurry, and a bridge reads as a hump of terrain across the river (may fall under the known limit "no detail below ~30 m beyond the photo"). The log held back until exit is filed as FB-006.
Expected: The 0.3.0 test list as handed over at the M3 close (not restated here).
Repro / where exactly: The 0.3.0 dist build, run 2026-10-17, shots taken 11:45 to 11:49. Time of day and weather in game not stated.
Screenshots: shots/FB-004-a.png (11:45:23, item 1 start view), shots/FB-004-b.png (11:46:10, item 2 at ~30 m, item 3), shots/FB-004-c.png (11:46:30, item 2 at ~60 m), shots/FB-004-d.png (11:47:04, item 2 at ~150 m, items 3 and 6), shots/FB-004-e.png (11:48:20, item 5 trees close), shots/FB-004-f.png (11:48:57: oblique aerial over the village, grey block buildings, dark cone trees, the river on the right, the church with a pale green nave roof in the centre; items 5 and 6), shots/FB-004-g.png (11:49:14: the Esc screen, "mattini 0.3.0", controls, credits with the five swisstopo datasets and the three Poly Haven textures, Resume and Quit; item 8). Items 4's shots are FB-003-a/-b. Mapping of shots to items is the tester's inference.
Possibly same as: FB-001 (item 1 rechecks it)

### FB-003 · 2026-10-17 · bug · Ground / river water effect (village, close up)
Machine: linux (the owner's laptop, not the RTX 4090 PC: RTX 3060 Laptop GPU 6 GB plus AMD Vega iGPU, game on the NVIDIA GPU via prime-run, Vulkan 1.4.341, Forward+; EndeavourOS, KDE Plasma on Wayland, NVIDIA driver 610.57.04, 15 GB RAM, 1920x1080 at 300 Hz, windowed, on AC, performance profile)
Build: 0.3.0 (dist 5f08379, all 10 files match the README's SHA-256 block; pause screen shows "mattini 0.3.0")
Impact: degraded
Owner's words: "water moves but very slightly and looks weird."
What happened: From the tester's report (Claude's reading of the shots, not the owner's verdict): up close the water is near-black with large white glints that change between two shots taken 5 s apart; a hard stepped edge with a jagged white rim where it meets the bank; the effect covers only a patch near the camera, the river beyond shows the flat photo.
Expected: not stated.
Repro / where exactly: Low over the river (the Vispa, guess) in the village, looking upstream along it, close to the water. Time of day and weather not stated. Item 4 (ground) of the 0.3.0 test.
Screenshots: shots/FB-003-a.png (11:47:45: low over the river, near-black water patch with white glints in the foreground, its jagged white rim at the bank; the river further up shows the flat photo; dark cone trees and pale block buildings either side), shots/FB-003-b.png (11:47:50, the same view 5 s later)
Possibly same as: —

### FB-001 · 2026-10-14 · design · Look / terrain and building colour (visual direction)
Machine: linux (EndeavourOS, kernel 7.1.9, KDE Plasma on Wayland, RTX 4090, NVIDIA driver 610.57.04, Vulkan 1.4.341)
Build: 0.2.0 (dist 5ce4888, all three files' SHA-256 equal to the README; pause screen shows 0.2.0)
Impact: degraded
Owner's words: "it's definitely too white." Owner's request, as relayed: buildings and terrain are nearly the same colour and the roofs barely differ from the walls; the owner now wants the realistic route instead of the stylised diorama look.
What happened: In the start view everything is near-white or pale grey; the buildings and the ground read as one colour, and the roofs are hardly distinguishable from the walls. This reverses SPEC §10's look and the board's "Photorealism: not planned", so it is for M3 planning.
Expected: Realistic colour (owner's direction, not a specified target).
Options the tester listed to put to the owner: (a) real colours from swisstopo data: SWISSIMAGE on the terrain, roof colours sampled from it, trees from the surface model; (b) (a) plus textured materials; (c) full photorealism. The tester suggested (a) first.
Repro / where exactly: Start view of the 0.2.0 build, looking up the valley with the village in the foreground. Time of day and weather not stated. Renderer was Forward+, as designed.
Same test, results the owner reported as all OK: (1) it starts: log has both startup lines (terrain village loaded, 4001 x 6001 vertices at 0.5 m; buildings village loaded, 1486 buildings in 6 chunks, 178910 triangles), no ERROR line, only the known Terrain3D deprecation warning; while running about 1.0 GB RAM, 1.1 GB VRAM, GPU around 44%. (2) The pause screen shows 0.2.0, the credits list both datasets, and the credits scroll. (3) The buildings sit right on the terrain: none floating, sunk, holed or inside-out; shadows and contour lines render. (4) Flight is smooth, including at Shift speed. (5) The controls are good. Not tested yet: the Windows build.
Screenshots: shots/FB-001-a.png (the start view: village houses in the foreground, the valley and a river or road running up the middle, steep slopes either side with contour lines; all pale grey-white, the sky pale blue-grey; the pause screen is not open)
Possibly same as: —
Disposition: → M3-04 to M3-07, M3-09 to M3-12 and M3-14 (arc M3, the realistic look the owner chose on 2026-10-14: SPEC §13 rows 29–33; docs/briefs/M3-plan.md). Design, 2026-10-14.
