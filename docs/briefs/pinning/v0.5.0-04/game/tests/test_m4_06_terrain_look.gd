extends GutTest
## Pinning tests for brief v0.5.0-04 (the lift; brief M4-06 decisions 2 and 3, re-cut onto 0.4.0's
## files): TerrainLoader hands the photo shader the capture shadows' mask, and the shader's lift
## and water are the pinned ones.
##
## M4-06's pin rebuilt (docs/briefs/pinning/M4-06/game/tests/test_m4_06_terrain_look.gd): its six
## tests of the loader and the lift, with one decision changed, and v0.4.0-03's three water tests
## (this file's live copy since 0.4.0) in place of M4-06's water test, whose water (0.3.1's two
## maps drifting apart) must not come back. ALBEDO_ASSIGNMENTS is rebuilt on the live water rule.
##
## Pinned decisions (m4-design §8; brief M4-06 decisions 2 and 3; the session's decision on the
## mask's mipmaps, 2026-10-29, briefs v0.5.0-03 and v0.5.0-04; SPEC §13 rows 41, 47 and 53):
## - TerrainLoader.create(grid, parent, photo, surfaces, shadows: CaptureShadowGrid = null): with a
##   photo and a mask, with or without a SurfaceGrid, the shader's capture_shadow is the
##   CaptureShadowGrid's own texture and capture_shadow_rect its rect(); with a photo and no
##   mask, capture_shadow is one texel of 0 (no lift; every sampler the shader declares is set)
##   and the photo, the classes and their rectangles are as before; without a photo, the clay
##   look and no mask.
## - The shader declares capture_shadow (a sampler2D: hint_default_black,
##   filter_linear_mipmap_anisotropic, repeat_disable, never source_color: the mask is data; the
##   session's decision reads the mask's mipmaps, as the photo's sampler reads the photo's, where
##   M4-06 said filter_linear), capture_shadow_rect (vec4) and shadow_lift (float, 3.0), and lifts
##   the photo's colour, as the first rule after the photo is sampled and before the neutral colour
##   outside the photo and every surface rule: m the mask filtered at the world point (0 outside
##   its rectangle), albedo × (1 + (shadow_lift - 1)·m), clipped at 1 (the prototype's clip,
##   M4-soften/README.md).
## - The water (v0.4.0-03; SPEC §13 row 53; FB-008; 0.3.1's R1-03): the water's albedo ×
##   water_albedo 0.9, roughness 0.3, strength 0.35 and its weight water_weight(xz) as v0.3.1-01
##   pinned them (the share of water among the 5 × 5 class texels around the point, the boxes of
##   the four nearest texel centres blended bilinearly, through smoothstep(0, 1, share)); the flow,
##   water_flow (SurfaceGrid's flow texture, linear, no repeat, placed by surfaces_rect, which its
##   box shares), decoded as (rg · 255 − 128) / 127 · b; both ripple maps (2 m at 0.8 m/s, 3.4 m at
##   0.5 m/s) drift downstream along it in two phases water_phase_s = 2 s apart that crossfade
##   (weights 1 − |2p − 1|), offset by water_phase(xz), a smooth field of two sines, so the phases'
##   restarts do not pulse in unison; TIME is read once, divided by water_phase_s, and 3600 s
##   (Godot's TIME rollover, the project's setting) holds a whole number of periods, so neither map
##   jumps when TIME wraps (0.3.1's map b jumped (0.80, 2.20) m once an hour). The speeds and the
##   phase field are look values.
##
## The shader's lines are a census of TEXT (lesson 5): it proves which expressions the shader
## holds and in which order, never that a GPU draws them so. The gate's render step proves what a
## render can (RENDER lift: where the lift lands and its strength under Compatibility; RENDER
## classes: where the water lies, its albedo, its bank eased over 1 m; it switches the ripples
## off, so it sees nothing of the flow). Neither proves the linear arithmetic under Forward+
## (Compatibility shows no sRGB conversion, brain.md H21): the census does, by pinning the one
## expression and that nothing converts the colour around it.
##
## Does NOT prove: that anything looks right or moves downstream on screen (no GPU here; the
## owner's PC); that the mask's mipmaps keep the lift from shimmering in the distance (a distant
## software render is the only evidence); that the crossfade does not read as a pulse; that the
## flow texture holds the right directions (test_surface_flow.gd) or reaches the shader
## (test_terrain_loader_surfaces.gd); the main scene's wiring (a later batch, M4-10).

