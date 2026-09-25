extends GutTest
## Pinning tests for brief M1-02: WorldConfig's inverse is tested for every rotation, with
## inputs from the wider type (M0 R1 C-03 and C-06; lesson 34).
##
## Pinned decisions: for each of the 24 rotations WorldConfig accepts, to_lv95(to_local(p))
## returns p. The owner's mapping swaps n and h and is its own inverse, so a to_lv95 that
## applied the mapping instead of its inverse passed every M0 game test; the 8 cyclic
## rotations tell the two apart (measured by the M0 review: 1.1 km off). Random round trips
## draw 64-bit offsets (a millimetre grid plus a sub-millimetre fraction), which a 32-bit
## Vector3 cannot hold exactly, so the 2 mm budget of SPEC §6 is actually exercised.

const MANIFEST_PATH := "res://assets/generated/manifest.json"
const SCRATCH_DIR := "user://test_world_config_round_trips"
const PERMUTATIONS := [
	["e", "n", "h"],
	["e", "h", "n"],
	["n", "e", "h"],
	["n", "h", "e"],
	["h", "e", "n"],
	["h", "n", "e"],
]
## Points with three different offsets from the origin, so no two axes can be confused.
const OFFSETS := [[825.13, -489.77, 1606.37], [-5951.25, -4327.0, 4478.0], [2000.0, 3.5, -12.25]]

var _written := 0


func before_all() -> void:
	DirAccess.make_dir_recursive_absolute(SCRATCH_DIR)


func after_all() -> void:
	for file in DirAccess.get_files_at(SCRATCH_DIR):
		DirAccess.remove_absolute(SCRATCH_DIR.path_join(file))
	DirAccess.remove_absolute(SCRATCH_DIR)


func _world_with_axes(axes: Dictionary) -> WorldConfig:
	var manifest: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(MANIFEST_PATH))
	manifest["world"]["axes"] = axes
	_written += 1
	var path := SCRATCH_DIR.path_join("manifest_%d.json" % _written)
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string(JSON.stringify(manifest))
	file.close()
	return WorldConfig.from_manifest(path)


## Parity of the permutation times the product of the signs: +1 for a rotation.
func _is_rotation(axes: Dictionary) -> bool:
	var order := []
	var sign := 1
	for game_axis in ["x", "y", "z"]:
		var spec: String = axes[game_axis]
		order.append(["e", "n", "h"].find(spec[1]))
		if spec[0] == "-":
			sign = -sign
	var inversions := 0
	for i in 3:
		for j in range(i + 1, 3):
			if order[i] > order[j]:
				inversions += 1
	return sign * (1 if inversions % 2 == 0 else -1) == 1


func test_every_rotation_round_trips() -> void:
	var rotations := 0
	for perm: Array in PERMUTATIONS:
		for bits in 8:
			var axes := {}
			for i in 3:
				axes[["x", "y", "z"][i]] = ("-" if bits & (1 << i) else "+") + perm[i]
			if not _is_rotation(axes):
				continue
			rotations += 1
			var world := _world_with_axes(axes)
			assert_not_null(world, "rotation %s is accepted" % [axes])
			if world == null:
				continue
			for offset: Array in OFFSETS:
				var e: float = world.origin_e + offset[0]
				var n: float = world.origin_n + offset[1]
				var h: float = offset[2]
				var back := world.to_lv95(world.to_local(e, n, h))
				assert_almost_eq(back[0], e, 0.002, "%s: e of %s" % [axes, offset])
				assert_almost_eq(back[1], n, 0.002, "%s: n of %s" % [axes, offset])
				assert_almost_eq(back[2], h, 0.002, "%s: h of %s" % [axes, offset])
	assert_eq(rotations, 24, "all 24 rotations round-trip")


func test_random_round_trips_with_64_bit_offsets() -> void:
	var world := WorldConfig.from_manifest(MANIFEST_PATH)
	assert_not_null(world)
	if world == null:
		return
	var rng := RandomNumberGenerator.new()
	rng.seed = 20260925
	var inexact := 0
	for i in 200:
		var de := rng.randi_range(-20000000, 20000000) / 1000.0 + rng.randf() * 0.001
		var dn := rng.randi_range(-20000000, 20000000) / 1000.0 + rng.randf() * 0.001
		var h := rng.randi_range(-500000, 5000000) / 1000.0 + rng.randf() * 0.001
		var local := world.to_local(world.origin_e + de, world.origin_n + dn, h)
		if float(local.x) != de:
			inexact += 1
		var back := world.to_lv95(local)
		assert_almost_eq(back[0], world.origin_e + de, 0.002, "e of point %d" % i)
		assert_almost_eq(back[1], world.origin_n + dn, 0.002, "n of point %d" % i)
		assert_almost_eq(back[2], h, 0.002, "h of point %d" % i)
	assert_gt(inexact, 150, "the offsets really are wider than 32 bits")
