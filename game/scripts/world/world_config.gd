class_name WorldConfig
extends RefCounted
## The game side of the world mapping (docs/SPEC.md §6; CLAUDE.md Hard Rule 4).
##
## Learns the origin, the height offset and the axis mapping only from the world block of
## the generated manifest, which the pipeline copies verbatim from config/world.json.
## Refuses a mapping that is not a proper rotation, as the pipeline does. Converts in
## 64-bit floats: the origin is subtracted before any Vector3 (32-bit) is built
## (brain.md H5). height_offset_m is read as the vertical part of the origin
## (y = H - height_offset_m), the reading the pipeline took (brief M0-02 Findings).

const MANIFEST_SCHEMA := 1
const WORLD_SCHEMA := 1
const CRS := {"horizontal": "EPSG:2056", "vertical": "EPSG:5728"}
## LV95 east, LV95 north, LN02 height: a right-handed frame.
const SOURCE_AXES := ["e", "n", "h"]
## Godot x (right), y (up), z (back): a right-handed frame.
const GAME_AXES := ["x", "y", "z"]

var origin_e: float
var origin_n: float
var height_offset: float
## For each game axis (x, y, z): the index into SOURCE_AXES it reads, and its sign.
var _source_index := PackedInt32Array([0, 0, 0])
var _sign := PackedFloat64Array([0.0, 0.0, 0.0])


## Reads the manifest at [param path]. Returns null and calls push_error naming the path
## when the file cannot be read or its world block is not valid.
static func from_manifest(path: String) -> WorldConfig:
	var text := FileAccess.get_file_as_string(path)
	if text.is_empty():
		var reason := error_string(FileAccess.get_open_error())
		push_error("WorldConfig: %s: cannot read the manifest (%s)" % [path, reason])
		return null
	var json := JSON.new()
	if json.parse(text) != OK:
		var where := "line %d: %s" % [json.get_error_line(), json.get_error_message()]
		push_error("WorldConfig: %s: not valid JSON, %s" % [path, where])
		return null
	var world := WorldConfig.new()
	var problem := world._read_manifest(json.data)
	if not problem.is_empty():
		push_error("WorldConfig: %s: %s" % [path, problem])
		return null
	return world


## LV95 easting, northing and LN02 height to Godot local coordinates in metres.
func to_local(e: float, n: float, h: float) -> Vector3:
	# 64-bit subtraction first; only the small local values are narrowed to 32 bits.
	var source := PackedFloat64Array([e - origin_e, n - origin_n, h - height_offset])
	return Vector3(
		_sign[0] * source[_source_index[0]],
		_sign[1] * source[_source_index[1]],
		_sign[2] * source[_source_index[2]],
	)


## Godot local coordinates in metres to [e, n, h]: LV95 easting, northing, LN02 height.
func to_lv95(p: Vector3) -> PackedFloat64Array:
	var source := PackedFloat64Array([0.0, 0.0, 0.0])
	for axis in GAME_AXES.size():
		source[_source_index[axis]] = _sign[axis] * p[axis]
	return PackedFloat64Array(
		[source[0] + origin_e, source[1] + origin_n, source[2] + height_offset]
	)


## Validates the manifest and fills this object; returns what is wrong, or "".
func _read_manifest(manifest: Variant) -> String:
	if typeof(manifest) != TYPE_DICTIONARY:
		return "the manifest is not a JSON object"
	if not _is_number(manifest.get("schema")) or manifest["schema"] != MANIFEST_SCHEMA:
		return "manifest schema must be %d, found %s" % [MANIFEST_SCHEMA, manifest.get("schema")]
	if typeof(manifest.get("world")) != TYPE_DICTIONARY:
		return "the manifest has no world block"
	return _read_world(manifest["world"])


func _read_world(world: Dictionary) -> String:
	if not _is_number(world.get("schema")) or world["schema"] != WORLD_SCHEMA:
		return "world schema must be %d, found %s" % [WORLD_SCHEMA, world.get("schema")]
	if typeof(world.get("crs")) != TYPE_DICTIONARY or world["crs"] != CRS:
		return "world crs must be %s, found %s" % [CRS, world.get("crs")]
	var problem := _read_origin(world.get("origin_lv95"), world.get("height_offset_m"))
	if problem.is_empty():
		problem = _read_axes(world.get("axes"))
	return problem


func _read_origin(origin: Variant, offset: Variant) -> String:
	if typeof(origin) != TYPE_DICTIONARY:
		return "world origin_lv95 must be an object, found %s" % [origin]
	for key in ["e", "n"]:
		if not _is_finite_number(origin.get(key)):
			return "world origin_lv95.%s must be a finite number, found %s" % [key, origin.get(key)]
	if not _is_finite_number(offset):
		return "world height_offset_m must be a finite number, found %s" % [offset]
	origin_e = origin["e"]
	origin_n = origin["n"]
	height_offset = offset
	return ""


## Reads the axis mapping ({"x": "+e", ...}); refuses anything but a proper rotation.
func _read_axes(axes: Variant) -> String:
	if typeof(axes) != TYPE_DICTIONARY or axes.size() != GAME_AXES.size():
		return "world axes must map exactly x, y and z, found %s" % [axes]
	var used := {}
	for axis in GAME_AXES.size():
		var spec: Variant = axes.get(GAME_AXES[axis])
		if (
			typeof(spec) != TYPE_STRING
			or spec.length() != 2
			or spec[0] not in ["+", "-"]
			or spec[1] not in SOURCE_AXES
		):
			return (
				"world axes.%s must be a signed source axis like +e, found %s"
				% [GAME_AXES[axis], spec]
			)
		_sign[axis] = 1.0 if spec[0] == "+" else -1.0
		_source_index[axis] = SOURCE_AXES.find(spec[1])
		used[spec[1]] = true
	if used.size() != SOURCE_AXES.size():
		return "world axes must use each of e, n and h exactly once, found %s" % [axes]
	if _determinant() != 1.0:
		return "world axes mirror the world (not a rotation): %s" % [axes]
	return ""


## Determinant of the signed permutation matrix: +1 for a rotation, -1 for a mirror.
func _determinant() -> float:
	var m := []
	for axis in GAME_AXES.size():
		var row := [0.0, 0.0, 0.0]
		row[_source_index[axis]] = _sign[axis]
		m.append(row)
	return (
		m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
		- m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
		+ m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0])
	)


static func _is_number(value: Variant) -> bool:
	return typeof(value) == TYPE_FLOAT or typeof(value) == TYPE_INT


static func _is_finite_number(value: Variant) -> bool:
	return _is_number(value) and is_finite(float(value))
