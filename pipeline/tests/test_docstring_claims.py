"""Pinning tests for brief M3-01 (M2 V1-P-04, M2-06 Findings 9): what two kinds of docstring say.

Pinned decisions (lesson 42, a fixture's words are claims too; Hard Rule 2, a comment never
claims what the code does not do):
- A test file a docstring or comment names exists. Every `test_<name>.py` or
  `test_<name>.gd` named in a docstring or a comment of the pipeline's code and tests, the
  game's scripts and tests and tools/*.sh, and every bare `(test_<name>)` in parentheses
  there, is a file under pipeline/tests/ or game/tests/ (a bare name may also be a test
  function defined there). The review found two docstrings sending the reader to a
  `test_expected_inputs_steps` that never existed. Code and strings are not read: a test
  may name the files of a scratch tree it writes.
- `manifest.py`'s docstring lists the terrain block's shape checks among its refusals: the
  box, the columns and the rows that are not the world config's area at the spacing
  (M2-06's `_check_shape`). It listed every other refusal; only the terrain block has
  columns and rows, so those two words are the test.

Does NOT prove: that the named file holds what the docstring says it does, or that the
manifest's sentence is right beyond naming those three (a census proves text, lesson 5:
the review reads the sentences); a test file named without its suffix and outside
parentheses, or in a comment after code on a GDScript or shell line.
"""

import ast
import io
import re
import tokenize
from pathlib import Path

import mattini.manifest

REPO = Path(__file__).resolve().parents[2]
FOLDERS = ("pipeline/mattini", "pipeline/tests", "game/scripts", "game/tests", "tools")
NAMED_FILE = re.compile(r"\btest_[a-z0-9_]+\.(?:py|gd)\b")
NAMED_IN_PARENTHESES = re.compile(r"\((test_[a-z0-9_]+)\)")
DEFINED = re.compile(r"^\s*(?:def|func)\s+(test_[a-z0-9_]+)\s*\(", re.MULTILINE)


def python_words(text: str) -> list[tuple[int, str]]:
    """(line, text) of every docstring line and every comment of a Python source."""
    found = []
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            first = node.body[0] if node.body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                lines = first.value.value.splitlines()
                found.extend((first.lineno + n, line) for n, line in enumerate(lines))
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type == tokenize.COMMENT:
            found.append((token.start[0], token.string))
    return found


def comment_lines(text: str) -> list[tuple[int, str]]:
    """(line, text) of every line of a GDScript or shell source that is a comment."""
    lines = enumerate(text.splitlines(), start=1)
    return [(n, line) for n, line in lines if line.lstrip().startswith("#")]


def _sources():
    for folder in FOLDERS:
        for path in sorted((REPO / folder).rglob("*")):
            source = path.suffix in {".py", ".gd", ".sh"} and "__pycache__" not in path.parts
            if source and path.is_file():
                yield path, path.read_text(encoding="utf-8")


def _test_files() -> set[str]:
    return {p.name for p in (REPO / "pipeline" / "tests").glob("test_*.py")} | {
        p.name for p in (REPO / "game" / "tests").rglob("test_*.gd")
    }


def missing_names(rel: str, words, files: set[str], defined: set[str]) -> list[str]:
    modules = {Path(name).stem for name in files}
    missing = []
    for number, line in words:
        for name in NAMED_FILE.findall(line):
            if name not in files:
                missing.append(f"{rel}:{number}: {name}")
        for name in NAMED_IN_PARENTHESES.findall(line):
            if name not in modules and name not in defined:
                missing.append(f"{rel}:{number}: ({name})")
    return missing


def test_every_test_file_a_docstring_names_exists():
    files, sources = _test_files(), list(_sources())
    defined = {name for _, text in sources for name in DEFINED.findall(text)}
    missing = []
    for path, text in sources:
        words = python_words(text) if path.suffix == ".py" else comment_lines(text)
        missing += missing_names(path.relative_to(REPO).as_posix(), words, files, defined)
    assert missing == [], missing


def test_the_census_sees_a_name_that_is_missing():
    """Positive control: a docstring, a comment and a GDScript comment naming a file that
    does not exist are found; the same names in code and strings are not read."""
    never = "test_never_" + "written"  # split, so that the census does not find it here
    source = (
        f'"""See {never}.py."""\n\n\ndef f():\n    """And ({never})."""\n'
        f'    return "{never}.gd"  # and {never}.gd\n'
    )
    found = missing_names("x.py", python_words(source), _test_files(), set())
    assert found == [f"x.py:1: {never}.py", f"x.py:5: ({never})", f"x.py:6: {never}.gd"]
    gd = f'## See {never}.gd\nvar a := "{never}.gd"\n'
    assert missing_names("x.gd", comment_lines(gd), _test_files(), set()) == [f"x.gd:1: {never}.gd"]
    assert (
        missing_names("x.py", [(1, "see (test_world) and test_world.py")], _test_files(), set())
        == []
    )


def test_the_manifest_docstring_names_the_terrain_shape_checks():
    """Only the terrain block has columns and rows; the box is named for both blocks."""
    doc = mattini.manifest.__doc__
    for word in ("box", "columns", "rows"):
        assert word in doc, (word, doc)