const PHOTO_SHADER := "res://shaders/terrain_photo.gdshader"
const CLAY_SHADER := "res://shaders/terrain_clay.gdshader"
const SHADOWS_FIXTURE := "tests/shared/shadows_fixture"
const SCRATCH_DIR := "user://test_m4_06_terrain_look"
const CompleteWorld := preload("res://tests/complete_world.gd")
## Godot's TIME is the frames' time modulo this setting, in both renderers (4.6.3:
## RasterizerGLES3::begin_frame and RendererCompositorRD::begin_frame, Math::fmod; default 3600).
const ROLLOVER_SETTING := "rendering/limits/time/time_rollover_secs"

## The capture shadows' uniforms, as declared.
const MASK_UNIFORMS := [
	(
		"uniform sampler2D capture_shadow : hint_default_black, filter_linear_mipmap_anisotropic,"
		+ " repeat_disable;"
	),
	"uniform vec4 capture_shadow_rect = vec4(0.0, 0.0, 1.0, 1.0);",
	"uniform float shadow_lift = 3.0;",
]
## The fragment's code lines from the photo's sample on: the lift comes first.
const LIFT_LINES := [
	"vec3 albedo = texture(photo, puv).rgb;",
	"vec2 muv = (v_vertex.xz - capture_shadow_rect.xy) / capture_shadow_rect.zw;",
	"float m = texture(capture_shadow, muv).r;",
	"if (any(lessThan(muv, vec2(0.0))) || any(greaterThan(muv, vec2(1.0)))) {",
	"m = 0.0;",
	"}",
	"albedo = min(albedo * (1.0 + (shadow_lift - 1.0) * m), vec3(1.0));",
	"if (any(lessThan(puv, vec2(0.0))) || any(greaterThan(puv, vec2(1.0)))) {",
	"albedo = outside_albedo;",
	"}",
]
## Every statement of the shader that assigns the albedo, in order: the lift once, before the
## outside colour and the rules of rock, road, path and water (the water's: WATER_RULE_LINES).
const ALBEDO_ASSIGNMENTS := [
	"vec3 albedo = texture(photo, puv).rgb;",
	"albedo = min(albedo * (1.0 + (shadow_lift - 1.0) * m), vec3(1.0));",
	"albedo = outside_albedo;",
	"albedo *= mix(1.0, relative, w_rock);",
	"albedo *= mix(1.0, relative, w_road);",
	"albedo *= mix(1.0, relative, w_path);",
	"albedo *= mix(1.0, water_albedo, w_water);",
]
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

var _camera: Camera3D
var _grid: TerrainGrid
var _photo: PhotoGrid
var _surfaces: SurfaceGrid
var _shadows: CaptureShadowGrid
var _with_mask: Terrain3D
var _without_mask: Terrain3D
var _mask_without_classes: Terrain3D
var _clay_with_mask: Terrain3D


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


func _parse(path: String) -> Dictionary:
	var json := JSON.new()
	json.parse(FileAccess.get_file_as_string(path))
	return json.data if typeof(json.data) == TYPE_DICTIONARY else {}


## The shared shadows fixture as a manifest (brief M4-09's form), written under SCRATCH_DIR.
func _shadows_manifest() -> String:
	DirAccess.make_dir_recursive_absolute(SCRATCH_DIR.path_join("shadows"))
	var world_path := _repo_file(SHADOWS_FIXTURE.path_join("world.json"))
	var manifest := {
		"schema": 1,
		"world": _parse(world_path),
		"world_sha256": FileAccess.get_sha256(world_path),
		"shadows": _parse(_repo_file(SHADOWS_FIXTURE.path_join("generated/shadows/fixture.json"))),
	}
	var out := FileAccess.open(SCRATCH_DIR.path_join("manifest.json"), FileAccess.WRITE)
	out.store_string(JSON.stringify(manifest, "  ", true, true))
	out.close()
	var png := FileAccess.get_file_as_bytes(
		_repo_file(SHADOWS_FIXTURE.path_join("generated/shadows/fixture.png"))
	)
	var file := FileAccess.open(SCRATCH_DIR.path_join("shadows/fixture.png"), FileAccess.WRITE)
	file.store_buffer(png)
	file.close()
	return SCRATCH_DIR.path_join("manifest.json")


