"""config/datasets.json: the swisstopo datasets, their pinned editions and attribution.

docs/SPEC.md §5. Every dataset names its STAC collection, a pinned edition and the credit
it requires; the pipeline never asks for "the latest" edition (Hard Rule 5), so an edition
must be a year. A dataset the pipeline reads at a resolution (`RESOLUTION_DATASETS`:
swissALTI3D) must name it, `resolution_m`, a positive number of metres: every command that
reads the config would otherwise end in a KeyError (brief M3-01, M2 V1-P-05). The loader
refuses a malformed config with a DatasetsConfigError whose message names the file (Hard
Rule 2).
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
REQUIRED_KEYS = ("collection", "edition", "attribution")
EDITION = re.compile(r"[0-9]{4}")
RESOLUTION_DATASETS = ("swissalti3d",)  # the datasets whose entry must carry `resolution_m`


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
        if not EDITION.fullmatch(dataset["edition"]):
            raise fail(
                f"dataset {name!r}: edition must be a pinned year like '2024', "
                f"found {dataset['edition']!r}"
            )
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
