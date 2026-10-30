// Copyright © 2023-2026 Cory Petkovsek, Roope Palmroos, and Contributors.
// This shader is the minimum needed to allow the terrain to function, without any texturing.
//
// mattini's photo look (briefs M3-09, M3-10 and v0.3.1-01; docs/SPEC.md §10): Terrain3D 1.0.2's
// extras/shaders/minimum.gdshader (MIT, res://addons/terrain_3d/LICENSE.txt) as in
// terrain_clay.gdshader, its vertex() and the terrain normals in fragment() unchanged, without
// the contour lines. The albedo is the aerial photo (SWISSIMAGE 2023): photo_rect holds the
// local x and z of its north-west corner, its width and its depth in metres, and the photo is
// sampled by world position; outside it the neutral colour of the clay look. Where the photo lay
// in shadow when it was flown the photo is lifted (brief v0.5.0-04; SPEC §13 rows 41 and 47): the
// first rule on the photo multiplies its linear colour by 1 + (shadow_lift - 1) * m, m the
// capture-shadow mask (CaptureShadowGrid) filtered at the world point, 0 outside the mask's
// rectangle and wherever no mask is given, clipped at 1 per channel, so the baked shadows do not
// darken the ground a second time under the game's own sun; the neutral colour outside the photo
// is never lifted. On it the surface
// classes (swissTLM3D: one byte per texel, placed by surfaces_rect, read with texelFetch and
// never filtered) add: on rock, a triplanar CC0 rock texture weighted by smoothstep(35°, 55°,
// slope), its luminance relative to its mean tinting the photo's colour; on roads and paths,
// CC0 detail textures whose luminance relative to their mean multiplies the photo, fading out
// by near_fade_m from the camera; on water, the photo's colour × 0.9 and roughness 0.3, with
// ripples from two noise normal maps (NoiseTexture2D, made by TerrainLoader) tiling every 2 m
// and 3.4 m that drift downstream along swissTLM3D's watercourse lines at 0.8 and 0.5 m/s
// (brief v0.4.0-03: the flow texture water_flow, two phases crossfaded), the water's weight
// eased over 1 m at the bank (water_weight).

shader_type spatial;
render_mode blend_mix,depth_draw_opaque,cull_back,diffuse_burley,specular_schlick_ggx,skip_vertex_transform;

// Defined Constants
#define SKIP_PASS 0
#define VERTEX_PASS 1
#define FRAGMENT_PASS 2

#if CURRENT_RENDERER == RENDERER_COMPATIBILITY
    #define fma(a, b, c) ((a) * (b) + (c))
    #define dFdxCoarse(a) dFdx(a)
    #define dFdyCoarse(a) dFdy(a)
#endif

// Private uniforms
// Commented uniforms aren't needed for this shader, but are available for your own needs.
uniform vec3 _camera_pos = vec3(0.f);
uniform float _mesh_size = 48.f;
uniform uint _background_mode = 1u; // NONE = 0, FLAT = 1, NOISE = 2
uniform uint _mouse_layer = 0x80000000u; // Layer 32
uniform float _vertex_spacing = 1.0;
uniform float _vertex_density = 1.0; // = 1/_vertex_spacing
uniform float _region_size = 1024.0;
uniform float _region_texel_size = 0.0009765625; // = 1/1024
uniform int _region_map_size = 32;
uniform int _region_map[1024];
//uniform vec2 _region_locations[1024];
//uniform float _texture_uv_scale_array[32];
//uniform float _texture_detile_array[32];
//uniform vec4 _texture_color_array[32];
uniform highp sampler2DArray _height_maps : repeat_disable;
uniform highp sampler2DArray _control_maps : repeat_disable;
//uniform highp sampler2DArray _color_maps : source_color, filter_linear_mipmap_anisotropic, repeat_disable;
//uniform highp sampler2DArray _texture_array_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
//uniform highp sampler2DArray _texture_array_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;

