extends GutTest
## Pinning tests for brief M3-R1-fix-5 (M3 review R1 G-03): a manifest field of the wrong type
## is refused by the reader that checks it, as a wrong value is, and never accepted behind a
## runtime error.
##
## Pinned decisions: in GDScript `!=` between a float read from JSON and a String, an Array or a
## Dictionary constant is a runtime error ("Invalid operands … in operator '!='"), and the guard
## that held the comparison did not refuse: the review's fuzz run found 21 manifests accepted
## that way, among them the top-level world_sha256 set to a number, which all six readers
## (TerrainGrid, BuildingChunks, PhotoGrid, SurfaceGrid, TreeChunks, BuildingRoofs) accepted.
## Every comparison of a manifest value with a constant now goes through ManifestValue.differs.
## Each case is the complete test world (complete_world.gd) with one field changed to a value
## of another type, or to another value of the right type, read by the reader that checks it: a
## null result and exactly one error, a push_error naming the manifest and saying which check
## refused it. An error of any other kind, a SCRIPT ERROR among them, fails the case. The wrong
## values of the format, the dataset, the class table and the chunk tile are pinned here too,
## each with its needle: those guards were among G-04's survivors (removed, every test stayed
## green).
##
## Brief v0.5.0-11 (0.4.0's whole-range review S-03) adds SkySite (res://scripts/sky/sky_site.gd),
## the reader of the sky block, to every census here: it is the seventh reader, its block is
## "sky", and it refuses a world_sha256 of the wrong type at the top level or in its block, and an
## origin or a height offset of the wrong type, as the six do. Its words for another world config
## are its own ("the sun's place was written for another world config", not "built"), so each
## reader's needle is read from OTHER_WORLD_WORDS; sky_site.gd's words do not change. Its own
## fields of the wrong type or value (area, latitude_deg, longitude_deg, true_to_grid_deg) are
## refused with its own words, each a case here.
##
## Does NOT prove: that no other manifest field of a wrong type is mishandled (a field no reader
## reads), nor that the readers' other checks are right.

const CompleteWorld := preload("res://tests/complete_world.gd")
const SCRATCH_DIR := "user://test_m3_r1_fix5_type_guards"
const READERS := [
	"TerrainGrid",
	"BuildingChunks",
	"PhotoGrid",
	"SurfaceGrid",
	"TreeChunks",
	"BuildingRoofs",
	"SkySite",
]
## The block of the manifest each reader checks.
const BLOCKS := {
	"TerrainGrid": "terrain",
	"BuildingChunks": "buildings",
	"PhotoGrid": "photo",
	"SurfaceGrid": "surfaces",
	"TreeChunks": "trees",
	"BuildingRoofs": "roofs",
	"SkySite": "sky",
}
const OTHER_WORLD := "built for another world config"
## Each reader's words for a block of another world config, where they are not OTHER_WORLD.
const OTHER_WORLD_WORDS := {"SkySite": "the sun's place was written for another world config"}
## SkySite's three numbers and the largest size of each, in degrees.
const SKY_LIMITS := {"latitude_deg": 90.0, "longitude_deg": 180.0, "true_to_grid_deg": 10.0}
const NOT_OURS := "the WorldConfig given was not read from this manifest"
const TREE_DATASETS := ["swissalti3d", "swissbuildings3d", "swisssurface3d", "swisstlm3d"]

var _cases := 0
var _buildings: BuildingChunks


func after_all() -> void:
	CompleteWorld.remove_tree(SCRATCH_DIR)


## The complete test world with [param change] applied to its manifest; returns its path.
func _world(change := Callable()) -> String:
	_cases += 1
	return CompleteWorld.write(SCRATCH_DIR.path_join("case_%d" % _cases), change)


## A change that sets the field at [param keys] (from the manifest's top level; a key is a
## String for an object, an int for a list) to a copy of [param value].
func _with_field(keys: Array, value: Variant) -> Callable:
	return func(manifest: Dictionary) -> void:
		var at: Variant = manifest
		for i in keys.size() - 1:
			at = at[keys[i]]
		var copy: Variant = value
		if value is Array or value is Dictionary:
			copy = value.duplicate(true)
		at[keys[keys.size() - 1]] = copy


