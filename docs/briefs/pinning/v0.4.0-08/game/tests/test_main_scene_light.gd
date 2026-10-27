extends GutTest
## Pinning tests for brief v0.4.0-08 (M4-10's full replacement of M3-14's file, re-cut: this
## header, the paragraph "Since brief v0.4.0-08" and its two tests; M3-14's pinned copy stays as
## the record): the sun and the moon stand where SkyClock puts them for the clock's time at the
## manifest's sky block, and the sky rig lights the scene.
##
## Pinned decisions (m4-design §4, §6, §9; briefs v0.4.0-04, v0.4.0-05, v0.4.0-06 and v0.4.0-07,
## from M4-04, M4-05 and M4-09; brief v0.4.0-08 decision 3, from M4-10): M3's fixed sun (183°,
## 52°, exposure 0.54, the procedural sky) is gone. Every frame the main scene asks SkyClock
## for the sun and the moon at the clock's time and the sky block's latitude and longitude,
## adds the block's true_to_grid_deg to each true azimuth (the azimuth from LV95 grid north),
## and turns azimuth and elevation into a local direction through the world config's east,
## north and up, as M3 did for its sun: east·sin A·cos e + north·cos A·cos e + up·sin e. SkyRig
## applies them (SkyRig.create on the scene's Sun, Moon and Environment, its frame the local
## east, north and up of TRUE north at the site: grid north turned by true_to_grid_deg, so the
## stars' pole stands at true north). Tier 1 (the review plan's placement lens): at the start,
## at the village's site (the complete world carries config/sky.json's village values as test
## data), the light stands at grid azimuth START_AZIMUTH_DEG and elevation START_ELEVATION_DEG
## within 0.05°, design's numbers measured with SkyClock (M4-04) and checked against m4-design
## §0's NOAA/SPA flight sun (true 184.9°, 50.3° at 11:40 UTC, minus 0.226°). The world is
## turned in one test (x = +n, z = +e) and the convergence set to +5° in another, so a
## hard-coded axis or the convergence's sign fails by far more than the tolerance.
##
## Since brief v0.4.0-08: the clock runs at 1x (each frame adds its delta to time_unix) and
## stands still while the pause screen is open, and every frame places the sun and the moon
## again (_place_sky from _process); the complete world's sky block is config/sky.json's village
## values, which the start test's 184.65°/50.34° depends on (lesson 42: a fixture's words are
## claims). The game's other speeds and its time keys are brief v0.4.0-09's.
##
## Does NOT prove: that anything renders or looks right (no GPU; the owner's Forward+ is the
## look); SkyClock's own accuracy (M4-04's vectors); the rig's curves (M4-05's tests).

const CompleteWorld := preload("res://tests/complete_world.gd")
const SCRATCH_DIR := "user://test_main_scene_light"
const DEPRECATION := "instance_reset_physics_interpolation() is deprecated"
const SKY_SHADER := "res://shaders/sky_physical.gdshader"
## Design's measurement (SkyClock at 2023-09-06T11:40:00Z, 46.0196233 N, 7.7485397 E, plus
## true_to_grid_deg -0.2258).
const START_AZIMUTH_DEG := 184.65
const START_ELEVATION_DEG := 50.34
const TIER_1_DEG := 0.05
## 2023-09-06 22:00 CEST.
const NIGHT := 1694030400.0
## One hour, in seconds: a frame's delta in the clock's test.
const HOUR_S := 3600.0
const SKY_CONFIG := "config/sky.json"

var _cases := 0
var _complete := ""


func before_all() -> void:
	_complete = CompleteWorld.write(SCRATCH_DIR.path_join("complete"))


func after_all() -> void:
	CompleteWorld.remove_tree(SCRATCH_DIR)


func _main_with(manifest_path: String) -> Node3D:
	var main: Node3D = load("res://main.tscn").instantiate()
	main.manifest_path = manifest_path
	add_child_autofree(main)
	for error in get_errors():
		if error.contains_text(DEPRECATION):
			error.handled = true
	main.set_process(false)
	return main


