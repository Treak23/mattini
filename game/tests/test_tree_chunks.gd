extends GutTest
## Pinning tests for brief M3-11: TreeChunks reads the manifest's trees block and its chunk
## files, checked, and never converts a coordinate itself.
##
## Pinned decisions (m3-design §5 and §9, the trees): the shared trees fixture
## (tests/shared/trees_fixture/generated/, its trees named in tests/shared/trees_vectors.json,
## computed by design two independent ways) is read as the pipeline writes it: three chunks in
## the block's order, 20 bytes per tree, local x, y, z of the tree's base, its height and its
## crown radius as little-endian float32. The seam: every named tree lies where
## WorldConfig.to_local puts its LV95 base point, and its file values arrive unchanged (Hard
## Rule 4). `dataset` is "swisssurface3d"; `edition` is the first and last of the editions of
## the source's swisssurface3d tiles joined by "-" ("2021-2022" here: the datasets config's
## list also names 2019, which no tile uses), one edition alone when they share one. Every
## problem is refused with one push_error naming the manifest and a null result (Hard Rule 2).
##
## Does NOT prove: that the trees render or look right (no GPU); the real village's chunks
## (the real run against config/trees.json does).

const SCRATCH_DIR := "user://test_tree_chunks"
const TREES_COMMAND := "python -m mattini trees"

var _cases := 0


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


func _fixture_manifest_path() -> String:
	return _repo_file("tests/shared/trees_fixture/generated/manifest.json")


func _parse(path: String) -> Dictionary:
	var json := JSON.new()
	assert_eq(json.parse(FileAccess.get_file_as_string(path)), OK, "%s parses" % path)
	return json.data if typeof(json.data) == TYPE_DICTIONARY else {}


func _vectors() -> Dictionary:
	return _parse(_repo_file("tests/shared/trees_vectors.json"))


func _read_fixture() -> TreeChunks:
	var world := WorldConfig.from_manifest(_fixture_manifest_path())
	return TreeChunks.from_manifest(_fixture_manifest_path(), world)


func after_all() -> void:
	_remove_tree(SCRATCH_DIR)


func _remove_tree(dir: String) -> void:
	for sub in DirAccess.get_directories_at(dir):
		_remove_tree(dir.path_join(sub))
	for file in DirAccess.get_files_at(dir):
		DirAccess.remove_absolute(dir.path_join(file))
	DirAccess.remove_absolute(dir)


func test_the_fixture_chunks_are_read_as_designed() -> void:
	var trees := _read_fixture()
	assert_not_null(trees, "the fixture's trees are read")
	if trees == null:
		return
	assert_eq(trees.area, "fixture")
	assert_eq(trees.dataset, "swisssurface3d")
	assert_eq(trees.edition, "2021-2022", "the editions the tiles use, not the config's list")
	assert_eq(trees.attribution, "© swisstopo")
	var block: Dictionary = _parse(_fixture_manifest_path())["trees"]
	var counts: Dictionary = _vectors()["chunks"]
	assert_eq(trees.chunks.size(), 3, "three chunks: the fourth tile has no tree")
	for i in trees.chunks.size():
		var chunk: Dictionary = trees.chunks[i]
		var entry: Dictionary = block["chunks"][i]
		assert_eq(chunk["tile"], entry["tile"], "chunks in the block's order")
		assert_eq(chunk["trees"], int(counts[entry["tile"]]), "%s: trees" % entry["tile"])
		for key in ["positions", "heights", "radii"]:
			assert_eq(chunk[key].size(), chunk["trees"], "%s: %s" % [entry["tile"], key])


func test_every_named_tree_is_where_the_world_config_puts_it() -> void:
	var trees := _read_fixture()
	var world := WorldConfig.from_manifest(_fixture_manifest_path())
	assert_not_null(trees, "the fixture's trees are read")
	if trees == null:
		return
	var by_tile := {}
	for chunk: Dictionary in trees.chunks:
		by_tile[chunk["tile"]] = chunk
	var named: Array = _vectors()["trees"]
	assert_eq(named.size(), 19, "the vectors name every tree of the fixture")
	for t: Dictionary in named:
		var chunk: Dictionary = by_tile[t["tile"]]
		var k := int(t["index"])
		var got: Vector3 = chunk["positions"][k]
		var local: Array = t["local"]
		# The file's own float32 values, exactly: nothing converted.
		assert_eq(got, Vector3(local[0], local[1], local[2]), "%s: as written" % t["name"])
		assert_eq(chunk["heights"][k], float(t["height_m"]), "%s: height" % t["name"])
		assert_eq(chunk["radii"][k], float(t["crown_radius_m"]), "%s: crown radius" % t["name"])
		# The seam: the pipeline's placement is the world config's (Hard Rule 4).
		var lv95: Array = t["lv95"]
		var expected := world.to_local(lv95[0], lv95[1], lv95[2])
		assert_almost_eq(got, expected, Vector3.ONE * 0.0001, "%s: to_local" % t["name"])


## Writes a copy of the fixture's generated folder with the manifest changed by
## [param change] and the chunk files changed by [param files] (tile -> PackedByteArray, or
## null to leave one out); returns the copy's manifest path.
func _write_case(change: Callable, files := {}) -> String:
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
		var tile: String = entry["tile"]
		var data: Variant = FileAccess.get_file_as_bytes(source_dir.path_join(entry["file"]))
		if files.has(tile):
			data = files[tile]
		if data != null:
			var file := FileAccess.open(dir.path_join(entry["file"]), FileAccess.WRITE)
			file.store_buffer(data)
			file.close()
	return dir.path_join("manifest.json")


func _assert_refused(path: String, why: String, needle := "") -> void:
	var world := WorldConfig.from_manifest(path)
	assert_not_null(world, "%s: the case's world block itself is valid" % why)
	var trees := TreeChunks.from_manifest(path, world)
	assert_null(trees, "%s is refused" % why)
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


func _chunk_bytes(tile: String) -> PackedByteArray:
	var source_dir := _fixture_manifest_path().get_base_dir()
	return FileAccess.get_file_as_bytes(source_dir.path_join("trees/%s.bin" % tile))


func test_no_trees_built_names_the_command() -> void:
	var path := _write_case(func(m: Dictionary) -> void: m["trees"] = null)
	_assert_refused(path, "no trees block", TREES_COMMAND)


func test_trees_built_for_another_world_are_refused() -> void:
	var path := _write_case(
		func(m: Dictionary) -> void: m["trees"]["world_sha256"] = "0".repeat(64)
	)
	_assert_refused(path, "another world's trees", TREES_COMMAND)


func test_a_damaged_chunk_file_is_refused() -> void:
	var data := _chunk_bytes("2651-1150")
	data[9] = data[9] ^ 1
	var path := _write_case(func(_m: Dictionary) -> void: pass, {"2651-1150": data})
	_assert_refused(path, "a damaged chunk file (same size)", "2651-1150")


func test_a_chunk_file_of_another_size_is_refused() -> void:
	var data := _chunk_bytes("2650-1149")
	data.resize(data.size() - 20)
	var path := _write_case(func(_m: Dictionary) -> void: pass, {"2650-1149": data})
	_assert_refused(path, "a chunk file one tree short", "2650-1149")
