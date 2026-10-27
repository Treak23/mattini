extends GutTest
## Pinning tests for brief v0.4.0-02 (SPEC §13 row 53, the owner's "1b" of 2026-10-27): SurfaceGrid
## reads the surfaces block's flow grid, checked, and makes the flow texture through WorldConfig.
##
## Pinned decisions (the release session's, brief v0.4.0-02): the block's "flow" object is the one
## brief v0.4.0-01 writes, exactly the keys cell_m, columns, encoding, file, pixels_sha256, rows and
## sha256; cell_m 2, encoding "downstream-bearing-1.5deg", columns × cell_m and rows × cell_m the
## box's sides (the flow covers the classes' box, so rect() places it too). The flow PNG's SHA-256
## is compared with flow.sha256 BEFORE it is decoded; it decodes to L8, one byte per cell, of
## exactly columns × rows; its decoded bytes' SHA-256 is flow.pixels_sha256; a code above 240 is
## refused. Every file message ends with ReleaseBuild.file_hint. Code k (1 to 240) is the LV95
## grid bearing b = (k − 1) × 1.5° downstream; its local direction is the world's local vector of
## (east sin b, north cos b), through WorldConfig (Hard Rule 4), its (x, z) part normalised; the
## flow texture is RGB8, one texel per cell, rows north to south as the PNG: R = round(128 + 127 x),
## G = round(128 + 127 z), B = 255, and code 0 (128, 128, 0), so a shader reading
## (rg · 255 − 128) / 127 · b sees no drift where there is no stream or no texture. flow_at(x, z)
## decodes the texel holding the local point the same way, half-open as class_at, the zero vector
## outside and on code 0.
##
## The data: the shared surfaces fixture (tests/shared/surfaces_fixture/, its flow 20 × 15 cells
## at 2 m, written by brief v0.4.0-01) and the flow section of tests/shared/surfaces_vectors.json
## (its points with their code, bearing and local direction (sin b, −cos b) under the fixture's
## owner's axes x = +e, z = −n, computed by design three ways). The fixture holds a north flow
## (s11, s8), an east flow (s10), a south flow (s2) and four of s1's bearings between 193° and
## 267°, so a direction with east and north swapped, with z flipped, or a grid read with its rows
## mirrored reads other vectors at the named points. COLOURS holds design's bytes for the
## fixture's twelve codes, computed two ways by the pin author (an emulation of this arithmetic in
## IEEE doubles with WorldConfig's float32 Vector3, and Godot itself); code 141 (210°) is one of the
## eight bearings whose exact R or G is a rounding tie (64.5): the normalisation in 64-bit floats
## after WorldConfig's 32-bit vector puts it 8.5e-7 past the tie, so R is 64, as at the other seven
## (64 or 192, a direction and its reverse decoding to exact opposites).
##
## SurfaceGrid's new members are reached by name (has_method, call, get), so this script loads
## before the change and fails by the members' names (lesson 40).
##
## Does NOT prove: that the shader samples the flow texture on the right texel or drifts the
## water along it (brief v0.4.0-03; no GPU here); that swisstopo drew every line downstream (the
## pipeline's premise, brief v0.4.0-01); the real village's flow in the game (the pin author's
## probe read it once; the main scene's headless run reads it at the release gate).

