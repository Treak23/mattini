extends GutTest
## Pinning tests for brief M1-04: Terrain3D 1.0.2 is vendored as its runtime part only.
##
## Pinned decisions (docs/SPEC.md §4 and §9; brain.md H11): the GDExtension and its Linux
## and Windows x86_64 binaries (debug and release), its licence and readme, and its icons;
## no other platform's binaries, and not its editor plugin, whose headless import prints
## leak ERROR lines at exit (measured 2026-09-24), so the plugin is neither vendored nor
## enabled. LICENSE.txt ships with the game for the credits (docs/RELEASE.md §A).

const ADDON := "res://addons/terrain_3d"


func test_terrain3d_1_0_2_is_available() -> void:
	assert_true(ClassDB.class_exists("Terrain3D"), "the GDExtension registers Terrain3D")
	var terrain := Terrain3D.new()
	assert_eq(terrain.get_version(), "1.0.2")
	terrain.free()


func test_the_runtime_files_are_vendored() -> void:
	for rel in [
		"terrain.gdextension",
		"LICENSE.txt",
		"README.md",
		"icons/terrain3d.svg",
		"bin/libterrain.linux.debug.x86_64.so",
		"bin/libterrain.linux.release.x86_64.so",
		"bin/libterrain.windows.debug.x86_64.dll",
		"bin/libterrain.windows.release.x86_64.dll",
	]:
		assert_true(FileAccess.file_exists(ADDON.path_join(rel)), "%s is vendored" % rel)


func test_nothing_else_is_vendored() -> void:
	var binaries := DirAccess.get_files_at(ADDON.path_join("bin"))
	for name in binaries:
		assert_true(
			name.contains(".x86_64.") and (name.contains(".linux.") or name.contains(".windows.")),
			"%s is a Linux or Windows x86_64 binary" % name
		)
	assert_eq(binaries.size(), 4, "four binaries: Linux and Windows, debug and release")
	for editor_part in ["plugin.cfg", "src", "menu", "tools", "utils", "brushes", "extras"]:
		var path := ADDON.path_join(editor_part)
		assert_false(
			FileAccess.file_exists(path) or DirAccess.dir_exists_absolute(path),
			"the editor plugin's %s is not vendored" % editor_part
		)


func test_the_editor_plugin_is_not_enabled() -> void:
	var enabled: PackedStringArray = ProjectSettings.get_setting(
		"editor_plugins/enabled", PackedStringArray()
	)
	assert_false(enabled.has(ADDON.path_join("plugin.cfg")), "Terrain3D's editor plugin is off")
