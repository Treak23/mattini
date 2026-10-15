class_name TreeLoader
extends RefCounted
## Puts one procedural conifer on every tree of TreeChunks, one MultiMesh per 250 m cell
## (docs/SPEC.md §8, the trees; §10, M3's game: the look).
##
## The data gives where a tree stands and how tall and wide it is, not what it is: every
## tree is the same generic conifer (TREES_NOTE says so in the credits), built once in code
## and normalised, its top at y = 1 and its widest rim at radius 1 from the axis, so an
## instance scaled to (crown radius, height, crown radius) has the data's height and crown.
## Each instance is turned about the vertical by a hash of its position, so the trees do not
## all face one way, and stands at the position from the file, unchanged: no coordinate is
## converted here.
##
## Each cell's MultiMesh is filled through its `buffer` (12 floats per instance, no colour
## and no custom data): measured in Godot 4.6.3, the headless RenderingServer drops
## set_instance_transform but keeps a buffer (brain.md H25), and colours never ride on
## instance data, because the renderers treat them differently (H21). The crown's colour
## comes from the photo, sampled by the shader (res://shaders/tree_conifer.gdshader).

const NODE_NAME := "Trees"
const SHADER := "res://shaders/tree_conifer.gdshader"
## The side of a cell in metres: a cell is floor(x / CELL_M), floor(z / CELL_M) of the
## trees' local x and z.
const CELL_M := 250.0
## The turn has this many steps about the vertical.
const YAW_STEPS := 4096
## A tuning value: beyond this many metres a tree is not drawn.
const VISIBILITY_END_M := 3000.0
## The credits' note (brief M3-14 shows it under "Placeholders"): the conifer is generic.
const TREES_NOTE := (
	"Trees: one generic conifer shape, placed and sized from swissSURFACE3D;"
	+ " the data gives no species."
)

## The conifer: six tiers of ten rim points (a tier is an apex, a ring of shoulders and a
## ring of rim points) and a hexagonal trunk. Everything below is in the unit tree's units.
const TIERS := 6
const RIM_POINTS := 10
const TRUNK_SIDES := 6
## Where each tier's rim stands, how wide it is before the rims are normalised, and where
## its apex is, bottom tier first. The top tier's apex is the tree's top, at y = 1.
const TIER_RIM_Y := [0.14, 0.29, 0.44, 0.58, 0.72, 0.85]
const TIER_RIM_RADIUS := [1.0, 0.84, 0.68, 0.52, 0.36, 0.22]
const TIER_APEX_Y := [0.46, 0.60, 0.72, 0.84, 0.94, 1.0]
## The shoulder ring's radius as a share of the rim's, and how far up the apex-to-rim line
## it stands (more than the share, so the boughs arch and droop at their tips).
const SHOULDER_RADIUS_SHARE := 0.55
const SHOULDER_RISE := 0.62
const TRUNK_RADIUS := 0.06
const TRUNK_FOOT_Y := -0.06
const TRUNK_TOP_Y := 0.2
## The conifer's variants: the shapes differ in their jitter, the topology is the same.
const VARIANTS := 3
## The rims' jitter: share of the radius, and radians of angle.
const RIM_JITTER := 0.18
const ANGLE_JITTER := 0.12


## Adds a Node3D named "Trees" to [param parent], holding one MultiMeshInstance3D per 250 m
## cell that holds trees, named "<cx>_<cz>", and returns it. With [param photo] and its
## rectangle [param photo_rect] (local x0, z0, width, depth: the rectangle of the terrain's
## photo), the crowns take their colour from the photo; without a photo, a labelled
## placeholder green. A rectangle without width or depth leaves the shader on the
## placeholder too. The shader reads each tree's position in world space, so the rectangle
## is in world space as well: the parent must sit at the origin, unturned and unscaled, as
## the main scene's root does.
static func create(
	chunks: TreeChunks, parent: Node, photo: Texture2D = null, photo_rect: Vector4 = Vector4.ZERO
) -> Node3D:
	var trees := Node3D.new()
	trees.name = NODE_NAME
	var mesh := conifer()
	var material := _material(photo, photo_rect)
	var cells := _cells(chunks)
	var keys := cells.keys()
	keys.sort_custom(
		func(a: Vector2i, b: Vector2i) -> bool: return a.x < b.x or (a.x == b.x and a.y < b.y)
	)
	for key: Vector2i in keys:
		var buffer: PackedFloat32Array = cells[key]
		var multimesh := MultiMesh.new()
		multimesh.transform_format = MultiMesh.TRANSFORM_3D
		multimesh.use_colors = false
		multimesh.use_custom_data = false
		multimesh.mesh = mesh
		multimesh.instance_count = buffer.size() / 12
		multimesh.buffer = buffer
		var instance := MultiMeshInstance3D.new()
		instance.name = "%d_%d" % [key.x, key.y]
		instance.multimesh = multimesh
		instance.material_override = material
		instance.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		instance.visibility_range_end = VISIBILITY_END_M
		trees.add_child(instance)
	parent.add_child(trees)
	return trees


