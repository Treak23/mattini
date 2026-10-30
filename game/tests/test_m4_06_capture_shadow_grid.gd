extends GutTest
## Pinning tests for brief M4-06: CaptureShadowGrid reads the manifest's shadows block and its mask
## PNG, checked, and places the mask's rectangle through WorldConfig.
##
## Re-pinned by brief v0.5.0-03, which builds the reader (M4-06 decisions 1 and 7): M4-06's file
## with one decision changed, the session's of 2026-10-29 on the owner's 3a: the mask's texture HAS
## mipmaps, a full chain made from the decoded L8 image, as the photo's has (PhotoGrid generates
## them; its sampler is filter_linear_mipmap_anisotropic): a 0.5 m binary mask under a mipmapped
## 0.2 m photo would alias in the distance. Level 0 is the decoded PNG, byte for byte. The
## reader's file messages end with ReleaseBuild.file_hint (test_m4_08_release_hints.gd pins that).
##
## Pinned decisions (m4-design §3 and §8; brief M4-03's files, brief M4-06 Decisions): the
## manifest's shadows block is the step's description as M4-03 writes it
## (tests/shared/shadows_fixture/generated/shadows/fixture.json): exactly the keys area, cell_m
## (0.5), columns, file, format ("png-l8"), lv95_box, pixels_sha256, rows, sha256 (the PNG's),
## source {attribution, collection, dataset "swisssurface3d", editions (a list), entry_sha256}, sun
## {azimuth_grid_deg, elevation_deg, note} and world_sha256. The PNG is 8-bit greyscale (Godot
## decodes it to L8), 0 lit and 255 shadow, rows north to south; its decoded bytes' SHA-256 is
## pixels_sha256. Texel (c, r) is the 0.5 m square whose north-west corner lies 0.5·c m east and
## 0.5·r m south of the box's north-west corner, which is WorldConfig.to_local(e_min, n_max) (no
## origin subtracted in the reader); only the owner's axes are accepted. value_at(x, z) gives the
## texel's byte (0 or 255) of the local point, -1 outside the half-open rectangle. Every problem
## is refused with one push_error "CaptureShadowGrid: <manifest path>: <problem>" and a null
## result (Hard Rule 2); the refusals the owner fixes by re-running the pipeline name
## `python -m mattini shadows`. Every compare of a manifest value is typed (brain.md H26): a
## number where a text belongs is refused, never a runtime error that lets the block through.
##
## The manifest is written here from the shared fixture (its world.json as the world block, that
## file's SHA-256 as world_sha256, fixture.json as the shadows block, as brief M4-09 will write
## it); the named cells are design's, in tests/shared/shadows_vectors.json.
##
## Does NOT prove: that the shader samples the mask where the reader places it (the gate's
## render step, `RENDER lift`); that the real village's mask reads the same way; that brief
## M4-09's manifest block has this form (its own pins); that the mipmaps are sampled or keep the
## distance from aliasing (the shader's sampler is the look's brief; a distant render is the
## only evidence).

const SCRATCH_DIR := "user://test_m4_06_capture_shadow_grid"
const SHADOWS_COMMAND := "python -m mattini shadows"
const FIXTURE_DIR := "tests/shared/shadows_fixture"
const VECTORS := "tests/shared/shadows_vectors.json"
## The fixture's rectangle: world.json's origin E 2650012 / N 1149988 and the box's north-west
## corner E 2650986 / N 1150026, 64 x 96 texels at 0.5 m.
const RECT := Vector4(974.0, -38.0, 32.0, 48.0)
const CompleteWorld := preload("res://tests/complete_world.gd")

var _cases := 0


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


func _parse_file(path: String) -> Dictionary:
	var json := JSON.new()
	assert_eq(json.parse(FileAccess.get_file_as_string(path)), OK, "%s parses" % path)
	return json.data if typeof(json.data) == TYPE_DICTIONARY else {}


func _fixture_png() -> PackedByteArray:
	return FileAccess.get_file_as_bytes(
		_repo_file(FIXTURE_DIR.path_join("generated/shadows/fixture.png"))
	)


