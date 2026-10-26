# mattini — builds

The `dist` shelf: exported builds of mattini, never merged, never deleted. Nothing here is
source; the source is on `main`, and every build names the `main` commit it came from.

## Current version: 0.3.1

Built from `main` cb5946eded1a2e6ce860b4d01c95d7739d223582 on 2026-10-26 (Godot 4.6.3,
Terrain3D 1.0.2). The release record is `docs/releases/v0.3.1.md` on `main`; it lists what
this build does not prove, and those are the things to look at first.

What it is: the village of Zermatt, 2 km × 3 km. The terrain at 0.5 m (swissALTI3D 2024)
carries the SWISSIMAGE 2023 aerial photo at 0.2 m per texel (the photo's real detail is 25 cm), with
roads, paths, water and rock from swissTLM3D drawn on it (free CC0 detail textures; the water is
animated by its shader). The 1'486 buildings
(swissBUILDINGS3D 3.0, 2020) have a roof colour each, measured from the photo, and plaster
walls (one colour, a placeholder). 34'412 generic conifers stand where the LiDAR surface
model (swissSURFACE3D) shows trees. The sun stands where it stood in the photo. A free-fly
camera moves through it. Only the village area is drawn; the mountains around it, the
Matterhorn included, come later (M5).

What 0.3.1 changes, from your test of 0.3.0:

- **The river:** the photo's own colour (× 0.9 instead of × 0.6), less of a mirror (roughness
  0.3 instead of 0.05), smaller, stronger ripples drifting apart at 0.8 m/s (no net direction; 0.3.0's
  drifted slowly downstream), and the bank eased over 1 m instead of the 0.2 m edge.
- **The frame rate:** at most 60 frames a second, and at most 15 while the pause screen is open.
- **The edges:** 4× MSAA.
- **The log:** every line is written to `godot.log` when it is printed, so the log fills while
  the game runs.
- **A missing data pack is named:** the log, and the error panel, name the missing pack, what it
  holds and the folder it is missing from.

0.3.0 ran on your Linux laptop. 0.3.1's changes have been checked only by software renders and by
starting the Linux build here without a GPU; nobody has seen them on a GPU yet, and the Windows
build has never been started. How it looks, and whether it starts with 4× MSAA on your GPU, is the
first look's job.

## Download and start