## The turn of the tree at local ([param x], [param z]) about the vertical, in radians: an
## integer hash of round(2x) and round(2z), in YAW_STEPS steps from 0 to a full turn.
static func yaw_of(x: float, z: float) -> float:
	var h := _hash(roundi(2.0 * x), roundi(2.0 * z))
	return TAU * float(h % YAW_STEPS) / float(YAW_STEPS)


## A 32-bit integer mix of two integers (any sign).
static func _hash(a: int, b: int) -> int:
	var h := (a * 0x9E3779B1 + b * 0x85EBCA6B) & 0xFFFFFFFF
	h = ((h ^ (h >> 15)) * 0x2C1B3C6D) & 0xFFFFFFFF
	h = ((h ^ (h >> 12)) * 0x297A2D39) & 0xFFFFFFFF
	return h ^ (h >> 15)


## The buffers of every cell that holds trees: cell (floor(x / CELL_M), floor(z / CELL_M)) to
## 12 floats per tree, the rows of its 3 x 4 matrix (basis columns x, y, z, then the origin).
static func _cells(chunks: TreeChunks) -> Dictionary:
	var cells := {}
	for chunk: Dictionary in chunks.chunks:
		var positions: PackedVector3Array = chunk["positions"]
		var heights: PackedFloat32Array = chunk["heights"]
		var radii: PackedFloat32Array = chunk["radii"]
		for k in positions.size():
			var at := positions[k]
			var key := Vector2i(floori(at.x / CELL_M), floori(at.z / CELL_M))
			if not cells.has(key):
				cells[key] = PackedFloat32Array()
			var buffer: PackedFloat32Array = cells[key]
			var radius := radii[k]
			var basis := Basis(Vector3.UP, yaw_of(at.x, at.z)).scaled(
				Vector3(radius, heights[k], radius)
			)
			buffer.append(basis.x.x)
			buffer.append(basis.y.x)
			buffer.append(basis.z.x)
			buffer.append(at.x)
			buffer.append(basis.x.y)
			buffer.append(basis.y.y)
			buffer.append(basis.z.y)
			buffer.append(at.y)
			buffer.append(basis.x.z)
			buffer.append(basis.y.z)
			buffer.append(basis.z.z)
			buffer.append(at.z)
	return cells


## The one material of every tree: the shader, and with a photo its texture and rectangle.
static func _material(photo: Texture2D, photo_rect: Vector4) -> ShaderMaterial:
	var material := ShaderMaterial.new()
	material.shader = load(SHADER)
	if photo != null:
		material.set_shader_parameter("photo", photo)
		material.set_shader_parameter("photo_rect", photo_rect)
	return material


## The conifer, built once: VERTEX holds variant 0, CUSTOM0 variant 1 and CUSTOM1 variant 2
## (the shader picks one by a hash of the instance's origin), TEX_UV.x is 1 on the trunk and
## 0 on the crown, TEX_UV.y shades a tier from its rim (0) to its apex (1). Three variants
## with the same topology: 138 vertices and 192 triangles. No normals: the shader derives
## flat ones. The custom AABB is the unit cylinder, because the mesh's own is VERTEX only.
static func conifer() -> ArrayMesh:
	var shapes: Array[PackedVector3Array] = []
	for variant in VARIANTS:
		shapes.append(_shape(variant))
	var shading := _shading()
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = shapes[0]
	arrays[Mesh.ARRAY_TEX_UV] = shading
	arrays[Mesh.ARRAY_CUSTOM0] = _floats(shapes[1])
	arrays[Mesh.ARRAY_CUSTOM1] = _floats(shapes[2])
	arrays[Mesh.ARRAY_INDEX] = _indices()
	var flags := (
		(Mesh.ARRAY_CUSTOM_RGB_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM0_SHIFT)
		| (Mesh.ARRAY_CUSTOM_RGB_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM1_SHIFT)
	)
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays, [], {}, flags)
	mesh.custom_aabb = AABB(
		Vector3(-1.0, TRUNK_FOOT_Y, -1.0), Vector3(2.0, 1.0 - TRUNK_FOOT_Y, 2.0)
	)
	return mesh


