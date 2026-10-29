class_name SkySite
extends RefCounted
## The manifest's sky block, checked: the place the sun and the moon are computed for (brief
## v0.4.0-08, from M4-10 decision 1; docs/SPEC.md; CLAUDE.md Hard Rules 2 and 4).
##
## Reads the manifest at the path given (TerrainGrid._load_manifest) and its sky block, no file of
## its own. Refuses, in this order, with one push_error naming the manifest and a null result:
## no WorldConfig; a manifest that cannot be read; a block not written (null); a block that is not
## an object; a world_sha256 that is not text or not the manifest's (a block without one is
## "another world config"); a WorldConfig not read from this manifest (BuildingChunks._check_world:
## any axes are accepted, the directions go through the world config); a key set other than
## exactly area, latitude_deg, longitude_deg, true_to_grid_deg and world_sha256; an area that is
## not one of the world config's areas; a latitude, longitude or convergence that is not a finite
## number or lies beyond 90, 180 and 10 degrees. Every compare is typed (brain.md H26). Every
## refusal but the world's (no WorldConfig, an unreadable manifest, a WorldConfig of another
## manifest) names the command that writes the block.

const SKY_COMMAND := "python -m mattini sky"
const KEYS := ["area", "latitude_deg", "longitude_deg", "true_to_grid_deg", "world_sha256"]
## The largest size of each number, in degrees.
const LIMITS := {"latitude_deg": 90.0, "longitude_deg": 180.0, "true_to_grid_deg": 10.0}

var area: String
var latitude_deg: float
var longitude_deg: float
## True north lies at this grid azimuth: the meridian convergence, negative where true north is
## west of grid north.
var true_to_grid_deg: float


## Reads the sky block of the manifest at [param path], checked against [param world], which must
## be read from the same manifest. Returns null and calls push_error naming the path on every
## problem.
static func from_manifest(path: String, world: WorldConfig) -> SkySite:
	var result := SkySite.new()
	var problem := result._read(path, world)
	if not problem.is_empty():
		push_error("SkySite: %s: %s" % [path, problem])
		return null
	return result


## Reads and checks everything and fills this object; returns what is wrong, or "".
func _read(path: String, world: WorldConfig) -> String:
	if world == null:
		return "no WorldConfig was given"
	var manifest: Variant = TerrainGrid._load_manifest(path)
	if typeof(manifest) == TYPE_STRING:
		return manifest
	var problem := _check_written(manifest)
	if problem.is_empty():
		problem = BuildingChunks._check_world(world, path, manifest.get("world"))
	if not problem.is_empty():
		return problem
	var areas: Variant = manifest["world"].get("areas")
	problem = _check_block(manifest["sky"], areas if typeof(areas) == TYPE_DICTIONARY else {})
	if problem.is_empty():
		var block: Dictionary = manifest["sky"]
		area = block["area"]
		latitude_deg = block["latitude_deg"]
		longitude_deg = block["longitude_deg"]
		true_to_grid_deg = block["true_to_grid_deg"]
	return problem


## The block was written, is an object and is for this manifest's world config.
static func _check_written(manifest: Dictionary) -> String:
	var block: Variant = manifest.get("sky")
	if block == null:
		return "the sun's place has not been written: run %s" % SKY_COMMAND
	if typeof(block) != TYPE_DICTIONARY:
		return "sky must be an object or null, found %s: run %s" % [block, SKY_COMMAND]
	if (
		typeof(block.get("world_sha256")) != TYPE_STRING
		or ManifestValue.differs(block["world_sha256"], manifest.get("world_sha256"))
	):
		return (
			(
				"the sun's place was written for another world config (sky.world_sha256 %s,"
				% [block.get("world_sha256")]
			)
			+ " the manifest's %s): run %s" % [manifest.get("world_sha256"), SKY_COMMAND]
		)
	return ""


## The block's key set, its area (one of [param areas]) and its three numbers.
static func _check_block(block: Dictionary, areas: Dictionary) -> String:
	var keys := block.keys()
	keys.sort()
	if keys != KEYS:
		return "sky must hold exactly %s, found %s: run %s" % [KEYS, keys, SKY_COMMAND]
	if typeof(block["area"]) != TYPE_STRING or not areas.has(block["area"]):
		return (
			"sky.area %s is not an area of the world config: run %s" % [block["area"], SKY_COMMAND]
		)
	for key: String in LIMITS:
		var value: Variant = block[key]
		var number := typeof(value) == TYPE_FLOAT or typeof(value) == TYPE_INT
		if not number or not is_finite(value) or absf(value) > LIMITS[key]:
			return (
				"sky.%s must be a finite number of at most %s degrees, found %s: run %s"
				% [key, LIMITS[key], value, SKY_COMMAND]
			)
	return ""
