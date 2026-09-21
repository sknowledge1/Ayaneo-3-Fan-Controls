#!/usr/bin/env python3
"""Remove the installed AY3 components, preserving settings and backups."""
import json
import os
from pathlib import Path
import subprocess

if os.geteuid() != 0:
    raise SystemExit("Run with sudo")
state = Path("/var/lib/ay3-fancontrol")
marker = state / "installation.json"
record = json.loads(marker.read_text())
if record.get("project") != "ay3-fancontrol":
    raise SystemExit("Unexpected installation marker")
units = ["ay3-fancontrol-sleep.service", "ay3-fancontrol.service"]
for unit in units:
    subprocess.run(["systemctl", "disable", "--now", unit], check=False)
fan_root = Path("/sys/devices/platform/ayaneo-ec/hwmon").resolve()
for fan in Path("/sys/class/hwmon").glob("hwmon*"):
    if (fan / "name").read_text().strip() == "ayaneo_ec" and fan.resolve().is_relative_to(fan_root):
        if (fan / "pwm1_enable").read_text().strip() != "2":
            raise SystemExit("Automatic mode is not verified; retaining recovery files")
        break
else:
    raise SystemExit("Fan interface missing; retaining recovery files")
user_home = Path(record.get("user_home", "/home/bazzite"))
legacy_decky = user_home / "homebrew/plugins/ay3-fancontrol"
managed_files = []
detached_decky = []
for text in record["files"]:
    if Path(text).resolve().is_relative_to(legacy_decky.resolve()):
        detached_decky.append(text)
    else:
        managed_files.append(text)
if detached_decky:
    migration = state / "detached-decky-v0.5.0.json"
    migration.write_text(json.dumps({"schema_version": 1,
                                     "reason": "Native uninstall preserved Decky-owned Ayaneo3 Fans files",
                                     "preserved_files": detached_decky}, indent=2) + "\n")
    os.chmod(migration, 0o600)
allowed_roots = [state / "app"]
native_zip = user_home / ".local/share/opengamepadui/plugins/ayaneo-fan-control.zip"
allowed_units = [Path("/etc/systemd/system") / unit for unit in units]
for text in managed_files:
    target = Path(text)
    if target not in allowed_units and target.resolve() != native_zip.resolve() and not any(target.resolve().is_relative_to(root.resolve()) for root in allowed_roots):
        raise SystemExit("Unexpected installed path: " + text)
for text in managed_files:
    Path(text).unlink(missing_ok=True)
for directory in [allowed_roots[0]]:
    try:
        directory.rmdir()
    except OSError:
        pass
marker.rename(state / "uninstalled.json")
subprocess.run(["systemctl", "daemon-reload"], check=True)
print("Removed native AYANEO 3 Fan Controls. Settings, backups, and Decky-owned Ayaneo3 Fans files remain. Restart OGUI or reboot to unload its native menu.")
