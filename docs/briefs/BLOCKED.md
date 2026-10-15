# BLOCKED — questions from executor sessions

Plain text, newest first. An executor that hits genuine ambiguity writes its question
here, marks its brief `Status: BLOCKED`, and takes the next OPEN brief — it never invents
the answer. Check `docs/history/RULINGS.md` BEFORE filing: a question it already answers
is answered, not filed. Answered blocks move to `docs/history/blocked/` (DESIGN.md rule 3).

## Open

### 2026-10-15 · M3 R1 · P-03 · does the gate run a software render of the shaders' placement? (fix brief M3-R1-fix-3, not written until design answers)

Filed by the orchestrator. The placement lens (`docs/reviews/M3-R1-placement.md`, P-03, P2,
Tier 1) shows that no gate runs the shaders that place the photo, the surface classes and the
tree crowns' colour: six placements of them (the photo's v flipped, shifted by 0.1 m, the
class grid half a texel off or flipped, the surface texture flipped against its class bytes,
the tree shader's photo lookup swapped) leave the full pytest and GUT green, and the first
also leaves the whole `tools/gate.sh` at exit 0. A software render (Compatibility, Mesa
llvmpipe under Xvfb, 19 s, the lens's `render_check.gd`) tells each apart by number.

Why it is blocked: BUILD.md rule 2b records, by design, that "renders / looks right" cannot be
gated in a container and that the brief's "does NOT prove" line is the accepted answer;
CLAUDE.md's gate paragraph says the same. The lens argues that where an image lies on the
ground is a number, not a look. A gate step that runs `xvfb-run` would change the standard
gate (a new tool dependency, a skip or a refusal where it is missing) and that recorded
exception. That is design's, not the build's.

Options. (a) The gate gains the render step (`render_check.gd` and its tree version; asserts
a correlation at least 0.95 and above every flipped or shifted alternative, and a water mask
best shift of 0), refusing where `xvfb-run` is missing unless a named variable skips it with a
printed line; BUILD.md rule 2b and CLAUDE.md's "what the gate cannot see" are amended to say
which claims a software render gates. (b) The gate stays as it is and the placement
expressions of the three shaders are pinned by substring, as line 375 of `terrain_photo.
gdshader` is today (weaker, lesson 5: a census proves text).

State: the part that needs no answer goes to fix brief M3-R1-fix-1 (a test that the surface
texture's bytes equal the class bytes, and the placement expressions pinned by substring as
the interim); nothing else of it moves until design answers.

### 2026-10-15 · M3 R1 · P-01 · the trees on a terrain at 1 m or 2 m (fix brief M3-R1-fix-2, not written until design answers)

Filed by the orchestrator. The placement lens (`docs/reviews/M3-R1-placement.md`, P-01, P2,
Tier 1) shows that a tree's y is taken from the 0.5 m terrain grid whatever
`config/terrain.json`'s spacing, as SPEC §8 item 7 says ("whatever the terrain config's
spacing"), while SPEC §7 and §8 promise that 1 or 2 m "is a config change and a pipeline
re-run, no code change". Measured in the real village, `spacing_m` set to 1.0 and the
`terrain` and `manifest` commands re-run (both exit 0, no panel): 3'542 of the 34'412 trees
stand more than 5 cm off Terrain3D's ground (worst 1.05 m); at 2.0, 18'932 (worst 4.39 m).

Why it is blocked: both ways out are design's. (a) Honouring the SPEC's promise: the trees
step reads `spacing_m` from the terrain config and takes y by bilinear interpolation of the
grid at that spacing, with the spacing in the trees' `computed_for` and expected chunk
SHA-256s per spacing in `config/trees.json` as `config/terrain.json` holds for the terrain:
those expected values are design's data (the build computing them from its own code would
copy the code under test). (b) Making the harm refuse: `build_trees` and `built_trees_block`
refuse a terrain config whose spacing is not 0.5, naming `config/terrain.json`, and SPEC §7
and §8 are changed to say that the trees tie the terrain to 0.5 m: that changes a design
promise.

State: nothing of it is built. The placement round cannot be clean (the plan: no P2 or above)
until one is chosen and built.
