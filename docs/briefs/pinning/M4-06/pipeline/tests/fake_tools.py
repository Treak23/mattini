"""tools/gate.sh and tools/export.sh run on output a test writes (brief M3-02's pins).

The scripts under test are the repository's own, copied unchanged into a scratch tree laid
out like the repository. The tools they call are small bash stand-ins that record their
arguments in `calls.txt` and print what the test gave them:
- `godot` (passed as $GODOT): `--version` prints Godot 4.6.3's version line; the GUT run
  (`-s addons/gut/gut_cmdln.gd`) prints the test's GUT output byte for byte and exits with
  the test's status; `--export-release <preset> <path>` writes <path> (for Linux a script
  printing the test's startup output) and beside it a `.pck` in Godot 4.6.3's pack format 3
  holding every generated file as an export does (`write_pck`, which gives PCKPacker's
  bytes, measured), so a check that reads the packs' directories reads it as a real one;
  anything else (the import, the parse check) prints nothing and exits 0.
- `uv`: `uv run ... python -c ...` runs this Python with the rest of the arguments; every
  other command (lock --check, pytest, ruff, the manifest, gdlint, gdformat) exits 0 at
  once, so no pipeline step and no gate runs inside the test.
- `xvfb-run` (brief M3-R1-fix-3): records its call, drops its `-a` and runs the rest; a test
  that hides it from PATH (`xvfb=False`) gets a PATH holding every executable of the real one
  but `xvfb-run`. The render scripts (`godot ... -s res://tests/render/<name>.gd`) print the
  test's lines for them (`render=`, by script name; by default each check's PASS line) and
  exit with its status.
- `uname` and `curl`, only where a test puts them first on PATH: `uname` prints the
  system the test names, `curl` records the call and fails.
So the scripts' own logic runs as it does for the owner, on output the test controls.

`gut_output` builds GUT 9.6.1's output as measured on Godot 4.6.3 in a cloud container
(2026-10-14, design's probes): its ANSI codes, its per-script heading and `<n>/<m>
passed.` lines, its run summary with GUT's own padding, and its final line.

Since brief M3-14 (design's full replacement of M3-02's file; only MANIFEST, STARTUP_LINES
and this paragraph change): the export ships six blocks, so the stand-in manifest holds the
terrain, buildings, photo, surfaces, trees and roofs blocks, and the started build prints
their six startup lines, M2's two first (test_export_startup_lines.py pins them).

Does NOT prove: that Godot, GUT or a Windows Godot print exactly this (each line was
measured on Linux only; a CRLF run is simulated by turning every LF into CR LF).
"""

import hashlib
import json
import os
import shutil
import stat
import struct
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BASH = shutil.which("bash")
GODOT_VERSION = "4.6.3.stable.official.7d41c59c4"


def _project_version(path: Path) -> str:
    """application/config/version from project.godot, the value export.sh's lines carry."""
    section, version = "", None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
        elif section == "application" and line.startswith("config/version="):
            version = json.loads(line.split("=", 1)[1])
    if version is None:
        raise RuntimeError(f"{path} has no application/config/version")
    return str(version)


# The export tree copies game/project.godot, so a release's version bump changes the
# startup lines and these stand-ins with it.
VERSION = _project_version(REPO / "game" / "project.godot")

FAKE_GODOT = r"""#!/usr/bin/env bash
# A stand-in for Godot 4.6.3 (pipeline/tests/fake_tools.py).
printf 'godot %s\n' "$*" >> "$FAKE_CALLS"
args=("$@")
for ((i = 0; i < ${#args[@]}; i++)); do
	case "${args[$i]}" in
		--path) game="${args[$((i + 1))]}" ;;
		--version)
			echo "$FAKE_GODOT_VERSION"
			exit 0
			;;
		addons/gut/gut_cmdln.gd)
			cat "$FAKE_GUT_OUTPUT"
			exit "${FAKE_GUT_EXIT:-0}"
			;;
		res://tests/render/*.gd)
			name="${args[$i]##*/}"
			cat "$FAKE_RENDER_DIR/${name%.gd}.txt"
			exit "${FAKE_RENDER_EXIT:-0}"
			;;
		--export-release)
			preset="${args[$((i + 1))]}"
			out="${args[$((i + 2))]}"
			mkdir -p "$(dirname "$out")"
			if [ "$preset" = "Linux" ]; then
				printf '#!/usr/bin/env bash\ncat "$FAKE_START_OUTPUT"\n' > "$out"
				chmod +x "$out"
			else
				printf 'MZ a stand-in for %s\n' "$preset" > "$out"
			fi
			"$FAKE_PYTHON" "$FAKE_TOOLS" pck "${out%.*}.pck" "${game:-game}/assets/generated"
			exit $?
			;;
	esac
done
exit 0
"""

