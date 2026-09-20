#!/usr/bin/env python3
"""Build the documented OGUI ZIP resource-pack format without replacing stock files."""
from pathlib import Path
import hashlib
import json
import zipfile

root = Path(__file__).resolve().parents[1]
native = root / "native"
metadata = json.loads((native / "plugin.json").read_text())
identifier = metadata["plugin.id"]
if identifier != "ayaneo-fan-control":
    raise SystemExit("Unexpected plugin ID")
destination = root / "dist"
destination.mkdir(exist_ok=True)
archive_path = destination / f"{identifier}-{metadata['plugin.version']}.zip"
files = [(p.relative_to(native).as_posix(), p) for p in native.rglob("*") if p.is_file()]
files.append(("LICENSE", root / "LICENSE"))
with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for relative, path in sorted(files):
        if relative.startswith("tests/"):
            continue
        member = zipfile.ZipInfo(f"plugins/{identifier}/{relative}", (1980, 1, 1, 0, 0, 0))
        member.compress_type = zipfile.ZIP_DEFLATED
        member.external_attr = 0o100644 << 16
        archive.writestr(member, path.read_bytes())
print(json.dumps({"file": str(archive_path), "sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest()}))
