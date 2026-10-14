extends GutTest
## Pinning tests for brief M3-11: TreeLoader puts one conifer on every tree, at its base,
## sized by its height and crown radius, one MultiMesh per 250 m cell.
##
## Pinned decisions (m3-design §5 and §9, the trees): TreeLoader.create(chunks, parent) adds a
## Node3D named "Trees" holding one MultiMeshInstance3D per 250 m cell of local x and z that
## holds trees, named "<cx>_<cz>" with cx = floor(x / 250), cz = floor(z / 250) (the fixture's
## trees fall in 3_-1, 4_-1 and 3_0; its fourth cell, 4_0, holds none and has no node); each
## instance is the unit conifer at the tree's position from the file, unchanged, turned about
## +y only and scaled to (crown radius, height, crown radius): its basis' y column is
## (0, height, 0), its x and z columns horizontal, of length crown radius. The turn is a hash
## of the position, so the trees do not all face one way. Shadows are cast. The unit conifer:
## its top at y = 1, its widest at radius 1 from the axis, its trunk's foot below y = 0 (into
## sloping ground), at most 256 triangles (34'412 trees in the village, measured).
## Each cell's MultiMesh is filled through its `buffer`, 12 floats per instance (TRANSFORM_3D,
## no colours, no custom data): measured in Godot 4.6.3, the headless (dummy) RenderingServer
## keeps a buffer as set but drops set_instance_transform (get_instance_transform reads the
## identity), so the buffer is how a headless test sees the instances; and no colour or data
## rides on the instances (the renderers treat instance colour differently: m3-design §5 has
## the shader sample the photo instead). TreeLoader.TREES_NOTE is the credits' note, exactly
## as brief M3-11 writes it (M3-14 shows it under "Placeholders").
##
## Does NOT prove: that the trees render or look right (no GPU; the owner's PC is the visual
## test); the crown colour from the photo (test_tree_loader_photo.gd).

const MAX_TRIANGLES := 256
const TREES_NOTE := (
	"Trees: one generic conifer shape, placed and sized from swissSURFACE3D;"
	+ " the data gives no species."
)

var _chunks: TreeChunks
var _trees: Node3D


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


func _vectors() -> Dictionary:
	var json := JSON.new()
	var path := _repo_file("tests/shared/trees_vectors.json")
	assert_eq(json.parse(FileAccess.get_file_as_string(path)), OK, "the vectors parse")
	return json.data if typeof(json.data) == TYPE_DICTIONARY else {}


func before_all() -> void:
	var manifest := _repo_file("tests/shared/trees_fixture/generated/manifest.json")
	_chunks = TreeChunks.from_manifest(manifest, WorldConfig.from_manifest(manifest))
	if _chunks != null:
		_trees = TreeLoader.create(_chunks, self)


func after_all() -> void:
	if _trees != null:
		_trees.free()


func _cells() -> Dictionary:
	var by_name := {}
	if _trees != null:
		for child in _trees.get_children():
			by_name[String(child.name)] = child
	return by_name


## The instances' transforms from the MultiMesh's buffer (TRANSFORM_3D: per instance the rows
## of the 3 x 4 matrix, basis columns x, y, z then the origin).
func _transforms(multimesh: MultiMesh) -> Array[Transform3D]:
	var b := multimesh.buffer
	var found: Array[Transform3D] = []
	for k in b.size() / 12:
		var o := 12 * k
		var basis := Basis(
			Vector3(b[o], b[o + 4], b[o + 8]),
			Vector3(b[o + 1], b[o + 5], b[o + 9]),
			Vector3(b[o + 2], b[o + 6], b[o + 10])
		)
		found.append(Transform3D(basis, Vector3(b[o + 3], b[o + 7], b[o + 11])))
	return found