const CompleteWorld := preload("res://tests/complete_world.gd")
const SCRATCH_DIR := "user://test_surface_flow"
const SURFACES_COMMAND := "python -m mattini surfaces"
const REBUILD := "; python -m mattini surfaces rebuilds it"
const FIXTURE_DIR := "tests/shared/surfaces_fixture/generated"
## The decoded vector's largest error: half a byte step, 0.5 / 127, and float rounding.
const DECODE_TOLERANCE := 0.004
## Design's bytes for each code of the fixture: [R, G, B].
const COLOURS := {
	0: [128, 128, 0],
	1: [128, 1, 255],
	6: [145, 2, 255],
	8: [151, 3, 255],
	60: [255, 125, 255],
	61: [255, 128, 255],
	62: [255, 131, 255],
	121: [128, 255, 255],
	130: [98, 251, 255],
	141: [64, 238, 255],
	155: [29, 208, 255],
	179: [1, 135, 255],
}
## Chosen texels: [column, row, code], each with COLOURS[code]: the four directions, the tie,
## both edges, the mod-240 north of s8 and code 0 at two corners.
const TEXELS := [
	[0, 0, 1],
	[1, 0, 0],
	[5, 0, 6],
	[15, 0, 141],
	[5, 1, 60],
	[16, 2, 130],
	[0, 3, 62],
	[14, 4, 155],
	[10, 7, 61],
	[2, 9, 121],
	[12, 9, 179],
	[9, 10, 1],
	[8, 13, 8],
	[19, 14, 0],
]
## A synthetic flow whose cell i (column i mod 20, row i div 20) holds code i for i = 0 to 240 and
## 0 after: the SHA-256 of its flow texture's 900 bytes, every code's colour, computed two ways by
## the pin author (the arithmetic emulated in Python; Godot). The same 723 bytes of colours come
## through the fixture's world, the complete world's and the real village's (the origin does not
## move them).
const ALL_CODES_TEXTURE_SHA256 := "a0c149faee09150cc86f14ddc7381c4fea7f8ee2c81b3e60a0a49602a0dcd373"
## The eight codes whose exact R or G is a rounding tie (sin or cos of the bearing ±1/2: 64.5 or
## 191.5), and their pinned [R, G]: 128 ± 64, a direction and its reverse decoding to opposites.
const TIES := {
	21: [192, 18],
	41: [238, 64],
	81: [238, 192],
	101: [192, 238],
	141: [64, 238],
	161: [18, 192],
	201: [18, 64],
	221: [64, 18],
}

var _cases := 0


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


func _manifest_path() -> String:
	return _repo_file(FIXTURE_DIR.path_join("manifest.json"))


func _parse(path: String) -> Dictionary:
	var json := JSON.new()
	assert_eq(json.parse(FileAccess.get_file_as_string(path)), OK, "%s parses" % path)
	return json.data if typeof(json.data) == TYPE_DICTIONARY else {}


func _flow_vectors() -> Dictionary:
	return _parse(_repo_file("tests/shared/surfaces_vectors.json")).get("flow", {})


func _fixture_file(name: String) -> PackedByteArray:
	return FileAccess.get_file_as_bytes(
		_repo_file(FIXTURE_DIR.path_join("surfaces").path_join(name))
	)


func _read_fixture() -> SurfaceGrid:
	return SurfaceGrid.from_manifest(_manifest_path(), WorldConfig.from_manifest(_manifest_path()))


## The fixture's flow codes, decoded here (not by SurfaceGrid): 20 × 15 bytes, rows from the north.
func _fixture_codes() -> PackedByteArray:
	var image := Image.new()
	assert_eq(image.load_png_from_buffer(_fixture_file("fixture-flow.png")), OK)
	assert_eq(image.get_format(), Image.FORMAT_L8, "the flow PNG decodes to L8")
	assert_eq(image.get_size(), Vector2i(20, 15), "20 columns, 15 rows")
	return image.get_data()


## SurfaceGrid.flow_at, called by name: NAN where the method is missing.
func _flow_at(grid: SurfaceGrid, x: float, z: float) -> Vector2:
	if not grid.has_method("flow_at"):
		return Vector2(NAN, NAN)
	return grid.call("flow_at", x, z)


## The flow texture's bytes (RGB8, row-major), or an empty array where there is none.
func _texture_bytes(grid: SurfaceGrid) -> PackedByteArray:
	var texture: Variant = grid.get("flow_texture")
	if not texture is ImageTexture:
		return PackedByteArray()
	var image: Image = texture.get_image()
	if image == null or image.get_format() != Image.FORMAT_RGB8:
		return PackedByteArray()
	return image.get_data()


func after_all() -> void:
	CompleteWorld.remove_tree(SCRATCH_DIR)


