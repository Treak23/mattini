extends GutTest
## Pinning tests for brief M3-14: the main scene hands every block to its loader, prints one
## startup line per block and credits every dataset, texture and placeholder.
##
## Pinned decisions (m3-design.md §8, §9; docs/SPEC.md §10, M3's game): after WorldConfig,
## TerrainGrid and BuildingChunks the main scene reads PhotoGrid, SurfaceGrid, TreeChunks and
## BuildingRoofs, then builds TerrainLoader.create(grid, self, photo, surfaces) ("Terrain"),
## TreeLoader.create(trees, self, photo.texture, photo.rect()) ("Trees") and
## BuildingLoader.create(chunks, self, roofs) ("Buildings"). So the terrain's photo shader
## holds the PhotoGrid's texture and rectangle and the SurfaceGrid's texture and rectangle,
## the trees' material holds the very same texture (decoded once: the village photo is about
## 600 MiB of texture) and the photo's rectangle, and the box's roof triangles carry the
## roofs block's colour. The complete test world (complete_world.gd) places the photo at
## (1017, 11.5, 16, 8) and the surfaces at (1013, 9, 40, 30), computed by design from their
## LV95 boxes, where the terrain grid spans (1015, 10.5, 20, 11.5): no rectangle stands in
## for another.
## The startup lines, exactly and in this order, one per block, after DataPacks' pack lines
## in an exported build (tools/export.sh step 6 requires them):
##   mattini <version>: terrain <area> loaded, <columns> x <rows> vertices at <spacing> m
##   mattini <version>: buildings <area> loaded, <n> buildings in <k> chunks, <t> triangles
##   mattini <version>: photo <area> loaded, <columns> x <rows> texels at <cell> m
##   mattini <version>: surfaces <area> loaded, <columns> x <rows> cells at <cell> m
##   mattini <version>: trees <area> loaded, <n> trees in <k> chunks
##   mattini <version>: roofs <area> loaded, <n> of <m> buildings coloured
## (numbers as main.gd writes them: at most two decimals, no trailing zeros). The credits:
## under "Data" one line per dataset loaded, "<dataset> <edition>, <attribution>", each once
## (the photo and the roofs share swissimage 2023), in name order; then "Textures" and
## game/textures/LICENSE.txt whole (every CC0 texture with its name, author, asset page and
## licence, brief M3-10); then "Placeholders": BuildingLoader's WALLS_NOTE (brief M3-12),
## TreeLoader's TREES_NOTE (brief M3-11) and the streams' assumed width, main.gd's
## STREAMS_NOTE; then the software licences as before. The three constants are read at run
## time, so a missing one fails this test by name, not by a parse error.
##
## Since brief v0.4.0-08 (M4-10 decision 8's Sky credits, cut to the sky, with the stars on the
## Hipparcos Catalogue, SPEC §13 row 51; one test and this paragraph change): after
## "Placeholders" a heading "Sky" names the sources of the sun's and the moon's formulas (NOAA's
## solar calculations; Paul Schlyter's planetary positions: main.gd's SUN_NOTE and MOON_NOTE) and,
## only when the star table res://sky/stars.csv is there (brief v0.4.0-06), the catalogue's credit,
## main.gd's STARS_NOTE: the table's first line without its "# " (ESA's "Credit: ESA" and the
## licence, CC BY-NC 3.0 IGO), so the stars are never drawn without their credit. The switch is
## an argument, _credits_text(datasets, stars), read here both ways whichever the tree holds. The
## sky prints no startup line.
##
## Does NOT prove: that anything renders or looks right (no GPU); what the shaders do with
## the textures; the real village's numbers (tools/export.sh step 6 does, on the exported
## build); that the catalogue's licence allows a sale (SPEC §13 row 51: it does not without ESA's
## permission).