// Public Uniforms
uniform bool flat_terrain_normals = false;
// The world's height offset: real height H = local y + height_offset_m (TerrainLoader sets it
// on every terrain shader; this one does not use it).
uniform float height_offset_m = 0.0;

group_uniforms photo;
// The aerial photo, and where it lies: local x0, z0 (its north-west corner), width, depth (m).
uniform sampler2D photo : source_color, filter_linear_mipmap_anisotropic, repeat_disable;
uniform vec4 photo_rect = vec4(0.0, 0.0, 1.0, 1.0);
// Outside the photo: the clay's neutral colour, never an invented ground.
uniform vec3 outside_albedo : source_color = vec3(0.52, 0.50, 0.47);

group_uniforms capture_shadow;
// The capture-shadow mask (CaptureShadowGrid): where the photo lay in shadow when it was flown,
// one byte per texel (255 in shadow, 0 not), 0.5 m texels with a full mip chain, placed like the
// photo: local x0, z0 (the north-west corner), width, depth (m), rows from the north. It is data,
// not a colour: no source_color. Filtered linearly with its mipmaps, as the photo: close up that
// is the bilinear feather between the texel centres that the mask's inset keeps inside the
// shadow; in the distance a mip level's mean m lifts a pixel by the mean of its texels' lifts
// (the lift is linear in m, before the clip), so the binary mask does not alias. Unset reads
// black (hint_default_black): no lift (an unset sampler without the hint reads white). repeat_disable
// clamps to the edge texel, hence the explicit 0 outside the rectangle in fragment().
uniform sampler2D capture_shadow : hint_default_black, filter_linear_mipmap_anisotropic, repeat_disable;
uniform vec4 capture_shadow_rect = vec4(0.0, 0.0, 1.0, 1.0);
// The lift's factor in full shadow (the owner's G = 3, SPEC §13 row 47).
uniform float shadow_lift = 3.0;

group_uniforms surfaces;
// The surface classes, one byte per texel (0 none, 1 rock, 2 water, 3 path, 4 road), placed
// like the photo: local x0, z0 (the north-west corner), width, depth (m). Read only with
// texelFetch: a filtered class would invent a class between two. No sRGB hint: a class is a
// number. Unset (no SurfaceGrid): black, class 0 everywhere.
uniform sampler2D surfaces : hint_default_black, filter_nearest, repeat_disable;
uniform vec4 surfaces_rect = vec4(0.0, 0.0, 1.0, 1.0);
// The road and path detail fades out by this distance from the camera (m).
uniform float near_fade_m = 150.0;

group_uniforms rock;
// Poly Haven rock_face_03 (CC0), 2.7 m on the ground.
uniform sampler2D rock_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D rock_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D rock_roughness : hint_roughness_r, filter_linear_mipmap_anisotropic, repeat_enable;
uniform float rock_scale_m = 2.7;

group_uniforms road_and_path;
// Poly Haven worn_asphalt and rocky_trail (CC0), 2 m on the ground each.
uniform sampler2D road_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D road_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform float road_scale_m = 2.0;
uniform sampler2D path_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D path_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform float path_scale_m = 2.0;
uniform float detail_normal_strength = 1.0;

