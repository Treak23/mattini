class_name SkyRig
extends RefCounted
## The sky rig (brief v0.4.0-05; M4-05 decisions 1 to 5; m4-design §6; SPEC §13 rows 51, 52)
## sets the sun light, a moon light, the exposure and the physical sky
## (res://shaders/sky_physical.gdshader) of an Environment.
##
## The rig reads no world config and no clock: it is given a frame (the scene's local east,
## north and up as the columns of a Basis) and the directions, and measures every elevation
## against that frame's up, never the scene's y. The stars are brief v0.4.0-06's (M4-05 section S
## on the Hipparcos Catalogue, SPEC §13 row 51): [method star_image] draws the star table
## res://sky/stars.csv and [method apply] sets the celestial basis the sky shader samples it by.
## The table's positions are ICRS at epoch J1991.25, used as given: not precessed to the date, so
## the stars stand 0.13 to 0.35 degrees from their mean places of 2023-09-06 (measured by the pin
## author; one texel of the image is 0.088 degrees).

const SHADER_PATH := "res://shaders/sky_physical.gdshader"

## The sky's ground below the horizon: the valley's own colour (SPEC §13 row 52, the owner's
## "3a"; brief v0.4.0-05 decision 6), in place of Godot's default (0.1, 0.07, 0.034), which left
## a shaded vertical face at a quarter of 0.3.1's light. Design data, measured in software
## Forward+ at the start's sun (grid azimuth 184.65, elevation 50.34): the village photo's mean
## linear colour (0.148308, 0.166591, 0.119924: the 0.2 m JPEG config/photo.json expects) times
## K = the radiance of flat white ground over the horizon's radiance, per channel (7.6400,
## 6.9994, 6.4102), times 2.6: at K itself a shaded vertical face kept 0.50 of 0.3.1's ratio to
## lit flat ground, and 2.6 is the smallest step of 0.1 that keeps it at 0.3.1's or above
## (0.0400 against 0.0391). A source_color value: Forward+ linearises it as it takes it.
const GROUND_COLOUR := Color(2.946, 3.032, 1.999)

## The sun's colour at an elevation of 0 degrees and below (white from 10 degrees up).
const SUN_LOW := Color(1.0, 0.72, 0.50)
## The moon light's colour.
const MOON_COLOUR := Color(0.80, 0.85, 1.0)
## The twilight's colour at a sun elevation of 0 degrees and above, at -6 and at -12 and below
## (design's rulings of 2026-10-17).
const TWILIGHT_AT_0 := Vector3(1.00, 0.55, 0.30)
const TWILIGHT_AT_MINUS_6 := Vector3(0.35, 0.30, 0.55)
const TWILIGHT_AT_MINUS_12 := Vector3(0.05, 0.06, 0.12)
## The exposure by day (a sun elevation of 10 degrees and above) and at night (-12 and below).
const EXPOSURE_DAY := 0.70
const EXPOSURE_NIGHT := 4.0
## The moon light's energy at full phase and height.
const MOON_ENERGY := 0.03

## The star image's size: an equirectangular image in celestial coordinates.
const STAR_WIDTH := 4096
const STAR_HEIGHT := 2048

## The sky's material, a ShaderMaterial of res://shaders/sky_physical.gdshader.
var sky_material: ShaderMaterial
## The latitude in degrees, from [method create]; [method apply] builds the celestial basis from it.
var latitude_deg := 0.0

var _sun: DirectionalLight3D
var _moon: DirectionalLight3D
var _environment: Environment
var _up := Vector3.UP
var _east := Vector3.RIGHT
var _north := Vector3.FORWARD


