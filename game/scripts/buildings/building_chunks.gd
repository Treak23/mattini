class_name BuildingChunks
extends RefCounted
## The manifest's buildings block and its chunk files, checked (docs/SPEC.md §8, the
## buildings; CLAUDE.md Hard Rules 2 and 4).
##
## Each chunk file holds the chunk's vertices, then its triangles, no header: every vertex
## as local x, y, z little-endian float32, every triangle as three little-endian uint32
## indices into the chunk's vertices, counter-clockwise seen from outside. The positions
## are local coordinates the pipeline computed for the world config that the block's
## world_sha256 pins; this reader never converts a coordinate. It ties the block to its
## manifest instead: the block's world_sha256 must be the manifest's, and the WorldConfig
## given must be read from the same manifest (Hard Rule 4). Every problem is refused with
## one push_error naming the manifest and a null result, never a plausible set of
## buildings.

const FORMAT := "mesh-f32-u32-le"
const BUILDINGS_COMMAND := "python -m mattini buildings"
const DOWNLOAD_COMMAND := "python -m mattini download buildings"
## Bytes per vertex (three float32) and per triangle (three uint32).
const VERTEX_BYTES := 12
const TRIANGLE_BYTES := 12
## The most vertices or triangles a chunk may hold: every index must fit an int32.
const MAX_COUNT := 2147483647
const CHUNK_KEYS := ["buildings", "file", "sha256", "tile", "triangles", "vertices"]

var area: String
var dataset: String
var edition: String
var attribution: String
## One Dictionary per chunk, in the block's order: {"tile": String, "buildings": int,
## "positions": PackedVector3Array, "indices": PackedInt32Array}.
var chunks: Array = []


## Reads the buildings block of the manifest at [param path] and its chunk files, checked
## against [param world], which must be read from the same manifest. Returns null and calls
## push_error naming the path on every problem.
static func from_manifest(path: String, world: WorldConfig) -> BuildingChunks:
	var result := BuildingChunks.new()
	var problem := result._read(path, world)
	if not problem.is_empty():
		push_error("BuildingChunks: %s: %s" % [path, problem])
		return null
	return result


## Reads and checks everything and fills this object; returns what is wrong, or "".
func _read(path: String, world: WorldConfig) -> String:
	if world == null:
		return "no WorldConfig was given (read it with WorldConfig.from_manifest first)"
	# The manifest and the path rule are read as TerrainGrid reads them: one home for each.
	var manifest: Variant = TerrainGrid._load_manifest(path)
	if typeof(manifest) == TYPE_STRING:
		return manifest
	var problem := _check_built(manifest)
	if problem.is_empty():
		problem = _check_world(world, manifest.get("world"))
	if problem.is_empty():
		problem = _read_block(manifest["buildings"])
	if problem.is_empty():
		problem = _read_chunks(path.get_base_dir(), manifest["buildings"]["chunks"])
	return problem


## Buildings were built, and for this manifest's world config.
static func _check_built(manifest: Dictionary) -> String:
	var block: Variant = manifest.get("buildings")
	if block == null:
		return (
			"no buildings have been built: run %s, then %s" % [DOWNLOAD_COMMAND, BUILDINGS_COMMAND]
		)
	if typeof(block) != TYPE_DICTIONARY:
		return "buildings must be an object or null, found %s" % [block]
	if (
		typeof(block.get("world_sha256")) != TYPE_STRING
		or block["world_sha256"] != manifest.get("world_sha256")
	):
		return (
			(
				"the buildings were built for another world config (buildings.world_sha256 %s,"
				% [block.get("world_sha256")]
			)
			+ " the manifest's %s): run %s" % [manifest.get("world_sha256"), BUILDINGS_COMMAND]
		)
	return ""


## The WorldConfig given must be this manifest's own: the positions are local for the world
## that the manifest's world block describes.
static func _check_world(world: WorldConfig, block: Variant) -> String:
	if typeof(block) != TYPE_DICTIONARY or typeof(block.get("origin_lv95")) != TYPE_DICTIONARY:
		return "the manifest has no world block with an origin"
	var origin: Dictionary = block["origin_lv95"]
	if (
		origin.get("e") != world.origin_e
		or origin.get("n") != world.origin_n
		or block.get("height_offset_m") != world.height_offset
	):
		return "the WorldConfig given was not read from this manifest (its origin differs)"
	return ""


## Checks the block's own fields and fills area, dataset, edition and attribution.
func _read_block(block: Dictionary) -> String:
	if block.get("format") != FORMAT:
		return "buildings.format must be %s, found %s" % [FORMAT, block.get("format")]
	if not _is_text(block.get("area")):
		return "buildings.area must be a name, found %s" % [block.get("area")]
	var source: Variant = block.get("source")
	if typeof(source) != TYPE_DICTIONARY:
		return "buildings.source must be an object, found %s" % [source]
	for key in ["attribution", "dataset", "edition"]:
		if not _is_text(source.get(key)):
			return "buildings.source.%s must be text, found %s" % [key, source.get(key)]
	var entries: Variant = block.get("chunks")
	if typeof(entries) != TYPE_ARRAY or entries.is_empty():
		return "buildings.chunks must be a list of chunks, found %s" % [entries]
	area = block["area"]
	dataset = source["dataset"]
	edition = source["edition"]
	attribution = source["attribution"]
	return ""


