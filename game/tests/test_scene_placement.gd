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
## Since brief M3-R1-fix-1 (M3 review R1, P-02): the same for the trees. The Trees node and
## every cell's MultiMeshInstance3D sit at the scene's origin, unturned and unscaled, which the
## tree shader depends on (it reads each instance's origin in world space against the photo's
## rectangle), and in the complete world each tree stands where CompleteWorld.tree_records puts
## it, its base on Terrain3D's ground (main._ground_height) within 1 mm. The instances are read
## from the MultiMesh buffers (brain.md H25: headless, set_instance_transform is dropped but an
## assigned buffer is kept), the very bytes the renderer is given.
##
## Since brief v0.4.0-08 (M4-10's replacement of this file, cut to the sky; only this paragraph
## and the reader absorbed change): the main scene also reads the sky block, which the shared
## buildings fixture holds as null ("sky": null, brief v0.4.0-07), so SkySite's refusal of it is
## absorbed as the others' are.
##
## Since brief v0.5.0-05 (M4-10's replacement of this file, cut to the capture mask; only this
## paragraph and the reader absorbed change): the main scene also reads the capture mask, which
## the shared buildings fixture holds as null ("shadows": null, brief v0.5.0-02), so
## CaptureShadowGrid's refusal of it is absorbed as the others' are.
##
## Does NOT prove: that anything renders or looks right (no GPU); that the real village's
## buildings meet its terrain (measured at M2 planning and by the review, SPEC §8); that the real
## village's 34'412 trees stand on its ground (the placement lens measured 0 of them more than
## 5 cm off, one clone, at the 0.5 m terrain; at the 1 m or 2 m terrain they do not, M3 R1 P-01,
## which is design's); that the tree shader draws a tree where its buffer row says.

const CompleteWorld := preload("res://tests/complete_world.gd")
const Main := preload("res://scripts/main.gd")
const TOLERANCE_M := 0.01
const SCRATCH_DIR := "user://test_scene_placement"
const DEPRECATION := "instance_reset_physics_interpolation() is deprecated"
## The readers whose refusals of the buildings fixture (it holds only buildings) are expected.
const ABSENT_BLOCKS := [
	"TerrainGrid: ",
	"PhotoGrid: ",
	"SurfaceGrid: ",
	"TreeChunks: ",
	"BuildingRoofs: ",
	"CaptureShadowGrid: ",
	"SkySite: ",
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


## The tree instances of [param trees]: the origin of every buffer row of every cell, in scene
## coordinates (the cell's global transform applied: a moved node shows).
func _tree_origins(trees: Node3D) -> PackedVector3Array:
	var origins := PackedVector3Array()
	for cell in trees.get_children():
		var buffer: PackedFloat32Array = (cell as MultiMeshInstance3D).multimesh.buffer
		# Twelve floats per instance: the transform's three rows of four, the origin last.
		for i in buffer.size() / 12:
			origins.append(
				(
					(cell as Node3D).global_transform
					* Vector3(buffer[12 * i + 3], buffer[12 * i + 7], buffer[12 * i + 11])
				)
			)
	return origins


func test_the_trees_sit_at_the_scene_origin() -> void:
	var main := _main_with(_complete_world())
	var trees: Node3D = main.get_node_or_null("Trees")
	assert_not_null(trees, "the trees are built")
	if trees == null:
		return
	assert_eq(trees.global_transform, Transform3D.IDENTITY, "the Trees node")
	assert_gt(trees.get_child_count(), 0, "at least one cell")
	for cell in trees.get_children():
		assert_eq((cell as Node3D).global_transform, Transform3D.IDENTITY, "cell %s" % cell.name)


func test_every_tree_stands_on_the_terrain_where_the_fixture_put_it() -> void:
	var path := _complete_world()
	var main := _main_with(path)
	var trees: Node3D = main.get_node_or_null("Trees")
	assert_not_null(trees, "the trees are built")
	if trees == null:
		return
	var manifest := CompleteWorld.read_manifest(path)
	var heights := FileAccess.get_file_as_bytes(
		CompleteWorld.terrain_fixture_path().get_base_dir().path_join("terrain/fixture.f32")
	)
	var records := CompleteWorld.tree_records(
		manifest["terrain"], WorldConfig.from_manifest(path), heights
	)
	var origins := _tree_origins(trees)
	assert_eq(origins.size(), CompleteWorld.TREES.size(), "one instance per tree of the fixture")
	assert_eq(records.size(), 5 * CompleteWorld.TREES.size(), "five floats per tree")
	for k in records.size() / 5:
		var x := records[5 * k]
		var z := records[5 * k + 2]
		var ground: float = main._ground_height(x, z)
		assert_false(is_nan(ground), "tree %d: the terrain is under it" % k)
		# The fixture's own rule (the mean of the pixel's four vertices) is Terrain3D's height.
		assert_almost_eq(records[5 * k + 1], ground, 0.001, "tree %d: the fixture stands on it" % k)
		var nearest := INF
		for origin in origins:
			nearest = minf(nearest, origin.distance_to(Vector3(x, ground, z)))
		assert_lt(
			nearest, 0.001, "tree %d: an instance's base is at (%f, %f, %f)" % [k, x, ground, z]
		)


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
