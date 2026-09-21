# Install native OGUI Fan Controls

**This is the native Bazzite/OpenGamepadUI frontend.** It appears as **Fan Controls**
in the stock OGUI menu. Decky is not required. For the **Ayaneo3 Fans** Decky
plugin, use [the Decky guide](DECKY_INSTALL.md).

All AYANEO 3 CPU variants are allowed. The service requires the existing
`ayaneo_ec` fan interface and valid `k10temp` Tctl telemetry. OGUI Plugin API 2.0
and Python 3.10+ are required; the tested Bazzite 44 stack provides them.

## Install from a release

1. In **Desktop Mode**, open the
   [latest release](https://github.com/sknowledge1/Ayaneo-3-Fan-Controls/releases/latest).
2. Download and extract **Ayaneo-3-Fan-Controls-v0.4.0.zip** from Assets.
3. Open the extracted **Ayaneo-3-Fan-Controls** folder containing `scripts` and
   `deploy-manifest.json`, then open a terminal there.
4. Install the shared fan service and native OGUI frontend:

   ```sh
   sudo python3 scripts/install-device.py . --user "$USER"
   ```

5. Restart the gaming session or reboot so OGUI loads the native ZIP.
6. Hold **Guide/Home** and press **B** to open OGUI, then expand **Fan Controls**.
7. Choose a fan mode and select **Apply changes**. **Restore automatic control**
   returns ownership to the firmware.

Guide/Home + B was confirmed on the test AYANEO 3. The RC shortcut depends on the
active device mapping. Native packages before v0.3.1 had overlay-tag/focus defects;
use the current release.

The native ZIP installs at
`~/.local/share/opengamepadui/plugins/ayaneo-fan-control.zip`. It belongs to OGUI,
not Decky's ZIP installer. The installer retains existing fan settings and stores
backups of managed files. See [validation](VALIDATION.md) for tested scope.

## Install both frontends

With Decky already installed, run this from the extracted complete release bundle:

```sh
sudo python3 scripts/install-device.py . --user "$USER" --with-decky
```

This installs the shared service, the native OGUI frontend, and **Ayaneo3 Fans**
for Decky. Both menus edit the same saved profile through one controller. A change
applied in either menu is reflected in the other.

## Build from source

```sh
python3 scripts/build-native.py
python3 scripts/create-deploy-manifest.py
sudo python3 scripts/install-device.py . --user "$USER"
```

## Remove the manual installation

From the extracted release/source folder, run:

```sh
sudo python3 scripts/uninstall-device.py
```

This removes components recorded by the installer after verifying firmware
automatic control. It retains settings/backups under `/var/lib/ay3-fancontrol`.
If the installer also managed the Decky frontend, that frontend is removed too.
Restart OGUI or reboot to unload its menu. RPM-managed installations should be
removed through their package manager instead.
