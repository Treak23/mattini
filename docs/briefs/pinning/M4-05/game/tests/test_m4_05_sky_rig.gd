extends GutTest
## Pinning tests for brief M4-05: the sky rig turns the sun's and the moon's directions into
## the scene's lights, exposure and sky.
##
## Pinned decisions (m4-design §6, as decided on 2026-10-17): SkyRig
## (game/scripts/sky/sky_rig.gd) is made by SkyRig.create(sun, moon, environment, frame,
## latitude_deg, stars: Image = null), frame a Basis whose columns are the scene's local east,
## north and up (main measures them through WorldConfig, as M3's sun). rig.apply(to_sun,
## to_moon, moon_fraction, sidereal_deg) takes unit vectors towards the sun and the moon and
## measures each elevation against the frame's up, never the scene's y.
## - Sun: energy smoothstep(-1, 10, elevation): 1.0 at 10 degrees and above, 0 at -1; hidden
##   below -1; colour white at 10 and above, mixed linearly to (1.0, 0.72, 0.50) at 0 and kept
##   below; shadows on, max distance 3000 m. The light shines along its -z, from the sun.
## - Moon (a second DirectionalLight3D, sky mode light only, shadows on): energy 0.03 times the
##   illuminated fraction times smoothstep(0, 5, elevation); colour (0.80, 0.85, 1.0); hidden
##   below 0.
## - Exposure 0.70 at a sun elevation of 10 degrees and above, 4.0 at -12 and below,
##   interpolated in log space against the elevation (at -1 degrees: sqrt(0.70 * 4.0) = 1.6733;
##   linear would be 2.35). 0.70, not m4-design §6's 0.54: design's rehearsal measured flat
##   sunlit ground at the photo's sun at 0.766 of the photo's brightness with 0.54 and 1.001
##   with 0.70 (software Forward+, lavapipe; Compatibility 0.736 and 0.967), and §6 asks for
##   1.0 +- 10 % in Forward+. Ambient light from the sky, contribution 0.25; Filmic, as M3 was
##   calibrated; the sky is the background.
## - The sky: a ShaderMaterial of res://shaders/sky_physical.gdshader, Godot 4.6.3's
##   PhysicalSkyMaterial converted (debanding and the night sky on) with its code kept, plus
##   `uniform float stars_strength`: 0 at a sun elevation of -6 degrees and above, 1 at -12 and
##   below, smoothstep between (0.5 at -9), multiplying both lines that add the night sky.
## The frame here is turned off every axis (no vector of it lies on x, y or z), so a rig that
## reads the scene's y as up or builds the light from fixed axes fails.
##
## Does NOT prove: that the sky or the lights render or look right (no GPU), that the shader
## draws what its text says (the census reads the text), or the calibration (the brief's
## Forward+ measurement).

