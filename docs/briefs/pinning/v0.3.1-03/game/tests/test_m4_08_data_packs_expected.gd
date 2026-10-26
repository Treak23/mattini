extends GutTest
## Pinning tests for brief v0.3.1-03 (M4-08 decision 4): DataPacks names the data packs an
## exported build needs, and says which one is missing from where, and what it holds (FB-005).
##
## Pinned decisions (brief v0.3.1-03, from M4-08; docs/SPEC.md §11, the data packs):
## DataPacks.EXPECTED_PACKS is exactly ["mattini-photo.pck", "mattini-terrain.pck"], the packs
## tools/export.sh writes (from brief v0.3.1-04 on, its own check reads this constant from
## res://scripts/data_packs.gd). The static missing_pack_errors(dir) returns one message per
## expected pack that is not a file in dir, in EXPECTED_PACKS' order: "DataPacks: the data pack
## <name> (<what it holds>) is missing from <dir>: download the release folder again", where
## mattini-photo.pck holds "the aerial photo" and mattini-terrain.pck "the terrain's heights". A
## pack beside the executable under another name (a leftover .part, a renamed copy) does not
## count. In an exported build (ReleaseBuild.is_exported()) DataPacks' _init() push_errors each
## message after loading the packs; outside one it does nothing. Showing them on the error panel
## is brief v0.3.1-05's (M4-10 decision 5).
##
## Does NOT prove: that _init() push_errors them in an exported build (no test runs inside the
## release template, and none here calls _init: the release gate's export run starts the Linux
## build with mattini-photo.pck moved aside and reads the ERROR line); that the player sees them
## (brief v0.3.1-05's panel).

const DATA_PACKS := "res://scripts/data_packs.gd"
const SCRATCH_DIR := "user://test_m4_08_data_packs_expected"
const EXPECTED := ["mattini-photo.pck", "mattini-terrain.pck"]


func after_all() -> void:
	for file in DirAccess.get_files_at(SCRATCH_DIR):
		DirAccess.remove_absolute(SCRATCH_DIR.path_join(file))
	DirAccess.remove_absolute(SCRATCH_DIR)


func _script() -> Variant:
	if not ResourceLoader.exists(DATA_PACKS):
		fail_test("there is no %s" % DATA_PACKS)
		return null
	return load(DATA_PACKS)


## The files [param names] (and nothing else) in a fresh folder; returns its path.
func _folder(case: String, names: Array) -> String:
	var dir := SCRATCH_DIR.path_join(case)
	DirAccess.make_dir_recursive_absolute(dir)
	for name: String in names:
		var file := FileAccess.open(dir.path_join(name), FileAccess.WRITE)
		file.store_string("a stand-in, not a pack")
		file.close()
	return dir


func _message(pack: String, holds: String, dir: String) -> String:
	return (
		"DataPacks: the data pack %s (%s) is missing from %s: download the release folder again"
		% [pack, holds, dir]
	)


func test_the_expected_packs_are_the_photo_and_the_terrain() -> void:
	var script: Variant = _script()
	if script == null:
		return
	var constants: Dictionary = script.get_script_constant_map()
	assert_has(constants, "EXPECTED_PACKS", "DataPacks names the packs it expects")
	assert_eq(constants.get("EXPECTED_PACKS"), EXPECTED)


func test_both_missing_are_named_with_their_folder_and_contents() -> void:
	var script: Variant = _script()
	if script == null:
		return
	var dir := _folder("none", [])
	var errors: PackedStringArray = script.missing_pack_errors(dir)
	assert_eq(
		errors,
		PackedStringArray(
			[
				_message("mattini-photo.pck", "the aerial photo", dir),
				_message("mattini-terrain.pck", "the terrain's heights", dir),
			]
		)
	)


func test_one_missing_is_named_alone() -> void:
	var script: Variant = _script()
	if script == null:
		return
	var dir := _folder("terrain-only", ["mattini-terrain.pck", "mattini.pck"])
	var errors: PackedStringArray = script.missing_pack_errors(dir)
	assert_eq(errors, PackedStringArray([_message("mattini-photo.pck", "the aerial photo", dir)]))


func test_all_there_gives_nothing() -> void:
	var script: Variant = _script()
	if script == null:
		return
	var dir := _folder("both", EXPECTED)
	assert_eq(script.missing_pack_errors(dir), PackedStringArray())


func test_a_leftover_or_another_name_does_not_count() -> void:
	var script: Variant = _script()
	if script == null:
		return
	var dir := _folder("lookalikes", ["mattini-photo.pck.part", "old-mattini-terrain.pck"])
	var errors: PackedStringArray = script.missing_pack_errors(dir)
	assert_eq(errors.size(), 2, "both are still missing: %s" % [errors])
