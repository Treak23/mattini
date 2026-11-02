"""The v0.6.0-07 rehearsal's mutation rows: each a text edit of the throwaway (one file, one or
more exact replacements), the pinned tests run broken and restored. Run from the clone's root:
python3 -I mutate.py <out_dir> [row ...]."""
import json, subprocess, sys, os
from pathlib import Path

M = "pipeline/mattini/"
ROWS = {
 1: ("the block left out of the manifest", M+"manifest.py", [('        "surroundings": surroundings,\n', '')]),
 2: ("{} when not built", M+"manifest.py", [('surroundings = None if colour is None else {**heights, **colour}', 'surroundings = {} if colour is None else {**heights, **colour}')]),
 3: ("the heights alone written as the block", M+"manifest.py", [('surroundings = None if colour is None else {**heights, **colour}', 'surroundings = heights if colour is None else {**heights, **colour}')]),
 4: ("the colour without the heights accepted as null", M+"manifest.py", [('    if colour is not None and heights is None:\n', '    if False:\n')]),
 5: ("the colour's description alone as the block", M+"manifest.py", [('surroundings = None if colour is None else {**heights, **colour}', 'surroundings = None if colour is None else colour')]),
 6: ("the manifest's own checks skipped for the heights", M+"manifest.py", [('        if checked(_HEIGHTS, area, surroundings_config)', '        if (Path(out_dir) / "surroundings" / f"{area}.json").exists()')]),
 7: ("the manifest's own checks skipped for the colour", M+"manifest.py", [('        if checked(_COLOUR, area, surroundings_config, "_colour")', '        if (Path(out_dir) / "surroundings" / f"{area}_colour.json").exists()')]),
 8: ("the world after the fit", M+"manifest.py", [('''    problem = world_refusal(step.config_name, computed_for, world_sha256)
    if problem:
        raise step.error(f"area {area!r}: {problem}")
    if area not in world.areas:
        return
    for name in step.names:''', '''    if area not in world.areas:
        return
    for name in step.names:'''), ('''    problem = _inputs_refusal(step, computed_for, lock())
    if problem:
        raise step.error(f"area {area!r}: {problem}")''', '''    problem = world_refusal(step.config_name, computed_for, world_sha256)
    if problem:
        raise step.error(f"area {area!r}: {problem}")
    problem = _inputs_refusal(step, computed_for, lock())
    if problem:
        raise step.error(f"area {area!r}: {problem}")''')]),
 9: ("the fit after the inputs", M+"manifest.py", [('''    for name in step.names:
        try:''', '''    problem = _inputs_refusal(step, computed_for, lock())
    if problem:
        raise step.error(f"area {area!r}: {problem}")
    for name in step.names:
        try:''')]),
 10: ("the colour's lock entries: swissaltiregio's alone (no far fit, the heights' inputs)", M+"manifest.py", [('''    "surroundings", SURROUNDINGS_CONFIG_NAME, tuple(sorted((REGIO, FARPHOTO))), FarColourError''', '''    "surroundings", SURROUNDINGS_CONFIG_NAME, (REGIO,), FarColourError''')]),
 11: ("the colour's inputs from swissimage_far's entry alone", M+"manifest.py", [('''    if len(step.names) == 1:''', '''    if len(step.names) == 1 or step.error is FarColourError:'''), ('''        (name,) = step.names''', '''        name = step.names[-1]''')]),
 12: ("the colour checked before the heights", M+"manifest.py", [('''    heights = (
        built_surroundings_block(
            out_dir, surroundings_config, world, world_sha256, datasets, lock()
        )
        if checked(_HEIGHTS, area, surroundings_config)
        else None
    )
    colour = (
        built_farcolour_block(out_dir, surroundings_config, world, world_sha256, datasets, lock())
        if checked(_COLOUR, area, surroundings_config, "_colour")
        else None
    )''', '''    colour = (
        built_farcolour_block(out_dir, surroundings_config, world, world_sha256, datasets, lock())
        if checked(_COLOUR, area, surroundings_config, "_colour")
        else None
    )
    heights = (
        built_surroundings_block(
            out_dir, surroundings_config, world, world_sha256, datasets, lock()
        )
        if checked(_HEIGHTS, area, surroundings_config)
        else None
    )''')]),
 13: ("the error classes of the two halves swapped", M+"manifest.py", [('''_HEIGHTS = _Step("surroundings", SURROUNDINGS_CONFIG_NAME, (REGIO,), SurroundingsError)''', '''_HEIGHTS = _Step("surroundings", SURROUNDINGS_CONFIG_NAME, (REGIO,), FarColourError)''')]),
 14: ("the manifest's fit given the committed config, not the one it was given", M+"manifest.py", [('''            problem = fit_problem(lock(), datasets, world, area, name, surroundings=surroundings)''', '''            problem = fit_problem(
                lock(), datasets, world, area, name, surroundings=load_surroundings_config()
            )''')]),
 15: ("surroundings_config_path not passed through write_manifest", M+"manifest.py", [('''        surroundings_config_path=surroundings_config_path,
    )
    text =''', '''    )
    text =''')]),
 16: ("the surroundings config loaded only when a half is built", M+"manifest.py", [('''    surroundings_config = load_surroundings_config(surroundings_config_path)
''', '''    surroundings_config = (
        load_surroundings_config(surroundings_config_path)
        if (Path(out_dir) / "surroundings").exists()
        else load_surroundings_config()
    )
''')]),
 17: ("fit_problem reads the committed config when given none (no TypeError)", M+"lock.py", [('''    if fit.surroundings and surroundings is None:
        raise TypeError(f"fit_problem for {dataset!r} needs surroundings=<the surroundings config>")''', '''    if fit.surroundings and surroundings is None:
        from mattini.surroundings import load_surroundings_config

        surroundings = load_surroundings_config()''')]),
 18: ("fit_problem reads the committed config instead of the one given", M+"lock.py", [('''    margin_m, spacing_m = download.surroundings_margin_spacing(surroundings, area)
    return download.regio_tiles(''', '''    from mattini.surroundings import load_surroundings_config

    surroundings = load_surroundings_config()
    margin_m, spacing_m = download.surroundings_margin_spacing(surroundings, area)
    return download.regio_tiles(''')]),
 19: ("the regio rule bound at import (not looked up on download)", M+"lock.py", [('''def _regio_ids(world: World, area: str, surroundings: dict) -> list[str]:''', '''_REGIO_TILES = download.regio_tiles


def _regio_ids(world: World, area: str, surroundings: dict) -> list[str]:'''), ('''    return download.regio_tiles(world, area, margin_m=margin_m, spacing_m=spacing_m)''', '''    return _REGIO_TILES(world, area, margin_m=margin_m, spacing_m=spacing_m)''')]),
 20: ("surroundings.py keeps its own tile rule for its fit (a copy of regio_tiles)", M+"surroundings.py", [('''        problem = fit_problem(lock, datasets, world, area, DATASET, surroundings=config)''', '''        import math as _m

        _s = config["areas"][area]
        _e0, _e1, _n0, _n1 = world.area(area)
        _h = _s["spacing_m"] / 2
        _own = [
            f"{(5_000 + 10_000 * i) // 1000:04d}-{(4_000 + 10_000 * j) // 1000:04d}"
            for i in range(
                _m.floor((_e0 - _s["margin_m"] - _h - 5_000) / 10_000),
                _m.ceil((_e1 + _s["margin_m"] + _h - 5_000) / 10_000),
            )
            for j in range(
                _m.floor((_n0 - _s["margin_m"] - _h - 4_000) / 10_000),
                _m.ceil((_n1 + _s["margin_m"] + _h - 4_000) / 10_000),
            )
        ]
        _entry = (lock.get("datasets") or {}).get(DATASET) or {}
        problem = (
            None
            if sorted(_entry.get("tiles") or {}) == _own
            else f"the lock does not fit; `{LOCK_COMMAND}`"
        )''')]),
 21: ("the step's fit skipped (only the shape checked)", M+"surroundings.py", [('''        problem = fit_problem(lock, datasets, world, area, DATASET, surroundings=config)''', '''        problem = None''')]),
 22: ("farcolour keeps its own copy of the far cells for its fit", M+"farcolour.py", [('''            problem = fit_problem(lock, datasets, world, area, name, surroundings=config)''', '''            if name == FAR:
                import math as _m

                _mg = config["areas"][area]["margin_m"]
                _e0, _e1, _n0, _n1 = world.area(area)
                _own = [
                    f"{e}-{n}"
                    for e in range(_m.floor((_e0 - _mg) / 1000), _m.ceil((_e1 + _mg) / 1000))
                    for n in range(_m.floor((_n0 - _mg) / 1000), _m.ceil((_n1 + _mg) / 1000))
                ]
                _en = (lock.get("datasets") or {}).get(FAR) or {}
                _have = sorted(list(_en.get("tiles") or {}) + list(_en.get("absent") or []))
                problem = None if _have == sorted(_own) else f"the lock does not fit; `{LOCK_FAR}`"
            else:
                problem = fit_problem(lock, datasets, world, area, name, surroundings=config)''')]),
 23: ("farcolour's far fit skipped", M+"farcolour.py", [('''    for name in (REGIO, FAR):''', '''    for name in (REGIO,):''')]),
 24: ("download regio and farphoto given the config read by __main__ itself", M+"__main__.py", [('''            extra["surroundings"] = surroundings.load_surroundings_config()
        count = len(''', '''            import json as _json

            extra["surroundings"] = _json.loads(
                (Path(__file__).resolve().parents[2] / "config" / "surroundings.json").read_bytes()
            )
        count = len(''')]),
 25: ("lock regio and farphoto given the config not through the module", M+"__main__.py", [('''            extra["surroundings"] = surroundings.load_surroundings_config()
        entry = entry_of''', '''            extra["surroundings"] = _LOAD()
        entry = entry_of'''), ('''def _lock(dataset: str) -> Path:''', '''_LOAD = surroundings.load_surroundings_config


def _lock(dataset: str) -> Path:''')]),
 26: ("the surroundings command given the config read by __main__ itself, not by the reader", M+"__main__.py", [('''        surroundings.build_surroundings(
            world,
            datasets,
            pinned,
            surroundings.load_surroundings_config(),''', '''        import json as _json

        surroundings.build_surroundings(
            world,
            datasets,
            pinned,
            _json.loads(surroundings.SURROUNDINGS_CONFIG_PATH.read_bytes()),''')]),
 27: ("farcolour handed to the surroundings step", M+"__main__.py", [('''        farcolour.build_farcolour(''', '''        surroundings.build_surroundings(''')]),
 28: ("the new commands after shadows in the help", M+"__main__.py", [('''    "surroundings": "build the far terrain's 50 m heights from the swissALTIRegio tiles",
    "farcolour": "build the far terrain's 10 m colour from the SWISSIMAGE 2 m tiles",
    "shadows": "build the capture shadows mask from the surface model",''', '''    "shadows": "build the capture shadows mask from the surface model",
    "surroundings": "build the far terrain's 50 m heights from the swissALTIRegio tiles",
    "farcolour": "build the far terrain's 10 m colour from the SWISSIMAGE 2 m tiles",''')]),
 29: ("SurroundingsError not caught", M+"__main__.py", [('''        surroundings.SurroundingsError,
        farcolour.FarColourError,''', '''        farcolour.FarColourError,''')]),
 30: ("FarColourError not caught", M+"__main__.py", [('''        surroundings.SurroundingsError,
        farcolour.FarColourError,''', '''        surroundings.SurroundingsError,''')]),
 31: ("a new command that does not write the manifest", M+"__main__.py", [('''    elif step == "farcolour":
        farcolour.build_farcolour(
            world,
            datasets,
            pinned,
            surroundings.load_surroundings_config(),
            raw_root,
            out_dir,
            progress=progress,
        )''', '''    elif step == "farcolour":
        farcolour.build_farcolour(
            world,
            datasets,
            pinned,
            surroundings.load_surroundings_config(),
            raw_root,
            out_dir,
            progress=progress,
        )
        return out_dir / "surroundings"''')]),
 32: ("the farcolour step built from an import-time name", M+"__main__.py", [('''        farcolour.build_farcolour(''', '''        _BUILD_FARCOLOUR('''), ('''def _build_step(step: str, raw_root: Path, out_dir: Path) -> Path:''', '''_BUILD_FARCOLOUR = farcolour.build_farcolour


def _build_step(step: str, raw_root: Path, out_dir: Path) -> Path:''')]),
 33: ("probe: a config without the area gives a KeyError, not the DownloadError", M+"download.py", [('''    settings = surroundings["areas"].get(area)
    if settings is None:''', '''    settings = surroundings["areas"][area]
    if settings is None:''')]),
 34: ("probe: farcolour's shape_problem after its fits dropped", M+"farcolour.py", [('''    problem = shape_problem(lock)
    if problem:
        raise FarColourError(problem)''', '''    problem = None
    if problem:
        raise FarColourError(problem)''')]),
 35: ("probe: the manifest written without its .part", M+"manifest.py", [('''    part = path.with_name(path.name + ".part")
    part.write_bytes((text + "\\n").encode("utf-8"))
    os.replace(part, path)''', '''    path.write_bytes((text + "\\n").encode("utf-8"))''')]),
 36: ("the regio fit's spacing hard-coded at 50 (the brief's row 33)", M+"lock.py", [("    return download.regio_tiles(world, area, margin_m=margin_m, spacing_m=spacing_m)", "    return download.regio_tiles(world, area, margin_m=margin_m, spacing_m=50)")]),
 37: ("the regio fit's spacing halved (the brief's row 33)", M+"lock.py", [("    return download.regio_tiles(world, area, margin_m=margin_m, spacing_m=spacing_m)", "    return download.regio_tiles(world, area, margin_m=margin_m, spacing_m=spacing_m // 2)")]),
}