const SHADER_PATH := "res://shaders/sky_physical.gdshader"
const EPS := 0.0001
## Godot 4.6.3's PhysicalSkyMaterial shader (scene/resources/3d/sky_material.cpp:735-819),
## every line but the comment naming the version and the three lines its code fills in
## (render_mode, the two night sky lines), stripped: each must appear in this order.
const GODOT_LINES: Array[String] = [
	"shader_type sky;",
	"uniform float rayleigh : hint_range(0, 64) = 2.0;",
	"uniform vec4 rayleigh_color : source_color = vec4(0.3, 0.405, 0.6, 1.0);",
	"uniform float mie : hint_range(0, 1) = 0.005;",
	"uniform float mie_eccentricity : hint_range(-1, 1) = 0.8;",
	"uniform vec4 mie_color : source_color = vec4(0.69, 0.729, 0.812, 1.0);",
	"uniform float turbidity : hint_range(0, 1000) = 10.0;",
	"uniform float sun_disk_scale : hint_range(0, 360) = 1.0;",
	"uniform vec4 ground_color : source_color = vec4(0.1, 0.07, 0.034, 1.0);",
	"uniform float exposure : hint_range(0, 128) = 1.0;",
	"uniform sampler2D night_sky : filter_linear, source_color, hint_default_black;",
	"const vec3 UP = vec3( 0.0, 1.0, 0.0 );",
	"const float rayleigh_zenith_size = 8.4e3;",
	"const float mie_zenith_size = 1.25e3;",
	"float henyey_greenstein(float cos_theta, float g) {",
	"const float k = 0.0795774715459;",
	"return k * (1.0 - g * g) / (pow(1.0 + g * g - 2.0 * g * cos_theta, 1.5));",
	"void sky() {",
	"if (LIGHT0_ENABLED) {",
	"float zenith_angle = clamp( dot(UP, normalize(LIGHT0_DIRECTION)), -1.0, 1.0 );",
	"float sun_energy = max(0.0, 0.757 * zenith_angle) * LIGHT0_ENERGY;",
	"float sun_fade = 1.0 - clamp(1.0 - exp(LIGHT0_DIRECTION.y), 0.0, 1.0);",
	"float rayleigh_coefficient = rayleigh - ( 1.0 * ( 1.0 - sun_fade ) );",
	"vec3 rayleigh_beta = rayleigh_coefficient * rayleigh_color.rgb * 0.0001;",
	"vec3 mie_beta = turbidity * mie * mie_color.rgb * 0.000434;",
	"float zenith = max(0.0, dot(UP, EYEDIR));",
	"float optical_mass = 1.0 / (zenith + 0.15 * pow(3.885 + 54.5 * zenith, -1.253));",
	"float rayleigh_scatter = rayleigh_zenith_size * optical_mass;",
	"float mie_scatter = mie_zenith_size * optical_mass;",
	"vec3 extinction = exp(-(rayleigh_beta * rayleigh_scatter + mie_beta * mie_scatter));",
	"float cos_theta = dot(EYEDIR, normalize(LIGHT0_DIRECTION));",
	"float rayleigh_phase = (3.0 / (16.0 * PI)) * (1.0 + pow(cos_theta * 0.5 + 0.5, 2.0));",
	"vec3 betaRTheta = rayleigh_beta * rayleigh_phase;",
	"float mie_phase = henyey_greenstein(cos_theta, mie_eccentricity);",
	"vec3 betaMTheta = mie_beta * mie_phase;",
	(
		"vec3 Lin = pow(sun_energy * ((betaRTheta + betaMTheta) / (rayleigh_beta + mie_beta))"
		+ " * (1.0 - extinction), vec3(1.5));"
	),
	(
		"Lin *= mix(vec3(1.0), pow(sun_energy * ((betaRTheta + betaMTheta) / (rayleigh_beta"
		+ " + mie_beta)) * extinction, vec3(0.5)), clamp(pow(1.0 - zenith_angle, 5.0), 0.0,"
		+ " 1.0));"
	),
	"Lin  *= mix(ground_color.rgb, vec3(1.0), smoothstep(-0.1, 0.1, dot(UP, EYEDIR)));",
	"float sunAngularDiameterCos = cos(LIGHT0_SIZE * sun_disk_scale);",
	"float sunAngularDiameterCos2 = cos(LIGHT0_SIZE * sun_disk_scale * 0.5);",
	"float sundisk = smoothstep(sunAngularDiameterCos, sunAngularDiameterCos2, cos_theta);",
	"vec3 L0 = (sun_energy * extinction) * sundisk * LIGHT0_COLOR;",
	"vec3 color = Lin + L0;",
	"COLOR = pow(color, vec3(1.0 / (1.2 + (1.2 * sun_fade))));",
	"COLOR *= exposure;",
	"} else {",
	"COLOR *= exposure;",
]
## Godot's uniforms and the one this brief adds, with their types (Variant.Type).
const UNIFORMS := {
	"rayleigh": TYPE_FLOAT,
	"rayleigh_color": TYPE_COLOR,
	"mie": TYPE_FLOAT,
	"mie_eccentricity": TYPE_FLOAT,
	"mie_color": TYPE_COLOR,
	"turbidity": TYPE_FLOAT,
	"sun_disk_scale": TYPE_FLOAT,
	"ground_color": TYPE_COLOR,
	"exposure": TYPE_FLOAT,
	"night_sky": TYPE_OBJECT,
	"stars_strength": TYPE_FLOAT,
}

var _root: Node3D
var _sun: DirectionalLight3D
var _moon: DirectionalLight3D
var _environment: Environment
var _frame: Basis
var _rig: SkyRig