FAKE_UV = r"""#!/usr/bin/env bash
# A stand-in for uv (pipeline/tests/fake_tools.py).
printf 'uv %s\n' "$*" >> "$FAKE_CALLS"
[ "${1:-}" = "run" ] || exit 0
shift
while [ "$#" -gt 0 ]; do
	case "$1" in
		--project) shift 2 ;;
		--frozen) shift ;;
		*) break ;;
	esac
done
if [ "${1:-}" = "python" ] && [ "${2:-}" = "-c" ]; then
	shift
	exec "$FAKE_PYTHON" "$@"
fi
exit 0
"""

FAKE_XVFB = r"""#!/usr/bin/env bash
# A stand-in for xvfb-run (pipeline/tests/fake_tools.py): no display, the command runs.
printf 'xvfb-run %s\n' "$*" >> "$FAKE_CALLS"
[ "${1:-}" = "-a" ] && shift
exec "$@"
"""

FAKE_UNAME = r"""#!/usr/bin/env bash
echo "$FAKE_UNAME"
"""

FAKE_CURL = r"""#!/usr/bin/env bash
printf 'curl %s\n' "$*" >> "$FAKE_CALLS"
exit 22
"""


# ---------------------------------------------------------------------- the render scripts

RENDER_PASSING = {
    "render_photo": [
        (
            "RENDER photo: PASS correlation 0.9761 north-south-mirrored 0.0547 "
            "east-west-mirrored -0.2240 over 34772 pixels"
        ),
        (
            "RENDER classes: PASS agreement 83091 of 83427, mirrored 70472, water "
            '{ "both": 8678, "render_only": 333, "data_only": 3, "neither": 74413 }'
        ),
    ],
    "render_lift": [
        (
            'RENDER lift: PASS correlation 1.0000 { "north-south-mirrored": 0.1912, '
            '"east-west-mirrored": 0.0, "transposed": 0.0, "nearest": 0.9827 }; lift 3.060 '
            "inside the mask (6244), 1.000 outside (15717), over 29688 pixels"
        )
    ],
    "render_trees": [
        (
            "RENDER trees: PASS correlation 0.9380 over 20 trees; with the photo read x and z "
            "exchanged -0.2014, mirrored north-south 0.2324, mirrored east-west -0.0031"
        )
    ],
}


def render_text(lines: list[str]) -> str:
    """A render script's output: Godot's banner, then `lines`."""
    return "\n".join([f"Godot Engine v{GODOT_VERSION} - https://godotengine.org", "", *lines, ""])


# ---------------------------------------------------------------------- the packs

PACKED_FOLDERS = ("photo", "terrain")  # their own packs from M3-08 on, never mattini.pck


def write_pck(path: Path, files: list[tuple[str, bytes]]) -> None:
    """A pack in Godot 4.6.3's format 3 holding `files` ((path without res://, bytes), in
    order): the header (magic GDPC, format 3, 4.6.3, flags 2 = relative file base, the
    file base and the directory's offset as u64, 16 reserved u32), each file from byte 128
    padded to 32, then the directory (a u32 count; per file its padded path, u64 offset
    from the file base, u64 size, MD5, u32 flags). Measured: PCKPacker's bytes for the same
    files (a 3-file pack, 440 bytes, SHA-256 f8bf4869…, design's probe of 2026-10-14)."""
    head = struct.pack("<6I", 0x43504447, 3, 4, 6, 3, 2)
    base = 128
    body, entries = bytearray(), []
    for name, data in files:
        entries.append((name, len(body), len(data), hashlib.md5(data).digest()))
        body += data + b"\0" * (-len(data) % 32)
    out = bytearray(head + struct.pack("<QQ", base, base + len(body)) + b"\0" * 64)
    out += b"\0" * (base - len(out)) + body + struct.pack("<I", len(entries))
    for name, offset, size, md5 in entries:
        raw = name.encode("utf-8")
        raw += b"\0" * (-len(raw) % 4)
        out += struct.pack("<I", len(raw)) + raw + struct.pack("<QQ", offset, size) + md5
        out += struct.pack("<I", 0)
    Path(path).write_bytes(bytes(out))


