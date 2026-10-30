"""The mutation rows of brief v0.5.0-10 (rows 1 to 13), on the throwaway's download.py.

python3 -I docs/briefs/sketches/v0.5.0/v0.5.0-10-mutate.py N   applies row N (from the repository's
root); undo it with `git apply -R` of the row's saved diff, or by restoring the file. Rows 1 to 6,
12 and 13 match the rehearsal's throwaway shape (a CutTransfer class, `length`, `written`, `cut`);
a builder's own shape needs its own edit of the same meaning.
"""
import sys
from pathlib import Path

D = "pipeline/mattini/download.py"
CHECK = "    if length is not None and length.isdigit() and written < int(length):\n"
ROWS = {
    1: [(D, CHECK + '        raise CutTransfer(f"cut at {written} of {int(length)} bytes")\n', "")],
    2: [(D, "class CutTransfer(OSError):", "class CutTransfer(RuntimeError):")],
    3: [(D, 'run the command again" if cut else ""', 'run the command again"')],
    4: [(D, 'run the command again" if cut else ""', 'run the command again" if False else ""')],
    5: [(D, 'problem, cut = f"fetch failed: {exc}", isinstance(exc, CutTransfer)',
         'problem, cut = f"fetch failed: {exc}", cut or isinstance(exc, CutTransfer)')],
    6: [(D, 'f"cut at {written} of {int(length)} bytes"', 'f"cut at {int(length)} of {written} bytes"')],
    7: [("pipeline/mattini/datasets.py",
         'RESOLUTION_DATASETS = ("swissalti3d", "swissimage", "swisssurface3d")',
         'RESOLUTION_DATASETS = ("swissalti3d",)')],
    8: [("pipeline/mattini/datasets.py",
         "            if type(resolution) not in (int, float) or not (\n"
         "                math.isfinite(resolution) and resolution > 0\n"
         "            ):",
         "            if type(resolution) not in (int, float) or not (resolution > 0):")],
    9: [("pipeline/mattini/roofs.py",
         "    problem = _inputs_refusal(computed_for, lock)\n"
         "    if problem:\n"
         '        raise RoofsError(f"area {area!r}: {problem}")\n'
         "\n"
         '    raw_dir = Path(raw_root) / BUILDINGS / buildings["edition"]\n'
         "    listed = _provenance_sheets(raw_dir / PROVENANCE, buildings, sheets)\n",
         '    raw_dir = Path(raw_root) / BUILDINGS / buildings["edition"]\n'
         "    listed = _provenance_sheets(raw_dir / PROVENANCE, buildings, sheets)\n"
         "    problem = _inputs_refusal(computed_for, lock)\n"
         "    if problem:\n"
         '        raise RoofsError(f"area {area!r}: {problem}")\n')],
    10: [("pipeline/mattini/surfaces.py",
          "            for key, value in expected.items():\n"
          "                if not (isinstance(value, str) and SHA256_HEX.fullmatch(value)):",
          "            for key, value in expected.items():\n"
          '                if not (isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40,64}", value)):')],
    11: [("pipeline/mattini/surfaces.py",
          "            for key, value in expected.items():\n"
          "                if not (isinstance(value, str) and SHA256_HEX.fullmatch(value)):",
          "            for key, value in expected.items():\n"
          "                if not (isinstance(value, str) and SHA256_HEX.match(value)):")],
    # the checker's rows (2026-10-30): an answer of no announced length taken for a cut
    12: [(D, CHECK + '        raise CutTransfer(f"cut at {written} of {int(length)} bytes")\n',
          "    if length is None or not length.isdigit() or written < int(length):\n"
          '        raise CutTransfer(f"cut at {written} of {length} bytes")\n')],
    13: [(D, CHECK, "    if length is not None and written < int(length):\n")],
}
for path, old, new in ROWS[int(sys.argv[1])]:
    text = Path(path).read_text(encoding="utf-8")
    if text.count(old) != 1:
        sys.exit(f"{path}: {old!r} found {text.count(old)} times")
    Path(path).write_text(text.replace(old, new), encoding="utf-8")
