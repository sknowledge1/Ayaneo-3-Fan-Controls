# Install Ayaneo3 Fans in Decky

**Ayaneo3 Fans is the Decky plugin in this repository.** It appears in Steam's
Quick Access Menu under Decky's plug icon. The native OGUI frontend has a
[separate installation guide](NATIVE_INSTALL.md).

All AYANEO 3 CPU variants are allowed, including Ryzen 7 8840U and Ryzen AI 9
HX 370. You need Linux/Bazzite with the `ayaneo_ec` fan interface and valid CPU
temperature telemetry. The physical test device is the 8840U model; the other
variant paths have simulated tests. See [compatibility and validation](VALIDATION.md).

## What you need

- Your AYANEO 3 running Bazzite 44, with Desktop Mode access and your sudo password.
- Decky Loader installed. If its plug icon is missing, follow the
  [official Decky installation instructions](https://github.com/SteamDeckHomebrew/decky-loader#-installation).
- The shared fan service from this project. The Decky ZIP is the frontend and
  does not install that privileged service. The native OGUI plugin is optional.

## 1. Download the release on your AYANEO 3

1. Switch to **Desktop Mode**.
2. Open the [latest release](https://github.com/sknowledge1/Ayaneo-3-Fan-Controls/releases/latest).
3. Download **Ayaneo-3-Fan-Controls-v0.4.0.zip** from **Assets**. This is the complete
   release bundle with the installer and built frontends; GitHub's automatically
   generated “Source code” archives require additional build steps.
4. Extract it and open the **Ayaneo-3-Fan-Controls** folder that contains
   `README.md`, `scripts`, and `deploy-manifest.json`.
5. Keep `dist/Ayaneo3-Fans.zip` available for the Decky installation below.
   You can also download [Ayaneo3-Fans.zip directly](https://github.com/sknowledge1/Ayaneo-3-Fan-Controls/releases/latest/download/Ayaneo3-Fans.zip).

## 2. Install or update the shared fan service

1. In the extracted folder, open a terminal using the file manager's **Open
   Terminal Here** action.
2. Run this command as your normal desktop account and enter your sudo password:

   ```sh
   sudo python3 scripts/install-device.py . --user "$USER" --backend-only
   ```

3. Verify that it started:

   ```sh
   systemctl is-active ay3-fancontrol.service
   python3 /var/lib/ay3-fancontrol/app/ay3_fancontrol.py --status
   ```

   The first command should print `active`; the status should have `"ok": true`,
   a current temperature/RPM sample, and no fault. A new installation starts in
   firmware automatic mode. Updating preserves saved fan settings.

This route installs only the shared service. It does not install the native
OGUI frontend. If the service was already installed by this project's installer,
rerun this step to update it. If it is RPM-managed, update it through the package
manager instead of placing a manual unit over the packaged one.

## 3. Add the plugin to Decky

1. Return to **Gaming Mode**.
2. Open Steam's **Quick Access Menu** (the …/Quick Access menu) and select the
   **Decky plug icon**.
3. Open **Decky Settings** with its gear icon.
4. Under **General**, enable **Developer Mode** in Decky.
5. Open Decky's **Developer** page.
6. Under **Install Plugin from ZIP File**, choose **Browse** and select
   `Ayaneo3-Fans.zip` from the extracted bundle's `dist` folder or Downloads.
7. Confirm the plugin installation. Return to the plugin list and open
   **Ayaneo3 Fans**. If Decky still shows an old entry, restart Decky or reboot.

These controls are provided by Decky's official
[General settings](https://github.com/SteamDeckHomebrew/decky-loader/blob/main/frontend/src/components/settings/pages/general/index.tsx)
and [Developer settings](https://github.com/SteamDeckHomebrew/decky-loader/blob/main/frontend/src/components/settings/pages/developer/index.tsx).

### Alternative: install the Decky frontend from URL

After installing the shared service, use **Developer → Install Plugin from URL**,
paste this URL, choose **Install**, and confirm:

```text
https://github.com/sknowledge1/Ayaneo-3-Fan-Controls/releases/latest/download/Ayaneo3-Fans.zip
```

Use the Decky archive for this step. The complete release bundle and the native
OGUI ZIP have different layouts and should not be selected in Decky's installer.

## 4. Use the fan controls

1. Open **Decky → Ayaneo3 Fans** and check the live RPM and CPU temperature.
2. Select **Automatic**, **Manual**, **Custom curve**, or **Quiet**.
3. Adjust any values and select **Apply changes**.
4. To hand control back to the device firmware, select **Restore automatic control**.

The setting range is 0–100%. Zero permits a stop while cool; nonzero output has a
10% running floor. The shared temperature policy reaches full fan at 95 C and
hands back to firmware at 98 C. These protections can raise the actual fan duty
above a selected value. See [fan profiles](../README.md#fan-profiles).

## Updating from AY3 Fan Control

The old display name was **AY3 Fan Control**. In Decky Settings → Plugins,
uninstall that old frontend entry before installing **Ayaneo3 Fans** from the new
ZIP. This removes the Decky frontend only; the shared service retains the fan
profile. Update the service using step 2 and install the new ZIP using step 3.

The internal plugin folder remains `~/homebrew/plugins/ay3-fancontrol` for upgrade
compatibility. The service name/socket/config paths also remain stable. The
display name in Decky is **Ayaneo3 Fans**.

## Troubleshooting

- **Fan service unavailable:** complete step 2 and check
  `sudo journalctl -u ay3-fancontrol.service -b`. The plugin ZIP alone is insufficient.
- **Unsupported hardware or missing telemetry:** check the AYANEO 3 identity,
  `ayaneo_ec` driver, and `k10temp` Tctl sensor. No CPU-name allowlist is used.
- **Plugin absent:** use Decky Settings → Plugins to check whether it is hidden or
  disabled, and confirm you installed the Decky ZIP.
- **Native OGUI menu wanted instead:** follow [the native guide](NATIVE_INSTALL.md).

This is a manually distributed community plugin; it is not currently listed or
approved in the official Decky store. [Submission status](DECKY_SUBMISSION.md)
records the outstanding policy/testing requirements.
