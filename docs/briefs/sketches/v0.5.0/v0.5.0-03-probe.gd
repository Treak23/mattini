extends SceneTree
# Pin author's probe (brief v0.5.0-03): the cost of reading a village-sized mask (4000 x 6000 L8),
# as the throwaway reader does it, headless. Synthetic content: blocks of shadow, so the PNG
# compresses roughly as a real mask; not the village's mask.


func _sha(data: PackedByteArray) -> String:
	var c := HashingContext.new()
	c.start(HashingContext.HASH_SHA256)
	c.update(data)
	return c.finish().hex_encode()


func _init() -> void:
	var w := 4000
	var h := 6000
	var px := PackedByteArray()
	px.resize(w * h)
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	for i in 3000:
		var x := rng.randi_range(0, w - 40)
		var y := rng.randi_range(0, h - 60)
		var bw := rng.randi_range(4, 40)
		var bh := rng.randi_range(4, 60)
		for r in bh:
			var at := (y + r) * w + x
			for c in bw:
				px[at + c] = 255
	var png := Image.create_from_data(w, h, false, Image.FORMAT_L8, px).save_png_to_buffer()
	print("png bytes ", png.size())
	for run in 3:
		var t0 := Time.get_ticks_usec()
		var s1 := _sha(png)
		var t1 := Time.get_ticks_usec()
		var image := Image.new()
		image.load_png_from_buffer(png)
		var t2 := Time.get_ticks_usec()
		var s2 := _sha(image.get_data())
		var t3 := Time.get_ticks_usec()
		image.generate_mipmaps()
		var t4 := Time.get_ticks_usec()
		var tex := ImageTexture.create_from_image(image)
		var t5 := Time.get_ticks_usec()
		print(
			"run %d: sha png %.3f s, decode %.3f s, sha pixels %.3f s, mipmaps %.3f s, texture %.3f s, total %.3f s; bytes with mipmaps %d, levels %d, %s %s"
			% [run, (t1 - t0) / 1e6, (t2 - t1) / 1e6, (t3 - t2) / 1e6, (t4 - t3) / 1e6, (t5 - t4) / 1e6, (t5 - t0) / 1e6,
			image.get_data().size(), image.get_mipmap_count(), s1.left(8), s2.left(8)]
		)
		tex = null
	quit()
