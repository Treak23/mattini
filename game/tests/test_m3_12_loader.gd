extends GutTest
## Brief M3-12's own tests: what BuildingLoader draws with and without roof colours, and the
## check that colours belong to the chunks they are given with.
##
## The pinned tests read each named triangle and every triangle of the shared roofs fixture.
## This one counts: the surfaces a mesh gets, how many triangles each holds, and that the
## walls do not depend on the colours. roofs_problem is the check that a BuildingRoofs
## object describes the BuildingChunks it is given with; create prints it as an ERROR line
## (not tested here: the gate's allowlist holds the pinned line only, brief M3-12 decision 5).
##
## Does NOT prove: that anything renders or looks right (no GPU); that create refuses a
## roofs object that does not fit (it calls roofs_problem, which is tested).

const MANIFEST := "tests/shared/roofs_fixture/generated/manifest.json"

var _chunks: BuildingChunks
var _roofs: BuildingRoofs
var _with: Node3D
var _without: Node3D


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


func before_all() -> void:
	var path := _repo_file(MANIFEST)
	var world := WorldConfig.from_manifest(path)
	_chunks = BuildingChunks.from_manifest(path, world)
	if _chunks != null:
		_roofs = BuildingRoofs.from_manifest(path, world, _chunks)
	if _roofs != null:
		_with = BuildingLoader.create(_chunks, self, _roofs)
		_without = BuildingLoader.create(_chunks, self)


func after_all() -> void:
	for node in [_with, _without]:
		if node != null:
			node.free()


## The triangle count of each named surface of the chunk [param i] under [param buildings],
## as {name: count}.
func _surface_triangles(buildings: Node3D, i: int) -> Dictionary:
	var mesh := (buildings.get_child(i) as MeshInstance3D).mesh as ArrayMesh
	var counts := {}
	for s in mesh.get_surface_count():
		var arrays := mesh.surface_get_arrays(s)
		counts[mesh.surface_get_name(s)] = (
			(arrays[Mesh.ARRAY_VERTEX] as PackedVector3Array).size() / 3
		)
	return counts


## How many of the chunk [param i]'s triangles are roof (normal.y >= 0.5), and how many of
## those belong to a building with a colour, counted from the file and the colours.
func _expected(i: int) -> Dictionary:
	var chunk: Dictionary = _chunks.chunks[i]
	var positions: PackedVector3Array = chunk["positions"]
	var indices: PackedInt32Array = chunk["indices"]
	var walls := 0
	var neutral := 0
	var coloured := 0
	var t := 0
	for building: Dictionary in _roofs.chunks[i]["buildings"]:
		for k in building["triangles"]:
			var a := positions[indices[3 * t]]
			var b := positions[indices[3 * t + 1]]
			var c := positions[indices[3 * t + 2]]
			t += 1
			if (b - a).cross(c - a).normalized().y < 0.5:
				walls += 1
			elif building["roof"] == null:
				neutral += 1
			else:
				coloured += 1
	return {"walls": walls, "roofs": neutral, "roofs_photo": coloured}


func test_the_fixture_has_every_kind_of_triangle() -> void:
	var totals := {"walls": 0, "roofs": 0, "roofs_photo": 0}
	for i in _chunks.chunks.size():
		var expected := _expected(i)
		for key: String in totals:
			totals[key] += expected[key]
	for key: String in totals:
		assert_gt(totals[key], 0, "the fixture has %s triangles, or this test sees nothing" % key)


func test_each_surface_holds_the_triangles_of_its_kind() -> void:
	assert_not_null(_with, "the fixture is loaded with roof colours")
	if _with == null:
		return
	for i in _chunks.chunks.size():
		var expected := _expected(i)
		var found := _surface_triangles(_with, i)
		for key: String in expected:
			assert_eq(
				found.get(key, 0),
				expected[key],
				"%s: %s triangles" % [_chunks.chunks[i]["tile"], key]
			)
		for key: String in found:
			assert_true(
				expected.has(key), "%s: no surface named %s" % [_chunks.chunks[i]["tile"], key]
			)


func test_without_roof_colours_no_roof_is_coloured() -> void:
	assert_not_null(_without, "the fixture is loaded without roof colours")
	if _without == null:
		return
	for i in _chunks.chunks.size():
		var expected := _expected(i)
		var found := _surface_triangles(_without, i)
		assert_eq(found.get("walls", 0), expected["walls"], "walls, as with colours")
		assert_eq(
			found.get("roofs", 0),
			expected["roofs"] + expected["roofs_photo"],
			"every roof is the neutral roof"
		)
		assert_false(found.has("roofs_photo"), "no coloured surface")


func test_the_colours_belong_to_the_chunks() -> void:
	assert_eq(BuildingLoader.roofs_problem(_chunks, _roofs), "", "the fixture's own colours fit")
	var other := BuildingRoofs.new()
	other.chunks = _roofs.chunks.duplicate(true)
	other.chunks.reverse()
	assert_ne(BuildingLoader.roofs_problem(_chunks, other), "", "chunks in another order")
	other.chunks = _roofs.chunks.slice(1)
	assert_ne(BuildingLoader.roofs_problem(_chunks, other), "", "a chunk less")
	other.chunks = _roofs.chunks.duplicate(true)
	other.chunks[2]["buildings"][0]["triangles"] += 1
	var problem := BuildingLoader.roofs_problem(_chunks, other)
	assert_true(
		problem.contains(_chunks.chunks[2]["tile"]), "a triangle more names the tile: %s" % problem
	)
