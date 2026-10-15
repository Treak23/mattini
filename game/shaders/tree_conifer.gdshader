// mattini's trees (brief M3-11; docs/SPEC.md §8, the trees; §10, M3's game: the look).
//
// Draws TreeLoader's MultiMeshes of the generic conifer: three variants of one topology, flat
// facets, the crown coloured from the terrain's photo.
//
// - The variant: VERTEX is variant 0, CUSTOM0.xyz variant 1, CUSTOM1.xyz variant 2; one is
//   picked by a hash of the instance's origin, so a tree keeps its shape from frame to frame.
// - The facets: flat normals from screen-space derivatives of the view-space position, so the
//   mesh carries no normals; cull_disabled draws both sides of the boughs.
// - The crown's colour: the photo at the tree's position (the instance's origin in world space,
//   which is the photo rectangle's space, local x0, z0, width, depth, while the trees' parent
//   sits at the origin unturned and unscaled, as the main scene's root does), at the mip
//   level of the crown's width,
//   times a look value. It is sampled here, in the vertex shader, from a source_color sampler:
//   colours never ride on instance data, because the renderers treat that differently
//   (brain.md H21).
// - Without a photo (photo_rect has no width or depth): a PLACEHOLDER green for the crown,
//   labelled as one. The trunk's brown is a PLACEHOLDER too: the data gives no species and no
//   bark. Neither is a measured colour.
//
// TEX_UV.x is 1 on the trunk and 0 on the crown; TEX_UV.y shades a tier from its rim to its apex.

shader_type spatial;
render_mode cull_disabled, diffuse_burley, specular_schlick_ggx;

uniform sampler2D photo : source_color, filter_linear_mipmap, repeat_disable;
// Local x0, z0, width and depth of the photo, in metres: the rectangle the terrain's photo
// covers. The default has no width: no photo.
uniform vec4 photo_rect = vec4(0.0);
// A look value (brief M3-11): the photo shows crowns in their own shadow, darker than the
// trees' sunlit tops.
uniform float crown_boost = 1.25;
// PLACEHOLDER colours (see above).
uniform vec3 placeholder_crown : source_color = vec3(0.17, 0.23, 0.13);
uniform vec3 trunk_color : source_color = vec3(0.22, 0.15, 0.09);
// How much darker a tier is at its rim than at its apex (a look value).
uniform float rim_shade = 0.75;

varying vec3 crown_color;
varying float trunk;
varying float shade;

uint hash_origin(vec3 origin) {
	ivec2 cell = ivec2(floor(origin.xz * 2.0));
	uint h = uint(cell.x) * 0x9E3779B1u + uint(cell.y) * 0x85EBCA6Bu;
	h = (h ^ (h >> 15u)) * 0x2C1B3C6Du;
	h = (h ^ (h >> 12u)) * 0x297A2D39u;
	return h ^ (h >> 15u);
}

void vertex() {
	vec3 origin = MODEL_MATRIX[3].xyz;
	uint variant = hash_origin(origin) % 3u;
	if (variant == 1u) {
		VERTEX = CUSTOM0.xyz;
	} else if (variant == 2u) {
		VERTEX = CUSTOM1.xyz;
	}
	trunk = UV.x;
	shade = mix(rim_shade, 1.0, UV.y);
	if (photo_rect.z > 0.0 && photo_rect.w > 0.0) {
		// The crown's width in photo texels picks the mip level: a wide crown averages the
		// photo under it.
		float crown_width = 2.0 * length(MODEL_MATRIX[0].xyz);
		float texel = photo_rect.z / float(textureSize(photo, 0).x);
		float lod = log2(max(crown_width / texel, 1.0));
		vec2 uv = (origin.xz - photo_rect.xy) / photo_rect.zw;
		crown_color = min(textureLod(photo, uv, lod).rgb * crown_boost, vec3(1.0));
	} else {
		crown_color = placeholder_crown;
	}
}

void fragment() {
	NORMAL = normalize(cross(dFdx(VERTEX), dFdy(VERTEX)));
	ALBEDO = mix(crown_color * shade, trunk_color, trunk);
	ROUGHNESS = 0.95;
	SPECULAR = 0.15;
}
