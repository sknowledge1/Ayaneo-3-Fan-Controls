#!/usr/bin/env python3
from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parents[1]
metadata = json.loads((root / "native/plugin.json").read_text())
paths = ["src/ay3_fancontrol.py", "systemd/ay3-fancontrol.service", "systemd/ay3-fancontrol-sleep.service",
         f"dist/ayaneo-fan-control-{metadata['plugin.version']}.zip"]
prefix = "plugin/" if (root / "plugin/plugin.json").exists() else ""
if (root / (prefix + "dist/index.js")).exists():
    paths += [prefix + p for p in ["main.py", "plugin.json", "package.json", "dist/index.js", "LICENSE", "LICENSE.decky-api"]]
manifest = {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in paths}
(root / "deploy-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps({"files": len(manifest), "manifest": "deploy-manifest.json"}))
