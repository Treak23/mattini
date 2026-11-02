extends GutTest
## Pinning tests for brief v0.6.0-08 (design §2 and §3): SurroundingsGrid reads the colour of the
## far terrain, the JPEG beside the heights, and guards the world it was built for.
##
## Pinned decisions (brief v0.6.0-08 decisions 1 to 3): the manifest's surroundings block holds,
## beside the heights' keys (test_m4_07_surroundings_grid.gd), exactly the colour's nine:
## colour_cell_m (a positive finite number of metres), colour_columns and colour_rows (whole
## numbers of at least 1 and at most 16384: a wider or taller texture draws black under the
## Compatibility renderer with no error, brain.md H21), colour_file (a plain relative path),
## colour_format ("jpeg"), colour_pixels_sha256 and colour_sha256 (64 hex digits each),
## colour_source {attribution, collection, dataset ("swissimage_far"), edition} (texts) and
## filled_fraction (a number from 0 to 1, the share of placeholder pixels, design §2). The colour
## covers the heights' own lv95_box: colour_columns × colour_cell_m and colour_rows ×
## colour_cell_m are its sides within 1 mm. The JPEG must exist (checked before any read), have
## colour_sha256 and decode to RGB8 of exactly colour_columns × colour_rows; the reader holds it
## as colour_texture, an ImageTexture with mipmaps whose level 0 is the file's pixels as Godot
## decodes them, image row 0 at the north edge (never flipped or resized). Every refusal is one
## push_error "SurroundingsGrid: <manifest path>: <problem>" and a null result. The heights' file
## messages end with ReleaseBuild.file_hint("python -m mattini surroundings"), the colour's with
## ReleaseBuild.file_hint("python -m mattini farcolour"), so an exported build tells the player
## to download the release folder again. A block that is null names every command that builds it.
## The world guard names what differs: "its origin differs" for the origin, "its height offset
## differs" for the height offset (design §3: the 0.5.0 batches' residue, fixed for this reader).
##
## Does NOT prove: that the loader puts this texture on the mesh at the right UVs
## (test_m4_07_surroundings_loader.gd); that the colour is right (brief v0.6.0-06 makes it; the
## fixture's is a designed placeholder); that the real village's 4200 × 4300 JPEG decodes in
## time (the main scene's run, brief v0.6.0-09); what an exported build shows (the release
## template ignores --script).

const SCRATCH_DIR := "user://test_v060_08_surroundings_colour"
const HEIGHTS_COMMAND := "python -m mattini surroundings"
const COLOUR_COMMAND := "python -m mattini farcolour"
const RELEASE_HINT := "; it ships in the release's packs: download the release folder again"
const FIXTURE_DIR := "tests/shared/surroundings_fixture/generated"
const F32 := "surroundings/fixture.f32"
const JPG := "surroundings/fixture_colour.jpg"
## Godot's decode of the fixture's north-west pixel against its design (60, 90, 150): JPEG's
## loss at quality 92 on a smooth gradient stays under this, in 8-bit steps.
const DESIGN_TOLERANCE := 8

var _cases := 0


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


func _manifest_path() -> String:
	return _repo_file(FIXTURE_DIR.path_join("manifest.json"))


func _parse(path: String) -> Dictionary:
	var json := JSON.new()
	assert_eq(json.parse(FileAccess.get_file_as_string(path)), OK, "%s parses" % path)
	return json.data if typeof(json.data) == TYPE_DICTIONARY else {}


func _fixture_bytes(rel: String) -> PackedByteArray:
	return FileAccess.get_file_as_bytes(_repo_file(FIXTURE_DIR.path_join(rel)))


func _sha256(data: PackedByteArray) -> String:
	var context := HashingContext.new()
	context.start(HashingContext.HASH_SHA256)
	context.update(data)
	return context.finish().hex_encode()


func after_each() -> void:
	ReleaseBuild.set_exported_for_tests(null)


