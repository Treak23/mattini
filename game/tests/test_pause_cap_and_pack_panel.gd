extends GutTest
## Pinning tests for brief v0.3.1-05 (from M4-10 decisions 2 and 5; FB-007's and FB-005's
## second halves): the pause screen's frame cap, and the missing data packs on the error panel.
##
## Pinned decisions (SPEC §13 row 45; briefs v0.3.1-02, v0.3.1-03 and v0.3.1-05): while the
## pause screen is open Engine.max_fps is 15. Closing it (toggle_pause, the pause action or the
## Resume button) gives back the project's cap, read from application/run/max_fps when it
## closes (60 since brief v0.3.1-02), and so does the main scene leaving the tree while paused;
## a player's --max-fps command-line cap is therefore replaced by the project's once the pause
## screen has closed (M4-10's choice). In an exported build (ReleaseBuild.is_exported()), before
## the manifest is read, main asks DataPacks.missing_pack_errors(the executable's folder)
## through a preload of res://scripts/data_packs.gd (the autoload has no class_name). The
## messages follow the error panel's first line after a blank line, before the refusals; with
## no refusal the first line is "mattini cannot find every data pack." and the fix is the
## release folder; a refused manifest lists them too, and a missing terrain pack shows the
## packs and then TerrainGrid's refusal, which ends in the release hint (brief v0.3.1-03).
## Outside an export no pack is asked. The panel's exported flag is ReleaseBuild's, not the
## OS's. error_text takes the messages as a fourth argument (default none). Main logs nothing
## more: DataPacks logged them at start.
##
## Does NOT prove: that fewer frames are drawn (these tests read Engine.max_fps; that the engine
## then sleeps was measured once for brief v0.3.1-05, not here) or that the cap lowers the
## owner's GPU load, heat or fan noise (no GPU here; the scene behind the pause screen still
## draws, at most 15 times a second); that an exported build shows the panel (the release
## template ignores --script, so these tests reach the panel only through ReleaseBuild's test
## seam; the release gate's run of the export reads DataPacks' log line, and the panel stays
## the owner's to see); how the panel looks or wraps on the owner's screen; the Windows build.

const CompleteWorld := preload("res://tests/complete_world.gd")
const MAIN_SCENE := "res://main.tscn"
const MAIN_SCRIPT := "res://scripts/main.gd"
## The autoload DataPacks' script (it has no class_name; --check-only knows no autoload).
const DATA_PACKS := preload("res://scripts/data_packs.gd")
const SCRATCH_DIR := "user://test_pause_cap_and_pack_panel"
const DEPRECATION := "instance_reset_physics_interpolation() is deprecated"
const RUN := "uv run --project pipeline python -m mattini "
const EXPORTED := (
	"keep mattini.pck and the data packs mattini-*.pck beside the executable:"
	+ " download the release folder again and keep its files together."
)
## The end of a reader's file message in an exported build (brief v0.3.1-03).
const RELEASE_HINT := "; it ships in the release's packs: download the release folder again"
## Not the project's 60: a cap the pause screen can give back only by reading the setting.
const OTHER_CAP := 45

var _cases := 0
var _complete := ""
var _project_cap := 0


func before_all() -> void:
	_complete = CompleteWorld.write(SCRATCH_DIR.path_join("complete"))
	_project_cap = ProjectSettings.get_setting("application/run/max_fps")


func after_all() -> void:
	ReleaseBuild.set_exported_for_tests(null)
	CompleteWorld.remove_tree(SCRATCH_DIR)


func after_each() -> void:
	ReleaseBuild.set_exported_for_tests(null)
	ProjectSettings.set_setting("application/run/max_fps", _project_cap)
	Engine.max_fps = ProjectSettings.get_setting("application/run/max_fps")


func _write(change := Callable()) -> String:
	_cases += 1
	return CompleteWorld.write(SCRATCH_DIR.path_join("case_%d" % _cases), change)


## The complete world without its terrain's heights file, as an exported build without
## mattini-terrain.pck finds it; returns its manifest's path.
func _write_without_heights() -> String:
	var path := _write()
	DirAccess.remove_absolute(path.get_base_dir().path_join("terrain/fixture.f32"))
	return path


