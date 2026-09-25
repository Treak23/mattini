extends GutTest
## Pinning tests for brief M1-05: the main scene shows the terrain, starts the camera above
## the terrain's centre looking towards the Matterhorn, shows every problem on screen, and
## shows the version only on the pause screen.
##
## Pinned decisions (docs/SPEC.md §10 and §11; the owner, 2026-09-25): the main scene reads
## the manifest at its manifest_path (res://assets/generated/manifest.json by default; every
## test sets it, so no result depends on what the machine has generated). It builds the
## terrain with TerrainLoader (node "Terrain"), a FreeFlyCamera ("Camera") that asks the
## terrain for the ground height, a fixed sun ("Sun") and a sky ("Environment"). The camera
## starts 150 m above the ground at the centre of the terrain grid, facing bearing 235
## degrees (clockwise from north, computed through WorldConfig), pitched 20 degrees down.
## A missing or refused manifest or terrain opens UI/ErrorPanel, whose Message names the
## command that fixes it (Hard Rule 2). The pause action opens UI/PauseMenu: the version
## (owner: only there), the controls, the credits (every dataset's attribution from the
## manifest, the licences of Godot and Terrain3D; docs/RELEASE.md §A), Resume and Quit.
## Does NOT prove: that anything renders or looks right (no GPU).

const SCRATCH_DIR := "user://test_main_scene"
const DEPRECATION := "instance_reset_physics_interpolation() is deprecated"

var _cases := 0


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


func _fixture_manifest_path() -> String:
	return _repo_file("tests/shared/terrain_fixture/generated/manifest.json")


func before_all() -> void:
	DirAccess.make_dir_recursive_absolute(SCRATCH_DIR)


func after_all() -> void:
	for file in DirAccess.get_files_at(SCRATCH_DIR):
		DirAccess.remove_absolute(SCRATCH_DIR.path_join(file))
	DirAccess.remove_absolute(SCRATCH_DIR)


## Terrain3D 1.0.2 prints this warning once per process, when the first terrain enters the
## tree (brain.md H4). Marks it handled where it appears; asserts nothing about it.
func _absorb_terrain3d_deprecation() -> void:
	for error in get_errors():
		if error.contains_text(DEPRECATION):
			error.handled = true


func _main_with(manifest_path: String) -> Node3D:
	var main: Node3D = load("res://main.tscn").instantiate()
	main.manifest_path = manifest_path
	add_child_autofree(main)
	_absorb_terrain3d_deprecation()
	return main


func _write_manifest_without_terrain() -> String:
	var manifest: Dictionary = JSON.parse_string(
		FileAccess.get_file_as_string(_fixture_manifest_path())
	)
	manifest["terrain"] = null
	_cases += 1
	var path := SCRATCH_DIR.path_join("manifest_%d.json" % _cases)
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string(JSON.stringify(manifest))
	file.close()
	return path


func test_the_fixture_terrain_is_shown_with_no_error() -> void:
	var main := _main_with(_fixture_manifest_path())
	assert_is(main.get_node_or_null("Terrain"), Terrain3D, "the terrain is built")
	assert_is(main.get_node_or_null("Camera"), FreeFlyCamera)
	assert_is(main.get_node_or_null("Sun"), DirectionalLight3D)
	assert_is(main.get_node_or_null("Environment"), WorldEnvironment)
	assert_false(main.get_node("UI/ErrorPanel").visible, "no error panel")
	assert_false(main.get_node("UI/PauseMenu").visible, "not paused at start")
	for error in get_errors():
		assert_true(error.handled, "no engine error or push_error: %s" % error.to_s())


