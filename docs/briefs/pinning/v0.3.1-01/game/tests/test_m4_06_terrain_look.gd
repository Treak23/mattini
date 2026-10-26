extends GutTest
## Pinning test for brief v0.3.1-01 (the river): the photo shader's water is the pinned one.
##
## A cut of brief M4-06's pin of this file (docs/briefs/pinning/M4-06/game/tests/
## test_m4_06_terrain_look.gd) to its water, at the same path. M4-06's other tests are the lift's:
## they use the capture shadows' reader (CaptureShadowGrid) and TerrainLoader's fifth argument,
## neither of which exists yet (a script that uses them does not parse, and GUT skips a script that
## does not parse, brain.md H3), and they pin the shader's lift, which comes in a later release.
## The batch that brings the lift replaces this file with M4-06's whole pin, whose water test is
## this one, unchanged.
##
## Pinned decisions (m4-design §8; brief M4-06 Decision 4): the water's albedo × water_albedo 0.9,
## roughness 0.3, normal maps at 2 m and 3.4 m drifting at 0.8 m/s in opposite directions (a along
## water_drift (0.48, 0.64), b against it), strength 0.35, its weight water_weight(xz): the share
## of water among the 5 × 5 class texels around the point, the boxes of the four nearest texel
## centres blended bilinearly, through smoothstep(0, 1, share).
##
## The shader's lines are a census of TEXT (lesson 5): it proves which expressions the shader
## holds and in which order, never that a GPU draws them so. The gate's render step proves what a
## render can (RENDER classes: where the water lies, its albedo, its bank eased over 1 m).
##
## Does NOT prove: that anything looks right (the brief's software screenshots and the owner's
## PC); the water's roughness, ripples and drift on screen (the render step switches them off).

const PHOTO_SHADER := "res://shaders/terrain_photo.gdshader"

## The water's uniforms and roughness.
const WATER_DECLARATIONS := [
	"uniform sampler2D water_normal_a : hint_normal, filter_linear_mipmap, repeat_enable;",
	"uniform sampler2D water_normal_b : hint_normal, filter_linear_mipmap, repeat_enable;",
	"uniform float water_scale_a_m = 2.0;",
	"uniform float water_scale_b_m = 3.4;",
	"uniform vec2 water_drift = vec2(0.48, 0.64);",
	"uniform float water_normal_strength = 0.35;",
	"uniform float water_albedo = 0.9;",
	"const float WATER_ROUGHNESS = 0.3;",
]
## The water's weight, line by line.
const WATER_WEIGHT_LINES := [
	"float water_weight(vec2 xz) {",
	"ivec2 size = textureSize(surfaces, 0);",
	"vec2 t = (xz - surfaces_rect.xy) / surfaces_rect.zw * vec2(size) - 0.5;",
	"vec2 base = floor(t);",
	"vec2 f = t - base;",
	"ivec2 i0 = ivec2(base);",
	"float share = 0.0;",
	"for (int j = -2; j <= 3; j++) {",
	"float wy = j == -2 ? 1.0 - f.y : (j == 3 ? f.y : 1.0);",
	"for (int i = -2; i <= 3; i++) {",
	"ivec2 p = i0 + ivec2(i, j);",
	"if (p.x < 0 || p.y < 0 || p.x >= size.x || p.y >= size.y) {",
	"continue;",
	"}",
	"float wx = i == -2 ? 1.0 - f.x : (i == 3 ? f.x : 1.0);",
	"int c = int(texelFetch(surfaces, p, 0).r * 255.0 + 0.5);",
	"share += wx * wy * float(c == 2);",
	"}",
	"}",
	"return smoothstep(0.0, 1.0, share / 25.0);",
	"}",
]
## The water rule in fragment(), from its weight to its end.
const WATER_RULE_LINES := [
	"float w_water = water_weight(xz);",
	"if (w_water > 0.0) {",
	"vec2 ua = (xz - TIME * water_drift) / water_scale_a_m;",
	"vec2 ub = (xz + TIME * water_drift) / water_scale_b_m;",
	(
		"vec3 na = unpack_normal(textureGrad(water_normal_a, ua, ddx_xz / water_scale_a_m,"
		+ " ddy_xz / water_scale_a_m));"
	),
	(
		"vec3 nb = unpack_normal(textureGrad(water_normal_b, ub, ddx_xz / water_scale_b_m,"
		+ " ddy_xz / water_scale_b_m));"
	),
	"vec2 ripple = (na.xy + nb.xy) * water_normal_strength;",
	"bump = mix(bump, vec3(ripple.x, 0.0, ripple.y), w_water);",
	"albedo *= mix(1.0, water_albedo, w_water);",
	"roughness = mix(roughness, WATER_ROUGHNESS, w_water);",
	"}",
]


## The code lines of the photo shader: comments cut, whitespace trimmed, blanks dropped.
func _code_lines() -> PackedStringArray:
	var found := PackedStringArray()
	for raw in FileAccess.get_file_as_string(PHOTO_SHADER).split("\n"):
		var code := raw.get_slice("//", 0).strip_edges()
		if not code.is_empty():
			found.append(code)
	return found


## The code lines matching the regular expression [param pattern], in order.
func _matching(pattern: String) -> PackedStringArray:
	var regex := RegEx.create_from_string(pattern)
	var found := PackedStringArray()
	for code in _code_lines():
		if regex.search(code) != null:
			found.append(code)
	return found


## [param count] code lines from the first that equals [param first].
func _run_from(first: String, count: int) -> PackedStringArray:
	var lines := _code_lines()
	var at := lines.find(first)
	assert_true(at >= 0, "the shader holds %s" % first)
	return lines.slice(at, at + count) if at >= 0 else PackedStringArray()


func test_the_water_is_the_pinned_one() -> void:
	# A census of text (lesson 5). Kills: M3's constants (albedo 0.6, roughness 0.05, one 10 m
	# scale, strength 0.2), a single drift direction, other scales, the class weight without the
	# 1 m ease, a box of another size, the ease without the smoothstep.
	assert_eq(
		_matching("^(uniform .*\\bwater_|const float WATER_)"),
		PackedStringArray(WATER_DECLARATIONS),
		"the water's uniforms and roughness"
	)
	var lines := _code_lines()
	var at := lines.find(WATER_WEIGHT_LINES[0])
	assert_true(at >= 0, "the shader defines water_weight")
	if at >= 0:
		assert_eq(
			lines.slice(at, at + WATER_WEIGHT_LINES.size()), PackedStringArray(WATER_WEIGHT_LINES)
		)
	assert_eq(
		_run_from(WATER_RULE_LINES[0], WATER_RULE_LINES.size()), PackedStringArray(WATER_RULE_LINES)
	)
	assert_eq(
		_matching("\\bw_water\\b\\s*="), PackedStringArray([WATER_RULE_LINES[0]]), "one weight"
	)
	assert_eq(
		_matching("water_weight\\("),
		PackedStringArray([WATER_WEIGHT_LINES[0], WATER_RULE_LINES[0]])
	)
