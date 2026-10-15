extends GutTest
## Pinning tests for brief M3-12: BuildingRoofs reads the manifest's roofs block against the
## BuildingChunks read from the same manifest, and refuses a block that does not fit them.
##
## Pinned decisions (m3-design.md §3 and §9): BuildingRoofs.from_manifest(path, world,
## chunks) returns the block's chunks in BuildingChunks' order, each {tile, buildings: [{uuid,
## triangles, vertices, roof}]}, roof a Color (Color.html of the block's "rrggbb") or null, or
## returns null after one push_error naming the manifest (Hard Rule 2). It refuses: no roofs
## block, naming python -m mattini roofs; a block built for another world config; chunks that
## are not BuildingChunks' chunks in order; a chunk whose buildings' triangles or vertices do
## not add up to the chunk file's, naming the tile. Refinement R1 of design's notes: a
## building whose triangles index vertices outside its own range is refused too, so counts
## moved between two buildings with the sums kept (which would colour another building's
## triangles) are caught. The shared fixture (tests/shared/roofs_fixture/generated/, its
## buildings in tests/shared/roofs_vectors.json) was computed by design two independent ways.
##
## Does NOT prove: that the colours are drawn (test_building_roof_colours.gd); that the real
## village's block reads the same way (the main scene's run on the owner's data does).

const SCRATCH_DIR := "user://test_building_roofs"
const ROOFS_COMMAND := "python -m mattini roofs"

var _cases := 0


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


func _fixture_manifest_path() -> String:
	return _repo_file("tests/shared/roofs_fixture/generated/manifest.json")


func _parse(path: String) -> Dictionary:
	var json := JSON.new()
	assert_eq(json.parse(FileAccess.get_file_as_string(path)), OK, "%s parses" % path)
	return json.data if typeof(json.data) == TYPE_DICTIONARY else {}


func _vectors() -> Dictionary:
	return _parse(_repo_file("tests/shared/roofs_vectors.json"))


func after_all() -> void:
	_remove_tree(SCRATCH_DIR)


func _remove_tree(dir: String) -> void:
	for sub in DirAccess.get_directories_at(dir):
		_remove_tree(dir.path_join(sub))
	for file in DirAccess.get_files_at(dir):
		DirAccess.remove_absolute(dir.path_join(file))
	DirAccess.remove_absolute(dir)


func test_the_fixture_roofs_are_read_as_designed() -> void:
	var path := _fixture_manifest_path()
	var world := WorldConfig.from_manifest(path)
	var chunks := BuildingChunks.from_manifest(path, world)
	assert_not_null(chunks, "the fixture's buildings are read")
	if chunks == null:
		return
	var roofs := BuildingRoofs.from_manifest(path, world, chunks)
	assert_not_null(roofs, "the fixture's roof colours are read")
	if roofs == null:
		return
	assert_eq(roofs.chunks.size(), chunks.chunks.size(), "one entry per chunk")
	var expected: Array = _vectors()["buildings"]
	var at := 0
	for i in roofs.chunks.size():
		var entry: Dictionary = roofs.chunks[i]
		assert_eq(entry["tile"], chunks.chunks[i]["tile"], "BuildingChunks' order")
		for building: Dictionary in entry["buildings"]:
			var want: Dictionary = expected[at]
			at += 1
			assert_eq(building["uuid"], want["uuid"], "chunk order")
			assert_eq(building["triangles"], int(want["triangles"]), want["uuid"])
			assert_eq(building["vertices"], int(want["vertices"]), want["uuid"])
			if want["roof"] == null:
				assert_null(building["roof"], "%s: no roof colour" % want["uuid"])
			else:
				assert_eq(
					building["roof"], Color.html(want["roof"]), "%s: its colour" % want["uuid"]
				)
	assert_eq(at, expected.size(), "every building, once")


## Writes a copy of the fixture's generated folder with its manifest changed by
## [param change] (a Callable taking the manifest Dictionary); returns the manifest's path.
func _write_case(change: Callable) -> String:
	_cases += 1
	var dir := SCRATCH_DIR.path_join("case_%d" % _cases)
	DirAccess.make_dir_recursive_absolute(dir.path_join("buildings"))
	var manifest := _parse(_fixture_manifest_path())
	var source_dir := _fixture_manifest_path().get_base_dir()
	for entry: Dictionary in manifest["buildings"]["chunks"]:
		var file := FileAccess.open(dir.path_join(entry["file"]), FileAccess.WRITE)
		file.store_buffer(FileAccess.get_file_as_bytes(source_dir.path_join(entry["file"])))
		file.close()
	change.call(manifest)
	var out := FileAccess.open(dir.path_join("manifest.json"), FileAccess.WRITE)
	out.store_string(JSON.stringify(manifest, "  ", true, true))
	out.close()
	return dir.path_join("manifest.json")


## The case's buildings are read (only the roofs block was changed), its roofs refused with
## one push_error naming the manifest and, when given, [param needle].
func _assert_refused(path: String, why: String, needle := "") -> void:
	var world := WorldConfig.from_manifest(path)
	var chunks := BuildingChunks.from_manifest(path, world)
	assert_not_null(chunks, "%s: the case's buildings themselves are read" % why)
	var roofs := BuildingRoofs.from_manifest(path, world, chunks)
	assert_null(roofs, "%s is refused" % why)
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
	assert_true(found, "%s: one push_error names %s and %s" % [why, path, needle])


## The roofs entry of the chunk [param tile] in a manifest Dictionary.
func _chunk(manifest: Dictionary, tile: String) -> Dictionary:
	for entry: Dictionary in manifest["roofs"]["chunks"]:
		if entry["tile"] == tile:
			return entry
	return {}


func test_no_roofs_block_names_the_command() -> void:
	var path := _write_case(func(m: Dictionary) -> void: m["roofs"] = null)
	_assert_refused(path, "no roofs block", ROOFS_COMMAND)


func test_roofs_built_for_another_world_are_refused() -> void:
	var path := _write_case(
		func(m: Dictionary) -> void: m["roofs"]["world_sha256"] = "0".repeat(64)
	)
	_assert_refused(path, "another world's roof colours", ROOFS_COMMAND)


func test_chunks_that_are_not_the_buildings_chunks_are_refused() -> void:
	var path := _write_case(func(m: Dictionary) -> void: m["roofs"]["chunks"].reverse())
	_assert_refused(path, "the chunks in another order")


func test_a_chunk_whose_triangles_do_not_add_up_is_refused() -> void:
	var change := func(m: Dictionary) -> void:
		var b: Dictionary = _chunk(m, "2650-1150")["buildings"][1]
		b["triangles"] = b["triangles"] + 1
	_assert_refused(_write_case(change), "one triangle too many in 2650-1150", "2650-1150")


func test_a_chunk_whose_vertices_do_not_add_up_is_refused() -> void:
	var change := func(m: Dictionary) -> void:
		var b: Dictionary = _chunk(m, "2651-1150")["buildings"][1]
		b["vertices"] = b["vertices"] - 1
	_assert_refused(_write_case(change), "one vertex too few in 2651-1150", "2651-1150")


func test_counts_moved_between_two_buildings_are_refused() -> void:
	# Refinement R1: the sums still add up, but the first building would take the second's
	# first triangle, whose indices lie past the first building's vertices.
	var change := func(m: Dictionary) -> void:
		var list: Array = _chunk(m, "2651-1149")["buildings"]
		list[0]["triangles"] = list[0]["triangles"] + 1
		list[1]["triangles"] = list[1]["triangles"] - 1
	_assert_refused(_write_case(change), "a triangle moved between two buildings", "2651-1149")
