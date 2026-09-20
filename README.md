# Ayaneo 3 Fan Controls

Fan adjustments in **Bazzite's built-in OpenGamepadUI quick-access menu**, with an
optional Decky frontend. Both frontends use one supervised service and the existing
`ayaneo_ec` kernel interface. Decky is not required for the native controls.

This is a community add-on, not an official Bazzite release or an approved store
listing. It targets the **AYANEO 3 with Ryzen 7 8840U**. Other models are rejected by
the hardware guard until separately validated.

## Controls

- Firmware automatic control, manual duty, and a five-point custom curve.
- A **0-100%** setting: zero allows a cool-temperature stop. Nonzero output below
  10% uses the tested 10% running floor.
- Temperature-based cooling increases, full fan at 85 C, and automatic recovery at
  95 C. Restart begins above 45 C; stopping again requires cooling to 42 C.
- Live RPM, CPU temperature, and actual control state.
- Saved settings, suspend/resume handoff, and independent watchdog recovery.

The zero-duty probe measured a stopped fan at 0%, no rotation at 1%, and restart
at 10%. A duty percentage is not a linear RPM percentage. Temperature protection
can raise the effective duty above the selected value.

## Native Bazzite interface

Open the stock OGUI menu (normally the **RC button** on AYANEO), expand **Fan
Controls**, select a mode, adjust the values, and choose **Apply changes**.
**Restore automatic control** hands the fan back to firmware.

The native ZIP uses OGUI Plugin API 2.0, its standard quick-access card, dropdowns,
sliders, buttons, focus behavior, and typed GDScript. It does not replace the stock
OGUI binary, kernel, InputPlumber, or TDP implementation.

## Installation

Requirements: the tested Bazzite 44 handheld stack, Python 3.10+, OGUI Plugin API
2.0, and the `ayaneo_ec` driver. Start from a downloaded source archive or clone of
this public repository.

```sh
python3 scripts/build-native.py
python3 scripts/create-deploy-manifest.py
sudo python3 scripts/install-device.py . --user "$USER"
```

Restart the stock OGUI session or reboot to load the native menu. The installer
uses the selected desktop account, validates staged checksums, backs up managed
files, and leaves existing settings intact. It writes the service to `/var/lib`
and `/etc/systemd/system` and the native ZIP to the user's OGUI plugin directory;
it does not unlock or replace the immutable operating-system image.

### Optional Decky frontend

The native fan service must be installed first. Build and install the optional
frontend with:

```sh
pnpm install --frozen-lockfile
pnpm build
python3 scripts/create-deploy-manifest.py
sudo python3 scripts/install-device.py . --user "$USER" --with-decky
```

It appears as **AY3 Fan Control** in Decky's plug menu. The frontend does not run
with Decky's root flag; it talks to the same local service as OGUI. Installing only
the Decky ZIP without the service produces an explanatory unavailable state.

## Build and test

```sh
python3 -m unittest discover -s tests -v
node scripts/build-frontend.mjs
python3 scripts/build-native.py
python3 scripts/build-decky-package.py
```

Use pnpm 9.15.9 for the published version-9 lockfile. The frontend has no
install-time npm dependencies. The pinned, readable
`@decky/api` source and license are included under `vendor/`.

Native UI tests use the matching Godot 4.7.2 development executable with the stock
OGUI PCK resources. See [validation](docs/VALIDATION.md) and
[maintainer guidance](docs/MAINTAINER_GUIDELINES.md) for tested scope and limits.

## Service and rollback

```sh
python3 /var/lib/ay3-fancontrol/app/ay3_fancontrol.py --status
sudo journalctl -u ay3-fancontrol.service -b
sudo python3 scripts/uninstall-device.py
```

The uninstaller verifies automatic mode before removing the recorded components.
Settings and backups remain in `/var/lib/ay3-fancontrol`; restart OGUI or reboot to
remove the native menu from the running session.

## Provenance and official stores

This project includes code generated with **Codex**, followed by source review,
automated tests, and device testing. That provenance is disclosed for reviewers.

The official Decky rules currently reject LLM-based code, and actual SteamOS
testing is also required. **This repository is not claiming official-store
eligibility or approval.** See [Decky submission status](docs/DECKY_SUBMISSION.md).
OGUI/Bazzite inclusion also requires their maintainers' review.

## License

Project code is MIT-licensed. The bundled `@decky/api` retains its LGPL license in
`LICENSE.decky-api` and original source under `vendor/decky-api-1.1.3/`.
See [third-party notices](THIRD_PARTY_NOTICES.md).
