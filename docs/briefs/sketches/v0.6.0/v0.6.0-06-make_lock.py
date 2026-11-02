import json, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]) / "pipeline/tests"))
from synthetic_farphoto import FIXTURE, raw_inputs
with tempfile.TemporaryDirectory() as d:
    _, lock = raw_inputs(Path(d))
    lock = {"datasets": lock["datasets"], "schema": 1}
(FIXTURE / "datasets.lock.json").write_bytes((json.dumps(lock, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode())
print(sorted(lock["datasets"]), {k: len(v["tiles"]) for k, v in lock["datasets"].items()})
