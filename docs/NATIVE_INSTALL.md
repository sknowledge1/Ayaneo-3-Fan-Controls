# Install native OGUI Fan Controls

This repository installs the shared fan service and the native Bazzite/OpenGamepadUI
frontend. Decky is not required. Ayaneo3 Fans for Decky is maintained separately:
https://github.com/sknowledge1/Ayaneo3-Fans

All AYANEO 3 CPU variants are allowed. The existing `ayaneo_ec` fan interface,
AYANEO 3 identity, and valid `k10temp` Tctl telemetry are required.

## Install from a release

1. Download and extract `Ayaneo-3-Fan-Controls-v0.5.1.zip` from the latest release.
2. Open a terminal in the extracted directory.
3. Install the service and native frontend:

   ```sh
   sudo python3 scripts/install-device.py . --user "$USER"
   ```

4. Restart the gaming session or reboot.
5. Open OGUI with **Guide/Home + B**, expand **Fan Controls**, and apply a mode.

To install only the service for another compatible client:

```sh
sudo python3 scripts/install-device.py . --user "$USER" --backend-only
```

Updating from the combined v0.4.0 installer preserves settings and the installed
Decky frontend, then detaches Decky's files from native installer ownership.
Decky Loader owns Ayaneo3 Fans after that migration.

## Verify

```sh
systemctl is-active ay3-fancontrol.service
python3 /var/lib/ay3-fancontrol/app/ay3_fancontrol.py --status
```

The status should report `api_version: 1`, current RPM/temperature telemetry, and
no fault. A new installation starts in firmware automatic mode.

## Remove

```sh
sudo python3 scripts/uninstall-device.py
```

The uninstaller verifies firmware automatic mode and removes only backend/native
files recorded after ownership migration. It retains saved settings, backups,
and all Decky-owned files. Restart OGUI or reboot to unload the menu.
