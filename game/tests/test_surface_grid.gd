extends GutTest
## Pinning tests for brief M3-10: SurfaceGrid reads the manifest's surfaces block and its
## class PNG, checked, and places the rectangle through WorldConfig.
##
## Pinned decisions (m3-design §4 "Game" and §9; brief M3-06's PNG): the shared surfaces
## fixture (tests/shared/surfaces_fixture/generated/, its vectors in
## tests/shared/surfaces_vectors.json, computed by design two independent ways) is read as
## the pipeline writes it: a PNG of 8-bit greyscale, filter 0 on every row, written by the
## pipeline's own stdlib writer, which Godot decodes natively (Image.load_png_from_buffer
## gives FORMAT_L8); 200 columns by 150 rows at 0.2 m, rows north to south, values 0 none,
## 1 rock, 2 water, 3 path, 4 road; its decoded bytes' SHA-256 is the block's pixels_sha256.
## The rectangle's north-west corner is WorldConfig.to_local(e_min, n_max) (x0 12.0,
## z0 -1.0 here, never an origin subtracted in this reader); only the owner's axes are
## accepted. class_at(x, z) gives the class of the texel holding the local point: column
## floor((x - x0) / cell_m), row floor((z - z0) / cell_m); the rectangle is half-open (its
## west and north edges in, its east and south edges out) and a point outside it gives -1.
## Every problem is refused with one push_error naming the manifest and a null result,
## never a plausible grid (Hard Rule 2); the refusals the owner fixes by re-running the
## pipeline name `python -m mattini surfaces`.
##
## Since brief M3-R1-fix-1 (M3 review R1, P-03): the texture's bytes are compared with the class
## bytes, row by row (a texture made after a flip drew every class mirrored with these tests
## green).
##
## Does NOT prove: that the terrain shader samples the texture on the right texel (no GPU;
## the owner's PC does: test_m3_09_photo_shader.gd pins the shader's expressions as text only);
## that the real village's PNG reads the same way (the main scene's headless run does, as for
## the terrain).

const SCRATCH_DIR := "user://test_surface_grid"
const SURFACES_COMMAND := "python -m mattini surfaces"
const FIXTURE_DIR := "tests/shared/surfaces_fixture/generated"

var _cases := 0


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


func _manifest_path() -> String:
	return _repo_file(FIXTURE_DIR.path_join("manifest.json"))


func _parse(path: String) -> Dictionary:
	var json := JSON.new()
	assert_eq(json.parse(FileAccess.get_file_as_string(path)), OK, "%s parses" % path)
	return json.data if typeof(json.data) == TYPE_DICTIONARY else {}


func _vectors() -> Dictionary:
	return _parse(_repo_file("tests/shared/surfaces_vectors.json"))


func _fixture_png() -> PackedByteArray:
	return FileAccess.get_file_as_bytes(_repo_file(FIXTURE_DIR.path_join("surfaces/fixture.png")))


func _read_fixture() -> SurfaceGrid:
	return SurfaceGrid.from_manifest(_manifest_path(), WorldConfig.from_manifest(_manifest_path()))


func after_all() -> void:
	_remove_tree(SCRATCH_DIR)


func _remove_tree(dir: String) -> void:
	for sub in DirAccess.get_directories_at(dir):
		_remove_tree(dir.path_join(sub))
	for file in DirAccess.get_files_at(dir):
		DirAccess.remove_absolute(dir.path_join(file))
	DirAccess.remove_absolute(dir)


func _sha256(data: PackedByteArray) -> String:
	var context := HashingContext.new()
	context.start(HashingContext.HASH_SHA256)
	context.update(data)
	return context.finish().hex_encode()


func test_godot_decodes_the_pipeline_s_png_natively() -> void:
	var block: Dictionary = _parse(_manifest_path())["surfaces"]
	var image := Image.new()
	assert_eq(image.load_png_from_buffer(_fixture_png()), OK, "Godot decodes the stdlib PNG")
	assert_eq(image.get_format(), Image.FORMAT_L8, "8-bit greyscale decodes to L8")
	assert_eq(image.get_size(), Vector2i(200, 150))
	var pixels := image.get_data()
	assert_eq(_sha256(pixels), block["pixels_sha256"], "the decoded bytes are the pipeline's")
	assert_eq(_sha256(pixels), _vectors()["pixels_sha256"]["0.2"], "and design's")


