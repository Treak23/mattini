mattini @VERSION@, built from `main` commit @SHA@ by the release workflow
(`.github/workflows/release.yml`) on a GitHub-hosted runner: the pipeline from the pinned
inputs, `tools/export.sh`, then `tools/release_checks.sh`. What this version changes is in
`docs/releases/v@VERSION@.md` on `main`; that record also lists what the build does not
prove, and those are the things to look at first.

## Download and start

Download the archive for your platform and unpack it into one folder. It holds five files
that belong together: the game, `mattini.pck` (the program's data), the two data packs
`mattini-terrain.pck` and `mattini-photo.pck`, and Terrain3D's library. Keep them in one
folder with their names unchanged.

- **Windows:** `mattini-@VERSION@-windows.zip`. Unpack it and double-click `mattini.exe`.
  The file is not signed, so Windows may say "Windows protected your PC": More info, then
  Run anyway.
- **Linux:** `mattini-@VERSION@-linux.tar.gz`. Unpack it (`tar xzf`), then run
  `./mattini.x86_64` from the unpacked folder; the archive keeps the executable bit.

## If it does not start

1. Check that the five files are in one folder, with their names unchanged. Without a data
   pack the game opens its error panel, and the panel and the log name the missing pack
   (for example "the data pack mattini-photo.pck (the aerial photo) is missing from <the
   folder>"). The fix is to download the archive again.
2. Godot writes a log on every start, line by line while the game runs:
   - Windows: `%APPDATA%\Godot\app_userdata\mattini\logs\godot.log`
   - Linux: `~/.local/share/godot/app_userdata/mattini/logs/godot.log`
3. If the game closes or shows nothing at the start (a possible cause: 4x MSAA on your GPU),
   try it without MSAA before rolling back: put a text file named `override.cfg` beside the
   executable holding these two lines, then start the game again:

       [rendering]
       anti_aliasing/quality/msaa_3d=0

   Delete the file to have MSAA again.
4. Send the log and a screenshot to the `feedback` session.

The rollback is the Release of the version before this one: download its archive and unpack
it into a folder of its own. Up to 0.3.1 the earlier builds are the named folders of the
`dist` branch (`mattini-0.3.1/`, and so on).

## Checksums

SHA-256 of the two archives and of the ten files inside them (`sha256sum -c SHA256SUMS`
beside the unpacked archives checks them; `SHA256SUMS` is also attached to this Release):

```
@SHA256SUMS@
```

## Credits

© swisstopo

Geodata from the Swiss Federal Office of Topography (open government data, swisstopo):

```
swissalti3d 2024, © swisstopo
swissbuildings3d 2020, © swisstopo
swissimage 2023, © swisstopo
swisssurface3d 2021-2022, © swisstopo
swisstlm3d 2026-02, © swisstopo
```

Stars:

Stars derived from the Hipparcos Catalogue (ESA 1997, ESA SP-1200): stars to V 6.0, positions rounded and reformatted. Credit: ESA. CC BY-NC 3.0 IGO, https://creativecommons.org/licenses/by-nc/3.0/igo/

Detail textures for rock, roads and paths: Poly Haven, CC0 1.0 Universal (public domain).

Software: Godot Engine, Terrain3D and GUT (MIT); their licences, and the other components'
copyright notices, are shown on the game's pause screen (Escape) and sit in the repository
beside each addon (`game/addons/`).
