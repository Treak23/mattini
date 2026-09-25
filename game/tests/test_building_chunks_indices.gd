extends GutTest
## BuildingChunks beyond the pinned tests (brief M2-05): an index of 2^31 or more is refused.
##
## The chunk files hold uint32 indices, which the reader takes as int32: one of 2^31 or more
## reads negative, and GDScript reads a packed array at a negative index from its end, so an
## index 0xFFFFFFFF, taken as -1, would draw a triangle to the chunk's last vertex: plausible,
## and wrong (Hard Rule 2). The pinned test_building_chunks.gd refuses an index just past the
## vertices; this one the other end, on a copy of the shared buildings fixture whose entry
## matches the changed file (size and SHA-256), so only the index check can refuse it.
##
## Does NOT prove: that the pipeline cannot write such an index (its own tests' subject).

const SCRATCH_DIR := "user://test_building_chunks_indices"
const FIXTURE := "tests/shared/buildings_fixture/generated/manifest.json"
const TILE := "2651-1150"


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


func after_all() -> void:
	for folder in [SCRATCH_DIR.path_join("buildings"), SCRATCH_DIR]:
		for file in DirAccess.get_files_at(folder):
			DirAccess.remove_absolute(folder.path_join(file))
		DirAccess.remove_absolute(folder)


## A copy of the fixture's generated folder whose TILE chunk has its last index set to
## [param index] (as uint32), its entry's SHA-256 updated; returns the manifest's path.
func _write_case(index: int) -> String:
	var source := _repo_file(FIXTURE)
	var json := JSON.new()
	json.parse(FileAccess.get_file_as_string(source))
	var manifest: Dictionary = json.data
	DirAccess.make_dir_recursive_absolute(SCRATCH_DIR.path_join("buildings"))
	for entry: Dictionary in manifest["buildings"]["chunks"]:
		var data := FileAccess.get_file_as_bytes(source.get_base_dir().path_join(entry["file"]))
		if entry["tile"] == TILE:
			data.encode_u32(data.size() - 4, index)
			var context := HashingContext.new()
			context.start(HashingContext.HASH_SHA256)
			context.update(data)
			entry["sha256"] = context.finish().hex_encode()
		var file := FileAccess.open(SCRATCH_DIR.path_join(entry["file"]), FileAccess.WRITE)
		file.store_buffer(data)
		file.close()
	var path := SCRATCH_DIR.path_join("manifest.json")
	var out := FileAccess.open(path, FileAccess.WRITE)
	out.store_string(JSON.stringify(manifest, "  ", true, true))
	out.close()
	return path


func test_an_index_of_2_to_the_31_or_more_is_refused() -> void:
	for index: int in [0xFFFFFFFF, 0x80000000]:
		var path := _write_case(index)
		var chunks := BuildingChunks.from_manifest(path, WorldConfig.from_manifest(path))
		assert_null(chunks, "the index %d is refused" % index)
		# One push_error, naming the manifest, the chunk and the index as the file holds it.
		var found := 0
		for error in get_errors():
			if (
				not error.handled
				and error.is_push_error()
				and error.contains_text(path)
				and error.contains_text("chunk %s: triangle " % TILE)
				and error.contains_text("has the index %d," % index)
			):
				error.handled = true
				found += 1
		assert_eq(found, 1, "one push_error names the chunk and the index %d" % index)


func test_the_same_copy_with_a_valid_index_is_read() -> void:
	# The case is sound but for the index: with the file's own last index it is read.
	var original := FileAccess.get_file_as_bytes(
		_repo_file(FIXTURE).get_base_dir().path_join("buildings/%s.bin" % TILE)
	)
	var path := _write_case(original.decode_u32(original.size() - 4))
	var chunks := BuildingChunks.from_manifest(path, WorldConfig.from_manifest(path))
	assert_not_null(chunks, "a valid index is read")
