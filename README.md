# AYANEO 3 Fan Controls for Bazzite / OpenGamepadUI

Native fan controls for every AYANEO 3 CPU variant, using Bazzite's stock
OpenGamepadUI quick-access menu and the existing `ayaneo_ec` kernel interface.
This repository also owns the single supervised fan service used by native OGUI
and compatible external clients.

Looking for Decky? **Ayaneo3 Fans is now a separate project:**
https://github.com/sknowledge1/Ayaneo3-Fans

## Native controls

- Firmware automatic, manual duty, custom curve, and Quiet modes.
- 0–100% settings; zero permits a fan stop while cool.
- Tested 10% minimum nonzero running duty.
- Full fan at 95 C and firmware handoff at 98 C, pending maintainer review.
- Live RPM, CPU temperature, effective duty, and fault state.
- Independent watchdog, sensor/write/stall recovery, and suspend/resume handoff.

All AYANEO 3 CPU names are accepted. The controller still requires AYANEO vendor
plus AYANEO 3 product/board identity, exactly one valid `ayaneo_ec` fan interface,
and exactly one `k10temp` Tctl sensor. Physical validation is currently on the
Ryzen 7 8840U model; HX 370 and other CPU-name paths have simulated coverage.

## Install native OGUI Fan Controls

Download and extract the complete native/service bundle from the latest release,
then run inside the extracted directory:

```sh
sudo python3 scripts/install-device.py . --user "$USER"
```

Restart the gaming session or reboot. Open OGUI with **Guide/Home + B**, expand
**Fan Controls**, choose a mode, and select **Apply changes**.

For the service without the native frontend:

```sh
sudo python3 scripts/install-device.py . --user "$USER" --backend-only
```

See [the complete native installation guide](docs/NATIVE_INSTALL.md).

## Shared service protocol

The service listens on `/run/ay3-fancontrol/control.sock`. Protocol 1 retains the
v0.4 request/configuration schema and adds `api_version: 1` to successful status
responses. See [the protocol contract](docs/PROTOCOL.md).

The service is the only fan writer. Client or menu closure does not interrupt its
control loop. Firmware automatic remains the default and recovery destination.

## Build and test

```sh
python3 -m unittest discover -s tests -v
python3 scripts/build-native.py
python3 scripts/create-deploy-manifest.py
```

Godot integration tests require a matching Godot development executable and the
stock OGUI PCK. See [validation](docs/VALIDATION.md).

## Packaging and source layout

- `backend/`: shared Python controller and socket server.
- `native/`: OGUI Plugin API 2.0 frontend and Godot tests.
- `systemd/`: supervised service and sleep handoff.
- `scripts/`: deterministic packaging, install, and rollback tools.
- `packaging/`: downstream package material once accepted upstream.

Internal identifiers (`ay3-fancontrol.service`, socket/config paths, and native
plugin ID `ayaneo-fan-control`) remain stable for upgrades.

## Safety and limits

The 95 C full-fan point is not a guaranteed maximum temperature. Hot thresholds
are tested with simulated telemetry; the device was not deliberately heated to
95/98 C. Quiet has not had a sustained acoustic or thermal soak. Other AYANEO 3
variants are enabled but have not yet had physical validation here.

This is a community project, not an official Bazzite release. See
[maintainer guidance](docs/MAINTAINER_GUIDELINES.md) and the
[OGUI store submission notes](docs/OGUI_SUBMISSION.md).

Project code is MIT licensed.
