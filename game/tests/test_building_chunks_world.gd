extends GutTest
## BuildingChunks' world check beyond the pinned test (brief M2-08, M2 R1 P-04): the
## WorldConfig given must be the manifest's own. test_scene_placement.gd (pinned) proves the
## check is wired into BuildingChunks.from_manifest, with a WorldConfig whose origin differs;
## this file calls BuildingChunks._check_world itself, so that each difference it must name
## (the origin, the height offset, the axes) is proven without an error line: _check_world
## returns what differs, and only BuildingChunks.from_manifest logs it.
##
## Each WorldConfig given is read (WorldConfig.from_manifest) from a copy of the shared
## buildings fixture's manifest whose world block differs in that one field, written under
## user://test_building_chunks_world. The other axes are a quarter turn about the vertical
## (x = +n, y = +h, z = +e, a proper rotation, so WorldConfig reads it) with the same origin
## and height offset: only the axes comparison can tell it from the fixture's own.
##
## Does NOT prove: that the buildings render or look right (no GPU).

const SCRATCH_DIR := "user://test_building_chunks_world"
const NOT_OURS := "the WorldConfig given was not read from this manifest"

var _cases := 0


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


func _fixture() -> String:
	return _repo_file("tests/shared/buildings_fixture/generated/manifest.json")


func _manifest() -> Dictionary:
	var json := JSON.new()
	assert_eq(json.parse(FileAccess.get_file_as_string(_fixture())), OK, "the fixture parses")
	return json.data if typeof(json.data) == TYPE_DICTIONARY else {}


func after_all() -> void:
	_remove_tree(SCRATCH_DIR)


func _remove_tree(dir: String) -> void:
	for sub in DirAccess.get_directories_at(dir):
		_remove_tree(dir.path_join(sub))
	for file in DirAccess.get_files_at(dir):
		DirAccess.remove_absolute(dir.path_join(file))
	DirAccess.remove_absolute(dir)


## Writes the fixture's manifest with its world block changed by [param change] (a Callable
## taking the world Dictionary); returns the path.
func _write_world(change: Callable) -> String:
	_cases += 1
	DirAccess.make_dir_recursive_absolute(SCRATCH_DIR)
	var manifest := _manifest()
	change.call(manifest["world"])
	var path := SCRATCH_DIR.path_join("manifest_%d.json" % _cases)
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string(JSON.stringify(manifest, "  ", true, true))
	file.close()
	return path


## _check_world's answer for a WorldConfig read from the fixture with [param change] applied
## to its world block, against the fixture's own manifest and world block.
func _check(change: Callable) -> String:
	var world := WorldConfig.from_manifest(_write_world(change))
	assert_not_null(world, "the changed world block is itself valid")
	if world == null:
		return "no WorldConfig"
	return BuildingChunks._check_world(world, _fixture(), _manifest()["world"])


func test_the_manifest_s_own_world_config_passes() -> void:
	var world := WorldConfig.from_manifest(_fixture())
	assert_not_null(world)
	assert_eq(BuildingChunks._check_world(world, _fixture(), _manifest()["world"]), "")


func test_another_origin_is_refused() -> void:
	var problem := _check(func(w: Dictionary) -> void: w["origin_lv95"]["e"] += 1.0)
	assert_string_contains(problem, NOT_OURS)
	assert_string_contains(problem, "origin or height offset")


func test_another_height_offset_is_refused() -> void:
	var problem := _check(func(w: Dictionary) -> void: w["height_offset_m"] += 1.0)
	assert_string_contains(problem, NOT_OURS)
	assert_string_contains(problem, "origin or height offset")


func test_other_axes_are_refused() -> void:
	var turned := {"x": "+n", "y": "+h", "z": "+e"}
	var problem := _check(func(w: Dictionary) -> void: w["axes"] = turned)
	assert_string_contains(problem, NOT_OURS)
	assert_string_contains(problem, "axes differ")


func test_a_manifest_whose_world_block_is_refused_is_named() -> void:
	# The given WorldConfig is the fixture's; the manifest's world block has the same origin
	# and height offset but mirrored axes, which WorldConfig refuses with its own push_error.
	var world := WorldConfig.from_manifest(_fixture())
	var mirrored := func(w: Dictionary) -> void: w["axes"] = {"x": "-e", "y": "+h", "z": "-n"}
	var path := _write_world(mirrored)
	var json := JSON.new()
	json.parse(FileAccess.get_file_as_string(path))
	var problem := BuildingChunks._check_world(world, path, json.data["world"])
	assert_string_contains(problem, "world block is refused")
	assert_push_error(path, "WorldConfig names the manifest whose world block it refuses")