func _write(change: Callable) -> String:
	_cases += 1
	return CompleteWorld.write(SCRATCH_DIR.path_join("case_%d" % _cases), change)


## The direction towards a light: it shines along its −z.
func _towards(light: DirectionalLight3D) -> Vector3:
	return light.global_transform.basis.z


## Azimuth (clockwise from LV95 grid north) and elevation, in degrees, of [param v] in the
## owner's axes (east +x, north −z, up +y).
func _angles(v: Vector3) -> Vector2:
	var azimuth := fposmod(rad_to_deg(atan2(v.x, -v.z)), 360.0)
	return Vector2(azimuth, rad_to_deg(asin(clampf(v.y, -1.0, 1.0))))


## The owner's axes: the local direction of a grid azimuth and an elevation.
func _owner(azimuth_deg: float, elevation_deg: float) -> Vector3:
	var a := deg_to_rad(azimuth_deg)
	var e := deg_to_rad(elevation_deg)
	return Vector3(sin(a) * cos(e), sin(e), -cos(a) * cos(e))


func _assert_near(found: Vector3, expected: Vector3, what: String) -> void:
	assert_lt(found.distance_to(expected), 0.0001, "%s: %s, expected %s" % [what, found, expected])


## A manifest holding only a world whose axes are not the owner's: x = +n, y = +h, z = +e.
func _turned_world() -> WorldConfig:
	DirAccess.make_dir_recursive_absolute(SCRATCH_DIR)
	var path := SCRATCH_DIR.path_join("turned.json")
	var manifest := {
		"schema": 1,
		"world":
		{
			"areas":
			{
				"turned":
				{"e_max": 2601100.0, "e_min": 2601000.0, "n_max": 1200100.0, "n_min": 1200000.0}
			},
			"axes": {"x": "+n", "y": "+h", "z": "+e"},
			"crs": {"horizontal": "EPSG:2056", "vertical": "EPSG:5728"},
			"height_offset_m": 1000.0,
			"origin_lv95": {"e": 2600000.0, "n": 1200000.0},
			"schema": 1,
		},
	}
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string(JSON.stringify(manifest, "  ", true, true))
	file.close()
	return WorldConfig.from_manifest(path)


func test_the_start_sun_stands_at_tier_1_s_numbers() -> void:
	var main := _main_with(_complete)
	assert_false(main.get_node("UI/ErrorPanel").visible, "the complete world opens no panel")
	assert_eq(main.time_unix, SkyClock.START_UNIX, "at the start")
	var sun: DirectionalLight3D = main.get_node("Sun")
	var angles := _angles(_towards(sun))
	assert_almost_eq(angles.x, START_AZIMUTH_DEG, TIER_1_DEG, "grid azimuth 184.65")
	assert_almost_eq(angles.y, START_ELEVATION_DEG, TIER_1_DEG, "elevation 50.34")
	# The same light, exactly, from SkyClock at the sky block's site.
	var sky: Dictionary = CompleteWorld.SKY
	var true_sun := SkyClock.sun(SkyClock.START_UNIX, sky["latitude_deg"], sky["longitude_deg"])
	var expected := _owner(true_sun.x + sky["true_to_grid_deg"], true_sun.y)
	_assert_near(_towards(sun), expected, "the sun, from SkyClock")
	var material: ShaderMaterial = main.get_node("Environment").environment.sky.sky_material
	var drawn: Variant = material.get_shader_parameter("sun_direction")
	assert_true(drawn is Vector3, "the sky shader's sun_direction is set")
	if drawn is Vector3:
		_assert_near(drawn, expected, "the sky draws the sun where the light comes from")


