"""Pinning tests for brief M3-01 (M2-04's check): fiona is imported only where a FileGDB is read.

Pinned decisions (docs/SPEC.md §4, fiona from M2-04; §8 *Reading*; brief M3-01): fiona,
and the GDAL its wheel bundles, is imported only inside the function that reads a FileGDB
(`buildings.read_sheet` today; a swissTLM3D reader of a later step alike), never when a
module is imported: importing every module of the `mattini` package, whatever modules it
holds then, and running a command that reads no FileGDB (`manifest` here), leave it
unimported. Harm prevented: a fiona that cannot load (its Windows wheel bundles GDAL DLLs
of its own, the M2 review) would stop every command, the terrain's and the manifest's
too, though only the buildings read a sheet. Each run is a fresh interpreter, so no
earlier import hides the answer; the positive control reads the committed real sample,
which must import it.

Does NOT prove: that fiona loads on the owner's Windows PC (only a run there does).
"""

import json
import subprocess
import sys

from mattini.world import REPO

SAMPLE = (
    REPO
    / "tests"
    / "shared"
    / "buildings_sample"
    / "swissbuildings3d_3_0_2020_1328-33_2056_5728.gdb.zip"
)
DRIVER = """
import json, sys

def fiona_modules():
    return sorted(m for m in sys.modules if m == "fiona" or m.startswith("fiona."))

import importlib, pkgutil
import mattini
modules = sorted(m.name for m in pkgutil.walk_packages(mattini.__path__, "mattini."))
for name in modules:
    importlib.import_module(name)
seen = {"modules": modules, "imported": fiona_modules()}
mattini.manifest.write_manifest(sys.argv[1])
seen["manifest"] = fiona_modules()
mattini.buildings.read_sheet(open(sys.argv[2], "rb").read(), "1328-33")
seen["read_sheet"] = fiona_modules()
print(json.dumps(seen))
"""


def test_fiona_is_imported_only_when_a_sheet_is_read(tmp_path):
    done = subprocess.run(  # the exit status is checked below
        [sys.executable, "-c", DRIVER, str(tmp_path / "generated"), str(SAMPLE)],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        timeout=120,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    seen = json.loads(done.stdout.splitlines()[-1])
    assert {"mattini.__main__", "mattini.buildings", "mattini.manifest"} <= set(seen["modules"])
    assert seen["imported"] == [], "importing the pipeline's modules imports fiona"
    assert seen["manifest"] == [], "`manifest`, which reads no sheet, imports fiona"
    assert "fiona" in seen["read_sheet"], "reading a sheet must import it (positive control)"