func after_all() -> void:
	_remove_tree(SCRATCH_DIR)


func _remove_tree(dir: String) -> void:
	for sub in DirAccess.get_directories_at(dir):
		_remove_tree(dir.path_join(sub))
	for file in DirAccess.get_files_at(dir):
		DirAccess.remove_absolute(dir.path_join(file))
	DirAccess.remove_absolute(dir)


## Writes a copy of the fixture's generated folder whose manifest is changed by [param change]
## and whose heights and colour files are [param f32] and [param jpg] (null leaves a file out;
## an empty array keeps the fixture's); returns the manifest's path.
func _write_case(
	change: Callable, f32: Variant = PackedByteArray(), jpg: Variant = PackedByteArray()
) -> String:
	_cases += 1
	var dir := SCRATCH_DIR.path_join("case_%d" % _cases)
	DirAccess.make_dir_recursive_absolute(dir.path_join("surroundings"))
	var manifest := _parse(_manifest_path())
	change.call(manifest)
	var out := FileAccess.open(dir.path_join("manifest.json"), FileAccess.WRITE)
	out.store_string(JSON.stringify(manifest, "  ", true, true))
	out.close()
	for pair in [[F32, f32], [JPG, jpg]]:
		if pair[1] == null:
			continue
		var bytes: PackedByteArray = pair[1] if not pair[1].is_empty() else _fixture_bytes(pair[0])
		var file := FileAccess.open(dir.path_join(pair[0]), FileAccess.WRITE)
		file.store_buffer(bytes)
		file.close()
	return dir.path_join("manifest.json")


func _unchanged() -> Callable:
	return func(_m: Dictionary) -> void: pass


func _set_key(key: String, value: Variant) -> Callable:
	return func(m: Dictionary) -> void: m["surroundings"][key] = value


## The case at [param path] is refused: null, and exactly one push_error naming the path and
## every text of [param needles], which is marked handled.
func _assert_refused(path: String, why: String, needles: Array, world: WorldConfig = null) -> void:
	if world == null:
		world = WorldConfig.from_manifest(path)
	assert_not_null(world, "%s: the case's world block itself is valid" % why)
	var grid := SurroundingsGrid.from_manifest(path, world)
	assert_null(grid, "%s is refused" % why)
	var naming := 0
	var found := false
	for error in get_errors():
		if error.handled or not error.is_push_error() or not error.contains_text(path):
			continue
		naming += 1
		error.handled = true
		if error.contains_text("SurroundingsGrid: %s: " % path):
			var all := true
			for needle: String in needles:
				all = all and error.contains_text(needle)
			found = found or all
	assert_eq(naming, 1, "%s: one push_error names %s" % [why, path])
	assert_true(found, "%s: it reads 'SurroundingsGrid: %s: …' with %s" % [why, path, needles])


func test_the_fixture_colour_is_read_as_designed() -> void:
	var path := _manifest_path()
	var grid := SurroundingsGrid.from_manifest(path, WorldConfig.from_manifest(path))
	assert_not_null(grid, "the fixture's surroundings are read")
	if grid == null:
		return
	assert_eq([grid.colour_columns, grid.colour_rows, grid.colour_cell_m], [15, 18, 1000.0])
	assert_eq(grid.filled_fraction, 0.2, "the share of placeholder pixels, as the block says")
	assert_eq(grid.colour_dataset, "swissimage_far")
	assert_eq(grid.colour_edition, "2023")
	assert_eq(grid.colour_attribution, "© swisstopo (synthetic test colours, not SWISSIMAGE data)")
	assert_not_null(grid.colour_texture, "the colour is a texture")
	if grid.colour_texture == null:
		return
	var image := grid.colour_texture.get_image()
	assert_eq(image.get_size(), Vector2i(15, 18), "the texture is the block's colour size")
	assert_eq(image.get_format(), Image.FORMAT_RGB8, "RGB8")
	assert_true(image.has_mipmaps(), "the texture has mipmaps (it is seen from 30 km)")


