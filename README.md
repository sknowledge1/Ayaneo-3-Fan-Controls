# AYANEO 3 Fan Controls

**This repository contains BOTH a Decky plugin and a native Bazzite/OGUI plugin.**
They are separate frontends. Install either one, or both, with the shared fan service.

| Frontend | Name you will see | Where it appears | Installation guide |
| --- | --- | --- | --- |
| **1. Decky plugin** | **Ayaneo3 Fans** | Steam Quick Access Menu → Decky plug icon | [Install in your Decky](docs/DECKY_INSTALL.md) |
| **2. Native Bazzite/OGUI plugin** | **Fan Controls** | Stock OGUI menu, opened with Guide/Home + B | [Install native OGUI controls](docs/NATIVE_INSTALL.md) |

**All AYANEO 3 models are eligible, regardless of CPU.** This includes the Ryzen 7
8840U and Ryzen AI 9 HX 370 variants. There is no CPU-name allowlist. The controller
still verifies AYANEO 3 identity, the existing `ayaneo_ec` fan interface, and valid
CPU temperature telemetry before taking control. Other AYANEO device families are
not enabled by this project. Hardware validation so far used an 8840U unit; other
CPU variants are enabled and covered by simulated compatibility tests.

## 1. Decky plugin — Ayaneo3 Fans

Ayaneo3 Fans provides Automatic, Manual, Custom curve, and Quiet modes directly
in Decky, with live fan RPM and CPU temperature.

**[Step-by-step: add Ayaneo3 Fans to your Decky](docs/DECKY_INSTALL.md)**

1. [Download the complete release bundle](https://github.com/sknowledge1/Ayaneo-3-Fan-Controls/releases/latest) and extract it on your AYANEO 3.
2. Install/update the shared service from the extracted folder:

   ```sh
   sudo python3 scripts/install-device.py . --user "$USER" --backend-only
   ```

3. In Decky Settings → General, enable Developer Mode. Open Developer → Install
   Plugin from ZIP File and select **[Ayaneo3-Fans.zip](https://github.com/sknowledge1/Ayaneo-3-Fan-Controls/releases/latest/download/Ayaneo3-Fans.zip)**.
4. Open **Decky → Ayaneo3 Fans**, choose a mode, and select **Apply changes**.

The Decky ZIP requires the shared service. It does not require the native OGUI
frontend. The detailed guide includes installation from URL, updating the old
**AY3 Fan Control** entry, verification, and troubleshooting.

## 2. Native Bazzite/OGUI plugin — Fan Controls

The native frontend places the same controls in Bazzite’s stock OGUI quick-access
menu. It uses OGUI’s Plugin API 2.0 and stock controls; Decky is not required.

**[Step-by-step: install native OGUI Fan Controls](docs/NATIVE_INSTALL.md)**

From the extracted complete release bundle:

```sh
sudo python3 scripts/install-device.py . --user "$USER"
```

Restart the gaming session or reboot, then open **Guide/Home + B → Fan Controls**.
To install both frontends together, use `--with-decky` with Decky already installed.

## Shared fan service

Both frontends communicate with one supervised `ay3-fancontrol.service`. It uses
the existing kernel hwmon interface, saves one common profile, and continues
controlling the fan when a menu is closed. A change applied in either frontend is
reflected in the other. Firmware automatic is the default for a new installation.

| Release file | Purpose |
| --- | --- |
| `Ayaneo3-Fans.zip` / `ayaneo3-fans-decky-0.4.0.zip` | Decky frontend; install through Decky after the service |
| `ayaneo-fan-control-0.4.0.zip` | Native OGUI frontend; installed by the native installer |
| `Ayaneo-3-Fan-Controls-v0.4.0.zip` | Complete bundle: shared service, both built frontends, installer, and guides |
| `SHA256SUMS` | Release checksums |

The stable internal folder/service identifiers retain `ay3-fancontrol` for upgrade
compatibility. The Decky display name is **Ayaneo3 Fans**.

## Fan profiles

- **Automatic:** firmware controls cooling.
- **Manual:** select 0–100% duty; temperature protection can raise the actual output.
- **Custom curve:** five points at 40/55/65/75/95 C, ending at 100% fan.
- **Quiet:** a gentler preset that allows warmer operation while preserving your
  custom curve and manual setting.

| Quiet temperature | 45 C or below | 55 C | 65 C | 75 C | 85 C | 90 C | 95 C |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Fan duty | 0% | 15% | 25% | 35% | 55% | 75% | 100% |

Zero permits fan stop while cool. Nonzero output uses a 10% running floor; restart
begins above 45 C and a running fan can stop again at 42 C. Duty can rise
immediately and decreases gradually in curve/Quiet modes.

Full fan begins at **95 C**, with firmware handoff at **98 C**. These are software
policy points, not a guaranteed cap on observed temperature. Sensor, stall,
ownership, sampling, and watchdog recovery remain active. Sustained Quiet
thermal/acoustic testing has not been performed. [Validation and limits](docs/VALIDATION.md).

## Source layout and builds

| Component | Source |
| --- | --- |
| Decky / Ayaneo3 Fans | `plugin.json`, `package.json`, `main.py`, `src/panel.js` |
| Native OGUI | `native/` |
| Shared service | `src/ay3_fancontrol.py`, `systemd/` |

```sh
pnpm install --frozen-lockfile
pnpm build
python3 scripts/build-decky-package.py
python3 scripts/build-native.py
python3 scripts/create-deploy-manifest.py
pnpm test
```

Use pnpm 9.15.9 and Node 18.12+. The frontend bundles the readable, pinned
`@decky/api` source under `vendor/`. Native tests use the matching Godot development
executable and stock OGUI resources with isolated test user data/logs.

## Project and store status

This is a community project with Codex-assisted code, automated checks, and
device testing. It is not an official Bazzite release or an approved store listing.
[Maintainer guidance](docs/MAINTAINER_GUIDELINES.md) and
[Decky submission status](docs/DECKY_SUBMISSION.md) document the review and policy
requirements. Native Bazzite inclusion and Decky store inclusion are separate processes.

Project code is MIT-licensed. The bundled Decky API retains its LGPL license and
original source. See [third-party notices](THIRD_PARTY_NOTICES.md).
