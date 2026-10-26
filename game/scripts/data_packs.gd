extends Node
## The autoload DataPacks (docs/SPEC.md §11; briefs M3-08 and v0.3.1-03): loads the data
## packs that sit beside the executable of an exported build, so the generated folders too
## large for mattini.pck (the terrain's heights, the photo) are there before the main scene
## reads the manifest, and names each expected pack that is not there. tools/export.sh
## writes them as mattini-<folder>.pck.
##
## It has no class_name: an autoload named like its class is a parse error. In an exported
## build (ReleaseBuild.is_exported()) its _init() loads every mattini-*.pck beside the
## executable and, when it finds none, prints a line saying so; then it push_errors one
## message per pack of EXPECTED_PACKS that is not there (missing_pack_errors), naming the
## pack, the folder and what the pack holds. The readers (TerrainGrid and the others) then
## refuse the missing files with their own message, which in an exported build says to
## download the release folder again (ReleaseBuild.file_hint). In the editor or a test run
## it loads and logs nothing.

const PATTERN := "mattini-*.pck"
## The data packs an exported build needs, in the order tools/export.sh writes them (its
## packed folders photo and terrain, each as mattini-<folder>.pck). Keep it on one line in
## exactly this form: from brief v0.3.1-04 on, tools/export.sh reads it by text.
const EXPECTED_PACKS := ["mattini-photo.pck", "mattini-terrain.pck"]
## What each expected pack holds, for the message that names it missing.
const PACK_CONTENTS := {
	"mattini-photo.pck": "the aerial photo",
	"mattini-terrain.pck": "the terrain's heights",
}
## The message naming a missing pack: its name, what it holds, the folder it is missing from.
const MISSING_PACK := (
	"DataPacks: the data pack %s (%s) is missing from %s:" + " download the release folder again"
)


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


## One message per pack of EXPECTED_PACKS that is not a file in [param dir], in EXPECTED_PACKS'
## order: "DataPacks: the data pack <name> (<what it holds>) is missing from <dir>: download
## the release folder again", [param dir] as given. A file under another name (a leftover
## .part, a copy) does not count as the pack. Empty when every expected pack is there. It logs
## nothing itself: the caller decides (_init push_errors each message).
static func missing_pack_errors(dir: String) -> PackedStringArray:
	var errors := PackedStringArray()
	for pack: String in EXPECTED_PACKS:
		if not FileAccess.file_exists(dir.path_join(pack)):
			errors.append(MISSING_PACK % [pack, PACK_CONTENTS[pack], dir])
	return errors


static func _version() -> String:
	return ProjectSettings.get_setting("application/config/version")


func _init() -> void:
	if not ReleaseBuild.is_exported():
		return
	var dir := OS.get_executable_path().get_base_dir()
	if load_from(dir).is_empty():
		print("mattini %s: no data pack (%s) in %s" % [_version(), PATTERN, dir])
	for message in missing_pack_errors(dir):
		push_error(message)