func test_the_texture_is_the_file_s_pixels_unflipped() -> void:
	var path := _manifest_path()
	var grid := SurroundingsGrid.from_manifest(path, WorldConfig.from_manifest(path))
	assert_not_null(grid, "the fixture's surroundings are read")
	if grid == null or grid.colour_texture == null:
		return
	var decoded := Image.new()
	assert_eq(decoded.load_jpg_from_buffer(_fixture_bytes(JPG)), OK, "the test decodes the JPEG")
	var level0 := grid.colour_texture.get_image()
	level0.clear_mipmaps()
	assert_eq(level0.get_data(), decoded.get_data(), "level 0 is the file's pixels, row 0 north")
	# The design: pixel (c, r) = (60 + 9c + 2r, 90 + 5r, 150 − 4c + 3r); the north-west corner
	# and the south-east corner tell a flip in either axis.
	var corners := {Vector2i(0, 0): [60, 90, 150], Vector2i(14, 17): [220, 175, 145]}
	for at: Vector2i in corners:
		var found := level0.get_pixelv(at)
		var want: Array = corners[at]
		var off := maxi(
			maxi(absi(found.r8 - want[0]), absi(found.g8 - want[1])), absi(found.b8 - want[2])
		)
		assert_true(off <= DESIGN_TOLERANCE, "pixel %s is %s, designed %s" % [at, found, want])


func test_no_surroundings_built_names_every_command() -> void:
	var path := _write_case(func(m: Dictionary) -> void: m["surroundings"] = null)
	_assert_refused(
		path,
		"no surroundings block",
		[
			"python -m mattini download regio",
			"python -m mattini download farphoto",
			HEIGHTS_COMMAND,
			COLOUR_COMMAND
		]
	)


func test_a_world_config_with_another_height_offset_is_refused_naming_it() -> void:
	var other := _write_case(func(m: Dictionary) -> void: m["world"]["height_offset_m"] = 1250.5)
	var path := _write_case(_unchanged())
	var world := WorldConfig.from_manifest(other)
	_assert_refused(path, "another height offset", ["its height offset differs"], world)


func test_a_world_config_with_another_origin_is_refused_naming_it() -> void:
	var move := func(m: Dictionary) -> void: m["world"]["origin_lv95"]["n"] = 1101751.0
	var other := _write_case(move)
	var path := _write_case(_unchanged())
	var world := WorldConfig.from_manifest(other)
	_assert_refused(path, "another origin", ["its origin differs"], world)


func test_another_colour_format_is_refused() -> void:
	_assert_refused(_write_case(_set_key("colour_format", "png")), "a PNG", ["colour_format"])


func test_a_colour_cell_that_is_not_a_positive_number_is_refused() -> void:
	var path := _write_case(_set_key("colour_cell_m", "1000"))
	_assert_refused(path, "a text cell", ["colour_cell_m"])
	path = _write_case(_set_key("colour_cell_m", 0.0))
	_assert_refused(path, "a cell of 0 m", ["colour_cell_m"])


func test_colour_columns_or_rows_that_do_not_fit_the_box_are_refused() -> void:
	# 14 pixels of 1000 m in a 15 km box: a texture stretched 7 % east-west.
	var path := _write_case(_set_key("colour_columns", 14.0))
	_assert_refused(path, "14 colour columns", ["colour_columns"])
	_assert_refused(_write_case(_set_key("colour_rows", 17.0)), "17 colour rows", ["colour_rows"])


func test_a_colour_wider_than_the_renderer_draws_is_refused() -> void:
	# 20000 pixels of 0.75 m fit the 15 km box, but Compatibility draws such a texture black.
	var wide := func(m: Dictionary) -> void:
		m["surroundings"]["colour_columns"] = 20000.0
		m["surroundings"]["colour_cell_m"] = 0.75
		m["surroundings"]["colour_rows"] = 24000.0
	_assert_refused(_write_case(wide), "a colour 20000 pixels wide", ["16384"])


