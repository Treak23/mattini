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
##
## Given a PhotoGrid the terrain wears the aerial photo: the override shader is
## terrain_photo.gdshader, which samples the photo by world position inside the PhotoGrid's
## rectangle. Without one it keeps M2's clay look. Given a SurfaceGrid as well, the shader
## also draws swissTLM3D's classes on the photo (rock, water, path, road) with the CC0
## textures under res://textures/ and two generated water normal maps; the classes alone,
## without a photo, change nothing.

const TERRAIN_NAME := "Terrain"
const REGION_WIDTH_M := 1024.0
const CLAY_SHADER := "res://shaders/terrain_clay.gdshader"
const PHOTO_SHADER := "res://shaders/terrain_photo.gdshader"
const TEXTURES_DIR := "res://textures"
## The photo shader's CC0 texture uniforms and the Poly Haven files they take (each named in
## res://textures/LICENSE.txt, imported with mipmaps).
const SURFACE_TEXTURES := {
	"rock_albedo": "rock_face_03_diff_2k.jpg",
	"rock_normal": "rock_face_03_nor_gl_2k.jpg",
	"rock_roughness": "rock_face_03_rough_2k.jpg",
	"road_albedo": "worn_asphalt_diff_1k.jpg",
	"road_normal": "worn_asphalt_nor_gl_1k.jpg",
	"path_albedo": "rocky_trail_diff_1k.jpg",
	"path_normal": "rocky_trail_nor_gl_1k.jpg",
}
## The water's two generated normal maps: uniform and noise seed.
const WATER_NORMALS := {"water_normal_a": 1, "water_normal_b": 2}
const WATER_NORMAL_SIZE := 256
const WATER_BUMP_STRENGTH := 6.0


## Adds a Terrain3D node named "Terrain" to [param parent] (in the tree, with a camera in
## its viewport) and returns it with the grid's heights loaded. The parent must be in the
## tree: Terrain3D builds its material and data only on entering it. With [param photo] the
## terrain shows that photo, otherwise the clay look; with [param surfaces] too, the classes
## are drawn on the photo.
static func create(
	grid: TerrainGrid, parent: Node, photo: PhotoGrid = null, surfaces: SurfaceGrid = null
) -> Terrain3D:
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
	# The shader first: Terrain3D drops a parameter set before the shader declares it (H25).
	material.shader_override = load(CLAY_SHADER if photo == null else PHOTO_SHADER)
	material.shader_override_enabled = true
	material.set_shader_param("height_offset_m", grid.height_offset_m)
	if photo != null:
		material.set_shader_param("photo", photo.texture)
		material.set_shader_param("photo_rect", photo.rect())
		if surfaces != null:
			_set_surfaces(material, surfaces)
	_import(terrain, grid, region_vertices)
	return terrain


## Hands the photo shader the classes, their own rectangle (not the photo's), the CC0
## textures and the water's generated normal maps. Every sampler the shader declares is set:
## an unset one draws Godot's default texture, silently.
static func _set_surfaces(material: Terrain3DMaterial, surfaces: SurfaceGrid) -> void:
	material.set_shader_param("surfaces", surfaces.texture)
	material.set_shader_param("surfaces_rect", surfaces.rect())
	for uniform: String in SURFACE_TEXTURES:
		material.set_shader_param(uniform, load(TEXTURES_DIR.path_join(SURFACE_TEXTURES[uniform])))
	for uniform: String in WATER_NORMALS:
		material.set_shader_param(uniform, _water_normal(WATER_NORMALS[uniform]))


## A seamless 256 × 256 normal map of smooth simplex noise (3 octaves), made in memory: the
## water's ripples need no file.
static func _water_normal(noise_seed: int) -> NoiseTexture2D:
	var noise := FastNoiseLite.new()
	noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	noise.seed = noise_seed
	noise.fractal_octaves = 3
	var texture := NoiseTexture2D.new()
	texture.noise = noise
	texture.width = WATER_NORMAL_SIZE
	texture.height = WATER_NORMAL_SIZE
	texture.seamless = true
	texture.as_normal_map = true
	texture.bump_strength = WATER_BUMP_STRENGTH
	return texture


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
