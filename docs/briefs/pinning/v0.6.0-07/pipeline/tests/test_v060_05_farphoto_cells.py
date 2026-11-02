"""Pinning tests for brief v0.6.0-05: the dataset `swissimage_far` and its cells (design §2).

Pinned decisions:

- `config/datasets.json` names `swissimage_far`: collection `ch.swisstopo.swissimage-dop10`,
  edition `2023`, `resolution_m` 2 (an integer: swisstopo writes the asset `..._2_2056.tif`),
  attribution `© swisstopo`; `resolution_m` is required for it as for the other datasets read
  at a resolution (`datasets.RESOLUTION_DATASETS`).
- Its cells are every 1 km cell (named `<E km>-<N km>` by its south-west corner, as the photo's
  tiles) that meets the surroundings box: the area's box grown by `margin_m` on every side,
  [e_min − m, e_max + m) × [n_min − m, n_max + m), the box itself with no half-spacing
  border (design §2; swissALTIRegio's tiles have one, brief v0.6.0-01). East outer, north
  inner, the order of the lock, the download and provenance.json.
  `download.farphoto_cells(world, area, *, margin_m)` is the rule; `lock.fit_problem(...,
  "swissimage_far", surroundings=<the config>)` asks it with the area's `margin_m` in the
  surroundings config it is given (re-cut by brief v0.6.0-07: `download.area_farphoto_cells`
  and `download.surroundings_settings` are gone; the config's one reader is
  `surroundings.load_surroundings_config`), so a config with another margin asks for other
  cells; the spacing is not read for the cells.
- The village with the committed margin 20'000: 42 × 43 = 1806 cells, E 2603 … 2644, N 1075 …
  1117 (design §0, measured).

Likeliest wrong twins, each caught here: the half-spacing border taken over from the regio
rule (a ring of cells too many); north outer; the margin hard-coded; a box edge off the km
grid rounded the wrong way.

Does NOT prove: which of the cells have an item (the lock's tests and the measured test).
"""

import json

import pytest

from mattini import download, lock, surroundings
from mattini.datasets import RESOLUTION_DATASETS, DatasetsConfigError, load_datasets
from mattini.world import REPO, load_world

COMMITTED_CONFIG = REPO / "config" / "surroundings.json"


def _config(tmp_path, **settings):
    data = json.loads(COMMITTED_CONFIG.read_text(encoding="utf-8"))
    data["areas"]["village"].update(settings)
    path = tmp_path / "surroundings.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def test_the_committed_config_names_swissimage_far():
    entry = load_datasets()["swissimage_far"]
    assert entry == {
        "collection": "ch.swisstopo.swissimage-dop10",
        "edition": "2023",
        "resolution_m": 2,
        "attribution": "© swisstopo",
    }
    assert type(entry["resolution_m"]) is int
    assert "swissimage_far" in RESOLUTION_DATASETS
    assert download.FARPHOTO == "swissimage_far"


@pytest.mark.parametrize("value", ["missing", 0, -2, "2", None])
def test_swissimage_far_needs_a_resolution(tmp_path, value):
    data = json.loads((REPO / "config" / "datasets.json").read_text(encoding="utf-8"))
    if value == "missing":
        del data["datasets"]["swissimage_far"]["resolution_m"]
    else:
        data["datasets"]["swissimage_far"]["resolution_m"] = value
    path = tmp_path / "datasets.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(DatasetsConfigError) as refusal:
        load_datasets(path)
    assert "swissimage_far" in str(refusal.value) and "resolution_m" in str(refusal.value)


def test_the_village_needs_the_1806_measured_cells():
    cells = download.farphoto_cells(load_world(), "village", margin_m=20_000)
    assert len(cells) == 1806
    assert cells[0] == "2603-1075" and cells[1] == "2603-1076" and cells[42] == "2603-1117"
    assert cells[43] == "2604-1075" and cells[-1] == "2644-1117"
    assert cells == [f"{e}-{n}" for e in range(2603, 2645) for n in range(1075, 1118)]


def test_no_half_spacing_border_and_no_ring():
    cells = set(download.farphoto_cells(load_world(), "village", margin_m=20_000))
    for outside in ("2602-1090", "2645-1090", "2620-1074", "2620-1118"):
        assert outside not in cells, outside


@pytest.mark.parametrize(
    "margin_m, east, north",
    [
        (0, range(2623, 2625), range(1095, 1098)),  # the area's own six cells
        (1000, range(2622, 2626), range(1094, 1099)),
        (
            500,
            range(2622, 2626),
            range(1094, 1099),
        ),  # edges off the km grid: the cells met
        (1, range(2622, 2626), range(1094, 1099)),
        (999, range(2622, 2626), range(1094, 1099)),
    ],
)
def test_the_cells_meet_the_grown_box(margin_m, east, north):
    cells = download.farphoto_cells(load_world(), "village", margin_m=margin_m)
    assert cells == [f"{e}-{n}" for e in east for n in north]


def _fit(lock_data: dict, world, config: dict):
    return lock.fit_problem(
        lock_data, load_datasets(), world, "village", "swissimage_far", surroundings=config
    )


def _lock_for(cells: list[str]) -> dict:
    """A lock whose swissimage_far entry pins exactly `cells` (none absent)."""
    data = json.loads((REPO / "config" / "datasets.lock.json").read_bytes())
    entry = data["datasets"]["swissimage_far"]
    entry["absent"] = []
    entry["tiles"] = {c: {"file": f"{c}.tif", "sha256": "0" * 64} for c in cells}
    return data


def test_the_fit_asks_for_the_cells_of_the_config_s_margin(tmp_path):
    """The fit takes the margin from the config it is given (brief v0.6.0-07): the committed
    config's 1806 cells for the committed lock; a config with margin 1000 asks for 20."""
    world = load_world()
    committed = surroundings.load_surroundings_config(COMMITTED_CONFIG)
    committed_lock = json.loads((REPO / "config" / "datasets.lock.json").read_bytes())
    assert _fit(committed_lock, world, committed) is None
    narrow = surroundings.load_surroundings_config(_config(tmp_path, margin_m=1000))
    cells = [f"{e}-{n}" for e in range(2622, 2626) for n in range(1094, 1099)]
    assert _fit(_lock_for(cells), world, narrow) is None
    assert _fit(committed_lock, world, narrow) is not None
    assert _fit(_lock_for(cells), world, committed) is not None


def test_the_spacing_does_not_change_the_cells(tmp_path):
    world = load_world()
    cells = [f"{e}-{n}" for e in range(2622, 2626) for n in range(1094, 1099)]
    wide = surroundings.load_surroundings_config(_config(tmp_path, margin_m=1000, spacing_m=500))
    assert len(cells) == 20 and _fit(_lock_for(cells), world, wide) is None


def test_a_config_the_reader_refuses_is_its_error(tmp_path):
    path = _config(tmp_path, margin_m=-1)
    with pytest.raises(surroundings.SurroundingsError) as refusal:
        surroundings.load_surroundings_config(path)
    assert str(path) in str(refusal.value) and "margin_m" in str(refusal.value)
