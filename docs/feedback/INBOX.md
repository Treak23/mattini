# Feedback inbox

Filed by the clerk (`docs/roles/FEEDBACK.md`); drained by the design realm. Entries move
to `docs/feedback/ARCHIVE.md` with a disposition, never deleted. Ids `FB-NNN` are
sequential across both files. Pull --rebase before every commit.

## Open

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
