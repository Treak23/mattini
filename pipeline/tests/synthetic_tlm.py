"""A synthetic swissTLM3D for the surfaces step's tests (brief M3-06).

`zipped_tlm` writes features in the reader's form ({"uuid", "attributes", "geometry"},
coordinates in whole millimetres) into a FileGDB with fiona's OpenFileGDB driver, on
swisstopo's own storage grid (XYSCALE 1000 and the origins of the 2026-02 edition, read
from its GDB_Items: then every E and N reads back within 1.9e-9 m of the 1 mm grid, as
swisstopo's do; GDAL's default grid reads back up to 2.4e-7 m off it, measured), and zips
the folder the way swisstopo's file is zipped: one `.gdb` folder whose member names use
backslashes, whatever the system (zipfile would turn a Windows separator into "/", so the
names are set on the ZipInfo directly). Polygon rings keep the orientation they are given;
GDAL's writer turns them to Esri's (outer clockwise, holes counter-clockwise), which is
how swisstopo's read, so the shared fixture holds them so (measured).

Does NOT prove: that swisstopo's own file reads the same way (design read the real file
with the same reader: tests/shared/surfaces_vectors.json and config/surfaces.json).
"""

import zipfile
from pathlib import Path

import fiona
from fiona.crs import CRS

SWISSTOPO_GRID = {
    "XORIGIN": "-27386400",
    "YORIGIN": "-32067900",
    "XYSCALE": "1000",
    "ZORIGIN": "-100000",
    "ZSCALE": "1000",
    "XYTOLERANCE": "0.01",
    "ZTOLERANCE": "0.01",
}
SCHEMAS = {
    "TLM_BODENBEDECKUNG": ("3D MultiPolygon", {"UUID": "str:38", "OBJEKTART": "int32"}),
    "TLM_FLIESSGEWAESSER": (
        "3D MultiLineString",
        {"UUID": "str:38", "OBJEKTART": "int32", "VERLAUF": "int32"},
    ),
    "TLM_STRASSE": (
        "3D MultiLineString",
        {"UUID": "str:38", "OBJEKTART": "int32", "BELAGSART": "int32", "KUNSTBAUTE": "int32"},
    ),
}


def _metres(coordinates, height: float, shift_m: float):
    """Integer-mm coordinates (any nesting) as (E, N, H) in metres; E moved by `shift_m`."""
    if isinstance(coordinates[0], int):
        return (coordinates[0] / 1000 + shift_m, coordinates[1] / 1000, height)
    return [_metres(item, height, shift_m) for item in coordinates]


def zipped_tlm(
    folder: Path,
    layers: dict,
    *,
    zip_name: str = "swisstlm3d_test_2056_5728.gdb.zip",
    gdb: str = "swissTLM3D_test_LV95_LN02.gdb",
    nudge: tuple[str, float] | None = None,
    xy_scale: int = 1000,
) -> Path:
    """Write `layers` ({layer: [feature]}) as a zipped FileGDB in `folder`; return its path.

    `nudge` = (uuid, metres) moves every E of that feature by the given amount, to put it
    off the 1 mm grid; that needs a finer storage grid than swisstopo's (`xy_scale` 10000,
    0.1 mm), which would otherwise round the nudge away. Each feature gets its own height;
    the reader drops heights.
    """
    target = folder / gdb
    for layer, features in sorted(layers.items()):
        geometry, properties = SCHEMAS[layer]
        with fiona.open(
            target,
            "w",
            driver="OpenFileGDB",
            schema={"geometry": geometry, "properties": properties},
            crs=CRS.from_epsg(2056),
            layer=layer,
            **{**SWISSTOPO_GRID, "XYSCALE": str(xy_scale)},
        ) as dst:
            for number, feature in enumerate(features):
                shift = nudge[1] if nudge and nudge[0] == feature["uuid"] else 0.0
                dst.write(
                    {
                        "geometry": {
                            "type": feature["geometry"]["type"],
                            "coordinates": _metres(
                                feature["geometry"]["coordinates"], 1500.0 + number, shift
                            ),
                        },
                        "properties": {"UUID": feature["uuid"], **feature["attributes"]},
                    }
                )
    path = folder / zip_name
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for member in sorted(target.iterdir()):
            info = zipfile.ZipInfo("member")
            info.filename = f"{gdb}\\{member.name}"  # swisstopo's separator, on every system
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, member.read_bytes())
    return path
