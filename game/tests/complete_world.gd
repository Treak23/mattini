extends RefCounted
## Test helper for the main scene's tests (briefs M2-05, M2-08; M3-14's full replacement): a
## complete world, every block the main scene reads, in one world, written into a folder
## under user://. Not a test script: GUT runs only scripts named test_*.
##
## - The terrain: the shared terrain fixture's manifest and heights (its world: origin
##   E 2'600'000 / N 1'200'000, height offset 1000 m, the owner's axes).
## - The buildings: one closed box, 2 m wide and BOX_HEIGHT tall, standing on the terrain's
##   centre, as the pinned test_main_scene_buildings.gd built it (brief M2-08: its floor
##   below the ground, its roof above).
## - The photo: the shared photo fixture's block and JPEG (80 x 40 texels at 0.2 m), its box
##   moved into this world's area at PHOTO_BOX (local rectangle PHOTO_RECT), its world_sha256
##   this world's.
## - The surfaces: the shared surfaces fixture's block and PNG (200 x 150 cells at 0.2 m), its
##   box moved to SURFACES_BOX (local SURFACES_RECT), its world_sha256 this world's.
## - The trees: the shared trees fixture's block and chunk files, its world_sha256 and box
##   this world's. Their local positions are the trees fixture's, written for that fixture's
##   world: here they stand beside and below this terrain, not on it.
## - The roofs: a block written here for the box, its colour ROOF.
## The three rectangles differ on purpose: the photo's is not the terrain grid's, and the
## surfaces' is neither. The moved boxes, the box, its roof colour and the trees' place are
## test data, invented here, not swisstopo's (Hard Rule 2).

const TERRAIN_FIXTURE := "tests/shared/terrain_fixture/generated/manifest.json"
const PHOTO_FIXTURE := "tests/shared/photo_fixture/generated/manifest.json"
const SURFACES_FIXTURE := "tests/shared/surfaces_fixture/generated/manifest.json"
const TREES_FIXTURE := "tests/shared/trees_fixture/generated/manifest.json"
const TILE := "2601-1199"
const CHUNK_FILE := "buildings/2601-1199.bin"
## The box's floor, local: at the fixture terrain's centre, 603 m (LN02 1603 m). The
## fixture's ground under the box lies from about 604.2 to 606.7 m (605.4 m at its middle),
## between the floor and the roof, as a building stands on its terrain (brief M2-08, M2 R1
## P-01: until then the box's roof lay 4 m under the ground).
const BOX_FLOOR := Vector3(1024.0, 603.0, 15.5)
## The box's height from its floor to its roof, in metres.
const BOX_HEIGHT := 6.0
## The photo's box in LV95: 16 m x 8 m (80 x 40 texels at 0.2 m), inside the terrain's area
## (E 2'601'015 - 2'601'035, N 1'199'978 - 1'199'989.5), 2 m east and 1 m south of its
## north-west corner.
const PHOTO_BOX := {"e_max": 2601033.0, "e_min": 2601017.0, "n_max": 1199988.5, "n_min": 1199980.5}
## The surfaces' box in LV95: 40 m x 30 m (200 x 150 cells at 0.2 m), over the terrain.
const SURFACES_BOX := {
	"e_max": 2601053.0, "e_min": 2601013.0, "n_max": 1199991.0, "n_min": 1199961.0
}
## The box's roof colour, sRGB, as the roofs block writes it.
const ROOF := "b4532a"
const ROOF_UUID := "{0F1E2D3C-4B5A-4978-8796-A5B4C3D2E1F0}"


static func repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


static func terrain_fixture_path() -> String:
	return repo_file(TERRAIN_FIXTURE)


