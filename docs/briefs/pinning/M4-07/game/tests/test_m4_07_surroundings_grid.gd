extends GutTest
## Pinning tests for brief M4-07: SurroundingsGrid reads the manifest's surroundings block and
## its heights file, checked, and places the grid through WorldConfig.
##
## Pinned decisions (m4-design §2 and §7; brief M4-02's files): the block is the description
## the surroundings step writes, verbatim, with exactly the keys area, columns, cut_box, file,
## format ("f32-le"), lv95_box, rows, sha256, source {attribution, collection, dataset
## ("swissaltiregio"), edition, entry_sha256}, spacing_m and world_sha256. Its file holds
## columns x rows little-endian float32 local heights, rows north to south, columns west to
## east, NaN at the vertices strictly inside cut_box. Row r, column c is the vertex at LV95
## (e_min + c·s, n_max − r·s); x_min and z_min are WorldConfig.to_local of the box's
## north-west corner, never an origin subtracted in this reader; only the owner's axes are
## accepted. The shared fixture (tests/shared/surroundings_fixture/generated/, its vectors in
## tests/shared/surroundings_vectors.json, design's, computed two independent ways) is read
## as the pipeline writes it: 6 columns x 7 rows at 3000 m, 6 NaN.
## Every problem is refused with one push_error "SurroundingsGrid: <manifest path>: <problem>"
## and a null result, never a plausible grid (Hard Rule 2). Each value read from the manifest
## is compared through ManifestValue (brain.md H26: a value of another type is refused, not a
## runtime error that lets the block through). The refusals the owner fixes by re-running the
## pipeline name `python -m mattini surroundings`.
##
## Does NOT prove: that the mesh is built from these heights in the right place
## (test_m4_07_surroundings_loader.gd); that the real village's file reads the same way (the
## main scene's run, M4-10); that the shadows land right (no GPU; the owner's PC).

const SCRATCH_DIR := "user://test_m4_07_surroundings_grid"
const COMMAND := "python -m mattini surroundings"
const FIXTURE_DIR := "tests/shared/surroundings_fixture/generated"
const F32 := "surroundings/fixture.f32"

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
	return _parse(_repo_file("tests/shared/surroundings_vectors.json"))


func _fixture_f32() -> PackedByteArray:
	return FileAccess.get_file_as_bytes(_repo_file(FIXTURE_DIR.path_join(F32)))


func _read_fixture() -> SurroundingsGrid:
	var path := _manifest_path()
	return SurroundingsGrid.from_manifest(path, WorldConfig.from_manifest(path))


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


func test_the_fixture_grid_is_read_as_designed() -> void:
	var grid := _read_fixture()
	assert_not_null(grid, "the fixture's surroundings are read")
	if grid == null:
		return
	assert_eq(grid.area, "fixture")
	assert_eq([grid.columns, grid.rows, grid.spacing_m], [6, 7, 3000.0])
	assert_eq(grid.dataset, "swissaltiregio")
	assert_eq(grid.edition, "2026-06")
	assert_eq(grid.attribution, "© swisstopo (synthetic test heights, not swissALTIRegio data)")
	# E 2613000 − 2618250 and −(N 1110000 − 1101750), through WorldConfig.
	assert_eq([grid.x_min, grid.z_min], [-5250.0, -8250.0], "the north-west corner, local")
	assert_eq(grid.heights.size(), 42, "one height per vertex")
	assert_eq(
		grid.heights.to_byte_array(), _fixture_f32(), "the heights are the file's, byte for byte"
	)
	var nan := 0
	for value in grid.heights:
		if is_nan(value):
			nan += 1
	assert_eq(nan, 6, "the cut's six vertices are NaN")
	assert_eq(
		grid.cut_box,
		{"e_max": 2625000.0, "e_min": 2616000.0, "n_max": 1107000.0, "n_min": 1095000.0},
		"the area box the pipeline cut"
	)


func test_every_named_vertex_has_its_height() -> void:
	var grid := _read_fixture()
	assert_not_null(grid, "the fixture's surroundings are read")
	if grid == null:
		return
	var vertices: Array = _vectors()["vertices"]
	assert_eq(vertices.size(), 14, "the vectors name 14 vertices")
	for v: Dictionary in vertices:
		var name := "row %d, column %d" % [v["row"], v["column"]]
		var found := grid.height(int(v["column"]), int(v["row"]))
		if v["local_y"] == null:
			assert_true(is_nan(found), "%s is in the cut: NaN, found %s" % [name, found])
		else:
			assert_eq(found, float(v["local_y"]), name)


## Writes a copy of the fixture's generated folder whose manifest is changed by
## [param change] (a Callable taking the manifest Dictionary) and whose heights file is
## [param f32] (null leaves it out; an empty array keeps the fixture's); returns its path.
func _write_case(change: Callable, f32: Variant = PackedByteArray()) -> String:
	_cases += 1
	var dir := SCRATCH_DIR.path_join("case_%d" % _cases)
	DirAccess.make_dir_recursive_absolute(dir.path_join("surroundings"))
	var manifest := _parse(_manifest_path())
	change.call(manifest)
	var out := FileAccess.open(dir.path_join("manifest.json"), FileAccess.WRITE)
	out.store_string(JSON.stringify(manifest, "  ", true, true))
	out.close()
	if f32 != null:
		var bytes: PackedByteArray = f32 if not f32.is_empty() else _fixture_f32()
		var file := FileAccess.open(dir.path_join(F32), FileAccess.WRITE)
		file.store_buffer(bytes)
		file.close()
	return dir.path_join("manifest.json")


