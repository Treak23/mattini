# mattini — builds

The `dist` shelf: exported builds of mattini, never merged, never deleted. Nothing here is
source; the source is on `main`, and every build names the `main` commit it came from.

## Current version: 0.3.0

Built from `main` 697a154fd3cbbeb64c29ebb023acb6457b927f12 on 2026-10-16 (Godot 4.6.3,
Terrain3D 1.0.2). The release record is `docs/releases/v0.3.0.md` on `main`; it lists what
this build does not prove, and those are the things to look at first.

What it is: the village of Zermatt, 2 km × 3 km. The terrain at 0.5 m (swissALTI3D 2024)
carries the SWISSIMAGE 2023 aerial photo at 0.2 m per texel (the photo's real detail is 25 cm), with
roads, paths, water and rock from swissTLM3D drawn on it (free CC0 detail textures; the water is
animated by its shader). The 1'486 buildings
(swissBUILDINGS3D 3.0, 2020) have a roof colour each, measured from the photo, and plaster
walls (one colour, a placeholder). 34'412 generic conifers stand where the LiDAR surface
model (swissSURFACE3D) shows trees. The sun stands where it stood in the photo. A free-fly
camera moves through it. Only the village area is drawn; the mountains around it, the
Matterhorn included, come later (M5). Nobody has seen it on a GPU yet: it has been checked by
software renders of test worlds and of the village, and the Linux build was started headless;
the Windows build has never been started. How it looks is the first look's job.

## Download and start

Take the five files of your platform and keep them together in one folder: the game, three
`.pck` files (the program's data and two data packs, each under GitHub's 100 MiB limit) and
Terrain3D's library.

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

Loading the village takes some seconds after the window opens (a headless start of 300 frames
took 9 s). Expect about 2 to 3 GB of GPU
memory (an estimate from the design, not yet measured on a GPU; the photo alone should take
0.6 to 0.8 GB).

## Controls

Hold the right mouse button to look around. W and S fly along the view, A and D sideways,
E and Q straight up and down. Shift is five times faster. The mouse wheel changes the
speed (from 2 to 1000 m/s, starting at 30 m/s). Escape opens the pause screen: the
version, the controls, the credits, Resume and Quit.

## If it does not start

1. Check that the five files are in one folder, with their names unchanged. Without a data
   pack the game shows an error panel that names what is missing; the fix is to download
   the folder again.
2. Godot writes a log on every start:
   - Windows: `%APPDATA%\Godot\app_userdata\mattini\logs\godot.log`
   - Linux: `~/.local/share/godot/app_userdata/mattini/logs/godot.log`
3. Send the log and a screenshot to the `feedback` session.

The rollback is the named folder of the version before the current one: `mattini-0.2.0/`
(the village with the white model, three files per platform). Take its files of your
platform, as above; its own README lines are under Checksums.

## Layout

- `windows/`, `linux/`: the current version, under fixed names.
- `mattini-<version>/windows/`, `mattini-<version>/linux/`: each version under its own
  name; the last three are kept (older ones stay in this branch's history).

Files are not renamed per version: each executable finds its `.pck` by its own name, its
data packs by the pattern `mattini-*.pck` beside it, and Terrain3D's library by its fixed
name.

## Checksums (SHA-256)

0.3.0, in `windows/`, `linux/` and `mattini-0.3.0/`:

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

0.1.0, in `mattini-0.1.0/`: the same executables and libraries, and the `.pck`
`9fca1a21e74196a378303f51414c848d7e94db511ddd66adfb06140ff7117b00`.

A version's `.pck` files are the same on both platforms. `mattini.pck` is not byte-reproducible:
exporting the same commit again in a fresh clone gives another hash (one entry of it, the
exported main scene, differs; the other 118 are identical), so the hash above is of the file
in this folder. `mattini.exe` and `mattini.x86_64`
are Godot 4.6.3's own release templates, unchanged; the two libraries are Terrain3D
1.0.2's, as vendored on `main`. 0.3.0's executables and libraries are 0.2.0's, byte for
byte; only the `.pck` files changed.

## Credits

Terrain, building, photo, surface-model and map data © swisstopo (swissALTI3D,
swissBUILDINGS3D, SWISSIMAGE, swissSURFACE3D, swissTLM3D). The detail textures for rock,
roads and paths are CC0 from Poly Haven. The game's pause screen carries the credits in
full: the data's attribution, the textures, the placeholders, and the licences of Godot and
its components, of Terrain3D and of godot-cpp (compiled into Terrain3D's library).