def exported_files(generated: Path) -> list[tuple[str, bytes]]:
    """What an export puts into mattini.pck from `generated`: every file but the packed
    folders', the hidden ones, `*.part` and `*.import`, at assets/generated/<path>."""
    files = []
    for file in sorted(generated.rglob("*")):
        rel = file.relative_to(generated).as_posix()
        packed = "/" in rel and rel.split("/")[0] in PACKED_FOLDERS
        hidden = file.name.startswith(".") or file.name.endswith((".part", ".import"))
        if file.is_file() and not packed and not hidden:
            files.append((f"assets/generated/{rel}", file.read_bytes()))
    return files


# ---------------------------------------------------------------------- GUT's output


def script_block(path: str, tests: list[tuple[str, list[str]]], *, first: bool) -> str:
    """One test script as GUT prints it: its heading, each test's name and the lines it
    printed, then `<passed>/<ran> passed.` (every test here passes)."""
    lines = [("\x1b[4m" if first else "\x1b[0m\x1b[4m"), "", path]
    for number, (test, printed) in enumerate(tests):
        lines.append(("\x1b[0m* " if number == 0 else "* ") + test)
        lines.extend(printed)
    lines.append(f"\x1b[1m{len(tests)}/{len(tests)} passed.")
    return "\n".join(lines) + "\n"


def _total(text: str, value) -> str:
    return text.ljust(18) + str(value).rjust(5)


def gut_output(
    scripts: list[tuple[str, list[tuple[str, list[str]]]]],
    *,
    gut_version: str | None = "9.6.1",
    before: list[str] = (),
    summary: bool = True,
    scripts_total: int | None = None,
    after: list[str] = (),
) -> str:
    """GUT 9.6.1's output for a run of `scripts`, each (path, [(test, [printed lines])]).

    `before` are lines printed while GUT collects the scripts (its warnings, Godot's load
    errors); `summary=False` ends the run without GUT's run summary (a run cut short);
    `scripts_total` is the summary's script count (by default the scripts printed); `after`
    are lines printed at exit. `gut_version=None` leaves GUT's version line out.
    """
    head = [
        f"Godot Engine v{GODOT_VERSION} - https://godotengine.org",
        "",
        "---  GUT  ---",
        (
            "\x1b[1m[INFO]:  \x1b[0musing [/tmp/gate/data/godot/app_userdata/mattini] for "
            "temporary output."
        ),
        "Godot version:  4.6.3",
    ]
    if gut_version is not None:
        head.append(f"GUT version:  {gut_version}")
    text = "\n".join([*head, *before]) + "\n"
    for number, (path, tests) in enumerate(scripts):
        text += script_block(path, tests, first=number == 0)
    if summary:
        tests = sum(len(tests) for _, tests in scripts)
        count = len(scripts) if scripts_total is None else scripts_total
        text += "\n".join(
            [
                "\x1b[0m",
                "",
                "",
                "\x1b[33m==============================================",
                "\x1b[0m\x1b[33m= Run Summary",
                "\x1b[0m\x1b[33m==============================================",
                "\x1b[0m",
                "Totals",
                "------",
                _total("Scripts", count),
                _total("Tests", tests),
                _total("Passing Tests", tests),
                _total("Asserts", tests),
                _total("Time", "0.427s"),
                "",
                "",
                "\x1b[32m---- All tests passed! ----",
                "\x1b[0m",
            ]
        )
        text += "\n"
    if after:
        text += "\n".join(after) + "\n"
    return text


def crlf(text: str) -> str:
    """The output with CR LF line ends, as a Windows console may write it."""
    return text.replace("\n", "\r\n")


# ---------------------------------------------------------------------- the trees


