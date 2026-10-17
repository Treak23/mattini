extends GutTest
## Pinning tests for brief M4-10: SkySite reads the manifest's sky block, the place the sun and
## the moon are computed for.
##
## Pinned decisions (m4-design §4; brief M4-09 decision 2, the block; brief M4-10): SkySite
## (res://scripts/sky/sky_site.gd), `static func from_manifest(path, world) -> SkySite`, null
## after one push_error("SkySite: <path>: <problem>") as every reader; `_read(path, world)`
## returns the problem without logging it. Properties area, latitude_deg, longitude_deg,
## true_to_grid_deg (float). It refuses, in this order: no WorldConfig; a manifest that cannot
## be read or is not an object; a null block ("the sun's place has not been written: run python
## -m mattini sky"); a block that is not an object; a world_sha256 that is not text or not the
## manifest's (naming python -m mattini sky); a WorldConfig not read from this manifest
## (BuildingChunks' check: any axes are fine, the directions go through the world config); a
## key set other than exactly {area, latitude_deg, longitude_deg, true_to_grid_deg,
## world_sha256}; an area that is not one of the world config's areas; a latitude, longitude or
## convergence that is not a finite number or beyond 90, 180 and 10 degrees. Every compare is
## typed (brain.md H26). Every refusal but the world's names python -m mattini sky.
##
## The cases are the complete test world's manifest (complete_world.gd, whose sky block holds
## config/sky.json's village values as test data) changed one way each; brief M4-09's fixture
## manifests are not read, so this brief does not wait for M4-09's landing.
##
## Does NOT prove: that the block's numbers are the area's centre (the pipeline's tests and
## config/sky.json's computed_for do); anything the main scene does with them
## (test_main_scene_light.gd).

const CompleteWorld := preload("res://tests/complete_world.gd")
const SCRATCH_DIR := "user://test_m4_10_sky_site"
const COMMAND := "python -m mattini sky"

var _cases := 0
var _complete := ""


func before_all() -> void:
	_complete = CompleteWorld.write(SCRATCH_DIR.path_join("complete"))


func after_all() -> void:
	CompleteWorld.remove_tree(SCRATCH_DIR)


func _remove_tree(dir: String) -> void:
	for sub in DirAccess.get_directories_at(dir):
		_remove_tree(dir.path_join(sub))
	for file in DirAccess.get_files_at(dir):
		DirAccess.remove_absolute(dir.path_join(file))
	DirAccess.remove_absolute(dir)


func _fixture() -> String:
	return _complete


func _manifest() -> Dictionary:
	var json := JSON.new()
	assert_eq(json.parse(FileAccess.get_file_as_string(_fixture())), OK, "the world parses")
	return json.data if typeof(json.data) == TYPE_DICTIONARY else {}


## The fixture's manifest with [param change] applied, written under SCRATCH_DIR.
func _write(change: Callable) -> String:
	var manifest := _manifest()
	change.call(manifest)
	_cases += 1
	DirAccess.make_dir_recursive_absolute(SCRATCH_DIR)
	var path := SCRATCH_DIR.path_join("case_%d.json" % _cases)
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string(JSON.stringify(manifest, "  ", true, true))
	file.close()
	return path


## The problem SkySite finds in the fixture with [param change], read with its own world.
func _problem(change: Callable) -> String:
	var path := _write(change)
	var site := SkySite.new()
	return site._read(path, WorldConfig.from_manifest(path))


func test_the_complete_world_s_sky_block_is_read() -> void:
	var path := _fixture()
	var site := SkySite.from_manifest(path, WorldConfig.from_manifest(path))
	assert_not_null(site, "the complete world's sky block is accepted")
	if site == null:
		return
	var block: Dictionary = _manifest()["sky"]
	assert_eq(site.area, "fixture", "its area")
	assert_eq(site.latitude_deg, block["latitude_deg"], "its latitude, as written")
	assert_eq(site.longitude_deg, block["longitude_deg"], "its longitude")
	assert_eq(site.true_to_grid_deg, block["true_to_grid_deg"], "its convergence, sign kept")
	assert_lt(site.true_to_grid_deg, 0.0, "the village's convergence is negative")


func test_no_world_config_is_refused() -> void:
	assert_eq(SkySite.new()._read(_fixture(), null), "no WorldConfig was given")


func test_a_missing_block_names_the_sky_command() -> void:
	var problem := _problem(func(m: Dictionary) -> void: m["sky"] = null)
	assert_eq(problem, "the sun's place has not been written: run " + COMMAND)


func test_a_block_that_is_not_an_object_is_refused() -> void:
	var problem := _problem(func(m: Dictionary) -> void: m["sky"] = [1, 2])
	assert_string_contains(problem, "sky must be an object or null")


func test_another_world_is_refused() -> void:
	var cases := [
		func(m: Dictionary) -> void: m["sky"]["world_sha256"] = "0".repeat(64),
		func(m: Dictionary) -> void: m["sky"]["world_sha256"] = 7,
		func(m: Dictionary) -> void: m["sky"].erase("world_sha256"),
	]
	for change: Callable in cases:
		var problem := _problem(change)
		assert_string_contains(problem, "another world config", "refused, not a runtime error")
		assert_string_contains(problem, COMMAND)


func test_a_world_config_of_another_manifest_is_refused() -> void:
	var path := _write(func(_m: Dictionary) -> void: pass)
	var other := _write(func(m: Dictionary) -> void: m["world"]["height_offset_m"] = 0.0)
	var problem := SkySite.new()._read(path, WorldConfig.from_manifest(other))
	assert_string_contains(problem, "not read from this manifest")


func test_another_key_set_is_refused() -> void:
	var cases := [
		func(m: Dictionary) -> void: m["sky"]["elevation_deg"] = 1.0,
		func(m: Dictionary) -> void: m["sky"].erase("true_to_grid_deg"),
	]
	for change: Callable in cases:
		var problem := _problem(change)
		assert_string_contains(problem, "sky must hold exactly")
		assert_string_contains(problem, COMMAND)


func test_an_area_not_in_the_world_is_refused() -> void:
	for area: Variant in ["village", 3, ""]:
		var problem := _problem(func(m: Dictionary) -> void: m["sky"]["area"] = area)
		assert_string_contains(problem, "is not an area of the world config", "area %s" % [area])


func test_values_out_of_range_or_not_numbers_are_refused() -> void:
	var cases := [
		["latitude_deg", 90.5],
		["latitude_deg", "46.0"],
		["longitude_deg", -180.5],
		["longitude_deg", null],
		["true_to_grid_deg", 10.5],
		["true_to_grid_deg", true],
	]
	for case: Array in cases:
		var problem := _problem(func(m: Dictionary) -> void: m["sky"][case[0]] = case[1])
		assert_string_contains(problem, "sky.%s must be a finite number" % case[0], str(case))
		assert_string_contains(problem, COMMAND)


func test_the_limits_themselves_are_accepted() -> void:
	var edge := func(m: Dictionary) -> void:
		m["sky"]["latitude_deg"] = -90.0
		m["sky"]["longitude_deg"] = 180.0
		m["sky"]["true_to_grid_deg"] = 10.0
	assert_eq(_problem(edge), "", "90, 180 and 10 degrees are accepted")
