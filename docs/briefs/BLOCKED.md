# BLOCKED — questions from executor sessions

Plain text, newest first. An executor that hits genuine ambiguity writes its question
here, marks its brief `Status: BLOCKED`, and takes the next OPEN brief — it never invents
the answer. Check `docs/history/RULINGS.md` BEFORE filing: a question it already answers
is answered, not filed. Answered blocks move to `docs/history/blocked/` (DESIGN.md rule 3).

## Open

### 2026-09-25 · M2-05 · all three pinned tests fail as pinned, with an implementation that passes corrected copies

Filed by the executor agent of the one M2 session, on its branch
`worktree-wf_a50d40b2-f95-1`; the brief's code is committed there at `e926a15`, on a green
gate, with the three pinned copies left out of the live tree (as M2-03's were).

What happens: copied byte for byte into `game/tests/` (`cmp` identical), each of M2-05's
pinned tests fails, and no implementation can make it pass:

1. `test_building_chunks.gd` does not parse: `SCRIPT ERROR: Parse Error: The function
   signature doesn't match the parent. Parent signature is "_set(StringName, Variant) ->
   bool".` at line 154. Its helper `func _set(key: String, value: Variant) -> Callable`
   overrides `Object._set`. GUT then prints `Ignoring script res://tests/test_building_chunks.gd
   because it does not extend GutTest` (brain.md H3); the gate fails on both lines.
2. `test_building_loader.gd`: 3/5 tests, 633/823 asserts. Two measured Godot facts:
   - `SurfaceTool.generate_normals()` smooths: vertices at the same position in the same
     smooth group (0 by default) get the average of their triangles' normals. Measured on
     two triangles sharing an edge at 90°: the shared vertices get (-0.707, -0.707, 0). A
     building's corners are shared by walls of different directions, so `godot_normals[3 *
     t]` is a smoothed normal: 93 of the fixture's 110 triangles fail "Godot's front face"
     (e.g. (-0.189, -0.667, 0.721) against the face normal (0, -1, 0)). With
     `tool.set_smooth_group(-1)` (flat, per the SurfaceTool docs) all 110 pass.
   - An `ArrayMesh` stores normals as 16-bit octahedral pairs, so `surface_get_arrays`
     gives them back rounded: (0, 1, 0) reads (0, 1, -1.5e-5), (0, 0, 1) reads (-1.5e-5,
     -1.5e-5, 1). So 96 of 110 fixture triangles miss the 1e-5 tolerance at line 147, and
     `test_a_flat_roof_faces_the_sky` fails: `is_equal_approx` allows 1e-5 near 0, and
     (0, 1, 0) itself is stored as (0, 1, -1.5e-5). Measured worst
     component difference: 5.0e-5 over the fixture's 110 triangles, 1.04e-4 over the real
     village's 178'910; no triangle of either lies within 1e-4 of the roof threshold
     (y = 0.5), so the storage cannot move one between roofs and walls.
3. `test_main_scene_buildings.gd`: 4/5 tests, 27/28 asserts.
   `test_without_terrain_and_buildings_the_panel_names_both` fails with `Unexpected
   Errors: [1] <push_error>BuildingChunks: …/case_5/manifest.json: no buildings have been
   built: …`. With terrain and buildings both null, TerrainGrid and BuildingChunks each log
   their refusal once (as the brief says: each reader logs its own), and GUT's
   `assert_push_error(text)` marks exactly one matching push_error handled per call
   (`test.gd:2258-2263`), so the second fails the test. Every other assert of the test
   passes (the panel names "the terrain and the buildings" and both commands).

Why it is blocked: the brief needs the live copies byte-identical to the pinned ones and
the gate green. Only design can change the pinned tests.

Question: may the pinned copies take these corrections (six lines; the diff below), or is
there another answer? With them, measured against `e926a15` in a scratch copy of the
project: `test_building_chunks.gd` 10/10 tests (101 asserts), `test_building_loader.gd`
5/5 (823), `test_main_scene_buildings.gd` 5/5 (28); the whole suite 20 scripts, 98 tests,
2'692 asserts, all passed; each of the brief's three mutations fails the named test
(Findings, item 6). gdlint and gdformat pass on the corrected copies.

```
test_building_chunks.gd: func _set(key …  → func _set_key(key …, and its two calls
test_building_loader.gd:135  after tool.begin(Mesh.PRIMITIVE_TRIANGLES):
                                 tool.set_smooth_group(-1)
test_building_loader.gd:147  Vector3.ONE * 1e-5  →  Vector3.ONE * 1e-4
test_building_loader.gd:167  if n.is_equal_approx(Vector3.UP):  →
                             if n.distance_to(Vector3.UP) < 1e-4:
test_main_scene_buildings.gd:237  assert_push_error(path, "the refusals are logged, …") →
    assert_push_error("TerrainGrid: " + path, "the terrain's refusal is logged")
    assert_push_error("BuildingChunks: " + path, "the buildings' refusal is logged")
```

(A test that ever reads the real village's normals back would need more than 1e-4: the
measured worst is 1.04e-4.)

State: everything else in the brief is done and committed at `e926a15`: the reader, the
loader, the materials, main.gd, the live main-scene tests on a complete world, export.sh
(passes with the real village, both startup lines), the screenshots. While the pinned
copies are out, the gate cannot see the seam: each of the brief's three mutations passes
the full gate at that commit (measured, Findings item 6). Closing the brief once the
pinned copies are fixed: copy them in, `cmp`; add two scoped allowlist entries,
`BuildingChunks: user://test_ @ res://tests/test_building_chunks.gd` and the same `@
res://tests/test_main_scene_buildings.gd` (their deliberate refusals print 8 and 3 ERROR
lines, measured; the TerrainGrid line is already excepted globally); run the gate; commit;
re-run the three mutations on the live gate; tick the first, second and last gates; DONE.
The brief's Findings has the rest.
