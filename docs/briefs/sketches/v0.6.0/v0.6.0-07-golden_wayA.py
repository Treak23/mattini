"""Way A (no mattini): the terrain fixture's world, every block null, twelve keys, dumped."""
import hashlib, json, sys
from pathlib import Path
world = Path(sys.argv[1]).read_bytes()
blocks = ["buildings","photo","roofs","shadows","sky","surfaces","surroundings","terrain","trees"]
m = dict.fromkeys(blocks)
m.update(schema=1, world=json.loads(world), world_sha256=hashlib.sha256(world).hexdigest())
raw = (json.dumps(m, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()
print(hashlib.sha256(raw).hexdigest(), len(raw))
del m["surroundings"]
raw = (json.dumps(m, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()
print("eleven:", hashlib.sha256(raw).hexdigest(), len(raw))