## Checks every chunk entry, then reads its file; fills chunks in the block's order.
func _read_chunks(folder: String, entries: Array) -> String:
	var tiles := {}
	for i in entries.size():
		var problem := _check_entry(entries[i], i)
		if not problem.is_empty():
			return problem
		var tile: String = entries[i]["tile"]
		if tiles.has(tile):
			return "buildings.chunks[%d]: the tile %s has a chunk already" % [i, tile]
		tiles[tile] = true
	for entry: Dictionary in entries:
		var problem := _read_chunk(folder, entry)
		if not problem.is_empty():
			return problem
	return ""


## An entry is exactly {buildings, file, sha256, tile, triangles, vertices}: whole counts of
## at least 1, a tile id "<e_km>-<n_km>", 64 hex digits and a plain relative path.
static func _check_entry(entry: Variant, i: int) -> String:
	var where := "buildings.chunks[%d]" % i
	if typeof(entry) != TYPE_DICTIONARY:
		return "%s must be an object, found %s" % [where, entry]
	var keys: Array = entry.keys()
	keys.sort()
	if keys != CHUNK_KEYS:
		return "%s must have exactly the keys %s, found %s" % [where, CHUNK_KEYS, keys]
	var tile: Variant = entry["tile"]
	if not _is_tile(tile):
		return "%s.tile must be a tile id like 2600-1200, found %s" % [where, tile]
	where = "chunk %s" % tile
	for key in ["buildings", "vertices", "triangles"]:
		if not _is_count(entry[key]):
			return (
				"%s: %s must be a whole number from 1 to %d, found %s"
				% [where, key, MAX_COUNT, entry[key]]
			)
	if not TerrainGrid._is_plain_relative_path(entry["file"]):
		return (
			"%s: file must be a plain relative path inside the manifest's folder, found %s"
			% [where, entry["file"]]
		)
	var sha256: Variant = entry["sha256"]
	if typeof(sha256) != TYPE_STRING or sha256.length() != 64 or not sha256.is_valid_hex_number():
		return "%s: sha256 must be 64 hex digits, found %s" % [where, sha256]
	return ""


## Checks the chunk file's size and SHA-256, reads it and checks every index.
func _read_chunk(folder: String, entry: Dictionary) -> String:
	var tile: String = entry["tile"]
	var vertices := int(entry["vertices"])
	var triangles := int(entry["triangles"])
	var chunk_path := folder.path_join(entry["file"])
	var rebuild := "; %s rebuilds it" % BUILDINGS_COMMAND
	if not FileAccess.file_exists(chunk_path):
		return "chunk %s: the file %s is missing%s" % [tile, chunk_path, rebuild]
	var expected_size := VERTEX_BYTES * vertices + TRIANGLE_BYTES * triangles
	var data := FileAccess.get_file_as_bytes(chunk_path)
	if data.size() != expected_size:
		return (
			"chunk %s: the file %s holds %d bytes, not %d (%d vertices, %d triangles)%s"
			% [tile, chunk_path, data.size(), expected_size, vertices, triangles, rebuild]
		)
	var found := FileAccess.get_sha256(chunk_path)
	if found != entry["sha256"].to_lower():
		return (
			"chunk %s: the file %s has SHA-256 %s, not the block's %s%s"
			% [tile, chunk_path, found, entry["sha256"], rebuild]
		)
	# Little-endian: every platform mattini builds for (x86_64) is. The uint32 indices are
	# read as int32; one of 2^31 or more reads negative, and the check below refuses it.
	var split := VERTEX_BYTES * vertices
	var positions := data.slice(0, split).to_vector3_array()
	var indices := data.slice(split).to_int32_array()
	var problem := _check_indices(indices, vertices)
	if not problem.is_empty():
		return "chunk %s: %s%s" % [tile, problem, rebuild]
	var chunk := {
		"tile": tile,
		"buildings": int(entry["buildings"]),
		"positions": positions,
		"indices": indices,
	}
	chunks.append(chunk)
	return ""


## Every index must name one of the chunk's [param vertices]; returns the first that does
## not, or "". The smallest and the largest are found on a sorted copy (native, not a loop
## in script over every index).
static func _check_indices(indices: PackedInt32Array, vertices: int) -> String:
	var sorted := indices.duplicate()
	sorted.sort()
	var bad: int
	if sorted[0] < 0:
		bad = sorted[0]
	elif sorted[sorted.size() - 1] >= vertices:
		bad = sorted[sorted.size() - 1]
	else:
		return ""
	var at := indices.find(bad)
	# A negative int32 is a uint32 of 2^31 or more.
	var value := bad if bad >= 0 else bad + (1 << 32)
	return (
		"triangle %d has the index %d, but the chunk has %d vertices (0 to %d)"
		% [at / 3, value, vertices, vertices - 1]
	)


static func _is_text(value: Variant) -> bool:
	return typeof(value) == TYPE_STRING and not value.is_empty()


## A tile id: two whole numbers of kilometres joined by "-", as the pipeline names chunks.
static func _is_tile(value: Variant) -> bool:
	if typeof(value) != TYPE_STRING:
		return false
	var parts: PackedStringArray = value.split("-")
	return parts.size() == 2 and parts[0].is_valid_int() and parts[1].is_valid_int()


## Godot's JSON reads every number as a float: a whole float from 1 to MAX_COUNT is a count.
static func _is_count(value: Variant) -> bool:
	if typeof(value) != TYPE_FLOAT and typeof(value) != TYPE_INT:
		return false
	return float(value) == floorf(value) and value >= 1 and value <= MAX_COUNT