## The fixture's manifest as brief M4-09 writes one: schema 1, the world block, its SHA-256,
## the shadows block.
func _fixture_manifest() -> Dictionary:
	var world_path := _repo_file(FIXTURE_DIR.path_join("world.json"))
	return {
		"schema": 1,
		"world": _parse_file(world_path),
		"world_sha256": FileAccess.get_sha256(world_path),
		"shadows": _parse_file(_repo_file(FIXTURE_DIR.path_join("generated/shadows/fixture.json"))),
	}


func _sha256(data: PackedByteArray) -> String:
	var context := HashingContext.new()
	context.start(HashingContext.HASH_SHA256)
	context.update(data)
	return context.finish().hex_encode()


func after_all() -> void:
	CompleteWorld.remove_tree(SCRATCH_DIR)


## Writes a case folder: the fixture's manifest changed by [param change] (a Callable taking the
## manifest Dictionary) and its PNG [param png] (null leaves it out; an empty array keeps the
## fixture's); returns the manifest's path.
func _write_case(change: Callable, png: Variant = PackedByteArray()) -> String:
	_cases += 1
	var dir := SCRATCH_DIR.path_join("case_%d" % _cases)
	DirAccess.make_dir_recursive_absolute(dir.path_join("shadows"))
	var manifest := _fixture_manifest()
	change.call(manifest)
	var out := FileAccess.open(dir.path_join("manifest.json"), FileAccess.WRITE)
	out.store_string(JSON.stringify(manifest, "  ", true, true))
	out.close()
	if png != null:
		var bytes: PackedByteArray = png if not png.is_empty() else _fixture_png()
		var file := FileAccess.open(dir.path_join("shadows/fixture.png"), FileAccess.WRITE)
		file.store_buffer(bytes)
		file.close()
	return dir.path_join("manifest.json")


func _read(path: String) -> CaptureShadowGrid:
	return CaptureShadowGrid.from_manifest(path, WorldConfig.from_manifest(path))


func _read_fixture() -> CaptureShadowGrid:
	return _read(_write_case(func(_m: Dictionary) -> void: pass))


func test_the_fixture_is_read_as_designed() -> void:
	var grid := _read_fixture()
	assert_not_null(grid, "the fixture's mask is read")
	if grid == null:
		return
	assert_eq(grid.area, "fixture")
	assert_eq([grid.columns, grid.rows, grid.cell_m], [64, 96, 0.5])
	assert_eq(grid.dataset, "swisssurface3d")
	assert_eq(grid.editions, PackedStringArray(["2021", "2022"]))
	assert_eq(grid.attribution, "© swisstopo")
	assert_eq([grid.x0, grid.z0], [RECT.x, RECT.y], "the north-west corner, through WorldConfig")
	assert_almost_eq(grid.width_m, RECT.z, 1e-9)
	assert_almost_eq(grid.depth_m, RECT.w, 1e-9)
	assert_eq(grid.rect(), RECT, "rect() is (x0, z0, width_m, depth_m)")
	assert_not_null(grid.texture, "an ImageTexture of the mask")
	if grid.texture != null:
		assert_eq(grid.texture.get_size(), Vector2(64, 96))
		assert_eq(grid.texture.get_format(), Image.FORMAT_L8, "L8: the mask is data, one byte")
		var image := grid.texture.get_image()
		assert_true(image.has_mipmaps(), "mipmaps, as the photo's: no aliasing in the distance")
		var chain := Image.create(64, 96, true, Image.FORMAT_L8).get_mipmap_count()
		assert_eq(image.get_mipmap_count(), chain, "the full chain, down to 1 x 1")
		assert_eq(image.get_format(), Image.FORMAT_L8, "and every level L8")


