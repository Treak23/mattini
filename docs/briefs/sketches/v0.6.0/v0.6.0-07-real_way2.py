"""Way 2 (no mattini code): the real village's manifest after `surroundings` and `farcolour`,
assembled by hand from the two descriptions the steps wrote and the committed world."""
import hashlib, json, sys
from pathlib import Path
out, world_path = Path(sys.argv[1]), Path(sys.argv[2])
world = world_path.read_bytes()
heights = json.loads((out / "surroundings" / "village.json").read_bytes())
colour = json.loads((out / "surroundings" / "village_colour.json").read_bytes())
assert not set(heights) & set(colour) and len(heights) + len(colour) == 20
blocks = ["buildings","photo","roofs","shadows","sky","surfaces","surroundings","terrain","trees"]
m = dict.fromkeys(blocks)
m.update(schema=1, surroundings={**heights, **colour}, world=json.loads(world), world_sha256=hashlib.sha256(world).hexdigest())
raw = (json.dumps(m, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()
print(hashlib.sha256(raw).hexdigest(), len(raw), raw == (out / "manifest.json").read_bytes())
