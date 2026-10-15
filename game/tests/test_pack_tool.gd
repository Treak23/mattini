extends GutTest
## Pinning tests for brief M3-08: the pack tool writes a data pack whose bytes depend only on
## the names and bytes of the folder's files.
##
## Pinned decisions (docs/SPEC.md §11, the data packs; brief M3-08): game/tools/pack.gd, a
## SceneTree script that tools/export.sh runs with the editor binary, headless
## (`-s res://tools/pack.gd -- <pack path> <res:// folder>`), writes one pack with Godot's
## PCKPacker (pck_start's defaults: alignment 32, no encryption) through its static
## write_pack(pack_path: String, source_dir: String, target_dir: String) -> String, which
## returns "" once the pack is written and otherwise what is wrong. The pack holds every
## file directly in source_dir at target_dir/<name>, added in name order (String.sort, code
## points, the order of Python's sorted()), except the names that start with "." (hidden,
## as DirAccess lists files), end with ".part" (a step's unfinished write) or end with
## ".import" (Godot's import settings): the presets keep those out of mattini.pck too. A
## source_dir that does not exist, holds a folder, or holds nothing to pack is refused, and
## no pack is written. The pack is written as <pack path>.part, then renamed. PCKPacker
## writes no time and no path of the machine, so the bytes are a function of the files'
## names and bytes; they are pinned for one fixed folder by a SHA-256 that design computed a
## second way, with its own writer of Godot 4.6.3's pack format 3 (which reproduces
## PCKPacker's bytes, M3-08's design notes). The names tell code-point order from a
## case-insensitive or a natural sort ("B.bin" before "a.bin", "10.bin" before "9.bin").
##
## Does NOT prove: that tools/export.sh packs the right folders (its own check of every
## generated file in exactly one pack does, at each export).

const SCRATCH_DIR := "user://test_pack_tool"
const PACK_TOOL := "res://tools/pack.gd"
const TARGET := "res://assets/generated/terrain"
## The pack of _fixture_files() at TARGET: 864 bytes.
const EXPECTED_SHA256 := "2233eb6a7199f2931460a01f400a407a450f9c8d50ade0bf0dd7edf044bc66b9"
const PACKED_NAMES := ["10.bin", "9.bin", "B.bin", "a.bin", "village.f32", "village.json"]


func after_all() -> void:
	_remove_tree(SCRATCH_DIR)


## Removes [param dir] and everything in it, hidden files included (the fixture's .gdignore).
func _remove_tree(dir: String) -> void:
	var access := DirAccess.open(dir)
	if access == null:
		return
	access.include_hidden = true
	for sub in access.get_directories():
		_remove_tree(dir.path_join(sub))
	for file in access.get_files():
		DirAccess.remove_absolute(dir.path_join(file))
	DirAccess.remove_absolute(dir)


func _bytes(count: int, first: int, step: int) -> PackedByteArray:
	var data := PackedByteArray()
	for i in count:
		data.append((first + i * step) % 256)
	return data


## The fixture folder's files: name -> bytes. The last three are not packed.
func _fixture_files() -> Dictionary:
	return {
		"village.f32": _bytes(100, 11, 37),
		"village.json": '{"area": "fixture"}\n'.to_utf8_buffer(),
		"B.bin": _bytes(33, 1, 5),
		"a.bin": _bytes(32, 255, 255),
		"10.bin": PackedByteArray([7]),
		"9.bin": PackedByteArray(),
		"village.f32.part": "part!".to_utf8_buffer(),
		"village.jpg.import": '[remap]\n\nimporter="keep"\n'.to_utf8_buffer(),
		".gdignore": PackedByteArray(),
	}


func _write_files(dir: String, files: Dictionary) -> void:
	DirAccess.make_dir_recursive_absolute(dir)
	for name: String in files:
		var file := FileAccess.open(dir.path_join(name), FileAccess.WRITE)
		file.store_buffer(files[name])
		file.close()


## Calls the tool's write_pack; the script is loaded when called, so that without it the
## tests fail by name rather than this file failing to parse.
func _write_pack(pack_path: String, source_dir: String) -> String:
	if not ResourceLoader.exists(PACK_TOOL):
		return "there is no %s" % PACK_TOOL
	var tool: Variant = load(PACK_TOOL)
	return tool.write_pack(pack_path, source_dir, TARGET)


