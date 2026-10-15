"""config/datasets.json: the swisstopo datasets, their pinned editions and attribution.

docs/SPEC.md §5. Every dataset names its STAC collection, the credit it requires and
exactly one of `edition` and `editions`; the pipeline never asks for "the latest" edition
(Hard Rule 5), so an edition is pinned: `edition` is a year (`2024`) or, as the national
products are named, a year and month (`2026-02`, the month 01 to 12), and `editions` is a
non-empty list of distinct years in ascending order, the editions a tile may be published
in (swissSURFACE3D: exactly one per tile, brief M3-03). A dataset the pipeline reads at a
resolution (`RESOLUTION_DATASETS`) must name it, `resolution_m`, a positive number of metres:
every command that reads the config would otherwise end in a KeyError (briefs M3-01 and
M3-03, M2 V1-P-05). The loader refuses a malformed config with a DatasetsConfigError whose
message names the file and the dataset (Hard Rule 2).
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

from mattini.world import REPO

DEFAULT_PATH = REPO / "config" / "datasets.json"

SCHEMA = 1
TOP_LEVEL_KEYS = {"schema", "terms", "datasets"}
REQUIRED_KEYS = ("collection", "attribution")
YEAR = re.compile(r"[0-9]{4}")
EDITION = re.compile(r"[0-9]{4}(?:-(?:0[1-9]|1[0-2]))?")  # a year, or a year and month 01-12
# the datasets whose entry must carry `resolution_m`
RESOLUTION_DATASETS = ("swissalti3d", "swissimage", "swisssurface3d")


class DatasetsConfigError(ValueError):
    """config/datasets.json is missing, malformed, or does not pin an edition."""


def load_datasets(path: Path | str = DEFAULT_PATH) -> dict:
    """The `datasets` object of a datasets config, validated; errors name the file."""
    path = Path(path)

    def fail(message: str) -> DatasetsConfigError:
        return DatasetsConfigError(f"{path}: {message}")

    try:
        data = json.loads(path.read_bytes().decode("utf-8"))
    except OSError as exc:
        raise fail(f"cannot read the datasets config: {exc}") from exc
    except (UnicodeDecodeError, ValueError) as exc:
        raise fail(f"not valid JSON: {exc}") from exc

    if not isinstance(data, dict) or set(data) != TOP_LEVEL_KEYS:
        raise fail(f"the top level must have exactly the keys {sorted(TOP_LEVEL_KEYS)}")
    if type(data["schema"]) is not int or data["schema"] != SCHEMA:
        raise fail(f"schema must be {SCHEMA}, found {data['schema']!r}")
    datasets = data["datasets"]
    if not isinstance(datasets, dict):
        raise fail("datasets must be an object")
    for name, dataset in datasets.items():
        if not isinstance(dataset, dict):
            raise fail(f"dataset {name!r} must be an object")
        for key in REQUIRED_KEYS:
            value = dataset.get(key)
            if not isinstance(value, str) or not value:
                raise fail(f"dataset {name!r}: {key} must be a non-empty string, found {value!r}")
        if ("edition" in dataset) == ("editions" in dataset):
            raise fail(
                f"dataset {name!r}: exactly one of edition and editions must be given, "
                f"found {'both' if 'edition' in dataset else 'neither'}"
            )
        if "edition" in dataset:
            edition = dataset["edition"]
            if not isinstance(edition, str) or not edition:
                raise fail(
                    f"dataset {name!r}: edition must be a non-empty string, found {edition!r}"
                )
            if not EDITION.fullmatch(edition):
                raise fail(
                    f"dataset {name!r}: edition must be a pinned year like '2024' or a year "
                    f"and month like '2026-02', found {edition!r}"
                )
        else:
            _check_editions(name, dataset["editions"], fail)
        if name in RESOLUTION_DATASETS:
            resolution = dataset.get("resolution_m")
            if type(resolution) not in (int, float) or not (
                math.isfinite(resolution) and resolution > 0
            ):
                raise fail(
                    f"dataset {name!r}: resolution_m must be a positive number of metres, "
                    f"found {resolution!r}"
                )
    return datasets


def _check_editions(name: str, editions: object, fail) -> None:
    """Refuse `editions` unless it is a non-empty list of distinct years, ascending."""
    if (
        not isinstance(editions, list)
        or not editions
        or not all(isinstance(year, str) and YEAR.fullmatch(year) for year in editions)
    ):
        raise fail(
            f"dataset {name!r}: editions must be a non-empty list of pinned years like "
            f"'2021', found {editions!r}"
        )
    if editions != sorted(set(editions)):
        raise fail(
            f"dataset {name!r}: editions must be distinct years in ascending order, "
            f"found {editions!r}"
        )