func _sha256(data: PackedByteArray) -> String:
	var context := HashingContext.new()
	context.start(HashingContext.HASH_SHA256)
	context.update(data)
	return context.finish().hex_encode()


func test_the_fixture_flow_is_read_as_designed() -> void:
	var grid := _read_fixture()
	assert_not_null(grid, "the fixture's surfaces are read")
	if grid == null:
		return
	assert_true(grid.has_method("flow_at"), "SurfaceGrid has flow_at(x, z) (brief v0.4.0-02)")
	assert_eq(
		[grid.get("flow_columns"), grid.get("flow_rows"), grid.get("flow_cell_m")],
		[20, 15, 2.0],
		"the flow grid: 20 columns, 15 rows of 2 m"
	)
	var texture: Variant = grid.get("flow_texture")
	assert_true(texture is ImageTexture, "SurfaceGrid has flow_texture, an ImageTexture")
	if not texture is ImageTexture:
		return
	assert_eq(texture.get_size(), Vector2(20, 15), "one texel per flow cell")
	var image: Image = texture.get_image()
	assert_eq(image.get_format(), Image.FORMAT_RGB8, "the flow texture is RGB8")
	assert_false(image.has_mipmaps(), "and has no mipmaps")
	assert_almost_eq(
		grid.rect(), Vector4(12.0, -1.0, 40.0, 30.0), Vector4.ONE * 1e-6, "the classes' box"
	)


func test_the_texels_at_chosen_cells_hold_design_s_bytes() -> void:
	var grid := _read_fixture()
	assert_not_null(grid, "the fixture's surfaces are read")
	if grid == null:
		return
	var bytes := _texture_bytes(grid)
	assert_eq(bytes.size(), 3 * 20 * 15, "the flow texture holds 3 bytes per cell")
	if bytes.size() != 3 * 20 * 15:
		return
	var codes := _fixture_codes()
	for texel: Array in TEXELS:
		var at: int = texel[1] * 20 + texel[0]
		assert_eq(
			codes[at], texel[2], "the fixture's code at column %d, row %d" % texel.slice(0, 2)
		)
		var found := [bytes[3 * at], bytes[3 * at + 1], bytes[3 * at + 2]]
		assert_eq(
			found,
			COLOURS[texel[2]],
			"texel (column %d, row %d), code %d: R, G, B" % [texel[0], texel[1], texel[2]]
		)


func test_the_texture_holds_every_cell_s_colour_row_by_row() -> void:
	# Rows from the north, as the PNG: a texture built from rows read from the south, or with
	# columns and rows exchanged, draws the flow somewhere else.
	var grid := _read_fixture()
	assert_not_null(grid, "the fixture's surfaces are read")
	if grid == null:
		return
	var bytes := _texture_bytes(grid)
	assert_eq(bytes.size(), 900, "the flow texture is there")
	if bytes.size() != 900:
		return
	var codes := _fixture_codes()
	var first_wrong := -1
	var first_wrong_at := -1
	for r in 15:
		for c in 20:
			var at := r * 20 + c
			var expected: Array = COLOURS.get(codes[at], [])
			var found := [bytes[3 * at], bytes[3 * at + 1], bytes[3 * at + 2]]
			if found != expected and first_wrong < 0:
				first_wrong = r
				first_wrong_at = c
			var centre := _flow_at(grid, 12.0 + 2.0 * c + 1.0, -1.0 + 2.0 * r + 1.0)
			var decoded: Vector2 = (
				Vector2((found[0] - 128) / 127.0, (found[1] - 128) / 127.0) * found[2] / 255.0
			)
			if not centre.is_equal_approx(decoded) and first_wrong < 0:
				first_wrong = r
				first_wrong_at = c
	assert_eq(
		[first_wrong, first_wrong_at],
		[-1, -1],
		"every texel holds its code's colour and flow_at decodes it (first wrong row, column)"
	)