group_uniforms water;
// The water's ripples drift downstream along swissTLM3D's watercourse lines (briefs v0.4.0-01 to
// v0.4.0-03; SPEC §13 row 53). Two NoiseTexture2D normal maps (TerrainLoader makes them; no
// file): map a tiles every water_scale_a_m and drifts at water_speed_a, map b tiles every
// water_scale_b_m and drifts at water_speed_b, both along the flow. water_flow is SurfaceGrid's
// flow texture, one RGB8 texel per 2 m cell of the classes' own box (placed by surfaces_rect):
// the downstream direction in local (x, z) of the nearest drawn stream, decoded as
// (rg · 255 − 128) / 127 · b, filtered linearly; b is 0 where no stream is near, and the sampler
// unset reads black (hint_default_black), no drift too. The flow varies by place, so each map is
// read in two phases half a period apart, each moved downstream for one period water_phase_s and
// then restarted where its weight is 0, the two crossfaded (the flowmap technique); 3600 s, Godot's
// TIME rollover, is a whole number of periods, so nothing jumps when TIME wraps.
uniform sampler2D water_normal_a : hint_normal, filter_linear_mipmap, repeat_enable;
uniform sampler2D water_normal_b : hint_normal, filter_linear_mipmap, repeat_enable;
uniform sampler2D water_flow : hint_default_black, filter_linear, repeat_disable;
uniform float water_scale_a_m = 2.0;
uniform float water_scale_b_m = 3.4;
// The crossfade's period (s), a look value; 3600 / water_phase_s must stay whole (a pinned test).
uniform float water_phase_s = 2.0;
// The drift speeds along the flow (m/s): look values, not measured (swissTLM3D gives no speed).
uniform float water_speed_a = 0.8;
uniform float water_speed_b = 0.5;
uniform float water_normal_strength = 0.35;
// On water the photo's colour is multiplied by this: the photo's own river, a little darker.
uniform float water_albedo = 0.9;
group_uniforms;

const float PHOTO_ROUGHNESS = 0.95;
const float WATER_ROUGHNESS = 0.3;

// Luminance of a linear colour (Rec. 709).
float luminance(vec3 c) {
	return dot(c, vec3(0.2126, 0.7152, 0.0722));
}

// The mean luminance of a texture: its smallest mip level (box-filtered by the importer).
float mean_luminance(sampler2D tex) {
	return max(luminance(textureLod(tex, vec2(0.5), 16.0).rgb), 1e-4);
}

// A tangent-space normal from a normal map, as (along +u, along +v, out). OpenGL convention:
// green points up the picture, which is -v in Godot's texture space. z is rebuilt from x and
// y: a two-channel compressed normal map has no blue.
vec3 unpack_normal(vec4 s) {
	vec2 xy = s.xy * 2.0 - 1.0;
	return vec3(xy.x, -xy.y, sqrt(max(0.0, 1.0 - dot(xy, xy))));
}

// The surface classes around (x, z): the weights of rock, water, path and road. Each of the
// four nearest class texels is read exactly (texelFetch) and the four are blended bilinearly
// per class, so a class edge is soft over one texel instead of stair-stepped. Texel (c, r) is
// centred at uv ((c + 0.5) / columns, (r + 0.5) / rows) of surfaces_rect, rows from the north
// (+z). Outside the grid: class 0.
vec4 class_weights(vec2 xz) {
	ivec2 size = textureSize(surfaces, 0);
	vec2 t = (xz - surfaces_rect.xy) / surfaces_rect.zw * vec2(size) - 0.5;
	vec2 base = floor(t);
	vec2 f = t - base;
	ivec2 i0 = ivec2(base);
	vec4 w = vec4(0.0);
	for (int k = 0; k < 4; k++) {
		ivec2 o = ivec2(k % 2, k / 2);
		ivec2 p = i0 + o;
		if (p.x < 0 || p.y < 0 || p.x >= size.x || p.y >= size.y) {
			continue;
		}
		int c = int(texelFetch(surfaces, p, 0).r * 255.0 + 0.5);
		float b = (o.x == 1 ? f.x : 1.0 - f.x) * (o.y == 1 ? f.y : 1.0 - f.y);
		w += b * vec4(float(c == 1), float(c == 2), float(c == 3), float(c == 4));
	}
	return w;
}

