"""The mutation rows of brief v0.5.0-04, as the pin author ran them on the throwaway (2026-10-30).

python3 -I docs/briefs/sketches/v0.5.0/v0.5.0-04-mutate.py N   applies row N to the working tree
(run from the repository's root; each edit must match exactly once). The rows' meaning, the
tests that fail and the harm are in the brief and in v0.5.0-04-PINSPEC.md. A builder's code may
read otherwise: the brief's table names the mistake, not these lines.
"""

import sys
from pathlib import Path

SHADER = "game/shaders/terrain_photo.gdshader"
LOADER = "game/scripts/terrain/terrain_loader.gd"
GATE = "tools/gate.sh"
WORLD = "game/tests/complete_world.gd"
MUV = "\tvec2 muv = (v_vertex.xz - capture_shadow_rect.xy) / capture_shadow_rect.zw;\n"
SAMPLE = "\tfloat m = texture(capture_shadow, muv).r;\n"
LIFT = "\talbedo = min(albedo * (1.0 + (shadow_lift - 1.0) * m), vec3(1.0));\n"
DECL = (
    "uniform sampler2D capture_shadow : hint_default_black, filter_linear_mipmap_anisotropic, "
    "repeat_disable;\n"
)
ZERO = (
    "\tif (any(lessThan(muv, vec2(0.0))) || any(greaterThan(muv, vec2(1.0)))) {\n"
    "\t\tm = 0.0;\n\t}\n"
)


def sample(uv: str) -> str:
    return f"\tfloat m = texture(capture_shadow, {uv}).r;\n"


ROWS = {
    # the loader
    1: [
        (
            LOADER,
            "\t\t_set_capture_shadow(material, shadows)\n",
            (
                "\t\t_set_capture_shadow(material, shadows)\n"
                '\t\tmaterial.set_shader_param("capture_shadow_rect", photo.rect())\n'
            ),
        )
    ],
    2: [
        (
            LOADER,
            '\t\tmaterial.set_shader_param("capture_shadow", ImageTexture.create_from_image(none))\n',
            "",
        )
    ],
    3: [(LOADER, "PackedByteArray([0]))", "PackedByteArray([255]))")],
    # the declarations
    4: [(SHADER, DECL, DECL.replace("hint_default_black", "source_color"))],
    5: [(SHADER, DECL, DECL.replace("hint_default_black, ", ""))],
    6: [
        (
            SHADER,
            DECL,
            DECL.replace("filter_linear_mipmap_anisotropic", "filter_nearest"),
        )
    ],
    7: [
        (
            SHADER,
            DECL,
            DECL.replace("filter_linear_mipmap_anisotropic", "filter_linear"),
        )
    ],
    8: [
        (SHADER, "uniform float shadow_lift = 3.0;", "uniform float shadow_lift = 2.0;")
    ],
    # the placement (Hard Rule 4)
    9: [(SHADER, MUV, MUV.replace("capture_shadow_rect", "photo_rect"))],
    10: [(SHADER, SAMPLE, sample("muv - 0.5 / vec2(textureSize(capture_shadow, 0))"))],
    11: [(SHADER, SAMPLE, sample("vec2(muv.x, 1.0 - muv.y)"))],
    12: [(SHADER, SAMPLE, sample("vec2(1.0 - muv.x, muv.y)"))],
    13: [(SHADER, SAMPLE, sample("muv.yx"))],
    14: [
        (SHADER, MUV, MUV.replace("v_vertex.xz - ", "v_vertex.xz - vec2(0.1, 0.0) - "))
    ],
    15: [(SHADER, MUV, MUV + "\tmuv.y = 1.0 - muv.y;\n")],
    16: [(SHADER, ZERO, "")],
    # the rule
    17: [(SHADER, LIFT, LIFT.replace("min(", "(").replace(", vec3(1.0))", ")"))],
    18: [
        (SHADER, LIFT, ""),
        (
            SHADER,
            "\tif (!flat_terrain_normals) {\n\t\tNORMAL = mat3(VIEW_MATRIX) * normalize(n + bump);",
            LIFT
            + "\tif (!flat_terrain_normals) {\n\t\tNORMAL = mat3(VIEW_MATRIX) * normalize(n + bump);",
        ),
    ],
    19: [
        (
            SHADER,
            LIFT,
            "\talbedo = pow(albedo, vec3(1.0 / 2.2));\n"
            + LIFT
            + "\talbedo = pow(albedo, vec3(2.2));\n",
        )
    ],
    20: [
        (
            SHADER,
            "uniform sampler2D photo : source_color, filter_linear_mipmap_anisotropic",
            "uniform sampler2D photo : filter_linear_mipmap_anisotropic",
        )
    ],
    # the seams
    21: [
        (
            GATE,
            "\trender_script res://tests/render/render_lift.gd lift || return 1\n",
            "",
        )
    ],
    22: [
        (
            WORLD,
            (
                '\tmanifest["shadows"] = _moved_description(SHADOWS_FIXTURE, dir, SHADOWS_BOX, '
                "world_sha256)\n"
            ),
            "",
        )
    ],
    # the water, kept (v0.4.0-03's row 1: the drift's sign)
    23: [
        (SHADER, "vec2 ua0 = (xz - p0 * da)", "vec2 ua0 = (xz + p0 * da)"),
        (SHADER, "vec2 ua1 = (xz - p1 * da)", "vec2 ua1 = (xz + p1 * da)"),
        (SHADER, "vec2 ub0 = (xz - p0 * db)", "vec2 ub0 = (xz + p0 * db)"),
        (SHADER, "vec2 ub1 = (xz - p1 * db)", "vec2 ub1 = (xz + p1 * db)"),
    ],
    # the mask handed only with the classes (the release's checkers, 2026-10-30)
    24: [
        (
            LOADER,
            "\t\t_set_capture_shadow(material, shadows)\n\t\tif surfaces != null:\n",
            "\t\tif surfaces != null:\n\t\t\t_set_capture_shadow(material, shadows)\n",
        )
    ],
}


def main() -> None:
    for path, old, new in ROWS[int(sys.argv[1])]:
        text = Path(path).read_text(encoding="utf-8")
        if text.count(old) != 1:
            sys.exit(f"{path}: {old!r} found {text.count(old)} times")
        Path(path).write_text(text.replace(old, new), encoding="utf-8")


if __name__ == "__main__":
    main()
