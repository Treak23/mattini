extends GutTest
## Pinning test for brief v0.4.0-03 (the water flows downstream): the photo shader's water is the
## pinned one, and nothing in it jumps when Godot's TIME wraps.
##
## At the path of brief M4-06's pin (docs/briefs/pinning/M4-06/game/tests/
## test_m4_06_terrain_look.gd), as v0.3.1-01's cut of it was: M4-06's other tests are the lift's,
## which comes in a later release. That release rebuilds M4-06's pin from this file's water tests;
## M4-06's own copy still holds 0.3.1's water (the two maps drifting apart) and must not come back.
##
## Pinned decisions (the release session of 0.4.0; SPEC §13 row 53; FB-008; 0.3.1's R1-03): the
## water's albedo × water_albedo 0.9, roughness 0.3, strength 0.35 and its weight water_weight(xz)
## as v0.3.1-01 pinned them (the share of water among the 5 × 5 class texels around the point,
## the boxes of the four nearest texel centres blended bilinearly, through smoothstep(0, 1,
## share)). New: the flow, water_flow (SurfaceGrid's flow texture, linear, no repeat, placed by
## surfaces_rect, which its box shares), decoded as (rg · 255 − 128) / 127 · b; both ripple maps
## (2 m at 0.8 m/s, 3.4 m at 0.5 m/s) drift downstream along it in two phases water_phase_s = 2 s
## apart that crossfade (weights 1 − |2p − 1|), offset by water_phase(xz), a smooth field of two
## sines, so the phases' restarts do not pulse in unison; TIME is read once, divided by
## water_phase_s, and 3600 s (Godot's TIME rollover, the project's setting) holds a whole number
## of periods, so neither map jumps when TIME wraps (0.3.1's map b jumped (0.80, 2.20) m once an
## hour). The speeds and the phase field are look values.
##
## The shader's lines are a census of TEXT (lesson 5): it proves which expressions the shader
## holds and in which order, never that a GPU draws them so. The gate's render step proves what a
## render can (RENDER classes: where the water lies, its albedo, its bank eased over 1 m; it
## switches the ripples off, so it sees nothing of the flow).
##
## Does NOT prove: that anything looks right or moves downstream on screen (no GPU here; the
## owner's PC); that the crossfade does not read as a pulse; that the flow texture holds the right
## directions (test_surface_flow.gd) or reaches the shader (test_terrain_loader_surfaces.gd).

const PHOTO_SHADER := "res://shaders/terrain_photo.gdshader"
## Godot's TIME is the frames' time modulo this setting, in both renderers (4.6.3:
## RasterizerGLES3::begin_frame and RendererCompositorRD::begin_frame, Math::fmod; default 3600).
const ROLLOVER_SETTING := "rendering/limits/time/time_rollover_secs"