func test_every_code_has_design_s_colour() -> void:
	var codes := PackedByteArray()
	codes.resize(300)
	for k in 241:
		codes[k] = k
	var png := Image.create_from_data(20, 15, false, Image.FORMAT_L8, codes).save_png_to_buffer()
	var path := _write_case(_recording(png, codes), png)
	var grid := SurfaceGrid.from_manifest(path, WorldConfig.from_manifest(path))
	assert_not_null(grid, "a flow holding every code 0 to 240 is read")
	if grid == null:
		return
	var bytes := _texture_bytes(grid)
	assert_eq(bytes.size(), 900, "the flow texture is there")
	if bytes.size() != 900:
		return
	assert_eq(_sha256(bytes), ALL_CODES_TEXTURE_SHA256, "every code's R, G and B are design's")
	for k: int in TIES:
		assert_eq(
			[bytes[3 * k], bytes[3 * k + 1]],
			TIES[k],
			(
				"code %d (%.1f°): the tie decided as pinned (normalised in 64-bit floats)"
				% [k, (k - 1) * 1.5]
			)
		)


func test_every_named_flow_point_has_its_direction() -> void:
	var grid := _read_fixture()
	var world := WorldConfig.from_manifest(_manifest_path())
	assert_not_null(grid, "the fixture's surfaces are read")
	if grid == null:
		return
	var points: Array = _flow_vectors().get("points", [])
	assert_eq(points.size(), 16, "the vectors name 16 flow points")
	for p: Dictionary in points:
		var local: Array = p["local"]
		var expected := Vector2.ZERO
		if int(p["code"]) != 0:
			expected = Vector2(p["direction_local"][0], p["direction_local"][1])
		var found := _flow_at(grid, local[0], local[1])
		assert_almost_eq(found, expected, Vector2.ONE * DECODE_TOLERANCE, p["name"])
		# The seam: the vectors' local point is the world config's (Hard Rule 4).
		var lv95: Array = p["lv95"]
		var placed := world.to_local(lv95[0], lv95[1], world.height_offset)
		assert_almost_eq(
			Vector2(placed.x, placed.z), Vector2(local[0], local[1]), Vector2.ONE * 1e-4, p["name"]
		)


func test_north_is_minus_z_and_east_is_plus_x() -> void:
	# The likeliest wrong twins, each named: east and north exchanged, z taken for north, the
	# rows mirrored north-south. Points from tests/shared/surfaces_vectors.json's flow section.
	var grid := _read_fixture()
	assert_not_null(grid, "the fixture's surfaces are read")
	if grid == null:
		return
	var tolerance := Vector2.ONE * DECODE_TOLERANCE
	assert_almost_eq(
		_flow_at(grid, 13.0, 0.0),
		Vector2(0.0, -1.0),
		tolerance,
		"s11 flows north: −z (not +z: z flipped; not +x: east and north exchanged)"
	)
	assert_almost_eq(
		_flow_at(grid, 33.0, 14.0),
		Vector2(1.0, 0.0),
		tolerance,
		"s10 flows east: +x (not −z: east and north exchanged)"
	)
	assert_almost_eq(
		_flow_at(grid, 17.0, 18.0),
		Vector2(0.0, 1.0),
		tolerance,
		"the waterfall s2 flows south: +z (not −z: z flipped)"
	)
	assert_almost_eq(
		_flow_at(grid, 13.0, 28.0),
		Vector2(0.0, 1.0),
		tolerance,
		"row 14, column 0 is s2's south (not s11's north: the rows mirrored)"
	)
	assert_almost_eq(
		_flow_at(grid, 37.0, 18.0),
		Vector2(-0.998630, 0.052336),
		tolerance,
		"s1's last segment, 267°: west and a little south (not north-east: mirrored)"
	)


