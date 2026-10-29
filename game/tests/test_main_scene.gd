extends GutTest
## The main scene beyond the pinned tests (brief M1-05; M0-03's default-path test replaced):
## it frees cleanly; the controls reach the camera through the InputMap and stop while the
## pause screen is open; the error panel shows the refusal itself with the command that fixes
## it; the credits and the controls hold what the pause screen promises. The sun and the
## light are test_main_scene_light.gd's since brief M3-14. Every test sets manifest_path, so
## no result depends on what this machine has generated.
##
## Brief M2-05: the shared terrain fixture has no buildings, and a missing buildings block
## is refused on screen, so these tests read a complete world (complete_world.gd): the
## terrain fixture plus one box. A test that means something is missing says so.
##
## Brief v0.4.0-08 (M4-10 decision 10, cut to the sky): a refused manifest names seven, the
## sun's and the moon's course after the roof colours.
##
## Does NOT prove: that anything renders or looks right (no GPU); how the controls feel.

const CompleteWorld := preload("res://tests/complete_world.gd")
const SCRATCH_DIR := "user://test_main_scene_errors"
const DEPRECATION := "instance_reset_physics_interpolation() is deprecated"

var _cases := 0
var _complete := ""


func _fixture_manifest_path() -> String:
	return _complete


func before_all() -> void:
	_complete = CompleteWorld.write(SCRATCH_DIR.path_join("complete"))


func after_all() -> void:
	CompleteWorld.remove_tree(SCRATCH_DIR)


func after_each() -> void:
	for action in [&"fly_forward", &"fly_up", &"fly_fast", &"fly_look"]:
		Input.action_release(action)


## Terrain3D 1.0.2 prints this warning once per process, when the first terrain enters the
## tree (brain.md H4). Marks it handled where it appears; asserts nothing about it.
func _absorb_terrain3d_deprecation() -> void:
	for error in get_errors():
		if error.contains_text(DEPRECATION):
			error.handled = true


func _instance(manifest_path: String) -> Node3D:
	var main: Node3D = load("res://main.tscn").instantiate()
	main.manifest_path = manifest_path
	return main


func _main_with(manifest_path: String) -> Node3D:
	var main := _instance(manifest_path)
	add_child_autofree(main)
	_absorb_terrain3d_deprecation()
	return main


## The complete world with [param change] applied and [param heights] (the fixture's when
## empty), written into a fresh folder under SCRATCH_DIR; returns its manifest's path.
func _write_manifest(change: Callable, heights := PackedByteArray()) -> String:
	_cases += 1
	return CompleteWorld.write(SCRATCH_DIR.path_join("case_%d" % _cases), change, heights)


func _write_text(text: String) -> String:
	_cases += 1
	DirAccess.make_dir_recursive_absolute(SCRATCH_DIR)
	var path := SCRATCH_DIR.path_join("manifest_%d.json" % _cases)
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string(text)
	file.close()
	return path


## Sends [param event] through the viewport's input path (_input, the GUI, then
## _unhandled_input), at once. Input.parse_input_event would deliver it a frame later.
func _send(event: InputEvent) -> void:
	get_viewport().push_input(event)


func _press(action: StringName, pressed: bool) -> void:
	var event := InputEventAction.new()
	event.action = action
	event.pressed = pressed
	_send(event)


func _motion(pixels: Vector2) -> InputEventMouseMotion:
	var motion := InputEventMouseMotion.new()
	motion.relative = pixels
	motion.screen_relative = pixels
	return motion


func _wheel_up() -> InputEventMouseButton:
	var wheel := InputEventMouseButton.new()
	wheel.button_index = MOUSE_BUTTON_WHEEL_UP
	wheel.pressed = true
	return wheel


func test_the_main_scene_frees_cleanly() -> void:
	var main := _instance(_fixture_manifest_path())
	add_child(main)
	_absorb_terrain3d_deprecation()
	await wait_process_frames(2)
	assert_true(main.is_inside_tree(), "the main scene is in the tree")
	remove_child(main)
	main.free()
	for error in get_errors():
		assert_true(error.handled, "no engine error or push_error: %s" % error.to_s())
	assert_no_new_orphans("freeing the main scene leaves no orphan nodes")


func test_the_camera_is_current_and_sees_far() -> void:
	var main := _main_with(_fixture_manifest_path())
	var camera: FreeFlyCamera = main.get_node("Camera")
	assert_true(camera.current, "the free-fly camera is the viewport's camera")
	assert_almost_eq(camera.near, 0.1, 0.00001)
	assert_almost_eq(camera.far, 20000.0, 0.001)
	assert_almost_eq(camera.fov, 70.0, 0.00001)


