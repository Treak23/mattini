extends GutTest
## Pinning tests for brief M2-05: BuildingChunks reads the manifest's buildings block and
## its chunk files, checked, and never converts a coordinate itself.
##
## Pinned decisions (docs/SPEC.md §8, the buildings; brief M2-05): the shared buildings
## fixture (tests/shared/buildings_fixture/generated/, its vectors in
## tests/shared/buildings_vectors.json, computed by design two independent ways) is read as
## the pipeline writes it: three chunks in tile order, each its vertices as little-endian
## float32 local x, y, z and its triangles as little-endian uint32 indices. The seam: every
## named vertex lies where WorldConfig.to_local puts its LV95 point (Hard Rule 4). Every
## problem is refused with one push_error naming the manifest and a null result, never a
## plausible set of buildings (Hard Rule 2).
##
## Does NOT prove: that the buildings render or look right (no GPU); that the real village's
## chunks read the same way (the main scene's headless run does).

const SCRATCH_DIR := "user://test_building_chunks"
const BUILDINGS_COMMAND := "python -m mattini buildings"

var _cases := 0


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


func _fixture_manifest_path() -> String:
	return _repo_file("tests/shared/buildings_fixture/generated/manifest.json")


func _parse(path: String) -> Dictionary:
	var json := JSON.new()
	assert_eq(json.parse(FileAccess.get_file_as_string(path)), OK, "%s parses" % path)
	return json.data if typeof(json.data) == TYPE_DICTIONARY else {}


func _vectors() -> Dictionary:
	return _parse(_repo_file("tests/shared/buildings_vectors.json"))


func _read_fixture() -> BuildingChunks:
	var world := WorldConfig.from_manifest(_fixture_manifest_path())
	return BuildingChunks.from_manifest(_fixture_manifest_path(), world)


func after_all() -> void:
	_remove_tree(SCRATCH_DIR)


func _remove_tree(dir: String) -> void:
	for sub in DirAccess.get_directories_at(dir):
		_remove_tree(dir.path_join(sub))
	for file in DirAccess.get_files_at(dir):
		DirAccess.remove_absolute(dir.path_join(file))
	DirAccess.remove_absolute(dir)


func test_the_fixture_chunks_are_read_as_designed() -> void:
	var chunks := _read_fixture()
	assert_not_null(chunks, "the fixture's buildings are read")
	if chunks == null:
		return
	var block: Dictionary = _parse(_fixture_manifest_path())["buildings"]
	assert_eq(chunks.area, "fixture")
	assert_eq(chunks.dataset, "swissbuildings3d")
	assert_eq(chunks.edition, "2020")
	assert_eq(chunks.attribution, "© swisstopo")
	assert_eq(chunks.chunks.size(), 3, "three chunks, the fourth tile has no building")
	var expected_chunks: Array = _vectors()["expected"]["chunks"]
	for i in chunks.chunks.size():
		var chunk: Dictionary = chunks.chunks[i]
		var entry: Dictionary = block["chunks"][i]
		assert_eq(chunk["tile"], entry["tile"], "chunks in the block's order")
		assert_eq(chunk["tile"], expected_chunks[i]["tile"])
		assert_eq(chunk["buildings"], int(entry["buildings"]))
		assert_eq(chunk["buildings"], expected_chunks[i]["buildings"].size())
		var positions: PackedVector3Array = chunk["positions"]
		var indices: PackedInt32Array = chunk["indices"]
		assert_eq(positions.size(), int(entry["vertices"]), "%s: vertices" % entry["tile"])
		assert_eq(indices.size(), 3 * int(entry["triangles"]), "%s: indices" % entry["tile"])
		for index in indices:
			if index < 0 or index >= positions.size():
				fail_test("%s: index %d out of range" % [entry["tile"], index])
				break


func test_every_named_vertex_lies_where_the_world_config_puts_it() -> void:
	var chunks := _read_fixture()
	var world := WorldConfig.from_manifest(_fixture_manifest_path())
	assert_not_null(chunks, "the fixture's buildings are read")
	if chunks == null:
		return
	var by_tile := {}
	for chunk: Dictionary in chunks.chunks:
		by_tile[chunk["tile"]] = chunk
	var vertices: Array = _vectors()["vertices"]
	assert_gt(vertices.size(), 7, "the vectors name vertices in every chunk")
	for v: Dictionary in vertices:
		var positions: PackedVector3Array = by_tile[v["tile"]]["positions"]
		var got := positions[int(v["index"])]
		var local: Array = v["local"]
		# The file's own float32 values, exactly.
		assert_eq(got, Vector3(local[0], local[1], local[2]), "%s: as written" % v["name"])
		# The seam: the pipeline's placement is the world config's (Hard Rule 4).
		var lv95: Array = v["lv95"]
		var expected := world.to_local(lv95[0], lv95[1], lv95[2])
		assert_almost_eq(got, expected, Vector3.ONE * 0.0001, "%s: to_local" % v["name"])