func test_flow_at_is_half_open_and_zero_outside() -> void:
	var grid := _read_fixture()
	assert_not_null(grid, "the fixture's surfaces are read")
	if grid == null:
		return
	var north := Vector2(0.0, -1.0)
	var tolerance := Vector2.ONE * DECODE_TOLERANCE
	assert_almost_eq(_flow_at(grid, 12.0, -1.0), north, tolerance, "the north-west corner is in")
	assert_almost_eq(_flow_at(grid, 13.999, 0.999), north, tolerance, "texel (0, 0)'s far corner")
	assert_eq(_flow_at(grid, 14.0, 0.0), Vector2.ZERO, "texel (1, 0) is code 0: no stream")
	assert_eq(_flow_at(grid, 11.999, 0.0), Vector2.ZERO, "west of the grid: zero")
	assert_eq(_flow_at(grid, 13.0, -1.001), Vector2.ZERO, "north of the grid: zero")
	assert_eq(_flow_at(grid, 52.0, 10.0), Vector2.ZERO, "the east edge is out")
	assert_eq(_flow_at(grid, 20.0, 29.0), Vector2.ZERO, "the south edge is out")
	assert_almost_eq(
		_flow_at(grid, 13.0, 28.999), Vector2(0.0, 1.0), tolerance, "the last row is in"
	)


func test_the_complete_world_carries_the_flow() -> void:
	# game/tests/complete_world.gd copies the flow PNG beside the classes and moves the box: every
	# scene test and the render step's world read it.
	var dir := SCRATCH_DIR.path_join("complete")
	var path := CompleteWorld.write(dir)
	var block: Dictionary = CompleteWorld.read_manifest(path)["surfaces"]
	assert_true(block.get("flow") is Dictionary, "the complete world's surfaces carry a flow")
	if not block.get("flow") is Dictionary:
		return
	var flow_png := dir.path_join(block["flow"]["file"])
	assert_true(FileAccess.file_exists(flow_png), "its flow PNG is written beside the classes")
	var grid := SurfaceGrid.from_manifest(path, WorldConfig.from_manifest(path))
	assert_not_null(grid, "the complete world's surfaces are read, the flow included")
	if grid == null:
		return
	assert_eq([grid.x0, grid.z0], [1013.0, 9.0], "the moved box's north-west corner")
	assert_almost_eq(
		_flow_at(grid, 1014.0, 10.0),
		Vector2(0.0, -1.0),
		Vector2.ONE * DECODE_TOLERANCE,
		"texel (0, 0) of the moved box flows north"
	)
	assert_almost_eq(
		_flow_at(grid, 1034.0, 24.0),
		Vector2(1.0, 0.0),
		Vector2.ONE * DECODE_TOLERANCE,
		"texel (10, 7) of the moved box flows east"
	)


## Writes a copy of the fixture's generated folder whose manifest is changed by [param change]:
## its class PNG, and its flow PNG [param flow_png] (null leaves it out; an empty array keeps the
## fixture's); returns the manifest's path.
func _write_case(change: Callable, flow_png: Variant = PackedByteArray()) -> String:
	_cases += 1
	var dir := SCRATCH_DIR.path_join("case_%d" % _cases)
	DirAccess.make_dir_recursive_absolute(dir.path_join("surfaces"))
	var manifest := _parse(_manifest_path())
	change.call(manifest)
	var out := FileAccess.open(dir.path_join("manifest.json"), FileAccess.WRITE)
	out.store_string(JSON.stringify(manifest, "  ", true, true))
	out.close()
	var files := {"surfaces/fixture.png": _fixture_file("fixture.png")}
	if flow_png != null:
		var bytes: PackedByteArray = flow_png
		files["surfaces/fixture-flow.png"] = (
			bytes if not bytes.is_empty() else _fixture_file("fixture-flow.png")
		)
	for rel: String in files:
		var file := FileAccess.open(dir.path_join(rel), FileAccess.WRITE)
		file.store_buffer(files[rel])
		file.close()
	return dir.path_join("manifest.json")