// The water's weight at (x, z), its bank eased over 1 m (m4-design §8): the share of water among
// the 5 x 5 class texels (1 m at 0.2 m) around the point, each read exactly (texelFetch); the
// boxes of the four nearest texel centres blended bilinearly, so 6 x 6 texels with the outer row
// and column weighted by the fraction; then a smoothstep. On a straight bank the weight is 0.5 on
// the class edge, 0 from 0.5 m outside it and 1 from 0.5 m inside; a channel narrower than 1 m
// never reaches 1. Texels are placed as in class_weights; outside the grid: no water.
float water_weight(vec2 xz) {
	ivec2 size = textureSize(surfaces, 0);
	vec2 t = (xz - surfaces_rect.xy) / surfaces_rect.zw * vec2(size) - 0.5;
	vec2 base = floor(t);
	vec2 f = t - base;
	ivec2 i0 = ivec2(base);
	float share = 0.0;
	for (int j = -2; j <= 3; j++) {
		float wy = j == -2 ? 1.0 - f.y : (j == 3 ? f.y : 1.0);
		for (int i = -2; i <= 3; i++) {
			ivec2 p = i0 + ivec2(i, j);
			if (p.x < 0 || p.y < 0 || p.x >= size.x || p.y >= size.y) {
				continue;
			}
			float wx = i == -2 ? 1.0 - f.x : (i == 3 ? f.x : 1.0);
			int c = int(texelFetch(surfaces, p, 0).r * 255.0 + 0.5);
			share += wx * wy * float(c == 2);
		}
	}
	return smoothstep(0.0, 1.0, share / 25.0);
}

// The water's phase offset at (x, z), in periods: two sines across the ground (wavelengths about
// 23 m and 37 m), together within ±0.5 of a period and smooth (no fract, so no seam), so that the
// two phases' restarts do not pulse over the whole river at once. A look value, never measured.
float water_phase(vec2 xz) {
	return 0.25 * sin(dot(xz, vec2(0.21, 0.17))) + 0.25 * sin(dot(xz, vec2(-0.11, 0.13)));
}

// The rock texture projected along the three world axes and blended by the terrain normal n
// (triplanar). Returns its luminance relative to its mean, its roughness, and the normal
// perturbation to add to n (UDN blend). p is the world position, dpdx and dpdy its screen
// derivatives (taken outside any branch, so textureGrad is exact inside one).
void rock_triplanar(vec3 p, vec3 n, vec3 dpdx, vec3 dpdy,
		out float relative, out float rough, out vec3 bump) {
	vec3 bw = pow(abs(n), vec3(4.0));
	bw /= bw.x + bw.y + bw.z;
	vec3 q = p / rock_scale_m;
	vec3 qx = dpdx / rock_scale_m;
	vec3 qy = dpdy / rock_scale_m;
	// X looks along x (u = z, v = y), Y along y (u = x, v = z), Z along z (u = x, v = y).
	vec2 ux = q.zy;
	vec2 uy = q.xz;
	vec2 uz = q.xy;
	float mean = mean_luminance(rock_albedo);
	relative = (
		luminance(textureGrad(rock_albedo, ux, qx.zy, qy.zy).rgb) * bw.x
		+ luminance(textureGrad(rock_albedo, uy, qx.xz, qy.xz).rgb) * bw.y
		+ luminance(textureGrad(rock_albedo, uz, qx.xy, qy.xy).rgb) * bw.z
	) / mean;
	rough = textureGrad(rock_roughness, ux, qx.zy, qy.zy).r * bw.x
		+ textureGrad(rock_roughness, uy, qx.xz, qy.xz).r * bw.y
		+ textureGrad(rock_roughness, uz, qx.xy, qy.xy).r * bw.z;
	vec3 tx = unpack_normal(textureGrad(rock_normal, ux, qx.zy, qy.zy));
	vec3 ty = unpack_normal(textureGrad(rock_normal, uy, qx.xz, qy.xz));
	vec3 tz = unpack_normal(textureGrad(rock_normal, uz, qx.xy, qy.xy));
	// Each projection's (along +u, along +v) in world axes.
	bump = vec3(0.0, tx.y, tx.x) * bw.x + vec3(ty.x, 0.0, ty.y) * bw.y + vec3(tz.x, tz.y, 0.0) * bw.z;
}