## The case at [param path] is refused: null, and exactly one push_error naming the path (and
## [param needle], when given), which is marked handled.
func _assert_refused(path: String, why: String, needle := "", world: WorldConfig = null) -> void:
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
			found = found or needle == "" or error.contains_text(needle)
	assert_eq(naming, 1, "%s: one push_error names %s" % [why, path])
	assert_true(found, "%s: it reads 'SurroundingsGrid: %s: …%s…'" % [why, path, needle])


func _set_key(key: String, value: Variant) -> Callable:
	return func(m: Dictionary) -> void: m["surroundings"][key] = value


func test_no_surroundings_built_names_the_command() -> void:
	var path := _write_case(func(m: Dictionary) -> void: m["surroundings"] = null)
	_assert_refused(path, "no surroundings block", COMMAND)


func test_surroundings_built_for_another_world_are_refused() -> void:
	var path := _write_case(_set_key("world_sha256", "0".repeat(64)))
	_assert_refused(path, "another world's surroundings", COMMAND)


func test_a_world_sha256_of_another_type_is_refused() -> void:
	# brain.md H26: `!=` between a float and a String is a runtime error that let a block of
	# M3's readers through; ManifestValue.differs refuses it.
	var path := _write_case(_set_key("world_sha256", 5.0))
	_assert_refused(path, "a numeric world_sha256", "world_sha256")


func test_a_rotated_world_is_refused() -> void:
	var rotate := func(m: Dictionary) -> void:
		m["world"]["axes"] = {"x": "+n", "y": "+h", "z": "+e"}
	_assert_refused(_write_case(rotate), "a world without the owner's axes", "axes")


func test_a_world_config_of_another_manifest_is_refused() -> void:
	var other := _repo_file("tests/shared/surfaces_fixture/generated/manifest.json")
	var path := _write_case(func(_m: Dictionary) -> void: pass)
	_assert_refused(
		path,
		"another manifest's WorldConfig",
		"not read from this manifest",
		WorldConfig.from_manifest(other)
	)


func test_another_format_is_refused() -> void:
	_assert_refused(_write_case(_set_key("format", "f32-be")), "another format", "format")


func test_a_block_with_another_key_set_is_refused() -> void:
	var path := _write_case(_set_key("cell_m", 3000.0))
	_assert_refused(path, "a block with a key too many", "cell_m")


func test_another_dataset_is_refused() -> void:
	var change := func(m: Dictionary) -> void:
		m["surroundings"]["source"]["dataset"] = "swissalti3d"
	_assert_refused(_write_case(change), "another dataset", "swissaltiregio")


func test_a_spacing_of_another_type_is_refused() -> void:
	_assert_refused(_write_case(_set_key("spacing_m", "3000")), "a text spacing", "spacing_m")


func test_columns_that_do_not_fit_the_box_are_refused() -> void:
	# 5 columns of 3000 m in a 15 km box: a reader that trusts the count reads a sheared grid.
	_assert_refused(_write_case(_set_key("columns", 5.0)), "5 columns in a 15 km box", "columns")


func test_rows_that_do_not_fit_the_box_are_refused() -> void:
	_assert_refused(_write_case(_set_key("rows", 6.0)), "6 rows in an 18 km box", "rows")


func test_a_cut_box_outside_the_box_is_refused() -> void:
	var change := func(m: Dictionary) -> void: m["surroundings"]["cut_box"]["e_max"] = 2631000.0
	_assert_refused(_write_case(change), "a cut reaching past the box", "cut_box")


func test_a_file_outside_the_manifest_s_folder_is_refused() -> void:
	var path := _write_case(_set_key("file", "../surroundings/fixture.f32"))
	_assert_refused(path, "a path leaving the folder", "file")


func test_a_missing_file_is_refused_naming_the_command() -> void:
	var path := _write_case(func(_m: Dictionary) -> void: pass, null)
	_assert_refused(path, "a missing heights file", "fixture.f32")
	# Its message names the step that rebuilds it.
	path = _write_case(func(_m: Dictionary) -> void: pass, null)
	_assert_refused(path, "a missing heights file", COMMAND)


func test_a_file_of_another_size_is_refused() -> void:
	# One float short, its SHA-256 recorded: only the size check can refuse it.
	var short := _fixture_f32().slice(0, 164)
	var path := _write_case(_set_key("sha256", _sha256(short)), short)
	_assert_refused(path, "a heights file of 164 bytes", "164")


func test_a_damaged_file_is_refused() -> void:
	var f32 := _fixture_f32()
	f32[20] = f32[20] ^ 1
	_assert_refused(
		_write_case(func(_m: Dictionary) -> void: pass, f32), "one bit flipped", "SHA-256"
	)