## The owner's axes (east +x, north -z, up +y) turned about (1, 2, 3) by 0.7 rad: no axis of
## the frame lies on x, y or z.
func _turned_frame() -> Basis:
	var turn := Basis(Vector3(1.0, 2.0, 3.0).normalized(), 0.7)
	return Basis(turn * Vector3(1, 0, 0), turn * Vector3(0, 0, -1), turn * Vector3(0, 1, 0))


## The unit vector towards azimuth [param az] (clockwise from north) and elevation [param el].
func _towards(az: float, el: float) -> Vector3:
	var a := deg_to_rad(az)
	var e := deg_to_rad(el)
	return (_frame.x * sin(a) + _frame.y * cos(a)) * cos(e) + _frame.z * sin(e)


func before_each() -> void:
	_root = Node3D.new()
	_sun = DirectionalLight3D.new()
	_moon = DirectionalLight3D.new()
	_root.add_child(_sun)
	_root.add_child(_moon)
	add_child_autofree(_root)
	_environment = Environment.new()
	_frame = _turned_frame()
	_rig = SkyRig.create(_sun, _moon, _environment, _frame, 46.02)


## Applies the sun at elevation [param sun_el] (azimuth 140) and the moon at [param moon_el]
## (azimuth 250) with fraction [param fraction].
func _apply(sun_el: float, moon_el := 30.0, fraction := 1.0) -> void:
	_rig.apply(_towards(140.0, sun_el), _towards(250.0, moon_el), fraction, 77.0)


func _stars_strength() -> float:
	return float(_rig.sky_material.get_shader_parameter("stars_strength"))


func test_the_lights_point_from_the_sun_and_the_moon() -> void:
	var to_sun := _towards(184.9, 50.3)
	var to_moon := _towards(296.0, 9.2)
	_rig.apply(to_sun, to_moon, 0.55, 168.06)
	var sun_z := _sun.global_transform.basis.z.normalized()
	var moon_z := _moon.global_transform.basis.z.normalized()
	assert_almost_eq(sun_z.distance_to(to_sun), 0.0, EPS, "the sun shines from the sun (+z)")
	assert_almost_eq(moon_z.distance_to(to_moon), 0.0, EPS, "the moon shines from the moon")
	assert_true(_sun.shadow_enabled, "the sun casts shadows")
	assert_almost_eq(_sun.directional_shadow_max_distance, 3000.0, EPS, "3000 m, as M3")
	assert_true(_moon.shadow_enabled, "the moon casts shadows")
	assert_eq(_moon.sky_mode, DirectionalLight3D.SKY_MODE_LIGHT_ONLY, "the moon lights only")
	assert_eq(_moon.light_color, Color(0.80, 0.85, 1.0), "the moon's colour")


func test_the_sun_light_at_its_pinned_points() -> void:
	var energies := {20.0: 1.0, 10.0: 1.0, 4.5: 0.5, 0.0: 0.0233, -0.5: 0.0060, -1.0: 0.0}
	for el in energies:
		_apply(el)
		assert_almost_eq(_sun.light_energy, energies[el], 0.0001, "sun energy at %.1f" % el)
	var warm := Color(1.0, 0.72, 0.50)
	var colours := {
		30.0: Color.WHITE,
		10.0: Color.WHITE,
		5.0: Color(1.0, 0.86, 0.75),
		0.0: warm,
		-0.5: warm,
	}
	for el in colours:
		_apply(el)
		var got := _sun.light_color
		var want: Color = colours[el]
		for c in 3:
			assert_almost_eq(got[c], want[c], 0.0001, "sun colour at %.1f, channel %d" % [el, c])


func test_the_lights_hide_below_their_horizons() -> void:
	_apply(-0.9)
	assert_true(_sun.visible, "the sun at -0.9 degrees is shown")
	_apply(-1.1)
	assert_false(_sun.visible, "the sun below -1 degree is hidden")
	_apply(-30.0, 0.1)
	assert_true(_moon.visible, "the moon at 0.1 degrees is shown")
	_apply(-30.0, -0.1)
	assert_false(_moon.visible, "the moon below 0 is hidden")


