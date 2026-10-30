"""Pinning tests for brief v0.5.0-13 (R1-06, G-05): tools/export.sh's refusals from step 4 on.

Pinned decisions (brief v0.5.0-13; the go of 2026-10-29, answer A: "the export's refusals (R1-06,
G-05)"):
- R1-06 (a): the stand-in pack tool (fake_tools.py) refuses what game/tools/pack.gd refuses, with
  its words: a folder that does not exist, that holds a folder, or that holds no file to pack
  (`pack: <problem>` on stderr, exit 1, no pack); it packs the names pack.gd packs and writes
  PCKPacker's bytes (the SHA-256 below was measured from pack.gd on Godot 4.6.3). Through
  tools/export.sh, a packed folder pack.gd refuses fails step 4b naming the folder, and step 4c is
  not reached. The stand-in used to pack an empty folder into an empty pack, and the export passed
  where a real one fails.
- R1-06 (b): once step 4 has begun (its first act is to delete build/linux), every refusal ends
  with the line UNFINISHED, once; a refusal before step 4 does not say it and leaves build/ as it
  was; a finished export does not say it. The line is on stderr. Every refusal exits 1, and
  every run, refused or not, leaves no scratch folder (TMPDIR) behind.
- G-05: step 5 lists every file under build/ and fails naming each one over 100 MiB
  (104'857'600 bytes) in sort order, and only those; a file of exactly 100 MiB passes. Step 4c
  fails, listing both build folders, on a generated file absent from its pack and on one whose
  pack holds it with one byte changed (its size the same, so a size-only check passes it).

The script under test is the repository's own, run on stand-ins (fake_tools.py). A file over the
limit is a sparse file under build/stray/ (step 4 replaces only build/linux and build/windows).

Does NOT prove: that a real export or pack tool fails this way (the release gate's export run,
docs/RELEASE.md §C, and the pin author's probe of pack.gd); that the owner reads the line before
shipping; GitHub's actual limit; the Windows build.
"""

import hashlib
import json
import platform
import subprocess
import sys

import fake_tools
import pytest

pytestmark = pytest.mark.skipif(
    fake_tools.BASH is None or platform.system() != "Linux",
    reason="tools/export.sh runs on Linux with bash",
)

DONE = "== export: done in"
UNFINISHED = "export: build/ is unfinished, do not ship it"
LIMIT = 104857600  # 100 MiB, GitHub's file limit (docs/RELEASE.md §C)
PHOTO = "res://assets/generated/photo"
# pack.gd's pack of the folder _noisy_folder writes, measured on Godot 4.6.3 (pin author,
# 2026-10-30): 332 bytes.
PACK_SHA256 = "4ba23169b5a92adcb5efa73b0e1105e4a2f168de7ac5e1afcfa97f605acef04c"


def _tree(tmp_path):
    templates = tmp_path / "xdg" / "godot" / "export_templates" / "4.6.3.stable"
    return fake_tools.export_tree(tmp_path, templates)


def _run(tmp_path, root, lines=fake_tools.STARTUP_LINES, **kwargs):
    return fake_tools.run_export(tmp_path, root, fake_tools.start_output(lines), **kwargs)


def _lines(done):
    return [line for line in done.stdout.splitlines() if line.strip()]


def _sparse(path, size):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as file:
        file.truncate(size)


def _generated(root):
    return root / "game" / "assets" / "generated"


# ---------------------------------------------------------------- R1-06 (a): the pack stand-in


def _noisy_folder(game):
    """A packed folder with two files pack.gd packs and four names it leaves out."""
    folder = game / "assets" / "generated" / "photo"
    (folder / ".hidden").mkdir(parents=True)
    (folder / "b.bin").write_bytes(b"second\n")
    (folder / "a.bin").write_bytes(b"first\n")
    (folder / "c.bin.part").write_bytes(b"part")
    (folder / "c.bin.import").write_bytes(b"imp")
    (folder / ".e").write_bytes(b"h")
    (folder / ".hidden" / "g").write_bytes(b"g")
    return folder