def run(out):
    pins = sorted(str(p) for p in Path("docs/briefs/pinning/v0.6.0-07/pipeline/tests").glob("*.py"))
    pins = ["pipeline/tests/" + Path(p).name for p in pins]
    done = subprocess.run(["uv", "run", "--project", "pipeline", "pytest", "-q", "-p", "no:cacheprovider", "--tb=no", "-rf", *pins], capture_output=True, text=True, env={**os.environ, "COLUMNS": "300"})
    out.write_text(done.stdout + done.stderr)
    last = [l for l in done.stdout.splitlines() if " passed" in l or " failed" in l or " error" in l]
    return last[-1] if last else done.stdout[-300:]

def main():
    out_dir = Path(sys.argv[1]); out_dir.mkdir(exist_ok=True)
    rows = [int(a) for a in sys.argv[2:]] or sorted(ROWS)
    for n in rows:
        what, path, edits = ROWS[n]
        p = Path(path); original = p.read_bytes(); text = original.decode()
        for old, new in edits:
            assert text.count(old) == 1, (n, old[:80], text.count(old))
            text = text.replace(old, new)
        p.write_text(text)
        try:
            broken = run(out_dir / f"row{n:02d}-broken.log")
        finally:
            p.write_bytes(original)
        restored = run(out_dir / f"row{n:02d}-restored.log")
        diff = subprocess.run(["git", "diff", "pipeline/mattini"], capture_output=True, text=True).stdout
        base = Path(os.environ["THROWAWAY_PATCH"]).read_text() if os.environ.get("THROWAWAY_PATCH") else ""
        tree = "the throwaway, byte for byte" if diff == base else "DIFFERS"
        print(f"row {n}: {what} | broken: {broken} | restored: {restored} | tree: {tree}", flush=True)

main()
