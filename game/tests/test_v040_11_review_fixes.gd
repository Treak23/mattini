extends GutTest
## Brief v0.4.0-11, the whole-range review's fixes (docs/briefs/v0.4.0-11-the-review-fixes.md).
##
## 1. SkySite's refusals end like every other reader's (ReleaseBuild.file_hint): in an exported
## build "download the release folder again", never the command a player cannot run (review F3);
## outside one, the command. Each refusal of the block is read in both modes.
## 2. Both render scripts stop the main scene's _process between add_child and the first await,
## so the game clock leaves the sun where _ready put it (text census, lesson 5).
##
## Does NOT prove: that an exported build prints the message (the release template ignores
## --script); that the render numbers repeat (the gate's render step prints them); that the
## stopped clock does what the census says it does, only that the line is there and in place.

const CompleteWorld := preload("res://tests/complete_world.gd")
const SCRATCH_DIR := "user://test_v040_11_review_fixes"
const COMMAND := "python -m mattini sky"
const RELEASE_HINT := "; it ships in the release's packs: download the release folder again"
const RENDER_SCRIPTS := [
	"res://tests/render/render_photo.gd",
	"res://tests/render/render_trees.gd",
]

var _cases := 0
var _complete := ""


func before_all() -> void:
	_complete = CompleteWorld.write(SCRATCH_DIR.path_join("complete"))


func after_each() -> void:
	ReleaseBuild.set_exported_for_tests(null)


func after_all() -> void:
	CompleteWorld.remove_tree(SCRATCH_DIR)


func _problem(change: Callable) -> String:
	var json := JSON.new()
	assert_eq(json.parse(FileAccess.get_file_as_string(_complete)), OK, "the world parses")
	var manifest: Dictionary = json.data
	change.call(manifest)
	_cases += 1
	DirAccess.make_dir_recursive_absolute(SCRATCH_DIR)
	var path := SCRATCH_DIR.path_join("case_%d.json" % _cases)
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string(JSON.stringify(manifest, "  ", true, true))
	file.close()
	return SkySite.new()._read(path, WorldConfig.from_manifest(path))


func _refusals() -> Array:
	return [
		func(m: Dictionary) -> void: m["sky"] = null,
		func(m: Dictionary) -> void: m["sky"] = [1, 2],
		func(m: Dictionary) -> void: m["sky"]["world_sha256"] = "0".repeat(64),
		func(m: Dictionary) -> void: m["sky"]["elevation_deg"] = 1.0,
		func(m: Dictionary) -> void: m["sky"]["area"] = "village",
		func(m: Dictionary) -> void: m["sky"]["latitude_deg"] = 90.5,
	]


func test_in_an_export_every_refusal_ends_with_the_release_hint() -> void:
	ReleaseBuild.set_exported_for_tests(true)
	var seen := 0
	for change: Callable in _refusals():
		var problem := _problem(change)
		seen += 1
		assert_false(problem.is_empty(), "case %d is refused" % seen)
		assert_true(problem.ends_with(RELEASE_HINT), "case %d ends: %s" % [seen, problem])
		assert_false(problem.contains("python -m mattini"), "no command a player cannot run")
		assert_false(problem.contains("run "), "no 'run <command>' ending: %s" % problem)
	assert_eq(seen, 6, "all six refusals were read")


func test_outside_an_export_every_refusal_names_the_command() -> void:
	ReleaseBuild.set_exported_for_tests(false)
	var seen := 0
	for change: Callable in _refusals():
		var problem := _problem(change)
		seen += 1
		assert_true(
			problem.ends_with("; %s rebuilds it" % COMMAND), "case %d: %s" % [seen, problem]
		)
		assert_false(problem.contains(RELEASE_HINT), "no release hint outside an export")
	assert_eq(seen, 6, "all six refusals were read")


func test_the_render_scripts_stop_the_main_scene_s_clock() -> void:
	for script: String in RENDER_SCRIPTS:
		var lines := FileAccess.get_file_as_string(script).split("\n")
		var added := -1
		var stopped := -1
		var awaited := -1
		for i in lines.size():
			var line := lines[i].strip_edges()
			if added < 0 and line == "root.add_child(main)":
				added = i
			elif stopped < 0 and line == "main.set_process(false)":
				stopped = i
			if added >= 0 and awaited < 0 and i > added and line.contains("await"):
				awaited = i
		assert_gt(added, -1, "%s adds the main scene" % script)
		assert_gt(stopped, added, "%s stops _process after add_child" % script)
		assert_gt(awaited, stopped, "%s stops it before the first await" % script)
