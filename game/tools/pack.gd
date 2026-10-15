extends SceneTree
## The data-pack tool (docs/SPEC.md §11; brief M3-08): writes the files of one generated
## folder into a pack beside the executable, so that no exported file reaches GitHub's 100 MiB
## limit. Run by tools/export.sh with the editor binary:
##
##   godot --headless --path game -s res://tools/pack.gd -- \
##     <pack path> res://assets/generated/<folder>
##
## Every file directly in the folder goes into <pack path> at its own res:// path, through
## Godot's PCKPacker at its defaults (alignment 32, no encryption), in name order: the bytes
## depend only on the files' names and bytes. Names that start with "." (DirAccess does not
## list them), end with ".part" (a step's unfinished write) or end with ".import" (Godot's
## import settings) are left out; the export presets keep them out of mattini.pck too.
## Prints "pack: wrote <pack path>, <n> files of <folder>" and exits 0; on a problem prints
## "pack: <problem>" to stderr and exits 1; on a wrong command line, exits 2. A folder that
## does not exist, holds a folder or holds nothing to pack writes no pack.

const GENERATED := "res://assets/generated/"
const NOT_PACKED_SUFFIXES: Array[String] = [".part", ".import"]


## Writes the pack at [param pack_path] holding the files of [param source_dir], each at
## [param target_dir]/<name>; the pack is written as <pack path>.part, then renamed. Returns ""
## once the pack is written, else what is wrong (the pack is then not written).
static func write_pack(pack_path: String, source_dir: String, target_dir: String) -> String:
	if not DirAccess.dir_exists_absolute(source_dir):
		return "%s does not exist" % source_dir
	if not DirAccess.get_directories_at(source_dir).is_empty():
		return "%s holds a folder, which a pack of its files would leave out" % source_dir
	var names := packed_names(source_dir)
	if names.is_empty():
		return "%s holds no file to pack" % source_dir
	var part := pack_path + ".part"
	var problem := _write(part, source_dir, target_dir, names)
	if problem.is_empty():
		var renamed := DirAccess.rename_absolute(part, pack_path)
		if renamed != OK:
			problem = "cannot rename %s to %s (%s)" % [part, pack_path, error_string(renamed)]
	if not problem.is_empty():
		DirAccess.remove_absolute(part)
	return problem


## The names of the files directly in [param source_dir] that a pack holds, in code-point
## order (PackedStringArray.sort, the order of Python's sorted()).
static func packed_names(source_dir: String) -> PackedStringArray:
	var names := PackedStringArray()
	for file in DirAccess.get_files_at(source_dir):
		var packed := true
		for suffix in NOT_PACKED_SUFFIXES:
			packed = packed and not file.ends_with(suffix)
		if packed:
			names.append(file)
	names.sort()
	return names


## Writes the pack file [param path]; returns what is wrong, or "". The packer is released
## when this returns, so a failed write can be cleaned up.
static func _write(
	path: String, source_dir: String, target_dir: String, names: PackedStringArray
) -> String:
	var packer := PCKPacker.new()
	var started := packer.pck_start(path)
	if started != OK:
		return "cannot start %s (%s)" % [path, error_string(started)]
	for file in names:
		var added := packer.add_file(target_dir.path_join(file), source_dir.path_join(file))
		if added != OK:
			return (
				"cannot add %s to %s (%s)" % [source_dir.path_join(file), path, error_string(added)]
			)
	var flushed := packer.flush()
	if flushed != OK:
		return "cannot write %s (%s)" % [path, error_string(flushed)]
	return ""


func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() != 2 or not args[1].begins_with(GENERATED):
		printerr("pack: usage: -- <pack path> %s<folder>" % GENERATED)
		quit(2)
		return
	var problem := write_pack(args[0], args[1], args[1])
	if not problem.is_empty():
		printerr("pack: %s" % problem)
		quit(1)
		return
	print("pack: wrote %s, %d files of %s" % [args[0], packed_names(args[1]).size(), args[1]])
	quit(0)
