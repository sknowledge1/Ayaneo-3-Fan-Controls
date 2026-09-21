#!/usr/bin/env python3
"""Install only the reviewed AY3 files from the supplied staging directory."""
import hashlib
import argparse
import json
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import time

SCHEMA_VERSION = 2
DECKY_DIRECTORY = "homebrew/plugins/ay3-fancontrol"

if os.geteuid() != 0:
    raise SystemExit("Run the installer with sudo")
parser = argparse.ArgumentParser()
parser.add_argument("stage", type=Path)
parser.add_argument("--user", default=os.environ.get("SUDO_USER"))
parser.add_argument("--backend-only", action="store_true", help="Install/update only the shared fan service")
args = parser.parse_args()
if not args.user or args.user == "root":
    raise SystemExit("Specify the desktop account with --user")
account = pwd.getpwnam(args.user)
stage = args.stage.resolve()
state = Path("/var/lib/ay3-fancontrol")
user_home = Path(account.pw_dir)
legacy_decky = user_home / DECKY_DIRECTORY
native_directory = user_home / ".local/share/opengamepadui/plugins"
native_zip = native_directory / "ayaneo-fan-control.zip"
unit_root = Path("/etc/systemd/system")
marker = state / "installation.json"
mapping = {
    "backend/ay3_fancontrol.py": state / "app/ay3_fancontrol.py",
    "systemd/ay3-fancontrol.service": unit_root / "ay3-fancontrol.service",
    "systemd/ay3-fancontrol-sleep.service": unit_root / "ay3-fancontrol-sleep.service",
}
if not args.backend_only:
    native_metadata = json.loads((stage / "native/plugin.json").read_text())
    native_archive = f"dist/ayaneo-fan-control-{native_metadata['plugin.version']}.zip"
    mapping[native_archive] = native_zip
updating = marker.exists()
previous = None
detached_decky = {}
if updating:
    previous = json.loads(marker.read_text())
    if previous.get("project") != "ay3-fancontrol":
        raise SystemExit("Unexpected installation marker")
    if previous.get("uid", account.pw_uid) != account.pw_uid:
        raise SystemExit("This installation belongs to a different desktop account")
    for installed_path, digest in previous["files"].items():
        resolved = Path(installed_path).resolve()
        if resolved.is_relative_to(legacy_decky.resolve()):
            detached_decky[installed_path] = digest
    known_paths = {str(Path(path).resolve()) for path in previous["files"]}
    for destination in mapping.values():
        if destination.exists() and str(destination.resolve()) not in known_paths:
            raise SystemExit("New installation target already exists: " + str(destination))
elif any(path.exists() for path in [state, *mapping.values()]):
    raise SystemExit("Installation targets already exist; inspect them before proceeding")
expected = json.loads((stage / "deploy-manifest.json").read_text())
for relative in mapping:
    digest = hashlib.sha256((stage / relative).read_bytes()).hexdigest()
    if expected.get(relative) != digest:
        raise SystemExit("Staged file checksum mismatch: " + relative)

def run(*args):
    result = subprocess.run(args, text=True, capture_output=True, timeout=30)
    print(json.dumps({"command": list(args), "code": result.returncode,
                      "stdout": result.stdout, "stderr": result.stderr}), flush=True)
    result.check_returncode()

if updating:
    run("systemctl", "stop", "ay3-fancontrol.service")
    backup = state / "backups" / str(int(time.time()))
    for relative, destination in mapping.items():
        if destination.is_file():
            target = backup / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(destination, target)
else:
    state.mkdir(mode=0o750)
if detached_decky:
    migration = state / "detached-decky-v0.5.0.json"
    migration.write_text(json.dumps({"schema_version": 1,
                                     "reason": "Decky Loader owns Ayaneo3 Fans after the repository split",
                                     "preserved_files": detached_decky}, indent=2) + "\n")
    os.chmod(migration, 0o600)
installed_hashes = ({str(Path(path).resolve()): digest for path, digest in previous["files"].items()
                     if not Path(path).resolve().is_relative_to(legacy_decky.resolve())} if updating else {})
for relative, destination in mapping.items():
    destination.parent.mkdir(parents=True, exist_ok=True)
    content = (stage / relative).read_bytes()
    if relative == "systemd/ay3-fancontrol.service":
        content = content.replace(b"Group=bazzite", f"Group={account.pw_gid}".encode())
    digest = hashlib.sha256(content).hexdigest()
    changed = not destination.is_file() or hashlib.sha256(destination.read_bytes()).hexdigest() != digest
    if changed:
        destination.write_bytes(content)
    os.chown(destination, account.pw_uid if destination == native_zip else 0,
             account.pw_gid if destination == native_zip else 0)
    os.chmod(destination, 0o644)
    installed_hashes[str(destination.resolve())] = digest
directories = [state / "app"]
if not args.backend_only:
    directories.append(native_directory)
for directory in directories:
    if directory.exists():
        os.chmod(directory, 0o755)
if not args.backend_only:
    os.chown(native_directory, account.pw_uid, account.pw_gid)
if not (state / "config.json").exists():
    (state / "config.json").write_text(json.dumps({"mode": "auto", "percent": 60, "curve": [40, 50, 70, 85, 100]}, indent=2) + "\n")
    os.chmod(state / "config.json", 0o600)
marker.write_text(json.dumps({"project": "ay3-fancontrol", "schema_version": SCHEMA_VERSION,
                             "installed_at": time.time(),
                             "uid": account.pw_uid, "user_home": str(user_home),
                             "files": installed_hashes}, indent=2) + "\n")
run("systemd-analyze", "verify", str(unit_root / "ay3-fancontrol.service"), str(unit_root / "ay3-fancontrol-sleep.service"))
run("systemctl", "daemon-reload")
run("systemctl", "enable", "--now", "ay3-fancontrol.service")
run("systemctl", "enable", "ay3-fancontrol-sleep.service")
run("/usr/bin/python3", str(state / "app/ay3_fancontrol.py"), "--status")
print(json.dumps({"installed": True, "native_plugin": None if args.backend_only else str(native_zip),
                  "decky_detached": bool(detached_decky), "state": str(state),
                  "next_step": "Shared fan service is ready" if args.backend_only else "Restart the stock OGUI session or reboot to load the native plugin"}))
