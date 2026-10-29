extends GutTest
## Fixer's tests for brief v0.4.0-02 (the prover's vacuous-gate findings), beside the pinned
## test_surface_flow.gd, which stays byte-identical. They call SurfaceGrid's string-returning
## steps (_place, _read_flow, _make_flow, _read_image, _make_texture) directly, so no case pushes
## an error. Each case fails on the mutation it is named for.
##
## Does NOT prove: anything about the shader or the look of the flow (brief v0.4.0-03).

const FIXTURE_DIR := "tests/shared/surfaces_fixture/generated"
const SCRATCH_DIR := "user://test_surface_flow_fixes"


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


func _manifest_path() -> String:
	return _repo_file(FIXTURE_DIR.path_join("manifest.json"))


func _manifest() -> Dictionary:
	var json := JSON.new()
	assert_eq(json.parse(FileAccess.get_file_as_string(_manifest_path())), OK)
	return json.data


func _world() -> WorldConfig:
	return WorldConfig.from_manifest(_manifest_path())


func after_all() -> void:
	DirAccess.remove_absolute(SCRATCH_DIR.path_join("manifest.json"))
	DirAccess.remove_absolute(SCRATCH_DIR)


## The fixture's box (40 × 30 m): the classes 200 × 150 at [param cell] / 10, the flow 20 × 15 at
## [param flow_cell].
func _grid_with(cell: float, flow_cell: float) -> SurfaceGrid:
	var grid := SurfaceGrid.new()
	grid.columns = 200
	grid.rows = 150
	grid.cell_m = cell / 10.0
	grid.flow_columns = 20
	grid.flow_rows = 15
	grid.flow_cell_m = flow_cell
	return grid


func _box() -> Dictionary:
	return {"e_min": 2700000.0, "e_max": 2700040.0, "n_min": 1200000.0, "n_max": 1200030.0}


# Mutation E22: the flow's fit tolerance widened to 1 m. Half a metre off is refused, within
# BOX_TOLERANCE_M it is accepted; the classes' fit, the same pattern, is held the same way.
func test_the_flow_fit_tolerance_is_the_box_tolerance() -> void:
	var world := _world()
	assert_eq(_grid_with(2.0, 2.0)._place(_box(), world), "", "an exact fit is accepted")
	assert_eq(_grid_with(2.0, 2.0 + 0.00001)._place(_box(), world), "", "flow within tolerance")
	assert_eq(_grid_with(2.0 + 0.00001, 2.0)._place(_box(), world), "", "classes within tolerance")
	var flow_off := _grid_with(2.0, 2.025)._place(_box(), world)
	assert_true(flow_off.contains("surfaces.flow.columns and rows"), "0.5 m off: %s" % flow_off)
	var classes_off := _grid_with(2.025, 2.0)._place(_box(), world)
	assert_true(classes_off.contains("do not fit lv95_box"), "classes 0.5 m off: %s" % classes_off)
	var just_over := _grid_with(2.0, 2.0 + 0.00006)._place(_box(), world)
	assert_true(just_over.contains("do not fit"), "1.2 mm off is over the tolerance")


# Mutations E23 and E24: an upper-case digest in the block is read as its lower-case. The
# classes' pair (the same pattern) is held too.
func test_upper_case_digests_are_accepted() -> void:
	var manifest := _manifest()
	var folder := _manifest_path().get_base_dir()
	var world := _world()
	var flow: Dictionary = manifest["surfaces"]["flow"].duplicate()
	flow["sha256"] = flow["sha256"].to_upper()
	flow["pixels_sha256"] = flow["pixels_sha256"].to_upper()
	assert_eq(_grid_with(2.0, 2.0)._read_flow(folder, flow, world), "", "flow digests, upper case")
	var only_pixels: Dictionary = manifest["surfaces"]["flow"].duplicate()
	only_pixels["pixels_sha256"] = only_pixels["pixels_sha256"].to_upper()
	assert_eq(_grid_with(2.0, 2.0)._read_flow(folder, only_pixels, world), "", "pixels only")
	var only_file: Dictionary = manifest["surfaces"]["flow"].duplicate()
	only_file["sha256"] = only_file["sha256"].to_upper()
	assert_eq(_grid_with(2.0, 2.0)._read_flow(folder, only_file, world), "", "file digest only")
	var surfaces: Dictionary = manifest["surfaces"].duplicate()
	surfaces["sha256"] = surfaces["sha256"].to_upper()
	surfaces["pixels_sha256"] = surfaces["pixels_sha256"].to_upper()
	assert_eq(_grid_with(2.0, 2.0)._read_image(folder, surfaces), "", "class digests, upper case")
	var class_pixels: Dictionary = manifest["surfaces"].duplicate()
	class_pixels["pixels_sha256"] = class_pixels["pixels_sha256"].to_upper()
	assert_eq(_grid_with(2.0, 2.0)._read_image(folder, class_pixels), "", "class pixels only")
	var class_file: Dictionary = manifest["surfaces"].duplicate()
	class_file["sha256"] = class_file["sha256"].to_upper()
	assert_eq(_grid_with(2.0, 2.0)._read_image(folder, class_file), "", "class file only")