const CompleteWorld := preload("res://tests/complete_world.gd")
const MAIN_SCRIPT := "res://scripts/main.gd"
const BUILDING_LOADER := "res://scripts/buildings/building_loader.gd"
const TREE_LOADER := "res://scripts/trees/tree_loader.gd"
const SCRATCH_DIR := "user://test_main_scene_data"
const DEPRECATION := "instance_reset_physics_interpolation() is deprecated"
const PHOTO_SHADER := "res://shaders/terrain_photo.gdshader"
## Design's rectangles for the complete world (local x0, z0, width, depth).
const PHOTO_RECT := Vector4(1017.0, 11.5, 16.0, 8.0)
const SURFACES_RECT := Vector4(1013.0, 9.0, 40.0, 30.0)
const GRID_EXTENT := Vector4(1015.0, 10.5, 20.0, 11.5)
## The texture credits, by hand from Poly Haven's asset pages (brief M3-10's table).
const TEXTURES := [
	["rock_face_03_diff_2k.jpg", "https://polyhaven.com/a/rock_face_03", "Dario Barresi"],
	["worn_asphalt_diff_1k.jpg", "https://polyhaven.com/a/worn_asphalt", "Amal Kumar"],
	["rocky_trail_diff_1k.jpg", "https://polyhaven.com/a/rocky_trail", "Amal Kumar"],
]
const STREAMS_NOTE := "Streams: drawn 2 m wide, an assumed width: swissTLM3D gives none."
const SKY_NOTES := [
	(
		"Sun: NOAA's solar position calculations (Meeus, Astronomical Algorithms),"
		+ " https://gml.noaa.gov/grad/solcalc/calcdetails.html"
	),
	(
		"Moon: Paul Schlyter, How to compute planetary positions,"
		+ " https://stjarnhimlen.se/comp/ppcomp.html"
	),
]
const STARS_TABLE := "res://sky/stars.csv"
## The star table's first line without its "# " (brief v0.4.0-06 decision 3).
const STARS_NOTE := (
	"Stars derived from the Hipparcos Catalogue (ESA 1997, ESA SP-1200): stars to V 6.0,"
	+ " positions rounded and reformatted. Credit: ESA. CC BY-NC 3.0 IGO,"
	+ " https://creativecommons.org/licenses/by-nc/3.0/igo/"
)


## Collects every line printed while it listens.
class LineCatcher:
	extends Logger

	var _lines := PackedStringArray()
	var _mutex := Mutex.new()

	func _log_message(message: String, error: bool) -> void:
		if error:
			return
		_mutex.lock()
		for line in message.strip_edges(false, true).split("\n"):
			_lines.append(line)
		_mutex.unlock()

	func lines() -> PackedStringArray:
		_mutex.lock()
		var copy := _lines.duplicate()
		_mutex.unlock()
		return copy


var _cases := 0
var _complete := ""


func before_all() -> void:
	_complete = CompleteWorld.write(SCRATCH_DIR.path_join("complete"))


func after_all() -> void:
	CompleteWorld.remove_tree(SCRATCH_DIR)


func _main_with(manifest_path: String) -> Node3D:
	var main: Node3D = load("res://main.tscn").instantiate()
	main.manifest_path = manifest_path
	add_child_autofree(main)
	for error in get_errors():
		if error.contains_text(DEPRECATION):
			error.handled = true
	return main


func _params(terrain: Terrain3D) -> Dictionary:
	var params: Variant = terrain.material.get("_shader_parameters")
	return params if typeof(params) == TYPE_DICTIONARY else {}


## Every ShaderMaterial that draws a tree cell: its material_override, else its mesh's.
func _tree_materials(trees: Node) -> Array[ShaderMaterial]:
	var found: Array[ShaderMaterial] = []
	for child in trees.get_children():
		var instance := child as MultiMeshInstance3D
		if instance == null:
			continue
		var material: Material = instance.material_override
		if material == null and instance.multimesh != null and instance.multimesh.mesh != null:
			material = instance.multimesh.mesh.surface_get_material(0)
		if material is ShaderMaterial:
			found.append(material)
	return found


## Every vertex colour drawn by a surface whose material takes it as albedo, in [param node].
func _albedo_vertex_colours(node: Node) -> Array[Color]:
	var colours: Array[Color] = []
	for child in node.get_children():
		var instance := child as MeshInstance3D
		if instance == null:
			continue
		for s in instance.mesh.get_surface_count():
			var material := instance.get_active_material(s) as StandardMaterial3D
			var arrays := instance.mesh.surface_get_arrays(s)
			if material == null or not material.vertex_color_use_as_albedo:
				continue
			if arrays[Mesh.ARRAY_COLOR] != null:
				for colour: Color in arrays[Mesh.ARRAY_COLOR]:
					colours.append(colour)
	return colours