def _executable(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _stand_ins(tmp_path: Path, *, system: str | None = None, xvfb: bool = True) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    _executable(bin_dir / "godot", FAKE_GODOT)
    _executable(bin_dir / "uv", FAKE_UV)
    if xvfb:
        _executable(bin_dir / "xvfb-run", FAKE_XVFB)
    if system is not None:
        _executable(bin_dir / "uname", FAKE_UNAME)
        _executable(bin_dir / "curl", FAKE_CURL)
    return bin_dir


def _path_without(tmp_path: Path, name: str) -> str:
    """A PATH holding a symlink to every executable of this process's PATH (the first of each
    name, as a shell finds it) but `name`: the tool is hidden, everything else stays."""
    farm = tmp_path / f"path-without-{name}"
    farm.mkdir(exist_ok=True)
    seen = {name}
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        if not directory or not Path(directory).is_dir():
            continue
        for entry in Path(directory).iterdir():
            if entry.name not in seen and entry.is_file() and os.access(entry, os.X_OK):
                seen.add(entry.name)
                (farm / entry.name).symlink_to(entry)
    return str(farm)


def _env(tmp_path: Path, bin_dir: Path, *, path: str | None = None, **extra) -> dict:
    env = dict(os.environ)
    env.pop("MATTINI_SKIP_RENDER", None)  # only a test that sets it has it
    env.update(
        PATH=f"{bin_dir}{os.pathsep}{path if path is not None else env.get('PATH', '')}",
        GODOT=str(bin_dir / "godot"),
        FAKE_TOOLS=str(Path(__file__).resolve()),
        FAKE_GODOT_VERSION=GODOT_VERSION,
        FAKE_CALLS=str(tmp_path / "calls.txt"),
        FAKE_PYTHON=sys.executable,
        XDG_DATA_HOME=str(tmp_path / "xdg"),
    )
    env.update({key: str(value) for key, value in extra.items()})
    return env


def calls(tmp_path: Path) -> list[str]:
    """Every call the stand-ins recorded, one line each."""
    path = tmp_path / "calls.txt"
    return path.read_text(encoding="utf-8").splitlines() if path.exists() else []


def gate_tree(tmp_path: Path, tests: list[str], allowlist: str = "") -> Path:
    """A scratch repository for tools/gate.sh: the gate, the allowlist given, GUT's vendored
    plugin.cfg, and a test script (`extends GutTest`) per name under game/tests/."""
    root = tmp_path / "repo"
    (root / "tools").mkdir(parents=True)
    shutil.copy2(REPO / "tools" / "gate.sh", root / "tools" / "gate.sh")
    (root / "tools" / "gate_allowlist.txt").write_text(allowlist, encoding="utf-8")
    plugin = root / "game" / "addons" / "gut" / "plugin.cfg"
    plugin.parent.mkdir(parents=True)
    shutil.copy2(REPO / "game" / "addons" / "gut" / "plugin.cfg", plugin)
    for name in tests:
        path = root / "game" / "tests" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("extends GutTest\n", encoding="utf-8")
    (root / "pipeline").mkdir()
    return root


def run_gate(
    tmp_path: Path,
    root: Path,
    output: str,
    *,
    status: int = 0,
    xvfb: bool = True,
    render: dict[str, list[str]] | None = None,
    render_status: int = 0,
    env: dict | None = None,
):
    """tools/gate.sh in `root`, its GUT run printing `output` (bytes as given) and exiting
    `status`. Its render scripts print their PASS lines (RENDER_PASSING) or, for a script named
    in `render` ("render_photo", "render_lift", "render_trees"), the lines given, and exit `render_status`;
    `xvfb=False` hides xvfb-run from PATH; `env` adds variables (MATTINI_SKIP_RENDER).
    Returns the CompletedProcess (stdout and stderr together in stdout)."""
    bin_dir = _stand_ins(tmp_path, xvfb=xvfb)
    gut = tmp_path / "gut-output.txt"
    gut.write_bytes(output.encode("utf-8"))
    printed = tmp_path / "render-output"
    printed.mkdir(exist_ok=True)
    for name, lines in {**RENDER_PASSING, **(render or {})}.items():
        (printed / f"{name}.txt").write_text(render_text(lines), encoding="utf-8")
    return subprocess.run(  # the caller checks the status
        [BASH, str(root / "tools" / "gate.sh")],
        cwd=tmp_path,
        env=_env(
            tmp_path,
            bin_dir,
            path=None if xvfb else _path_without(tmp_path, "xvfb-run"),
            FAKE_GUT_OUTPUT=gut,
            FAKE_GUT_EXIT=status,
            FAKE_RENDER_DIR=printed,
            FAKE_RENDER_EXIT=render_status,
            **(env or {}),
        ),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
        check=False,
    )


TEMPLATES = (
    "version.txt",
    "linux_debug.x86_64",
    "linux_release.x86_64",
    "windows_debug_x86_64.exe",
    "windows_debug_x86_64_console.exe",
    "windows_release_x86_64.exe",
    "windows_release_x86_64_console.exe",
)
MANIFEST = {
    "buildings": {
        "area": "village",
        "chunks": [
            {"buildings": 1000, "triangles": 100000},
            {"buildings": 486, "triangles": 78910},
        ],
    },
    "photo": {"area": "village", "cell_m": 0.2, "columns": 10000, "rows": 15000},
    "roofs": {
        "area": "village",
        "chunks": [
            {"buildings": [{"roof": "a1b2c3"}] * 999 + [{"roof": None}]},
            {"buildings": [{"roof": "445566"}] * 486},
        ],
    },
    "schema": 1,
    "surfaces": {"area": "village", "cell_m": 0.5, "columns": 4000, "rows": 6000},
    "terrain": {"area": "village", "columns": 4001, "rows": 6001, "spacing_m": 0.5},
    "trees": {
        "area": "village",
        "chunks": [{"trees": 5734}, {"trees": 3662}, {"trees": 25027}],
    },
}
STARTUP_LINES = (
    f"mattini {VERSION}: terrain village loaded, 4001 x 6001 vertices at 0.5 m",
    f"mattini {VERSION}: buildings village loaded, 1486 buildings in 2 chunks, 178910 triangles",
    f"mattini {VERSION}: photo village loaded, 10000 x 15000 texels at 0.2 m",
    f"mattini {VERSION}: surfaces village loaded, 4000 x 6000 cells at 0.5 m",
    f"mattini {VERSION}: trees village loaded, 34423 trees in 3 chunks",
    f"mattini {VERSION}: roofs village loaded, 1485 of 1486 buildings coloured",
)


def export_tree(tmp_path: Path, templates_dir: Path | None) -> Path:
    """A scratch repository for tools/export.sh: the script, game/project.godot, a manifest
    with both blocks (step 1's rewrite is the stand-in uv's no-op), and, unless None,
    Godot's export templates installed in `templates_dir`."""
    import json

    root = tmp_path / "repo"
    (root / "tools").mkdir(parents=True)
    shutil.copy2(REPO / "tools" / "export.sh", root / "tools" / "export.sh")
    (root / "game").mkdir()
    shutil.copy2(REPO / "game" / "project.godot", root / "game" / "project.godot")
    manifest = root / "game" / "assets" / "generated" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps(MANIFEST, indent=2), encoding="utf-8")
    (root / "pipeline").mkdir()
    if templates_dir is not None:
        templates_dir.mkdir(parents=True)
        (templates_dir / "version.txt").write_text("4.6.3.stable\n", encoding="utf-8")
        for name in TEMPLATES[1:]:
            (templates_dir / name).write_bytes(b"a stand-in template\n")
    return root