// A detail texture on the ground (u = x, v = z): its luminance relative to its mean and the
// normal perturbation (UDN) to add to the terrain normal.
void ground_detail(sampler2D albedo_tex, sampler2D normal_tex, vec2 xz, float scale, vec2 ddx,
		vec2 ddy, out float relative, out vec3 bump) {
	vec2 uv = xz / scale;
	relative = luminance(textureGrad(albedo_tex, uv, ddx / scale, ddy / scale).rgb)
		/ mean_luminance(albedo_tex);
	vec3 t = unpack_normal(textureGrad(normal_tex, uv, ddx / scale, ddy / scale));
	bump = vec3(t.x, 0.0, t.y);
}

// Varyings & Types
// Some are required for editor functions
varying float v_vertex_xz_dist;
varying vec3 v_vertex;

////////////////////////
// Vertex
////////////////////////

// Takes in world space XZ (UV) coordinates & search depth (only applicable for background mode none)
// Returns ivec3 with:
// XY: (0 to _region_size - 1) coordinates within a region
// Z: layer index used for texturearrays, -1 if not in a region
ivec3 get_index_coord(const vec2 uv, const int search) {
	vec2 r_uv = round(uv);
	vec2 o_uv = mod(r_uv,_region_size);
	ivec2 pos;
	int bounds, layer_index = -1;
	for (int i = -1; i < clamp(search, SKIP_PASS, FRAGMENT_PASS); i++) {
		if ((layer_index == -1 && _background_mode == 0u ) || i < 0) {
			r_uv -= i == -1 ? vec2(0.0) : vec2(float(o_uv.x <= o_uv.y), float(o_uv.y <= o_uv.x));
			pos = ivec2(floor((r_uv) * _region_texel_size)) + (_region_map_size / 2);
			bounds = int(uint(pos.x | pos.y) < uint(_region_map_size));
			layer_index = (_region_map[ pos.y * _region_map_size + pos.x ] * bounds - 1);
		}
	}
	return ivec3(ivec2(mod(r_uv,_region_size)), layer_index);
}

void vertex() {
	// Get vertex of flat plane in world coordinates and set world UV
	v_vertex = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;

	// Camera distance to vertex on flat plane
	v_vertex_xz_dist = length(v_vertex.xz - _camera_pos.xz);

	// Geomorph vertex, set end and start for linear height interpolate
	float scale = MODEL_MATRIX[0][0];
	float vertex_lerp = smoothstep(0.55, 0.95, (v_vertex_xz_dist / scale - _mesh_size - 4.0) / (_mesh_size - 2.0));
	vec2 v_fract = fract(VERTEX.xz * 0.5) * 2.0;
	// For LOD0 morph from a regular grid to an alternating grid to align with LOD1+
	vec2 shift = (scale < _vertex_spacing + 1e-6) ? // LOD0 or not
		// Shift from regular to symetric
		mix(v_fract, vec2(v_fract.x, -v_fract.y),
			round(fract(round(mod(v_vertex.z * _vertex_density, 4.0)) *
			round(mod(v_vertex.x * _vertex_density, 4.0)) * 0.25))
			) :
		// Symetric shift
		v_fract * round((fract(v_vertex.xz * 0.25 / scale) - 0.5) * 4.0);
	vec2 start_pos = v_vertex.xz * _vertex_density;
	vec2 end_pos = (v_vertex.xz - shift * scale) * _vertex_density;
	v_vertex.xz -= shift * scale * vertex_lerp;

	// UV coordinates in world space. Values are 0 to _region_size within regions
	UV = v_vertex.xz * _vertex_density;

	// UV coordinates in region space + texel offset. Values are 0 to 1 within regions
	UV2 = fma(UV, vec2(_region_texel_size), vec2(0.5 * _region_texel_size));

	// Discard vertices for Holes. 1 lookup
	ivec3 v_region = get_index_coord(start_pos, VERTEX_PASS);
	uint control = floatBitsToUint(texelFetch(_control_maps, v_region, 0)).r;
	bool hole = bool(control >>2u & 0x1u);

	// Show holes to all cameras except mouse camera (on exactly 1 layer)
	if ( !(CAMERA_VISIBLE_LAYERS == _mouse_layer) &&
			(hole || (_background_mode == 0u && v_region.z < 0))) {
		v_vertex.x = 0. / 0.;
	} else {
		// Interpolate Geomorph Start & End, set height. 2 Lookups.
		ivec3 uv_a = get_index_coord(start_pos, VERTEX_PASS);
		ivec3 uv_b = get_index_coord(end_pos, VERTEX_PASS);
		float h = mix(texelFetch(_height_maps, uv_a, 0).r, texelFetch(_height_maps, uv_b, 0).r, vertex_lerp);
		v_vertex.y = h;
	}

	// Convert model space to view space w/ skip_vertex_transform render mode
	VERTEX = (VIEW_MATRIX * vec4(v_vertex, 1.0)).xyz;
	NORMAL = normalize((MODELVIEW_MATRIX * vec4(NORMAL, 0.0)).xyz);
	BINORMAL = normalize((MODELVIEW_MATRIX * vec4(BINORMAL, 0.0)).xyz);
	TANGENT = normalize((MODELVIEW_MATRIX * vec4(TANGENT, 0.0)).xyz);
}