## The text constant [param name] of the script at [param path], read at run time, so a
## missing one fails this test by name, not by a parse error.
func _constant(path: String, name: String) -> String:
	var value: Variant = (load(path) as GDScript).get_script_constant_map().get(name)
	assert_true(value is String, "%s declares %s" % [path, name])
	return value if value is String else "<no %s in %s>" % [name, path]


func _parse(path: String) -> Dictionary:
	var json := JSON.new()
	assert_eq(json.parse(FileAccess.get_file_as_string(path)), OK, "%s parses" % path)
	return json.data if typeof(json.data) == TYPE_DICTIONARY else {}


func test_every_loader_receives_its_block() -> void:
	var main := _main_with(_complete)
	assert_false(main.get_node("UI/ErrorPanel").visible, "the complete world opens no panel")
	var terrain: Terrain3D = main.get_node_or_null("Terrain")
	var trees: Node3D = main.get_node_or_null("Trees")
	var buildings: Node3D = main.get_node_or_null("Buildings")
	assert_not_null(terrain, "Terrain")
	assert_not_null(trees, "Trees, beside Terrain and Buildings")
	assert_not_null(buildings, "Buildings")
	if terrain == null or trees == null or buildings == null:
		return
	assert_eq(trees.get_parent(), main, "Trees is a child of the main scene")
	var shader: Shader = terrain.material.shader_override
	assert_eq(shader.resource_path if shader != null else "", PHOTO_SHADER, "the photo look")
	var params := _params(terrain)
	var photo: Variant = params.get("photo")
	assert_true(photo is Texture2D, "the terrain holds the photo")
	if photo is Texture2D:
		assert_eq(photo.get_size(), Vector2(80, 40), "the photo's 80 x 40 texels")
	assert_eq(params.get("photo_rect"), PHOTO_RECT, "the photo's rectangle")
	assert_ne(params.get("photo_rect"), GRID_EXTENT, "not the terrain grid's")
	var surfaces: Variant = params.get("surfaces")
	assert_true(surfaces is Texture2D, "the terrain holds the surfaces")
	if surfaces is Texture2D:
		assert_eq(surfaces.get_size(), Vector2(200, 150), "the surfaces' 200 x 150 cells")
	assert_eq(params.get("surfaces_rect"), SURFACES_RECT, "the surfaces' own rectangle")
	var materials := _tree_materials(trees)
	assert_gt(materials.size(), 0, "a ShaderMaterial draws the trees")
	for material in materials:
		assert_same(material.get_shader_parameter("photo"), photo, "the terrain's photo, once")
		assert_eq(material.get_shader_parameter("photo_rect"), PHOTO_RECT, "its rectangle")
	var colours := _albedo_vertex_colours(buildings)
	assert_eq(colours.size(), 6, "the box's two roof triangles carry vertex colours")
	for colour in colours:
		assert_eq(colour, Color.html(CompleteWorld.ROOF), "the roofs block's colour")


func test_the_startup_lines_name_every_block_in_order() -> void:
	var version: String = ProjectSettings.get_setting("application/config/version")
	var manifest := _parse(_complete)
	var trees: Array = manifest["trees"]["chunks"]
	var count := 0
	for chunk: Dictionary in trees:
		count += int(chunk["trees"])
	var expected := [
		"mattini %s: terrain fixture loaded, 41 x 24 vertices at 0.5 m" % version,
		"mattini %s: buildings fixture loaded, 1 buildings in 1 chunks, 12 triangles" % version,
		"mattini %s: photo fixture loaded, 80 x 40 texels at 0.2 m" % version,
		"mattini %s: surfaces fixture loaded, 200 x 150 cells at 0.2 m" % version,
		"mattini %s: trees fixture loaded, %d trees in %d chunks" % [version, count, trees.size()],
		"mattini %s: roofs fixture loaded, 1 of 1 buildings coloured" % version,
	]
	assert_gt(count, trees.size(), "the fixture's tree count differs from its chunk count")
	# The same world with the box's roof uncoloured: "0 of 1".
	_cases += 1
	var uncoloured := func(m: Dictionary) -> void:
		m["roofs"]["chunks"][0]["buildings"][0]["roof"] = null
		m["roofs"]["chunks"][0]["buildings"][0]["roof_pixels"] = 0
	var plain := CompleteWorld.write(SCRATCH_DIR.path_join("case_%d" % _cases), uncoloured)
	var catcher := LineCatcher.new()
	OS.add_logger(catcher)
	_main_with(_complete)
	OS.remove_logger(catcher)
	var complete_lines := catcher.lines()
	catcher = LineCatcher.new()
	OS.add_logger(catcher)
	_main_with(plain)
	OS.remove_logger(catcher)
	var plain_lines := catcher.lines()
	var startup := PackedStringArray()
	for line in complete_lines:
		if line.begins_with("mattini %s: " % version):
			startup.append(line)
	assert_eq(startup, PackedStringArray(expected), "the six lines, exactly, in this order")
	var roofs_line := "mattini %s: roofs fixture loaded, 0 of 1 buildings coloured" % version
	assert_has(plain_lines, roofs_line, "a building without a colour is not counted")


