extends GutTest
## Pinning tests for brief M2-05: the main scene shows the buildings with the terrain,
## names swissBUILDINGS3D in the credits, and says on screen what it cannot show.
##
## Pinned decisions (docs/SPEC.md §10, M2's game; brief M2-05): after the terrain the main
## scene reads the manifest's buildings block (BuildingChunks) and adds the node
## "Buildings" (BuildingLoader) beside "Terrain". A refused or missing buildings block opens
## UI/ErrorPanel with the refusal and the commands `python -m mattini download buildings`
## and `python -m mattini buildings`, while the terrain stays; its first line names what
## cannot be shown: "the terrain", "the buildings" or "the terrain and the buildings". The
## credits list each loaded dataset on its own line, `<dataset> <edition>, <attribution>`.
##
## The shared terrain fixture has no buildings, so these tests compose a complete world in
## user://: the terrain fixture's manifest and heights, plus a buildings block written here
## for one 2 m box at the terrain's centre, in the same world. The buildings' placement is
## test_building_chunks.gd's subject, not this file's.
##
## Does NOT prove: that anything renders or looks right (no GPU).

const SCRATCH_DIR := "user://test_main_scene_buildings"
const DEPRECATION := "instance_reset_physics_interpolation() is deprecated"
const BUILDINGS_COMMANDS := [
	"python -m mattini download buildings",
	"python -m mattini buildings",
]

var _cases := 0


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


func _terrain_manifest_path() -> String:
	return _repo_file("tests/shared/terrain_fixture/generated/manifest.json")


func after_all() -> void:
	_remove_tree(SCRATCH_DIR)


func _remove_tree(dir: String) -> void:
	for sub in DirAccess.get_directories_at(dir):
		_remove_tree(dir.path_join(sub))
	for file in DirAccess.get_files_at(dir):
		DirAccess.remove_absolute(dir.path_join(file))
	DirAccess.remove_absolute(dir)


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


## One closed box, 2 m wide, its floor at local (1024, y0, 15.5), counter-clockwise from
## outside (as the pipeline writes): 8 vertices, 12 triangles.
func _box_chunk(y0: float) -> PackedByteArray:
	var x0 := 1024.0
	var z0 := 15.5
	var corners := [
		Vector3(x0, y0, z0),
		Vector3(x0 + 2, y0, z0),
		Vector3(x0 + 2, y0, z0 + 2),
		Vector3(x0, y0, z0 + 2),
		Vector3(x0, y0 + 2, z0),
		Vector3(x0 + 2, y0 + 2, z0),
		Vector3(x0 + 2, y0 + 2, z0 + 2),
		Vector3(x0, y0 + 2, z0 + 2),
	]
	# Each face as two triangles whose right-hand normal points out of the box.
	var triangles := [
		[0, 1, 2],
		[0, 2, 3],  # bottom, facing -y
		[4, 7, 6],
		[4, 6, 5],  # top, facing +y
		[0, 4, 5],
		[0, 5, 1],  # z0 side, facing -z
		[3, 2, 6],
		[3, 6, 7],  # z0 + 2 side, facing +z
		[0, 3, 7],
		[0, 7, 4],  # x0 side, facing -x
		[1, 5, 6],
		[1, 6, 2],  # x0 + 2 side, facing +x
	]
	var data := PackedByteArray()
	data.resize(12 * corners.size() + 12 * triangles.size())
	var at := 0
	for corner: Vector3 in corners:
		for axis in 3:
			data.encode_float(at, corner[axis])
			at += 4
	for triangle: Array in triangles:
		for index: int in triangle:
			data.encode_u32(at, index)
			at += 4
	return data


func _sha256(data: PackedByteArray) -> String:
	var context := HashingContext.new()
	context.start(HashingContext.HASH_SHA256)
	context.update(data)
	return context.finish().hex_encode()


