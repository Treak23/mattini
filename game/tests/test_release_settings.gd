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
##
## Brief M3-08 (the data packs; docs/SPEC.md §11): the generated folders terrain/ and photo/
## ship in their own packs beside the executable, mattini-terrain.pck and
## mattini-photo.pck, which tools/export.sh writes, so both presets exclude
## assets/generated/terrain/* and assets/generated/photo/* from mattini.pck, and *.part (a
## pipeline step's unfinished write) everywhere. The filters are matched as Godot's export
## matches them (String.matchn against the path with and without res://), so the test also
## reads which generated files each filter keeps in mattini.pck: a folder that only starts
## like a packed one (terrain_old/) stays.

const PRESETS := "res://export_presets.cfg"
const INCLUDE_FILTER := (
	"assets/generated/*, addons/terrain_3d/LICENSE.txt, " + "credits/godot-cpp-LICENSE.txt"
)
const EXCLUDE_FILTER := (
	"tests/*, addons/gut/*, tools/*, *.part, "
	+ "assets/generated/photo/*, assets/generated/terrain/*"
)
## Generated paths and whether mattini.pck holds them (true) or not (false).
const GENERATED_IN_MAIN_PACK := {
	"res://assets/generated/manifest.json": true,
	"res://assets/generated/buildings/2623-1096.bin": true,
	"res://assets/generated/buildings/village.json": true,
	"res://assets/generated/terrain/village.f32": false,
	"res://assets/generated/terrain/village.json": false,
	"res://assets/generated/photo/village.jpg": false,
	"res://assets/generated/photo/village.json": false,
	"res://assets/generated/terrain_old/village.f32": true,
	"res://assets/generated/buildings/2623-1096.bin.part": false,
	"res://assets/generated/manifest.json.part": false,
}


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


## True when a filter of comma-separated globs holds [param path] as Godot's export reads it
## (editor_export_platform.cpp: String.matchn against the path with and without res://).
static func _filter_holds(filter: String, path: String) -> bool:
	for glob in filter.split(","):
		var pattern := glob.strip_edges()
		if pattern.is_empty():
			continue
		if path.matchn(pattern) or path.trim_prefix("res://").matchn(pattern):
			return true
	return false


func test_the_main_pack_keeps_the_small_generated_files_and_no_part() -> void:
	for name: String in ["Linux", "Windows Desktop"]:
		var p: Dictionary = _presets().get(name, {})
		if p.is_empty():
			fail_test("no preset %s" % name)
			continue
		var config: ConfigFile = p["config"]
		var include: String = config.get_value(p["preset"], "include_filter", "")
		var exclude: String = config.get_value(p["preset"], "exclude_filter", "")
		for path: String in GENERATED_IN_MAIN_PACK:
			var held := _filter_holds(include, path) and not _filter_holds(exclude, path)
			assert_eq(held, GENERATED_IN_MAIN_PACK[path], "%s: mattini.pck holds %s" % [name, path])
