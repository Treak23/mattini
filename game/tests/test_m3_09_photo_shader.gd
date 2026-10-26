extends GutTest
## Brief M3-09: the photo shader keeps Terrain3D 1.0.2's minimum shader as the clay shader
## has it (brain.md H11): its private uniforms, varyings, vertex() and the terrain normals in
## fragment() are not touched, and only the albedo and roughness at the end differ.
##
## A census of text: it proves the two shader files hold the same Terrain3D code, never that
## either compiles or draws (the pinned loader test reads the uniforms through Godot's own
## parser; a render does the rest). It exists because the brief forbids changing that code
## and nothing else would notice a stray edit in it.
##
## Since brief M3-R1-fix-1 (M3 review R1, P-03): the same kind of census for where the photo and
## the surface classes are placed on the ground, the last link between the data and the screen:
## the code lines that read photo_rect, surfaces_rect and puv, and the whole of class_weights,
## are pinned as text, so a flipped row, a shifted uv, a half texel removed or a second
## statement added after the pinned one (each a mutation the placement lens made with the whole
## gate green) fails here. It proves the TEXT; only a render proves that the photo and the
## classes land where the readers say, and that is design's question (docs/briefs/BLOCKED.md,
## M3 R1 P-03).

const CLAY := "res://shaders/terrain_clay.gdshader"
const PHOTO := "res://shaders/terrain_photo.gdshader"
const PRIVATE_FROM := "// Defined Constants"
const PRIVATE_TO := "// Public Uniforms"
const TERRAIN_FROM := "// Varyings & Types"
const CLAY_LOOK := "\t// Apply PBR: clay with contour lines of the real height H."
const PHOTO_LOOK := "\t// The photo look."
## Every code line (comments cut, blanks dropped) of the photo shader that names the photo's or
## the classes' rectangle, the photo's uv, or the world position the classes are read at.
const PLACEMENT_NAMES := "\\b(puv|photo_rect|surfaces_rect)\\b"
const PLACEMENT_CALLS := "class_weights\\(|texture\\(photo|vec2 xz ="
const PLACEMENT_LINES := [
	"uniform vec4 photo_rect = vec4(0.0, 0.0, 1.0, 1.0);",
	"uniform vec4 surfaces_rect = vec4(0.0, 0.0, 1.0, 1.0);",
	"vec4 class_weights(vec2 xz) {",
	"vec2 t = (xz - surfaces_rect.xy) / surfaces_rect.zw * vec2(size) - 0.5;",
	# Brief M4-06: water_weight reads the classes from the same texel centres.
	"vec2 t = (xz - surfaces_rect.xy) / surfaces_rect.zw * vec2(size) - 0.5;",
	"vec2 xz = v_vertex.xz;",
	"vec2 puv = (v_vertex.xz - photo_rect.xy) / photo_rect.zw;",
	"vec3 albedo = texture(photo, puv).rgb;",
	"if (any(lessThan(puv, vec2(0.0))) || any(greaterThan(puv, vec2(1.0)))) {",
	"vec4 classes = class_weights(xz);",
]
## class_weights, line by line: texel (c, r) at ((c + 0.5) / columns, (r + 0.5) / rows) of
## surfaces_rect, rows from the north, the four nearest texels read exactly and blended.
const CLASS_WEIGHTS_LINES := [
	"vec4 class_weights(vec2 xz) {",
	"ivec2 size = textureSize(surfaces, 0);",
	"vec2 t = (xz - surfaces_rect.xy) / surfaces_rect.zw * vec2(size) - 0.5;",
	"vec2 base = floor(t);",
	"vec2 f = t - base;",
	"ivec2 i0 = ivec2(base);",
	"vec4 w = vec4(0.0);",
	"for (int k = 0; k < 4; k++) {",
	"ivec2 o = ivec2(k % 2, k / 2);",
	"ivec2 p = i0 + o;",
	"if (p.x < 0 || p.y < 0 || p.x >= size.x || p.y >= size.y) {",
	"continue;",
	"}",
	"int c = int(texelFetch(surfaces, p, 0).r * 255.0 + 0.5);",
	"float b = (o.x == 1 ? f.x : 1.0 - f.x) * (o.y == 1 ? f.y : 1.0 - f.y);",
	"w += b * vec4(float(c == 1), float(c == 2), float(c == 3), float(c == 4));",
	"}",
	"return w;",
	"}",
]


## The text of [param path] from [param from] up to (not including) [param to].
func _between(path: String, from: String, to: String) -> String:
	var text := FileAccess.get_file_as_string(path)
	assert_false(text.is_empty(), "%s is readable" % path)
	var start := text.find(from)
	var end := text.find(to, start)
	assert_true(start >= 0 and end > start, "%s holds %s … %s" % [path, from, to])
	return text.substr(start, end - start)


## The code lines of the shader at [param path], in order: comments cut, whitespace trimmed,
## blanks dropped, only those matching the regular expression [param pattern].
func _code_lines_matching(path: String, pattern: String) -> PackedStringArray:
	var regex := RegEx.create_from_string(pattern)
	var found := PackedStringArray()
	for raw in FileAccess.get_file_as_string(path).split("\n"):
		var code := raw.get_slice("//", 0).strip_edges()
		if not code.is_empty() and regex.search(code) != null:
			found.append(code)
	return found


## The code lines of the function that starts at the line beginning with [param signature], up to
## its closing brace at the start of a line.
func _function_lines(path: String, signature: String) -> PackedStringArray:
	var found := PackedStringArray()
	var inside := false
	for raw in FileAccess.get_file_as_string(path).split("\n"):
		inside = inside or raw.begins_with(signature)
		var code := raw.get_slice("//", 0).strip_edges()
		if inside and not code.is_empty():
			found.append(code)
		if inside and raw.begins_with("}"):
			break
	return found


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


func test_the_photo_and_the_classes_are_placed_by_the_pinned_expressions() -> void:
	# A census of text (lesson 5): it proves which lines of the shader say where the photo and the
	# classes lie, never what a GPU does with them. Each mutation of the placement lens that
	# left the gate green changes one of these lines or adds one that names puv or the rectangles:
	# the photo's rows flipped (puv.y = 1.0 - puv.y), shifted by 0.1 m (puv.x -= ...), the classes
	# half a texel off (the - 0.5 removed) or read from the south (a flipped texelFetch row).
	assert_eq(
		_code_lines_matching(PHOTO, PLACEMENT_NAMES + "|" + PLACEMENT_CALLS),
		PackedStringArray(PLACEMENT_LINES),
		"the lines that name puv, photo_rect, surfaces_rect or the class position are the pinned ones"
	)
	assert_eq(
		_function_lines(PHOTO, "vec4 class_weights("),
		PackedStringArray(CLASS_WEIGHTS_LINES),
		"class_weights is the pinned function: texel centres at (c + 0.5), rows from the north"
	)


func test_exactly_one_statement_assigns_the_photo_uv() -> void:
	# The same census, by its count: a statement added after the pinned one (puv.y = 1.0 - puv.y,
	# puv.x -= 0.1 / photo_rect.z, puv = puv.yx) is an assignment to puv or to one of its parts.
	var assignments := _code_lines_matching(PHOTO, "\\bpuv\\b[.a-z]*\\s*([-+*/]?=)[^=]")
	assert_eq(assignments.size(), 1, "one assignment to puv: %s" % [assignments])
	assert_eq(assignments, PackedStringArray([PLACEMENT_LINES[6]]), "and it is the pinned one")
