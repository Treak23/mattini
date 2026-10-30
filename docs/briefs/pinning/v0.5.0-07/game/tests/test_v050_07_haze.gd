extends GutTest
## Pinning tests for brief v0.5.0-07 (FB-004 item 5; the owner chose variant V2 of 0.4.0's record,
## docs/releases/v0.4.0.md "The trees", at the go of 2026-10-29): the trees' haze. Distant forest in
## the shade drew near-black (80.5 % of the start view's forest below sRGB 20 on every channel at
## 13:40, software Forward+); a light haze, the sky's own colour added with distance, lifts it to a
## dark grey-blue.
##
## Pinned decisions: SkyRig.create (game/scripts/sky/sky_rig.gd) turns the environment's fog on,
## exponential with distance (Godot's FOG_MODE_EXPONENTIAL: the share fogged at a distance D is
## 1 - exp(-density * D); the pin author measured it so in software Forward+ and in Compatibility,
## a black wall at 500, 1000, 2000 and 4000 m within one 8-bit level), at the density
## SkyRig.HAZE_DENSITY, a named design constant the builder measures in software Forward+ so that
## ground 2 km away is about 10 % fogged (the start: 5.27e-5 per metre, -ln(0.9) / 2000 m; the pin
## author's wall at 2000 m read 0.0999). Its exact value is the builder's measurement, so this file
## pins only that it exists, lies between DENSITY_MIN and DENSITY_MAX (about 4 % to 26 % at 2 km)
## and is the value the environment reads. fog_aerial_perspective 1.0: the fog's colour is the
## sky's radiance, so it follows the moving sun and goes dark at night with no per-frame code;
## fog_sky_affect 0.0: the sky itself is not fogged. No height fog (fog_height_density stays 0,
## checked to 1e-9, below the haze's own scale of about 5e-5 per metre): the density alone sets the
## haze, as measured. No sun scatter and no volumetric fog (fog_sun_scatter 0, volumetric fog off:
## Godot's defaults, which the environment handed here holds). create sets each of the five,
## whatever the environment held; apply, called every frame, touches none of the five nor the
## three left at their defaults.
##
## The gate's render checks of the main scene (game/tests/render/render_photo.gd and
## render_trees.gd) switch the haze off before their first capture, as they switch off ambient
## light: the fog adds the sky's colour to every pixel, and their numbers are ratios and
## correlations of the data. The pin author measured the moves without it (photo's mirrored scans,
## classes' agreement 70031 of 70180 and eased bank 0.993, trees 0.8661; every line still PASS,
## so the gate alone would not see a lost override): this file reads their text for the line, at
## the start of a line and one tab in, so a line commented out or nested under a condition does
## not count.
##
## The environment handed to create here holds the wrong value for each setting (fog off, depth
## fog, Godot's default density 0.01, a quarter of aerial perspective, the sky fully fogged), so
## a rig that leaves one alone fails by its name.
##
## Does NOT prove: that the haze renders or looks right (no GPU; the brief's software renders are
## evidence, the owner's PC is the test), that 2 km reads about 10 % (the builder's measurement,
## recorded in the brief's Findings), the fog's colour at any hour (Godot draws it from the sky's
## radiance map, which the dummy renderer here does not hold), or that the render checks'
## override takes effect (the text is read; the brief's batch gate compares the RENDER lines digit
## for digit).

const RIG_PATH := "res://scripts/sky/sky_rig.gd"
const EPS := 0.0001
## The tolerance for a fog value that must stay 0: below the haze's own density scale.
const NONE_EPS := 1e-9
## The density's bounds, per metre: 1 - exp(-DENSITY_MIN * 2000) = 0.039 and
## 1 - exp(-DENSITY_MAX * 2000) = 0.259 at 2 km.
const DENSITY_MIN := 2e-5
const DENSITY_MAX := 1.5e-4
## The render checks that draw the main scene, and the line each holds before its first capture.
const RENDER_CHECKS: Array[String] = [
	"res://tests/render/render_photo.gd", "res://tests/render/render_trees.gd"
]
const FOG_OFF := "\n\tenvironment.fog_enabled = false\n"
const FIRST_CAPTURE := "await Common.capture(self)"

var _root: Node3D
var _sun: DirectionalLight3D
var _moon: DirectionalLight3D
var _environment: Environment
var _frame: Basis
var _rig: SkyRig


## The owner's axes (east +x, north -z, up +y) turned about (1, 2, 3) by 0.7 rad, as the sky rig's
## own tests turn them.
func _turned_frame() -> Basis:
	var turn := Basis(Vector3(1.0, 2.0, 3.0).normalized(), 0.7)
	return Basis(turn * Vector3(1, 0, 0), turn * Vector3(0, 0, -1), turn * Vector3(0, 1, 0))


