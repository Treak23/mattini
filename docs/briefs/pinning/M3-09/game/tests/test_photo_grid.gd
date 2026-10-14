extends GutTest
## Pinning tests for brief M3-09: PhotoGrid reads the manifest's photo block and its JPEG,
## checked, decoded and placed through WorldConfig.
##
## Pinned decisions (m3-design §2 and §9, the photo): the shared fixture
## (tests/shared/photo_fixture/generated/, designed in tests/shared/photo_vectors.json) is
## read as the pipeline writes it: 80 columns by 40 rows of 0.2 m texels; the rectangle's
## north-west corner is WorldConfig.to_local(e_min, n_max, h), local x 412.5 and z -215.0
## (never an origin subtracted here), 16 m wide along +x and 8 m deep along +z, and rect()
## is (x0, z0, width_m, depth_m). The JPEG decodes with Image.load_jpg_from_buffer to RGB8
## of exactly columns × rows, image row 0 at the north edge, and the texture holds it with
## mipmaps. With the shader's rule uv = ((x, z) - (x0, z0)) / (width_m, depth_m) and texel
## (floor(u · columns), floor(v · rows)), every named world point lands on its texel and
## reads the designed value within the vectors' tolerance (measured: Godot 4.6.3 decodes
## every texel there exactly). The points sit on both sides of block edges, so half a
## texel or one texel off, a north-south or east-west flip, swapped axes or the south-west
## corner as origin read another block (the vectors list which points catch which).
## Refused, with one push_error naming the manifest and a null result: only the owner's
## axes (x = +e, y = +h, z = -n) are accepted; a block whose key set is not exact, whose
## world_sha256 is not the manifest's, whose columns × cell or rows × cell is not the box;
## a JPEG that is missing, not the block's SHA-256, or of another decoded size. The
## refusals the owner fixes by running the pipeline name the command.

const SCRATCH_DIR := "user://test_photo_grid"
const PHOTO_COMMAND := "python -m mattini photo"

var _cases := 0


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


func _fixture_manifest_path() -> String:
	return _repo_file("tests/shared/photo_fixture/generated/manifest.json")


func _fixture_jpeg() -> PackedByteArray:
	return FileAccess.get_file_as_bytes(
		_repo_file("tests/shared/photo_fixture/generated/photo/fixture.jpg")
	)


func _vectors() -> Dictionary:
	var text := FileAccess.get_file_as_string(_repo_file("tests/shared/photo_vectors.json"))
	var json := JSON.new()
	assert_eq(json.parse(text), OK, "the shared photo vectors parse")
	return json.data


func _fixture_manifest() -> Dictionary:
	var json := JSON.new()
	assert_eq(json.parse(FileAccess.get_file_as_string(_fixture_manifest_path())), OK)
	return json.data


func after_all() -> void:
	_remove_tree(SCRATCH_DIR)


func _remove_tree(dir: String) -> void:
	for sub in DirAccess.get_directories_at(dir):
		_remove_tree(dir.path_join(sub))
	for file in DirAccess.get_files_at(dir):
		DirAccess.remove_absolute(dir.path_join(file))
	DirAccess.remove_absolute(dir)


## Writes a manifest and (unless jpeg is null) photo/fixture.jpg into a fresh folder under
## SCRATCH_DIR, laid out like the generated folder; returns the manifest's path.
func _write_case(manifest: Dictionary, jpeg: Variant) -> String:
	_cases += 1
	var dir := SCRATCH_DIR.path_join("case_%d" % _cases)
	DirAccess.make_dir_recursive_absolute(dir.path_join("photo"))
	var path := dir.path_join("manifest.json")
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string(JSON.stringify(manifest, "  ", true, true))
	file.close()
	if jpeg != null:
		var data := FileAccess.open(dir.path_join("photo/fixture.jpg"), FileAccess.WRITE)
		data.store_buffer(jpeg)
		data.close()
	return path


## The photo a case manifest yields, read with the world block of that same manifest.
func _read(path: String) -> PhotoGrid:
	var world := WorldConfig.from_manifest(path)
	assert_not_null(world, "the case's world block itself is valid: %s" % path)
	return PhotoGrid.from_manifest(path, world)


## Asserts one push_error naming the manifest (and containing needle, when given).
func _assert_refused(path: String, grid: PhotoGrid, why: String, needle := "") -> void:
	assert_null(grid, "%s is refused" % why)
	var found := false
	for error in get_errors():
		if (
			not found
			and not error.handled
			and error.is_push_error()
			and error.contains_text(path)
			and (needle == "" or error.contains_text(needle))
		):
			error.handled = true
			found = true
	assert_true(found, "%s: one push_error names %s %s" % [why, path, needle])


func _sha256(data: PackedByteArray) -> String:
	var context := HashingContext.new()
	context.start(HashingContext.HASH_SHA256)
	context.update(data)
	return context.finish().hex_encode()


