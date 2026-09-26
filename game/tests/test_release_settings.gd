extends GutTest
## Pinning tests for brief M1-06: the first version and the two export presets.
##
## Pinned decisions (docs/SPEC.md §11; the owner, 2026-09-25): the version scheme is
## 0.<n>.<patch> until v1; M1's close shipped 0.1.0, M2's ships 0.2.0. Exports for Linux
## and Windows, x86_64, go to build/ (git-ignored) with the .pck beside the executable, so
## no single file carries the engine and the data together (GitHub's 100 MB limit,
## docs/RELEASE.md §C).
## The generated assets and Terrain3D's licence ship; the tests and GUT do not. The Windows
## preset does not rewrite the executable's resources, which would need rcedit.
##
## Brief M2-02 (M1 R1 G-02, G-06): both presets' include and exclude filters are pinned
## exactly, since a narrower filter still holds the texts a substring check looks for
## ("assets/generated/*.json" contains "assets/generated/*") and ships a build without its
## heights; godot-cpp's licence ships for the credits.
##
## Brief M2-08 (M2 R1 G-06): the development tools under res://tools/ (the screenshot
## script) do not ship: both presets exclude tools/*.

const PRESETS := "res://export_presets.cfg"
const INCLUDE_FILTER := (
	"assets/generated/*, addons/terrain_3d/LICENSE.txt, " + "credits/godot-cpp-LICENSE.txt"
)
const EXCLUDE_FILTER := "tests/*, addons/gut/*, tools/*"


func _presets() -> Dictionary:
	var config := ConfigFile.new()
	assert_eq(config.load(PRESETS), OK, "export_presets.cfg loads")
	var by_name := {}
	for section in config.get_sections():
		if section.count(".") == 1 and section.begins_with("preset."):
			var name: String = config.get_value(section, "name", "")
			by_name[name] = {"preset": section, "options": section + ".options", "config": config}
	return by_name


func test_the_version_is_0_2_0() -> void:
	assert_eq(ProjectSettings.get_setting("application/config/version"), "0.2.0")


func test_linux_and_windows_presets_exist() -> void:
	var presets := _presets()
	assert_eq(presets.keys().size(), 2, "two presets")
	assert_has(presets, "Linux")
	assert_has(presets, "Windows Desktop")


func test_each_preset_ships_the_data_and_the_licence_but_not_the_tests() -> void:
	var paths := {
		"Linux": "../build/linux/mattini.x86_64",
		"Windows Desktop": "../build/windows/mattini.exe",
	}
	for name: String in paths:
		var p: Dictionary = _presets().get(name, {})
		if p.is_empty():
			fail_test("no preset %s" % name)
			continue
		var config: ConfigFile = p["config"]
		assert_eq(config.get_value(p["preset"], "platform"), name, "%s platform" % name)
		assert_eq(config.get_value(p["preset"], "export_path"), paths[name], "%s path" % name)
		var include: String = config.get_value(p["preset"], "include_filter", "")
		assert_eq(include, INCLUDE_FILTER, "%s include filter, exactly" % name)
		var exclude: String = config.get_value(p["preset"], "exclude_filter", "")
		assert_eq(exclude, EXCLUDE_FILTER, "%s exclude filter, exactly" % name)
		assert_eq(config.get_value(p["options"], "binary_format/architecture"), "x86_64")
		assert_eq(config.get_value(p["options"], "binary_format/embed_pck"), false, "pck beside")
	var windows: Dictionary = _presets().get("Windows Desktop", {})
	if not windows.is_empty():
		var config: ConfigFile = windows["config"]
		assert_eq(config.get_value(windows["options"], "application/modify_resources"), false)
