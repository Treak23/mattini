extends GutTest
## Pinning tests for brief M3-08: the autoload DataPacks loads the data packs beside the
## executable.
##
## Pinned decisions (docs/SPEC.md §11, the data packs; brief M3-08; the owner chose packs,
## 2026-10-14): tools/export.sh writes the large generated folders into data packs named
## mattini-<folder>.pck beside each executable. The autoload DataPacks
## (res://scripts/data_packs.gd, a singleton) loads them in its _init() in an exported build
## (OS.has_feature("template")), before the main scene reads the manifest, through its
## static load_from(dir: String) -> PackedStringArray, which returns the names it loaded:
## every file in dir whose name matches mattini-*.pck (never mattini.pck itself, the main
## pack, nor a leftover .part), in name order (String.sort, code points), each with
## ProjectSettings.load_resource_pack(path, false), so a pack never replaces a file loaded
## before it: mattini.pck's files win, then the first pack by name. Each pack loaded prints
## one line, "mattini <version>: data pack <name> loaded", which tools/export.sh's step 6
## requires. A pack that does not load is refused with a push_error naming its path, and the
## packs after it still load. A folder that does not exist loads nothing and logs nothing.
##
## Every pack here is written by PCKPacker in this test, into user://, and holds files under
## res://test_data_packs/, a folder no project file uses: a pack loaded in a test stays
## loaded for the rest of the run (Godot cannot unload one), so each test uses its own
## paths.
##
## Does NOT prove: that an exported build finds the packs beside its executable (the
## release template ignores --script; tools/export.sh's step 6 starts the Linux build with
## its packs, the owner's PC the Windows build).

const SCRATCH_DIR := "user://test_data_packs"
const DATA_PACKS := "res://scripts/data_packs.gd"
const PACKED := "res://test_data_packs"


## Collects every line printed or logged while it listens.
class LineCatcher:
	extends Logger

	var _lines := PackedStringArray()
	var _mutex := Mutex.new()

	func _log_message(message: String, _error: bool) -> void:
		_mutex.lock()
		_lines.append(message.strip_edges(false, true))
		_mutex.unlock()

	func lines() -> PackedStringArray:
		_mutex.lock()
		var copy := _lines.duplicate()
		_mutex.unlock()
		return copy


func after_all() -> void:
	_remove_tree(SCRATCH_DIR)


func _remove_tree(dir: String) -> void:
	for sub in DirAccess.get_directories_at(dir):
		_remove_tree(dir.path_join(sub))
	for file in DirAccess.get_files_at(dir):
		DirAccess.remove_absolute(dir.path_join(file))
	DirAccess.remove_absolute(dir)


func _version() -> String:
	return ProjectSettings.get_setting("application/config/version")


## Writes a pack at [param path] holding [param files] (res:// path -> PackedByteArray),
## through a source file per entry in [param dir]/sources.
func _write_pack(dir: String, pack_name: String, files: Dictionary) -> void:
	var sources := dir.path_join("sources")
	DirAccess.make_dir_recursive_absolute(sources)
	var packer := PCKPacker.new()
	assert_eq(packer.pck_start(dir.path_join(pack_name)), OK, "%s starts" % pack_name)
	var index := 0
	for target: String in files:
		var source := sources.path_join("%s-%d.bin" % [pack_name, index])
		index += 1
		var file := FileAccess.open(source, FileAccess.WRITE)
		file.store_buffer(files[target])
		file.close()
		assert_eq(packer.add_file(target, source), OK, "%s takes %s" % [pack_name, target])
	assert_eq(packer.flush(), OK, "%s is written" % pack_name)


func _text(value: String) -> PackedByteArray:
	return value.to_utf8_buffer()


## Calls DataPacks.load_from([param dir]) while a LineCatcher listens; returns [the names it
## returned, the lines logged meanwhile]. The script is loaded when called, so that without
## it the tests fail by name rather than this file failing to parse.
func _load_from(dir: String) -> Array:
	if not ResourceLoader.exists(DATA_PACKS):
		fail_test("there is no %s" % DATA_PACKS)
		return [PackedStringArray(), PackedStringArray()]
	var script: Variant = load(DATA_PACKS)
	var catcher := LineCatcher.new()
	OS.add_logger(catcher)
	var loaded: PackedStringArray = script.load_from(dir)
	OS.remove_logger(catcher)
	return [loaded, catcher.lines()]


