# M4 design notes (the sun cycle) — design's working notes, 2026-10-17

The briefs and pinned tests cite these as "m4-design §N". SPEC and the briefs outrank them.
The owner's answers: SPEC §13 rows 41–46. The measurements behind every number:
`docs/briefs/sketches/M4-deshadow/`, `M4-soften/` (their READMEs), and §0 below.

## 0. Measurements (2026-10-17, agents of the design session)

- **The flight's sun.** NOAA (Meeus) with refraction, cross-checked against pvlib SPA (agree
  within 0.01°), 46.02 N 7.749 E 1610 m: 2023-09-06 11:25/11:40/11:55 UTC → azimuth (true)
  179.0/184.9/190.7, elevation 50.4/50.3/50.0; 09-07 the same within 0.4°. Mean 184.9°, 50.1°.
  LV95 grid north lies 0.226° east of true north at the village (pyproj, PROJ's
  meridian_convergence, swisstopo's approximate formulas): a grid azimuth is the true azimuth
  minus 0.226 (corrected 2026-10-17 by M4-03's rehearsal; design's first notes added it). M3's sun (183°, 52°, measured from
  the photo's shadows) agrees within the shadows' measuring error.
- **Shadow extent.** At capture 32.3 % of the box is in shadow in the photo. Under the game's
  sun on the same day: 25–32 % of the box is dark in the photo and shaded by the game
  (double darkening), 4–7 % baked-dark where the game lights it; the baked shadows point north.
- **De-shadowing.** Shadows are about 20–23× darker than lit ground (linear); a full lift
  turns JPEG 4:2:0 noise into speckle. A capped lift G = 3 with an inset feather leaves them
  about 7.5× darker, 2 % clipped inside the mask (village), grain 8.7 vs 4.6 sRGB levels.
  A 1 m mask is visually equal to 0.5 m.
- **Horizon.** 2023-09-06 at the village centre: direct sun 09:41–17:41 CEST (astronomical
  06:55–19:59). 2026-06-21 07:57–18:22, 2026-12-21 11:41–15:03. With the 2 × 3 km box alone
  the times are off by 11 to 62 minutes.
- **Far mountains in Godot 4.6.3.** A shadows-only mesh of swissALTIRegio at 100 m, the area
  box cut out, agrees with a CPU ray-cast truth on 98.2–100 % of pixels in Forward+ (lavapipe)
  with the default `directional_shadow_max_distance` 3000 and pancake size: Godot keeps
  casters 10⁶ m towards the light and Forward+ clamps their depth to the near plane
  (`renderer_scene_cull.cpp:2320–2349`, `scene_forward_clustered.glsl:679`). Not cutting the
  box: 85–99 % (the coarse mesh shadows the real terrain in blotches). Compatibility ignores
  pancaking: no far shadow unless the pancake size is about 25 km, which costs self-shadow
  detail; the owner plays Forward+, so Compatibility shows none (said in the release record).
  Software cost: 100 m mesh +40–60 % frame time on llvmpipe (not a GPU measure); 50 m about 2.6×.
- **`light()`** works and keeps ATTENUATION but replaces Godot's whole direct BRDF: not used.
- **Sky.** PhysicalSkyMaterial follows the DirectionalLight's direction (`LIGHT0_DIRECTION`);
  its `night_sky` texture is added by day too (a fade needs a sky shader). Compatibility's
  physical sky is much darker and greyer. Night: a moon light of energy 0.03 at exposure 0.54
  is black; at exposure 4.0 the ground reads dark but visible. Auto exposure is Forward+ only
  and pushed the night to daylight: not used.
- **Frame cap.** `application/run/max_fps` (default 0) and `Engine.max_fps` are a CPU sleep,
  independent of vsync: fps = min(display, cap). `application/run/flush_stdout_on_print`
  defaults false (`.debug` true): release exports buffer stdout and `godot.log`
  (`main.cpp:1047–1048`, `logger.cpp:213, 230`). MSAA: `rendering/anti_aliasing/quality/msaa_3d`
  (2 = 4×); no Terrain3D note found.
- **Water.** The Vispa is a TLM area polygon and a line; 94 % of the channel seen in the photo
  carries the water class (`M4-soften/water-overlay.jpg`). FB-003's "patch" is the shading.
- **swissALTIRegio.** OGD terms with its own source text (§1 below); 10 × 10 km XYZ zip tiles
  (about 6 MB, `file:checksum` each) and one national COG (10.1 GB).

## 1. The input: swissALTIRegio (brief M4-01)

- `config/datasets.json` gains `swissaltiregio`: collection `ch.swisstopo.swissaltiregio`,
  `edition` as the STAC items give it (measured by M4-01's design rehearsal, recorded in the
  brief), `resolution_m` 10, and `attribution` = the product page's source text for the 2025
  and later versions, verbatim (§1a). The credits print it whole.
- Tiles: the 10 km items `swissaltiregio_<EEEE>-<NNNN>` (km of the tile's corner as STAC's bbox
  shows, measured in the rehearsal) whose square meets the surroundings box (§2), asset the one
  ending `_2056_5728.xyz.zip`. The national COG is not used (its bytes cannot be verified in part).
- Lock entry `swissaltiregio` {collection, edition, resolution_m, tiles: {<tile>: {file,
  sha256}}}, written only by `python -m mattini lock regio`; `download regio` writes
  `swissaltiregio/<edition>/` with a provenance like the terrain's; the same refusal rules as
  every other input (SPEC §5).

### 1a. The source text (https://www.swisstopo.admin.ch/en/height-model-swissaltiregio, read 2026-10-17)

> Bundesamt für Landestopografie swisstopo; Tarquini S., I. Isola, M. Favalli, A. Battistini,
> G. Dotta (2023). TINITALY, a digital elevation model of Italy with a 10 meters cell size
> (Version 1.1). Istituto Nazionale di Geofisica e Vulcanologia (INGV).
> https://doi.org/10.13127/tinitaly/1.1; DGM Österreich, geoland.at; DGM1, Bayerische
> Vermessungsverwaltung – www.geodaten.bayern.de; DGM1, Baden-Württemberg: LGL, www.lgl-bw.de,
> dl-de/by-2-0; RGEAlti, Institut National de l'information géographique et forestière, données
> originales téléchargées sur https://geoservices.ign.fr/rgealti#telechargement5m, mise à jour
> du juillet 2023

(The published page has a stray closing quote after `dl-de/by-2-0` and the typo
"tétéchargées"; design's reading: both are typos, corrected above. The terms: "may be used,
distributed and made accessible … enriched and processed and also used commercially. A reference
to the source is mandatory.")

## 2. The surroundings step (brief M4-02)

The heights of the mountains around the area, for a shadows-only mesh (§7).

- `config/surroundings.json` (design data): `margin_m` 20000, `spacing_m` 100, per area the
  expected values and `computed_for` {inputs_sha256 (the `swissaltiregio` lock entry), world_sha256}.
- **The box:** the area box grown by `margin_m` on every side. The village: E 2603000–2645000,
  N 1075000–1118000; 421 columns × 431 rows. `margin_m` and the area's corners are multiples of
  `spacing_m` (refused otherwise).
- **A vertex** every `spacing_m` from the box's north-west corner, edges included: row r, column
  c is (e_min + c·s, n_max − r·s), as the terrain's grid.
- **Its height:** the largest swissALTIRegio height among the samples whose position lies in the
  half-open square [E − s/2, E + s/2) × [N − s/2, N + s/2) (a shadow caster keeps its peaks),
  minus `height_offset_m` (local y, as the terrain), rounded once to float32. A vertex with no
  sample is refused naming the vertex and `download regio`.
- **The cut:** a vertex strictly inside the area box (e_min < E < e_max and n_min < N < n_max)
  is NaN; vertices on the box's edge keep their height (they meet the terrain's edge). Measured:
  without the cut the coarse mesh shadows the real terrain in blotches.
- **Files:** `surroundings/<area>.f32` (little-endian float32, rows north to south, columns west
  to east, no header) and `surroundings/<area>.json` {area, columns, file, format "f32-le",
  lv95_box (the surroundings box), cut_box (the area box), rows, sha256, source {attribution,
  collection, dataset, edition, entry_sha256}, spacing_m, world_sha256}, each through a `.part`
  rename; design's SHA-256 compared before writing, as the terrain (lesson 38).

## 3. The capture shadows step (brief M4-03)

Where the photo was in shadow when it was flown, for the terrain shader's lift (§6).

- `config/shadows.json` (design data): `cell_m` 1; `sun` {azimuth_grid_deg 184.67,
  elevation_deg 50.1, note: the flight's mean sun, 2023-09-06/07 11:25–11:55 UTC, true azimuth
  184.9 + true_to_grid −0.2258}; `threshold_m` 0.05; per area expected `pixels_sha256` and
  `png_sha256` and `computed_for` {inputs_sha256 (the `swisssurface3d` lock entry),
  world_sha256}.
- **The surface:** swissSURFACE3D's 0.5 m tiles over the area, mosaicked; each 1 m cell (aligned
  to the area's north-west corner) takes the largest of its 2 × 2 source pixels, in float64.
- **Cast shadow:** with A the grid azimuth and e the elevation, for k = 1 … K the point
  p + k·(sin A, cos A) metres (east, north) from the cell centre p; the surface there by
  bilinear interpolation of the 1 m cell centres (a point outside the grid casts nothing);
  the cell is in shadow if, for any k, surface(k) > h(p) + k·tan e + threshold_m.
  K = ceil((max − min) / tan e) over the area's cells.
- **Own shadow:** the normal from central differences (one-sided at the edges); a cell whose
  normal · sun ≤ 0 is in shadow.
- **Inset, at 0.5 m** (ruled after M4-03's rehearsal: a 1 m inset kept 20 % of 32 %): each 1 m
  cell becomes its 2 × 2 cells of 0.5 m (`cell_m` 0.5, `march_cell_m` 1); a 0.5 m shadow cell stays
  255 only if its four neighbours inside the grid are shadow too; every other cell 0 (the feather is the shader's bilinear filter, which then stays inside the
  shadow: a centred feather lit the ground beside it by 1.53×, measured).
- **Files:** `shadows/<area>.png` (8-bit grey, 4000 × 6000 for the village, rows north to south, the surfaces' PNG writer and
  its zlib rule, `expected_png_sha256`, brain.md H27), `shadows/<area>.png.import` holding exactly
  `[remap]\n\nimporter="keep"\n` (H24), `shadows/<area>.json` {area, cell_m, columns, file,
  format "png-l8", lv95_box, pixels_sha256, rows, sha256, source {…}, sun {…}, world_sha256}.
- Outside the area nothing casts (the horizon at azimuth 185° is about 17°, below 50.1°).

## 4. The sky block (brief M4-09, design data `config/sky.json`)

- `config/sky.json`: per area `latitude_deg`, `longitude_deg` (WGS84 of the area box's centre)
  and `true_to_grid_deg` (added to an azimuth from true north it gives the azimuth from LV95
  grid north at the centre: −0.2258 for the village), with `computed_for` {world_sha256}.
  Computed by design with pyproj; a pipeline test recomputes them with swisstopo's published
  approximate LV95→WGS84 formulas (no new dependency): latitude and longitude within 1e-4°, the
  convergence within 0.01°.
- The manifest's `sky` block copies them with `world_sha256`; the game reads the sun's place
  only from there (Hard Rule 4: the world config stays the one home of the origin and axes; this
  is derived data with its `computed_for`, like every expected value).

## 5. The sky clock (brief M4-04): `game/scripts/sky/sky_clock.gd`, `class_name SkyClock`

Static, headless, pure. Times are Unix seconds UTC (float).
- `START_UNIX` = 2023-09-06T11:40:00Z (13:40 CEST), the photo's moment (SPEC §13 row 43).
- `zurich_offset_s(unix) -> int`: 7200 from the last Sunday of March 01:00 UTC to the last
  Sunday of October 01:00 UTC, else 3600 (Swiss SR 941.299.1 = the EU rule; a table-free rule,
  one function, so a change is one edit).
- `local_text(unix) -> String`: "6 Sep 2023 13:40 CEST" (day without leading zero, English
  three-letter month, 24-hour, CET or CEST).
- `sun(unix, lat_deg, lon_deg) -> Vector2(azimuth_true_deg, elevation_deg)`: NOAA's solar
  position (Meeus), apparent elevation with NOAA's refraction; azimuth clockwise from true
  north in [0, 360).
- `moon(unix, lat_deg, lon_deg) -> Vector3(azimuth_true_deg, elevation_deg,
  illuminated_fraction)`: Paul Schlyter's method ("How to compute planetary positions") with
  the moon's main perturbation terms and topocentric parallax; our own code, the source named
  in a comment.
- `sidereal_deg(unix, lon_deg) -> float`: local mean sidereal time in degrees [0, 360).
- Tolerances against `tests/shared/sky_vectors.json` (design data: the sun by pvlib's SPA,
  the moon by skyfield with DE421, sidereal time by skyfield): sun 0.05° where elevation > 2°,
  0.3° from −5° to 2°; moon 0.5° in azimuth·cos(elevation) and elevation, fraction 0.03;
  sidereal 0.01°; offsets and texts exact.

## 6. The sky rig (brief M4-05): `game/scripts/sky/sky_rig.gd`, `class_name SkyRig`

Turns the clock's angles into the scene's light. Directions arrive as local unit vectors
(main converts azimuth and elevation through WorldConfig, §9; Tier 1).
- **Sun light:** energy 1.0 at elevation ≥ 10°, smoothstep to 0 at −1°; hidden below −1°;
  colour white at ≥ 10°, mixed linearly to (1.0, 0.72, 0.50) at 0°; shadows on as today
  (max distance 3000).
- **Moon light** (a second DirectionalLight3D, `sky_mode` light only, shadows on): energy
  0.03 × illuminated fraction × smoothstep(0°, 5°, moon elevation); colour (0.80, 0.85, 1.0);
  hidden below 0°.
- **Exposure:** 0.54 at sun elevation ≥ 10°, 4.0 at ≤ −12°, between them interpolated in log
  space against elevation. Ambient: the sky, contribution 0.25 (M3's calibration).
- **The sky:** Godot's PhysicalSkyMaterial converted to a sky shader (its code kept, MIT,
  Godot's licence already in the credits) with one change: the night sky's contribution times
  `stars_strength` = 0 at sun elevation ≥ −6°, 1 at ≤ −12°, smoothstep between.
- **Stars** (only with the owner's catalogue answer, §10): the star table's stars drawn into an
  equirectangular image in celestial coordinates; the sky shader turns EYEDIR into right
  ascension and declination with a `celestial_basis` from local sidereal time, the latitude and
  the local east/north/up. Pinned: Polaris stands at the latitude's elevation (±0.5°) in the
  north at any time.
- **Calibration kept:** at the photo's sun (start), flat sunlit ground renders at the photo's
  brightness within ±10 % in software Forward+ (H12; M3 measured 1.06× under Compatibility).

## 7. The far mountains in the game (brief M4-07)

- `SurroundingsGrid.from_manifest(path, world)` reads the `surroundings` block and its `.f32`
  (SHA-256, size, world guard as every reader, H26 typed compares).
- `SurroundingsLoader.create(grid, parent) -> MeshInstance3D` named "Surroundings":
  `cast_shadow = SHADOW_CASTING_SETTING_SHADOWS_ONLY`, two triangles per grid square whose four
  vertices are finite (front faces clockwise, H16), positions through WorldConfig (64-bit
  subtraction first, H5), unturned at the scene's origin. Nothing visible: the far mountains are
  drawn in M5.

## 8. The terrain's look (brief M4-06)

- `CaptureShadowGrid.from_manifest` reads the `shadows` block and PNG like `SurfaceGrid`.
- `terrain_photo.gdshader`: `capture_shadow` (filter_linear, repeat_disable) and its rect;
  `shadow_lift` 3.0: the photo's linear colour × (1 + (shadow_lift − 1)·m), m the mask in 0..1,
  before every other surface rule.
- **Water:** albedo × 0.9 (was 0.6), roughness 0.3 (was 0.05), two normal maps at 2 m and
  3.4 m drifting at 0.8 m/s in opposite directions (no single world direction: a torrent's
  turbulence), strength 0.35; the water weight eased over 1 m at the bank (the class sampled
  over a 5 × 5 texel box). Water draws at every distance as today.
- The gate's render step gains `RENDER lift`: where the lift lands on the complete test world,
  by the same correlation as the photo (flips, half texels and 0.1 m shifts fail it).

## 9. The main scene (brief M4-10)

- The clock starts at `SkyClock.START_UNIX`, running at 1×.
- Keys (InputMap): `time_earlier` (comma) and `time_later` (period) ∓15 minutes;
  `day_earlier` ([) and `day_later` (]) ∓1 day; `time_speed` (T) cycles 1×, 60×, 600×,
  stopped; `time_now` (N) the computer's clock. A label `UI/Clock` bottom left,
  "6 Sep 2023 13:40 CEST · 1×", shown 4 s after a time key and always while paused.
- Every frame: sun and moon from the clock and the manifest's `sky` block; azimuth true →
  grid (+ `true_to_grid_deg`) → local through WorldConfig's east, north and up (as M3's sun);
  the rig applies them. At the start view the sun stands at grid azimuth about 184.7°, 50.1°.
- Pause: time stops; `Engine.max_fps` 15 while the pause screen is open, the project's 60 when
  it closes.
- "Surroundings" and the capture mask from their readers; refusals on the error panel ("the
  mountains' shadows", "the photo's softened shadows") with their commands; DataPacks' errors
  on the panel too. Startup lines after the roofs: surroundings, shadows.
- Credits: swissALTIRegio's source text whole; the star catalogue's citation (if stars); the
  sun and moon formulas' sources.

## 10. Open with the GO: the star catalogue

No candidate's licence is unambiguous (the research of 2026-10-17): Hipparcos is
CC BY-NC 3.0 IGO (non-commercial: refused); the Yale Bright Star Catalogue (BSC5, 9'110 stars,
NASA/ADC, CDS V/50) states no licence anywhere authoritative, cite Hoffleit & Warren (1991);
HYG v4.4 is CC BY-SA 4.0 but built on Hipparcos. Options for the owner: (a) BSC5 with its
citation, the licence question on the board before any commercial release; (b) no stars until a
clean source is confirmed (night with the moon only).