func test_the_moon_and_the_night_follow_the_clock() -> void:
	var main := _main_with(_complete)
	main.time_unix = NIGHT
	main._place_sky()
	var sky: Dictionary = CompleteWorld.SKY
	var moon := SkyClock.moon(NIGHT, sky["latitude_deg"], sky["longitude_deg"])
	var sun := SkyClock.sun(NIGHT, sky["latitude_deg"], sky["longitude_deg"])
	assert_lt(sun.y, -12.0, "22:00: the sun is more than 12 degrees down")
	var moon_light: DirectionalLight3D = main.get_node("Moon")
	_assert_near(
		_towards(moon_light),
		_owner(moon.x + sky["true_to_grid_deg"], moon.y),
		"the moon, from SkyClock"
	)
	assert_false(main.get_node("Sun").visible, "the sun is hidden at night")
	var environment: Environment = main.get_node("Environment").environment
	assert_almost_eq(environment.tonemap_exposure, 4.0, 0.0001, "the night's exposure")
	assert_eq(moon_light.visible, moon.y >= 0.0, "the moon shown only above the horizon")


func test_the_light_turns_with_the_world_config() -> void:
	var main := _main_with(_complete)
	var turned := _turned_world()
	assert_not_null(turned, "the turned world is read")
	if turned == null:
		return
	main._read_directions(turned)
	main._place_sky()
	var sky: Dictionary = CompleteWorld.SKY
	var sun := SkyClock.sun(main.time_unix, sky["latitude_deg"], sky["longitude_deg"])
	var a := deg_to_rad(sun.x + sky["true_to_grid_deg"])
	var e := deg_to_rad(sun.y)
	# Here north is +x and east is +z.
	var expected := Vector3(cos(a) * cos(e), sin(e), sin(a) * cos(e))
	_assert_near(_towards(main.get_node("Sun")), expected, "the sun in the turned world")


func test_true_to_grid_is_added_to_the_true_azimuth() -> void:
	var path := _write(func(m: Dictionary) -> void: m["sky"]["true_to_grid_deg"] = 5.0)
	var main := _main_with(path)
	assert_false(main.get_node("UI/ErrorPanel").visible, "the changed site is accepted")
	var sky: Dictionary = CompleteWorld.SKY
	var sun := SkyClock.sun(main.time_unix, sky["latitude_deg"], sky["longitude_deg"])
	var angles := _angles(_towards(main.get_node("Sun")))
	assert_almost_eq(angles.x, fposmod(sun.x + 5.0, 360.0), 0.001, "true azimuth + 5 degrees")


func test_the_site_is_the_sky_block_s() -> void:
	var far_north := func(m: Dictionary) -> void:
		m["sky"]["latitude_deg"] = 60.0
		m["sky"]["longitude_deg"] = -20.0
	var main := _main_with(_write(far_north))
	var sun := SkyClock.sun(main.time_unix, 60.0, -20.0)
	var angles := _angles(_towards(main.get_node("Sun")))
	assert_almost_eq(angles.y, sun.y, 0.001, "the elevation at 60 N, 20 W")
	assert_almost_eq(angles.x, fposmod(sun.x - 0.2258, 360.0), 0.001, "and its azimuth")
	assert_gt(absf(angles.y - START_ELEVATION_DEG), 5.0, "far from the village's")


