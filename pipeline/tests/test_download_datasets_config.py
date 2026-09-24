"""config/datasets.json is read and validated by `load_datasets` (brief M0-04; SPEC §5).

A malformed config, or one that does not pin an edition (Hard Rule 5: never "the latest"),
is refused with a DatasetsConfigError naming the file (Hard Rule 2).
"""

import json
import re

import pytest

from mattini.datasets import DatasetsConfigError, load_datasets
from mattini.world import REPO

CONFIG = REPO / "config" / "datasets.json"


def _mutated(tmp_path, mutate):
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    mutate(data)
    path = tmp_path / "datasets.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def test_the_committed_config_loads_verbatim():
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert load_datasets() == data["datasets"]
    assert load_datasets(CONFIG) == data["datasets"]


def _set(key, value):
    def mutate(data):
        data["datasets"]["swissalti3d"][key] = value

    return mutate


def _drop(key):
    def mutate(data):
        del data["datasets"]["swissalti3d"][key]

    return mutate


@pytest.mark.parametrize(
    ("mutate", "complaint"),
    [
        (_set("edition", "latest"), "pinned year"),
        (_set("edition", "current"), "pinned year"),
        (_set("edition", "20245"), "pinned year"),
        (_set("edition", 2024), "non-empty string"),
        (_set("edition", ""), "non-empty string"),
        (_drop("edition"), "non-empty string"),
        (_set("attribution", ""), "non-empty string"),
        (_drop("attribution"), "non-empty string"),
        (_set("collection", None), "non-empty string"),
        (lambda data: data.update(schema=2), "schema must be 1"),
        (lambda data: data.update(schema=True), "schema must be 1"),
        (lambda data: data.update(extra=1), "top level"),
        (lambda data: data.pop("terms"), "top level"),
        (lambda data: data.update(datasets=[]), "datasets must be an object"),
        (lambda data: data["datasets"].update(swissalti3d="2024"), "must be an object"),
    ],
)
def test_a_malformed_config_is_refused_with_the_file_named(tmp_path, mutate, complaint):
    path = _mutated(tmp_path, mutate)
    with pytest.raises(DatasetsConfigError, match=re.escape(complaint)) as caught:
        load_datasets(path)
    assert str(path) in str(caught.value)


@pytest.mark.parametrize("raw", [b"", b"{", b"\xff\xfe", b"[]"])
def test_unparseable_config_is_refused_with_the_file_named(tmp_path, raw):
    path = tmp_path / "datasets.json"
    path.write_bytes(raw)
    with pytest.raises(DatasetsConfigError, match=re.escape(str(path))):
        load_datasets(path)


def test_a_missing_config_is_refused_with_the_file_named(tmp_path):
    path = tmp_path / "absent.json"
    with pytest.raises(DatasetsConfigError, match=re.escape(str(path))):
        load_datasets(path)