func test_the_fly_actions_move_the_camera_and_stop_while_paused() -> void:
	var main := _main_with(_fixture_manifest_path())
	var camera: FreeFlyCamera = main.get_node("Camera")
	var start := camera.position
	Input.action_press(&"fly_up")
	await wait_process_frames(3)
	Input.action_release(&"fly_up")
	assert_gt(camera.position.y, start.y, "fly_up lifts the camera")
	main.toggle_pause()
	var paused_at := camera.position
	Input.action_press(&"fly_up")
	await wait_process_frames(3)
	Input.action_release(&"fly_up")
	assert_eq(camera.position, paused_at, "the camera ignores its controls while paused")


func test_the_pause_action_opens_and_closes_the_pause_screen() -> void:
	var main := _main_with(_fixture_manifest_path())
	var menu: Control = main.get_node("UI/PauseMenu")
	_press(&"pause", true)
	_press(&"pause", false)
	assert_true(menu.visible, "Escape opens the pause screen")
	_press(&"pause", true)
	_press(&"pause", false)
	assert_false(menu.visible, "Escape again closes it")
	main.toggle_pause()
	main.get_node("UI/PauseMenu/Resume").pressed.emit()
	assert_false(menu.visible, "Resume closes it")
	assert_true(main.get_node("Camera").input_enabled, "and gives the controls back")


func test_looking_turns_the_camera_only_while_fly_look_is_held() -> void:
	var main := _main_with(_fixture_manifest_path())
	var camera: FreeFlyCamera = main.get_node("Camera")
	var yaw := camera.rotation.y
	_send(_motion(Vector2(40, 0)))
	assert_almost_eq(camera.rotation.y, yaw, 0.00001, "no turn without fly_look")
	_press(&"fly_look", true)
	_send(_motion(Vector2(40, 0)))
	_press(&"fly_look", false)
	assert_almost_eq(
		camera.rotation.y, wrapf(yaw - 40 * camera.mouse_sensitivity, -PI, PI), 0.00001, "turned"
	)
	yaw = camera.rotation.y
	_send(_motion(Vector2(40, 0)))
	assert_almost_eq(camera.rotation.y, yaw, 0.00001, "no turn once fly_look is released")


func test_the_wheel_changes_the_speed_but_not_while_paused() -> void:
	var main := _main_with(_fixture_manifest_path())
	var camera: FreeFlyCamera = main.get_node("Camera")
	_send(_wheel_up())
	assert_almost_eq(camera.speed_mps, 37.5, 0.0001, "one notch up")
	main.toggle_pause()
	_send(_wheel_up())
	assert_almost_eq(camera.speed_mps, 37.5, 0.0001, "the wheel is ignored while paused")


func test_a_manifest_that_is_not_json_shows_its_refusal_and_the_manifest_command() -> void:
	var path := _write_text("{ not json")
	var main := _main_with(path)
	assert_true(main.get_node("UI/ErrorPanel").visible, "the error panel is open")
	var message: String = main.get_node("UI/ErrorPanel/Message").text
	assert_string_contains(message, "not valid JSON")
	assert_string_contains(message, path)
	assert_string_contains(message, "uv run --project pipeline python -m mattini manifest")
	assert_true(
		message.begins_with(
			(
				"mattini cannot show the terrain, the buildings, the aerial photo, the surfaces"
				+ " (roads, paths, water and rock), the trees, the roof colours and the sun's and"
				+ " the moon's course.\n"
			)
		),
		"a refused manifest shows nothing: all seven are named (M2-05, M3-14, v0.4.0-08)"
	)
	assert_null(main.get_node_or_null("Terrain"))
	assert_null(main.get_node_or_null("Buildings"))
	var credits: String = main.get_node("UI/PauseMenu/Credits").text
	assert_string_contains(credits, "\nNo generated data is loaded, so no dataset is shown.\n")
	assert_push_error("not valid JSON", "the refusal is logged once, by WorldConfig")
	assert_push_error_count(1, "and only once")


func test_a_damaged_heights_file_shows_its_refusal_and_the_terrain_commands() -> void:
	var fixture := _fixture_manifest_path().get_base_dir().path_join("terrain/fixture.f32")
	var heights := FileAccess.get_file_as_bytes(fixture)
	heights[0] ^= 1
	var path := _write_manifest(func(_manifest: Dictionary) -> void: pass, heights)
	var main := _main_with(path)
	assert_true(main.get_node("UI/ErrorPanel").visible, "the error panel is open")
	var message: String = main.get_node("UI/ErrorPanel/Message").text
	assert_string_contains(message, "SHA-256")
	var download := message.find("uv run --project pipeline python -m mattini download terrain")
	var build := message.rfind("uv run --project pipeline python -m mattini terrain")
	assert_gt(download, -1, "the download command is named")
	assert_gt(build, download, "then the terrain command")
	assert_false(message.contains("buildings"), "the buildings are not refused (M2-05)")
	assert_null(main.get_node_or_null("Terrain"))
	assert_is(main.get_node_or_null("Buildings"), Node3D, "the buildings stay")
	assert_push_error("SHA-256", "the refusal is logged once, by TerrainGrid")
	assert_push_error_count(1, "and only once")