## Writes a copy of the fixture's generated folder with the manifest changed by
## [param change] (a Callable taking the manifest Dictionary) and the chunk files changed
## by [param files] (tile -> PackedByteArray, or null to leave one out); returns the path.
func _write_case(change: Callable, files := {}) -> String:
	_cases += 1
	var dir := SCRATCH_DIR.path_join("case_%d" % _cases)
	DirAccess.make_dir_recursive_absolute(dir.path_join("buildings"))
	var manifest := _parse(_fixture_manifest_path())
	change.call(manifest)
	var out := FileAccess.open(dir.path_join("manifest.json"), FileAccess.WRITE)
	out.store_string(JSON.stringify(manifest, "  ", true, true))
	out.close()
	var source_dir := _fixture_manifest_path().get_base_dir()
	for entry: Dictionary in _parse(_fixture_manifest_path())["buildings"]["chunks"]:
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
	var chunks := BuildingChunks.from_manifest(path, world)
	assert_null(chunks, "%s is refused" % why)
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


func _set(key: String, value: Variant) -> Callable:
	return func(m: Dictionary) -> void: m["buildings"][key] = value


func test_no_buildings_built_names_the_commands() -> void:
	var path := _write_case(func(m: Dictionary) -> void: m["buildings"] = null)
	_assert_refused(path, "no buildings block", BUILDINGS_COMMAND)


func test_buildings_built_for_another_world_are_refused() -> void:
	var path := _write_case(_set("world_sha256", "0".repeat(64)))
	_assert_refused(path, "another world's buildings", BUILDINGS_COMMAND)


func test_another_format_is_refused() -> void:
	_assert_refused(_write_case(_set("format", "glb")), "another format", "format")


func test_a_missing_chunk_file_is_refused() -> void:
	var path := _write_case(func(_m: Dictionary) -> void: pass, {"2650-1150": null})
	_assert_refused(path, "a missing chunk file", "2650-1150")


func test_a_damaged_chunk_file_is_refused() -> void:
	var source_dir := _fixture_manifest_path().get_base_dir()
	var data := FileAccess.get_file_as_bytes(source_dir.path_join("buildings/2651-1150.bin"))
	data[5] = data[5] ^ 1
	var path := _write_case(func(_m: Dictionary) -> void: pass, {"2651-1150": data})
	_assert_refused(path, "a damaged chunk file (same size)", "2651-1150")


func test_a_chunk_file_of_the_wrong_size_is_refused() -> void:
	var source_dir := _fixture_manifest_path().get_base_dir()
	var data := FileAccess.get_file_as_bytes(source_dir.path_join("buildings/2650-1149.bin"))
	data.resize(data.size() - 12)
	var path := _write_case(func(_m: Dictionary) -> void: pass, {"2650-1149": data})
	_assert_refused(path, "a chunk file cut short", "2650-1149")


func test_an_index_out_of_range_is_refused() -> void:
	# A file that matches its own entry (size and SHA-256) but whose last index points past
	# the chunk's vertices: only the index check can refuse it.
	var source_dir := _fixture_manifest_path().get_base_dir()
	var data := FileAccess.get_file_as_bytes(source_dir.path_join("buildings/2651-1150.bin"))
	data.encode_u32(data.size() - 4, 17)  # the chunk has 17 vertices: 0 .. 16
	var sha := _sha256(data)
	var change := func(m: Dictionary) -> void:
		for entry: Dictionary in m["buildings"]["chunks"]:
			if entry["tile"] == "2651-1150":
				entry["sha256"] = sha
	var path := _write_case(change, {"2651-1150": data})
	_assert_refused(path, "an index out of range", "2651-1150")


func test_a_file_outside_the_manifest_s_folder_is_refused() -> void:
	var change := func(m: Dictionary) -> void:
		m["buildings"]["chunks"][0]["file"] = "../buildings/2650-1149.bin"
	_assert_refused(_write_case(change), "a path leaving the folder", "file")


func _sha256(data: PackedByteArray) -> String:
	var context := HashingContext.new()
	context.start(HashingContext.HASH_SHA256)
	context.update(data)
	return context.finish().hex_encode()