static func _floats(points: PackedVector3Array) -> PackedFloat32Array:
	var floats := PackedFloat32Array()
	floats.resize(3 * points.size())
	for i in points.size():
		floats[3 * i] = points[i].x
		floats[3 * i + 1] = points[i].y
		floats[3 * i + 2] = points[i].z
	return floats


## One variant's vertices: per tier the apex, the shoulders and the rim points, then the
## trunk's foot ring and top ring. The rims are jittered from a fixed seed per variant and
## the crown is then scaled in x and z so its widest point is exactly at radius 1. The apexes
## stay on the axis, the top one at y = 1; the trunk is the same in every variant.
static func _shape(variant: int) -> PackedVector3Array:
	var random := RandomNumberGenerator.new()
	random.seed = 1 + variant
	var points := PackedVector3Array()
	for tier in TIERS:
		var phase := 0.31 * tier + 0.7 * variant
		var rim_radius: float = TIER_RIM_RADIUS[tier]
		var rim_y: float = TIER_RIM_Y[tier]
		var apex_y: float = TIER_APEX_Y[tier]
		var shoulder_y := rim_y + SHOULDER_RISE * (apex_y - rim_y)
		points.append(Vector3(0.0, apex_y, 0.0))
		var shoulders := PackedVector3Array()
		var rim := PackedVector3Array()
		for k in RIM_POINTS:
			var angle := phase + TAU * k / RIM_POINTS + ANGLE_JITTER * random.randf_range(-1.0, 1.0)
			var reach := 1.0 + RIM_JITTER * random.randf_range(-1.0, 1.0)
			var droop := 0.03 * random.randf()
			shoulders.append(_around(angle, SHOULDER_RADIUS_SHARE * rim_radius * reach, shoulder_y))
			rim.append(_around(angle, rim_radius * reach, rim_y - droop))
		points.append_array(shoulders)
		points.append_array(rim)
	var widest := 0.0
	for p in points:
		widest = maxf(widest, Vector2(p.x, p.z).length())
	for i in points.size():
		points[i] = Vector3(points[i].x / widest, points[i].y, points[i].z / widest)
	for y in [TRUNK_FOOT_Y, TRUNK_TOP_Y]:
		for k in TRUNK_SIDES:
			points.append(_around(TAU * k / TRUNK_SIDES, TRUNK_RADIUS, y))
	return points


## The point at [param angle] about the vertical axis, [param radius] from it, at height
## [param y]: x = cos, z = -sin, so the angle grows counter-clockwise seen from above.
static func _around(angle: float, radius: float, y: float) -> Vector3:
	return Vector3(radius * cos(angle), y, -radius * sin(angle))


## TEX_UV per vertex: x 1 on the trunk and 0 on the crown, y the shade from rim to apex.
static func _shading() -> PackedVector2Array:
	var uv := PackedVector2Array()
	for tier in TIERS:
		uv.append(Vector2(0.0, 1.0))
		for k in RIM_POINTS:
			uv.append(Vector2(0.0, 0.6))
		for k in RIM_POINTS:
			uv.append(Vector2(0.0, 0.0))
	for k in 2 * TRUNK_SIDES:
		uv.append(Vector2(1.0, 0.0))
	return uv


## The triangles, shared by the three variants. Each is written (a, b, c) with its
## right-hand normal pointing out of the tree and goes in as (a, c, b): Godot's front faces
## are clockwise (brain.md H16). A tier is a fan from its apex to its shoulders, then a strip
## from the shoulders to the rim.
static func _indices() -> PackedInt32Array:
	var indices := PackedInt32Array()
	var per_tier := 1 + 2 * RIM_POINTS
	for tier in TIERS:
		var apex := tier * per_tier
		var shoulder := apex + 1
		var rim := shoulder + RIM_POINTS
		for k in RIM_POINTS:
			var next := (k + 1) % RIM_POINTS
			_triangle(indices, apex, shoulder + k, shoulder + next)
			_triangle(indices, shoulder + k, rim + k, rim + next)
			_triangle(indices, shoulder + k, rim + next, shoulder + next)
	var foot := TIERS * per_tier
	var top := foot + TRUNK_SIDES
	for k in TRUNK_SIDES:
		var next := (k + 1) % TRUNK_SIDES
		_triangle(indices, foot + k, foot + next, top + k)
		_triangle(indices, foot + next, top + next, top + k)
	return indices


static func _triangle(indices: PackedInt32Array, a: int, b: int, c: int) -> void:
	indices.append(a)
	indices.append(c)
	indices.append(b)