## The complete world without its terrain: the buildings stay (M2-05).
func test_without_terrain_the_camera_still_flies_and_no_version_shows() -> void:
	var path := _write_manifest(func(manifest: Dictionary) -> void: manifest["terrain"] = null)
	var main := _main_with(path)
	assert_push_error(path)
	var camera: FreeFlyCamera = main.get_node("Camera")
	var start := camera.position
	Input.action_press(&"fly_forward")
	await wait_process_frames(3)
	Input.action_release(&"fly_forward")
	assert_ne(camera.position, start, "the camera flies with no terrain")
	var version: String = ProjectSettings.get_setting("application/config/version")
	var menu: Node = main.get_node("UI/PauseMenu")
	# Every visible Control with a text property outside the menu, not only Labels (M2-02).
	var shown := 0
	for control: Control in main.find_children("*", "Control", true, false):
		var text: Variant = control.get("text")
		if typeof(text) != TYPE_STRING or menu == control or menu.is_ancestor_of(control):
			continue
		if control.is_visible_in_tree():
			shown += 1
			assert_false(text.contains(version), "%s shows no version" % control.get_path())
	assert_gt(shown, 0, "the error panel's message is shown and looked at")
	var credits: String = main.get_node("UI/PauseMenu/Credits").text
	assert_false(credits.contains("swissalti3d"), "no terrain, so no terrain dataset")
	assert_string_contains(credits, "\nswissbuildings3d 2020, © swisstopo\n", "the buildings'")


func test_the_credits_hold_the_dataset_and_every_licence_text() -> void:
	var main := _main_with(_fixture_manifest_path())
	var credits: String = main.get_node("UI/PauseMenu/Credits").text
	assert_string_contains(credits, "swissalti3d 2024, © swisstopo")
	assert_true(credits.contains(Engine.get_license_text()), "Godot's licence")
	var licences := Engine.get_license_info()
	for licence: String in licences:
		assert_true(credits.contains(licences[licence]), "the licence %s" % licence)
	for component: Dictionary in Engine.get_copyright_info():
		assert_true(credits.contains(component["name"] + ": ©"), component["name"])
	var terrain3d := FileAccess.get_file_as_string("res://addons/terrain_3d/LICENSE.txt")
	assert_false(terrain3d.is_empty(), "Terrain3D's licence file is there")
	assert_true(credits.contains("Terrain3D 1.0.2\n" + terrain3d), "Terrain3D's licence")
	assert_true(main.get_node("UI/PauseMenu/Credits").scroll_active, "the credits scroll")


## Brief M2-02 (M1 R1 G-06; M1 close, D17): godot-cpp is compiled into Terrain3D's library,
## so its MIT notice follows Terrain3D's licence, from its LICENSE.md vendored verbatim.
func test_the_credits_carry_godot_cpp_after_terrain3d() -> void:
	var main := _main_with(_fixture_manifest_path())
	var credits: String = main.get_node("UI/PauseMenu/Credits").text
	var heading := "godot-cpp (compiled into Terrain3D's library)"
	var copyright := "Copyright (c) 2017-present Godot Engine contributors."
	assert_string_contains(credits, "\n" + heading + "\n")
	assert_string_contains(credits, copyright)
	var godot_cpp := FileAccess.get_file_as_string("res://credits/godot-cpp-LICENSE.txt")
	assert_string_contains(godot_cpp, copyright, "the vendored file holds the copyright line")
	assert_string_contains(godot_cpp, "Permission is hereby granted", "and the MIT licence")
	assert_true(credits.contains(heading + "\n" + godot_cpp), "the whole file after the heading")
	var terrain3d := FileAccess.get_file_as_string("res://addons/terrain_3d/LICENSE.txt")
	var terrain3d_at := credits.find("Terrain3D 1.0.2\n" + terrain3d)
	assert_gt(terrain3d_at, -1, "Terrain3D's licence is there")
	assert_gt(credits.find(heading), terrain3d_at, "godot-cpp's notice follows it")
	assert_eq(
		FileAccess.get_sha256("res://credits/godot-cpp-LICENSE.txt"),
		"26a5b210d90760156ce886267ce9df235787dcc6cebfd7ecd95ef5b6fdcc95bf",
		"godot-cpp's LICENSE.md at 6388e26d, the commit Terrain3D 1.0.2 builds with, unchanged"
	)


func test_the_controls_name_every_action_and_the_wheel() -> void:
	var main := _main_with(_fixture_manifest_path())
	var controls: String = main.get_node("UI/PauseMenu/Controls").text
	for line in ["W: fly forward", "Shift: hold to fly 5 times faster", "Escape: this screen"]:
		assert_string_contains(controls, line)
	assert_string_contains(controls, "Right Mouse Button: hold and move the mouse to look")
	assert_string_contains(controls, "Mouse Wheel: flying speed ×1.25 per notch, 2 to 1000 m/s")
