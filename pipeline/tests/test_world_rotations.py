"""Every signed axis mapping: the 24 rotations are accepted, the 24 mirrors refused.

Complements the pinned tests (brief M0-02), which try one mirror; here the loader meets
all 48 signed permutations of (e, n, h) onto (x, y, z), and every accepted mapping must
keep the world right-handed and round-trip exactly.
"""

import itertools
import json
import re
from pathlib import Path

import pytest

from mattini.world import WorldConfigError, load_world

REPO = Path(__file__).resolve().parents[2]
CONFIG = REPO / "config" / "world.json"


def _mappings():
    for perm in itertools.permutations("enh"):
        for signs in itertools.product("+-", repeat=3):
            yield {axis: sign + src for axis, sign, src in zip("xyz", signs, perm, strict=True)}


def _parity(perm: tuple[str, ...]) -> int:
    inversions = sum(1 for i, j in itertools.combinations(range(3), 2) if perm[i] > perm[j])
    return -1 if inversions % 2 else 1


def _is_rotation(axes: dict[str, str]) -> bool:
    order = tuple("enh".index(axes[a][1]) for a in "xyz")
    sign = 1
    for a in "xyz":
        sign *= -1 if axes[a][0] == "-" else 1
    return sign * _parity(order) == 1


def _config_with(tmp_path, axes):
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    data["axes"] = axes
    path = tmp_path / "world.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def test_there_are_24_rotations_and_24_mirrors():
    kinds = [_is_rotation(m) for m in _mappings()]
    assert (kinds.count(True), kinds.count(False)) == (24, 24)


@pytest.mark.parametrize("axes", list(_mappings()), ids=lambda m: ",".join(m.values()))
def test_rotations_accepted_mirrors_refused(tmp_path, axes):
    path = _config_with(tmp_path, axes)
    if not _is_rotation(axes):
        with pytest.raises(WorldConfigError, match=re.escape(str(path))):
            load_world(path)
        return
    world = load_world(path)
    o = (world.origin_e, world.origin_n, 0.0)
    base = world.to_local(*o)

    def step(de, dn, dh):
        moved = world.to_local(o[0] + de, o[1] + dn, o[2] + dh)
        return tuple(m - b for b, m in zip(base, moved, strict=True))

    east, north, up = step(1.0, 0.0, 0.0), step(0.0, 1.0, 0.0), step(0.0, 0.0, 1.0)
    assert _cross(east, north) == up  # east x north = up survives the mapping
    for axis, spec in axes.items():  # and each game axis reads the source axis it names
        unit = {"e": east, "n": north, "h": up}[spec[1]]
        assert unit["xyz".index(axis)] == (1.0 if spec[0] == "+" else -1.0)
    point = (2623825.13, 1096489.77, 1606.37)
    assert world.to_lv95(*world.to_local(*point)) == pytest.approx(point, abs=1e-9)
