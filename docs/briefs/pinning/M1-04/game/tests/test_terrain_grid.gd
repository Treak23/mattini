extends GutTest
## Pinning tests for brief M1-04: TerrainGrid reads the manifest's terrain block and its
## heights file, checked, and places the grid through WorldConfig.
##
## Pinned decisions (docs/SPEC.md §8, the terrain grid): the shared fixture
## (tests/shared/terrain_fixture/generated/) is read as the pipeline writes it: 41 columns
## by 24 rows at 0.5 m, column 0 at local x 1015.0 and row 0 at local z 10.5 (placed through
## the manifest's own world block, never by subtracting an origin here), heights as 32-bit
## local y (H - height_offset_m). Every problem is refused with push_error naming the
## manifest and a null result, never a plausible grid (Hard Rules 2 and 4); the two refusals
## the owner can fix by re-running the pipeline name the command.

const SCRATCH_DIR := "user://test_terrain_grid"
const TERRAIN_COMMAND := "python -m mattini terrain"

var _cases := 0


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


func _fixture_manifest_path() -> String:
	return _repo_file("tests/shared/terrain_fixture/generated/manifest.json")


func _fixture_heights_path() -> String:
	return _repo_file("tests/shared/terrain_fixture/generated/terrain/fixture.f32")


func _vectors() -> Dictionary:
	var text := FileAccess.get_file_as_string(_repo_file("tests/shared/terrain_vectors.json"))
	var parsed: Variant = JSON.parse_string(text)
	assert_typeof(parsed, TYPE_DICTIONARY, "the shared terrain vectors parse")
	return parsed


func _fixture_manifest() -> Dictionary:
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(_fixture_manifest_path()))
	assert_typeof(parsed, TYPE_DICTIONARY, "the fixture manifest parses")
	return parsed


func _fixture_heights() -> PackedByteArray:
	return FileAccess.get_file_as_bytes(_fixture_heights_path())


func before_all() -> void:
	DirAccess.make_dir_recursive_absolute(SCRATCH_DIR.path_join("terrain"))
	# The target of the "../terrain/fixture.f32" case exists and matches, so only a check of
	# the path itself can refuse it.
	var decoy := FileAccess.open(SCRATCH_DIR.path_join("terrain/fixture.f32"), FileAccess.WRITE)
	decoy.store_buffer(_fixture_heights())
	decoy.close()


func after_all() -> void:
	_remove_tree(SCRATCH_DIR)


func _remove_tree(dir: String) -> void:
	for sub in DirAccess.get_directories_at(dir):
		_remove_tree(dir.path_join(sub))
	for file in DirAccess.get_files_at(dir):
		DirAccess.remove_absolute(dir.path_join(file))
	DirAccess.remove_absolute(dir)


## Writes a manifest and (unless heights is null) terrain/fixture.f32 into a fresh folder
## under SCRATCH_DIR, laid out like the generated folder; returns the manifest's path.
func _write_case(manifest: Dictionary, heights: Variant) -> String:
	_cases += 1
	var dir := SCRATCH_DIR.path_join("case_%d" % _cases)
	DirAccess.make_dir_recursive_absolute(dir.path_join("terrain"))
	var path := dir.path_join("manifest.json")
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string(JSON.stringify(manifest, "  ", true, true))
	file.close()
	if heights != null:
		var data := FileAccess.open(dir.path_join("terrain/fixture.f32"), FileAccess.WRITE)
		data.store_buffer(heights)
		data.close()
	return path


## The grid a case manifest yields, read with the world block of that same manifest.
func _read(path: String) -> TerrainGrid:
	var world := WorldConfig.from_manifest(path)
	assert_not_null(world, "the case's world block itself is valid: %s" % path)
	return TerrainGrid.from_manifest(path, world)


## Asserts one push_error naming the manifest (and containing needle, when given).
func _assert_refused(path: String, grid: TerrainGrid, why: String, needle := "") -> void:
	assert_null(grid, "%s is refused" % why)
	var found := false
	for error in get_errors():
		if (
			not found
			and not error.handled
			and error.is_push_error()
			and error.contains_text(path)
			and (needle == "" or error.contains_text(needle))
		):
			error.handled = true
			found = true
	assert_true(found, "%s: one push_error names %s %s" % [why, path, needle])


