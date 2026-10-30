extends GutTest
## Brief v0.5.0-04's fix round: what the mutation prover found no test failing for (lesson 51).
##
## Pins decision 1's no-mask rectangle, the shader header's words about the lift (Hard Rule 2:
## a comment never claims what the code does not do) and the loader's rule that the mask belongs
## to the photo look only. Does NOT prove: that the lift looks right, or anything on a GPU.

const LOADER := "res://scripts/terrain/terrain_loader.gd"
const PHOTO_SHADER := "res://shaders/terrain_photo.gdshader"
## What the shader's header says about the lift, each phrase as the code does it.
const HEADER_PHRASES := [
	"the first rule on the photo multiplies its linear colour by 1 + (shadow_lift - 1) * m",
	"0 outside the mask's rectangle and wherever no mask is given",
	"clipped at 1 per channel",
	"the neutral colour outside the photo is never lifted",
]

var _camera: Camera3D
var _no_mask: Terrain3D


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


func before_all() -> void:
	var terrain_manifest := _repo_file("tests/shared/terrain_fixture/generated/manifest.json")
	var grid := TerrainGrid.from_manifest(
		terrain_manifest, WorldConfig.from_manifest(terrain_manifest)
	)
	var photo_manifest := _repo_file("tests/shared/photo_fixture/generated/manifest.json")
	var photo := PhotoGrid.from_manifest(photo_manifest, WorldConfig.from_manifest(photo_manifest))
	_camera = Camera3D.new()
	add_child(_camera)
	if grid != null and photo != null:
		_no_mask = TerrainLoader.create(grid, self, photo)


func after_all() -> void:
	if _no_mask != null:
		_no_mask.free()
	_camera.free()


func test_without_a_mask_its_rectangle_is_the_unit_one() -> void:
	# Decision 1: the no-mask rectangle is (0, 0, 1, 1). With the texel at 0 any rectangle
	# lifts nothing, so only this test holds the value.
	if _no_mask == null:
		fail_test("no terrain was built without the mask")
		return
	var params: Variant = _no_mask.material.get("_shader_parameters")
	assert_eq(params.get("capture_shadow_rect"), Vector4(0.0, 0.0, 1.0, 1.0), "the unit rectangle")


func test_the_shader_header_says_what_the_lift_does() -> void:
	var header := PackedStringArray()
	for raw in FileAccess.get_file_as_string(PHOTO_SHADER).split("\n"):
		if raw.begins_with("shader_type"):
			break
		header.append(raw.trim_prefix("//").strip_edges())
	var text := " ".join(header)
	assert_gt(text.length(), 0, "a header was read")
	for phrase: String in HEADER_PHRASES:
		assert_true(text.contains(phrase), "the header says: %s" % phrase)


func test_only_the_photo_branch_hands_the_mask() -> void:
	# A census of the loader's text. The clay shader declares no mask and Terrain3D drops a
	# parameter that is not declared (H25), so a terrain test cannot see a mask set on the clay.
	var lines := FileAccess.get_file_as_string(LOADER).split("\n")
	var calls := []
	var branch_indent := -1
	for i in lines.size():
		var line: String = lines[i]
		if line.strip_edges() == "if photo != null:":
			branch_indent = line.length() - line.lstrip("\t").length()
		if line.contains("_set_capture_shadow(") and not line.begins_with("static func"):
			calls.append(i)
	assert_eq(calls.size(), 1, "one call of _set_capture_shadow")
	assert_gt(branch_indent, -1, "the photo branch is there")
	if calls.size() == 1 and branch_indent > -1:
		var line: String = lines[calls[0]]
		var indent := line.length() - line.lstrip("\t").length()
		assert_gt(indent, branch_indent, "the call sits inside the photo branch")
		var start := lines.find("\tif photo != null:")
		assert_true(start != -1 and start < calls[0], "after the branch opens")
	var outside := 0
	for line: String in lines:
		if line.contains('"capture_shadow') and line.contains("set_shader_param"):
			outside += 1
	assert_eq(outside, 4, "the mask and its rectangle are set in _set_capture_shadow only (2 x 2)")