## The buildings of an unchanged complete world: what BuildingRoofs is given.
func _good_buildings() -> BuildingChunks:
	if _buildings == null:
		var path := _world()
		_buildings = BuildingChunks.from_manifest(path, WorldConfig.from_manifest(path))
		assert_not_null(_buildings, "the unchanged world's buildings are read")
	return _buildings


## [param reader] reads the manifest at [param path], placed through the WorldConfig of the
## manifest at [param world_from] (default: the same one).
func _read(reader: String, path: String, world_from := "") -> RefCounted:
	var world := WorldConfig.from_manifest(path if world_from.is_empty() else world_from)
	assert_not_null(world, "%s: the WorldConfig is read" % reader)
	if world == null:
		return null
	var result: RefCounted = null
	match reader:
		"TerrainGrid":
			result = TerrainGrid.from_manifest(path, world)
		"BuildingChunks":
			result = BuildingChunks.from_manifest(path, world)
		"PhotoGrid":
			result = PhotoGrid.from_manifest(path, world)
		"SurfaceGrid":
			result = SurfaceGrid.from_manifest(path, world)
		"TreeChunks":
			result = TreeChunks.from_manifest(path, world)
		"BuildingRoofs":
			result = BuildingRoofs.from_manifest(path, world, _good_buildings())
		"SkySite":
			result = SkySite.from_manifest(path, world)
		_:
			assert_true(false, "%s is not a reader" % reader)
	return result


## The read was refused: a null result, and exactly one error, a push_error naming [param path]
## and saying [param needle]. Every error of this case is handled, so the next case starts clean.
func _assert_refused_once(result: RefCounted, path: String, why: String, needle: String) -> void:
	assert_null(result, "%s: a null result" % why)
	var pushed := 0
	var others := []
	for error in get_errors():
		if error.handled:
			continue
		if error.is_push_error() and error.contains_text(path) and error.contains_text(needle):
			pushed += 1
		else:
			others.append("%s %s" % [error.code, error.rationale])
		error.handled = true
	assert_eq(pushed, 1, "%s: one push_error names %s and says '%s'" % [why, path, needle])
	assert_eq(others, [], "%s: no other error, no SCRIPT ERROR" % why)


## [param reader]'s words for a block of another world config.
func _other_world(reader: String) -> String:
	return OTHER_WORLD_WORDS.get(reader, OTHER_WORLD)


func _name(keys: Array) -> String:
	return "/".join(PackedStringArray(keys.map(func(key: Variant) -> String: return str(key))))


## For every value: the complete world with the field at [param keys] set to it, read by
## [param reader], is refused with [param needle].
func _refuse_each(reader: String, keys: Array, values: Array, needle: String) -> void:
	for value: Variant in values:
		var path := _world(_with_field(keys, value))
		var why := "%s, %s = %s" % [reader, _name(keys), JSON.stringify(value)]
		_assert_refused_once(_read(reader, path), path, why, needle)


func test_the_unchanged_world_is_read_by_every_reader() -> void:
	# The control: no case below is refused for any reason but its change.
	var path := _world()
	for reader: String in READERS:
		assert_not_null(_read(reader, path), "%s reads the unchanged world" % reader)
	assert_eq(get_errors().size(), 0, "and prints nothing")


func test_a_world_sha256_of_the_wrong_type_is_refused_by_every_reader() -> void:
	# The manifest's own hash, the one every block's is compared with: a number was accepted
	# by all six readers (G-03), with six SCRIPT ERROR lines. SkySite, the seventh, since
	# brief v0.5.0-11.
	for value: Variant in [5.0, true, [], {}, null]:
		var path := _world(_with_field(["world_sha256"], value))
		for reader: String in READERS:
			var why := "%s, world_sha256 = %s" % [reader, JSON.stringify(value)]
			_assert_refused_once(_read(reader, path), path, why, _other_world(reader))


func test_a_block_world_sha256_of_the_wrong_type_is_refused_by_every_reader() -> void:
	for reader: String in READERS:
		var keys := [BLOCKS[reader], "world_sha256"]
		_refuse_each(reader, keys, [5.0, true, [], {}, null], _other_world(reader))


