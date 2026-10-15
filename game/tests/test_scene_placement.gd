extends GutTest
## Pinning tests for briefs M2-08 and M3-02 (M2 R1 P-01, P-04, G-02; M2 V1-G-02): the
## buildings stand in the scene where the world config puts them, on their terrain.
##
## Pinned decisions (docs/SPEC.md §8, the buildings, the game part; brief M2-08): the
## Buildings node and every chunk mesh sit at the scene's origin with no rotation or scale
## (global_transform is the identity), so a vertex's place in the scene is the local
## position the pipeline wrote for the world config the manifest pins (Hard Rule 4). On the
## shared buildings fixture every named vertex lies, in the scene, at WorldConfig.to_local
## of its LV95 point. In the complete test world the ground at the box's footprint lies
## between its floor and its roof. BuildingChunks refuses a WorldConfig read from another
## manifest. With the terrain refused, the camera starts over the centre of the buildings'
## bounds, START_ABOVE_M above the highest of their vertices.
##
## Since brief M3-02 (M2 V1-G-02; design's full replacement of M2-08's file) the camera's
## start is compared with those two points within 1 cm, where it was only required to lie
## inside the bounds and above the highest vertex: a start over a corner of the bounds,
## START_ABOVE_M above the lowest vertex, passed that.
##
## Since brief M3-14 (design's full replacement of M3-02's file; only this paragraph and the
## errors absorbed change): the main scene also reads the photo, surfaces, trees and roofs
## blocks, and the shared buildings fixture has none of them, so their readers' refusals of
## it are absorbed as the terrain's are; complete_world.gd now holds every block.
##
## Does NOT prove: that anything renders or looks right (no GPU); that the real village's
## buildings meet its terrain (measured at M2 planning and by the review, SPEC §8).

const CompleteWorld := preload("res://tests/complete_world.gd")
const Main := preload("res://scripts/main.gd")
const TOLERANCE_M := 0.01
const SCRATCH_DIR := "user://test_scene_placement"
const DEPRECATION := "instance_reset_physics_interpolation() is deprecated"
## The readers whose refusals of the buildings fixture (it holds only buildings) are expected.
const ABSENT_BLOCKS := [
	"TerrainGrid: ", "PhotoGrid: ", "SurfaceGrid: ", "TreeChunks: ", "BuildingRoofs: "
]

var _cases := 0


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


func after_all() -> void:
	_remove_tree(SCRATCH_DIR)


func _remove_tree(dir: String) -> void:
	for sub in DirAccess.get_directories_at(dir):
		_remove_tree(dir.path_join(sub))
	for file in DirAccess.get_files_at(dir):
		DirAccess.remove_absolute(dir.path_join(file))
	DirAccess.remove_absolute(dir)


func _absorb_expected_errors() -> void:
	for error in get_errors():
		if error.contains_text(DEPRECATION):
			error.handled = true
		for reader: String in ABSENT_BLOCKS:
			if error.contains_text(reader):
				error.handled = true


func _main_with(manifest_path: String) -> Node3D:
	var main: Node3D = load("res://main.tscn").instantiate()
	main.manifest_path = manifest_path
	add_child_autofree(main)
	_absorb_expected_errors()
	return main


func _complete_world() -> String:
	_cases += 1
	return CompleteWorld.write(SCRATCH_DIR.path_join("case_%d" % _cases))


func _buildings_fixture() -> String:
	return _repo_file("tests/shared/buildings_fixture/generated/manifest.json")


func _vectors() -> Dictionary:
	var json := JSON.new()
	var text := FileAccess.get_file_as_string(_repo_file("tests/shared/buildings_vectors.json"))
	assert_eq(json.parse(text), OK, "the buildings vectors parse")
	return json.data if typeof(json.data) == TYPE_DICTIONARY else {}


## Every vertex of every surface of [param mesh], in scene coordinates.
func _global_vertices(mesh: MeshInstance3D) -> PackedVector3Array:
	var found := PackedVector3Array()
	var array_mesh := mesh.mesh as ArrayMesh
	for s in array_mesh.get_surface_count():
		var vertices: PackedVector3Array = array_mesh.surface_get_arrays(s)[Mesh.ARRAY_VERTEX]
		for v in vertices:
			found.append(mesh.global_transform * v)
	return found


