#!/usr/bin/env python3
"""Build the complete native/service source bundle with deterministic metadata."""
from pathlib import Path
import hashlib
import json
import zipfile

root = Path(__file__).resolve().parents[1]
metadata = json.loads((root / "native/plugin.json").read_text())
version = metadata["plugin.version"]
native_archive = root / "dist" / f"ayaneo-fan-control-{version}.zip"
required = [native_archive, root / "deploy-manifest.json"]
if any(not path.is_file() for path in required):
    raise SystemExit("Build the native ZIP and deploy manifest first")

files = []
for name in ["README.md", "LICENSE", "deploy-manifest.json"]:
    files.append(root / name)
for directory in ["backend", "native", "systemd", "scripts", "tests", "docs", "packaging"]:
    files.extend(path for path in (root / directory).rglob("*")
                 if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc")
files.append(native_archive)

output = root / "dist" / f"Ayaneo-3-Fan-Controls-v{version}.zip"
with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for path in sorted(set(files)):
        relative = path.relative_to(root).as_posix()
        member = zipfile.ZipInfo(f"Ayaneo-3-Fan-Controls/{relative}", (1980, 1, 1, 0, 0, 0))
        member.compress_type = zipfile.ZIP_DEFLATED
        member.external_attr = 0o100644 << 16
        archive.writestr(member, path.read_bytes())
print(json.dumps({"file": str(output), "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))