def _pack_tool(tmp_path, game, folder=PHOTO):
    out = tmp_path / "out.pck"
    done = subprocess.run(  # the test checks the status
        [sys.executable, fake_tools.__file__, "pack", str(out), str(game), folder],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    return done, out


def _refused_folder(game, case):
    folder = game / "assets" / "generated" / "photo"
    if case == "does-not-exist":
        (game / "assets" / "generated").mkdir(parents=True)
        return "does not exist"
    folder.mkdir(parents=True)
    if case == "empty":
        return "holds no file to pack"
    if case == "only-names-it-leaves-out":
        for name in ("village.jpg.part", "village.jpg.import", ".village.jpg"):
            (folder / name).write_bytes(b"left out")
        return "holds no file to pack"
    (folder / "village.jpg").write_bytes(b"a photo")
    (folder / "tiles").mkdir()
    (folder / "tiles" / "2623-1096.jpg").write_bytes(b"a tile")
    return "holds a folder, which a pack of its files would leave out"


REFUSED = ["does-not-exist", "empty", "only-names-it-leaves-out", "a-folder"]


@pytest.mark.parametrize("case", REFUSED)
def test_the_stand_in_pack_tool_refuses_as_pack_gd_does(tmp_path, case):
    game = tmp_path / "game"
    problem = _refused_folder(game, case)
    done, out = _pack_tool(tmp_path, game)
    assert done.returncode == 1, (done.stdout, done.stderr)
    assert done.stderr == f"pack: {PHOTO} {problem}\n"
    assert done.stdout == ""
    assert not out.exists()


def test_the_stand_in_pack_tool_packs_what_pack_gd_packs(tmp_path):
    game = tmp_path / "game"
    _noisy_folder(game)
    done, out = _pack_tool(tmp_path, game)
    assert done.returncode == 0, done.stderr
    assert done.stdout == f"pack: wrote {out}, 2 files of {PHOTO}\n"
    assert hashlib.sha256(out.read_bytes()).hexdigest() == PACK_SHA256


def test_the_stand_in_s_words_are_pack_gd_s():
    """A census of pack.gd's text (it proves text, not behaviour; the probe in the brief's
    record ran pack.gd): if pack.gd's words or its left-out names change, the stand-in is stale."""
    source = (fake_tools.REPO / "game" / "tools" / "pack.gd").read_text(encoding="utf-8")
    for text in (
        'return "%s does not exist" % source_dir',
        'return "%s holds a folder, which a pack of its files would leave out" % source_dir',
        'return "%s holds no file to pack" % source_dir',
        'printerr("pack: %s" % problem)',
        'print("pack: wrote %s, %d files of %s" % [args[0], packed_names(args[1]).size(), args[1]])',
        'const NOT_PACKED_SUFFIXES: Array[String] = [".part", ".import"]',
    ):
        assert text in source, text
    assert fake_tools.NOT_PACKED_SUFFIXES == (".part", ".import")


@pytest.mark.parametrize("case", ["empty", "only-names-it-leaves-out", "a-folder"])
def test_a_packed_folder_pack_gd_refuses_fails_step_4b(tmp_path, case):
    root = _tree(tmp_path)
    folder = _generated(root) / "photo"
    for path in folder.iterdir():
        path.unlink()
    folder.rmdir()
    problem = _refused_folder(root / "game", case)
    done = _run(tmp_path, root)
    lines = _lines(done)
    assert done.returncode == 1 and DONE not in done.stdout, done.stdout[-3000:]
    assert f"pack: {PHOTO} {problem}" in lines, done.stdout[-3000:]
    assert any(line.startswith("export: the pack tool failed for photo, exit 1") for line in lines)
    assert "== export: 4c. every generated file is in exactly one pack, as it is" not in lines
    assert not (root / "build" / "linux" / "mattini-photo.pck").exists()


# ---------------------------------------------------------------- R1-06 (b): build/ unfinished


def _after_step_4(tmp_path, root, case):
    """Runs the export so that it fails at the step `case` names; returns the run and the
    refusal's first line."""
    generated = _generated(root)
    if case == "4-the-export-prints-an-error":
        done = _run(tmp_path, root, export_output="ERROR: a stand-in export error\n")
        return done, "export: Godot's export of Linux printed error lines:"
    if case == "4b-the-pack-tool-refuses":
        (generated / "photo" / "village.jpg").unlink()
        return _run(tmp_path, root), "export: the pack tool failed for photo, exit 1"
    if case == "4b-a-pack-not-written":
        (generated / "terrain" / "village.f32").unlink()
        (generated / "terrain").rmdir()
        return _run(tmp_path, root), (
            "export: the data packs written (mattini-photo.pck) are not the ones the game expects"
        )
    if case == "4c-a-file-left-out":
        done = _run(tmp_path, root, leave_out="assets/generated/manifest.json")
        return done, "export: the packs do not hold every generated file exactly once, as it is:"
    if case == "5-a-file-over-the-limit":
        _sparse(root / "build" / "stray" / "big.bin", LIMIT + 1)
        return _run(tmp_path, root), "export: over 100 MiB (104857600 bytes)"
    lines = fake_tools.STARTUP_LINES[:-1]  # the shadows' line is not printed
    done = _run(tmp_path, root, lines=lines)
    return done, "export: the Linux build did not print its startup line:"


AFTER_STEP_4 = [
    "4-the-export-prints-an-error",
    "4b-the-pack-tool-refuses",
    "4b-a-pack-not-written",
    "4c-a-file-left-out",
    "5-a-file-over-the-limit",
    "6-a-startup-line-missing",
]


@pytest.mark.parametrize("case", AFTER_STEP_4)
def test_a_refusal_once_step_4_began_says_build_is_unfinished(tmp_path, case):
    root = _tree(tmp_path)
    done, refusal = _after_step_4(tmp_path, root, case)
    lines = _lines(done)
    assert done.returncode == 1 and DONE not in done.stdout, done.stdout[-3000:]
    refused = [number for number, line in enumerate(lines) if line.startswith(refusal)]
    assert refused, (refusal, done.stdout[-3000:])
    assert lines[-1] == UNFINISHED, done.stdout[-3000:]
    assert done.stdout.count(UNFINISHED) == 1, done.stdout[-3000:]
    assert lines.index(UNFINISHED) > refused[0]


def test_the_unfinished_line_is_on_stderr(tmp_path, monkeypatch):
    """The line goes to stderr with the refusal it ends (run_export merges the two streams, so
    this case keeps them apart)."""
    run = subprocess.run

    def apart(*args, **kwargs):
        if kwargs.get("stderr") is subprocess.STDOUT:
            kwargs["stderr"] = subprocess.PIPE
        return run(*args, **kwargs)

    monkeypatch.setattr(fake_tools.subprocess, "run", apart)
    root = _tree(tmp_path)
    done = _run(tmp_path, root, leave_out="assets/generated/manifest.json")
    assert done.returncode == 1, done.stdout[-3000:]
    errors = [line for line in done.stderr.splitlines() if line.strip()]
    assert errors and errors[-1] == UNFINISHED, done.stderr[-3000:]
    assert UNFINISHED not in done.stdout


@pytest.mark.parametrize("case", ["finished", "4c-a-file-left-out", "another-system"])
def test_the_export_leaves_no_scratch_folder(tmp_path, monkeypatch, case):
    """export.sh's EXIT trap removes its mktemp folder: a trap that prints the unfinished line
    must keep that cleanup (bash keeps one EXIT trap)."""
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setenv("TMPDIR", str(scratch))
    root = _tree(tmp_path)
    if case == "finished":
        done = _run(tmp_path, root)
        assert done.returncode == 0, done.stdout[-3000:]
    elif case == "another-system":
        done = _run(tmp_path, root, system="Darwin")
        assert done.returncode == 1, done.stdout[-3000:]
    else:
        done = _run(tmp_path, root, leave_out="assets/generated/manifest.json")
        assert done.returncode == 1, done.stdout[-3000:]
    assert sorted(path.name for path in scratch.iterdir()) == []


def _before_step_4(tmp_path, case):
    """A tree and the run that fails at the step `case` names, before step 4."""
    if case == "3-the-templates-cannot-be-downloaded":
        root = fake_tools.export_tree(tmp_path, None)
        return root, lambda: _run(tmp_path, root, system="Linux")
    root = _tree(tmp_path)
    if case == "another-system":
        return root, lambda: _run(tmp_path, root, system="Darwin")
    if case == "2-a-block-missing":
        manifest = _generated(root) / "manifest.json"
        blocks = dict(fake_tools.MANIFEST)
        del blocks["shadows"]
        manifest.write_text(json.dumps(blocks, indent=2), encoding="utf-8")
        return root, lambda: _run(tmp_path, root)
    (root / "game" / "scripts" / "data_packs.gd").unlink()
    return root, lambda: _run(tmp_path, root)


@pytest.mark.parametrize(
    "case",
    [
        "another-system",
        "2-a-block-missing",
        "2b-no-data-packs-script",
        "3-the-templates-cannot-be-downloaded",
    ],
)
def test_a_refusal_before_step_4_leaves_build_as_it_was_and_does_not_say_so(tmp_path, case):
    root, run = _before_step_4(tmp_path, case)
    earlier = {
        root / "build" / "linux" / "mattini.x86_64": b"an earlier export\n",
        root / "build" / "windows" / "mattini.exe": b"MZ an earlier export\n",
    }
    for path, data in earlier.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    done = run()
    assert done.returncode == 1 and DONE not in done.stdout, done.stdout[-3000:]
    assert "== export: 4. the exports" not in done.stdout
    assert "unfinished" not in done.stdout, done.stdout[-3000:]
    for path, data in earlier.items():
        assert path.read_bytes() == data, path


def test_a_finished_export_does_not_say_build_is_unfinished(tmp_path):
    root = _tree(tmp_path)
    done = _run(tmp_path, root)
    assert done.returncode == 0 and DONE in done.stdout, done.stdout[-3000:]
    assert "unfinished" not in done.stdout


# ---------------------------------------------------------------- G-05: step 5


def _listed(size, name):
    return f"{size:12d} bytes {size / 1048576:9.2f} MiB  {name}"


def test_a_file_of_exactly_100_mib_passes_step_5(tmp_path):
    root = _tree(tmp_path)
    _sparse(root / "build" / "stray" / "at-the-limit.bin", LIMIT)
    done = _run(tmp_path, root)
    assert done.returncode == 0 and DONE in done.stdout, done.stdout[-3000:]
    assert _listed(LIMIT, "build/stray/at-the-limit.bin") in _lines(done)


def test_files_over_100_mib_fail_step_5_naming_each_and_only_those(tmp_path):
    root = _tree(tmp_path)
    sizes = {
        "build/stray/at-the-limit.bin": LIMIT,
        "build/stray/over-by-one.bin": LIMIT + 1,
        "build/stray/twice.bin": 2 * LIMIT,
    }
    for name, size in sizes.items():
        _sparse(root / name, size)
    done = _run(tmp_path, root)
    lines = _lines(done)
    assert done.returncode == 1 and DONE not in done.stdout, done.stdout[-3000:]
    for name, size in sizes.items():
        assert _listed(size, name) in lines, name
    assert (
        "export: over 100 MiB (104857600 bytes), which GitHub refuses (docs/RELEASE.md §C): "
        "build/stray/over-by-one.bin build/stray/twice.bin"
    ) in lines, done.stdout[-3000:]
    assert "== export: 6. the Linux build starts" not in lines


# ---------------------------------------------------------------- G-05: step 4c

HEADER_4C = "export: the packs do not hold every generated file exactly once, as it is:"


@pytest.mark.parametrize(
    "rel, pack",
    [("manifest.json", "mattini.pck"), ("terrain/village.f32", "mattini-terrain.pck")],
    ids=["manifest-in-mattini.pck", "terrain-in-its-data-pack"],
)
def test_a_generated_file_absent_from_its_pack_fails_step_4c(tmp_path, rel, pack):
    root = _tree(tmp_path)
    done = _run(tmp_path, root, leave_out=f"assets/generated/{rel}")
    lines = _lines(done)
    assert done.returncode == 1 and DONE not in done.stdout, done.stdout[-3000:]
    assert HEADER_4C in lines, done.stdout[-3000:]
    for build in ("build/linux", "build/windows"):
        assert f"{build}: {rel} is in no pack, not in {pack} alone" in lines, build
    assert "== export: 5. every file in build/ against GitHub's limit" not in lines


@pytest.mark.parametrize(
    "rel, pack",
    [("manifest.json", "mattini.pck"), ("photo/village.jpg", "mattini-photo.pck")],
    ids=["manifest-in-mattini.pck", "photo-in-its-data-pack"],
)
def test_a_generated_file_with_a_changed_byte_fails_step_4c(tmp_path, rel, pack):
    root = _tree(tmp_path)
    data = (_generated(root) / rel).read_bytes()
    changed = data[:-1] + bytes([data[-1] ^ 0x01])
    held, real = hashlib.md5(changed).hexdigest(), hashlib.md5(data).hexdigest()
    done = _run(tmp_path, root, change=f"assets/generated/{rel}")
    lines = _lines(done)
    assert done.returncode == 1 and DONE not in done.stdout, done.stdout[-3000:]
    assert HEADER_4C in lines, done.stdout[-3000:]
    n = len(data)
    for build in ("build/linux", "build/windows"):
        line = f"{build}: {rel} in {pack} has {n} bytes, MD5 {held}; the file has {n} bytes, MD5 {real}"
        assert line in lines, (line, done.stdout[-3000:])
    assert "== export: 5. every file in build/ against GitHub's limit" not in lines