func test_the_camera_starts_above_the_centre_facing_the_matterhorn() -> void:
	var main := _main_with(_fixture_manifest_path())
	var camera: FreeFlyCamera = main.get_node("Camera")
	var terrain: Terrain3D = main.get_node("Terrain")
	# The fixture grid: 41 x 24 vertices at 0.5 m from local (1015.0, 10.5).
	assert_almost_eq(camera.position.x, 1025.0, 0.001, "centre x")
	assert_almost_eq(camera.position.z, 16.25, 0.001, "centre z")
	var ground := terrain.data.get_height(Vector3(1025.0, 0.0, 16.25))
	assert_almost_eq(camera.position.y, ground + 150.0, 0.001, "150 m above the ground")
	var forward := -camera.global_transform.basis.z
	assert_almost_eq(forward.y, sin(deg_to_rad(-20.0)), 0.001, "pitched 20 degrees down")
	var level := Vector2(forward.x, forward.z).normalized()
	var bearing := deg_to_rad(235.0)  # east = sin, north = cos; local z points south here
	assert_almost_eq(level.x, sin(bearing), 0.001, "bearing 235: east part")
	assert_almost_eq(level.y, -cos(bearing), 0.001, "bearing 235: south part")


func test_the_camera_keeps_above_the_ground() -> void:
	var main := _main_with(_fixture_manifest_path())
	var camera: FreeFlyCamera = main.get_node("Camera")
	var terrain: Terrain3D = main.get_node("Terrain")
	camera.set_view(Vector3(1020.0, 0.0, 15.0), 0.0, 0.0)
	var ground := terrain.data.get_height(Vector3(1020.0, 0.0, 15.0))
	assert_almost_eq(camera.position.y, ground + 1.5, 0.001, "lifted above the ground")


func test_no_terrain_built_opens_the_error_panel_naming_the_command() -> void:
	var path := _write_manifest_without_terrain()
	var main := _main_with(path)
	assert_null(main.get_node_or_null("Terrain"), "no terrain without a built terrain")
	assert_true(main.get_node("UI/ErrorPanel").visible, "the error panel is open")
	var message: String = main.get_node("UI/ErrorPanel/Message").text
	assert_string_contains(message, "python -m mattini terrain")
	assert_push_error(path, "the refusal is also logged, naming the manifest")


func test_a_missing_manifest_opens_the_error_panel_naming_the_command() -> void:
	var path := SCRATCH_DIR.path_join("absent/manifest.json")
	var main := _main_with(path)
	assert_true(main.get_node("UI/ErrorPanel").visible, "the error panel is open")
	var message: String = main.get_node("UI/ErrorPanel/Message").text
	assert_string_contains(message, "python -m mattini manifest")
	assert_push_error(path, "the refusal is also logged, naming the manifest")


func test_the_pause_menu_shows_version_controls_and_credits() -> void:
	var main := _main_with(_fixture_manifest_path())
	var camera: FreeFlyCamera = main.get_node("Camera")
	main.toggle_pause()
	var menu: Control = main.get_node("UI/PauseMenu")
	assert_true(menu.visible, "the pause action opens the menu")
	assert_false(camera.input_enabled, "the camera ignores the controls while paused")
	var version: String = ProjectSettings.get_setting("application/config/version")
	assert_eq(main.get_node("UI/PauseMenu/Version").text, "mattini %s" % version)
	var credits: String = main.get_node("UI/PauseMenu/Credits").text
	assert_string_contains(credits, "© swisstopo")
	assert_true(credits.to_lower().contains("swissalti3d"), "the dataset is named")
	assert_string_contains(credits, "Godot Engine")
	assert_string_contains(credits, "Terrain3D")
	assert_string_contains(credits, "Permission is hereby granted")
	var controls: String = main.get_node("UI/PauseMenu/Controls").text
	for key in ["W", "A", "S", "D", "Q", "E", "Shift"]:
		assert_string_contains(controls, key)
	main.toggle_pause()
	assert_false(menu.visible, "the pause action closes the menu")
	assert_true(camera.input_enabled)


func test_the_version_shows_only_in_the_pause_menu() -> void:
	var main := _main_with(_fixture_manifest_path())
	var version: String = ProjectSettings.get_setting("application/config/version")
	var menu: Node = main.get_node("UI/PauseMenu")
	for label in main.find_children("*", "Label", true, false):
		if label.is_visible_in_tree() and not menu.is_ancestor_of(label):
			assert_false(label.text.contains(version), "%s shows no version" % label.name)
	assert_false(get_tree().root.title.contains(version), "nor the window title")