func test_the_fixture_grid_is_read_as_designed() -> void:
	var grid := _read_fixture()
	assert_not_null(grid, "the fixture's surfaces are read")
	if grid == null:
		return
	assert_eq(grid.area, "fixture")
	assert_eq(grid.dataset, "swisstlm3d")
	assert_eq(grid.edition, "2026-02")
	assert_eq(grid.attribution, "© swisstopo")
	assert_eq([grid.columns, grid.rows, grid.cell_m], [200, 150, 0.2])
	assert_eq([grid.x0, grid.z0], [12.0, -1.0], "the north-west corner, through WorldConfig")
	assert_almost_eq(grid.width_m, 40.0, 1e-9)
	assert_almost_eq(grid.depth_m, 30.0, 1e-9)
	assert_almost_eq(grid.rect(), Vector4(12.0, -1.0, 40.0, 30.0), Vector4.ONE * 1e-6)
	assert_not_null(grid.texture, "an ImageTexture of the classes")
	if grid.texture != null:
		assert_eq(grid.texture.get_size(), Vector2(200, 150))
		assert_eq(grid.texture.get_format(), Image.FORMAT_L8)


func test_the_texture_holds_the_class_bytes_row_by_row() -> void:
	# The shader reads the texture; class_at and the reader's tests read the decoded bytes. Two
	# copies of the classes that nothing compared: a texture made from the image after a flip
	# (M3 review R1, P-03, GM-surf-texture-flip) draws every class mirrored on the terrain
	# while class_at, the PNG's hash and the size and format checks all stay right.
	var block: Dictionary = _parse(_manifest_path())["surfaces"]
	var grid := _read_fixture()
	assert_not_null(grid, "the fixture's surfaces are read")
	if grid == null or grid.texture == null:
		return
	var image := grid.texture.get_image()
	assert_eq(image.get_format(), Image.FORMAT_L8, "the texture holds L8 bytes")
	var bytes := image.get_data()
	assert_eq(bytes.size(), grid.columns * grid.rows, "one byte per texel")
	assert_eq(_sha256(bytes), block["pixels_sha256"], "the texture's bytes are the decoded bytes")
	var first_wrong := -1
	for r in grid.rows:
		for c in grid.columns:
			var at := grid.class_at(
				grid.x0 + (c + 0.5) * grid.cell_m, grid.z0 + (r + 0.5) * grid.cell_m
			)
			if bytes[r * grid.columns + c] != at and first_wrong < 0:
				first_wrong = r
	assert_eq(
		first_wrong, -1, "every texel's byte is class_at's class at its centre (first wrong row)"
	)


func test_every_named_point_has_its_class() -> void:
	var grid := _read_fixture()
	var world := WorldConfig.from_manifest(_manifest_path())
	assert_not_null(grid, "the fixture's surfaces are read")
	if grid == null:
		return
	var points: Array = _vectors()["points"]
	assert_gt(points.size(), 40, "the vectors name points of every class and case")
	var seen := {}
	for p: Dictionary in points:
		var local: Array = p["local"]
		assert_eq(grid.class_at(local[0], local[1]), int(p["class"]), p["name"])
		seen[int(p["class"])] = true
		# The seam: the vectors' local point is the world config's (Hard Rule 4).
		var lv95: Array = p["lv95"]
		var placed := world.to_local(lv95[0], lv95[1], world.height_offset)
		var placed_xz := Vector2(placed.x, placed.z)
		assert_almost_eq(placed_xz, Vector2(local[0], local[1]), Vector2.ONE * 1e-4, p["name"])
	assert_eq(seen.size(), 5, "points of all five classes")


func test_the_rectangle_is_half_open_and_outside_is_minus_one() -> void:
	var grid := _read_fixture()
	assert_not_null(grid, "the fixture's surfaces are read")
	if grid == null:
		return
	for p: Dictionary in _vectors()["inside_edges"]:
		var local: Array = p["local"]
		assert_eq(grid.class_at(local[0], local[1]), int(p["class"]), p["name"])
	for p: Dictionary in _vectors()["outside"]:
		var local: Array = p["local"]
		assert_eq(grid.class_at(local[0], local[1]), -1, p["name"])


