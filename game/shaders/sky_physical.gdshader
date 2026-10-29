// NOTE: Shader automatically converted from Godot Engine 4.6.3.stable's PhysicalSkyMaterial.
// mattini: brief v0.4.0-05 (M4-05 decision 4). Godot's code (MIT, in the credits) with debanding
// mattini: and the night sky on, as Godot fills them; every change is marked 'mattini:' on a line
// mattini: of its own. The rig (game/scripts/sky/sky_rig.gd) sets the uniforms added here.
// mattini: Added: stars_strength (the night sky's fade), twilight_and_glow() (the dusk towards the
// mattini: sun and the night sky's faint glow), and the sun's disk from sun_disk_deg. The ground's
// mattini: blend line and ground_color's declaration are Godot's; the rig sets ground_color
// mattini: (SkyRig.GROUND_COLOUR, SPEC section 13 row 52).

shader_type sky;
render_mode use_debanding;

uniform float rayleigh : hint_range(0, 64) = 2.0;
uniform vec4 rayleigh_color : source_color = vec4(0.3, 0.405, 0.6, 1.0);
uniform float mie : hint_range(0, 1) = 0.005;
uniform float mie_eccentricity : hint_range(-1, 1) = 0.8;
uniform vec4 mie_color : source_color = vec4(0.69, 0.729, 0.812, 1.0);

uniform float turbidity : hint_range(0, 1000) = 10.0;
uniform float sun_disk_scale : hint_range(0, 360) = 1.0;
uniform vec4 ground_color : source_color = vec4(0.1, 0.07, 0.034, 1.0);
uniform float exposure : hint_range(0, 128) = 1.0;

uniform sampler2D night_sky : filter_linear, source_color, hint_default_black;
// mattini: 0 by day, 1 at a sun elevation of -12 degrees and below; multiplies the night sky.
uniform float stars_strength : hint_range(0, 1) = 0.0;
// mattini: the twilight and the night sky's glow. sun_direction is the unit vector towards the
// mattini: sun, set by the rig every frame (a hidden sun light is not the sky's LIGHT0).
uniform vec3 sun_direction = vec3(0.0, 1.0, 0.0);
uniform vec3 twilight_colour = vec3(0.0);
uniform float twilight_energy : hint_range(0, 16) = 0.3;
uniform vec3 skyglow = vec3(0.004, 0.005, 0.009);
// mattini: the sun's disk in degrees, in place of Godot's LIGHT0_SIZE (0 with a sharp sun light).
uniform float sun_disk_deg : hint_range(0, 5) = 0.53;

const vec3 UP = vec3( 0.0, 1.0, 0.0 );

// Optical length at zenith for molecules.
const float rayleigh_zenith_size = 8.4e3;
const float mie_zenith_size = 1.25e3;

float henyey_greenstein(float cos_theta, float g) {
	const float k = 0.0795774715459;
	return k * (1.0 - g * g) / (pow(1.0 + g * g - 2.0 * g * cos_theta, 1.5));
}

// mattini: twilight towards the sun and the faint glow of the night sky, added before the exposure.
// mattini: horizontal and elevation use y as up, as Godot's own UP does.
vec3 twilight_and_glow(vec3 dir) {
	vec2 eye_h = dir.xz;
	vec2 sun_h = sun_direction.xz;
	float facing = 0.0;
	if (length(eye_h) > 1e-5 && length(sun_h) > 1e-5) {
		facing = max(0.0, dot(normalize(eye_h), normalize(sun_h)));
	}
	float eye_elevation = degrees(asin(clamp(dir.y, -1.0, 1.0)));
	float shape = (0.3 + 0.7 * pow(facing, 3.0)) * exp(-max(0.0, eye_elevation) / 12.0);
	return twilight_colour * twilight_energy * shape + skyglow;
}