////////////////////////
// Fragment
////////////////////////

void fragment() {
	// Recover UVs
	vec2 uv = UV;
	//vec2 uv2 = UV2;

	// Lookup offsets, ID and blend weight
	const vec3 offsets = vec3(0, 1, 2);
	vec2 index_id = floor(uv);
	vec2 weight = fract(uv);
	vec2 invert = 1.0 - weight;
	vec4 weights = vec4(
		invert.x * weight.y, // 0
		weight.x * weight.y, // 1
		weight.x * invert.y, // 2
		invert.x * invert.y  // 3
	);

	vec3 base_ddx = dFdxCoarse(v_vertex);
	vec3 base_ddy = dFdyCoarse(v_vertex);
	//vec4 base_derivatives = vec4(base_ddx.xz, base_ddy.xz);
	// Calculate the effective mipmap for regionspace, and if less than 0,
	// skip all extra lookups required for bilinear blend.
	float region_mip = log2(max(length(base_ddx.xz), length(base_ddy.xz)) * _vertex_density);
	bool bilerp = region_mip < 0.0;

	ivec3 index[4];
	// control map lookups, used for some normal lookups as well
	index[0] = get_index_coord(index_id + offsets.xy, FRAGMENT_PASS);
	index[1] = get_index_coord(index_id + offsets.yy, FRAGMENT_PASS);
	index[2] = get_index_coord(index_id + offsets.yx, FRAGMENT_PASS);
	index[3] = get_index_coord(index_id + offsets.xx, FRAGMENT_PASS);

	// Terrain normals
	vec3 index_normal[4];
	float h[4];
	// allows additional derivatives, eg world noise, brush previews etc
	float u = 0.0;
	float v = 0.0;

	// Re-use index[] for the first lookups, skipping some math. 3 lookups
	h[3] = texelFetch(_height_maps, index[3], 0).r; // 0 (0,0)
	h[2] = texelFetch(_height_maps, index[2], 0).r; // 1 (1,0)
	h[0] = texelFetch(_height_maps, index[0], 0).r; // 2 (0,1)
	index_normal[3] = normalize(vec3(h[3] - h[2] + u, _vertex_spacing, h[3] - h[0] + v));

	// Set flat world normal - overriden if bilerp is true
	vec3 w_normal = index_normal[3];

	// Branching smooth normals must be done seperatley for correct normals at all 4 index ids
	if (bilerp) {
		// 5 lookups
		// Fetch the additional required height values for smooth normals
		h[1] = texelFetch(_height_maps, index[1], 0).r; // 3 (1,1)
		float h_4 = texelFetch(_height_maps, get_index_coord(index_id + offsets.yz, FRAGMENT_PASS), 0).r; // 4 (1,2)
		float h_5 = texelFetch(_height_maps, get_index_coord(index_id + offsets.zy, FRAGMENT_PASS), 0).r; // 5 (2,1)
		float h_6 = texelFetch(_height_maps, get_index_coord(index_id + offsets.zx, FRAGMENT_PASS), 0).r; // 6 (2,0)
		float h_7 = texelFetch(_height_maps, get_index_coord(index_id + offsets.xz, FRAGMENT_PASS), 0).r; // 7 (0,2)

		// Calculate the normal for the remaining index ids.
		index_normal[0] = normalize(vec3(h[0] - h[1] + u, _vertex_spacing, h[0] - h_7 + v));
		index_normal[1] = normalize(vec3(h[1] - h_5 + u, _vertex_spacing, h[1] - h_4 + v));
		index_normal[2] = normalize(vec3(h[2] - h_6 + u, _vertex_spacing, h[2] - h[1] + v));

		// Set interpolated world normal
		w_normal =
			index_normal[0] * weights[0] +
			index_normal[1] * weights[1] +
			index_normal[2] * weights[2] +
			index_normal[3] * weights[3] ;
	}

	// Apply terrain normals
	vec3 w_tangent = normalize(cross(w_normal, vec3(0.0, 0.0, 1.0)));
	vec3 w_binormal = normalize(cross(w_normal, w_tangent));
	NORMAL = mat3(VIEW_MATRIX) * w_normal;
	TANGENT = mat3(VIEW_MATRIX) * w_tangent;
	BINORMAL = mat3(VIEW_MATRIX) * w_binormal;

	if (flat_terrain_normals) {
		NORMAL = normalize(cross(dFdyCoarse(VERTEX),dFdxCoarse(VERTEX)));
		TANGENT = normalize(cross(NORMAL, VIEW_MATRIX[2].xyz));
		BINORMAL = normalize(cross(NORMAL, TANGENT));
	}

	// The photo look. n is the terrain's world normal from above. The position and its screen
	// derivatives are world-space ones (v_vertex is in world space), taken here outside any
	// branch, so there is no seam at Terrain3D's region borders and textureGrad is exact inside
	// the branches below.
	vec3 n = w_normal;
	vec2 xz = v_vertex.xz;
	vec2 ddx_xz = base_ddx.xz;
	vec2 ddy_xz = base_ddy.xz;
	float dist = length(VERTEX);

	// The photo, sampled everywhere (texture() outside any branch, so its derivatives stay
	// valid); outside it the neutral colour.
	vec2 puv = (v_vertex.xz - photo_rect.xy) / photo_rect.zw;
	vec3 albedo = texture(photo, puv).rgb;
	vec2 muv = (v_vertex.xz - capture_shadow_rect.xy) / capture_shadow_rect.zw;
	float m = texture(capture_shadow, muv).r;
	if (any(lessThan(muv, vec2(0.0))) || any(greaterThan(muv, vec2(1.0)))) {
		m = 0.0;
	}
	albedo = min(albedo * (1.0 + (shadow_lift - 1.0) * m), vec3(1.0));
	if (any(lessThan(puv, vec2(0.0))) || any(greaterThan(puv, vec2(1.0)))) {
		albedo = outside_albedo;
	}
	float roughness = PHOTO_ROUGHNESS;
	vec3 bump = vec3(0.0);

	vec4 classes = class_weights(xz); // rock, water, path, road

	// Rock: only on class rock, by the slope of the terrain.
	float slope = acos(clamp(n.y, -1.0, 1.0));
	float w_rock = classes.x * smoothstep(radians(35.0), radians(55.0), slope);
	if (w_rock > 0.0) {
		float relative;
		float rough;
		vec3 rock_bump;
		rock_triplanar(v_vertex, n, base_ddx, base_ddy, relative, rough, rock_bump);
		albedo *= mix(1.0, relative, w_rock);
		roughness = mix(roughness, rough, w_rock);
		bump += rock_bump * w_rock;
	}

	// Roads and paths: detail near the camera, the photo's colour kept (mean 1).
	float near = 1.0 - smoothstep(near_fade_m / 3.0, near_fade_m, dist);
	float w_road = classes.w * near;
	float w_path = classes.z * near;
	if (w_road > 0.0) {
		float relative;
		vec3 detail_bump;
		ground_detail(road_albedo, road_normal, xz, road_scale_m, ddx_xz, ddy_xz, relative, detail_bump);
		albedo *= mix(1.0, relative, w_road);
		bump += detail_bump * detail_normal_strength * w_road;
	}
	if (w_path > 0.0) {
		float relative;
		vec3 detail_bump;
		ground_detail(path_albedo, path_normal, xz, path_scale_m, ddx_xz, ddy_xz, relative, detail_bump);
		albedo *= mix(1.0, relative, w_path);
		bump += detail_bump * detail_normal_strength * w_path;
	}

	// Water: the photo's colour × water_albedo, roughness WATER_ROUGHNESS, its weight eased over
	// 1 m at the bank; both ripple maps drift downstream along the flow, each read in two phases
	// (p0, p1, half a period apart) whose weights (w0, w1) sum to 1 and are 0 at each restart.
	float w_water = water_weight(xz);
	if (w_water > 0.0) {
		vec4 t = texture(water_flow, (xz - surfaces_rect.xy) / surfaces_rect.zw);
		vec2 flow = (t.rg * 255.0 - 128.0) / 127.0 * t.b;
		float p0 = fract(TIME / water_phase_s + water_phase(xz));
		float p1 = fract(p0 + 0.5);
		// Each map's offset over one whole period, downstream (m).
		vec2 da = flow * water_speed_a * water_phase_s;
		vec2 db = flow * water_speed_b * water_phase_s;
		// The pattern at xz is the one from (xz - offset): it moves along +flow.
		vec2 ua0 = (xz - p0 * da) / water_scale_a_m;
		vec2 ua1 = (xz - p1 * da) / water_scale_a_m;
		vec2 ub0 = (xz - p0 * db) / water_scale_b_m;
		vec2 ub1 = (xz - p1 * db) / water_scale_b_m;
		vec2 dxa = ddx_xz / water_scale_a_m;
		vec2 dya = ddy_xz / water_scale_a_m;
		vec2 dxb = ddx_xz / water_scale_b_m;
		vec2 dyb = ddy_xz / water_scale_b_m;
		vec3 na0 = unpack_normal(textureGrad(water_normal_a, ua0, dxa, dya));
		vec3 na1 = unpack_normal(textureGrad(water_normal_a, ua1, dxa, dya));
		vec3 nb0 = unpack_normal(textureGrad(water_normal_b, ub0, dxb, dyb));
		vec3 nb1 = unpack_normal(textureGrad(water_normal_b, ub1, dxb, dyb));
		float w0 = 1.0 - abs(2.0 * p0 - 1.0);
		float w1 = 1.0 - abs(2.0 * p1 - 1.0);
		vec2 ripple = (w0 * (na0.xy + nb0.xy) + w1 * (na1.xy + nb1.xy)) * water_normal_strength;
		bump = mix(bump, vec3(ripple.x, 0.0, ripple.y), w_water);
		albedo *= mix(1.0, water_albedo, w_water);
		roughness = mix(roughness, WATER_ROUGHNESS, w_water);
	}

	if (!flat_terrain_normals) {
		NORMAL = mat3(VIEW_MATRIX) * normalize(n + bump);
	}
	ALBEDO = albedo;
	ROUGHNESS = roughness;
}