def run_export(tmp_path: Path, root: Path, start_output: str, *, system: str | None = None):
    """tools/export.sh in `root`; the exported Linux build prints `start_output`. With
    `system`, `uname` says that system and `curl` fails. APPDATA points into tmp_path."""
    bin_dir = _stand_ins(tmp_path, system=system)
    start = tmp_path / "start-output.txt"
    start.write_bytes(start_output.encode("utf-8"))
    extra = {"FAKE_START_OUTPUT": start, "APPDATA": tmp_path / "appdata"}
    if system is not None:
        extra["FAKE_UNAME"] = system
    return subprocess.run(  # the caller checks the status
        [BASH, str(root / "tools" / "export.sh")],
        cwd=tmp_path,
        env=_env(tmp_path, bin_dir, **extra),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
        check=False,
    )


def start_output(lines=STARTUP_LINES) -> str:
    """The started build's output: Godot's banner, Terrain3D's deprecation warning (its
    first line and where, as the gate's GUT run prints them, measured), then `lines`."""
    return "\n".join(
        [
            f"Godot Engine v{GODOT_VERSION} - https://godotengine.org",
            "",
            "WARNING: instance_reset_physics_interpolation() is deprecated.",
            (
                "     at: _instance_reset_physics_interpolation_bind_compat_104269 "
                "(servers/rendering/rendering_server.compat.inc:58)"
            ),
            *lines,
            "",
        ]
    )


if __name__ == "__main__" and sys.argv[1:2] == ["pck"]:  # the stand-in Godot's export
    write_pck(Path(sys.argv[2]), exported_files(Path(sys.argv[3])))
