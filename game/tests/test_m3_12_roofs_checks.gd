extends GutTest
## Brief M3-12's own tests: the refusals of BuildingRoofs that the pinned tests do not reach.
##
## The pinned test_building_roofs.gd reads the shared roofs fixture and refuses a missing
## block, another world's block, chunks in another order and counts that do not add up. This
## one refuses the rest of the brief's list: key sets that are not exact, the format and the
## area, the buildings' source, uuids that do not ascend, a roof that is not a lower-case
## rrggbb, a null roof with photo pixels, a colour from no pixel, a building count that is
## not the chunk's, and a WorldConfig that is not the manifest's. It calls _read, which
## returns the problem as text, instead of from_manifest, which prints it as an ERROR line:
## the gate's allowlist holds the pinned test's line only (brief M3-12, decision 5). The
## wording of each refusal is not pinned; the test checks that the refusal names the thing
## that is wrong.
##
## Does NOT prove: that from_manifest prints the problem (the pinned tests do); that the
## real village's block reads the same way.

const SCRATCH_DIR := "user://test_m3_12_roofs_checks"
const FIXTURE := "tests/shared/roofs_fixture/generated/manifest.json"

var _cases := 0
var _world: WorldConfig
var _chunks: BuildingChunks


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


func before_all() -> void:
	var path := _repo_file(FIXTURE)
	_world = WorldConfig.from_manifest(path)
	_chunks = BuildingChunks.from_manifest(path, _world)


func after_all() -> void:
	_remove_tree(SCRATCH_DIR)


func _remove_tree(dir: String) -> void:
	for sub in DirAccess.get_directories_at(dir):
		_remove_tree(dir.path_join(sub))
	for file in DirAccess.get_files_at(dir):
		DirAccess.remove_absolute(dir.path_join(file))
	DirAccess.remove_absolute(dir)


func _parse(path: String) -> Dictionary:
	var json := JSON.new()
	assert_eq(json.parse(FileAccess.get_file_as_string(path)), OK, "%s parses" % path)
	return json.data if typeof(json.data) == TYPE_DICTIONARY else {}


## The fixture's manifest, changed by [param change] (a Callable taking the manifest
## Dictionary), written to a scratch folder; returns its path. Only the manifest is needed:
## BuildingRoofs reads no chunk file.
func _write_case(change: Callable) -> String:
	_cases += 1
	var dir := SCRATCH_DIR.path_join("case_%d" % _cases)
	DirAccess.make_dir_recursive_absolute(dir)
	var manifest := _parse(_repo_file(FIXTURE))
	change.call(manifest)
	var out := FileAccess.open(dir.path_join("manifest.json"), FileAccess.WRITE)
	out.store_string(JSON.stringify(manifest, "  ", true, true))
	out.close()
	return dir.path_join("manifest.json")


## What BuildingRoofs finds wrong with the case, "" when it reads it.
func _problem(change: Callable) -> String:
	var path := _write_case(change)
	return BuildingRoofs.new()._read(path, _world, _chunks)


func _building(manifest: Dictionary, tile: String, at: int) -> Dictionary:
	for entry: Dictionary in manifest["roofs"]["chunks"]:
		if entry["tile"] == tile:
			return entry["buildings"][at]
	return {}


func _assert_refused(problem: String, why: String, needle: String) -> void:
	assert_ne(problem, "", "%s is refused" % why)
	assert_true(problem.contains(needle), "%s: the problem names '%s': %s" % [why, needle, problem])


func test_the_unchanged_fixture_is_read() -> void:
	assert_eq(_problem(func(_m: Dictionary) -> void: pass), "", "the fixture itself is read")


func test_the_block_must_have_exactly_its_keys() -> void:
	_assert_refused(
		_problem(func(m: Dictionary) -> void: m["roofs"]["extra"] = 1), "an extra block key", "keys"
	)
	_assert_refused(
		_problem(func(m: Dictionary) -> void: m["roofs"].erase("lv95_box")),
		"a missing block key",
		"keys"
	)
	_assert_refused(
		_problem(func(m: Dictionary) -> void: m["roofs"]["source"]["extra"] = 1),
		"an extra source key",
		"roofs.source"
	)
	_assert_refused(
		_problem(func(m: Dictionary) -> void: m["roofs"]["chunks"][0]["extra"] = 1),
		"an extra chunk key",
		"roofs.chunks[0]"
	)
	_assert_refused(
		_problem(func(m: Dictionary) -> void: _building(m, "2650-1149", 0).erase("roof_pixels")),
		"a building without roof_pixels",
		"roof_pixels"
	)


func test_the_format_and_the_area_must_be_the_buildings() -> void:
	_assert_refused(
		_problem(func(m: Dictionary) -> void: m["roofs"]["format"] = "roofs-v2"),
		"another format",
		"format"
	)
	_assert_refused(
		_problem(func(m: Dictionary) -> void: m["roofs"]["area"] = "elsewhere"),
		"another area",
		"area"
	)