func before_all() -> void:
	var terrain_manifest := _repo_file("tests/shared/terrain_fixture/generated/manifest.json")
	_grid = TerrainGrid.from_manifest(terrain_manifest, WorldConfig.from_manifest(terrain_manifest))
	var photo_manifest := _repo_file("tests/shared/photo_fixture/generated/manifest.json")
	_photo = PhotoGrid.from_manifest(photo_manifest, WorldConfig.from_manifest(photo_manifest))
	var classes_manifest := _repo_file("tests/shared/surfaces_fixture/generated/manifest.json")
	_surfaces = SurfaceGrid.from_manifest(
		classes_manifest, WorldConfig.from_manifest(classes_manifest)
	)
	var shadows_manifest := _shadows_manifest()
	_shadows = CaptureShadowGrid.from_manifest(
		shadows_manifest, WorldConfig.from_manifest(shadows_manifest)
	)
	# Terrain3D looks for the viewport's camera and prints an ERROR when there is none.
	_camera = Camera3D.new()
	add_child(_camera)
	if _grid != null and _photo != null and _surfaces != null and _shadows != null:
		_with_mask = TerrainLoader.create(_grid, self, _photo, _surfaces, _shadows)
		_without_mask = TerrainLoader.create(_grid, self, _photo, _surfaces)
		_mask_without_classes = TerrainLoader.create(_grid, self, _photo, null, _shadows)
		_clay_with_mask = TerrainLoader.create(_grid, self, null, null, _shadows)


func after_all() -> void:
	for terrain in [_with_mask, _without_mask, _mask_without_classes, _clay_with_mask]:
		if terrain != null:
			terrain.free()
	_camera.free()
	CompleteWorld.remove_tree(SCRATCH_DIR)


func _params(terrain: Terrain3D) -> Dictionary:
	var params: Variant = terrain.material.get("_shader_parameters")
	return params if typeof(params) == TYPE_DICTIONARY else {}


func _shader_path(terrain: Terrain3D) -> String:
	var shader: Shader = terrain.material.shader_override
	return "" if shader == null else shader.resource_path


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


func test_the_fixtures_are_read_and_the_terrains_built() -> void:
	assert_not_null(_shadows, "the shadows fixture's CaptureShadowGrid is read")
	assert_not_null(_with_mask, "TerrainLoader.create takes the mask")
	assert_not_null(_without_mask, "and works without it")
	assert_not_null(_clay_with_mask, "and with a mask but no photo")


func test_the_shader_declares_the_mask_and_the_lift() -> void:
	var uniforms := {}
	var shader: Shader = load(PHOTO_SHADER)
	if shader != null:
		for uniform: Dictionary in shader.get_shader_uniform_list():
			uniforms[uniform["name"]] = uniform
	for name in ["capture_shadow", "capture_shadow_rect", "shadow_lift"]:
		assert_true(uniforms.has(name), "a %s uniform" % name)
	if uniforms.size() > 0 and uniforms.has("capture_shadow"):
		assert_eq(uniforms["capture_shadow"]["hint_string"], "Texture2D", "a sampler2D")
		assert_eq(uniforms["capture_shadow_rect"]["type"], TYPE_VECTOR4, "a vec4")
		assert_eq(uniforms["shadow_lift"]["type"], TYPE_FLOAT, "a float")
	assert_eq(
		_matching("^uniform .*\\b(capture_shadow|capture_shadow_rect|shadow_lift)\\b"),
		PackedStringArray(MASK_UNIFORMS),
		"the mask is data (no source_color), filtered with its mipmaps, black when unset, not repeated"
	)


func test_the_mask_and_its_rectangle_reach_the_shader() -> void:
	if _with_mask == null:
		fail_test("no terrain was built with the mask")
		return
	assert_eq(_shader_path(_with_mask), PHOTO_SHADER, "the photo look")
	var params := _params(_with_mask)
	assert_same(
		params.get("capture_shadow"), _shadows.texture, "the CaptureShadowGrid's own texture"
	)
	assert_eq(_shadows.rect(), Vector4(974.0, -38.0, 32.0, 48.0), "the fixture's rectangle")
	assert_eq(
		params.get("capture_shadow_rect"), _shadows.rect(), "capture_shadow_rect is its rect()"
	)
	assert_ne(params.get("capture_shadow_rect"), params.get("photo_rect"), "not the photo's")
	assert_ne(params.get("capture_shadow_rect"), params.get("surfaces_rect"), "not the classes'")
	assert_eq(params.get("photo"), _photo.texture, "the photo as before")
	assert_eq(params.get("surfaces"), _surfaces.texture, "the classes as before")