func test_one_multimesh_per_250_m_cell() -> void:
	assert_not_null(_trees, "the loader returns the Trees node")
	if _trees == null:
		return
	assert_eq(_trees.name, &"Trees")
	assert_eq(_trees.get_parent(), self, "added to the given parent")
	var cells := _cells()
	var names := cells.keys()
	names.sort()
	assert_eq(names, ["3_-1", "3_0", "4_-1"], "one node per cell that holds trees")
	var counts: Dictionary = _vectors()["cells"]
	var total := 0
	for cell_name: String in cells:
		var instance := cells[cell_name] as MultiMeshInstance3D
		assert_not_null(instance, "%s is a MultiMeshInstance3D" % cell_name)
		if instance == null:
			continue
		assert_eq(
			instance.multimesh.instance_count, int(counts[cell_name]), "%s: trees" % cell_name
		)
		assert_eq(instance.multimesh.transform_format, MultiMesh.TRANSFORM_3D)
		assert_eq(
			instance.multimesh.buffer.size(),
			12 * instance.multimesh.instance_count,
			"%s: the buffer holds 12 floats per tree, nothing else" % cell_name
		)
		assert_eq(
			instance.cast_shadow, GeometryInstance3D.SHADOW_CASTING_SETTING_ON, "casts shadows"
		)
		total += instance.multimesh.instance_count
	assert_eq(total, 19, "every tree once")


func test_every_named_tree_stands_at_its_position_scaled_to_its_size() -> void:
	var cells := _cells()
	var named: Array = _vectors()["trees"]
	assert_eq(named.size(), 19)
	var turns := {}
	for t: Dictionary in named:
		var instance := cells.get(t["cell"]) as MultiMeshInstance3D
		assert_not_null(instance, "%s: its cell %s" % [t["name"], t["cell"]])
		if instance == null:
			continue
		var local: Array = t["local"]
		var at := Vector3(local[0], local[1], local[2])
		var basis := Basis()
		var found := false
		for transform in _transforms(instance.multimesh):
			if transform.origin == at:
				basis = transform.basis
				found = true
		assert_true(found, "%s: an instance at the file's position, exactly" % t["name"])
		if not found:
			continue
		var height := float(t["height_m"])
		var radius := float(t["crown_radius_m"])
		assert_almost_eq(basis.y, Vector3(0.0, height, 0.0), Vector3.ONE * 1e-5 * height, t["name"])
		for column: Vector3 in [basis.x, basis.z]:
			assert_almost_eq(column.y, 0.0, 1e-5 * radius, "%s: turned about +y only" % t["name"])
			assert_almost_eq(column.length(), radius, 1e-5 * radius, "%s: crown radius" % t["name"])
		assert_almost_eq(basis.x.dot(basis.z), 0.0, 1e-4 * radius * radius, t["name"])
		turns[snappedf(atan2(basis.x.z, basis.x.x), 0.001)] = true
	assert_gt(turns.size(), 9, "the turns differ from tree to tree")


func test_the_conifer_is_the_unit_tree() -> void:
	var cells := _cells()
	assert_false(cells.is_empty(), "the loader made cells")
	if cells.is_empty():
		return
	var mesh: Mesh = (cells.values()[0] as MultiMeshInstance3D).multimesh.mesh
	assert_not_null(mesh, "the cells draw a mesh")
	if mesh == null:
		return
	var top := -INF
	var foot := INF
	var widest := 0.0
	var triangles := 0
	for s in mesh.get_surface_count():
		var arrays := mesh.surface_get_arrays(s)
		var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var indices: Variant = arrays[Mesh.ARRAY_INDEX]
		triangles += (vertices.size() if indices == null else indices.size()) / 3
		for v in vertices:
			top = maxf(top, v.y)
			foot = minf(foot, v.y)
			widest = maxf(widest, Vector2(v.x, v.z).length())
	assert_almost_eq(top, 1.0, 1e-5, "height 1: the top at y = 1")
	assert_almost_eq(widest, 1.0, 1e-5, "crown radius 1")
	assert_lt(foot, 0.0, "the trunk's foot reaches below the base")
	assert_between(triangles, 1, MAX_TRIANGLES, "at most %d triangles" % MAX_TRIANGLES)


func test_the_credits_note_says_the_conifer_is_generic() -> void:
	# Read from the script's constants, so a loader without the note fails here by name.
	var loader: Script = load("res://scripts/trees/tree_loader.gd")
	assert_not_null(loader, "the loader's script loads")
	if loader != null:
		var note: Variant = loader.get_script_constant_map().get("TREES_NOTE")
		assert_eq(note, TREES_NOTE, "TreeLoader.TREES_NOTE, as the brief writes it")
