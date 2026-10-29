# ARCHIVE.md — feedback whose fix shipped, or that was declined

Moved here from `INBOX.md` §Open by the design realm's drain, each with its disposition and
version. Entries keep their original text; nothing is deleted.

### FB-008 · 2026-10-26 · bug · Ground / the river flows side to side, it needs a direction
Machine: linux (the owner's laptop: RTX 3060 Laptop GPU 6 GB plus AMD Vega iGPU, EndeavourOS, KDE Plasma on Wayland, 1920x1080 at 300 Hz; as FB-003)
Build: 0.3.1 (dist 5b51347; the owner's local session verified the five Linux files and the mattini-0.3.0/ rollback against the README's checksums)
Impact: degraded
Owner's words: "river flows but side to side, we will need to give it a direction. everything else is good"
What happened: Filed by the 0.3.1 release session from the owner's message in its chat (the clerk was not in the loop). The river now visibly moves, but its two ripple patterns drift apart in opposite directions at 0.8 m/s with no net direction (0.3.1's design, the owner's answer at the go), which reads as side to side.
Expected: the river flows in one direction, downstream.
Repro / where exactly: 0.3.1, the Vispa in the village, any view.
Screenshots: none
Possibly same as: FB-003 (archived, shipped in 0.3.1)
Disposition: → the next release's triage (0.4.0): a flow direction per stretch from swissTLM3D's river lines (the option offered at 0.3.1's go, pipeline work), or one fixed downstream direction for the village's Vispa (a shader change, wrong wherever a stream runs another way). Release session, 2026-10-26.
Disposition (0.4.0 go): taken into 0.4.0, the owner's "1b": a direction per stretch from swissTLM3D's watercourse lines, which swisstopo draws downstream (SPEC §13 row 53; `docs/history/blocked/2026-10-27-1.md`). Release session, 2026-10-27.
Disposition (0.4.0, 2026-10-29): shipped in 0.4.0, the owner's "1b": a flow direction per stretch from swissTLM3D's watercourse lines (briefs v0.4.0-01 to -03); measured in a software render the ripples move downstream at 0.71 to 0.80 m/s within 0.4 degrees of the local flow; not seen by eye by anyone yet (`docs/releases/v0.4.0.md`). Release session, 2026-10-29.

### FB-007 · 2026-10-17 · bug · Performance / GPU runs flat out, also while paused (no frame cap)
Machine: linux (the owner's laptop: RTX 3060 Laptop GPU 6 GB plus AMD Vega iGPU, game on the NVIDIA GPU via prime-run; EndeavourOS, KDE Plasma on Wayland, NVIDIA driver 610.57.04, 1920x1080 at 300 Hz)
Build: 0.3.0 (dist 5f08379)
Impact: degraded
Owner's words: not stated (the owner said "fluid"; the GPU load is the tester's measurement)
What happened: MEASURED over ~15 min (432 samples every 2 s): GPU utilisation 94 % on average, 100 % at peak, also while paused in the Esc menu; 87 C and 111 W at peak. The display runs at 300 Hz and project.godot sets no frame cap, so the GPU renders flat out all the time: heat and fan noise on a laptop. No frame rate was measured (no counter in the game, no MangoHud installed).
Expected: not stated.
Repro / where exactly: 0.3.0 dist build on the laptop, windowed, any view including the Esc menu. Samples: ~/mattini-test-0.3.0/resources.csv on the owner's laptop.
Screenshots: none
Possibly same as: FB-004 (item 10)
Disposition: → M4-08 (frame cap 60 in the project) and M4-10 (15 while the pause screen is open); SPEC §13 row 45. Design, 2026-10-17.
Disposition (0.3.1): Shipped in 0.3.1 (2026-10-26, `docs/releases/v0.3.1.md`): at most 60 frames a second (v0.3.1-02, `b784d96`) and 15 while the pause screen is open (v0.3.1-05, `8dd6949`); the exported build printed `Project FPS: 60` at the release gate. The GPU load on the owner's laptop is the owner's to read. Release session, 2026-10-26.

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
Disposition: → M4-08 (`application/run/flush_stdout_on_print` true: release exports flush stdout and godot.log per line, measured in Godot's source); SPEC §13 row 45. Design, 2026-10-17.
Disposition (0.3.1): Shipped in 0.3.1 (2026-10-26, `docs/releases/v0.3.1.md`): `application/run/flush_stdout_on_print` true (v0.3.1-02, `b784d96`); the release gate saw the exported Linux build's pack and startup lines in the console and in `godot.log` while it was still running. Release session, 2026-10-26.

### FB-005 · 2026-10-17 · bug · Errors / missing photo pack message names the pipeline, not the pack
Machine: linux (the owner's laptop: RTX 3060 Laptop GPU 6 GB plus AMD Vega iGPU, game on the NVIDIA GPU via prime-run; EndeavourOS, KDE Plasma on Wayland, NVIDIA driver 610.57.04, 1920x1080 at 300 Hz)
Build: 0.3.0 (dist 5f08379)
Impact: degraded
Owner's words: not stated (the owner declined this test: "no i dont want to do that. if there are real errors i will screenshot them, i wont fabricate them"; found by the tester, MEASURED)
What happened: With mattini-photo.pck moved aside, the game did not crash and kept running; the log carries "ERROR: PhotoGrid: res://assets/generated/manifest.json: the photo res://assets/generated/photo/village.jpg is missing; python -m mattini photo rebuilds it". The message gives a developer hint (run the pipeline) and never names mattini-photo.pck, which is what a player of the shipped build would be missing. Whether an error panel appeared on screen: unknown (nobody looked; the tester closed the game after ~30 s). The pack was restored, checksum OK.
Expected: not stated.
Repro / where exactly: 0.3.0 dist build, start with mattini-photo.pck removed from the game folder. Log: ~/mattini-test-0.3.0/mattini-0.3.0-no-photo.log on the owner's laptop.
Screenshots: none
Possibly same as: FB-004 (item 9)
Disposition: → M4-08 (DataPacks names a missing pack, the folder and what it holds; in an export the readers' hint says to download the release folder again, not the pipeline) and M4-10 (DataPacks' errors on the error panel); SPEC §13 row 45. Design, 2026-10-17.
Disposition (0.3.1): Shipped in 0.3.1 (2026-10-26, `docs/releases/v0.3.1.md`): DataPacks names a missing pack, its folder and what it holds, and the readers' messages in a release say to download the release folder again (v0.3.1-03, `041c0d8`); the error panel lists the missing packs (v0.3.1-05, `8dd6949`); `tools/export.sh` refuses a release with other packs (v0.3.1-04, `f0b7df0`). The release gate's run with `mattini-photo.pck` moved aside logged both lines; the panel was seen only in a software render. Release session, 2026-10-26.

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
Disposition: → M4-06 (measured: 94 % of the Vispa's channel carries the water class, so the "patch" is the shading: albedo × 0.9, roughness 0.3, turbulent ripples at 0.8 m/s, the bank eased over 1 m; docs/briefs/sketches/M4-soften/README.md); SPEC §13 row 45. Design, 2026-10-17.
Disposition (0.3.1): Shipped in 0.3.1 (2026-10-26, `docs/releases/v0.3.1.md`): the water in the photo's own colour (× 0.9), roughness 0.3, ripples at 2 m and 3.4 m drifting apart at 0.8 m/s with no net direction (the owner's answer at the go), the bank eased over 1 m (v0.3.1-01, `9793026`). Whether it reads right, and whether the near-black patch was a real or a baked shadow (not changed), is the owner's look. Release session, 2026-10-26.

### FB-002 · 2026-10-14 · idea · Game type / collaborative "Zermatt builder"
Machine: not stated
Build: 0.2.0 (same test session as FB-001)
Impact: wish
Owner's words: a collaborative "Zermatt builder" that could be used for a variety of projects (relayed in the tester's summary, not a verbatim owner quote).
What happened: Not a defect. An idea for the game type, which is still an open decision. The tester asks that it be raised at M3 planning, because "collaborative" implies networking and saved edits, which affect the architecture early.
Expected: not stated
Repro / where exactly: not applicable
Screenshots: none
Possibly same as: —
Disposition: declined for now (design, 2026-10-14): the game type stays OPEN by the owner's word, "keep open, lets just build the map first. i want it as detailed and beautiful as possible" (SPEC §13 row 34). The idea is on the board's Ideas list. Its two early architectural needs are noted there: every machine already rebuilds the same base world (Hard Rule 5, every file checked by SHA-256), and M3 gives the game each building's id (M3-05, M3-12).

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
Closed: shipped in 0.3.0 (2026-10-16). The owner's first look at 0.3.0 (FB-004, 2026-10-17): "looks not bad"; the tester read it as not too white but flat and grey, which M4 takes up (FB-004's disposition). Design, 2026-10-17.