## The read is refused: a null result, and exactly one error, a push_error naming [param path]
## and saying [param needle]. Every error of the case is handled, so the next case starts clean;
## an error of any other kind (a SCRIPT ERROR, an engine ERROR) fails the case.
func _assert_refused(path: String, why: String, needle: String, hint := false) -> void:
	var world := WorldConfig.from_manifest(path)
	assert_not_null(world, "%s: the case's world block itself is valid" % why)
	var grid := SurfaceGrid.from_manifest(path, world)
	assert_null(grid, "%s is refused" % why)
	var pushed := 0
	var others := []
	for error in get_errors():
		if error.handled:
			continue
		if error.is_push_error() and error.contains_text(path) and error.contains_text(needle):
			pushed += 1
			if hint:
				assert_true(
					error.contains_text(REBUILD), "%s: the message ends with file_hint" % why
				)
		else:
			others.append("%s %s" % [error.code, error.rationale])
		error.handled = true
	assert_eq(pushed, 1, "%s: one push_error names %s and says '%s'" % [why, path, needle])
	assert_eq(others, [], "%s: no other error, no SCRIPT ERROR" % why)


func _set_flow(key: String, value: Variant) -> Callable:
	return func(m: Dictionary) -> void: m["surfaces"]["flow"][key] = value


## A change recording [param png]'s SHA-256 as flow.sha256, and [param pixels]' as
## flow.pixels_sha256 when they are given.
func _recording(png: PackedByteArray, pixels := PackedByteArray()) -> Callable:
	var sha := _sha256(png)
	# HashingContext refuses an empty buffer with an engine error: no digest for no pixels.
	var pixels_sha := "" if pixels.is_empty() else _sha256(pixels)
	return func(m: Dictionary) -> void:
		m["surfaces"]["flow"]["sha256"] = sha
		if not pixels.is_empty():
			m["surfaces"]["flow"]["pixels_sha256"] = pixels_sha


func test_a_missing_flow_png_is_refused() -> void:
	var path := _write_case(func(_m: Dictionary) -> void: pass, null)
	_assert_refused(path, "a missing flow PNG", "fixture-flow.png is missing", true)


func test_the_sha256_is_compared_before_decoding() -> void:
	# Bytes that are not a PNG at all: the SHA-256 refuses them, and nothing tries to decode them
	# (a decoder fed a foreign file reports its own errors, or decodes it).
	var junk := "not a PNG, a file of another kind".to_utf8_buffer()
	var path := _write_case(func(_m: Dictionary) -> void: pass, junk)
	_assert_refused(path, "bytes that are not a PNG", "has SHA-256", true)


func test_a_png_of_other_bytes_is_refused_by_its_sha256() -> void:
	# The same codes, encoded by Godot: other bytes, so not the PNG the block describes.
	var codes := _fixture_codes()
	var png := Image.create_from_data(20, 15, false, Image.FORMAT_L8, codes).save_png_to_buffer()
	assert_ne(_sha256(png), _sha256(_fixture_file("fixture-flow.png")), "Godot writes other bytes")
	var path := _write_case(func(_m: Dictionary) -> void: pass, png)
	_assert_refused(path, "a flow PNG of other bytes", "not surfaces.flow.sha256", true)


func test_a_flow_png_of_another_size_is_refused() -> void:
	# 15 columns by 20 rows: the same count of cells, the grid's sides exchanged.
	var codes := PackedByteArray()
	codes.resize(300)
	var png := Image.create_from_data(15, 20, false, Image.FORMAT_L8, codes).save_png_to_buffer()
	var path := _write_case(_recording(png), png)
	_assert_refused(path, "a flow PNG of 15 × 20 cells", "decodes to 15 × 20", true)


func test_a_flow_png_that_is_not_greyscale_is_refused() -> void:
	var image := Image.create_from_data(20, 15, false, Image.FORMAT_L8, _fixture_codes())
	image.convert(Image.FORMAT_RGB8)
	var png := image.save_png_to_buffer()
	var path := _write_case(_recording(png), png)
	_assert_refused(path, "an RGB flow PNG", "of L8", true)


