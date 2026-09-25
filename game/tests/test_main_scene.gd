extends GutTest
## The main scene beyond the pinned tests (brief M1-05; M0-03's default-path test replaced):
## it frees cleanly; the controls reach the camera through the InputMap and stop while the
## pause screen is open; the sun is placed through WorldConfig; the error panel shows the
## refusal itself with the command that fixes it; the credits and the controls hold what
## the pause screen promises. Every test sets manifest_path, so no result depends on what
## this machine has generated.
##
## Does NOT prove: that anything renders or looks right (no GPU); how the controls feel.

const SCRATCH_DIR := "user://test_main_scene_errors"
const DEPRECATION := "instance_reset_physics_interpolation() is deprecated"

var _cases := 0


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


func _fixture_manifest_path() -> String:
	return _repo_file("tests/shared/terrain_fixture/generated/manifest.json")


func before_all() -> void:
	DirAccess.make_dir_recursive_absolute(SCRATCH_DIR.path_join("terrain"))


func after_all() -> void:
	for folder in [SCRATCH_DIR.path_join("terrain"), SCRATCH_DIR]:
		for file in DirAccess.get_files_at(folder):
			DirAccess.remove_absolute(folder.path_join(file))
		DirAccess.remove_absolute(folder)


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


## The fixture's manifest with [param change] applied, written under SCRATCH_DIR next to a
## copy of the fixture's heights; returns its path.
func _write_manifest(change: Callable, heights := PackedByteArray()) -> String:
	var fixture := _fixture_manifest_path()
	var manifest: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(fixture))
	if heights.is_empty():
		heights = FileAccess.get_file_as_bytes(
			fixture.get_base_dir().path_join("terrain/fixture.f32")
		)
	var heights_file := FileAccess.open(
		SCRATCH_DIR.path_join("terrain/fixture.f32"), FileAccess.WRITE
	)
	heights_file.store_buffer(heights)
	heights_file.close()
	change.call(manifest)
	_cases += 1
	var path := SCRATCH_DIR.path_join("manifest_%d.json" % _cases)
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string(JSON.stringify(manifest))
	file.close()
	return path


func _write_text(text: String) -> String:
	_cases += 1
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


func test_the_sun_shines_from_azimuth_150_at_35_degrees() -> void:
	var main := _main_with(_fixture_manifest_path())
	var sun: DirectionalLight3D = main.get_node("Sun")
	assert_true(sun.shadow_enabled, "the sun casts shadows")
	var to_sun := sun.global_transform.basis.z  # a light shines along its −z
	var elevation := deg_to_rad(35.0)
	var azimuth := deg_to_rad(150.0)
	assert_almost_eq(to_sun.y, sin(elevation), 0.0001, "elevation 35 degrees")
	# The owner's axes: east is +x, north is −z.
	assert_almost_eq(to_sun.x, sin(azimuth) * cos(elevation), 0.0001, "east part")
	assert_almost_eq(to_sun.z, -cos(azimuth) * cos(elevation), 0.0001, "south part")


func test_a_manifest_that_is_not_json_shows_its_refusal_and_the_manifest_command() -> void:
	var path := _write_text("{ not json")
	var main := _main_with(path)
	assert_true(main.get_node("UI/ErrorPanel").visible, "the error panel is open")
	var message: String = main.get_node("UI/ErrorPanel/Message").text
	assert_string_contains(message, "not valid JSON")
	assert_string_contains(message, path)
	assert_string_contains(message, "uv run --project pipeline python -m mattini manifest")
	assert_null(main.get_node_or_null("Terrain"))
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
	assert_null(main.get_node_or_null("Terrain"))
	assert_push_error("SHA-256", "the refusal is logged once, by TerrainGrid")
	assert_push_error_count(1, "and only once")


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
	for label in main.find_children("*", "Label", true, false):
		if label.is_visible_in_tree() and not menu.is_ancestor_of(label):
			assert_false(label.text.contains(version), "%s shows no version" % label.name)
	var credits: String = main.get_node("UI/PauseMenu/Credits").text
	assert_string_contains(credits, "No terrain is loaded")


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


func test_the_controls_name_every_action_and_the_wheel() -> void:
	var main := _main_with(_fixture_manifest_path())
	var controls: String = main.get_node("UI/PauseMenu/Controls").text
	for line in ["W: fly forward", "Shift: hold to fly 5 times faster", "Escape: this screen"]:
		assert_string_contains(controls, line)
	assert_string_contains(controls, "Right Mouse Button: hold and move the mouse to look")
	assert_string_contains(controls, "Mouse Wheel: flying speed ×1.25 per notch, 2 to 1000 m/s")
