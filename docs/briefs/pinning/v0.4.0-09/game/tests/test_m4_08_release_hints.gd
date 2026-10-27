extends GutTest
## Pinning tests for brief v0.3.1-03 (M4-08 decisions 2 and 3): in an exported build, a reader
## that finds a generated file missing or damaged tells the player to download the release
## folder again, not to run the pipeline (FB-005).
##
## Pinned decisions (brief v0.3.1-03, from M4-08): ReleaseBuild
## (res://scripts/world/release_build.gd) answers "is this an exported build" for DataPacks and
## the readers' file messages: is_exported() is OS.has_feature("template") unless a test has
## called set_exported_for_tests(true or false); set_exported_for_tests(null) gives the question
## back to the OS, whatever was set before. file_hint(command) is the end of every reader
## message about a generated file: outside an export "; <command> rebuilds it", as before; in an
## export "; it ships in the release's packs: download the release folder again" (the photo and
## the heights ship in the data packs, the rest in mattini.pck: both are the release's packs).
## Every reader site that used to write "; <command> rebuilds it" calls file_hint: TerrainGrid
## (the heights), PhotoGrid (the JPEG; its decoding), SurfaceGrid (the PNG; its decoding; from
## brief v0.4.0-02 the flow PNG and its decoding too), TreeChunks and BuildingChunks (a chunk
## file). BuildingRoofs reads no file of its own. The
## readers are called through _read(path, world), which returns the problem without a
## push_error, so this script prints no ERROR line.
##
## The census at the end is text only: no script under res://scripts but release_build.gd
## spells "rebuilds it" itself.
##
## Since brief v0.4.0-09 (the owner's "4d" of 2026-10-27, 0.3.1 R1 F6; only the census and this
## paragraph change): the census skips no reader. The two paths it used to skip by name until
## M4-10, surroundings_grid.gd (SurroundingsGrid, the far mountains, M4-07) and shadow_grid.gd
## (CaptureShadowGrid, the photo's capture mask, M4-06), belong to a later release and do not
## exist yet; from their first commit they must call file_hint like every other reader (M4-10
## decision 6), or this census names them.
##
## Does NOT prove: that an exported build shows these messages (the release template ignores
## --script; the release gate's export run starts the Linux build with mattini-photo.pck moved
## aside and reads PhotoGrid's line); main.gd's error panel and its own hints (brief v0.3.1-05
## moves the panel onto ReleaseBuild, M4-10 decision 5); the "not built" and "another world"
## refusals, which still name the pipeline (a release ships a manifest whose blocks are built
## for its world; tools/export.sh refuses any other).

const SCRATCH_DIR := "user://test_m4_08_release_hints"
const RELEASE_HINT := "; it ships in the release's packs: download the release folder again"
const SHARED := "tests/shared"

var _cases := 0


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


func _parse(path: String) -> Dictionary:
	var json := JSON.new()
	assert_eq(json.parse(FileAccess.get_file_as_string(path)), OK, "%s parses" % path)
	return json.data if typeof(json.data) == TYPE_DICTIONARY else {}


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


func _sha256(data: PackedByteArray) -> String:
	var context := HashingContext.new()
	context.start(HashingContext.HASH_SHA256)
	context.update(data)
	return context.finish().hex_encode()


## A copy of [param fixture]'s manifest, changed by [param change], with [param files]
## (relative path -> bytes) beside it and nothing else; returns its path.
func _write_case(fixture: String, change: Callable, files := {}) -> String:
	_cases += 1
	var dir := SCRATCH_DIR.path_join("case_%d" % _cases)
	DirAccess.make_dir_recursive_absolute(dir)
	var manifest := _parse(
		_repo_file(SHARED.path_join(fixture).path_join("generated/manifest.json"))
	)
	change.call(manifest)
	var out := FileAccess.open(dir.path_join("manifest.json"), FileAccess.WRITE)
	out.store_string(JSON.stringify(manifest, "  ", true, true))
	out.close()
	for rel: String in files:
		DirAccess.make_dir_recursive_absolute(dir.path_join(rel).get_base_dir())
		var file := FileAccess.open(dir.path_join(rel), FileAccess.WRITE)
		file.store_buffer(files[rel])
		file.close()
	return dir.path_join("manifest.json")


