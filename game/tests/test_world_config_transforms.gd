extends GutTest
## WorldConfig's transforms beyond the pinned vectors (brief M0-03): the origin and the
## height offset come from the manifest it is given, and conversions round-trip.
##
## The height-offset test pins the same reading as the pipeline's
## test_world_transforms.py (brief M0-02 Findings): y = H - height_offset_m. A game that
## read it the other way would sit twice the offset away from the pipeline's terrain.

const MANIFEST_PATH := "res://assets/generated/manifest.json"
const SCRATCH_DIR := "user://test_world_config_transforms"


func before_all() -> void:
	DirAccess.make_dir_recursive_absolute(SCRATCH_DIR)


func after_all() -> void:
	for file in DirAccess.get_files_at(SCRATCH_DIR):
		DirAccess.remove_absolute(SCRATCH_DIR.path_join(file))
	DirAccess.remove_absolute(SCRATCH_DIR)


func _world_with(name: String, change: Callable) -> WorldConfig:
	var manifest: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(MANIFEST_PATH))
	change.call(manifest["world"])
	var path := SCRATCH_DIR.path_join(name + ".json")
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string(JSON.stringify(manifest))
	file.close()
	return WorldConfig.from_manifest(path)


func test_origin_comes_from_the_manifest_it_is_given() -> void:
	var world := _world_with(
		"moved_origin",
		func(w: Dictionary) -> void: w["origin_lv95"] = {"e": 2600000.0, "n": 1200000.0}
	)
	assert_not_null(world)
	assert_eq(world.to_local(2600001.0, 1200001.0, 5.0), Vector3(1.0, 5.0, -1.0))


func test_height_offset_is_subtracted_from_heights() -> void:
	var world := _world_with(
		"height_offset", func(w: Dictionary) -> void: w["height_offset_m"] = 1000.0
	)
	assert_not_null(world)
	assert_eq(world.height_offset, 1000.0)
	var p := world.to_local(world.origin_e + 3.0, world.origin_n + 4.0, 1600.0)
	assert_eq(p, Vector3(3.0, 600.0, -4.0))
	var back := world.to_lv95(Vector3(3.0, 600.0, -4.0))
	assert_eq(back[0], world.origin_e + 3.0)
	assert_eq(back[1], world.origin_n + 4.0)
	assert_eq(back[2], 1600.0)


func test_round_trips_stay_within_a_millimetre() -> void:
	var world := WorldConfig.from_manifest(MANIFEST_PATH)
	assert_not_null(world)
	var rng := RandomNumberGenerator.new()
	rng.seed = 20260924
	for i in 200:
		var e := world.origin_e + rng.randf_range(-20000.0, 20000.0)
		var n := world.origin_n + rng.randf_range(-20000.0, 20000.0)
		var h := rng.randf_range(-500.0, 5000.0)
		var back := world.to_lv95(world.to_local(e, n, h))
		# 32-bit Vector3 in between: about 2 mm at 20 km, SPEC section 6.
		assert_almost_eq(back[0], e, 0.002, "e of point %d" % i)
		assert_almost_eq(back[1], n, 0.002, "n of point %d" % i)
		assert_almost_eq(back[2], h, 0.001, "h of point %d" % i)
