# mattini — builds

The `dist` shelf: exported builds of mattini, never merged, never deleted. Nothing here is
source; the source is on `main`, and every build names the `main` commit it came from.

## Current version: 0.2.0

Built from `main` 10f00604755837c60753913f47fc7cb0416dd56a on 2026-09-26 (Godot 4.6.3,
Terrain3D 1.0.2). The release record is `docs/releases/v0.2.0.md` on `main`.

What it is: the village of Zermatt as terrain, 2 km × 3 km at 0.5 m (swissALTI3D 2024),
in a clay relief-model look, with its 1'486 buildings (swissBUILDINGS3D 3.0, 2020) as a
white architectural model, and a free-fly camera. Only the village area is drawn; the
mountains around it, the Matterhorn included, come later (M5).

## Download and start

Take the three files of your platform and keep them together in one folder.

- **Windows:** `windows/mattini.exe`, `windows/mattini.pck`,
  `windows/libterrain.windows.release.x86_64.dll`. Double-click `mattini.exe`. The file is
  not signed, so Windows may say "Windows protected your PC": More info, then Run anyway.
- **Linux:** `linux/mattini.x86_64`, `linux/mattini.pck`,
  `linux/libterrain.linux.release.x86_64.so`. Run `chmod +x mattini.x86_64` once (a browser
  download loses the executable bit), then `./mattini.x86_64`.

On GitHub: switch the branch to `dist`, open the folder, open each file, "Download raw
file". Or clone only this branch:
`git clone --branch dist --single-branch --depth 1 https://github.com/Treak23/mattini mattini-dist`.

Loading the village takes a few seconds after the window opens.

## Controls

Hold the right mouse button to look around. W and S fly along the view, A and D sideways,
E and Q straight up and down. Shift is five times faster. The mouse wheel changes the
speed (from 2 to 1000 m/s, starting at 30 m/s). Escape opens the pause screen: the
version, the controls, the credits, Resume and Quit.

## If it does not start

1. Check that the three files are in one folder, with their names unchanged.
2. Godot writes a log on every start:
   - Windows: `%APPDATA%\Godot\app_userdata\mattini\logs\godot.log`
   - Linux: `~/.local/share/godot/app_userdata/mattini/logs/godot.log`
3. Send the log and a screenshot to the `feedback` session.

The rollback is the named folder of the version before the current one: `mattini-0.1.0/`
(the terrain without the buildings). Take its three files of your platform, as above.

## Layout

- `windows/`, `linux/`: the current version, under fixed names.
- `mattini-<version>/windows/`, `mattini-<version>/linux/`: each version under its own
  name; the last three are kept (older ones stay in this branch's history).

Files are not renamed per version: each executable finds its `.pck` by its own name, and
Terrain3D's library by its fixed name.

## Checksums (SHA-256)

0.2.0, in `windows/`, `linux/` and `mattini-0.2.0/`:

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

The two `.pck` files of a version are the same file. `mattini.exe` and `mattini.x86_64`
are Godot 4.6.3's own release templates, unchanged; the two libraries are Terrain3D
1.0.2's, as vendored on `main`.

## Credits

Terrain and building data © swisstopo. The game's pause screen carries the credits in
full: the data's attribution and the licences of Godot and its components, of Terrain3D
and of godot-cpp (compiled into Terrain3D's library; 0.1.0 lacked its notice).
