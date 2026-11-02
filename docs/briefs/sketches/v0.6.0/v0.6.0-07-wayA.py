"""Way A: the live fixture manifest with one line `  "surroundings": null,` before `  "terrain"`."""
import hashlib, sys
from pathlib import Path
repo, out = Path(sys.argv[1]), Path(sys.argv[2])
for name in ["terrain_fixture","terrain_fixture_nw","buildings_fixture","photo_fixture","roofs_fixture","surfaces_fixture","trees_fixture","shadows_fixture"]:
    raw = (repo/"tests/shared"/name/"generated/manifest.json").read_bytes()
    lines = raw.decode("utf-8").split("\n")
    at = [i for i,l in enumerate(lines) if l.startswith('  "terrain": ')]
    assert len(at) == 1, name
    at = at[0]
    assert lines[at-1].startswith('  ') and lines[at-1].endswith(','), (name, lines[at-1])
    assert '"surroundings"' not in raw.decode(), name
    new = "\n".join(lines[:at] + ['  "surroundings": null,'] + lines[at:]).encode("utf-8")
    (out/name).mkdir(parents=True, exist_ok=True)
    (out/name/"manifest.json").write_bytes(new)
    print(name, hashlib.sha256(raw).hexdigest(), hashlib.sha256(new).hexdigest(), len(new))
