"""The pin author's mutation harness for brief v0.5.0-12 (sketch, not a test; never run by the gate).

Usage: python3 v0.5.0-12-mutate.py <repo worktree> <scratch dir> [row numbers...]
Each row: one exact text edit, its diff saved to <scratch>/rows/row-N.patch, the check run (T:
RENDER-T, P: RENDER-P, Y: PY-12), the file restored by `git apply -R` and checked equal.
Needs XDG_DATA_HOME set to the worktree's own (brain.md H9).
"""
import subprocess, sys, pathlib, json
F = pathlib.Path(sys.argv[1]); S = pathlib.Path(sys.argv[2]); only = sys.argv[3:]
TL = "game/scripts/trees/tree_loader.gd"; SH = "game/shaders/terrain_photo.gdshader"
SG = "game/scripts/terrain/surface_grid.gd"; G = "tools/gate.sh"
WW = "\tvec2 t = (xz - surfaces_rect.xy) / surfaces_rect.zw * vec2(size) - 0.5;\n\tvec2 base = floor(t);\n\tvec2 f = t - base;\n\tivec2 i0 = ivec2(base);\n\tfloat share = 0.0;"
def ww(dx, dz):
    return (SH, WW, WW.replace("(xz - surfaces_rect", f"(xz - vec2({dx}, {dz}) - surfaces_rect"))
gate = (F / G).read_text()
para_old = "where the photo, the water class, the capture-shadow"
ROWS = {
 1: (TL, "const VISIBILITY_END_M := 3000.0", "const VISIBILITY_END_M := 1.0", "T"),
 2: (TL, "\ttrees.name = NODE_NAME\n", "\ttrees.name = NODE_NAME\n\ttrees.visible = false\n", "T"),
 3: (TL, "Vector3(radius, heights[k], radius)", "Vector3(radius * 0.1, heights[k], radius * 0.1)", "T"),
 4: (TL, "Vector3(radius, heights[k], radius)", "Vector3(radius, heights[k] * 0.05, radius)", "T"),
 5: ww("0.1", "0.0") + ("P",), 6: ww("-0.05", "0.0") + ("P",), 7: ww("0.0", "0.3") + ("P",),
 8: ww("0.0", "-0.2") + ("P",),
 9: (SH, WW, WW.replace("* vec2(size) - 0.5;", "* vec2(size);"), "P"),
 10: ww("0.0", "0.1") + ("P",),
 11: (G, para_old, "where the photo, the surface classes, the capture-shadow", "Y"),
 12: (G, "land, whether the crowns are drawn (brief v0.5.0-12), and which", "land, (brief v0.5.0-12), and which", "Y"),
 13: (G, "where the photo, the water class, the lift and the crowns' colour land, whether the crowns are drawn and which way the ripples drift are not checked\"",
      "where the photo, the classes, the lift and the crowns' colour land and which way the ripples drift are not checked\"", "Y"),
 14: (SG, "var column := floori((x - x0) / cell_m)", "var column := roundi((x - x0) / cell_m)", "P"),
 15: (SG, "var row := floori((z - z0) / cell_m)", "var row := roundi((z - z0) / cell_m)", "P"),
 16: (G, "Of the classes only the\n# water is checked; rock", "Of the classes the\n# water is checked; rock", "Y"),
 17: (G, "(the photo and the water class, the lift", "(the photo and the classes, the lift", "Y"),
}
def run(kind):
    if kind == "Y":
        r = subprocess.run("uv run --project pipeline pytest -q -p no:cacheprovider -rf pipeline/tests/test_gate_render.py pipeline/tests/test_v050_12_render_words.py", shell=True, cwd=F, capture_output=True, text=True)
        return "\n".join(l for l in r.stdout.splitlines() if l.startswith("FAILED") or " passed" in l or " failed" in l)
    script = {"T": "render_trees.gd", "P": "render_photo.gd"}[kind]
    cmd = ("xvfb-run -a timeout --kill-after=10 180 godot --path game --audio-driver Dummy "
           "--fixed-fps 60 --rendering-method gl_compatibility --resolution 1280x720 "
           f"-s res://tests/render/{script}")
    r = subprocess.run(cmd, shell=True, cwd=F, capture_output=True, text=True)
    lines = [l for l in r.stdout.splitlines() if l.startswith("RENDER")]
    return "\n".join(lines + [f"exit {r.returncode}"])
for n, (path, old, new, kind) in ROWS.items():
    if only and str(n) not in only: continue
    p = F / path; before = p.read_text()
    assert before.count(old) == 1, (n, before.count(old))
    p.write_text(before.replace(old, new))
    patch = S / f"rows/row-{n}.patch"
    patch.write_text(subprocess.run(["git", "diff", "--", path], cwd=F, capture_output=True, text=True).stdout)
    out = run(kind)
    subprocess.run(["git", "apply", "-R", str(patch)], cwd=F, check=True)
    assert p.read_text() == before, n
    print(f"=== row {n} ({kind})\n{out}", flush=True)