func test_every_named_cell_has_its_value() -> void:
	var grid := _read_fixture()
	var world := WorldConfig.from_manifest(_write_case(func(_m: Dictionary) -> void: pass))
	assert_not_null(grid, "the fixture's mask is read")
	if grid == null:
		return
	var vectors := _parse_file(_repo_file(VECTORS))
	var cells: Array = vectors["cells"]
	assert_gt(cells.size(), 10, "design names cells of every case")
	for cell: Dictionary in cells:
		var local: Array = cell["local_xz"]
		# The seam: design's local point is the world config's (Hard Rule 4).
		var lv95: Array = cell["lv95"]
		var placed := world.to_local(lv95[0], lv95[1], world.height_offset)
		assert_almost_eq(
			Vector2(placed.x, placed.z), Vector2(local[0], local[1]), Vector2.ONE * 1e-4
		)
		# The centre and four points 0.05 m inside each corner of the texel: a mask placed half a
		# texel (0.25 m) off in any direction reads another texel at one of them.
		for offset: Vector2 in [
			Vector2.ZERO,
			Vector2(-0.2, -0.2),
			Vector2(0.2, -0.2),
			Vector2(-0.2, 0.2),
			Vector2(0.2, 0.2)
		]:
			assert_eq(
				grid.value_at(local[0] + offset.x, local[1] + offset.y),
				int(cell["value"]),
				"%s at %s" % [cell["name"], offset]
			)


func test_every_texel_reads_back_where_lv95_puts_it() -> void:
	# The test decodes the PNG itself and places each texel from LV95 through WorldConfig (the
	# vectors' formula: centre E = e_min + 0.25 + 0.5 c, N = n_max - 0.25 - 0.5 r): a reader that
	# flips the rows or the columns, swaps them, or places the rectangle from another corner reads
	# another byte at some texel; so does a texture made from the image after a flip.
	var path := _write_case(func(_m: Dictionary) -> void: pass)
	var world := WorldConfig.from_manifest(path)
	var grid := CaptureShadowGrid.from_manifest(path, world)
	assert_not_null(grid, "the fixture's mask is read")
	if grid == null or grid.texture == null:
		return
	var image := Image.new()
	assert_eq(image.load_png_from_buffer(_fixture_png()), OK)
	var box: Dictionary = _fixture_manifest()["shadows"]["lv95_box"]
	var texture_bytes := grid.texture.get_image().get_data()
	var first_wrong := ""
	var shadow := 0
	for r in 96:
		for c in 64:
			var byte := image.get_pixel(c, r).r8
			if byte == 255:
				shadow += 1
			var e: float = box["e_min"] + 0.25 + 0.5 * c
			var n: float = box["n_max"] - 0.25 - 0.5 * r
			var at := world.to_local(e, n, world.height_offset)
			var read := grid.value_at(at.x, at.z)
			if first_wrong.is_empty() and (read != byte or texture_bytes[r * 64 + c] != byte):
				first_wrong = (
					"row %d column %d: PNG %d, value_at %d, texture %d"
					% [r, c, byte, read, texture_bytes[r * 64 + c]]
				)
	assert_eq(
		first_wrong, "", "every texel's byte is where LV95 puts it, in value_at and the texture"
	)
	assert_eq(shadow, int(_parse_file(_repo_file(VECTORS))["shadow_cells"]), "design's count")


func test_the_rectangle_is_half_open_and_outside_is_minus_one() -> void:
	var grid := _read_fixture()
	assert_not_null(grid, "the fixture's mask is read")
	if grid == null:
		return
	# The corners just inside, then just outside on each side.
	assert_eq(grid.value_at(RECT.x, RECT.y), 0, "the north-west corner is in")
	assert_eq(
		grid.value_at(RECT.x + RECT.z - 0.01, RECT.y + RECT.w - 0.01), 0, "south-east, inside"
	)
	# Row 11, column 63 (the ridge at the east edge) is 255: its east edge is out.
	var ridge_z := RECT.y + 11 * 0.5 + 0.25
	assert_eq(
		grid.value_at(RECT.x + RECT.z - 0.01, ridge_z), 255, "the ridge touches the east edge"
	)
	assert_eq(grid.value_at(RECT.x + RECT.z, ridge_z), -1, "the east edge is out")
	assert_eq(grid.value_at(RECT.x - 0.01, RECT.y + 1.0), -1, "west of it")
	assert_eq(grid.value_at(RECT.x + 1.0, RECT.y - 0.01), -1, "north of it")
	assert_eq(grid.value_at(RECT.x + 1.0, RECT.y + RECT.w), -1, "the south edge is out")