func test_another_colour_dataset_or_source_key_set_is_refused() -> void:
	var change := func(m: Dictionary) -> void:
		m["surroundings"]["colour_source"]["dataset"] = "swissimage"
	_assert_refused(_write_case(change), "the near photo's dataset", ["swissimage_far"])
	change = func(m: Dictionary) -> void:
		m["surroundings"]["colour_source"]["entry_sha256"] = "0".repeat(64)
	_assert_refused(_write_case(change), "a colour source with a key too many", ["colour_source"])


func test_a_filled_fraction_outside_0_to_1_is_refused() -> void:
	var path := _write_case(_set_key("filled_fraction", 1.5))
	_assert_refused(path, "a share of 1.5", ["filled_fraction"])
	path = _write_case(_set_key("filled_fraction", "0.2"))
	_assert_refused(path, "a text share", ["filled_fraction"])


func test_a_colour_digest_that_is_not_hex_is_refused() -> void:
	var path := _write_case(_set_key("colour_sha256", "z".repeat(64)))
	_assert_refused(path, "a colour SHA-256 of z", ["colour_sha256"])
	path = _write_case(_set_key("colour_pixels_sha256", 5.0))
	_assert_refused(path, "a numeric pixels SHA-256", ["colour_pixels_sha256"])


func test_a_colour_file_outside_the_manifest_s_folder_is_refused() -> void:
	var path := _write_case(_set_key("colour_file", "../surroundings/fixture_colour.jpg"))
	_assert_refused(path, "a colour path leaving the folder", ["colour_file"])


func test_a_missing_colour_file_is_refused_naming_its_command() -> void:
	var path := _write_case(_unchanged(), PackedByteArray(), null)
	_assert_refused(path, "a missing colour", ["fixture_colour.jpg", COLOUR_COMMAND])


func test_a_damaged_colour_file_is_refused() -> void:
	var jpg := _fixture_bytes(JPG)
	jpg[400] = jpg[400] ^ 1
	var path := _write_case(_unchanged(), PackedByteArray(), jpg)
	_assert_refused(path, "one bit of the colour flipped", ["SHA-256", COLOUR_COMMAND])


func test_a_colour_of_another_size_is_refused() -> void:
	# A valid JPEG one row short, its SHA-256 recorded: only the decoded size can refuse it.
	var image := Image.create(15, 17, false, Image.FORMAT_RGB8)
	image.fill(Color8(60, 90, 150))
	var jpg := image.save_jpg_to_buffer(0.92)
	var path := _write_case(_set_key("colour_sha256", _sha256(jpg)), PackedByteArray(), jpg)
	_assert_refused(path, "a colour of 15 x 17", ["fixture_colour.jpg", COLOUR_COMMAND])


func test_the_file_messages_end_with_the_release_hint_in_an_export() -> void:
	# _read returns the problem without a push_error (every reader's shape), so no ERROR line.
	var world := WorldConfig.from_manifest(_manifest_path())
	var cases := {
		"the heights missing": [_write_case(_unchanged(), null), HEIGHTS_COMMAND],
		"the colour missing": [_write_case(_unchanged(), PackedByteArray(), null), COLOUR_COMMAND],
	}
	for why: String in cases:
		var path: String = cases[why][0]
		ReleaseBuild.set_exported_for_tests(false)
		var problem := SurroundingsGrid.new()._read(path, world)
		assert_string_contains(problem, "%s rebuilds it" % cases[why][1], false)
		ReleaseBuild.set_exported_for_tests(true)
		problem = SurroundingsGrid.new()._read(path, world)
		assert_true(problem.ends_with(RELEASE_HINT), "%s, exported: %s" % [why, problem])
		assert_false(problem.contains("rebuilds it"), "%s, exported: no pipeline hint" % why)
