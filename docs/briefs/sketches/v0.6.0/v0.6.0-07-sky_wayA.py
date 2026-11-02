"""Way A (no mattini): a folder holding only a fixture's sky description: the manifest by hand."""
import hashlib, json, sys
from pathlib import Path
shared = Path(sys.argv[1])
blocks = ["buildings","photo","roofs","shadows","sky","surfaces","surroundings","terrain","trees"]
for name in ("shadows_fixture", "surroundings_fixture"):
    world = (shared/name/"world.json").read_bytes()
    m = dict.fromkeys(blocks)
    m["sky"] = json.loads((shared/name/"generated/sky/fixture.json").read_bytes())
    m.update(schema=1, world=json.loads(world), world_sha256=hashlib.sha256(world).hexdigest())
    raw = (json.dumps(m, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()
    print(name, hashlib.sha256(raw).hexdigest(), len(raw))
