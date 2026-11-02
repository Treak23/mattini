"""Runs each mutation row both ways on the rehearsal's throwaway: break, GUT-3, restore, GUT-3."""
import hashlib, subprocess, sys
from pathlib import Path

import os
B = Path(os.environ.get("MUTATE_TREE", "/tmp/claude-0/-home-user-mattini/2df1b92e-a4c1-5fe4-978f-0932f23f43fb/scratchpad/pins/B"))
G = "game/scripts/terrain/surroundings_grid.gd"
L = "game/scripts/terrain/surroundings_loader.gd"
GUT = os.environ.get("MUTATE_GUT", "/tmp/claude-0/-home-user-mattini/2df1b92e-a4c1-5fe4-978f-0932f23f43fb/scratchpad/pins/work08/gut3.sh")
ROWS = [
 ("R1", G, 'world.to_local(box["e_min"], box["n_max"], world.height_offset)', 'world.to_local(box["e_min"], box["n_min"], world.height_offset)', "reader: rows flipped (z_min from n_min)"),
 ("R2", G, '		x_min = corner.x\n		z_min = corner.z', '		var f32 := Vector3(box["e_min"], 0.0, box["n_max"]) - Vector3(world.origin_e, 0.0, world.origin_n)\n		x_min = f32.x\n		z_min = -f32.z', "reader: a 32-bit subtraction"),
 ("R3", G, '	if ManifestValue.differs(block.get("height_offset_m"), world.height_offset):', '	if false:', "reader: no height-offset guard"),
 ("R4", G, '		or ManifestValue.differs(origin.get("n"), world.origin_n)\n	):', '		or ManifestValue.differs(origin.get("n"), world.origin_n)\n		or ManifestValue.differs(block.get("height_offset_m"), world.height_offset)\n	):', "reader: one wording for both (the 0.5.0 residue)"),
 ("R5", G, '	if absf(count * cell - side) > BOX_TOLERANCE_M:', '	if false:', "reader: no colour fit check"),
 ("R6", G, '	if count > MAX_TEXTURE:', '	if false:', "reader: no 16384 limit"),
 ("R7", G, '	if ManifestValue.differs(source["dataset"], COLOUR_DATASET):', '	if false:', "reader: no colour dataset check"),
 ("R8", G, 'not (filled >= 0.0 and filled <= 1.0)', 'false', "reader: filled_fraction range unchecked"),
 ("R9", G, '	if found != String(block["colour_sha256"]).to_lower():', '	if false:', "reader: no colour SHA-256 check"),
 ("R10", G, '		or image.get_size() != Vector2i(colour_columns, colour_rows)', '		or false', "reader: no decoded-size check"),
 ("R11", G, '	var rebuild := ReleaseBuild.file_hint(COLOUR_COMMAND)', '	var rebuild := ReleaseBuild.file_hint(HEIGHTS_COMMAND)', "reader: colour messages name the heights' command"),
 ("R12", G, '	var rebuild := ReleaseBuild.file_hint(COLOUR_COMMAND)', '	var rebuild := "; %s rebuilds " % COLOUR_COMMAND + "it"', "reader: the colour hint spelled out, not file_hint"),
 ("R13", G, '	image.generate_mipmaps()', '	image.flip_y()\n	image.generate_mipmaps()', "reader: colour flipped north-south"),
 ("R14", G, '	image.generate_mipmaps()', '	pass', "reader: no mipmaps"),
 ("R15", G, '	if _sorted_keys(block) != KEYS:', '	if false:', "reader: key set unchecked"),
 ("R16", G, '		typeof(block.get("world_sha256")) != TYPE_STRING\n		or ManifestValue.differs(block["world_sha256"], manifest.get("world_sha256"))', '		block.get("world_sha256") != manifest.get("world_sha256")', "reader: the type check dropped and != instead of ManifestValue (H26)"),
 ("L1", L, '				grid.z_min + row * grid.spacing_m', '				grid.z_min + (grid.rows - 1 - row) * grid.spacing_m', "loader: rows flipped"),
 ("L2", L, '				grid.x_min + column * grid.spacing_m,\n				grid.heights[k],\n				grid.z_min + row * grid.spacing_m', '				grid.z_min + row * grid.spacing_m,\n				grid.heights[k],\n				grid.x_min + column * grid.spacing_m', "loader: x and z swapped"),
 ("L3", L, '			if is_nan(heights[k]):', '			if false:', "loader: the cut ignored"),
 ("L4", L, '			indices.append_array([a, b, c, b, d, c])', '			indices.append_array([a, b, c])', "loader: one triangle per square"),
 ("L5", L, '			indices.append_array([a, b, c, b, d, c])', '			indices.append_array([a, c, b, b, c, d])', "loader: winding reversed"),
 ("L6", L, '			chunk.mesh = mesh', '			chunk.mesh = mesh\n			chunk.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_SHADOWS_ONLY', "loader: chunks shadows-only (M4-07's)"),
 ("L7", L, '		skirt.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF', '		pass', "loader: the skirt casts"),
 ("L8", L, 'const CHUNK_SQUARES := 80', 'const CHUNK_SQUARES := 64', "loader: chunks of 64"),
 ("L9", L, '			var h_w := heights[k - 1] if west else h', '			var h_w := h', "loader: one-sided differences east-west"),
 ("L10", L, '			normals[k] = Vector3(-dx, 1.0, -dz).normalized()', '			normals[k] = Vector3(-dx, 1.0, dz).normalized()', "loader: normal's z sign flipped"),
 ("L11", L, '			uvs[k] = Vector2(float(column) / (grid.columns - 1), float(row) / (grid.rows - 1))', '			uvs[k] = Vector2(float(column) / (grid.columns - 1), 1.0 - float(row) / (grid.rows - 1))', "loader: v flipped (texture mirrored north-south)"),
 ("L12", L, '			uvs[k] = Vector2(float(column) / (grid.columns - 1), float(row) / (grid.rows - 1))', '			uvs[k] = Vector2(float(column) / grid.columns, float(row) / grid.rows)', "loader: UV over columns, not columns - 1"),
 ("L13", L, '		skirt_material.cull_mode = BaseMaterial3D.CULL_DISABLED', '		skirt_material.cull_mode = BaseMaterial3D.CULL_BACK', "loader: the skirt one-sided (back faces culled; the session's ruling re-cut this row)"),
 ("L14", L, 'const SKIRT_DEPTH_M := 100.0', 'const SKIRT_DEPTH_M := 50.0', "loader: skirt 50 m deep"),
 ("L15", L, '			if north != south:', '			if false:', "loader: no skirt on the east-west edges"),
 ("L16", L, '	material.roughness = 1.0', '	material.roughness = 0.5', "loader: roughness 0.5"),
 ("L17", L, '	material.specular_mode = BaseMaterial3D.SPECULAR_DISABLED', '	pass', "loader: specular on"),
 ("L18", L, '	material.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC', '	material.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR', "loader: no mipmaps or anisotropy"),
 ("L19", L, '	root.name = "Surroundings"', '	root.name = "Surroundings"\n	root.rotate_y(PI)', "loader: the node turned"),
 ("L20", L, '				grid.x_min + column * grid.spacing_m,', '				grid.x_min + (column + 0.5) * grid.spacing_m,', "loader: every vertex half a spacing east"),
 ("L21", L, '			if mesh == null:\n				continue', '			if mesh == null:\n				var empty := MeshInstance3D.new()\n				empty.name = "Chunk_%d_%d" % [i, j]\n				root.add_child(empty)\n				continue', "loader: a node for an empty chunk"),
 ("L22", L, '		skirt_uvs.append_array([uvs[ka], uvs[kb], uvs[ka], uvs[kb]])', '		skirt_uvs.append_array([uvs[ka], uvs[kb], Vector2.ZERO, Vector2.ZERO])', "loader: skirt bottoms' UV 0"),
 ("L23", L, '			normals.append(outward)', '			normals.append(Vector3.UP)', "loader: skirt normals up"),
 ("L24", L, '		skirt_mesh.surface_set_material(0, skirt_material)', '		skirt_mesh.surface_set_material(0, material)', "loader: the skirt drawn with the chunks' material (the session's ruling)"),
 ("R17", G, '	return _check_cut(f32_path, block, rebuild)', '	return ""', "reader: no NaN layout check (the session's ruling)"),
]
only = set(sys.argv[1:])
for rid, rel, old, new, what in ROWS:
    if only and rid not in only:
        continue
    p = B / rel
    orig = p.read_text(encoding="utf-8")
    assert orig.count(old) == 1, (rid, "old text not unique")
    p.write_text(orig.replace(old, new), encoding="utf-8")
    broke = subprocess.run([GUT], capture_output=True, text=True).stdout.strip().split("\n")
    p.write_text(orig, encoding="utf-8")
    assert hashlib.sha256(p.read_bytes()).digest() == hashlib.sha256(orig.encode()).digest()
    back = subprocess.run([GUT], capture_output=True, text=True).stdout.strip().split("\n")
    print(f"## {rid} {what}")
    print("  broken:", " | ".join(broke))
    print("  restored:", back[1] if len(back) > 1 else back)
    sys.stdout.flush()
