extends GutTest
## Brief M3-11, the checks the pinned TreeChunks tests leave open: each refusal of the
## reader, and the editions, reached through TreeChunks._read, which returns the problem
## instead of calling push_error (so no ERROR line reaches the gate's scan).
##
## What each case must catch: a block read with its key set changed, another format, a
## damaged chunk entry, a file path that leaves the manifest's folder, a missing file, a
## WorldConfig that is not the manifest's (another origin, other axes) or that is not the
## owner's (x = +e, y = +h, z = -n), and an `edition` taken from the datasets config's list
## instead of the tiles' own.
##
## Does NOT prove: that the trees render or look right (no GPU); the pinned tests' own
## cases (a missing block, another world_sha256, a damaged or short chunk file), which go
## through from_manifest and its push_error.

const SCRATCH_DIR := "user://test_m3_11_tree_chunks"

var _cases := 0


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


func _fixture_manifest_path() -> String:
	return _repo_file("tests/shared/trees_fixture/generated/manifest.json")


func _parse(path: String) -> Dictionary:
	var json := JSON.new()
	assert_eq(json.parse(FileAccess.get_file_as_string(path)), OK, "%s parses" % path)
	return json.data if typeof(json.data) == TYPE_DICTIONARY else {}


func after_all() -> void:
	_remove_tree(SCRATCH_DIR)


func _remove_tree(dir: String) -> void:
	for sub in DirAccess.get_directories_at(dir):
		_remove_tree(dir.path_join(sub))
	for file in DirAccess.get_files_at(dir):
		DirAccess.remove_absolute(dir.path_join(file))
	DirAccess.remove_absolute(dir)


## A copy of the fixture's generated folder with the manifest changed by [param change];
## returns the copy's manifest path.
func _write_case(change: Callable) -> String:
	_cases += 1
	var dir := SCRATCH_DIR.path_join("case_%d" % _cases)
	DirAccess.make_dir_recursive_absolute(dir.path_join("trees"))
	var manifest := _parse(_fixture_manifest_path())
	change.call(manifest)
	var out := FileAccess.open(dir.path_join("manifest.json"), FileAccess.WRITE)
	out.store_string(JSON.stringify(manifest, "  ", true, true))
	out.close()
	var source_dir := _fixture_manifest_path().get_base_dir()
	for entry: Dictionary in _parse(_fixture_manifest_path())["trees"]["chunks"]:
		var data := FileAccess.get_file_as_bytes(source_dir.path_join(entry["file"]))
		var file := FileAccess.open(dir.path_join(entry["file"]), FileAccess.WRITE)
		file.store_buffer(data)
		file.close()
	return dir.path_join("manifest.json")


## What TreeChunks._read says about the case made by [param change], read with the
## WorldConfig of that same manifest.
func _problem(change: Callable) -> String:
	var path := _write_case(change)
	var world := WorldConfig.from_manifest(path)
	assert_not_null(world, "the case's world block itself is valid")
	return TreeChunks.new()._read(path, world)


func _assert_refused(change: Callable, why: String, needle: String) -> void:
	var problem := _problem(change)
	assert_ne(problem, "", "%s is refused" % why)
	assert_true(
		problem.contains(needle), "%s: the problem names '%s', found: %s" % [why, needle, problem]
	)


func test_the_unchanged_fixture_is_accepted() -> void:
	assert_eq(_problem(func(_m: Dictionary) -> void: pass), "", "the fixture passes the checks")


func test_the_block_must_have_exactly_its_keys() -> void:
	_assert_refused(func(m: Dictionary) -> void: m["trees"]["extra"] = 1, "an extra key", "exactly")
	_assert_refused(
		func(m: Dictionary) -> void: m["trees"].erase("parameters"), "a missing key", "exactly"
	)
	_assert_refused(
		func(m: Dictionary) -> void: m["trees"]["format"] = "trees-f32x4-le",
		"another format",
		"format"
	)
	_assert_refused(
		func(m: Dictionary) -> void: m["trees"]["area"] = "", "no area name", "trees.area"
	)
	_assert_refused(
		func(m: Dictionary) -> void: m["trees"]["chunks"] = [], "no chunks", "trees.chunks"
	)
	_assert_refused(
		func(m: Dictionary) -> void: m["trees"] = [1], "a block that is a list", "trees"
	)


func test_the_box_and_the_parameters_must_be_complete() -> void:
	_assert_refused(
		func(m: Dictionary) -> void: m["trees"]["lv95_box"].erase("n_max"),
		"a box without n_max",
		"lv95_box"
	)
	_assert_refused(
		func(m: Dictionary) -> void: m["trees"]["lv95_box"]["e_min"] = "2650976",
		"a text easting",
		"e_min"
	)
	_assert_refused(
		func(m: Dictionary) -> void: m["trees"]["parameters"]["extra"] = 1,
		"a parameter nobody knows",
		"parameters"
	)
	_assert_refused(
		func(m: Dictionary) -> void: m["trees"]["parameters"].erase("window"),
		"a parameter missing",
		"parameters"
	)