func test_the_fixture_photo_is_read_as_designed() -> void:
	var world := WorldConfig.from_manifest(_fixture_manifest_path())
	var grid := PhotoGrid.from_manifest(_fixture_manifest_path(), world)
	assert_not_null(grid, "the fixture photo is read")
	if grid == null:
		return
	var expected: Dictionary = _vectors()["grid"]
	assert_eq(grid.area, "fixture")
	assert_eq(grid.cell_m, float(expected["cell_m"]))
	assert_eq(grid.columns, int(expected["columns"]))
	assert_eq(grid.rows, int(expected["rows"]))
	assert_eq(grid.x0, float(expected["x0"]), "the north-west corner lies at local x 412.5")
	assert_eq(grid.z0, float(expected["z0"]), "the north-west corner lies at local z -215.0")
	assert_eq(grid.width_m, float(expected["width_m"]))
	assert_eq(grid.depth_m, float(expected["depth_m"]))
	var r: Array = expected["rect"]
	assert_eq(grid.rect(), Vector4(r[0], r[1], r[2], r[3]))
	assert_eq(grid.dataset, "swissimage")
	assert_eq(grid.edition, "2023")
	assert_eq(grid.attribution, "© swisstopo")
	assert_not_null(grid.texture, "the photo is a texture")
	if grid.texture == null:
		return
	assert_eq(grid.texture.get_size(), Vector2(80, 40))
	var image := grid.texture.get_image()
	assert_eq(image.get_format(), Image.FORMAT_RGB8)
	assert_true(image.has_mipmaps(), "the texture has mipmaps")


func test_the_named_points_read_their_texels() -> void:
	var world := WorldConfig.from_manifest(_fixture_manifest_path())
	var grid := PhotoGrid.from_manifest(_fixture_manifest_path(), world)
	assert_not_null(grid, "the fixture photo is read")
	if grid == null:
		return
	var vectors := _vectors()
	var tolerance := int(vectors["tolerance"])
	var image := grid.texture.get_image()
	for p: Dictionary in vectors["points"]:
		var name: String = p["name"]
		var local := world.to_local(p["lv95"][0], p["lv95"][1], world.height_offset)
		assert_eq(local.x, float(p["local_xz"][0]), "%s: local x" % name)
		assert_eq(local.z, float(p["local_xz"][1]), "%s: local z" % name)
		var u := (local.x - grid.x0) / grid.width_m
		var v := (local.z - grid.z0) / grid.depth_m
		var column := floori(u * grid.columns)
		var row := floori(v * grid.rows)
		assert_eq([column, row], [int(p["texel"][0]), int(p["texel"][1])], "%s: texel" % name)
		var colour := image.get_pixel(column, row)
		var found := [roundi(colour.r * 255.0), roundi(colour.g * 255.0), roundi(colour.b * 255.0)]
		for channel in 3:
			var wanted := int(p["rgb"][channel])
			assert_almost_eq(found[channel], wanted, tolerance, "%s: channel %d" % [name, channel])


func test_a_rotated_world_is_refused() -> void:
	# A proper rotation WorldConfig accepts; the photo is defined for x=+e, y=+h, z=-n.
	var manifest := _fixture_manifest()
	manifest["world"]["axes"] = {"x": "+n", "y": "+h", "z": "+e"}
	var path := _write_case(manifest, _fixture_jpeg())
	_assert_refused(path, _read(path), "a world rotated about the vertical")


func test_a_manifest_without_a_photo_names_the_command() -> void:
	var manifest := _fixture_manifest()
	manifest["photo"] = null
	var path := _write_case(manifest, null)
	_assert_refused(path, _read(path), "a manifest whose photo is null", PHOTO_COMMAND)


func test_a_photo_built_for_another_world_names_the_command() -> void:
	var manifest := _fixture_manifest()
	manifest["photo"]["world_sha256"] = "0".repeat(64)
	var path := _write_case(manifest, _fixture_jpeg())
	_assert_refused(path, _read(path), "a photo built for another world config", PHOTO_COMMAND)


func test_malformed_photo_blocks_are_refused() -> void:
	var cases := {
		"a block with a key more": func(b: Dictionary) -> void: b["note"] = "x",
		"a block without pixels_sha256": func(b: Dictionary) -> void: b.erase("pixels_sha256"),
		# The JPEG still decodes to columns x rows: only the box check can refuse it.
		"a box half a metre wider than columns x cell":
		func(b: Dictionary) -> void: b["lv95_box"]["e_max"] = 2610429.0,
		"rows and columns swapped": func(b: Dictionary) -> void: b["columns"] = 40,
		"a cell that is not 0.2, 0.5 or 1 m": func(b: Dictionary) -> void: b["cell_m"] = 0.25,
		"a file outside the manifest's folder":
		func(b: Dictionary) -> void: b["file"] = "../photo/fixture.jpg",
	}
	for why: String in cases:
		var manifest := _fixture_manifest()
		(cases[why] as Callable).call(manifest["photo"])
		var path := _write_case(manifest, _fixture_jpeg())
		_assert_refused(path, _read(path), why)


func test_jpegs_that_do_not_match_are_refused() -> void:
	var changed := _fixture_jpeg()
	changed[300] = changed[300] ^ 1
	var cases := {"a missing JPEG": null, "a JPEG with one bit changed": changed}
	for why: String in cases:
		var path := _write_case(_fixture_manifest(), cases[why])
		_assert_refused(path, _read(path), why)
	# A valid JPEG whose SHA-256 the block names, 40 x 80 instead of 80 x 40: only the
	# decoded size can refuse it.
	var other := Image.create_empty(40, 80, false, Image.FORMAT_RGB8)
	other.fill(Color(0.5, 0.5, 0.5))
	var jpeg := other.save_jpg_to_buffer(0.92)
	var manifest := _fixture_manifest()
	manifest["photo"]["sha256"] = _sha256(jpeg)
	var path := _write_case(manifest, jpeg)
	_assert_refused(path, _read(path), "a JPEG of another size")