## Makes a rig for [param sun], [param moon] and [param environment]. [param frame]'s columns are
## the scene's local east, north and up. Sets what never changes: the sun's shadows on, their
## maximum distance 3000 m and [code]light_angular_distance[/code] 0 (sharp shadows: the sky draws
## the sun's disk from its own uniform); the moon's shadows on, its sky mode light only (so the
## sun stays the sky's LIGHT0) and its colour; the environment's background the sky, whose
## material is a ShaderMaterial of the physical sky (property [member sky_material]) with
## [constant GROUND_COLOUR] as its ground, ambient light from the sky with contribution 0.25 and
## Filmic tonemapping. With [param stars], an ImageTexture of it is the material's night_sky.
static func create(
	sun: DirectionalLight3D,
	moon: DirectionalLight3D,
	environment: Environment,
	frame: Basis,
	latitude_deg: float,
	stars: Image = null
) -> SkyRig:
	var rig := SkyRig.new()
	rig._sun = sun
	rig._moon = moon
	rig._environment = environment
	rig._up = frame.z.normalized()
	rig._east = frame.x.normalized()
	rig._north = frame.y.normalized()
	rig.latitude_deg = latitude_deg

	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 3000.0
	sun.light_angular_distance = 0.0
	moon.shadow_enabled = true
	moon.sky_mode = DirectionalLight3D.SKY_MODE_LIGHT_ONLY
	moon.light_color = MOON_COLOUR

	var material := ShaderMaterial.new()
	material.shader = load(SHADER_PATH)
	material.set_shader_parameter("ground_color", GROUND_COLOUR)
	if stars != null:
		material.set_shader_parameter("night_sky", ImageTexture.create_from_image(stars))
	rig.sky_material = material
	var sky := Sky.new()
	sky.sky_material = material
	environment.background_mode = Environment.BG_SKY
	environment.sky = sky
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	environment.ambient_light_sky_contribution = 0.25
	environment.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	return rig


## The star image (brief v0.4.0-06; M4-05 decision 8) of the table at [param path] (lines
## starting with "# " and the line "ra_deg,dec_deg,vmag" draw nothing; every other line is
## "ra_deg,dec_deg,vmag" as three numbers): 4096 x 2048, FORMAT_RGBE9995 (a first-magnitude star
## and a sixth-magnitude one fit one texel), no mipmaps, equirectangular in celestial
## coordinates: u = right ascension / 360, v = (90 - declination) / 180. A star adds
## 10^(-0.4 V) to red, green and blue (the stars are white) of the row
## min(floor((90 - dec) / 180 * 2048), 2047), at the columns c - h to c + h, wrapped, with
## c = floor(ra / 360 * 4096) mod 4096 and h = floor(0.5 / cos(dec)): the run keeps a star about
## one texel high wide at any declination, where one texel would be 0.001 degrees wide at
## Polaris and show nothing. A file that cannot be read, or a line that is not three numbers, is
## an error (push_error, naming the file and the line) and null. The positions are not
## precessed: see the class comment.
static func star_image(path: String) -> Image:
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		push_error("SkyRig: %s: cannot be read (error %d)" % [path, FileAccess.get_open_error()])
		return null
	var light := {}
	var number := 0
	while not file.eof_reached():
		var line := file.get_line().strip_edges()
		number += 1
		if line.is_empty() or line.begins_with("# ") or line == "ra_deg,dec_deg,vmag":
			continue
		var fields := line.split(",")
		if (
			fields.size() != 3
			or not fields[0].is_valid_float()
			or not fields[1].is_valid_float()
			or not fields[2].is_valid_float()
		):
			push_error("SkyRig: %s line %d: not three numbers: %s" % [path, number, line])
			return null
		var ra := fields[0].to_float()
		var dec := fields[1].to_float()
		var flux := pow(10.0, -0.4 * fields[2].to_float())
		var col := int(floor(ra / 360.0 * STAR_WIDTH)) % STAR_WIDTH
		var row := mini(int(floor((90.0 - dec) / 180.0 * STAR_HEIGHT)), STAR_HEIGHT - 1)
		var half := int(floor(0.5 / cos(deg_to_rad(dec))))
		for c in range(col - half, col + half + 1):
			var key := row * STAR_WIDTH + posmod(c, STAR_WIDTH)
			light[key] = light.get(key, 0.0) + flux
	var image := Image.create(STAR_WIDTH, STAR_HEIGHT, false, Image.FORMAT_RGBE9995)
	for key: int in light:
		var value: float = light[key]
		image.set_pixel(key % STAR_WIDTH, key / STAR_WIDTH, Color(value, value, value))
	return image