func test_the_source_must_name_the_four_datasets() -> void:
	_assert_refused(
		func(m: Dictionary) -> void: m["trees"]["source"].erase("swisstlm3d"),
		"a source without the TLM",
		"trees.source"
	)
	_assert_refused(
		func(m: Dictionary) -> void: m["trees"]["source"]["swissalti3d"]["dataset"] = "swissimage",
		"a dataset block under another name",
		"swissalti3d"
	)
	var surface := "swisssurface3d"
	_assert_refused(
		func(m: Dictionary) -> void: m["trees"]["source"][surface].erase("tiles"),
		"a surface block without tiles",
		"tiles"
	)
	_assert_refused(
		func(m: Dictionary) -> void: m["trees"]["source"][surface]["tiles"] = [],
		"no surface tiles",
		"tiles"
	)
	_assert_refused(
		func(m: Dictionary) -> void: m["trees"]["source"][surface]["tiles"][0]["extra"] = 1,
		"a surface tile with an extra key",
		"tiles[0]"
	)
	_assert_refused(
		func(m: Dictionary) -> void: m["trees"]["source"][surface]["tiles"][1]["edition"] = 2021,
		"an edition that is a number",
		"edition"
	)
	_assert_refused(
		func(m: Dictionary) -> void: m["trees"]["source"][surface]["attribution"] = "",
		"no attribution",
		"attribution"
	)


func test_a_chunk_entry_must_be_exact() -> void:
	_assert_refused(
		func(m: Dictionary) -> void: m["trees"]["chunks"][0]["extra"] = 1,
		"an entry with an extra key",
		"chunks[0]"
	)
	_assert_refused(
		func(m: Dictionary) -> void: m["trees"]["chunks"][1].erase("sha256"),
		"an entry without a checksum",
		"chunks[1]"
	)
	_assert_refused(
		func(m: Dictionary) -> void: m["trees"]["chunks"][0]["tile"] = "2650/1149",
		"a tile id that is not one",
		"tile"
	)
	_assert_refused(
		func(m: Dictionary) -> void: m["trees"]["chunks"][1]["tile"] = "2650-1149",
		"two chunks of one tile",
		"has a chunk already"
	)
	for count: Variant in [0.0, 2.5, -1.0, "6"]:
		_assert_refused(
			func(m: Dictionary) -> void: m["trees"]["chunks"][0]["trees"] = count,
			"a tree count of %s" % [count],
			"trees must be a whole number"
		)
	_assert_refused(
		func(m: Dictionary) -> void: m["trees"]["chunks"][0]["sha256"] = "abc",
		"a short checksum",
		"sha256"
	)


func test_a_file_path_must_stay_in_the_manifests_folder() -> void:
	for file: String in [
		"../trees/2650-1149.bin", "/etc/passwd", "trees\\2650-1149.bin", "c:x.bin", ""
	]:
		_assert_refused(
			func(m: Dictionary) -> void: m["trees"]["chunks"][0]["file"] = file,
			"the file path '%s'" % file,
			"plain relative path"
		)


func test_a_missing_chunk_file_is_named_before_it_is_read() -> void:
	var path := _write_case(func(_m: Dictionary) -> void: pass)
	DirAccess.remove_absolute(path.get_base_dir().path_join("trees/2650-1150.bin"))
	var problem := TreeChunks.new()._read(path, WorldConfig.from_manifest(path))
	assert_true(problem.contains("2650-1150") and problem.contains("is missing"), problem)
	assert_true(problem.contains("python -m mattini trees"), "it names the command: %s" % problem)


func test_a_world_config_that_is_not_the_manifests_is_refused() -> void:
	var path := _write_case(func(_m: Dictionary) -> void: pass)
	var other := _write_case(func(m: Dictionary) -> void: m["world"]["origin_lv95"]["e"] += 1000.0)
	var problem := TreeChunks.new()._read(path, WorldConfig.from_manifest(other))
	assert_true(problem.contains("not read from this manifest"), "another origin: %s" % problem)
	var turned := _write_case(
		func(m: Dictionary) -> void: m["world"]["axes"] = {"x": "+n", "y": "+h", "z": "+e"}
	)
	problem = TreeChunks.new()._read(path, WorldConfig.from_manifest(turned))
	assert_true(problem.contains("not read from this manifest"), "other axes: %s" % problem)
	problem = TreeChunks.new()._read(path, null)
	assert_true(problem.contains("no WorldConfig"), "no world at all: %s" % problem)


func test_a_world_that_is_not_the_owners_axes_is_refused() -> void:
	# The manifest itself maps east to +z (a proper rotation, so WorldConfig takes it): the
	# trees' base heights and positions are defined for the owner's axes only.
	var problem := _problem(
		func(m: Dictionary) -> void: m["world"]["axes"] = {"x": "+n", "y": "+h", "z": "+e"}
	)
	assert_true(problem.contains("the trees need the axes x=+e, y=+h, z=-n"), problem)


func test_the_edition_is_the_first_and_last_of_the_tiles() -> void:
	var tiles := "swisssurface3d"
	var editions := {
		"all tiles share one": [["2021", "2021", "2021", "2021"], "2021"],
		"two editions": [["2022", "2021", "2021", "2021"], "2021-2022"],
		"three editions in no order": [["2022", "2019", "2021", "2021"], "2019-2022"],
		"the other way round": [["2019", "2022", "2019", "2022"], "2019-2022"],
	}
	for why: String in editions:
		var path := _write_case(
			func(m: Dictionary) -> void:
				for i in 4:
					m["trees"]["source"][tiles]["tiles"][i]["edition"] = editions[why][0][i]
		)
		var trees := TreeChunks.new()
		assert_eq(trees._read(path, WorldConfig.from_manifest(path)), "", why)
		assert_eq(
			trees.edition, editions[why][1], "%s: the tiles' editions, not the config's list" % why
		)
