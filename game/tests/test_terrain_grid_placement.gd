extends GutTest
## TerrainGrid's checks beyond the pinned tests (brief M1-04): the WorldConfig it places
## the grid with must be its own manifest's, a fractional count is refused even where the
## box would fit it, and a rotated world is refused for its axes. Each case is the shared
## fixture with one change, written under user://test_terrain_grid_placement.
##
## Does NOT prove: that a caller passes the right manifest path (M1-05's main scene).

const SCRATCH_DIR := "user://test_terrain_grid_placement"

var _cases := 0


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


func _fixture_manifest_path() -> String:
	return _repo_file("tests/shared/terrain_fixture/generated/manifest.json")


func _fixture_manifest() -> Dictionary:
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(_fixture_manifest_path()))
	assert_typeof(parsed, TYPE_DICTIONARY, "the fixture manifest parses")
	return parsed


func before_all() -> void:
	DirAccess.make_dir_recursive_absolute(SCRATCH_DIR)


func after_all() -> void:
	_remove_tree(SCRATCH_DIR)


func _remove_tree(dir: String) -> void:
	for sub in DirAccess.get_directories_at(dir):
		_remove_tree(dir.path_join(sub))
	for file in DirAccess.get_files_at(dir):
		DirAccess.remove_absolute(dir.path_join(file))
	DirAccess.remove_absolute(dir)


## Writes a manifest and the fixture's heights file into a fresh case folder.
func _write_case(manifest: Dictionary) -> String:
	_cases += 1
	var dir := SCRATCH_DIR.path_join("case_%d" % _cases)
	DirAccess.make_dir_recursive_absolute(dir.path_join("terrain"))
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


func _assert_refused(path: String, grid: TerrainGrid, why: String, needle: String) -> void:
	assert_null(grid, "%s is refused" % why)
	var found := false
	for error in get_errors():
		if (
			not found
			and not error.handled
			and error.is_push_error()
			and error.contains_text(path)
			and error.contains_text(needle)
		):
			error.handled = true
			found = true
	assert_true(found, "%s: one push_error names %s and says %s" % [why, path, needle])


func test_the_fixture_world_places_the_fixture_grid() -> void:
	# The control: the same manifest and its own world are accepted.
	var path := _write_case(_fixture_manifest())
	var grid := TerrainGrid.from_manifest(path, WorldConfig.from_manifest(path))
	assert_not_null(grid, "the fixture, copied, is read")


func test_a_world_from_another_manifest_is_refused() -> void:
	# The case's origin moved 1 km east: a valid manifest whose own world places the grid at
	# local x 15, while the fixture's world would place it at x 1015, 1 km off.
	var manifest := _fixture_manifest()
	manifest["world"]["origin_lv95"]["e"] = 2601000.0
	var path := _write_case(manifest)
	var own := WorldConfig.from_manifest(path)
	assert_not_null(own, "the case's own world block is valid")
	var foreign := WorldConfig.from_manifest(_fixture_manifest_path())
	var grid := TerrainGrid.from_manifest(path, foreign)
	_assert_refused(path, grid, "the fixture's world for another manifest", "not read from this")


func test_a_fractional_column_count_is_refused() -> void:
	# A box a quarter metre wider fits 41.5 columns, so only the count check can refuse it.
	var manifest := _fixture_manifest()
	manifest["terrain"]["columns"] = 41.5
	manifest["terrain"]["lv95_box"]["e_max"] = 2601035.25
	var path := _write_case(manifest)
	var grid := TerrainGrid.from_manifest(path, WorldConfig.from_manifest(path))
	_assert_refused(path, grid, "41.5 columns", "whole number")


func test_a_rotated_world_is_refused_for_its_axes() -> void:
	# The pinned test_a_rotated_world_is_refused accepts any refusal, and the columns check
	# refuses this grid too (it does not fit the box once rotated); this one pins the reason.
	var manifest := _fixture_manifest()
	manifest["world"]["axes"] = {"x": "+n", "y": "+h", "z": "+e"}
	var path := _write_case(manifest)
	var grid := TerrainGrid.from_manifest(path, WorldConfig.from_manifest(path))
	_assert_refused(path, grid, "a world rotated about the vertical", "x=+e, y=+h, z=-n")