func test_a_format_of_the_wrong_type_or_value_is_refused() -> void:
	# A wrong value too: a photo block that says "png" reached the credits (G-04).
	var values := [5.0, true, [], {}, null, "png"]
	_refuse_each("TerrainGrid", ["terrain", "format"], values, "terrain.format must be")
	_refuse_each("BuildingChunks", ["buildings", "format"], values, "buildings.format must be")
	_refuse_each("PhotoGrid", ["photo", "format"], values, "photo.format must be")
	_refuse_each("SurfaceGrid", ["surfaces", "format"], values, "surfaces.format must be")
	_refuse_each("TreeChunks", ["trees", "format"], values, "trees.format must be")
	_refuse_each("BuildingRoofs", ["roofs", "format"], values, "roofs.format must be")


func test_a_dataset_of_the_wrong_type_or_value_is_refused() -> void:
	var values := [5.0, true, [], {}, null, "swissalti3d"]
	_refuse_each(
		"PhotoGrid", ["photo", "source", "dataset"], values, "photo.source.dataset must be"
	)
	_refuse_each(
		"SurfaceGrid", ["surfaces", "source", "dataset"], values, "surfaces.source.dataset must be"
	)
	for name: String in TREE_DATASETS:
		var needle := "trees.source.%s must be the %s block" % [name, name]
		# Another dataset's name is a wrong value for each of the four.
		var others := values.duplicate()
		others[others.size() - 1] = "swisstlm3d" if name != "swisstlm3d" else "swissalti3d"
		_refuse_each("TreeChunks", ["trees", "source", name, "dataset"], others, needle)


func test_a_class_table_of_the_wrong_type_or_value_is_refused() -> void:
	var table := {"0": "none", "1": "rock", "2": "water", "3": "path", "4": "road"}
	var values: Array = [[], 5.0, true, null, "classes", {}, {"0": "none"}]
	var renamed := table.duplicate()
	renamed["4"] = 4.0
	values.append(renamed)
	var extra := table.duplicate()
	extra["5"] = "ice"
	values.append(extra)
	_refuse_each("SurfaceGrid", ["surfaces", "classes"], values, "surfaces.classes must be")


func test_roofs_of_the_wrong_area_tile_or_buildings_source_are_refused() -> void:
	var wrong := [5.0, true, [], {}, null]
	_refuse_each("BuildingRoofs", ["roofs", "area"], wrong + ["elsewhere"], "roofs.area")
	# A tile of the right shape that is not the buildings' chunk: with its check removed,
	# nothing else notices, the colours would be laid on another chunk.
	_refuse_each(
		"BuildingRoofs",
		["roofs", "chunks", 0, "tile"],
		wrong + ["2999-1199"],
		"the buildings' chunk 0 is %s" % CompleteWorld.TILE
	)
	var other_source := {"attribution": "© elsewhere"}
	_refuse_each(
		"BuildingRoofs",
		["roofs", "source", "buildings"],
		wrong + ["swissbuildings3d", other_source],
		"roofs.source.buildings is not the manifest's buildings.source"
	)


func test_a_sky_field_of_the_wrong_type_or_value_is_refused() -> void:
	# Brief v0.5.0-11: SkySite's own fields, each refused with its own words. A wrong value too:
	# an area the world config does not hold, a number beyond its limit.
	var wrong := [5.0, true, [], {}, null]
	_refuse_each("SkySite", ["sky", "area"], wrong + ["elsewhere"], "sky.area")
	for key: String in SKY_LIMITS:
		var values: Array = ["x", true, [], {}, null, SKY_LIMITS[key] + 0.5]
		var needle := "sky.%s must be a finite number" % key
		_refuse_each("SkySite", ["sky", key], values, needle)


func test_an_origin_or_height_offset_of_the_wrong_type_is_refused_by_every_reader() -> void:
	# The world guard compares the manifest's world block with the WorldConfig given. The
	# given one is read from an unchanged world, as one read from another manifest is.
	var given := _world()
	var fields := [["origin_lv95", "e"], ["origin_lv95", "n"], ["height_offset_m"]]
	for field: Array in fields:
		for value: Variant in ["x", true, [], {}]:
			var path := _world(_with_field(["world"] + field, value))
			for reader: String in READERS:
				var why := "%s, world/%s = %s" % [reader, _name(field), JSON.stringify(value)]
				_assert_refused_once(_read(reader, path, given), path, why, NOT_OURS)
