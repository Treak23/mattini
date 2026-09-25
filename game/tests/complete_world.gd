extends RefCounted
## Test helper for the main scene's tests (brief M2-05): a complete world, the shared terrain
## fixture's manifest and heights plus a buildings block for one closed 2 m box standing at
## the terrain's centre, in the same world, written into a folder under user://. The shared
## terrain fixture has no buildings (its manifest says "buildings": null), so a main-scene
## test that means "everything is there" reads this world; a test that means "no buildings"
## says so. Built as the pinned test_main_scene_buildings.gd builds its world. The box is
## test data, invented here, not swisstopo's (Hard Rule 2). Not a test script: GUT runs only
## scripts named test_*.

const TERRAIN_FIXTURE := "tests/shared/terrain_fixture/generated/manifest.json"
const TILE := "2601-1199"
const CHUNK_FILE := "buildings/2601-1199.bin"
## The box's floor, local: at the fixture terrain's centre, 599 m (LN02 1599 m).
const BOX_FLOOR := Vector3(1024.0, 599.0, 15.5)


static func repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


static func terrain_fixture_path() -> String:
	return repo_file(TERRAIN_FIXTURE)


## Writes the complete world into [param dir] (created if missing): manifest.json, the
## terrain's heights (the fixture's, or [param heights] when given) and the box's chunk,
## with [param change] (a Callable taking the manifest Dictionary) applied last. Returns
## the manifest's path.
static func write(dir: String, change := Callable(), heights := PackedByteArray()) -> String:
	DirAccess.make_dir_recursive_absolute(dir.path_join("terrain"))
	DirAccess.make_dir_recursive_absolute(dir.path_join("buildings"))
	var source := terrain_fixture_path()
	var json := JSON.new()
	json.parse(FileAccess.get_file_as_string(source))
	var manifest: Dictionary = json.data
	if heights.is_empty():
		heights = FileAccess.get_file_as_bytes(
			source.get_base_dir().path_join("terrain/fixture.f32")
		)
	_store(dir.path_join("terrain/fixture.f32"), heights)
	var chunk := box_chunk()
	_store(dir.path_join(CHUNK_FILE), chunk)
	manifest["buildings"] = {
		"area": "fixture",
		"chunks":
		[
			{
				"buildings": 1,
				"file": CHUNK_FILE,
				"sha256": sha256(chunk),
				"tile": TILE,
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


## One closed box, 2 m wide, its floor's corner at BOX_FLOOR, counter-clockwise from outside
## as the pipeline writes: 8 vertices as float32 x, y, z, then 12 triangles as uint32.
static func box_chunk() -> PackedByteArray:
	var o := BOX_FLOOR
	var corners := [
		o,
		o + Vector3(2, 0, 0),
		o + Vector3(2, 0, 2),
		o + Vector3(0, 0, 2),
		o + Vector3(0, 2, 0),
		o + Vector3(2, 2, 0),
		o + Vector3(2, 2, 2),
		o + Vector3(0, 2, 2),
	]
	# Each face as two triangles whose right-hand normal points out of the box: bottom (-y),
	# top (+y), the sides facing -z, +z, -x and +x.
	var triangles := [
		[0, 1, 2],
		[0, 2, 3],
		[4, 7, 6],
		[4, 6, 5],
		[0, 4, 5],
		[0, 5, 1],
		[3, 2, 6],
		[3, 6, 7],
		[0, 3, 7],
		[0, 7, 4],
		[1, 5, 6],
		[1, 6, 2],
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


static func sha256(data: PackedByteArray) -> String:
	var context := HashingContext.new()
	context.start(HashingContext.HASH_SHA256)
	context.update(data)
	return context.finish().hex_encode()


## Removes [param dir] and everything under it.
static func remove_tree(dir: String) -> void:
	for sub in DirAccess.get_directories_at(dir):
		remove_tree(dir.path_join(sub))
	for file in DirAccess.get_files_at(dir):
		DirAccess.remove_absolute(dir.path_join(file))
	DirAccess.remove_absolute(dir)


static func _store(path: String, data: PackedByteArray) -> void:
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_buffer(data)
	file.close()
