# Brief: M4-05 — The sky rig
Status: OPEN

Written in the design realm; executed by one fresh builder session under
`docs/roles/BUILD.md`. Lane E of wave 1 of arc M4.

## Goal

The scene's light follows the sun and the moon wherever they stand.

- **`SkyRig`** (`game/scripts/sky/sky_rig.gd`) takes the directions towards the sun and the
  moon, as local unit vectors, and sets the sun light, a moon light, the exposure and the sky.
- **The sky** is Godot's physical sky converted to a sky shader
  (`game/shaders/sky_physical.gdshader`), with a twilight towards the sun from +6° to −12°, a
  faint glow of the night sky, the sun's disk, and a night sky that fades in after dusk.
- **The stars** (section S, only with the owner's catalogue answer, m4-design §10 option (a)):
  the Yale Bright Star Catalogue's stars to magnitude 6, drawn at their real places for the
  time and the latitude.

The rig is built and tested on its own nodes. The main scene uses it from M4-10 (wave 2), which
converts the clock's azimuths and elevations into local vectors through WorldConfig.

## Read first, in order

1. `CLAUDE.md` (Hard Rules 2, 3); `brain.md` H3, H9, H12 (software Forward+), H21 (colour),
   H24 (a `.import` that keeps a file), H25 (shader declarations headless; `timeout`).
2. `docs/briefs/sketches/m4-design.md` §0 (*Sky*), §6 (this brief), §10 (the catalogue).
3. `game/main.tscn`, `game/scripts/main.gd` (`_read_directions`, `_place_sun`: how M3 builds a
   direction from east, north and up), `game/tests/test_main_scene_light.gd` (M3's light).
4. Godot 4.6.3's `scene/resources/3d/sky_material.cpp`, `PhysicalSkyMaterial::_update_shader`
   (lines 728–821 at tag `4.6.3-stable`; `git clone --depth 1 --branch 4.6.3-stable
   --filter=blob:none --sparse https://github.com/godotengine/godot`, then `git
   sparse-checkout set scene/resources`). The headless editor cannot hand out a material's
   shader code (`get_shader_rid` is not exposed): convert from the source.
5. The pinned tests: `docs/briefs/pinning/M4-05/` (`test_m4_05_sky_rig.gd`; section S:
   `test_m4_05_stars.gd`).

## Decisions already made

1. **The rig.** `class_name SkyRig`, `extends RefCounted`.
   - `static func create(sun: DirectionalLight3D, moon: DirectionalLight3D, environment:
     Environment, frame: Basis, latitude_deg: float, stars: Image = null) -> SkyRig`. `frame`'s
     columns are the scene's local east, north and up (main: `Basis(_east, _north, _up)`). It
     sets what never changes: the sun's shadows on, `directional_shadow_max_distance` 3000,
     `light_angular_distance` 0 (sharp shadows, as today; design's ruling of 2026-10-17, for
     the reason measured in decision 4c: the sky draws the sun's disk from its own uniform);
     the moon's shadows on, `sky_mode` `SKY_MODE_LIGHT_ONLY` (so the sun stays the sky's
     `LIGHT0`), colour (0.80, 0.85, 1.0); the environment's background the sky, a `Sky` whose
     material is a `ShaderMaterial` of `res://shaders/sky_physical.gdshader` (property
     `sky_material` of the rig), ambient light from the sky with contribution 0.25, Filmic.
     With `stars`, an `ImageTexture` of it is the material's `night_sky`.
   - `func apply(to_sun: Vector3, to_moon: Vector3, moon_fraction: float, sidereal_deg:
     float) -> void`, every frame. Each elevation is `asin(direction · up)` of the frame's up,
     never the scene's y. Each light's basis is `Basis.looking_at(-direction, up)` (it shines
     along its −z, as M3's sun). It sets the sky material's `stars_strength`, `sun_direction`
     (`to_sun` normalised, every frame, also while the sun light is hidden),
     `twilight_colour` (decision 4b) and (section S) `celestial_basis`.
2. **The curves** (m4-design §6), all against the elevation in degrees:
   - sun energy `smoothstep(-1, 10, e)`; hidden below −1; colour white at 10 and above,
     mixed linearly to (1.0, 0.72, 0.50) at 0, kept below 0;
   - moon energy `0.03 × fraction × smoothstep(0, 5, e)`; hidden below 0;
   - exposure 0.70 at a sun elevation of 10 and above, 4.0 at −12 and below,
     `exp(lerp(ln 0.70, ln 4.0, (10 − e) / 22))` between;
   - `stars_strength` `1 − smoothstep(-12, -6, e)` of the sun;
   - `twilight_colour` (a `Vector3`) = t(e) × colour(e) of the sun, t = `smoothstep(-12, -4,
     e) × (1 − smoothstep(0, 6, e))`, colour (1.00, 0.55, 0.30) at 0 and above, linear to
     (0.35, 0.30, 0.55) at −6, linear to (0.05, 0.06, 0.12) at −12 (design's ruling of
     2026-10-17). Computed by the rig in GDScript and passed as a uniform, so the pinned test
     reads the real function, not a mirror of shader code: 0.5 × sunset at +3°, (0.675,
     0.425, 0.425) at −3°, 0.84375 × (0.35, 0.30, 0.55) at −6°, 0 at +6° and −12°.
3. **The day exposure is 0.70, not m4-design §6's 0.54** (design's rehearsal, 2026-10-17). §6
   asks that flat sunlit ground at the photo's sun render at the photo's brightness within
   ±10 % in software Forward+; measured with this rig (flat ground of albedo sRGB 128,
   roughness 0.95, the sun at grid azimuth 185.13°, 50.1°, the start's moon; camera straight
   down; linear luminance of a 64 × 64 px centre, rendered over albedo):

   | light | Forward+ (lavapipe) | Compatibility (llvmpipe) |
   |---|---|---|
   | M3's (procedural sky, sun 183°/52°, exposure 0.54) | 0.808 | 1.060 (M3 measured 1.063) |
   | this rig, exposure 0.54 | 0.766 | 0.736 |
   | this rig, exposure 0.70 | **1.001** (twice) | 0.967 |

   So 0.54 was a Compatibility calibration: under Forward+, the owner's renderer, 0.3.0's
   ground renders at about 0.81 of the photo. The physical sky lights flat ground a little
   less than M3's procedural sky did.
4. **The sky shader** is Godot's generated code with `p_use_debanding` and `p_use_night_sky`
   true, its `%s` filled as Godot fills them (`render_mode use_debanding;`), every other line
   kept, and these changes only, each marked `// mattini:` in a comment:
   - two uniforms after `night_sky`: `uniform float stars_strength : hint_range(0, 1) = 0.0;`
     and (section S) `uniform mat3 celestial_basis = mat3(1.0);`;
   - both night-sky lines multiply by `stars_strength`: `L0 += texture(night_sky, …).xyz *
     extinction * stars_strength;` and `COLOR = texture(night_sky, …).xyz * stars_strength;`;
   - (section S) the night sky is sampled at the celestial coordinates of `EYEDIR`, not
     `SKY_COORDS`: `c = celestial_basis * EYEDIR`, `uv = (fract(atan(c.y, c.x) / TAU),
     acos(clamp(c.z, -1, 1)) / PI)` (u = right ascension / 360, v = (90° − declination) /
     180°). Without section S the two lines keep `SKY_COORDS`.
   - twilight and glow (design's rulings of 2026-10-17), four uniforms declared exactly
     `uniform vec3 sun_direction = vec3(0.0, 1.0, 0.0);`, `uniform vec3 twilight_colour =
     vec3(0.0);`, `uniform float twilight_energy : hint_range(0, 16) = 0.3;`, `uniform vec3
     skyglow = vec3(0.004, 0.005, 0.009);`; a function before `sky()`, exactly:
     ```glsl
     vec3 twilight_and_glow(vec3 dir) {
     	vec2 eye_h = dir.xz;
     	vec2 sun_h = sun_direction.xz;
     	float facing = 0.0;
     	if (length(eye_h) > 1e-5 && length(sun_h) > 1e-5) {
     		facing = max(0.0, dot(normalize(eye_h), normalize(sun_h)));
     	}
     	float eye_elevation = degrees(asin(clamp(dir.y, -1.0, 1.0)));
     	float shape = (0.3 + 0.7 * pow(facing, 3.0)) * exp(-max(0.0, eye_elevation) / 12.0);
     	return twilight_colour * twilight_energy * shape + skyglow;
     }
     ```
     and `COLOR += twilight_and_glow(EYEDIR);` as the line just before each of Godot's two
     `COLOR *= exposure;` (the sun's branch and the night's). "Horizontal" and "elevation"
     use the shader's y as up, as Godot's own `UP` does.
   - the sun's disk (design's ruling of 2026-10-17): `uniform float sun_disk_deg :
     hint_range(0, 5) = 0.53;` declared after `skyglow`, and Godot's three disk lines
     replaced, exactly:
     ```glsl
     float sunAngularDiameterCos = cos(radians(sun_disk_deg) * sun_disk_scale);
     float sunAngularDiameterCos2 = cos(radians(sun_disk_deg) * sun_disk_scale * 0.5);
     float sundisk = smoothstep(sunAngularDiameterCos, sunAngularDiameterCos2, dot(EYEDIR, normalize(sun_direction)));
     ```
     (Godot's read `LIGHT0_SIZE`, which is 0 with the light's angular distance 0, so no disk,
     and `cos_theta`). `LIGHT0_SIZE` then appears nowhere in the shader. The disk is drawn only
     in Godot's lit branch, so only while the sun light is shown (from −1°).
   The first comment line stays Godot's ("Shader automatically converted from Godot Engine
   4.6.3.stable's PhysicalSkyMaterial"); Godot's licence is in the credits already (MIT).
4a. **Why `sun_direction` is a uniform** (measured 2026-10-17 in Forward+ and Compatibility,
   a sky shader painting `LIGHT0_ENABLED` and the sign of `LIGHT0_DIRECTION.y`): a visible sun
   10° below the horizon is the sky's LIGHT0 with its direction; a hidden one is not
   (`LIGHT0_ENABLED` false); a visible one of energy 0 still is. The rig hides the sun below
   −1°, so the twilight from −1° to −12° needs the direction from the rig.
4b. **What design measured** (software Forward+, lavapipe, the rig's exposure):
   - `twilight_energy` 0.3: sun at −3° (exposure 1.96), view 5° above the horizon towards the
     sun sRGB (184, 150, 158), 15° up (127, 101, 109), 30° up (60, 64, 58); away from the sun
     at 5° (114, 84, 100). 0.2 gave (158, 125, 136) and 0.4 (202, 169, 175), close to washing
     out at the horizon. Continuous across the sun light's hiding: 5° up towards the sun
     (192, 151, 130) at −0.5°, (189, 151, 141) at −1.5°; (153, 123, 107) at +3°; at −9°
     (92, 71, 120).
   - The night: flat ground of albedo sRGB 128, sun −30°, moon −20°, exposure 4.0, stars
     unbound: rendered at 0.0057 of its albedo's linear luminance, sRGB (3, 4, 8): dark but
     not zero; the ambient comes from `skyglow` alone.
   - The day calibration does not move: 1.0012 (decision 3) with the glow and the disk.
4c. **Why the disk is the sky's, not the light's** (design first ruled `light_angular_distance`
   0.5 and reversed it on this measurement, 2026-10-17). Measured with the disk as built (the
   light at 0, `sun_disk_deg` 0.53): the box's shadow at 100 m is 0.054 with a 0.34 m edge,
   the 0° values below; the sun at +10° (azimuth 270, a view 15° up, fov 60) peaks at sRGB
   (174, 162, 141) where `sun_disk_deg` 0 gives (142, 139, 134), the sky 20 px aside
   (137, 137, 131). The measurement that decided it (Forward+, lavapipe; a 20 × 20 × 200 m box,
   the photo's sun; the 10 %–90 % width of its shadow's side edge where the edge is cast
   from 144 m up; the real 0.5° penumbra there is about 1.6 m):
   | camera, looking straight down | angular 0 | angular 0.5° |
   |---|---|---|
   | 100 m up, fov 10° (0.034 m/px) | edge 0.34 m, shadow 0.054 (lit 0.502) | edge 0.44 m, **shadow interior 0.306** |
   | 2000 m up, fov 10° (0.68 m/px) | edge 0.68 m (one pixel) | **edge 11.6 m** |
   | 2900 m up, fov 10° (0.99 m/px) | shadow nearly faded (0.485) | the same, edge about 6 m |
   Godot's soft directional shadows over-soften at this scale: near the camera the 20 m
   wide shadow lets about half the light through; at 2 km its edge is seven times the real
   penumbra. At 2.9 km both settings have almost no shadow: Godot fades directional shadows
   from `directional_shadow_fade_start` (0.8) of the 3000 m distance.
4d. **Risk, carried to M4-10 by design:** in the shadow probe, a camera looking straight down
   with a narrow view (fov 10° or less) that does not hold the caster drew no shadow at all
   once it was 300 m up or more (from 300 m to 2900 m, with either angular distance), while at
   100 m and 200 m it did; with a view that holds the caster (fov 10° at 2000 m and 2900 m,
   30° at 1000 m) the shadow is there. Not understood; plausibly the caster culled for the
   cascades beyond the first. Harm if it holds in the game: shadows of things out of view
   (the far mountains of M4-07 at the edge of a narrow view) missing. Not this brief's to
   fix; M4-10's render check should look at it.
5. **Testing headless:** the curves through the nodes after `apply`; the shader's
   declarations through `Shader.get_shader_uniform_list()` (H25); the material's parameters
   through `get_shader_parameter`; Godot's code by a census of its lines, in order
   (`test_the_sky_shader_keeps_godots_code`: it proves the text, not what draws). The
   uniforms' defaults cannot be read headless (`RenderingServer.shader_get_parameter_default`
   and an unset `get_shader_parameter` return null for every uniform, measured), so the
   twilight's declarations and function are a census of their exact text
   (`test_the_sky_shader_adds_twilight_and_glow_before_each_exposure`).

### Section S — the stars (option (a) of m4-design §10; drop the whole section for (b))

6. **The catalogue:** the Yale Bright Star Catalogue, 5th revised edition (Hoffleit and Warren
   1991), CDS V/50, `https://cdsarc.cds.unistra.fr/ftp/cats/V/50/catalog.gz`: 573'921 bytes,
   SHA-256 `3dc44b1e90be8fbe5bcc7656032560f51275f985c7e3f783c9028e1838ec7bed` (Last-Modified
   1993-10-04; fetched 2026-10-17). 9110 records of up to 197 bytes (trailing blanks cut: pad
   before slicing); per its ReadMe, 1-based bytes 76–77 RAh, 78–79 RAm, 80–83 RAs (F4.1), 84
   the declination's sign, 85–86 DEd, 87–88 DEm, 89–90 DEs (J2000, epoch 2000), 103–107 Vmag
   (F5.2). 14 records have no J2000 position (novae, clusters: HR 92, 95, 182, 1057, 1841,
   2472, 2496, 3515, 3671, 6309, 6515, 7189, 7539, 8296): skipped. Its licence states nothing
   (§10): the question goes on the board before any commercial release. The credits (M4-10)
   cite: "Stars: The Bright Star Catalogue, 5th Revised Ed. (Hoffleit, D., Warren, W. H. Jr.,
   1991), NASA/ADC, CDS V/50."
7. **The table** `game/sky/stars.csv`, made by `tools/stars_table.py` (the builder's; Python
   standard library only, run with `python3 -I`): it reads `catalog.gz` from a path given (the
   builder downloads it under `data/`, which git ignores; it is never committed), refuses
   another size or SHA-256, and writes:
   - the header `ra_deg,dec_deg,vmag`;
   - per star with a J2000 position, a V and V ≤ 6.0: `ra = (h + m/60 + s/3600) * 15`, `dec =
     sign * (d + m/60 + s/3600)` (floats, in that order), written `f"{ra:.4f},{dec:.4f},
     {v:.2f}"`;
   - sorted by the written V, then right ascension, then declination, as numbers;
   - LF endings and a final LF. Expected: 5080 stars, 112'127 bytes, SHA-256
     `2281ac5417e1aeadb94f2c611ec01daea1e2b766a22ae45e874cb54dcc30bc9e` (design computed it
     twice, with a Python and an awk program: the same bytes). The script prints the SHA-256.
   - Beside it `game/sky/stars.csv.import` holding exactly `[remap]\n\nimporter="keep"\n`:
     measured, without it Godot imports a `.csv` as translations (`stars.dec.translation`,
     `stars.vmag.translation` written beside it) and an export ships those, not the table.
8. **The star image:** `static func star_image(path: String) -> Image`: 4096 × 2048,
   `FORMAT_RGBE9995` (Sirius at 3.8 and a 6th-magnitude star at 0.004 in one 4-byte texel;
   32 MiB), no mipmaps; each star adds 10^(−0.4 V) to red, green and blue of row
   `min(floor((90 − dec) / 180 × 2048), 2047)`, columns `c − h … c + h` wrapped, `c =
   floor(ra / 360 × 4096) mod 4096`, `h = floor(0.5 / cos(dec))`. The run keeps a star about
   one texel high wide at any declination: measured under Forward+, with one texel per star
   Polaris's texel is 0.001° wide and nothing shows; with the run it is the brightest pixel,
   two pixels from the centre of a 10° view aimed at it.
9. **`celestial_basis`**, set by `apply`: the Basis turning a scene direction into celestial
   coordinates (x towards RA 0 on the equator, y towards RA 90°, z the north celestial pole).
   With east E, north N, up U, latitude φ and sidereal time θ: pole P = N cos φ + U sin φ,
   the equator's meridian point Q = U cos φ − N sin φ, X = Q cos θ − E sin θ, Y = Q sin θ +
   E cos θ; the basis whose rows are X, Y, P (`Basis(X, Y, P).transposed()`). Measured under
   Forward+ with a coordinate image (red = u, green = v): a view aimed at RA 123°, Dec 20°
   read RA 123.09°, Dec 20.44° at its centre (8-bit quantisation): the uniform reaches GLSL
   as GDScript multiplies it, neither mirrored nor transposed.
10. **Polaris and the pole.** m4-design §6 pins Polaris at the latitude's elevation ±0.5° at
    any time; Polaris is 0.74° from the pole (J2000), so it swings ±0.74°: the pinned test holds
    the pole there to 0.001° at five sidereal times, and Polaris where its hour angle puts it
    (0.01°) and within 1° of the latitude.

## Scope — files you may touch

- `game/scripts/sky/sky_rig.gd` and its `.uid` (new);
- `game/shaders/sky_physical.gdshader` and its `.uid` (new);
- section S: `game/sky/stars.csv`, `game/sky/stars.csv.import` (new), `tools/stars_table.py`
  (new);
- `game/tests/`: the pinned `test_m4_05_sky_rig.gd` and (section S) `test_m4_05_stars.gd` (new,
  with `.uid`), and your own new tests.

Not `main.gd`, `main.tscn` or `project.godot` (M4-10 wires the rig and replaces M3's fixed sun
and `test_main_scene_light.gd`'s exposure 0.54, procedural sky and fixed angles: the seam of
wave 2); nothing under `game/scripts/sky/` but this file (lane D writes `sky_clock.gd`).

## Depends on

None. The tests pass directions and a sidereal time directly; the rig never calls `SkyClock`
(M4-04, lane D).

## Done when (gates)

- [ ] The pinned copies are in place (`docs/briefs/pinning/M4-05/game/tests/*.gd` copied to
      `game/tests/`) and stay byte-identical (`cmp`). For option (b): only
      `test_m4_05_sky_rig.gd`.
      - does NOT prove: that they are the right tests.
- [ ] Section S: `python3 -I tools/stars_table.py <catalog.gz> game/sky/stars.csv` run twice
      writes the same file, SHA-256 `2281ac54…` both times; a catalogue with one byte changed
      is refused before anything is written.
      - does NOT prove: the catalogue's licence, or that a star is where the sky shows it.
- [ ] Mutations, each applied alone, each failing a named pinned test, recorded with the harm
      it reproduces: the elevation from the scene's y; the exposure interpolated linearly; the
      sun never hidden; the moon's sky mode left as default; `stars_strength` not inverted;
      the sun's colour mix reversed; `stars_strength` dropped from the night branch;
      `sun_direction` set only while the sun is shown; the twilight not faded above the
      horizon; its −6° to 0° segment reversed; the glow missing from the sun's branch; the
      light's angular distance set to 0.5; the disk left at `LIGHT0_SIZE`; section S:
      the basis not transposed; one texel per star; the night sky sampled at `SKY_COORDS`.
      - does NOT prove: what the sky looks like.
- [ ] **The calibration, measured in software Forward+** (H12: `VK_ICD_FILENAMES=/usr/share/
      vulkan/icd.d/lvp_icd.json xvfb-run -a godot --path game --rendering-driver vulkan
      --rendering-method forward_plus --audio-driver Dummy --resolution 512x512 -s
      <probe>.gd`, the probe a SceneTree script kept in scratch, never committed): a 4000 m
      plane with a `StandardMaterial3D` of albedo `Color8(128, 128, 128)` and roughness 0.95,
      the rig created and applied with the sun at grid azimuth 185.13°, elevation 50.1° in the
      owner's frame (east +x, north −z, up +y) and the moon at 295.96°, 9.16°, fraction 0.553,
      sidereal 168.06°; a camera 100 m up looking straight down, fov 30; after 30 frames the
      mean linear luminance (Rec. 709) of the centre 64 × 64 pixels over the albedo's linear
      0.2159 is within 0.90 to 1.10. Record the number in Findings (design: 1.0012).
      - does NOT prove: the look on the owner's GPU, the photo's own brightness (a flat grey
        stands in for it), or any other sun height.
- [ ] The same recipe, recorded in Findings beside design's numbers (decision 4b): the sun at
      −3° (grid azimuth 270), a camera 10 m up, fov 60, looking towards the sun 15° up: the
      sky 5° above the horizon towards the sun brighter than away from it, and visibly
      coloured; the night ground (sun −30°, moon −20°) above zero; the sun at +10° shows a
      disk brighter than the sky beside it (and than with `sun_disk_deg` 0); decision 4c's box
      shadow at 100 m at the 0° value (0.054).
      - does NOT prove: that the twilight looks right; it is a look value the owner judges.
- [ ] Optional (section S), the same recipe: night (sun −30°), a 10° camera aimed at Polaris
      through the rig's basis; the brightest pixel within 3 px of the centre; none above the
      background with `stars_strength` 0. Record it.
      - does NOT prove: how the stars look.
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that it renders or looks right, or anything about the main scene
        (M4-10).

## Forbidden

Touching the main scene or `project.godot`; changing Godot's sky code beyond decision 4;
an angular distance on the sun light other than 0, or another shadow setting than decision
1's (decision 4c);
auto exposure (m4-design §0: Forward+ only, and it turned the night into day); another star
catalogue (Hipparcos and HYG: m4-design §10); committing `catalog.gz`; a new dependency; editing
a pinned file.

## Findings (executor writes)