func test_the_credits_name_every_dataset_texture_and_placeholder() -> void:
	var main := _main_with(_complete)
	var credits: String = main.get_node("UI/PauseMenu/Credits").text
	var data := (
		"\n"
		. join(
			[
				"Data",
				"swissalti3d 2024, © swisstopo",
				"swissbuildings3d 2020, © swisstopo",
				"swissimage 2023, © swisstopo",
				"swisssurface3d 2021-2022, © swisstopo",
				"swisstlm3d 2026-02, © swisstopo",
				"",
				"Textures",
				"",
			]
		)
	)
	assert_string_contains(credits, "\n" + data, "the datasets, each once, in name order")
	var licence := FileAccess.get_file_as_string("res://textures/LICENSE.txt").strip_edges()
	assert_string_contains(licence, "CC0 1.0 Universal", "the textures' licence note is there")
	assert_string_contains(credits, "\nTextures\n" + licence + "\n", "the note, whole")
	for texture: Array in TEXTURES:
		var at := credits.find("\nTextures\n")
		for part: String in texture:
			assert_gt(credits.find(part, at), at, "Textures: %s" % part)
	var walls := _constant(BUILDING_LOADER, "WALLS_NOTE")
	var trees := _constant(TREE_LOADER, "TREES_NOTE")
	var notes := "\n".join(["Placeholders", walls, trees, STREAMS_NOTE, ""])
	assert_string_contains(credits, "\n\n" + notes, "the three placeholder notes")
	assert_eq(_constant(MAIN_SCRIPT, "STREAMS_NOTE"), STREAMS_NOTE, "the streams' note, as written")
	assert_string_contains(walls, "placeholder", "the walls' note says so")
	assert_string_contains(trees, "species", "the trees' note says what is not")
	assert_lt(credits.find("\nPlaceholders\n"), credits.find("\nGodot Engine\n"), "before Godot")


func test_the_credits_name_the_sky_s_sources_and_the_stars_only_with_their_table() -> void:
	var main := _main_with(_complete)
	var credits: String = main.get_node("UI/PauseMenu/Credits").text
	var sky := "\n".join(["", "", "Sky"] + SKY_NOTES)
	assert_string_contains(credits, sky, "the sun's and the moon's sources")
	assert_lt(credits.find("\nPlaceholders\n"), credits.find("\nSky\n"), "after the placeholders")
	assert_lt(credits.find("\nSky\n"), credits.find("\nGodot Engine\n"), "before Godot")
	assert_eq(_constant(MAIN_SCRIPT, "STARS_NOTE"), STARS_NOTE, "the stars' credit, as written")
	if FileAccess.file_exists(STARS_TABLE):
		var first := FileAccess.get_file_as_string(STARS_TABLE).get_slice("\n", 0)
		assert_eq(first, "# " + STARS_NOTE, "the credit is the table's own first line")
		assert_string_contains(credits, sky + "\n" + STARS_NOTE + "\n", "the catalogue, credited")
	else:
		assert_false(credits.contains("Hipparcos"), "no stars, no catalogue")
	# The switch itself, both ways, whichever this tree holds (main's
	# _credits_text(datasets, stars)).
	var none: String = main._credits_text(PackedStringArray(), false)
	assert_false(none.contains("Hipparcos"), "without the stars no credit")
	assert_string_contains(none, sky + "\n\n", "and the sky's two sources still")
	var some: String = main._credits_text(PackedStringArray(), true)
	assert_string_contains(some, sky + "\n" + STARS_NOTE + "\n", "with them, the credit")