func test_the_mask_reaches_the_shader_without_the_classes() -> void:
	# The mask is handed whether or not a SurfaceGrid is given: a loader that sets it only with
	# the classes leaves a photo without classes unlifted (the no-mask texel, or nothing).
	if _mask_without_classes == null:
		fail_test("no terrain was built with the photo and the mask but no classes")
		return
	assert_eq(_shader_path(_mask_without_classes), PHOTO_SHADER, "the photo look")
	var params := _params(_mask_without_classes)
	assert_same(
		params.get("capture_shadow"), _shadows.texture, "the CaptureShadowGrid's own texture"
	)
	assert_eq(
		params.get("capture_shadow_rect"), _shadows.rect(), "capture_shadow_rect is its rect()"
	)
	assert_eq(params.get("photo_rect"), _photo.rect(), "the photo's rectangle as before")


func test_without_a_mask_nothing_is_lifted_and_every_sampler_is_set() -> void:
	if _without_mask == null:
		fail_test("no terrain was built without the mask")
		return
	var params := _params(_without_mask)
	var mask: Variant = params.get("capture_shadow")
	assert_true(mask is Texture2D, "the mask's sampler is set (an unset one draws a default)")
	if mask is Texture2D:
		var image: Image = mask.get_image()
		assert_eq(image.get_size(), Vector2i(1, 1), "one texel")
		assert_eq(image.get_pixel(0, 0).r8, 0, "of 0: no lift")
	assert_eq(params.get("photo_rect"), _photo.rect(), "the photo's rectangle as before")
	assert_eq(params.get("surfaces_rect"), _surfaces.rect(), "the classes' rectangle as before")
	var shader: Shader = load(PHOTO_SHADER)
	for uniform: Dictionary in shader.get_shader_uniform_list():
		var name: String = uniform["name"]
		if uniform["hint_string"] == "Texture2D" and not name.begins_with("_"):
			assert_true(params.get(name) is Texture2D, "%s has a texture" % name)


func test_without_a_photo_the_mask_is_not_used() -> void:
	if _clay_with_mask == null:
		fail_test("no terrain was built with the mask alone")
		return
	assert_eq(_shader_path(_clay_with_mask), CLAY_SHADER, "the lift needs the photo")
	assert_false(_params(_clay_with_mask).has("capture_shadow"), "no mask is set on the clay")


func test_the_lift_is_the_first_rule_on_the_photo() -> void:
	# A census of text (lesson 5). Kills: the lift after the outside colour, the water, road or
	# path rule; the mask read through another rectangle, half a texel off or with its rows
	# flipped (test_m3_09_photo_shader.gd pins the same two placement lines); no zero outside the
	# mask's rectangle (repeat_disable clamps to the edge texel); the lift unclipped or on sRGB
	# values (any conversion is one more assignment to albedo).
	assert_eq(
		_run_from(LIFT_LINES[0], LIFT_LINES.size()),
		PackedStringArray(LIFT_LINES),
		"the lift, from the photo's sample to the neutral colour outside it"
	)
	# Linear light: the photo is a source_color sampler, so under Forward+ the colour the lift
	# multiplies is linear (brain.md H21); without the hint it would be the JPEG's sRGB values.
	assert_eq(
		_matching("^uniform sampler2D photo\\b"),
		PackedStringArray(
			[
				(
					"uniform sampler2D photo : source_color, filter_linear_mipmap_anisotropic,"
					+ " repeat_disable;"
				)
			]
		),
		"the photo is sampled as colour, linearised"
	)
	assert_eq(
		_matching("\\balbedo\\b\\s*([-+*/]?=)[^=]"),
		PackedStringArray(ALBEDO_ASSIGNMENTS),
		"every assignment to the albedo, in order: the lift once, first"
	)
	assert_eq(
		_matching("\\b(muv|capture_shadow|capture_shadow_rect|shadow_lift)\\b|^m = |^float m "),
		PackedStringArray(
			(
				["group_uniforms capture_shadow;"]
				+ MASK_UNIFORMS
				+ LIFT_LINES.slice(1, 5)
				+ [LIFT_LINES[6]]
			)
		),
		"no other line reads the mask or its rectangle"
	)


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
