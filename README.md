# mattini
Zermatt in 3D

A desktop game (Windows, Linux) set in Zermatt, built from swisstopo's open geodata with Godot.
The builds are on the `dist` branch; how to start one is in that branch's README.

## Sources

- Geodata © swisstopo (swissALTI3D, swissBUILDINGS3D, SWISSIMAGE, swissSURFACE3D, swissTLM3D),
  used under swisstopo's terms for free geodata (OGD). The screenshots and renders of the village
  under `docs/` show this data; `tests/shared/buildings_sample/` is one of swisstopo's own files.
  The game's credits list each dataset with its edition.
- Detail textures: Poly Haven, CC0 (`game/textures/LICENSE.txt`). Vendored code: Terrain3D and
  GUT, MIT, each with its licence in its folder under `game/addons/`; godot-cpp's notice in
  `game/credits/`.

mattini's own code carries no licence yet: all rights reserved.