## The water's uniforms and roughness.
const WATER_DECLARATIONS := [
	"uniform sampler2D water_normal_a : hint_normal, filter_linear_mipmap, repeat_enable;",
	"uniform sampler2D water_normal_b : hint_normal, filter_linear_mipmap, repeat_enable;",
	"uniform sampler2D water_flow : hint_default_black, filter_linear, repeat_disable;",
	"uniform float water_scale_a_m = 2.0;",
	"uniform float water_scale_b_m = 3.4;",
	"uniform float water_phase_s = 2.0;",
	"uniform float water_speed_a = 0.8;",
	"uniform float water_speed_b = 0.5;",
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
## The phase field, in periods: two sines (wavelengths about 23 m and 37 m), within ±0.5, no fract.
const WATER_PHASE_LINES := [
	"float water_phase(vec2 xz) {",
	"return 0.25 * sin(dot(xz, vec2(0.21, 0.17))) + 0.25 * sin(dot(xz, vec2(-0.11, 0.13)));",
	"}",
]
## The water rule in fragment(), from its weight to its end.
const WATER_RULE_LINES := [
	"float w_water = water_weight(xz);",
	"if (w_water > 0.0) {",
	"vec4 t = texture(water_flow, (xz - surfaces_rect.xy) / surfaces_rect.zw);",
	"vec2 flow = (t.rg * 255.0 - 128.0) / 127.0 * t.b;",
	"float p0 = fract(TIME / water_phase_s + water_phase(xz));",
	"float p1 = fract(p0 + 0.5);",
	"vec2 da = flow * water_speed_a * water_phase_s;",
	"vec2 db = flow * water_speed_b * water_phase_s;",
	"vec2 ua0 = (xz - p0 * da) / water_scale_a_m;",
	"vec2 ua1 = (xz - p1 * da) / water_scale_a_m;",
	"vec2 ub0 = (xz - p0 * db) / water_scale_b_m;",
	"vec2 ub1 = (xz - p1 * db) / water_scale_b_m;",
	"vec2 dxa = ddx_xz / water_scale_a_m;",
	"vec2 dya = ddy_xz / water_scale_a_m;",
	"vec2 dxb = ddx_xz / water_scale_b_m;",
	"vec2 dyb = ddy_xz / water_scale_b_m;",
	"vec3 na0 = unpack_normal(textureGrad(water_normal_a, ua0, dxa, dya));",
	"vec3 na1 = unpack_normal(textureGrad(water_normal_a, ua1, dxa, dya));",
	"vec3 nb0 = unpack_normal(textureGrad(water_normal_b, ub0, dxb, dyb));",
	"vec3 nb1 = unpack_normal(textureGrad(water_normal_b, ub1, dxb, dyb));",
	"float w0 = 1.0 - abs(2.0 * p0 - 1.0);",
	"float w1 = 1.0 - abs(2.0 * p1 - 1.0);",
	"vec2 ripple = (w0 * (na0.xy + nb0.xy) + w1 * (na1.xy + nb1.xy)) * water_normal_strength;",
	"bump = mix(bump, vec3(ripple.x, 0.0, ripple.y), w_water);",
	"albedo *= mix(1.0, water_albedo, w_water);",
	"roughness = mix(roughness, WATER_ROUGHNESS, w_water);",
	"}",
]
## What the water did in 0.3.1, which no comment may still say (Hard Rule 2).
const OLD_WORDS := ["drifting apart", "drifts against", "no net direction", "water_drift"]


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
	# A census of text (lesson 5). Kills: 0.3.1's two maps drifting apart along one vector, the
	# drift upstream, the flow's r and g exchanged, the flow placed by the photo's rectangle or not
	# read, one phase without the crossfade, other speeds, scales or period, the phase field
	# removed or cut by fract, and v0.3.1-01's kills (albedo, roughness, the 1 m ease).
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
			lines.slice(at, at + WATER_WEIGHT_LINES.size()),
			PackedStringArray(WATER_WEIGHT_LINES),
			"water_weight, line by line"
		)
	assert_eq(
		_run_from(WATER_PHASE_LINES[0], WATER_PHASE_LINES.size()),
		PackedStringArray(WATER_PHASE_LINES),
		"the phase field"
	)
	assert_eq(
		_run_from(WATER_RULE_LINES[0], WATER_RULE_LINES.size()),
		PackedStringArray(WATER_RULE_LINES),
		"the water rule: the flow, two phases crossfaded, both maps drifting downstream"
	)
	assert_eq(
		_matching("\\bw_water\\b\\s*="), PackedStringArray([WATER_RULE_LINES[0]]), "one weight"
	)
	assert_eq(
		_matching("water_weight\\("),
		PackedStringArray([WATER_WEIGHT_LINES[0], WATER_RULE_LINES[0]]),
		"water_weight defined once and read once"
	)
	assert_eq(
		_matching("water_phase\\("),
		PackedStringArray([WATER_PHASE_LINES[0], WATER_RULE_LINES[4]]),
		"the phase field defined once and read once"
	)
	assert_eq(
		_matching("\\bwater_flow\\b"),
		PackedStringArray([WATER_DECLARATIONS[2], WATER_RULE_LINES[2]]),
		"the flow declared once and sampled once"
	)


func test_a_whole_number_of_periods_fits_in_the_time_rollover() -> void:
	# R1-03 (0.3.1's review): TIME wraps at the rollover, and a drift that is not a whole number
	# of tiles per rollover jumps there. Here every use of TIME is fract(TIME / water_phase_s …),
	# so it is continuous across the wrap exactly when the rollover is a whole number of periods.
	# The period is read from its declaration's text: a uniform's default cannot be read headless
	# (brain.md H25).
	assert_eq(
		_matching("\\bTIME\\b"),
		PackedStringArray([WATER_RULE_LINES[4]]),
		"TIME is read once, divided by water_phase_s inside fract"
	)
	var declared := _matching("^uniform float water_phase_s\\s*=")
	assert_eq(declared.size(), 1, "water_phase_s is declared once: %s" % [declared])
	if declared.size() != 1:
		return
	var value := declared[0].get_slice("=", 1).trim_suffix(";").strip_edges()
	assert_true(value.is_valid_float(), "water_phase_s's default is a number: %s" % value)
	var period := value.to_float()
	var rollover: float = ProjectSettings.get_setting(ROLLOVER_SETTING)
	assert_eq(rollover, 3600.0, "the project keeps Godot's TIME rollover (3600 s)")
	assert_gt(period, 0.0, "the period is positive")
	if period <= 0.0:
		return
	var periods := rollover / period
	assert_almost_eq(
		periods,
		roundf(periods),
		1e-6,
		"%s s / water_phase_s %s s is a whole number of periods" % [rollover, value]
	)


func test_the_comments_say_what_the_water_does_now() -> void:
	# Hard Rule 2: a comment never claims what the code does not do. The water comments say that
	# the ripples drift downstream along swissTLM3D's lines; nothing says what 0.3.1's did.
	var text := FileAccess.get_file_as_string(PHOTO_SHADER)
	for words: String in OLD_WORDS:
		assert_false(text.contains(words), "the shader no longer says '%s'" % words)
	var start := text.find("group_uniforms water;")
	var end := text.find("group_uniforms;", start)
	assert_true(start >= 0 and end > start, "the shader holds the water's uniform group")
	var comments := PackedStringArray()
	for raw in text.substr(start, end - start).split("\n"):
		if raw.strip_edges().begins_with("//"):
			comments.append(raw)
	var said := "\n".join(comments)
	assert_string_contains(said, "downstream")
	assert_string_contains(said, "swissTLM3D")
	assert_string_contains(said, "look value")