func test_the_moon_light_follows_its_phase_and_height() -> void:
	var cases := [
		[30.0, 1.0, 0.03],
		[30.0, 0.5, 0.015],
		[5.0, 1.0, 0.03],
		[2.5, 1.0, 0.015],
		[2.5, 0.2, 0.003],
		[0.0, 1.0, 0.0]
	]
	for c in cases:
		_apply(-30.0, c[0], c[1])
		assert_almost_eq(
			_moon.light_energy, c[2], 0.00001, "moon at %.1f, fraction %.1f" % [c[0], c[1]]
		)


func test_the_exposure_is_interpolated_in_log_space() -> void:
	var exposures := {30.0: 0.70, 10.0: 0.70, -1.0: 1.6733, 4.5: 1.0823, -12.0: 4.0, -40.0: 4.0}
	for el in exposures:
		_apply(el)
		assert_almost_eq(
			_environment.tonemap_exposure, exposures[el], 0.0001, "exposure at %.1f" % el
		)


func test_the_stars_fade_in_with_the_sun_below_minus_6() -> void:
	var strengths := {
		10.0: 0.0, -6.0: 0.0, -7.0: 0.0741, -9.0: 0.5, -11.0: 0.9259, -12.0: 1.0, -40.0: 1.0
	}
	for el in strengths:
		_apply(el)
		assert_almost_eq(_stars_strength(), strengths[el], 0.0001, "stars at %.1f" % el)


func test_the_curves_are_monotonic() -> void:
	var last := {}
	for step in range(-160, 161):
		var el := step * 0.25
		_apply(el, el, 0.7)
		var now := {
			"sun energy": _sun.light_energy,
			"sun green": _sun.light_color.g,
			"sun blue": _sun.light_color.b,
			"moon energy": _moon.light_energy,
			"minus exposure": -_environment.tonemap_exposure,
			"minus stars": -_stars_strength(),
		}
		for key in now:
			if last.has(key):
				assert_true(now[key] >= last[key] - 1e-6, "%s does not fall at %.2f" % [key, el])
		last = now


func test_the_environment_is_lit_by_the_physical_sky() -> void:
	_apply(50.0)
	assert_eq(_environment.background_mode, Environment.BG_SKY, "the sky is the background")
	assert_eq(_environment.ambient_light_source, Environment.AMBIENT_SOURCE_SKY, "lit by the sky")
	assert_almost_eq(_environment.ambient_light_sky_contribution, 0.25, EPS, "the sky's share")
	assert_eq(_environment.tonemap_mode, Environment.TONE_MAPPER_FILMIC, "Filmic, as calibrated")
	assert_not_null(_environment.sky, "a sky")
	if _environment.sky == null:
		return
	var material := _environment.sky.sky_material as ShaderMaterial
	assert_not_null(material, "a ShaderMaterial draws the sky")
	if material == null:
		return
	assert_eq(material, _rig.sky_material, "the rig's sky material")
	assert_eq(material.shader.resource_path, SHADER_PATH, "the converted physical sky")


func test_the_sky_shader_declares_the_physical_skys_uniforms() -> void:
	var shader: Shader = load(SHADER_PATH)
	var declared := {}
	for uniform in shader.get_shader_uniform_list():
		declared[uniform["name"]] = uniform["type"]
	for name in UNIFORMS:
		assert_true(declared.has(name), "declares %s" % name)
		assert_eq(declared.get(name), UNIFORMS[name], "%s's type" % name)


func test_the_sky_shader_keeps_godots_code() -> void:
	var shader: Shader = load(SHADER_PATH)
	var lines: Array[String] = []
	for line in shader.code.split("\n"):
		lines.append(line.strip_edges())
	assert_true(lines.has("render_mode use_debanding;"), "debanding on, as Godot's default")
	var at := 0
	for want in GODOT_LINES:
		var found := lines.find(want, at)
		assert_true(found >= 0, "Godot's line, in order: %s" % want)
		if found >= 0:
			at = found + 1
	var night: Array[String] = []
	for line in lines:
		if line.contains("texture(night_sky"):
			night.append(line)
	assert_eq(night.size(), 2, "the night sky is added in two places, as Godot's")
	for line in night:
		assert_true(line.contains("* stars_strength"), "times stars_strength: %s" % line)
	assert_true(
		night[0].begins_with("L0 += texture(night_sky,") if night.size() == 2 else false,
		"the sun's branch adds it to L0"
	)
	assert_true(
		night[1].begins_with("COLOR = texture(night_sky,") if night.size() == 2 else false,
		"the night's branch"
	)
