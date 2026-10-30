"""The mutation rows of brief v0.5.0-09, as the session's finalizer ran them (2026-10-30).

python3 -I docs/briefs/sketches/v0.5.0/v0.5.0-09-mutate.py N   applies row N to the working tree
(run from the repository's root, the throwaway gate.sh in place; each edit must match exactly
once). Rows 1 to 14, 20 and 21 edit the shader and are read by RENDER-F; rows 15 to 19 edit
tools/gate.sh and are read by PY-R (16 and 19 by RENDER-F too). The rows' meaning, the checks
that fail and the harm are in the brief and in v0.5.0-09-PINSPEC.md. A builder's code may read
otherwise: the brief's table names the mistake, not these lines.
"""

import sys
from pathlib import Path

SHADER = "game/shaders/terrain_photo.gdshader"
GATE = "tools/gate.sh"
LOOKUP = (
    "\t\tvec4 t = texture(water_flow, (xz - surfaces_rect.xy) / surfaces_rect.zw);\n"
)
FLOW = "\t\tvec2 flow = (t.rg * 255.0 - 128.0) / 127.0 * t.b;\n"
RIPPLE = "\t\tvec2 ripple = (w0 * (na0.xy + nb0.xy) + w1 * (na1.xy + nb1.xy)) * water_normal_strength;\n"
SPEEDS = "uniform float water_speed_a = 0.8;\nuniform float water_speed_b = 0.5;\n"


def turned(c: str, s: str) -> str:
    return (
        f"\t\tvec2 flow = mat2(vec2({c}, {s}), vec2(-{s}, {c})) * "
        "((t.rg * 255.0 - 128.0) / 127.0 * t.b);\n"
    )


def speeds(a: str, b: str) -> str:
    return f"uniform float water_speed_a = {a};\nuniform float water_speed_b = {b};\n"


def lookup(uv: str) -> str:
    return (
        "\t\tvec2 fuv = (xz - surfaces_rect.xy) / surfaces_rect.zw;\n"
        f"\t\tvec4 t = texture(water_flow, {uv});\n"
    )


ROWS = {
    1: [
        (SHADER, "(xz - p0 * da)", "(xz + p0 * da)"),
        (SHADER, "(xz - p1 * da)", "(xz + p1 * da)"),
        (SHADER, "(xz - p0 * db)", "(xz + p0 * db)"),
        (SHADER, "(xz - p1 * db)", "(xz + p1 * db)"),
    ],
    2: [(SHADER, FLOW, FLOW.replace("t.rg", "t.gr"))],
    3: [(SHADER, FLOW, "\t\tvec2 flow = vec2(0.515, -0.857);\n")],
    4: [(SHADER, FLOW, turned("0.0", "1.0"))],
    5: [(SHADER, FLOW, turned("0.98481", "0.17365"))],
    6: [(SHADER, FLOW, FLOW.replace("* t.b;", "* t.b * vec2(-1.0, 1.0);"))],
    7: [(SHADER, FLOW, FLOW.replace("* t.b;", "* t.b * vec2(1.0, -1.0);"))],
    8: [
        (
            SHADER,
            "\t\tfloat p0 = fract(TIME / water_phase_s + water_phase(xz));\n",
            "\t\tfloat p0 = fract(water_phase(xz));\n",
        )
    ],
    9: [(SHADER, LOOKUP, LOOKUP.replace("surfaces_rect", "photo_rect"))],
    10: [(SHADER, SPEEDS, speeds("1.6", "1.0"))],
    11: [
        (
            SHADER,
            "uniform float water_normal_strength = 0.35;\n",
            "uniform float water_normal_strength = 0.0;\n",
        )
    ],
    12: [
        (
            SHADER,
            RIPPLE,
            "\t\tvec2 ripple = (na0.xy + nb0.xy) * water_normal_strength;\n",
        )
    ],
    13: [(SHADER, SPEEDS, speeds("0.4", "0.25"))],
    14: [(SHADER, FLOW, turned("0.99452", "0.10453"))],
    15: [
        (
            GATE,
            "\trender_script res://tests/render/render_flow.gd flow || return 1\n",
            "",
        )
    ],
    16: [(GATE, ' --fixed-fps "$RENDER_FPS"', "")],
    17: [
        (
            GATE,
            "the crowns' colour land and which way the ripples drift are not checked\"",
            "the crowns' colour land is not checked\"",
        )
    ],
    18: [
        (
            GATE,
            "\trender_script res://tests/render/render_flow.gd flow || return 1\n",
            "",
        ),
        (
            GATE,
            "\trender_script res://tests/render/render_trees.gd trees\n",
            (
                "\trender_script res://tests/render/render_trees.gd trees || return 1\n"
                "\trender_script res://tests/render/render_flow.gd flow\n"
            ),
        ),
    ],
    19: [(GATE, "RENDER_FPS=60\n", "RENDER_FPS=30\n")],
    # The session's finalizer (the checker's P2): where the flow is read, mirrored.
    20: [(SHADER, LOOKUP, lookup("vec2(fuv.x, 1.0 - fuv.y)"))],
    21: [(SHADER, LOOKUP, lookup("vec2(1.0 - fuv.x, fuv.y)"))],
}


def main() -> None:
    for path, old, new in ROWS[int(sys.argv[1])]:
        file = Path(path)
        text = file.read_text(encoding="utf-8")
        if text.count(old) != 1:
            sys.exit(f"{path}: {old!r} found {text.count(old)} times, not once")
        file.write_text(text.replace(old, new), encoding="utf-8")


if __name__ == "__main__":
    main()