## The pack's directory, read as Godot 4.6.3 writes it (format 3): one [path, size, md5]
## per file, in the directory's order.
func _directory(pack_path: String) -> Array:
	var entries := []
	var file := FileAccess.open(pack_path, FileAccess.READ)
	if file == null:
		return entries
	assert_eq(file.get_32(), 0x43504447, "the GDPC magic")
	assert_eq(file.get_32(), 3, "pack format 3")
	# The directory's offset follows the file base, at byte 32.
	file.seek(32)
	file.seek(file.get_64())
	for i in file.get_32():
		var raw := file.get_buffer(file.get_32())
		while not raw.is_empty() and raw[raw.size() - 1] == 0:
			raw.resize(raw.size() - 1)
		# Past the file's offset: its size, its MD5, then its flags.
		file.seek(file.get_position() + 8)
		var size := file.get_64()
		var md5 := file.get_buffer(16).hex_encode()
		file.seek(file.get_position() + 4)
		entries.append([raw.get_string_from_utf8(), size, md5])
	return entries


func _md5(data: PackedByteArray) -> String:
	var context := HashingContext.new()
	context.start(HashingContext.HASH_MD5)
	if not data.is_empty():
		context.update(data)
	return context.finish().hex_encode()


func test_the_pack_holds_the_folders_files_in_name_order() -> void:
	var source := SCRATCH_DIR.path_join("order/terrain")
	_write_files(source, _fixture_files())
	var pack := SCRATCH_DIR.path_join("order/mattini-terrain.pck")
	assert_eq(_write_pack(pack, source), "", "the pack is written")
	var files := _fixture_files()
	var expected := []
	for name: String in PACKED_NAMES:
		var data: PackedByteArray = files[name]
		expected.append(["assets/generated/terrain/" + name, data.size(), _md5(data)])
	assert_eq(_directory(pack), expected, "each file at its path, in name order, bytes as is")


func test_the_same_files_give_the_pinned_bytes() -> void:
	var source := SCRATCH_DIR.path_join("twice/terrain")
	var first := SCRATCH_DIR.path_join("twice/first.pck")
	var second := SCRATCH_DIR.path_join("twice/second.pck")
	_write_files(source, _fixture_files())
	assert_eq(_write_pack(first, source), "", "the first pack is written")
	# The same files written again: newer times, the same names and bytes.
	_write_files(source, _fixture_files())
	assert_eq(_write_pack(second, source), "", "the second pack is written")
	assert_eq(FileAccess.get_sha256(first), EXPECTED_SHA256, "the pinned bytes")
	assert_eq(FileAccess.get_sha256(second), EXPECTED_SHA256, "the same bytes again")
	assert_false(FileAccess.file_exists(first + ".part"), "the .part was renamed")


func test_a_folder_that_holds_a_folder_is_refused() -> void:
	var source := SCRATCH_DIR.path_join("nested/terrain")
	_write_files(source, {"village.f32": _bytes(8, 0, 1)})
	DirAccess.make_dir_recursive_absolute(source.path_join("older"))
	var pack := SCRATCH_DIR.path_join("nested/mattini-terrain.pck")
	var problem := _write_pack(pack, source)
	assert_ne(problem, "", "refused")
	assert_string_contains(problem, source)
	assert_false(FileAccess.file_exists(pack), "no pack")
	assert_false(FileAccess.file_exists(pack + ".part"), "no partial pack")


func test_a_folder_with_nothing_to_pack_is_refused() -> void:
	var empty := SCRATCH_DIR.path_join("empty/terrain")
	_write_files(empty, {"village.f32.part": _bytes(8, 0, 1), ".gdignore": PackedByteArray()})
	var missing := SCRATCH_DIR.path_join("missing/terrain")
	for source in [empty, missing]:
		var pack: String = source.get_base_dir().path_join("mattini-terrain.pck")
		var problem := _write_pack(pack, source)
		assert_ne(problem, "", "%s is refused" % source)
		assert_string_contains(problem, source)
		assert_false(FileAccess.file_exists(pack), "no pack for %s" % source)