func test_a_flow_png_of_other_codes_is_refused() -> void:
	# A valid PNG whose own SHA-256 the block records, one code changed (column 10, row 7: east,
	# 61, made 62): only the check of the decoded bytes against flow.pixels_sha256 can refuse it.
	var codes := _fixture_codes()
	codes[7 * 20 + 10] = 62
	var png := Image.create_from_data(20, 15, false, Image.FORMAT_L8, codes).save_png_to_buffer()
	var path := _write_case(_recording(png), png)
	_assert_refused(path, "other codes", "not surfaces.flow.pixels_sha256", true)


func test_a_code_above_240_is_refused() -> void:
	# Both SHA-256s recorded, as a pipeline that wrote code 241 would: only the code check is left.
	var codes := _fixture_codes()
	codes[5 * 20 + 3] = 241
	var png := Image.create_from_data(20, 15, false, Image.FORMAT_L8, codes).save_png_to_buffer()
	var path := _write_case(_recording(png, codes), png)
	_assert_refused(path, "a code above 240", "the code 241 at column 3, row 5, above 240", true)


func test_a_flow_that_is_not_the_designed_object_is_refused() -> void:
	var cases := [
		["no flow object", func(m: Dictionary) -> void: m["surfaces"]["flow"] = null],
		["a flow that is text", func(m: Dictionary) -> void: m["surfaces"]["flow"] = "flow"],
		["a flow that is a number", func(m: Dictionary) -> void: m["surfaces"]["flow"] = 2.0],
		["a flow that is a list", func(m: Dictionary) -> void: m["surfaces"]["flow"] = []],
		["a flow with a speed", _set_flow("speed_m_s", 1.0)],
		[
			"a flow without its encoding",
			func(m: Dictionary) -> void: m["surfaces"]["flow"].erase("encoding")
		],
	]
	for case: Array in cases:
		var path := _write_case(case[1])
		_assert_refused(path, case[0], "surfaces.flow must hold exactly the keys")


func test_a_flow_of_another_cell_or_encoding_is_refused() -> void:
	var cases := [
		["cell_m", 1.0, "surfaces.flow.cell_m must be 2"],
		["cell_m", "2", "surfaces.flow.cell_m must be 2"],
		["cell_m", 0.2, "surfaces.flow.cell_m must be 2"],
		["encoding", "downstream-bearing-1.4deg", "surfaces.flow.encoding must be"],
		["encoding", 1.5, "surfaces.flow.encoding must be"],
		["encoding", null, "surfaces.flow.encoding must be"],
	]
	for case: Array in cases:
		var path := _write_case(_set_flow(case[0], case[1]))
		_assert_refused(path, "flow.%s = %s" % [case[0], JSON.stringify(case[1])], case[2])


func test_flow_counts_that_do_not_fit_the_box_are_refused() -> void:
	var cases := [
		["columns", 21.0, "do not fit lv95_box"],
		["rows", 16.0, "do not fit lv95_box"],
		["columns", 15.0, "do not fit lv95_box"],
		["columns", 20.5, "surfaces.flow.columns must be a whole number"],
		["rows", "15", "surfaces.flow.rows must be a whole number"],
		["rows", 0.0, "surfaces.flow.rows must be a whole number"],
	]
	for case: Array in cases:
		var path := _write_case(_set_flow(case[0], case[1]))
		_assert_refused(path, "flow.%s = %s" % [case[0], JSON.stringify(case[1])], case[2])


func test_a_flow_file_or_digest_of_the_wrong_kind_is_refused() -> void:
	var cases := [
		[
			"file",
			"../surfaces/fixture-flow.png",
			"surfaces.flow.file must be a plain relative path"
		],
		["file", 3.0, "surfaces.flow.file must be a plain relative path"],
		["sha256", 7.0, "surfaces.flow.sha256 must be 64 hex digits"],
		["sha256", "abc", "surfaces.flow.sha256 must be 64 hex digits"],
		["pixels_sha256", "z".repeat(64), "surfaces.flow.pixels_sha256 must be 64 hex digits"],
	]
	for case: Array in cases:
		var path := _write_case(_set_flow(case[0], case[1]))
		_assert_refused(path, "flow.%s = %s" % [case[0], JSON.stringify(case[1])], case[2])
