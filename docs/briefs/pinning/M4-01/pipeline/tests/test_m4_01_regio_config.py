"""Pinning tests for brief M4-01: swissALTIRegio in config/datasets.json (m4-design §1, §1a).

Pinned decisions:

- `swissaltiregio`: collection `ch.swisstopo.swissaltiregio`, edition `2026-06` (the items'
  `properties.datetime` 2026-06-01T00:00:00Z, measured 2026-10-17: the item ids carry no
  edition), `resolution_m` 10 (an integer, as the lock copies it), and `attribution` the
  product page's source text for the 2025 and later versions, verbatim as design corrected
  it (m4-design §1a: the stray quote after `dl-de/by-2-0` and "tétéchargées" are typos),
  one line, the sentences joined by single spaces. The credits print it whole. Its terms:
  OGD, "a reference to the source is mandatory".
- `resolution_m` is required for swissaltiregio as for the other datasets read at a
  resolution (`datasets.RESOLUTION_DATASETS`), refused naming the file and the dataset.

Does NOT prove: that the credits show the text (the manifest and the game, wave 2).
"""

import json

import pytest

from mattini.datasets import DatasetsConfigError, load_datasets
from mattini.world import REPO

CONFIG = REPO / "config" / "datasets.json"
SOURCE_TEXT = (
    "Bundesamt für Landestopografie swisstopo; Tarquini S., I. Isola, M. Favalli, "
    "A. Battistini, G. Dotta (2023). TINITALY, a digital elevation model of Italy with a 10 "
    "meters cell size (Version 1.1). Istituto Nazionale di Geofisica e Vulcanologia (INGV). "
    "https://doi.org/10.13127/tinitaly/1.1; DGM Österreich, geoland.at; DGM1, Bayerische "
    "Vermessungsverwaltung – www.geodaten.bayern.de; DGM1, Baden-Württemberg: LGL, "
    "www.lgl-bw.de, dl-de/by-2-0; RGEAlti, Institut National de l'information géographique "
    "et forestière, données originales téléchargées sur "
    "https://geoservices.ign.fr/rgealti#telechargement5m, mise à jour du juillet 2023"
)


def test_the_committed_config_holds_swissaltiregio_as_measured():
    datasets = load_datasets(CONFIG)
    assert datasets["swissaltiregio"] == {
        "collection": "ch.swisstopo.swissaltiregio",
        "edition": "2026-06",
        "resolution_m": 10,
        "attribution": SOURCE_TEXT,
    }
    assert type(datasets["swissaltiregio"]["resolution_m"]) is int
    assert set(datasets) == {
        "swissaltiregio",
        "swissalti3d",
        "swissbuildings3d",
        "swissimage",
        "swisssurface3d",
        "swisstlm3d",
    }


def test_the_source_text_is_the_corrected_one():
    assert "tétéchargées" not in SOURCE_TEXT and 'by-2-0"' not in SOURCE_TEXT
    assert "\n" not in SOURCE_TEXT and "  " not in SOURCE_TEXT


@pytest.mark.parametrize("value", ["missing", 0, -10, "10", None])
def test_swissaltiregio_needs_a_resolution(tmp_path, value):
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    if value == "missing":
        del data["datasets"]["swissaltiregio"]["resolution_m"]
    else:
        data["datasets"]["swissaltiregio"]["resolution_m"] = value
    path = tmp_path / "datasets.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(DatasetsConfigError) as refusal:
        load_datasets(path)
    assert str(path) in str(refusal.value) and "'swissaltiregio'" in str(refusal.value)
    assert "resolution_m" in str(refusal.value)