func _png_of(width: int, height: int) -> PackedByteArray:
	return Image.create_empty(width, height, false, Image.FORMAT_L8).save_png_to_buffer()


# Mutation E26: the size check compares the width only. A PNG of the right width and another
# height is refused, for the flow and for the classes (the same pattern).
func test_a_png_of_the_right_width_and_another_height_is_refused() -> void:
	var world := _world()
	var zeros := "0".repeat(64)
	var short := _png_of(20, 14)
	var flow_problem := _grid_with(2.0, 2.0)._make_flow(short, "x-flow.png", zeros, world)
	assert_true(flow_problem.contains("decodes to 20 × 14 pixels"), "flow: %s" % flow_problem)
	var class_short := _png_of(200, 149)
	var class_problem := _grid_with(2.0, 2.0)._make_texture(class_short, "x.png", zeros)
	assert_true(
		class_problem.contains("decodes to 200 × 149 pixels"), "classes: %s" % class_problem
	)
	var tall := _png_of(20, 16)
	assert_true(_grid_with(2.0, 2.0)._make_flow(tall, "x", zeros, world).contains("× 16"))
	var class_tall := _png_of(200, 151)
	assert_true(_grid_with(2.0, 2.0)._make_texture(class_tall, "x", zeros).contains("× 151"))


## A world whose manifest maps x = -e, y = +h, z = +n: a proper rotation other than the
## fixture's own, written under user:// and read through WorldConfig.from_manifest.
func _rotated_world() -> WorldConfig:
	var manifest := _manifest()
	manifest["world"]["axes"] = {"x": "-e", "y": "+h", "z": "+n"}
	DirAccess.make_dir_recursive_absolute(SCRATCH_DIR)
	var path := SCRATCH_DIR.path_join("manifest.json")
	var out := FileAccess.open(path, FileAccess.WRITE)
	out.store_string(JSON.stringify(manifest, "  ", true, true))
	out.close()
	return WorldConfig.from_manifest(path)


# Mutation E13 (Hard Rule 4): the colour table is made through WorldConfig.to_local, not from a
# hard-coded (sin b, -cos b). Under x = -e, z = +n the local direction of the bearing b is
# (-sin b, +cos b), so bearing 90 (code 61, east) reads R = 1, G = 128 and bearing 0 (code 1,
# north) reads R = 128, G = 255; every code is within one byte of the independent formula.
func test_the_colours_follow_the_worlds_axes() -> void:
	var world := _rotated_world()
	assert_not_null(world, "the rotated world is read")
	if world == null:
		return
	var colours := SurfaceGrid._flow_colours(world)
	assert_eq(colours.size(), 3 * 241, "three bytes per code")
	assert_eq([colours[3], colours[4], colours[5]], [128, 255, 255], "north is +z here")
	assert_eq([colours[183], colours[184], colours[185]], [1, 128, 255], "east is -x here")
	for k in range(1, SurfaceGrid.FLOW_CODES + 1):
		var bearing := deg_to_rad((k - 1) * SurfaceGrid.FLOW_STEP_DEG)
		assert_almost_eq(float(colours[3 * k]), 128.0 + 127.0 * -sin(bearing), 1.0, "R of %d" % k)
		assert_almost_eq(
			float(colours[3 * k + 1]), 128.0 + 127.0 * cos(bearing), 1.0, "G of %d" % k
		)
