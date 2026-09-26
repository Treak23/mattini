# A real swissBUILDINGS3D sheet, as a test fixture

`swissbuildings3d_3_0_2020_1328-33_2056_5728.gdb.zip` is swisstopo's own file, unchanged:
swissBUILDINGS3D 3.0, edition 2020, map sheet 1328-33 (three buildings north-west of the
village box), 45'668 bytes, SHA-256
`72b2502856d315b9f265f8279a9491cfa3f45065a42cc492824fd9731d7c4292`, from the STAC item
`swissbuildings3d_3_0_2020_1328-33` of the collection `ch.swisstopo.swissbuildings3d_3_0`.

© swisstopo. Used under swisstopo's terms of use for free geodata (OGD), which allow
redistribution with the source named (docs/SPEC.md §5).

It is here because only a real file holds an Esri MultiPatch, the geometry the buildings
reader must read, and GDAL cannot write one (docs/SPEC.md §8). It is the one file of raw
geodata in git, by the owner's word of 2026-09-25 (docs/SPEC.md §13 row 24; brief M2-09);
`pipeline/tests/test_repo_hygiene.py` names it with its SHA-256 and refuses any other.