func test_the_fixture_grid_is_read_as_designed() -> void:
	var world := WorldConfig.from_manifest(_fixture_manifest_path())
	var grid := TerrainGrid.from_manifest(_fixture_manifest_path(), world)
	assert_not_null(grid, "the fixture grid is read")
	if grid == null:
		return
	var expected: Dictionary = _vectors()["grid"]
	assert_eq(grid.area, "fixture")
	assert_eq(grid.columns, int(expected["columns"]))
	assert_eq(grid.rows, int(expected["rows"]))
	assert_eq(grid.spacing_m, float(expected["spacing_m"]))
	assert_eq(grid.x_min, float(expected["x_min"]), "column 0 lies at local x 1015.0")
	assert_eq(grid.z_min, float(expected["z_min"]), "row 0 lies at local z 10.5")
	assert_eq(grid.height_offset_m, float(expected["height_offset_m"]))
	assert_eq(grid.heights.size(), grid.columns * grid.rows)
	assert_eq(grid.attribution, "© swisstopo")


func test_heights_are_the_fixtures_local_heights() -> void:
	var world := WorldConfig.from_manifest(_fixture_manifest_path())
	var grid := TerrainGrid.from_manifest(_fixture_manifest_path(), world)
	assert_not_null(grid, "the fixture grid is read")
	if grid == null:
		return
	for v: Dictionary in _vectors()["vertices"]:
		var column := int(v["column"])
		var row := int(v["row"])
		assert_eq(grid.height(column, row), float(v["y"]), v["name"])
		assert_eq(
			grid.heights[row * grid.columns + column], float(v["y"]), "%s: row-major" % v["name"]
		)


func test_a_manifest_without_terrain_names_the_command() -> void:
	var manifest := _fixture_manifest()
	manifest["terrain"] = null
	var path := _write_case(manifest, null)
	_assert_refused(path, _read(path), "a manifest whose terrain is null", TERRAIN_COMMAND)


func test_terrain_built_for_another_world_names_the_command() -> void:
	var manifest := _fixture_manifest()
	manifest["terrain"]["world_sha256"] = "0".repeat(64)
	var path := _write_case(manifest, _fixture_heights())
	_assert_refused(path, _read(path), "terrain built for another world config", TERRAIN_COMMAND)


func test_a_missing_manifest_is_refused() -> void:
	var path := SCRATCH_DIR.path_join("no_such_folder/manifest.json")
	var grid := TerrainGrid.from_manifest(path, WorldConfig.from_manifest(_fixture_manifest_path()))
	_assert_refused(path, grid, "a missing manifest")


func test_a_rotated_world_is_refused() -> void:
	# A proper rotation WorldConfig accepts; the terrain grid is defined for x=+e, y=+h, z=-n.
	var manifest := _fixture_manifest()
	manifest["world"]["axes"] = {"x": "+n", "y": "+h", "z": "+e"}
	var path := _write_case(manifest, _fixture_heights())
	_assert_refused(path, _read(path), "a world rotated about the vertical")


func test_a_grid_off_the_vertex_lattice_is_refused() -> void:
	# Shifted by a quarter metre: 41 columns still fit the box, but column 0 would sit at
	# x = 1015.25, between Terrain3D's vertices (multiples of 0.5 m).
	var manifest := _fixture_manifest()
	manifest["terrain"]["lv95_box"]["e_min"] = 2601015.25
	manifest["terrain"]["lv95_box"]["e_max"] = 2601035.25
	var path := _write_case(manifest, _fixture_heights())
	_assert_refused(path, _read(path), "a grid between the vertices")


func test_malformed_terrain_blocks_are_refused() -> void:
	var cases := {
		"a block without rows": func(t: Dictionary) -> void: t.erase("rows"),
		"another file format": func(t: Dictionary) -> void: t["format"] = "float64-le",
		"a spacing that is not 0.5, 1 or 2 m": func(t: Dictionary) -> void: t["spacing_m"] = 0.25,
		"columns that do not fit the box": func(t: Dictionary) -> void: t["columns"] = 42,
		"a file outside the manifest's folder":
		func(t: Dictionary) -> void: t["file"] = "../terrain/fixture.f32",
	}
	for why: String in cases:
		var manifest := _fixture_manifest()
		(cases[why] as Callable).call(manifest["terrain"])
		var path := _write_case(manifest, _fixture_heights())
		_assert_refused(path, _read(path), why)


func test_heights_files_that_do_not_match_are_refused() -> void:
	var short := _fixture_heights()
	short.resize(short.size() - 4)
	var changed := _fixture_heights()
	changed[100] = changed[100] ^ 1
	var cases := {"a missing heights file": null, "a file one height short": short}
	cases["a file with one bit changed"] = changed
	for why: String in cases:
		var path := _write_case(_fixture_manifest(), cases[why])
		_assert_refused(path, _read(path), why)