void sky() {
	if (LIGHT0_ENABLED) {
		float zenith_angle = clamp( dot(UP, normalize(LIGHT0_DIRECTION)), -1.0, 1.0 );
		float sun_energy = max(0.0, 0.757 * zenith_angle) * LIGHT0_ENERGY;
		float sun_fade = 1.0 - clamp(1.0 - exp(LIGHT0_DIRECTION.y), 0.0, 1.0);

		// Rayleigh coefficients.
		float rayleigh_coefficient = rayleigh - ( 1.0 * ( 1.0 - sun_fade ) );
		vec3 rayleigh_beta = rayleigh_coefficient * rayleigh_color.rgb * 0.0001;
		// mie coefficients from Preetham
		vec3 mie_beta = turbidity * mie * mie_color.rgb * 0.000434;

		// Optical length.
		float zenith = max(0.0, dot(UP, EYEDIR));
		float optical_mass = 1.0 / (zenith + 0.15 * pow(3.885 + 54.5 * zenith, -1.253));
		float rayleigh_scatter = rayleigh_zenith_size * optical_mass;
		float mie_scatter = mie_zenith_size * optical_mass;

		// Light extinction based on thickness of atmosphere.
		vec3 extinction = exp(-(rayleigh_beta * rayleigh_scatter + mie_beta * mie_scatter));

		// In scattering.
		float cos_theta = dot(EYEDIR, normalize(LIGHT0_DIRECTION));

		float rayleigh_phase = (3.0 / (16.0 * PI)) * (1.0 + pow(cos_theta * 0.5 + 0.5, 2.0));
		vec3 betaRTheta = rayleigh_beta * rayleigh_phase;

		float mie_phase = henyey_greenstein(cos_theta, mie_eccentricity);
		vec3 betaMTheta = mie_beta * mie_phase;

		vec3 Lin = pow(sun_energy * ((betaRTheta + betaMTheta) / (rayleigh_beta + mie_beta)) * (1.0 - extinction), vec3(1.5));
		// Hack from https://github.com/mrdoob/three.js/blob/master/examples/jsm/objects/Sky.js
		Lin *= mix(vec3(1.0), pow(sun_energy * ((betaRTheta + betaMTheta) / (rayleigh_beta + mie_beta)) * extinction, vec3(0.5)), clamp(pow(1.0 - zenith_angle, 5.0), 0.0, 1.0));

		// Hack in the ground color.
		Lin  *= mix(ground_color.rgb, vec3(1.0), smoothstep(-0.1, 0.1, dot(UP, EYEDIR)));

		// Solar disk and out-scattering.
		// mattini: the disk from sun_disk_deg and sun_direction, not LIGHT0_SIZE and cos_theta.
		// mattini: it is drawn only in this branch, so only while the sun light is shown (from -1 degree).
		float sunAngularDiameterCos = cos(radians(sun_disk_deg) * sun_disk_scale);
		float sunAngularDiameterCos2 = cos(radians(sun_disk_deg) * sun_disk_scale * 0.5);
		float sundisk = smoothstep(sunAngularDiameterCos, sunAngularDiameterCos2, dot(EYEDIR, normalize(sun_direction)));
		vec3 L0 = (sun_energy * extinction) * sundisk * LIGHT0_COLOR;
		// mattini: the night sky fades in with stars_strength.
		L0 += texture(night_sky, SKY_COORDS).xyz * extinction * stars_strength;

		vec3 color = Lin + L0;
		COLOR = pow(color, vec3(1.0 / (1.2 + (1.2 * sun_fade))));
		// mattini: the twilight and the glow, before the exposure.
		COLOR += twilight_and_glow(EYEDIR);
		COLOR *= exposure;
	} else {
		// There is no sun, so display night_sky and nothing else.
		// mattini: the night sky fades in with stars_strength; the glow and the twilight on top.
		COLOR = texture(night_sky, SKY_COORDS).xyz * stars_strength;
		COLOR += twilight_and_glow(EYEDIR);
		COLOR *= exposure;
	}
}
