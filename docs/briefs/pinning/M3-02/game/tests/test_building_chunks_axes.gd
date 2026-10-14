extends GutTest
## Pinning tests for brief M3-02 (M2 V1-G-03): BuildingChunks compares all three axes.
##
## Pinned decision (docs/SPEC.md §8, the buildings, the game; brief M2-08): the WorldConfig
## given must map one metre east, north and up to the same local vectors as one read from
## the manifest. Its test turned only the east step (x = +n, y = +h, z = +e keeps up), so a
## check of the east step alone passed it. Here each of three quarter turns keeps one step
## and turns the other two: east kept (x = +e, y = +n, z = +h), north kept (x = +h, y = -e,
## z = -n), up kept (x = +n, y = +h, z = +e). A check that compares one step only is fooled
## by the turn that keeps that step; every one of the three must be refused. Each is a
## proper rotation (WorldConfig reads it) with the fixture's origin and height offset, so
## only the axes can tell it from the fixture's own world. As in
## test_building_chunks_world.gd, BuildingChunks._check_world is called itself: it returns
## what differs without logging it.
##
## Does NOT prove: that the buildings render or look right (no GPU).

const SCRATCH_DIR := "user://test_building_chunks_axes"
const AXES_DIFFER := "the WorldConfig given was not read from this manifest (its axes differ)"

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


## _check_world's answer for a WorldConfig whose world block is the fixture's with
## [param axes], against the fixture's own manifest and world block.
func _check_axes(axes: Dictionary) -> String:
	_cases += 1
	DirAccess.make_dir_recursive_absolute(SCRATCH_DIR)
	var manifest := _manifest()
	manifest["world"]["axes"] = axes
	var path := SCRATCH_DIR.path_join("manifest_%d.json" % _cases)
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string(JSON.stringify(manifest, "  ", true, true))
	file.close()
	var world := WorldConfig.from_manifest(path)
	assert_not_null(world, "%s is a proper rotation, which WorldConfig reads" % [axes])
	if world == null:
		return "no WorldConfig"
	return BuildingChunks._check_world(world, _fixture(), _manifest()["world"])


func test_the_fixture_s_own_axes_pass() -> void:
	assert_eq(_check_axes({"x": "+e", "y": "+h", "z": "-n"}), "", "the owner's axes")


func test_east_kept_north_and_up_turned_is_refused() -> void:
	assert_eq(_check_axes({"x": "+e", "y": "+n", "z": "+h"}), AXES_DIFFER)


func test_north_kept_east_and_up_turned_is_refused() -> void:
	assert_eq(_check_axes({"x": "+h", "y": "-e", "z": "-n"}), AXES_DIFFER)


func test_up_kept_east_and_north_turned_is_refused() -> void:
	assert_eq(_check_axes({"x": "+n", "y": "+h", "z": "+e"}), AXES_DIFFER)
