extends RefCounted
## Helpers of the gate's render scripts, render_photo.gd, render_lift.gd, render_flow.gd and
## render_trees.gd (brief M3-R1-fix-3; docs/reviews/M3-R1-placement.md §M3-R1-P-03 and its
## Appendix B and C; the lift's and the flow's scripts from briefs v0.5.0-04 and v0.5.0-09).
## Not a test script (GUT runs only test_*.gd) and not a check itself.
##
## A check renders a synthetic world on a flat terrain with a camera straight above it
## (Compatibility renderer, Mesa's llvmpipe under Xvfb: tools/gate.sh runs it with
## xvfb-run) and compares the pixels with what the DATA says is at the world point under
## each one. Together they prove WHERE the photo, the water class, the lift and the crowns'
## colour land, that the crowns are drawn, and which way the ripples drift, to a number; they
## do not prove how anything looks, the other classes, Forward+, the colour encoding or the
## owner's GPU (SPEC §12, brain.md H12, H21).
##
## Each check prints one line, "RENDER <check>: PASS <numbers>" or "RENDER <check>: FAIL
## <what failed>; <numbers>"; tools/gate.sh requires the PASS line of every check and refuses
## a FAIL line. A script's exit status is 1 when any check failed.

const CompleteWorld := preload("res://tests/complete_world.gd")
## The frames a view is given to settle before it is read back.
const SETTLE_FRAMES := 10
## How far below the flat ground a check buries the complete world's box and trees, which
## would stand in the camera's view: the ground is opaque, so they are drawn under it. Their
## blocks stay valid, so that the main scene reads the world without logging a refusal.
const BURY_M := 40.0


## The rendered luminance of [param c] on a 0 to 255 scale (Rec. 709 weights, as the colours
## are, with no transfer function: the same on both sides of every comparison).
static func lum(c: Color) -> float:
	return 255.0 * (0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b)


## The Pearson correlation of [param a] and [param b], to four decimals.
static func corr(a: PackedFloat64Array, b: PackedFloat64Array) -> float:
	var n := a.size()
	var mean_a := 0.0
	var mean_b := 0.0
	for i in n:
		mean_a += a[i]
		mean_b += b[i]
	mean_a /= n
	mean_b /= n
	var sab := 0.0
	var saa := 0.0
	var sbb := 0.0
	for i in n:
		var da := a[i] - mean_a
		var db := b[i] - mean_b
		sab += da * db
		saa += da * da
		sbb += db * db
	return snappedf(sab / sqrt(maxf(saa * sbb, 1e-12)), 0.0001)


## Lowers the complete world's box (its chunk file in [param dir]) by [constant BURY_M] and
## writes its new checksum into [param manifest]: test data, invented in complete_world.gd.
static func bury_buildings(dir: String, manifest: Dictionary) -> void:
	var chunk: Dictionary = manifest["buildings"]["chunks"][0]
	var path := dir.path_join(chunk["file"])
	var data := FileAccess.get_file_as_bytes(path)
	for vertex in int(chunk["vertices"]):
		var at := 12 * vertex + 4
		data.encode_float(at, data.decode_float(at) - BURY_M)
	_store(path, data)
	chunk["sha256"] = CompleteWorld.sha256(data)


## The same for the complete world's trees: each record is five float32, x, y, z, height and
## crown radius, and y goes down by [constant BURY_M].
static func bury_trees(dir: String, manifest: Dictionary) -> void:
	var chunk: Dictionary = manifest["trees"]["chunks"][0]
	var path := dir.path_join(chunk["file"])
	var data := FileAccess.get_file_as_bytes(path)
	for tree in int(chunk["trees"]):
		var at := 20 * tree + 4
		data.encode_float(at, data.decode_float(at) - BURY_M)
	_store(path, data)
	chunk["sha256"] = CompleteWorld.sha256(data)


static func _store(path: String, data: PackedByteArray) -> void:
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_buffer(data)
	file.close()


## The frame the root viewport shows after [constant SETTLE_FRAMES] frames and the draw.
static func capture(tree: SceneTree) -> Image:
	for i in SETTLE_FRAMES:
		await tree.process_frame
	await RenderingServer.frame_post_draw
	return tree.root.get_texture().get_image()


## Saves [param image] as <dir>/<name>.png where a folder was given after "--" on the
## command line (evidence for a brief's Findings; the gate gives none).
static func save(image: Image, name: String) -> void:
	var args := OS.get_cmdline_user_args()
	if args.is_empty():
		return
	image.save_png(args[0].path_join(name + ".png"))


## Prints the check's result line and returns whether it passed: [param failures] is empty.
static func report(check: String, failures: PackedStringArray, numbers: String) -> bool:
	if failures.is_empty():
		print("RENDER %s: PASS %s" % [check, numbers])
		return true
	print("RENDER %s: FAIL %s; %s" % [check, "; ".join(failures), numbers])
	return false
