"""Tests for brief v0.5.0-12: the render step's words claim what its checks compare.

Pinned decisions (brief v0.5.0-12, decision 1; M3 round R2 P-03 and the 0.3.1 residue R1-05;
lesson 44): the render step reads the water class only, so no word of it says it checks "the
surface classes":
- no render script under game/tests/render/ and not tools/gate.sh says "surface classes" or
  "the classes land";
- tools/gate.sh's render paragraph (the header's paragraph that starts "# The render step runs
  last") names "the water class" and "whether the crowns are drawn" (the trees' drawn check of
  brief v0.5.0-12), and says "Of the classes only the water is checked" (Hard Rule 2);
- the comment above RENDER_TIMEOUT names the photo's script "the photo and the water class";
- render_photo.gd no longer says the water's tolerance includes "the light's highlight" (the
  check switches the highlight off).

Does NOT prove: what the checks compare (their own result lines and the brief's mutation rows
do); any word but these; the SKIPPED line (test_gate_render.py pins it whole). A census proves
text, never behaviour (lesson 5).

The render scripts are exactly the five named here, by design: a brief that adds a render script
adds it to this census, so that its words are read too (a deliberate tripwire, not an accident).
"""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GATE = REPO / "tools" / "gate.sh"
RENDER_DIR = REPO / "game" / "tests" / "render"
SCRIPTS = (
    "render_common.gd",
    "render_photo.gd",
    "render_lift.gd",
    "render_flow.gd",
    "render_trees.gd",
)


def _render_files():
    return [GATE] + [RENDER_DIR / name for name in SCRIPTS]


def _render_paragraph():
    lines = GATE.read_text(encoding="utf-8").splitlines()
    start = next(
        i for i, line in enumerate(lines) if line.startswith("# The render step runs last")
    )
    paragraph = []
    for line in lines[start:]:
        if not line.startswith("#") or line.strip() == "#":
            break
        paragraph.append(line[1:].strip())
    return " ".join(paragraph)


def _comment_above(marker):
    lines = GATE.read_text(encoding="utf-8").splitlines()
    end = next(i for i, line in enumerate(lines) if line.startswith(marker))
    start = end
    while start > 0 and lines[start - 1].startswith("#"):
        start -= 1
    return " ".join(line[1:].strip() for line in lines[start:end])


def test_the_files_read_are_there():
    """The census reads the five render scripts and the gate, or it proves nothing."""
    missing = [str(path) for path in _render_files() if not path.is_file()]
    assert missing == []
    assert sorted(p.name for p in RENDER_DIR.glob("render_*.gd")) == sorted(SCRIPTS)


def test_no_render_word_claims_the_surface_classes():
    for path in _render_files():
        text = " ".join(path.read_text(encoding="utf-8").replace("#", " ").split())
        assert "surface classes" not in text.lower(), f"{path.name} says 'surface classes'"
        assert "the classes land" not in text.lower(), f"{path.name} says 'the classes land'"


def test_the_gate_s_render_paragraph_names_the_water_class_and_the_crowns_drawn():
    paragraph = _render_paragraph()
    assert len(paragraph) > 400, paragraph
    assert "the water class" in paragraph, paragraph
    assert "whether the crowns are drawn" in paragraph, paragraph


def test_the_gate_s_render_paragraph_says_only_the_water_class_is_checked():
    assert "Of the classes only the water is checked" in _render_paragraph()


def test_the_comment_above_the_render_timeout_names_the_water_class():
    comment = _comment_above("RENDER_TIMEOUT=")
    assert "four scripts" in comment, comment
    assert "the photo and the water class" in comment, comment


def test_the_water_s_tolerance_does_not_claim_the_highlight():
    text = (RENDER_DIR / "render_photo.gd").read_text(encoding="utf-8")
    assert "highlight on roughness 0.3 included" not in text
    assert "light_specular = 0.0" in text
