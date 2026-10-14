extends GutTest
## Pinning tests for brief M3-09: TerrainLoader gives the terrain the photo look when it is
## given a PhotoGrid, and keeps M2's clay look without one.
##
## Pinned decisions (m3-design.md §7 and §9; docs/SPEC.md §10): TerrainLoader.create(grid,
## parent, photo: PhotoGrid = null, surfaces: SurfaceGrid = null). With a photo the override
## shader is res://shaders/terrain_photo.gdshader, which declares the uniforms photo (a
## Texture2D sampler) and photo_rect (a vec4: local x0, z0 of the photo's north-west corner,
## width_m, depth_m), and the loader sets them to the PhotoGrid's own texture and rect(). The
## rectangle comes from WorldConfig through the reader, never from the terrain grid: the
## shared photo fixture (tests/shared/photo_fixture/, a world of its own) lies at (412.5,
## -215.0, 16.0, 8.0) (tests/shared/photo_vectors.json, computed by design from LV95), where a
## rectangle taken from the terrain grid (1015.0, 10.5, 20.0, 11.5), a z0 of the wrong sign,
## texels instead of metres (80 × 40) or width and depth swapped all land elsewhere. Without
## a photo the clay shader stays: M2's look is the fallback.
##
## Read back from Terrain3DMaterial's stored parameters ("_shader_parameters"), because
## headless get_shader_param() returns null (the dummy renderer keeps no material state); the
## store keeps only the uniforms the active shader declares, so a value read back there also
## proves that the shader declares it and that the loader set it after setting the shader
## (measured with Terrain3D 1.0.2, 2026-10-14: a parameter set before the override shader is
## dropped). The terrains are built in before_all, where Terrain3D's one deprecation warning
## (brain.md H4) fails no test.
##
## Does NOT prove: that anything renders or looks right (no GPU); what the shader does with
## the photo (the brief's screenshots and review do).

const PHOTO_SHADER := "res://shaders/terrain_photo.gdshader"
const CLAY_SHADER := "res://shaders/terrain_clay.gdshader"

var _camera: Camera3D
var _grid: TerrainGrid
var _photo: PhotoGrid
var _with_photo: Terrain3D
var _without_photo: Terrain3D


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


## The photo fixture's rectangle as design computed it from LV95 (photo_vectors.json grid.rect).
func _expected_rect() -> Vector4:
	var text := FileAccess.get_file_as_string(_repo_file("tests/shared/photo_vectors.json"))
	var json := JSON.new()
	assert_eq(json.parse(text), OK, "the shared photo vectors parse")
	var rect: Array = json.data["grid"]["rect"]
	return Vector4(rect[0], rect[1], rect[2], rect[3])


func before_all() -> void:
	var terrain_manifest := _repo_file("tests/shared/terrain_fixture/generated/manifest.json")
	_grid = TerrainGrid.from_manifest(terrain_manifest, WorldConfig.from_manifest(terrain_manifest))
	var photo_manifest := _repo_file("tests/shared/photo_fixture/generated/manifest.json")
	_photo = PhotoGrid.from_manifest(photo_manifest, WorldConfig.from_manifest(photo_manifest))
	# Terrain3D looks for the viewport's camera and prints an ERROR when there is none.
	_camera = Camera3D.new()
	add_child(_camera)
	if _grid != null and _photo != null:
		_with_photo = TerrainLoader.create(_grid, self, _photo)
	if _grid != null:
		_without_photo = TerrainLoader.create(_grid, self)


func after_all() -> void:
	for terrain in [_with_photo, _without_photo]:
		if terrain != null:
			terrain.free()
	_camera.free()


func _shader_path(terrain: Terrain3D) -> String:
	var shader: Shader = terrain.material.shader_override
	return "" if shader == null else shader.resource_path


func _params(terrain: Terrain3D) -> Dictionary:
	var params: Variant = terrain.material.get("_shader_parameters")
	return params if typeof(params) == TYPE_DICTIONARY else {}


func test_the_fixtures_are_read() -> void:
	assert_not_null(_grid, "the terrain fixture's grid is read")
	assert_not_null(_photo, "the photo fixture's PhotoGrid is read")
	assert_not_null(_with_photo, "TerrainLoader.create returns the terrain with a photo")
	assert_not_null(_without_photo, "and without one")


func test_with_a_photo_the_terrain_uses_the_photo_shader() -> void:
	if _with_photo == null:
		fail_test("no terrain was built with the photo")
		return
	var material := _with_photo.material
	assert_true(material.shader_override_enabled, "the override shader is on")
	assert_eq(_shader_path(_with_photo), PHOTO_SHADER)
	assert_false(material.show_checkered, "the checkerboard debug view is off")
	assert_eq(material.world_background, Terrain3DMaterial.NONE, "no invented ground")


func test_the_photo_shader_declares_the_photo_and_its_rectangle() -> void:
	var shader: Shader = load(PHOTO_SHADER)
	assert_not_null(shader, "the photo shader loads")
	if shader == null:
		return
	var uniforms := {}
	for uniform: Dictionary in shader.get_shader_uniform_list():
		uniforms[uniform["name"]] = uniform
	assert_true(uniforms.has("photo"), "a photo uniform")
	assert_true(uniforms.has("photo_rect"), "a photo_rect uniform")
	if uniforms.has("photo"):
		assert_eq(uniforms["photo"]["type"], TYPE_OBJECT, "photo is a sampler")
		assert_eq(uniforms["photo"]["hint_string"], "Texture2D", "a sampler2D")
	if uniforms.has("photo_rect"):
		assert_eq(uniforms["photo_rect"]["type"], TYPE_VECTOR4, "photo_rect is a vec4")


func test_the_photo_and_its_rectangle_reach_the_shader() -> void:
	if _with_photo == null:
		fail_test("no terrain was built with the photo")
		return
	var params := _params(_with_photo)
	assert_true(params.has("photo"), "the photo is set, after the shader")
	assert_same(params.get("photo"), _photo.texture, "the PhotoGrid's own texture")
	assert_not_null(_photo.texture, "which exists")
	var expected := _expected_rect()
	assert_eq(_photo.rect(), expected, "PhotoGrid places the photo where design computed it")
	assert_eq(params.get("photo_rect"), expected, "photo_rect is the PhotoGrid's rectangle")
	var grid_extent := Vector4(
		_grid.x_min,
		_grid.z_min,
		(_grid.columns - 1) * _grid.spacing_m,
		(_grid.rows - 1) * _grid.spacing_m
	)
	assert_ne(params.get("photo_rect"), grid_extent, "not the terrain grid's extent")


func test_without_a_photo_the_clay_look_stays() -> void:
	if _without_photo == null:
		fail_test("no terrain was built without a photo")
		return
	assert_true(_without_photo.material.shader_override_enabled, "the override shader is on")
	assert_eq(_shader_path(_without_photo), CLAY_SHADER, "M2's clay look is the fallback")
	var params := _params(_without_photo)
	assert_false(params.has("photo") and params["photo"] != null, "no photo is set")
