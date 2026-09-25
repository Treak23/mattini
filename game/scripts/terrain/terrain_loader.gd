class_name TerrainLoader
extends RefCounted
## Builds the Terrain3D terrain from a TerrainGrid, every height on its own vertex
## (docs/SPEC.md §8, the terrain grid; brain.md H11 for each measured trap it steps around).
##
## Terrain3D's vertices sit at whole multiples of its vertex spacing, in regions 1024 m wide
## here. import_images puts an image's first pixel at the corner of the region that holds
## the position it is given, so the loader builds images that cover whole regions from a
## region corner, with the grid blitted at its own vertex offset and every other vertex a
## hole. Heights outside the grid are 0.0, never NaN (Terrain3D turns NaN into 0 m, not a
## hole); the control map's hole bit is what hides them. Nothing is drawn outside the
## regions (world background none) and there is no collision in M1.

const TERRAIN_NAME := "Terrain"
const REGION_WIDTH_M := 1024.0
const CLAY_SHADER := "res://shaders/terrain_clay.gdshader"


## Adds a Terrain3D node named "Terrain" to [param parent] (in the tree, with a camera in
## its viewport) and returns it with the grid's heights loaded. The parent must be in the
## tree: Terrain3D builds its material and data only on entering it.
static func create(grid: TerrainGrid, parent: Node) -> Terrain3D:
	var terrain := Terrain3D.new()
	terrain.name = TERRAIN_NAME
	# Before entering the tree: made in code, it prints ERROR lines on entering unless
	# free_editor_textures is off; vertex_spacing is honoured here (region_size and
	# collision_mode are not, so they come after).
	terrain.free_editor_textures = false
	terrain.vertex_spacing = grid.spacing_m
	parent.add_child(terrain)
	terrain.collision_mode = Terrain3DCollision.DISABLED
	var region_vertices := int(REGION_WIDTH_M / grid.spacing_m)
	terrain.change_region_size(region_vertices)
	# The material exists only once the node is in the tree.
	var material := terrain.material
	material.world_background = Terrain3DMaterial.NONE
	material.show_checkered = false
	material.shader_override = load(CLAY_SHADER)
	material.shader_override_enabled = true
	material.set_shader_param("height_offset_m", grid.height_offset_m)
	_import(terrain, grid, region_vertices)
	return terrain


## Imports the grid as one height image and one control image covering every region the
## grid touches, placed at the north-west region corner.
static func _import(terrain: Terrain3D, grid: TerrainGrid, region_vertices: int) -> void:
	var s := grid.spacing_m
	var x_max := grid.x_min + (grid.columns - 1) * s
	var z_max := grid.z_min + (grid.rows - 1) * s
	var first := Vector2i(floori(grid.x_min / REGION_WIDTH_M), floori(grid.z_min / REGION_WIDTH_M))
	var last := Vector2i(floori(x_max / REGION_WIDTH_M), floori(z_max / REGION_WIDTH_M))
	var size := (last - first + Vector2i.ONE) * region_vertices
	var corner := Vector3(first.x * REGION_WIDTH_M, 0.0, first.y * REGION_WIDTH_M)
	# The grid's first vertex, in vertices from the corner: whole, as TerrainGrid checked.
	var offset := Vector2i(roundi((grid.x_min - corner.x) / s), roundi((grid.z_min - corner.z) / s))

	var grid_image := Image.create_from_data(
		grid.columns, grid.rows, false, Image.FORMAT_RF, grid.heights.to_byte_array()
	)
	var height := Image.create_empty(size.x, size.y, false, Image.FORMAT_RF)
	height.blit_rect(grid_image, Rect2i(Vector2i.ZERO, grid_image.get_size()), offset)

	var hole := Color(Terrain3DUtil.as_float(Terrain3DUtil.enc_hole(true)), 0.0, 0.0, 1.0)
	var control := Image.create_empty(size.x, size.y, false, Image.FORMAT_RF)
	control.fill(hole)
	control.fill_rect(Rect2i(offset, grid_image.get_size()), Color(0.0, 0.0, 0.0, 1.0))

	terrain.data.import_images([height, control, null], corner, 0.0, 1.0)
