"""Gaps found in brief v0.5.0-09 (F1): tools/gate.sh's header must not claim that a shifted
flow read is gated. The flow check cannot see a north-south shift of where the flow is read
(brief decision 5), so the header says so (Hard Rule 2: a comment never claims what the code
does not do).

Does NOT prove: that the render check really misses such a shift (the brief's mutation rows).
"""

import re
from pathlib import Path

GATE = Path(__file__).resolve().parents[2] / "tools" / "gate.sh"


def _header() -> str:
    lines = []
    for line in GATE.read_text(encoding="utf-8").splitlines():
        if not line.startswith("#"):
            break
        lines.append(line.lstrip("#").strip())
    return re.sub(r"\s+", " ", " ".join(lines))


def test_header_states_the_flow_checks_north_south_blind_spot():
    text = _header()
    assert "does not see where the flow is read from north to south" in text
    assert "not gated" in text
