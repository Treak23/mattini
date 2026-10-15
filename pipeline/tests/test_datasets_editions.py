"""Pinning tests for brief M3-03: the datasets config's editions (docs/SPEC.md §5).

Pinned decisions: config/datasets.json holds five datasets: swissALTI3D 2024 and
swissBUILDINGS3D 2020 unchanged, SWISSIMAGE 10 cm 2023 (`swissimage`), the swissSURFACE3D
raster in 2021 or 2022 per tile (`swisssurface3d`) and swissTLM3D 2026-02 (`swisstlm3d`),
each `© swisstopo`. A dataset names its STAC collection, its attribution and exactly one of
`edition` (a pinned year `YYYY`, or a year and month `YYYY-MM` with the month 01 to 12,
as the national products are named) or `editions` (a non-empty list of distinct years in
ascending order: the editions a tile may be published in, exactly one per tile). Never
"the latest" (Hard Rule 5). Anything else is a DatasetsConfigError naming the file and the
dataset, with both and neither refused as "exactly one of edition and editions".

Likeliest wrong twins, each caught here: a loader that reads `edition` and ignores a stray
`editions` (both given); one that accepts any `[0-9]{4}-[0-9]{2}` (month 13); one that
checks the order but not distinctness (a repeated year), or distinctness but not the order;
one that accepts a month in `editions`.

Does NOT prove: that the editions exist at swisstopo (the lock's tests and the builder's
live run do).
"""

import copy
import json
import re

import pytest

from mattini.datasets import DatasetsConfigError, load_datasets
from mattini.world import REPO

CONFIG = REPO / "config" / "datasets.json"
EXPECTED = {
    "swissalti3d": {
        "attribution": "© swisstopo",
        "collection": "ch.swisstopo.swissalti3d",
        "edition": "2024",
        "resolution_m": 0.5,
    },
    "swissbuildings3d": {
        "attribution": "© swisstopo",
        "collection": "ch.swisstopo.swissbuildings3d_3_0",
        "edition": "2020",
    },
    "swissimage": {
        "attribution": "© swisstopo",
        "collection": "ch.swisstopo.swissimage-dop10",
        "edition": "2023",
        "resolution_m": 0.1,
    },
    "swisssurface3d": {
        "attribution": "© swisstopo",
        "collection": "ch.swisstopo.swisssurface3d-raster",
        "editions": ["2021", "2022"],
        "resolution_m": 0.5,
    },
    "swisstlm3d": {
        "attribution": "© swisstopo",
        "collection": "ch.swisstopo.swisstlm3d",
        "edition": "2026-02",
    },
}


def _write(tmp_path, datasets):
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    data["datasets"] = datasets
    path = tmp_path / "datasets.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def _with(name, **changes):
    """The expected datasets with `name` changed: a value of None removes the key."""
    datasets = copy.deepcopy(EXPECTED)
    for key, value in changes.items():
        if value is None:
            datasets[name].pop(key, None)
        else:
            datasets[name][key] = value
    return datasets


def test_the_committed_config_holds_the_five_datasets():
    assert load_datasets() == EXPECTED
    raw = CONFIG.read_bytes()
    assert raw.endswith(b"}\n") and b"\r" not in raw


@pytest.mark.parametrize(
    ("name", "changes"),
    [
        ("swisstlm3d", {"edition": "2026-12"}),
        ("swisstlm3d", {"edition": "2026-01"}),
        ("swissimage", {"edition": "2019"}),
        ("swisssurface3d", {"editions": ["2021"]}),
        ("swisssurface3d", {"editions": ["2017", "2019", "2023"]}),
    ],
    ids=[
        "year-month-december",
        "year-month-january",
        "another-year",
        "one-edition-list",
        "three-editions",
    ],
)
def test_the_accepted_shapes_load_verbatim(tmp_path, name, changes):
    datasets = _with(name, **changes)
    assert load_datasets(_write(tmp_path, datasets)) == datasets


@pytest.mark.parametrize(
    ("name", "changes", "complaint"),
    [
        ("swisssurface3d", {"edition": "2021"}, "exactly one of edition and editions"),
        ("swisstlm3d", {"editions": ["2026"]}, "exactly one of edition and editions"),
        ("swisstlm3d", {"edition": None}, "exactly one of edition and editions"),
        ("swisssurface3d", {"editions": None}, "exactly one of edition and editions"),
        ("swisstlm3d", {"edition": "2026-13"}, "edition"),
        ("swisstlm3d", {"edition": "2026-00"}, "edition"),
        ("swisstlm3d", {"edition": "2026-2"}, "edition"),
        ("swisstlm3d", {"edition": "2026-02-24"}, "edition"),
        ("swisstlm3d", {"edition": "202602"}, "edition"),
        ("swisstlm3d", {"edition": "latest"}, "edition"),
        ("swisssurface3d", {"editions": []}, "editions"),
        ("swisssurface3d", {"editions": ["2022", "2021"]}, "editions"),
        ("swisssurface3d", {"editions": ["2021", "2021"]}, "editions"),
        ("swisssurface3d", {"editions": ["2021", "2022", "2022"]}, "editions"),
        ("swisssurface3d", {"editions": ["2021", 2022]}, "editions"),
        ("swisssurface3d", {"editions": "2021"}, "editions"),
        ("swisssurface3d", {"editions": ["2021", "2026-02"]}, "editions"),
        ("swisssurface3d", {"editions": ["21"]}, "editions"),
        ("swisssurface3d", {"editions": ["latest"]}, "editions"),
    ],
    ids=[
        "both-given",
        "both-given-tlm",
        "neither-tlm",
        "neither-surface",
        "month-13",
        "month-00",
        "month-one-digit",
        "a-date",
        "no-dash",
        "latest",
        "empty-list",
        "descending",
        "repeated",
        "repeated-at-the-end",
        "not-a-string",
        "a-string-not-a-list",
        "a-month-in-editions",
        "two-digit-year",
        "latest-in-editions",
    ],
)
def test_other_shapes_are_refused_naming_the_file_and_the_dataset(
    tmp_path, name, changes, complaint
):
    path = _write(tmp_path, _with(name, **changes))
    with pytest.raises(DatasetsConfigError) as refused:
        load_datasets(path)
    message = str(refused.value)
    assert message.startswith(f"{path}: "), message
    assert f"dataset {name!r}" in message, message
    assert re.search(re.escape(complaint), message), message