## The terrain fixture's manifest with a buildings block for one box (unless [param
## with_buildings] is false), and [param change] applied; written with the terrain's heights
## and the box's chunk under a fresh folder. Returns the manifest's path.
func _write_case(with_buildings := true, change := Callable()) -> String:
	_cases += 1
	var dir := SCRATCH_DIR.path_join("case_%d" % _cases)
	DirAccess.make_dir_recursive_absolute(dir.path_join("terrain"))
	DirAccess.make_dir_recursive_absolute(dir.path_join("buildings"))
	var source := _terrain_manifest_path()
	var json := JSON.new()
	json.parse(FileAccess.get_file_as_string(source))
	var manifest: Dictionary = json.data
	var heights := FileAccess.get_file_as_bytes(
		source.get_base_dir().path_join("terrain/fixture.f32")
	)
	var out := FileAccess.open(dir.path_join("terrain/fixture.f32"), FileAccess.WRITE)
	out.store_buffer(heights)
	out.close()
	manifest["buildings"] = null
	if with_buildings:
		var data := _box_chunk(599.0)
		var chunk := FileAccess.open(dir.path_join("buildings/2601-1199.bin"), FileAccess.WRITE)
		chunk.store_buffer(data)
		chunk.close()
		manifest["buildings"] = {
			"area": "fixture",
			"chunks":
			[
				{
					"buildings": 1,
					"file": "buildings/2601-1199.bin",
					"sha256": _sha256(data),
					"tile": "2601-1199",
					"triangles": 12,
					"vertices": 8,
				}
			],
			"format": "mesh-f32-u32-le",
			"lv95_box": manifest["terrain"]["lv95_box"],
			"source":
			{
				"attribution": "© swisstopo",
				"collection": "ch.swisstopo.swissbuildings3d_3_0",
				"dataset": "swissbuildings3d",
				"edition": "2020",
				"sheets": [{"sha256": "0".repeat(64), "sheet": "1166-44"}],
			},
			"world_sha256": manifest["world_sha256"],
		}
	if change.is_valid():
		change.call(manifest)
	var path := dir.path_join("manifest.json")
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string(JSON.stringify(manifest, "  ", true, true))
	file.close()
	return path


func _message(main: Node3D) -> String:
	return main.get_node("UI/ErrorPanel/Message").text


func test_terrain_and_buildings_are_shown_with_no_error() -> void:
	var main := _main_with(_write_case())
	assert_is(main.get_node_or_null("Terrain"), Terrain3D, "the terrain is built")
	var buildings := main.get_node_or_null("Buildings")
	assert_is(buildings, Node3D, "the buildings are built")
	if buildings != null:
		assert_eq(buildings.get_child_count(), 1, "one chunk")
		assert_is(buildings.get_node_or_null("2601-1199"), MeshInstance3D)
	assert_false(main.get_node("UI/ErrorPanel").visible, "no error panel")
	for error in get_errors():
		assert_true(error.handled, "no engine error or push_error: %s" % error.to_s())


func test_the_credits_name_both_datasets_each_on_its_own_line() -> void:
	var main := _main_with(_write_case())
	var credits: String = main.get_node("UI/PauseMenu/Credits").text
	var lines := credits.split("\n")
	assert_has(lines, "swissalti3d 2024, © swisstopo", "the terrain's line")
	assert_has(lines, "swissbuildings3d 2020, © swisstopo", "the buildings' line")
	assert_lt(
		lines.find("swissalti3d 2024, © swisstopo"),
		lines.find("swissbuildings3d 2020, © swisstopo"),
		"the terrain's first"
	)


func test_no_buildings_built_names_the_buildings_commands_and_keeps_the_terrain() -> void:
	var path := _write_case(false)
	var main := _main_with(path)
	assert_is(main.get_node_or_null("Terrain"), Terrain3D, "the terrain stays")
	assert_null(main.get_node_or_null("Buildings"), "no buildings")
	assert_true(main.get_node("UI/ErrorPanel").visible, "the error panel is open")
	var message := _message(main)
	assert_string_contains(message, "the buildings")
	assert_false(message.contains("the terrain and"), "only the buildings are missing")
	for command: String in BUILDINGS_COMMANDS:
		assert_string_contains(message, command)
	assert_push_error(path, "the refusal is also logged, naming the manifest")


func test_stale_buildings_are_refused_on_screen() -> void:
	var stale := func(m: Dictionary) -> void: m["buildings"]["world_sha256"] = "0".repeat(64)
	var path := _write_case(true, stale)
	var main := _main_with(path)
	assert_null(main.get_node_or_null("Buildings"), "stale buildings are not shown")
	assert_true(main.get_node("UI/ErrorPanel").visible, "the error panel is open")
	assert_string_contains(_message(main), "python -m mattini buildings")
	assert_push_error(path, "the refusal is also logged, naming the manifest")


func test_without_terrain_and_buildings_the_panel_names_both() -> void:
	var none := func(m: Dictionary) -> void: m["terrain"] = null
	var path := _write_case(false, none)
	var main := _main_with(path)
	assert_null(main.get_node_or_null("Terrain"))
	assert_null(main.get_node_or_null("Buildings"))
	var message := _message(main)
	assert_string_contains(message, "the terrain and the buildings")
	assert_string_contains(message, "python -m mattini terrain")
	assert_string_contains(message, "python -m mattini buildings")
	assert_push_error("TerrainGrid: " + path, "the terrain's refusal is logged")
	assert_push_error("BuildingChunks: " + path, "the buildings' refusal is logged")