func test_the_buildings_sit_at_the_scene_origin() -> void:
	var main := _main_with(_complete_world())
	var buildings: Node3D = main.get_node_or_null("Buildings")
	assert_not_null(buildings, "the buildings are built")
	if buildings == null:
		return
	assert_eq(buildings.global_transform, Transform3D.IDENTITY, "the Buildings node")
	assert_gt(buildings.get_child_count(), 0, "at least one chunk")
	for mesh in buildings.get_children():
		assert_eq(mesh.global_transform, Transform3D.IDENTITY, "chunk %s" % mesh.name)


func test_every_named_vertex_lies_in_the_scene_where_the_world_config_puts_it() -> void:
	# The buildings fixture has no terrain: the panel opens for it, the buildings load.
	var main := _main_with(_buildings_fixture())
	var world := WorldConfig.from_manifest(_buildings_fixture())
	var buildings: Node3D = main.get_node_or_null("Buildings")
	assert_not_null(buildings, "the fixture's buildings are built without a terrain")
	if buildings == null or world == null:
		return
	var vertices: Array = _vectors()["vertices"]
	assert_gt(vertices.size(), 7, "the vectors name vertices in every chunk")
	for v: Dictionary in vertices:
		var mesh: MeshInstance3D = buildings.get_node_or_null(String(v["tile"]))
		assert_not_null(mesh, "%s: its chunk's mesh" % v["name"])
		if mesh == null:
			continue
		var lv95: Array = v["lv95"]
		var expected := world.to_local(lv95[0], lv95[1], lv95[2])
		var nearest := INF
		for p in _global_vertices(mesh):
			nearest = minf(nearest, p.distance_to(expected))
		assert_lt(nearest, 0.0001, "%s: in the scene at to_local of its LV95 point" % v["name"])


func test_the_box_stands_on_its_terrain() -> void:
	var main := _main_with(_complete_world())
	var floor_y: float = CompleteWorld.BOX_FLOOR.y
	var roof_y: float = floor_y + CompleteWorld.BOX_HEIGHT
	var x: float = CompleteWorld.BOX_FLOOR.x + 1.0
	var z: float = CompleteWorld.BOX_FLOOR.z + 1.0
	var ground: float = main._ground_height(x, z)
	assert_false(is_nan(ground), "the terrain is under the box")
	assert_between(ground, floor_y, roof_y, "the ground lies between the box's floor and roof")
	# And the box is where its chunk says: its lowest global vertex is the floor.
	var lowest := INF
	for p in _global_vertices(main.get_node("Buildings").get_child(0)):
		lowest = minf(lowest, p.y)
	assert_almost_eq(lowest, floor_y, 0.0001, "the floor, in the scene")


func test_a_world_config_from_another_manifest_is_refused() -> void:
	var other := WorldConfig.from_manifest(
		_repo_file("tests/shared/terrain_fixture/generated/manifest.json")
	)
	assert_not_null(other)
	var chunks := BuildingChunks.from_manifest(_buildings_fixture(), other)
	assert_null(chunks, "another world's config is refused")
	var found := false
	for error in get_errors():
		if not found and error.is_push_error() and error.contains_text(_buildings_fixture()):
			error.handled = true
			found = true
	assert_true(found, "one push_error names the manifest")


func test_without_terrain_the_camera_starts_over_the_buildings() -> void:
	var main := _main_with(_buildings_fixture())
	var camera: Camera3D = main.get_node("Camera")
	var box := AABB()
	var first := true
	for mesh in main.get_node("Buildings").get_children():
		for p in _global_vertices(mesh):
			if first:
				box = AABB(p, Vector3.ZERO)
				first = false
			else:
				box = box.expand(p)
	assert_false(first, "the fixture's buildings have vertices")
	# The fixture is asymmetric enough that a corner or the lowest vertex is metres away.
	assert_gt(box.size.x, 1.0, "the bounds are wider than the tolerance (x)")
	assert_gt(box.size.y, 1.0, "the bounds are taller than the tolerance")
	assert_gt(box.size.z, 1.0, "the bounds are deeper than the tolerance (z)")
	var centre := box.get_center()
	var at := camera.position
	assert_almost_eq(at.x, centre.x, TOLERANCE_M, "over the centre of the bounds (x)")
	assert_almost_eq(at.z, centre.z, TOLERANCE_M, "over the centre of the bounds (z)")
	var start_y: float = box.end.y + Main.START_ABOVE_M
	assert_almost_eq(at.y, start_y, TOLERANCE_M, "START_ABOVE_M above the highest vertex")
