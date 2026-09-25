"""Synthetic swissBUILDINGS3D map sheets for the buildings step's tests (brief M2-04).

A sheet is a zipped FileGDB that fiona writes, layer `Building_solid`, EPSG:2056, with
the attributes the reader uses (UUID, OBJEKTART). Its geometries are MultiPolygon Z, one
triangle per polygon, not the Esri MultiPatch swisstopo's files hold: GDAL cannot write a
MultiPatch (measured at M2 planning). `raw_folder` lays sheets out as `download buildings`
leaves them (the zips and provenance.json) and returns the lock that pins them.

Does NOT prove: that swisstopo's own MultiPatch reads the same way (the real run, checked
against design's chunk hashes, does).
"""

import hashlib
import io
import json
import zipfile
from pathlib import Path

import fiona
from fiona.crs import CRS

from mattini.download import BUILDINGS

ZIP_NAME = "swissbuildings3d_3_0_{edition}_{sheet}_2056_5728.gdb.zip"


def sheet_zip(
    folder: Path, features: list[dict], gdb: str = "synthetic.gdb", layer: str = "Building_solid"
) -> bytes:
    """The bytes of a zipped FileGDB holding `features` ({"uuid", "objektart", "triangles"}).

    Each of a feature's faces is written as one polygon whose ring is its points closed by
    the first again: a triangle's three points make the four-point ring the reader wants,
    four points a quad it refuses.
    """
    path = Path(folder) / gdb
    schema = {
        "geometry": "3D MultiPolygon",
        "properties": {"UUID": "str:50", "OBJEKTART": "str:25"},
    }
    with fiona.open(
        path,
        "w",
        driver="OpenFileGDB",
        schema=schema,
        crs=CRS.from_epsg(2056),
        layer=layer,
    ) as dst:
        for feature in features:
            rings = [[list(p) for p in face] + [list(face[0])] for face in feature["triangles"]]
            dst.write(
                {
                    "geometry": {"type": "MultiPolygon", "coordinates": [[r] for r in rings]},
                    "properties": {"UUID": feature["uuid"], "OBJEKTART": feature["objektart"]},
                }
            )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for file in sorted(path.iterdir()):
            archive.write(file, f"{gdb}/{file.name}")
    return buffer.getvalue()


def raw_folder(raw_root: Path, datasets: dict, sheets: dict[str, bytes]) -> dict:
    """Lay the zips of `sheets` (sheet id -> bytes) and provenance.json out as the download
    does, under `<raw_root>/swissbuildings3d/<edition>/`; return the lock pinning them."""
    dataset = datasets[BUILDINGS]
    edition = dataset["edition"]
    out = Path(raw_root) / BUILDINGS / edition
    out.mkdir(parents=True, exist_ok=True)
    entries, pinned = [], {}
    for sheet in sorted(sheets):
        name = ZIP_NAME.format(edition=edition, sheet=sheet)
        (out / name).write_bytes(sheets[sheet])
        sha256 = hashlib.sha256(sheets[sheet]).hexdigest()
        entries.append(
            {
                "file": name,
                "item": f"swissbuildings3d_3_0_{edition}_{sheet}",
                "sha256": sha256,
                "sheet": sheet,
                "size_bytes": len(sheets[sheet]),
                "url": f"https://example.invalid/{name}",
            }
        )
        pinned[sheet] = {"file": name, "sha256": sha256}
    provenance = {
        "attribution": dataset["attribution"],
        "collection": dataset["collection"],
        "dataset": BUILDINGS,
        "edition": edition,
        "schema": 1,
        "sheets": entries,
    }
    (out / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    return {
        "schema": 1,
        "datasets": {
            BUILDINGS: {
                "collection": dataset["collection"],
                "edition": edition,
                "sheets": pinned,
            }
        },
    }