Keep the five files of your platform together in one folder: the game, `mattini.pck` (the
program's data), the two data packs `mattini-terrain.pck` and `mattini-photo.pck` (each under
GitHub's 100 MiB limit) and Terrain3D's library.

- **Windows:** `windows/mattini.exe`, `windows/mattini.pck`, `windows/mattini-terrain.pck`,
  `windows/mattini-photo.pck`, `windows/libterrain.windows.release.x86_64.dll`. Double-click
  `mattini.exe`. The file is not signed, so Windows may say "Windows protected your PC":
  More info, then Run anyway.
- **Linux:** `linux/mattini.x86_64`, `linux/mattini.pck`, `linux/mattini-terrain.pck`,
  `linux/mattini-photo.pck`, `linux/libterrain.linux.release.x86_64.so`. Run
  `chmod +x mattini.x86_64` once (a browser download loses the executable bit), then
  `./mattini.x86_64`.

On GitHub: switch the branch to `dist`, open the folder, open each file, "Download raw
file". Or clone only this branch (it holds every kept version, so it is large):
`git clone --branch dist --single-branch --depth 1 https://github.com/Treak23/mattini mattini-dist`.

Loading the village takes some seconds after the window opens (a headless start here printed
its last startup line within 10 s). On your laptop (RTX 3060, 1920 × 1080) 0.3.0 peaked at
1'763 MiB of GPU memory; 0.3.1's 4× MSAA needs more, not measured.

## Controls

Hold the right mouse button to look around. W and S fly along the view, A and D sideways,
E and Q straight up and down. Shift is five times faster. The mouse wheel changes the
speed (from 2 to 1000 m/s, starting at 30 m/s). Escape opens the pause screen: the
version, the controls, the credits, Resume and Quit.

## If it does not start

1. Check that the five files are in one folder, with their names unchanged. Without a data
   pack the game opens its error panel: without the terrain pack it says "mattini cannot show
   the terrain", without the photo pack "mattini cannot show the aerial photo", and the panel
   and the log name the missing pack (for example "the data pack mattini-photo.pck (the aerial
   photo) is missing from <the folder>"). The fix is to download the folder again.
2. Godot writes a log on every start, line by line while the game runs:
   - Windows: `%APPDATA%\Godot\app_userdata\mattini\logs\godot.log`
   - Linux: `~/.local/share/godot/app_userdata/mattini/logs/godot.log`
3. If the game closes or shows nothing at the start (a possible cause: 4× MSAA on your GPU),
   try it without MSAA before rolling back: put a text file named `override.cfg` beside the
   executable holding these two lines, then start the game again:

       [rendering]
       anti_aliasing/quality/msaa_3d=0

   The exported build reads such a file (checked here by overriding another setting, not by
   a crash); delete it to have MSAA again.
4. Send the log and a screenshot to the `feedback` session.

The rollback is the named folder of the version before the current one: `mattini-0.3.0/`
(0.3.0, five files per platform, as above). Take its files of your platform and keep them
together; its own lines are under Checksums.

## Layout

- `windows/`, `linux/`: the current version, under fixed names.
- `mattini-<version>/windows/`, `mattini-<version>/linux/`: each version under its own
  name; the last three are kept (`mattini-0.3.1/`, `mattini-0.3.0/`, `mattini-0.2.0/`; older
  ones, `mattini-0.1.0/` among them, stay in this branch's history).

Files are not renamed per version: each executable finds its `.pck` by its own name, its
data packs by the pattern `mattini-*.pck` beside it, and Terrain3D's library by its fixed
name.

## Checksums (SHA-256)

0.3.1, in `windows/`, `linux/` and `mattini-0.3.1/`:

```
91724f15024a3a545e28ccd83134403d31ce2323a38e51c95e4dfa282f732ab6  windows/mattini.exe
42588a787f6329532da40f8567306430798a2151d3c4820dc56362126da2821e  windows/mattini.pck
f3118736ec7765a297634b54aef42ad3929f5bff0c9d89cac6a4fdf1829590da  windows/mattini-terrain.pck
c29b01a6788fc082a0a93eca8cbcfd3c859ac39f7315764bae893e7855c94661  windows/mattini-photo.pck
40900e649c3c6c7619c383d28732c3e2e8dc87c2938de43b29122a668aedcf86  windows/libterrain.windows.release.x86_64.dll
2c78919325d7f29fa7607287c7c1eeac367ea4c94e7b8b6f5f4c6b20492f73d0  linux/mattini.x86_64
42588a787f6329532da40f8567306430798a2151d3c4820dc56362126da2821e  linux/mattini.pck
f3118736ec7765a297634b54aef42ad3929f5bff0c9d89cac6a4fdf1829590da  linux/mattini-terrain.pck
c29b01a6788fc082a0a93eca8cbcfd3c859ac39f7315764bae893e7855c94661  linux/mattini-photo.pck
e79ebb2e48a63a5d6189a825f1d63ec847319dc8fa030936d95bf6fad8f294ef  linux/libterrain.linux.release.x86_64.so
```

0.3.0, in `mattini-0.3.0/` (the same files but `mattini.pck`):

```
91724f15024a3a545e28ccd83134403d31ce2323a38e51c95e4dfa282f732ab6  windows/mattini.exe
ce1cd06e316149fabcba03ef59fb31a16fbfe15df85edc394e8b504fd7f4030a  windows/mattini.pck
f3118736ec7765a297634b54aef42ad3929f5bff0c9d89cac6a4fdf1829590da  windows/mattini-terrain.pck
c29b01a6788fc082a0a93eca8cbcfd3c859ac39f7315764bae893e7855c94661  windows/mattini-photo.pck
40900e649c3c6c7619c383d28732c3e2e8dc87c2938de43b29122a668aedcf86  windows/libterrain.windows.release.x86_64.dll
2c78919325d7f29fa7607287c7c1eeac367ea4c94e7b8b6f5f4c6b20492f73d0  linux/mattini.x86_64
ce1cd06e316149fabcba03ef59fb31a16fbfe15df85edc394e8b504fd7f4030a  linux/mattini.pck
f3118736ec7765a297634b54aef42ad3929f5bff0c9d89cac6a4fdf1829590da  linux/mattini-terrain.pck
c29b01a6788fc082a0a93eca8cbcfd3c859ac39f7315764bae893e7855c94661  linux/mattini-photo.pck
e79ebb2e48a63a5d6189a825f1d63ec847319dc8fa030936d95bf6fad8f294ef  linux/libterrain.linux.release.x86_64.so
```

0.2.0, in `mattini-0.2.0/` (three files per platform; its two `.pck` files are the same file):

```
91724f15024a3a545e28ccd83134403d31ce2323a38e51c95e4dfa282f732ab6  windows/mattini.exe
ca4a17bdedbe9756c2112d9613e23070b6d4c84b96087913d18607f956b52172  windows/mattini.pck
40900e649c3c6c7619c383d28732c3e2e8dc87c2938de43b29122a668aedcf86  windows/libterrain.windows.release.x86_64.dll
2c78919325d7f29fa7607287c7c1eeac367ea4c94e7b8b6f5f4c6b20492f73d0  linux/mattini.x86_64
ca4a17bdedbe9756c2112d9613e23070b6d4c84b96087913d18607f956b52172  linux/mattini.pck
e79ebb2e48a63a5d6189a825f1d63ec847319dc8fa030936d95bf6fad8f294ef  linux/libterrain.linux.release.x86_64.so
```

A version's `.pck` files are the same on both platforms. `mattini.pck` is not byte-reproducible:
exporting the same commit again in a fresh clone gives another hash (one entry of it, the
exported main scene, differs; measured at 0.3.0), so the hash above is of the file in this
folder. `mattini.exe` and `mattini.x86_64` are Godot 4.6.3's own release templates, unchanged;
the two libraries are Terrain3D 1.0.2's, as vendored on `main`. 0.3.1's executables, libraries
and data packs are 0.3.0's, byte for byte; only `mattini.pck` changed.

## Credits

Terrain, building, photo, surface-model and map data © swisstopo (swissALTI3D,
swissBUILDINGS3D, SWISSIMAGE, swissSURFACE3D, swissTLM3D). The detail textures for rock,
roads and paths are CC0 from Poly Haven. The game's pause screen carries the credits in
full: the data's attribution, the textures, the placeholders, and the licences of Godot and
its components, of Terrain3D and of godot-cpp (compiled into Terrain3D's library).