func _keep(_m: Dictionary) -> void:
	pass


## The problem [param reader] (a new reader object) finds in the case at [param path], in an
## exported build ([param exported] true) or not.
func _problem(reader: Object, path: String, exported: bool) -> String:
	ReleaseBuild.set_exported_for_tests(exported)
	var world := WorldConfig.from_manifest(path)
	assert_not_null(world, "%s: its world block is valid" % path)
	var problem: String = reader.call("_read", path, world)
	ReleaseBuild.set_exported_for_tests(null)
	return problem


## The case is refused naming [param needle]; with the pipeline's hint outside an export and
## the release's in one.
func _assert_hints(make_reader: Callable, path: String, needle: String, command: String) -> void:
	var developer := _problem(make_reader.call(), path, false)
	assert_string_contains(developer, needle)
	assert_true(
		developer.ends_with("; %s rebuilds it" % command),
		"outside an export it names %s: %s" % [command, developer]
	)
	var player := _problem(make_reader.call(), path, true)
	assert_string_contains(player, needle)
	assert_true(player.ends_with(RELEASE_HINT), "in an export it says download: %s" % player)
	assert_false(player.contains("python -m mattini"), "and names no pipeline: %s" % player)


func test_the_seam_follows_the_os_unless_a_test_sets_it() -> void:
	assert_false(OS.has_feature("template"), "this test run is not an exported build")
	assert_false(ReleaseBuild.is_exported(), "so the seam says no")
	ReleaseBuild.set_exported_for_tests(true)
	assert_true(ReleaseBuild.is_exported(), "a test may say yes")
	assert_eq(ReleaseBuild.file_hint("python -m mattini x"), RELEASE_HINT)
	ReleaseBuild.set_exported_for_tests(false)
	assert_eq(ReleaseBuild.file_hint("python -m mattini x"), "; python -m mattini x rebuilds it")
	ReleaseBuild.set_exported_for_tests(null)
	assert_false(ReleaseBuild.is_exported(), "null gives the question back to the OS")
	ReleaseBuild.set_exported_for_tests(true)
	ReleaseBuild.set_exported_for_tests(null)
	assert_false(ReleaseBuild.is_exported(), "null after yes gives the question back too")
	assert_eq(ReleaseBuild.file_hint("python -m mattini x"), "; python -m mattini x rebuilds it")


func test_terrain_heights_missing() -> void:
	var path := _write_case("terrain_fixture", _keep)
	_assert_hints(TerrainGrid.new, path, "fixture.f32 is missing", "python -m mattini terrain")


func test_photo_missing() -> void:
	var path := _write_case("photo_fixture", _keep)
	_assert_hints(PhotoGrid.new, path, "fixture.jpg is missing", "python -m mattini photo")


func test_photo_that_decodes_to_another_size() -> void:
	# A JPEG whose SHA-256 the block records, 8 × 8 pixels: PhotoGrid's second site, the decoding.
	var image := Image.create(8, 8, false, Image.FORMAT_RGB8)
	image.fill(Color(0.4, 0.5, 0.3))
	var jpeg := image.save_jpg_to_buffer()
	var sha := _sha256(jpeg)
	var change := func(m: Dictionary) -> void: m["photo"]["sha256"] = sha
	var path := _write_case("photo_fixture", change, {"photo/fixture.jpg": jpeg})
	_assert_hints(PhotoGrid.new, path, "decodes to 8 × 8", "python -m mattini photo")


func test_surfaces_missing() -> void:
	var path := _write_case("surfaces_fixture", _keep)
	_assert_hints(SurfaceGrid.new, path, "fixture.png is missing", "python -m mattini surfaces")