func test_the_buildings_source_must_be_the_manifests() -> void:
	_assert_refused(
		_problem(
			func(m: Dictionary) -> void: m["roofs"]["source"]["buildings"]["edition"] = "2099"
		),
		"roof colours measured on other buildings",
		"buildings.source"
	)
	_assert_refused(
		_problem(func(m: Dictionary) -> void: m["roofs"]["source"]["photo"]["edition"] = ""),
		"a photo source without an edition",
		"edition"
	)


func test_the_uuids_must_ascend() -> void:
	var swap := func(m: Dictionary) -> void:
		var first := _building(m, "2650-1149", 0)
		var second := _building(m, "2650-1149", 1)
		var uuid: String = first["uuid"]
		first["uuid"] = second["uuid"]
		second["uuid"] = uuid
	_assert_refused(_problem(swap), "two buildings out of order", "ascend")
	var repeat := func(m: Dictionary) -> void:
		_building(m, "2650-1149", 1)["uuid"] = _building(m, "2650-1149", 0)["uuid"]
	_assert_refused(_problem(repeat), "a uuid twice", "ascend")


func test_a_roof_is_a_lower_case_rrggbb_or_null() -> void:
	for roof: Variant in ["636C0C", "636c0", "636c0cc", "+636c0", "-636c0", "zzzzzz", 636, ""]:
		var change := func(m: Dictionary) -> void: _building(m, "2650-1149", 0)["roof"] = roof
		_assert_refused(_problem(change), "the roof %s" % [roof], "roof")


func test_a_null_roof_and_the_photo_pixels_must_agree() -> void:
	_assert_refused(
		_problem(func(m: Dictionary) -> void: _building(m, "2650-1149", 0)["roof"] = null),
		"no colour for a roof with photo pixels",
		"roof is null"
	)
	_assert_refused(
		_problem(func(m: Dictionary) -> void: _building(m, "2650-1149", 0)["roof_pixels"] = 0),
		"a colour from no photo pixel",
		"no photo pixel"
	)
	_assert_refused(
		_problem(func(m: Dictionary) -> void: _building(m, "2650-1149", 0)["roof_pixels"] = -1),
		"a negative pixel count",
		"roof_pixels"
	)


func test_the_counts_must_be_whole_and_positive() -> void:
	_assert_refused(
		_problem(func(m: Dictionary) -> void: _building(m, "2650-1149", 0)["triangles"] = 0),
		"a building without triangles",
		"triangles"
	)
	_assert_refused(
		_problem(func(m: Dictionary) -> void: _building(m, "2650-1149", 0)["vertices"] = 2.5),
		"half a vertex",
		"vertices"
	)


func test_the_building_count_must_be_the_chunks() -> void:
	var fewer := func(m: Dictionary) -> void: m["roofs"]["chunks"][0]["buildings"].pop_back()
	_assert_refused(_problem(fewer), "a building missing from 2650-1149", "2650-1149")
	var fewer_chunks := func(m: Dictionary) -> void: m["roofs"]["chunks"].pop_back()
	_assert_refused(_problem(fewer_chunks), "a chunk missing", "chunks")


func test_the_sums_must_be_the_chunk_files() -> void:
	# The last building of 2650-1150 takes one triangle less, or one vertex more, than the file
	# holds: every index it keeps is still inside its own vertices, so only the sums tell.
	var fewer_triangles := func(m: Dictionary) -> void:
		var b := _building(m, "2650-1150", 1)
		b["triangles"] = b["triangles"] - 1
	_assert_refused(_problem(fewer_triangles), "one triangle too few in 2650-1150", "2650-1150")
	var more_vertices := func(m: Dictionary) -> void:
		var b := _building(m, "2650-1150", 1)
		b["vertices"] = b["vertices"] + 1
	_assert_refused(_problem(more_vertices), "one vertex too many in 2650-1150", "2650-1150")


func test_the_world_config_must_be_the_manifests() -> void:
	var path := _write_case(func(m: Dictionary) -> void: m["world"]["height_offset_m"] = 501.0)
	_assert_refused(
		BuildingRoofs.new()._read(path, _world, _chunks),
		"a WorldConfig of another height offset",
		"WorldConfig"
	)
	_assert_refused(
		BuildingRoofs.new()._read(_repo_file(FIXTURE), null, _chunks),
		"no WorldConfig",
		"WorldConfig"
	)
	_assert_refused(
		BuildingRoofs.new()._read(_repo_file(FIXTURE), _world, null),
		"no BuildingChunks",
		"BuildingChunks"
	)


func test_the_properties_come_from_the_photo_source() -> void:
	var roofs := BuildingRoofs.new()
	assert_eq(roofs._read(_repo_file(FIXTURE), _world, _chunks), "", "the fixture is read")
	assert_eq(roofs.area, "fixture", "the area")
	assert_eq(roofs.dataset, "swissimage", "the photo's dataset")
	assert_eq(roofs.edition, "2023", "the photo's edition")
	assert_eq(roofs.attribution, "© swisstopo", "the photo's attribution")
	assert_eq(roofs.chunks.size(), 4, "four chunks")
