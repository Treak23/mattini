extends GutTest
## project.godot holds the decisions of brief M0-03: name, version, main scene, Forward+,
## and the GUT plugin enabled.


func test_project_settings_hold_the_briefs_decisions() -> void:
	assert_eq(ProjectSettings.get_setting("application/config/name"), "mattini")
	assert_eq(ProjectSettings.get_setting("application/config/version"), "0.2.0")
	assert_eq(ProjectSettings.get_setting("application/run/main_scene"), "res://main.tscn")
	assert_eq(ProjectSettings.get_setting("rendering/renderer/rendering_method"), "forward_plus")
	assert_has(
		ProjectSettings.get_setting("editor_plugins/enabled", PackedStringArray()),
		"res://addons/gut/plugin.cfg"
	)
