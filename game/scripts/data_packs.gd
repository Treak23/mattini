extends Node
## The autoload DataPacks (docs/SPEC.md §11; brief M3-08): loads the data packs that sit
## beside the executable of an exported build, so the generated folders too large for
## mattini.pck (the terrain's heights, the photo) are there before the main scene reads the
## manifest. tools/export.sh writes them as mattini-<folder>.pck.
##
## It has no class_name: an autoload named like its class is a parse error. In an exported
## build (OS.has_feature("template")) its _init() loads every mattini-*.pck beside the
## executable and, when it finds none, prints a line saying so; the readers (TerrainGrid and
## the others) then refuse the missing files with their own message. In the editor or a test
## run it loads nothing.

const PATTERN := "mattini-*.pck"


## Loads every file of [param dir] whose name matches mattini-*.pck (not mattini.pck, the
## main pack, and not a leftover .part), in name order, each with load_resource_pack(path,
## false), so a pack never replaces a file loaded before it: mattini.pck's files win, then
## the first pack by name. Prints "mattini <version>: data pack <name> loaded" per pack and
## returns the names loaded. A pack that does not load is refused with a push_error naming
## its path, and the packs after it still load. A folder that does not exist loads nothing
## and logs nothing.
static func load_from(dir: String) -> PackedStringArray:
	var loaded := PackedStringArray()
	if not DirAccess.dir_exists_absolute(dir):
		return loaded
	var names := PackedStringArray()
	for file in DirAccess.get_files_at(dir):
		if file.match(PATTERN):
			names.append(file)
	names.sort()
	for file in names:
		var path := dir.path_join(file)
		if ProjectSettings.load_resource_pack(path, false):
			print("mattini %s: data pack %s loaded" % [_version(), file])
			loaded.append(file)
		else:
			push_error("DataPacks: cannot load the data pack %s" % path)
	return loaded


static func _version() -> String:
	return ProjectSettings.get_setting("application/config/version")


func _init() -> void:
	if not OS.has_feature("template"):
		return
	var dir := OS.get_executable_path().get_base_dir()
	if load_from(dir).is_empty():
		print("mattini %s: no data pack (%s) in %s" % [_version(), PATTERN, dir])