func test_the_complete_world_carries_the_mask_at_its_own_box() -> void:
	# The render step's world (complete_world.gd): the fixture moved to SHADOWS_BOX, read like the
	# others. Its rectangle is neither the photo's nor the classes'.
	var dir := SCRATCH_DIR.path_join("complete")
	var path := CompleteWorld.write(dir)
	var world := WorldConfig.from_manifest(path)
	var grid := CaptureShadowGrid.from_manifest(path, world)
	assert_not_null(grid, "the complete world's mask is read")
	if grid == null:
		return
	assert_eq(grid.rect(), Vector4(1019.0, -4.5, 32.0, 48.0), "SHADOWS_BOX through the world")
	var photo := PhotoGrid.from_manifest(path, world)
	var surfaces := SurfaceGrid.from_manifest(path, world)
	assert_ne(grid.rect(), photo.rect(), "not the photo's rectangle")
	assert_ne(grid.rect(), surfaces.rect(), "not the classes' rectangle")


func _assert_refused(path: String, why: String, needle := "") -> void:
	var world := WorldConfig.from_manifest(path)
	assert_not_null(world, "%s: the case's world block itself is valid" % why)
	var grid := CaptureShadowGrid.from_manifest(path, world)
	assert_null(grid, "%s is refused" % why)
	var found := false
	for error in get_errors():
		if (
			not found
			and not error.handled
			and error.is_push_error()
			and error.contains_text("CaptureShadowGrid: %s: " % path)
			and (needle == "" or error.contains_text(needle))
		):
			error.handled = true
			found = true
	assert_true(
		found, "%s: one push_error 'CaptureShadowGrid: %s: ...' names %s" % [why, path, needle]
	)


func _set_key(key: String, value: Variant) -> Callable:
	return func(m: Dictionary) -> void: m["shadows"][key] = value


func _set_nested(outer: String, key: String, value: Variant) -> Callable:
	return func(m: Dictionary) -> void: m["shadows"][outer][key] = value


func _png_case(pixels: PackedByteArray, image_format: Image.Format) -> String:
	var image := Image.create_from_data(64, 96, false, image_format, pixels)
	var png := image.save_png_to_buffer()
	var sha := _sha256(png)
	return _write_case(func(m: Dictionary) -> void: m["shadows"]["sha256"] = sha, png)


func test_no_shadows_built_names_the_commands() -> void:
	var path := _write_case(func(m: Dictionary) -> void: m["shadows"] = null)
	_assert_refused(path, "no shadows block", SHADOWS_COMMAND)
	var missing := _write_case(func(m: Dictionary) -> void: m.erase("shadows"))
	_assert_refused(missing, "a manifest without the key", "python -m mattini download surface")


func test_shadows_built_for_another_world_are_refused() -> void:
	var path := _write_case(_set_key("world_sha256", "0".repeat(64)))
	_assert_refused(path, "another world's mask", SHADOWS_COMMAND)


func test_values_of_another_type_are_refused_not_a_runtime_error() -> void:
	# brain.md H26: `!=` between a String and a float stops the function; the reader must refuse.
	_assert_refused(_write_case(_set_key("world_sha256", 5.0)), "a numeric world_sha256")
	_assert_refused(_write_case(_set_key("format", 1.0)), "a numeric format", "format")
	_assert_refused(_write_case(_set_key("cell_m", "0.5")), "a text cell_m", "cell_m")
	_assert_refused(
		_write_case(_set_nested("source", "dataset", [])), "a list as dataset", "dataset"
	)
	_assert_refused(
		_write_case(_set_nested("source", "editions", "2021")), "editions as text", "editions"
	)
	_assert_refused(_write_case(_set_key("sun", [184.67, 50.1])), "a list as sun", "sun")


func test_a_rotated_world_is_refused() -> void:
	var rotate := func(m: Dictionary) -> void:
		m["world"]["axes"] = {"x": "+n", "y": "+h", "z": "+e"}
	_assert_refused(_write_case(rotate), "a world without the owner's axes", "axes")