func test_the_autoload_is_data_packs() -> void:
	assert_eq(ProjectSettings.get_setting("autoload/DataPacks"), "*" + DATA_PACKS)
	var node := get_tree().root.get_node_or_null("DataPacks")
	assert_not_null(node, "the autoload is in the tree")
	if node != null:
		assert_eq(node.get_script().resource_path, DATA_PACKS)


func test_the_packs_load_in_name_order_and_their_files_read_back() -> void:
	var dir := SCRATCH_DIR.path_join("beside")
	var root := PACKED.path_join("order")
	var all_bytes := PackedByteArray()
	for value in 256:
		all_bytes.append(value)
	# Written in another order than their names', each holding the same shared.txt.
	_write_pack(
		dir,
		"mattini-c.pck",
		{root.path_join("shared.txt"): _text("c"), root.path_join("c.txt"): _text("only c")}
	)
	_write_pack(
		dir,
		"mattini-a.pck",
		{
			root.path_join("shared.txt"): _text("a"),
			root.path_join("a.txt"): _text("only a"),
			root.path_join("sub/bytes.bin"): all_bytes,
		}
	)
	_write_pack(
		dir,
		"mattini-b.pck",
		{root.path_join("shared.txt"): _text("b"), root.path_join("b.txt"): _text("only b")}
	)
	# Beside them: the main pack's own name, other packs, a leftover of an unfinished write.
	_write_pack(dir, "mattini.pck", {root.path_join("main.txt"): _text("main")})
	_write_pack(dir, "other.pck", {root.path_join("other.txt"): _text("other")})
	_write_pack(dir, "mattini-d.pck.part", {root.path_join("d.txt"): _text("d")})
	var result := _load_from(dir)
	var names := PackedStringArray(["mattini-a.pck", "mattini-b.pck", "mattini-c.pck"])
	assert_eq(result[0], names, "the packs loaded, in name order")
	var lines := PackedStringArray()
	for name in names:
		lines.append("mattini %s: data pack %s loaded" % [_version(), name])
	assert_eq(result[1], lines, "one line per pack loaded, in the order loaded")
	assert_eq(
		FileAccess.get_file_as_string(root.path_join("shared.txt")),
		"a",
		"a pack never replaces a file loaded before it: the first by name wins"
	)
	for letter in ["a", "b", "c"]:
		assert_eq(
			FileAccess.get_file_as_string(root.path_join("%s.txt" % letter)), "only " + letter
		)
	assert_eq(FileAccess.get_file_as_bytes(root.path_join("sub/bytes.bin")), all_bytes)
	for absent in ["main.txt", "other.txt", "d.txt"]:
		assert_false(FileAccess.file_exists(root.path_join(absent)), "%s is not loaded" % absent)


func test_a_folder_that_does_not_exist_loads_nothing_silently() -> void:
	var result := _load_from(SCRATCH_DIR.path_join("no such folder"))
	assert_eq(result[0], PackedStringArray(), "nothing loaded")
	assert_eq(result[1], PackedStringArray(), "nothing logged")
	assert_eq(get_errors().size(), 0, "no error")


func test_a_broken_pack_is_refused_and_the_next_still_loads() -> void:
	var dir := SCRATCH_DIR.path_join("broken")
	var root := PACKED.path_join("broken")
	DirAccess.make_dir_recursive_absolute(dir)
	var broken := FileAccess.open(dir.path_join("mattini-a.pck"), FileAccess.WRITE)
	broken.store_string("not a pack, but long enough to be read as one")
	broken.close()
	_write_pack(dir, "mattini-b.pck", {root.path_join("b.txt"): _text("only b")})
	var result := _load_from(dir)
	assert_eq(result[0], PackedStringArray(["mattini-b.pck"]), "only the good pack loaded")
	assert_push_error("DataPacks: cannot load the data pack %s" % dir.path_join("mattini-a.pck"))
	assert_eq(FileAccess.get_file_as_string(root.path_join("b.txt")), "only b")