## Sets the lights, the exposure and the sky for the unit vectors [param to_sun] and
## [param to_moon] (local, in the frame given to [method create]) and the moon's illuminated
## fraction [param moon_fraction]. Called every frame. Each elevation is measured against the
## frame's up. Sets the sky material's stars_strength, sun_direction (every frame, also while the
## sun light is hidden), twilight_colour and celestial_basis; it does not touch ground_color.
## [param sidereal_deg] is the local sidereal time in degrees.
##
## The celestial basis (brief v0.4.0-06; M4-05 decision 9) turns a scene direction into celestial
## coordinates (x towards RA 0 on the equator, y towards RA 90, z the north celestial pole). With
## the frame's east E, north N and up U, the latitude phi ([member latitude_deg]) and the local
## sidereal time theta: the pole P = N cos(phi) + U sin(phi), the equator's meridian point
## Q = U cos(phi) - N sin(phi), X = Q cos(theta) - E sin(theta), Y = Q sin(theta) + E cos(theta);
## the basis whose rows are X, Y, P. Measured in software Forward+ (brief v0.4.0-06 gate P2): the
## shader's mat3 uniform reaches it as GDScript multiplies it, neither mirrored nor transposed.
func apply(to_sun: Vector3, to_moon: Vector3, moon_fraction: float, sidereal_deg: float) -> void:
	var sun_dir := to_sun.normalized()
	var moon_dir := to_moon.normalized()
	var sun_el := _elevation(sun_dir)
	var moon_el := _elevation(moon_dir)

	_point(_sun, sun_dir)
	_sun.visible = sun_el >= -1.0
	_sun.light_energy = smoothstep(-1.0, 10.0, sun_el)
	_sun.light_color = SUN_LOW.lerp(Color.WHITE, clampf(sun_el / 10.0, 0.0, 1.0))

	_point(_moon, moon_dir)
	_moon.visible = moon_el >= 0.0
	_moon.light_energy = MOON_ENERGY * moon_fraction * smoothstep(0.0, 5.0, moon_el)

	_environment.tonemap_exposure = _exposure(sun_el)
	sky_material.set_shader_parameter("stars_strength", 1.0 - smoothstep(-12.0, -6.0, sun_el))
	sky_material.set_shader_parameter("sun_direction", sun_dir)
	sky_material.set_shader_parameter("twilight_colour", _twilight(sun_el))
	sky_material.set_shader_parameter("celestial_basis", _celestial_basis(sidereal_deg))


## The basis of [method apply]'s comment for the local sidereal time [param sidereal_deg].
func _celestial_basis(sidereal_deg: float) -> Basis:
	var phi := deg_to_rad(latitude_deg)
	var theta := deg_to_rad(sidereal_deg)
	var pole := _north * cos(phi) + _up * sin(phi)
	var meridian := _up * cos(phi) - _north * sin(phi)
	var x_axis := meridian * cos(theta) - _east * sin(theta)
	var y_axis := meridian * sin(theta) + _east * cos(theta)
	return Basis(x_axis, y_axis, pole).transposed()


## The elevation in degrees of the unit vector [param direction] above the frame's horizon.
func _elevation(direction: Vector3) -> float:
	return rad_to_deg(asin(clampf(direction.dot(_up), -1.0, 1.0)))


## Turns [param light] to shine along its -z from [param direction] (as M3's sun).
func _point(light: DirectionalLight3D, direction: Vector3) -> void:
	# looking_at needs a target that is not parallel to its up: at the zenith, take another.
	var up := _up
	if absf(direction.dot(_up)) > 0.9999:
		up = _up.cross(Vector3.RIGHT) if absf(_up.x) < 0.9 else _up.cross(Vector3.FORWARD)
	var basis := Basis.looking_at(-direction, up)
	if light.is_inside_tree():
		light.global_basis = basis
	else:
		light.basis = basis


## The exposure at a sun elevation: 0.70 from 10 degrees up, 4.0 from -12 down, interpolated in
## log space between.
func _exposure(sun_el: float) -> float:
	var t := clampf((10.0 - sun_el) / 22.0, 0.0, 1.0)
	return exp(lerpf(log(EXPOSURE_DAY), log(EXPOSURE_NIGHT), t))


## The twilight's colour at a sun elevation, t(e) times colour(e) (design's rulings of
## 2026-10-17).
func _twilight(sun_el: float) -> Vector3:
	var t := smoothstep(-12.0, -4.0, sun_el) * (1.0 - smoothstep(0.0, 6.0, sun_el))
	var colour := TWILIGHT_AT_0
	if sun_el < -6.0:
		colour = TWILIGHT_AT_MINUS_12.lerp(
			TWILIGHT_AT_MINUS_6, clampf((sun_el + 12.0) / 6.0, 0.0, 1.0)
		)
	elif sun_el < 0.0:
		colour = TWILIGHT_AT_MINUS_6.lerp(TWILIGHT_AT_0, (sun_el + 6.0) / 6.0)
	return colour * t
