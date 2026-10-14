extends GutTest
## Pinning tests for brief M3-14: the sun stands where it stood in the photo, and the light
## renders the photo at its own brightness.
##
## Pinned decisions (m3-design.md §8; docs/SPEC.md §10, M3's game): the fixed sun ("Sun")
## shines from azimuth 183 degrees (clockwise from LV95 north) at an elevation of 52
## degrees: the photo's sun, measured from its shadows and its flight time, 7 September 2023
## at about 11:30 UTC. It replaces M2's 150 and 35 degrees (this test replaces
## test_main_scene.gd's M2 sun test). Its direction is measured through WorldConfig, never
## assumed: in a world whose axes are not the owner's the sun turns with them. It casts
## shadows. The Environment keeps M2's sky (background and ambient light from the sky) and
## the Filmic tonemapper, the mode the calibration was measured with; its exposure is 0.54
## and the sky's share of the ambient light 0.25: design's calibration, under which flat
## sunlit ground renders at 1.063 times the photo's linear luminance (Compatibility,
## software rendering, 2026-10-14). 183 degrees is asymmetric on purpose: its east-west
## mirror, 177 degrees, puts the sun 0.06 east of where it is (the test's tolerance is
## 0.0001), and an azimuth counted from the south or counter-clockwise lands elsewhere too.
##
## Does NOT prove: that anything renders or looks right (no GPU); the calibration itself
## (measured in software, not on the owner's Forward+ GPU).

const CompleteWorld := preload("res://tests/complete_world.gd")
const SCRATCH_DIR := "user://test_main_scene_light"
const DEPRECATION := "instance_reset_physics_interpolation() is deprecated"
const AZIMUTH_DEG := 183.0
const ELEVATION_DEG := 52.0

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
	return main


## A manifest holding only a world whose axes are not the owner's: x = +n, y = +h, z = +e
## (a proper rotation). WorldConfig reads it; nothing else is built from it.
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


func test_the_sun_shines_from_azimuth_183_at_52_degrees() -> void:
	var main := _main_with(_complete)
	var sun: DirectionalLight3D = main.get_node("Sun")
	assert_true(sun.shadow_enabled, "the sun casts shadows")
	var to_sun := sun.global_transform.basis.z  # a light shines along its -z
	var elevation := deg_to_rad(ELEVATION_DEG)
	var azimuth := deg_to_rad(AZIMUTH_DEG)
	assert_almost_eq(to_sun.y, sin(elevation), 0.0001, "elevation 52 degrees")
	# The owner's axes: east is +x, north is -z. 183 degrees: south, a little west.
	assert_almost_eq(to_sun.x, sin(azimuth) * cos(elevation), 0.0001, "east part (-0.0322)")
	assert_almost_eq(to_sun.z, -cos(azimuth) * cos(elevation), 0.0001, "south part (0.6148)")
	assert_false(main.get_node("UI/ErrorPanel").visible, "the complete world opens no panel")


func test_the_sun_is_placed_through_the_world_config() -> void:
	var main := _main_with(_complete)
	var turned := _turned_world()
	assert_not_null(turned, "the turned world is read")
	if turned == null:
		return
	# The main scene measures east, north and up through the world it read, then places the
	# sun from them (main.gd's _read_directions and _place_sun, as since M1-05).
	main._read_directions(turned)
	main._place_sun()
	var to_sun: Vector3 = main.get_node("Sun").global_transform.basis.z
	var elevation := deg_to_rad(ELEVATION_DEG)
	var azimuth := deg_to_rad(AZIMUTH_DEG)
	# Here east is +z and north is +x.
	assert_almost_eq(to_sun.y, sin(elevation), 0.0001, "elevation, turned world")
	assert_almost_eq(to_sun.x, cos(azimuth) * cos(elevation), 0.0001, "north part, turned")
	assert_almost_eq(to_sun.z, sin(azimuth) * cos(elevation), 0.0001, "east part, turned")


func test_the_environment_is_the_calibrated_light() -> void:
	var main := _main_with(_complete)
	var environment: Environment = (main.get_node("Environment") as WorldEnvironment).environment
	assert_not_null(environment, "the main scene has its Environment")
	if environment == null:
		return
	assert_almost_eq(environment.tonemap_exposure, 0.54, 0.00001, "exposure 0.54")
	assert_almost_eq(
		environment.ambient_light_sky_contribution, 0.25, 0.00001, "the sky's share 0.25"
	)
	assert_eq(environment.tonemap_mode, Environment.TONE_MAPPER_FILMIC, "Filmic, as calibrated")
	assert_eq(environment.background_mode, Environment.BG_SKY, "M2's sky")
	assert_eq(environment.ambient_light_source, Environment.AMBIENT_SOURCE_SKY, "lit by the sky")
	assert_almost_eq(environment.ambient_light_energy, 1.0, 0.00001, "M2's ambient energy")
	var sun: DirectionalLight3D = main.get_node("Sun")
	assert_almost_eq(sun.light_energy, 1.0, 0.00001, "M2's sun energy, as calibrated")
