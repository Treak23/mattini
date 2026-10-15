extends GutTest
## Brief M3-09: the photo shader keeps Terrain3D 1.0.2's minimum shader as the clay shader
## has it (brain.md H11): its private uniforms, varyings, vertex() and the terrain normals in
## fragment() are not touched, and only the albedo and roughness at the end differ.
##
## A census of text: it proves the two shader files hold the same Terrain3D code, never that
## either compiles or draws (the pinned loader test reads the uniforms through Godot's own
## parser; a render does the rest). It exists because the brief forbids changing that code
## and nothing else would notice a stray edit in it.

const CLAY := "res://shaders/terrain_clay.gdshader"
const PHOTO := "res://shaders/terrain_photo.gdshader"
const PRIVATE_FROM := "// Defined Constants"
const PRIVATE_TO := "// Public Uniforms"
const TERRAIN_FROM := "// Varyings & Types"
const CLAY_LOOK := "\t// Apply PBR: clay with contour lines of the real height H."
const PHOTO_LOOK := "\t// The photo by world position."


## The text of [param path] from [param from] up to (not including) [param to].
func _between(path: String, from: String, to: String) -> String:
	var text := FileAccess.get_file_as_string(path)
	assert_false(text.is_empty(), "%s is readable" % path)
	var start := text.find(from)
	var end := text.find(to, start)
	assert_true(start >= 0 and end > start, "%s holds %s … %s" % [path, from, to])
	return text.substr(start, end - start)


func test_the_private_uniforms_are_terrain3ds() -> void:
	var clay := _between(CLAY, PRIVATE_FROM, PRIVATE_TO)
	assert_eq(_between(PHOTO, PRIVATE_FROM, PRIVATE_TO), clay)
	assert_true(clay.contains("_region_map"), "the block is the one that holds the region map")


func test_the_vertex_and_terrain_normal_code_is_terrain3ds() -> void:
	var clay := _between(CLAY, TERRAIN_FROM, CLAY_LOOK)
	assert_eq(_between(PHOTO, TERRAIN_FROM, PHOTO_LOOK), clay)
	assert_true(clay.contains("void vertex()"), "the block holds vertex()")
	assert_true(clay.contains("Apply terrain normals"), "and the terrain normals")


func test_the_photo_is_sampled_in_world_space() -> void:
	var text := FileAccess.get_file_as_string(PHOTO)
	assert_true(
		text.contains("(v_vertex.xz - photo_rect.xy) / photo_rect.zw"),
		"the photo's uv is world xz relative to the rectangle"
	)
	assert_false(text.contains("textureGrad(photo"), "no region-space derivatives for the photo")