func test_surfaces_that_decode_to_other_classes() -> void:
	# A PNG whose SHA-256 the block records, one class changed: SurfaceGrid's second site.
	var fixture := _repo_file(SHARED.path_join("surfaces_fixture/generated/surfaces/fixture.png"))
	var image := Image.new()
	assert_eq(image.load_png_from_buffer(FileAccess.get_file_as_bytes(fixture)), OK)
	var pixels := image.get_data()
	pixels[15000] = (pixels[15000] + 1) % 5
	var png := Image.create_from_data(200, 150, false, Image.FORMAT_L8, pixels).save_png_to_buffer()
	var sha := _sha256(png)
	var change := func(m: Dictionary) -> void: m["surfaces"]["sha256"] = sha
	var path := _write_case("surfaces_fixture", change, {"surfaces/fixture.png": png})
	_assert_hints(SurfaceGrid.new, path, "pixels_sha256", "python -m mattini surfaces")


func test_surfaces_flow_missing() -> void:
	# The class PNG there, the flow PNG not (brief v0.4.0-02): SurfaceGrid's flow site.
	var fixture := _repo_file(SHARED.path_join("surfaces_fixture/generated/surfaces/fixture.png"))
	var files := {"surfaces/fixture.png": FileAccess.get_file_as_bytes(fixture)}
	var path := _write_case("surfaces_fixture", _keep, files)
	_assert_hints(
		SurfaceGrid.new, path, "fixture-flow.png is missing", "python -m mattini surfaces"
	)


func test_surfaces_flow_that_decodes_to_other_codes() -> void:
	# A flow PNG whose SHA-256 the block records, one code changed: the flow's decoding site.
	var shared := _repo_file(SHARED.path_join("surfaces_fixture/generated/surfaces"))
	var image := Image.new()
	var flow := FileAccess.get_file_as_bytes(shared.path_join("fixture-flow.png"))
	assert_eq(image.load_png_from_buffer(flow), OK)
	var codes := image.get_data()
	codes[150] = (codes[150] + 1) % 241
	var png := Image.create_from_data(20, 15, false, Image.FORMAT_L8, codes).save_png_to_buffer()
	var sha := _sha256(png)
	var change := func(m: Dictionary) -> void: m["surfaces"]["flow"]["sha256"] = sha
	var files := {
		"surfaces/fixture.png": FileAccess.get_file_as_bytes(shared.path_join("fixture.png")),
		"surfaces/fixture-flow.png": png,
	}
	var path := _write_case("surfaces_fixture", change, files)
	_assert_hints(SurfaceGrid.new, path, "flow.pixels_sha256", "python -m mattini surfaces")


func test_tree_chunk_missing() -> void:
	var path := _write_case("trees_fixture", _keep)
	_assert_hints(TreeChunks.new, path, "is missing", "python -m mattini trees")


func test_building_chunk_missing() -> void:
	var path := _write_case("buildings_fixture", _keep)
	_assert_hints(BuildingChunks.new, path, "is missing", "python -m mattini buildings")


## Every .gd file under [param dir], recursively, as res:// paths.
func _scripts(dir: String) -> PackedStringArray:
	var found := PackedStringArray()
	for sub in DirAccess.get_directories_at(dir):
		found.append_array(_scripts(dir.path_join(sub)))
	for file in DirAccess.get_files_at(dir):
		if file.ends_with(".gd"):
			found.append(dir.path_join(file))
	return found


func test_no_script_spells_the_pipeline_hint_itself() -> void:
	# Text only (lesson 5): the tests above prove the behaviour of each site they reach.
	# No exception but ReleaseBuild itself (brief v0.4.0-09: the far mountains' and the capture
	# mask's readers, when they come, are counted like every other).
	var allowed := ["res://scripts/world/release_build.gd"]
	var scripts := _scripts("res://scripts")
	assert_gt(scripts.size(), 10, "the census reads the game's scripts")
	var spelled := []
	for script in scripts:
		if script in allowed:
			continue
		if FileAccess.get_file_as_string(script).contains("rebuilds it"):
			spelled.append(script)
	assert_eq(spelled, [], "only ReleaseBuild writes the pipeline's hint")
