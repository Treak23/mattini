extends GutTest
## Pinning tests for brief M3-02 (M2 V1-G-08): TerrainGrid names the fields that differ.
##
## Pinned decision (docs/SPEC.md §8, the terrain grid, the game; brief M3-02): TerrainGrid
## refuses a WorldConfig that was not read from the manifest it reads, and the refusal says
## "(its origin or height offset differs)", as BuildingChunks' does: the two fields it
## compares, either of which places the grid elsewhere. It said "(its origin differs)" when
## only the height offset differed, sending the reader to the wrong field. Each case is the
## shared terrain fixture's manifest with one field of its world block changed, written
## under user://test_terrain_grid_world, read with the fixture's own WorldConfig.
##
## Does NOT prove: that the refusal reaches the error panel (test_main_scene_terrain.gd).

const SCRATCH_DIR := "user://test_terrain_grid_world"
const NOT_OURS := "the WorldConfig given was not read from this manifest"
const WHICH := "(its origin or height offset differs)"

var _cases := 0


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


func _fixture() -> String:
	return _repo_file("tests/shared/terrain_fixture/generated/manifest.json")


func after_all() -> void:
	_remove_tree(SCRATCH_DIR)


func _remove_tree(dir: String) -> void:
	for sub in DirAccess.get_directories_at(dir):
		_remove_tree(dir.path_join(sub))
	for file in DirAccess.get_files_at(dir):
		DirAccess.remove_absolute(dir.path_join(file))
	DirAccess.remove_absolute(dir)


## The fixture's manifest with its world block changed by [param change], and its heights
## file beside it, in a fresh case folder; returns the manifest's path.
func _write_case(change: Callable) -> String:
	_cases += 1
	var dir := SCRATCH_DIR.path_join("case_%d" % _cases)
	DirAccess.make_dir_recursive_absolute(dir.path_join("terrain"))
	var json := JSON.new()
	assert_eq(json.parse(FileAccess.get_file_as_string(_fixture())), OK, "the fixture parses")
	var manifest: Dictionary = json.data
	change.call(manifest["world"])
	var path := dir.path_join("manifest.json")
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string(JSON.stringify(manifest, "  ", true, true))
	file.close()
	var heights := FileAccess.get_file_as_bytes(
		_repo_file("tests/shared/terrain_fixture/generated/terrain/fixture.f32")
	)
	var data := FileAccess.open(dir.path_join("terrain/fixture.f32"), FileAccess.WRITE)
	data.store_buffer(heights)
	data.close()
	return path


## The grid is refused with one push_error naming [param path] that says [param needle].
func _assert_refused(path: String, grid: TerrainGrid, needle: String) -> void:
	assert_null(grid, "the fixture's WorldConfig is refused for %s" % path)
	var found := ""
	for error in get_errors():
		if found.is_empty() and error.is_push_error() and error.contains_text(path):
			error.handled = true
			found = "%s %s" % [error.code, error.rationale]
	assert_string_contains(found, NOT_OURS)
	assert_string_contains(found, needle)


func test_the_fixture_s_own_world_config_places_the_grid() -> void:
	# The control: the case folder with its world block unchanged is read.
	var path := _write_case(func(_world: Dictionary) -> void: pass)
	assert_not_null(TerrainGrid.from_manifest(path, WorldConfig.from_manifest(path)))


func test_another_height_offset_alone_is_named_with_the_origin() -> void:
	var path := _write_case(func(world: Dictionary) -> void: world["height_offset_m"] += 1.0)
	var grid := TerrainGrid.from_manifest(path, WorldConfig.from_manifest(_fixture()))
	_assert_refused(path, grid, WHICH)


func test_another_origin_is_named_the_same_way() -> void:
	var path := _write_case(func(world: Dictionary) -> void: world["origin_lv95"]["e"] += 1000.0)
	var grid := TerrainGrid.from_manifest(path, WorldConfig.from_manifest(_fixture()))
	_assert_refused(path, grid, WHICH)
