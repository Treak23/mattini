extends GutTest
## WorldConfig's transforms beyond the pinned vectors (brief M0-03): the origin and the
## height offset come from the manifest it is given. The round trips, for every rotation
## and with 64-bit offsets, are in test_world_config_round_trips.gd (brief M1-02).
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