## Writes the complete world into [param dir] (created if missing): manifest.json, the
## terrain's heights (the fixture's, or [param heights] when given), the box's chunk, the
## photo, the surfaces and the trees' chunks, with [param change] (a Callable taking the
## manifest Dictionary) applied last. Returns the manifest's path.
static func write(dir: String, change := Callable(), heights := PackedByteArray()) -> String:
	for folder in ["terrain", "buildings", "photo", "surfaces", "trees"]:
		DirAccess.make_dir_recursive_absolute(dir.path_join(folder))
	var source := terrain_fixture_path()
	var manifest := _parse(source)
	if heights.is_empty():
		heights = FileAccess.get_file_as_bytes(
			source.get_base_dir().path_join("terrain/fixture.f32")
		)
	_store(dir.path_join("terrain/fixture.f32"), heights)
	var chunk := box_chunk()
	_store(dir.path_join(CHUNK_FILE), chunk)
	var world_sha256: String = manifest["world_sha256"]
	var box: Dictionary = manifest["terrain"]["lv95_box"]
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
		"lv95_box": box,
		"source":
		{
			"attribution": "© swisstopo",
			"collection": "ch.swisstopo.swissbuildings3d_3_0",
			"dataset": "swissbuildings3d",
			"edition": "2020",
			"sheets": [{"sha256": "0".repeat(64), "sheet": "1166-44"}],
		},
		"world_sha256": world_sha256,
	}
	manifest["photo"] = _moved(PHOTO_FIXTURE, "photo", dir, PHOTO_BOX, world_sha256)
	manifest["surfaces"] = _moved(SURFACES_FIXTURE, "surfaces", dir, SURFACES_BOX, world_sha256)
	manifest["trees"] = _trees(dir, box, world_sha256)
	manifest["roofs"] = {
		"area": "fixture",
		"chunks":
		[
			{
				"buildings":
				[
					{
						"roof": ROOF,
						"roof_pixels": 37,
						"triangles": 12,
						"uuid": ROOF_UUID,
						"vertices": 8,
					}
				],
				"tile": TILE,
			}
		],
		"format": "roofs-v1",
		"lv95_box": box,
		"source":
		{
			"buildings": manifest["buildings"]["source"].duplicate(true),
			"photo": manifest["photo"]["source"].duplicate(true),
		},
		"world_sha256": world_sha256,
	}
	if change.is_valid():
		change.call(manifest)
	var path := dir.path_join("manifest.json")
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string(JSON.stringify(manifest, "  ", true, true))
	file.close()
	return path


## The block [param key] of the shared fixture at [param fixture], its file copied into
## [param dir], its box [param box] and its world_sha256 [param world_sha256].
static func _moved(
	fixture: String, key: String, dir: String, box: Dictionary, world_sha256: String
) -> Dictionary:
	var source := repo_file(fixture)
	var block: Dictionary = _parse(source)[key]
	var file: String = block["file"]
	_store(dir.path_join(file), FileAccess.get_file_as_bytes(source.get_base_dir().path_join(file)))
	block["lv95_box"] = box.duplicate()
	block["world_sha256"] = world_sha256
	return block


## The shared trees fixture's block, its chunk files copied into [param dir].
static func _trees(dir: String, box: Dictionary, world_sha256: String) -> Dictionary:
	var source := repo_file(TREES_FIXTURE)
	var block: Dictionary = _parse(source)["trees"]
	for entry: Dictionary in block["chunks"]:
		var file: String = entry["file"]
		var data := FileAccess.get_file_as_bytes(source.get_base_dir().path_join(file))
		_store(dir.path_join(file), data)
	block["lv95_box"] = box.duplicate()
	block["world_sha256"] = world_sha256
	return block


## One closed box, 2 m wide and BOX_HEIGHT tall, its floor's corner at BOX_FLOOR,
## counter-clockwise from outside as the pipeline writes: 8 vertices as float32 x, y, z, then
## 12 triangles as uint32.
static func box_chunk() -> PackedByteArray:
	var o := BOX_FLOOR
	var corners := [
		o,
		o + Vector3(2, 0, 0),
		o + Vector3(2, 0, 2),
		o + Vector3(0, 0, 2),
		o + Vector3(0, BOX_HEIGHT, 0),
		o + Vector3(2, BOX_HEIGHT, 0),
		o + Vector3(2, BOX_HEIGHT, 2),
		o + Vector3(0, BOX_HEIGHT, 2),
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


static func _parse(path: String) -> Dictionary:
	var json := JSON.new()
	json.parse(FileAccess.get_file_as_string(path))
	return json.data if typeof(json.data) == TYPE_DICTIONARY else {}


static func _store(path: String, data: PackedByteArray) -> void:
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_buffer(data)
	file.close()