func test_another_world_config_given_is_refused() -> void:
	# Each origin coordinate on its own: a guard that compares only the east one lets a world
	# shifted north-south through.
	var path := _write_case(func(_m: Dictionary) -> void: pass)
	for axis in ["e", "n"]:
		var other := _write_case(
			func(m: Dictionary) -> void: m["world"]["origin_lv95"][axis] += 12.0
		)
		var grid := CaptureShadowGrid.from_manifest(path, WorldConfig.from_manifest(other))
		assert_null(grid, "a WorldConfig read from another manifest (origin %s) is refused" % axis)
		var found := false
		for error in get_errors():
			if (
				not found
				and not error.handled
				and error.is_push_error()
				and error.contains_text("CaptureShadowGrid: %s: " % path)
			):
				error.handled = true
				found = true
		assert_true(found, "and named (origin %s)" % axis)


func test_the_block_s_fields_are_checked() -> void:
	_assert_refused(_write_case(_set_key("format", "png-rgb8")), "another format", "format")
	_assert_refused(_write_case(_set_key("cell_m", 1.0)), "a 1 m mask", "cell_m")
	_assert_refused(_write_case(_set_key("classes", {})), "a key too many", "classes")
	_assert_refused(
		_write_case(func(m: Dictionary) -> void: m["shadows"].erase("sun")), "no sun", "sun"
	)
	_assert_refused(_write_case(_set_key("columns", 63.0)), "63 columns in a 32 m box", "columns")
	_assert_refused(_write_case(_set_key("rows", 96.5)), "a fraction of a row", "rows")
	_assert_refused(_write_case(_set_key("pixels_sha256", "xyz")), "a bad digest", "pixels_sha256")
	_assert_refused(
		_write_case(_set_nested("source", "dataset", "swissalti3d")), "another dataset", "dataset"
	)
	_assert_refused(
		_write_case(_set_nested("lv95_box", "e_max", 2651017.0)), "a box 31 m wide", "columns"
	)
	_assert_refused(
		_write_case(_set_nested("lv95_box", "n_min", 1149977.0)), "a box 49 m deep", "columns"
	)
	_assert_refused(
		_write_case(_set_nested("source", "licence", "CC0")), "a source key too many", "source"
	)


func test_a_file_outside_the_manifest_s_folder_is_refused() -> void:
	var path := _write_case(_set_key("file", "../shadows/fixture.png"))
	_assert_refused(path, "a path leaving the folder", "file")
	# An absolute path to the fixture's own PNG (its SHA-256 the block's): a reader that opened it
	# as given would accept it; the path check must refuse it.
	var absolute := (
		_repo_file(FIXTURE_DIR.path_join("generated/shadows/fixture.png")).simplify_path()
	)
	_assert_refused(_write_case(_set_key("file", absolute)), "an absolute path", "file")


func test_a_missing_png_is_refused() -> void:
	var path := _write_case(func(_m: Dictionary) -> void: pass, null)
	_assert_refused(path, "a missing PNG", SHADOWS_COMMAND)


func test_a_damaged_png_is_refused() -> void:
	var png := _fixture_png()
	var middle := png.size() >> 1
	png[middle] = png[middle] ^ 1
	_assert_refused(
		_write_case(func(_m: Dictionary) -> void: pass, png), "a damaged PNG", "SHA-256"
	)


func test_a_png_of_another_mask_is_refused() -> void:
	# A valid PNG whose own SHA-256 the block records, one texel changed: only the check of the
	# decoded bytes against pixels_sha256 can refuse it.
	var image := Image.new()
	image.load_png_from_buffer(_fixture_png())
	var pixels := image.get_data()
	pixels[40 * 64 + 10] = 0  # behind the block
	_assert_refused(_png_case(pixels, Image.FORMAT_L8), "another mask", "pixels_sha256")


func test_a_png_that_is_not_greyscale_is_refused() -> void:
	var image := Image.new()
	image.load_png_from_buffer(_fixture_png())
	image.convert(Image.FORMAT_RGB8)
	_assert_refused(_png_case(image.get_data(), Image.FORMAT_RGB8), "an RGB PNG", "L8")