func _write_text(text: String) -> String:
	_cases += 1
	DirAccess.make_dir_recursive_absolute(SCRATCH_DIR)
	var path := SCRATCH_DIR.path_join("manifest_%d.json" % _cases)
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string(text)
	file.close()
	return path


func _main_with(manifest_path: String) -> Node3D:
	var main: Node3D = load(MAIN_SCENE).instantiate()
	main.manifest_path = manifest_path
	add_child_autofree(main)
	for error in get_errors():
		if error.contains_text(DEPRECATION):
			error.handled = true
	return main


func _main() -> Node3D:
	return _main_with(_complete)


func _message(main: Node3D) -> String:
	assert_true(main.get_node("UI/ErrorPanel").visible, "the error panel is open")
	return main.get_node("UI/ErrorPanel/Message").text


func _press(action: StringName) -> void:
	for pressed in [true, false]:
		var event := InputEventAction.new()
		event.action = action
		event.pressed = pressed
		get_viewport().push_input(event)


## The messages DataPacks gives for this test's executable, which has no data pack beside it.
func _packs() -> PackedStringArray:
	return DATA_PACKS.missing_pack_errors(OS.get_executable_path().get_base_dir())


func test_the_pause_screen_caps_the_frames_at_15_and_gives_the_cap_back() -> void:
	var main := _main()
	var menu: Control = main.get_node("UI/PauseMenu")
	assert_eq(Engine.max_fps, 60, "the project's cap before")
	main.toggle_pause()
	assert_eq(Engine.max_fps, 15, "15 fps while the pause screen is open")
	main.toggle_pause()
	assert_eq(Engine.max_fps, 60, "closing it gives back the project's cap")
	_press(&"pause")
	assert_true(menu.visible, "the pause action opens the pause screen")
	assert_eq(Engine.max_fps, 15, "15 fps once the pause action opened it")
	_press(&"pause")
	assert_false(menu.visible, "the pause action again closes it")
	assert_eq(Engine.max_fps, 60, "and gives back the project's cap")
	_press(&"pause")
	main.get_node("UI/PauseMenu/Resume").pressed.emit()
	assert_false(menu.visible, "Resume closes it")
	assert_eq(Engine.max_fps, 60, "and gives back the project's cap")


func test_a_scene_freed_while_paused_gives_the_cap_back() -> void:
	var main: Node3D = load(MAIN_SCENE).instantiate()
	main.manifest_path = _complete
	add_child(main)
	for error in get_errors():
		if error.contains_text(DEPRECATION):
			error.handled = true
	main.toggle_pause()
	assert_eq(Engine.max_fps, 15, "paused")
	remove_child(main)
	main.free()
	assert_eq(Engine.max_fps, 60, "the project's cap is back once the scene is gone")


func test_the_cap_given_back_is_the_project_setting_not_a_literal() -> void:
	ProjectSettings.set_setting("application/run/max_fps", OTHER_CAP)
	var main: Node3D = load(MAIN_SCENE).instantiate()
	main.manifest_path = _complete
	add_child(main)
	for error in get_errors():
		if error.contains_text(DEPRECATION):
			error.handled = true
	main.toggle_pause()
	assert_eq(Engine.max_fps, 15, "15 fps while the pause screen is open")
	main.toggle_pause()
	assert_eq(Engine.max_fps, OTHER_CAP, "closing it gives back the cap the project now holds")
	main.toggle_pause()
	remove_child(main)
	main.free()
	assert_eq(Engine.max_fps, OTHER_CAP, "and so does a scene freed while paused")


func test_in_an_exported_build_the_missing_packs_are_on_the_panel() -> void:
	ReleaseBuild.set_exported_for_tests(true)
	var main := _main_with(_write())
	var dir := OS.get_executable_path().get_base_dir()
	var packs: PackedStringArray = DATA_PACKS.missing_pack_errors(dir)
	assert_eq(packs.size(), 2, "this test's executable has no data pack beside it")
	var expected := PackedStringArray(["mattini cannot find every data pack.", ""])
	expected.append_array(packs)
	expected.append_array(["", "To fix it, " + EXPORTED])
	assert_eq(_message(main), "\n".join(expected), "the packs' messages and the release folder")
	assert_push_error_count(0, "main logs nothing more: DataPacks logged them at start")