## The unit vector towards azimuth [param az] (clockwise from north) and elevation [param el].
func _towards(az: float, el: float) -> Vector3:
	var a := deg_to_rad(az)
	var e := deg_to_rad(el)
	return (_frame.x * sin(a) + _frame.y * cos(a)) * cos(e) + _frame.z * sin(e)


## An environment holding the wrong value for every setting the haze decides.
func _wrong_environment() -> Environment:
	var environment := Environment.new()
	environment.fog_enabled = false
	environment.fog_mode = Environment.FOG_MODE_DEPTH
	environment.fog_density = 0.01
	environment.fog_aerial_perspective = 0.25
	environment.fog_sky_affect = 1.0
	return environment


func before_each() -> void:
	_root = Node3D.new()
	_sun = DirectionalLight3D.new()
	_moon = DirectionalLight3D.new()
	_root.add_child(_sun)
	_root.add_child(_moon)
	add_child_autofree(_root)
	_environment = _wrong_environment()
	_frame = _turned_frame()
	_rig = SkyRig.create(_sun, _moon, _environment, _frame, 46.02)


## SkyRig.HAZE_DENSITY read from the script's constants (so that a rig without it fails here by
## name, not by a parse error), or null.
func _density_constant() -> Variant:
	var constants: Dictionary = load(RIG_PATH).get_script_constant_map()
	return constants.get("HAZE_DENSITY")


## The settings the haze decides or leaves at Godot's defaults, as the environment holds them.
func _haze() -> Dictionary:
	return {
		"fog_enabled": _environment.fog_enabled,
		"fog_mode": _environment.fog_mode,
		"fog_density": _environment.fog_density,
		"fog_aerial_perspective": _environment.fog_aerial_perspective,
		"fog_sky_affect": _environment.fog_sky_affect,
		"fog_height_density": _environment.fog_height_density,
		"fog_sun_scatter": _environment.fog_sun_scatter,
		"volumetric_fog_enabled": _environment.volumetric_fog_enabled,
	}


func test_the_haze_is_on_and_exponential_with_distance() -> void:
	assert_true(_environment.fog_enabled, "the haze is on")
	assert_eq(
		_environment.fog_mode,
		Environment.FOG_MODE_EXPONENTIAL,
		"exponential with distance, not depth fog"
	)
	assert_almost_eq(_environment.fog_height_density, 0.0, NONE_EPS, "no height fog")
	assert_almost_eq(_environment.fog_sun_scatter, 0.0, NONE_EPS, "no sun scatter")
	assert_false(_environment.volumetric_fog_enabled, "no volumetric fog")


func test_the_haze_takes_the_sky_s_colour_and_leaves_the_sky_clear() -> void:
	assert_almost_eq(
		_environment.fog_aerial_perspective, 1.0, EPS, "the haze's colour is the sky's radiance"
	)
	assert_almost_eq(_environment.fog_sky_affect, 0.0, EPS, "the sky itself is not fogged")


func test_the_density_is_the_rig_s_named_constant_in_its_range() -> void:
	var constant: Variant = _density_constant()
	assert_true(constant is float, "SkyRig.HAZE_DENSITY exists and is a float (got %s)" % constant)
	if not constant is float:
		return
	var density: float = constant
	assert_between(density, DENSITY_MIN, DENSITY_MAX, "SkyRig.HAZE_DENSITY, per metre")
	assert_almost_eq(
		_environment.fog_density, density, density * 1e-6, "the environment reads HAZE_DENSITY"
	)


func test_the_haze_needs_no_per_frame_code() -> void:
	var created := _haze()
	var elevations := [50.0, 10.0, -3.0, -9.0, -30.0, 89.99]
	for el: float in elevations:
		_rig.apply(_towards(140.0, el), _towards(250.0, 30.0), 1.0, 77.0)
		var now := _haze()
		for key: String in created:
			assert_eq(now[key], created[key], "%s after apply at a sun of %.2f" % [key, el])


func test_the_render_checks_switch_the_haze_off_before_they_capture() -> void:
	for path in RENDER_CHECKS:
		var text := FileAccess.get_file_as_string(path)
		assert_true(text.length() > 0, "%s is read" % path)
		assert_eq(text.count(FOG_OFF), 1, "%s switches the haze off, once" % path)
		var off := text.find(FOG_OFF)
		var capture := text.find(FIRST_CAPTURE)
		assert_true(capture > 0, "%s captures" % path)
		assert_true(off >= 0 and off < capture, "%s: the haze off before the first capture" % path)
