#!/usr/bin/env python3
from pathlib import Path
import hashlib
import json
import zipfile

root = Path(__file__).resolve().parents[1]
plugin = root / "plugin" if (root / "plugin/plugin.json").exists() else root
metadata = json.loads((plugin / "package.json").read_text())
output = root / "dist"
output.mkdir(exist_ok=True)
archive_path = output / f"ay3-fan-control-decky-{metadata['version']}.zip"
paths = ["main.py", "plugin.json", "package.json", "dist/index.js", "LICENSE", "LICENSE.decky-api"]
with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for relative in paths:
        info = zipfile.ZipInfo("ay3-fancontrol/" + relative, (1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        archive.writestr(info, (plugin / relative).read_bytes())
print(json.dumps({"file": str(archive_path), "sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest()}))