func test_a_missing_terrain_pack_lists_the_packs_then_the_terrain() -> void:
	ReleaseBuild.set_exported_for_tests(true)
	var path := _write_without_heights()
	var main := _main_with(path)
	var packs := _packs()
	var message := _message(main)
	var lines := message.split("\n")
	assert_eq(lines.size(), 8, "the first line, two packs, the terrain's refusal, the fix")
	var reader := lines[5] if lines.size() == 8 else ""
	assert_true(
		reader.begins_with("TerrainGrid: %s: the heights file " % path), "TerrainGrid's refusal"
	)
	assert_true(reader.ends_with(RELEASE_HINT), "ending in the release hint (brief v0.3.1-03)")
	var expected := PackedStringArray(["mattini cannot show the terrain.", ""])
	expected.append_array(packs)
	expected.append_array(["", reader, "", "To fix it, " + EXPORTED])
	assert_eq(message, "\n".join(expected), "the packs after the first line, then the refusal")
	assert_false(message.contains("uv run"), "no pipeline command")
	assert_push_error("TerrainGrid: " + path, "TerrainGrid logs its refusal")
	assert_push_error_count(1, "once, and main logs nothing more")
	assert_not_null(main.get_node_or_null("Buildings"), "the buildings stay")


func test_a_refused_manifest_in_an_export_still_lists_the_packs() -> void:
	ReleaseBuild.set_exported_for_tests(true)
	var path := _write_text("{ not json")
	var main := _main_with(path)
	var packs := _packs()
	var message := _message(main)
	var lines := message.split("\n")
	assert_true(
		message.begins_with("mattini cannot show the terrain, the buildings, "), "all are named"
	)
	assert_gt(lines.size(), 5, "the first line, the packs and the manifest's refusal")
	if lines.size() <= 5:
		return
	assert_eq(lines[1], "", "a blank line after the first")
	assert_eq(lines[2], packs[0], "the photo's pack")
	assert_eq(lines[3], packs[1], "the terrain's pack")
	assert_eq(lines[4], "", "a blank line after the packs")
	assert_true(lines[5].begins_with("WorldConfig: %s: not valid JSON" % path), "the refusal")
	assert_true(message.ends_with("\n\nTo fix it, " + EXPORTED), "the release folder")
	assert_false(message.contains("uv run"), "no pipeline command")
	assert_push_error("WorldConfig: " + path, "WorldConfig logs its refusal")
	assert_push_error_count(1, "once, and main logs nothing more")


func test_outside_an_export_no_pack_is_asked() -> void:
	ReleaseBuild.set_exported_for_tests(false)
	var main := _main_with(_write())
	assert_false(main.get_node("UI/ErrorPanel").visible, "the complete world opens no panel")
	var path := _write_without_heights()
	main = _main_with(path)
	var message := _message(main)
	assert_true(message.begins_with("mattini cannot show the terrain.\n\nTerrainGrid: "), "named")
	assert_false(message.contains("DataPacks"), "no pack is named")
	var fix := [
		"To fix it, run these in the mattini folder, in this order:",
		"    " + RUN + "download terrain",
		"    " + RUN + "terrain",
	]
	assert_true(message.ends_with("\n" + "\n".join(fix)), "the commands, not the release folder")
	assert_push_error("TerrainGrid: " + path, "TerrainGrid logs its refusal")


func test_error_text_shows_the_packs_after_the_first_line() -> void:
	var path := "res://assets/generated/manifest.json"
	var photo := [
		"the aerial photo",
		PackedStringArray(["PhotoGrid: %s: the JPEG is missing" % path]),
		[RUN + "download photo", RUN + "photo"],
	]
	var packs := PackedStringArray(["DataPacks: the data pack mattini-photo.pck (x) is missing"])
	var script: GDScript = load(MAIN_SCRIPT)
	var text: String = script.call("error_text", [photo], path, true, packs)
	var expected := [
		"mattini cannot show the aerial photo.",
		"",
		packs[0],
		"",
		"PhotoGrid: %s: the JPEG is missing" % path,
		"",
		"To fix it, " + EXPORTED,
	]
	assert_eq(text, "\n".join(expected), "the pack's line after the first, then the refusal")
	var without: String = script.call("error_text", [photo], path, true)
	assert_false(without.contains("DataPacks"), "no packs by default")
