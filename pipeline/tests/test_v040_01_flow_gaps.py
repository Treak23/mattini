"""Three guards of brief v0.4.0-01's flow grid that no pinned test failed without (the
mutation prover's findings X28, X14 and X21; the session widened the brief's Scope by this
file). Each guard is in the code; each test below fails when its guard is removed:

- X28: the step encodes the flow's PNG with `png_l8(flow, FLOW_CODES)`, the flow's own bound
  (240), not the classes' default or 255: a flow holding a code above 240 is refused by the
  step, naming the bound, before anything is written.
- X14: `built_surfaces_block` compares the built flow's pixels' SHA-256 with the description's
  `flow.pixels_sha256`: a description that lies about its pixels is refused, though the pixels
  are design's and the PNG's bytes match `flow.sha256`.
- X21: `built_surfaces_block` compares `flow.cell_m`, `flow.columns` and `flow.rows` by value
  and by type, as the classes' block does (brief decision 9, "by value and type"): `2` for `2.0`
  and `20.0` for `20` are refused though they are equal.

The fixture and the helpers are test_surfaces_flow.py's; every expected value is derived from
the fixture's designed flow and the module's constants.

Does NOT prove: that `flow.encoding` and `flow.file` are typed (their values are pinned in
test_surfaces_flow.py; a non-string cannot equal them), that the mutation prover's other
rows are caught, or that anything renders. The real village's flow is the step's own
comparison on a real run.
"""

import hashlib
import json

import numpy as np
import pytest
from test_surfaces_flow import GENERATED, REBUILD, _build, _built, _case, _check, _rewrite

from mattini import surfaces
from mattini.surfaces import FLOW_CODES, SurfacesError


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _designed_flow() -> np.ndarray:
    return surfaces.read_png_l8((GENERATED / "surfaces" / "fixture-flow.png").read_bytes())


def test_the_step_refuses_a_flow_with_a_code_above_the_flow_s_bound(tmp_path, monkeypatch):
    too_high = _designed_flow().copy()
    too_high[0, 0] = FLOW_CODES + 1
    monkeypatch.setattr(surfaces, "flow_grid", lambda *args: too_high)
    case = _case(tmp_path)
    # the pixels' comparison must pass so that the step reaches the PNG's encoder, whose
    # bound is under test: a config expecting this very flow is the one way there
    case.config["areas"]["fixture"]["expected_flow_pixels_sha256"] = _sha(too_high.tobytes())
    with pytest.raises(SurfacesError, match=f"0 to {FLOW_CODES}, found {FLOW_CODES + 1}"):
        _build(case)
    assert not case.out.exists(), "refused before anything is written"


def test_a_description_that_misstates_its_flow_pixels_is_refused_though_the_png_is_designs(
    tmp_path,
):
    out = _built(tmp_path)
    designed = json.loads((out / "surfaces" / "fixture.json").read_text(encoding="utf-8"))
    liar = _sha(b"not the flow's pixels")
    assert liar != designed["flow"]["pixels_sha256"]
    _rewrite(out, lambda block: block["flow"].update(pixels_sha256=liar))
    with pytest.raises(SurfacesError, match=r"flow\.pixels_sha256") as refusal:
        _check(out)
    assert liar in str(refusal.value)
    assert REBUILD in str(refusal.value)


def _swapped_type(value):
    """The same number as the other numeric type: 2.0 as 2, 20 as 20.0."""
    assert float(value) == value
    return int(value) if isinstance(value, float) else float(value)


@pytest.mark.parametrize("key", ["cell_m", "columns", "rows"])
def test_a_flow_number_of_the_other_numeric_type_is_refused_though_equal(tmp_path, key):
    out = _built(tmp_path)
    designed = json.loads((out / "surfaces" / "fixture.json").read_text(encoding="utf-8"))
    value = designed["flow"][key]
    other = _swapped_type(value)
    assert other == value and type(other) is not type(value)
    _rewrite(out, lambda block: block["flow"].update({key: other}))
    with pytest.raises(SurfacesError, match=rf"flow\.{key} is") as refusal:
        _check(out)
    assert REBUILD in str(refusal.value)