## Writes a copy of the fixture's generated folder whose manifest is changed by
## [param change] (a Callable taking the manifest Dictionary) and whose PNG is
## [param png] (null leaves it out; an empty array keeps the fixture's); returns its path.
func _write_case(change: Callable, png: Variant = PackedByteArray()) -> String:
	_cases += 1
	var dir := SCRATCH_DIR.path_join("case_%d" % _cases)
	DirAccess.make_dir_recursive_absolute(dir.path_join("surfaces"))
	var manifest := _parse(_manifest_path())
	change.call(manifest)
	var out := FileAccess.open(dir.path_join("manifest.json"), FileAccess.WRITE)
	out.store_string(JSON.stringify(manifest, "  ", true, true))
	out.close()
	if png != null:
		var bytes: PackedByteArray = png if not png.is_empty() else _fixture_png()
		var file := FileAccess.open(dir.path_join("surfaces/fixture.png"), FileAccess.WRITE)
		file.store_buffer(bytes)
		file.close()
	return dir.path_join("manifest.json")


func _assert_refused(path: String, why: String, needle := "") -> void:
	var world := WorldConfig.from_manifest(path)
	assert_not_null(world, "%s: the case's world block itself is valid" % why)
	var grid := SurfaceGrid.from_manifest(path, world)
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


func _set_key(key: String, value: Variant) -> Callable:
	return func(m: Dictionary) -> void: m["surfaces"][key] = value


## A PNG Godot encodes from [param pixels] in [param image_format], and a change that
## records its SHA-256 in the block, as a pipeline would.
func _png_case(pixels: PackedByteArray, image_format: Image.Format) -> String:
	var image := Image.create_from_data(200, 150, false, image_format, pixels)
	var png := image.save_png_to_buffer()
	var sha := _sha256(png)
	return _write_case(func(m: Dictionary) -> void: m["surfaces"]["sha256"] = sha, png)


func test_no_surfaces_built_names_the_command() -> void:
	var path := _write_case(func(m: Dictionary) -> void: m["surfaces"] = null)
	_assert_refused(path, "no surfaces block", SURFACES_COMMAND)


func test_surfaces_built_for_another_world_are_refused() -> void:
	var path := _write_case(_set_key("world_sha256", "0".repeat(64)))
	_assert_refused(path, "another world's surfaces", SURFACES_COMMAND)


func test_a_rotated_world_is_refused() -> void:
	var rotate := func(m: Dictionary) -> void:
		m["world"]["axes"] = {"x": "+n", "y": "+h", "z": "+e"}
	_assert_refused(_write_case(rotate), "a world without the owner's axes", "axes")


func test_another_format_is_refused() -> void:
	_assert_refused(_write_case(_set_key("format", "png-rgb8")), "another format", "format")


func test_a_block_with_another_key_set_is_refused() -> void:
	var path := _write_case(_set_key("spacing_m", 0.2))
	_assert_refused(path, "a block with a key too many", "spacing_m")


func test_columns_that_do_not_fit_the_box_are_refused() -> void:
	var path := _write_case(_set_key("columns", 199.0))
	_assert_refused(path, "199 columns of 0.2 m in a 40 m box", "columns")


func test_a_file_outside_the_manifest_s_folder_is_refused() -> void:
	var path := _write_case(_set_key("file", "../surfaces/fixture.png"))
	_assert_refused(path, "a path leaving the folder", "file")


func test_a_missing_png_is_refused() -> void:
	var path := _write_case(func(_m: Dictionary) -> void: pass, null)
	_assert_refused(path, "a missing PNG", "fixture.png")


func test_a_damaged_png_is_refused() -> void:
	var png := _fixture_png()
	var middle := png.size() >> 1
	png[middle] = png[middle] ^ 1
	var path := _write_case(func(_m: Dictionary) -> void: pass, png)
	_assert_refused(path, "a damaged PNG (same size)", "fixture.png")


func test_a_png_of_other_classes_is_refused() -> void:
	# A valid PNG whose own SHA-256 the block records, one class changed: only the check
	# of the decoded bytes against pixels_sha256 can refuse it.
	var image := Image.new()
	image.load_png_from_buffer(_fixture_png())
	var pixels := image.get_data()
	pixels[15000] = (pixels[15000] + 1) % 5  # row 75, column 0
	_assert_refused(_png_case(pixels, Image.FORMAT_L8), "other classes", "pixels_sha256")


func test_a_png_that_is_not_greyscale_is_refused() -> void:
	var image := Image.new()
	image.load_png_from_buffer(_fixture_png())
	image.convert(Image.FORMAT_RGB8)
	_assert_refused(_png_case(image.get_data(), Image.FORMAT_RGB8), "an RGB PNG", "L8")