func test_the_environment_is_the_sky_rig_s() -> void:
	var main := _main_with(_complete)
	var environment: Environment = main.get_node("Environment").environment
	assert_almost_eq(environment.tonemap_exposure, 0.70, 0.0001, "exposure 0.70 by day")
	assert_eq(environment.tonemap_mode, Environment.TONE_MAPPER_FILMIC, "Filmic")
	assert_eq(environment.background_mode, Environment.BG_SKY, "the sky as background")
	assert_eq(environment.ambient_light_source, Environment.AMBIENT_SOURCE_SKY, "lit by the sky")
	assert_almost_eq(environment.ambient_light_sky_contribution, 0.25, 0.00001, "its share 0.25")
	var material: Material = environment.sky.sky_material if environment.sky != null else null
	assert_true(material is ShaderMaterial, "the sky is a ShaderMaterial, not M3's procedural sky")
	if material is ShaderMaterial:
		var shader: Shader = material.shader
		assert_eq(shader.resource_path if shader != null else "", SKY_SHADER, "M4-05's sky")
	var sun: DirectionalLight3D = main.get_node("Sun")
	assert_true(sun.shadow_enabled, "the sun casts shadows")
	assert_almost_eq(sun.light_energy, 1.0, 0.0001, "full sun at 50 degrees")
	var moon := main.get_node_or_null("Moon") as DirectionalLight3D
	assert_not_null(moon, "a Moon light beside the Sun")
	if moon != null:
		assert_eq(moon.sky_mode, DirectionalLight3D.SKY_MODE_LIGHT_ONLY, "the sun stays LIGHT0")
		assert_true(moon.shadow_enabled, "the moon casts shadows")


func test_the_stars_pole_stands_at_true_north() -> void:
	if not FileAccess.file_exists("res://sky/stars.csv"):
		pass_test("no stars section (m4-design §10 option (b)): no celestial basis to check")
		return
	var main := _main_with(_complete)
	var sky: Dictionary = CompleteWorld.SKY
	var material: ShaderMaterial = main.get_node("Environment").environment.sky.sky_material
	var basis: Variant = material.get_shader_parameter("celestial_basis")
	assert_true(basis is Basis, "the celestial basis is set")
	if not basis is Basis:
		return
	# True north lies at grid azimuth true_to_grid_deg; the pole stands there at the latitude.
	var pole := _owner(sky["true_to_grid_deg"], sky["latitude_deg"])
	_assert_near(basis * pole, Vector3(0.0, 0.0, 1.0), "the pole, at true north")
	var grid_pole := _owner(0.0, sky["latitude_deg"])
	assert_gt(
		(basis * grid_pole).distance_to(Vector3(0, 0, 1)), 0.002, "not at grid north (0.0027 away)"
	)


func test_the_complete_world_s_site_is_config_sky_json_s_village() -> void:
	var json := JSON.new()
	var text := FileAccess.get_file_as_string(CompleteWorld.repo_file(SKY_CONFIG))
	assert_eq(json.parse(text), OK, "config/sky.json parses")
	var areas: Variant = json.data.get("areas") if json.data is Dictionary else null
	var village: Variant = areas.get("village") if areas is Dictionary else null
	assert_true(village is Dictionary, "config/sky.json holds the village")
	if not village is Dictionary:
		return
	for key: String in ["latitude_deg", "longitude_deg", "true_to_grid_deg"]:
		assert_eq(CompleteWorld.SKY[key], village.get(key), "the complete world's %s" % key)


func test_each_frame_the_clock_runs_at_1x_and_the_sky_follows() -> void:
	var main := _main_with(_complete)
	var sky: Dictionary = CompleteWorld.SKY
	main._process(HOUR_S)
	var later: float = SkyClock.START_UNIX + HOUR_S
	assert_almost_eq(main.time_unix, later, 0.000001, "1x: a frame adds its delta")
	var sun := SkyClock.sun(later, sky["latitude_deg"], sky["longitude_deg"])
	var expected := _owner(sun.x + sky["true_to_grid_deg"], sun.y)
	_assert_near(_towards(main.get_node("Sun")), expected, "the frame placed the sun an hour on")
	var moon := SkyClock.moon(later, sky["latitude_deg"], sky["longitude_deg"])
	_assert_near(
		_towards(main.get_node("Moon")),
		_owner(moon.x + sky["true_to_grid_deg"], moon.y),
		"and the moon"
	)
	main.toggle_pause()
	main._process(HOUR_S)
	main.toggle_pause()
	assert_almost_eq(main.time_unix, later, 0.000001, "the clock stands still while paused")
