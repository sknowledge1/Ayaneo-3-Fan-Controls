# Validation

Physically tested on AYANEO 3 / Ryzen 7 8840U / BIOS 1.00 with Bazzite Deck 44,
kernel 7.2.4-ogc3.1.fc44.x86_64, OGUI 0.46.1, and Godot 4.7.2.

All AYANEO 3 CPU names are eligible. Tests cover HX 370, arbitrary/missing CPU
names, product identity with a different board name, wrong device families,
renumbered hwmon paths, and missing/invalid Tctl telemetry. Other CPU variants
have not yet had physical thermal validation.

## Automated coverage

- Backend configuration, interpolation, Quiet, zero-duty restart/hysteresis,
  sensor/write/ownership/stall/watchdog recovery, and protocol version 1.
- Installer schema-v2 ownership migration, backend-only/native selection,
  preserved configuration, and Decky file detachment.
- Native menu widgets, overlay filtering, stock card expansion, nested controller
  focus, encoded process transport, legacy protocol acceptance, and rejection of
  unknown/malformed protocols.

Native tests use an isolated `XDG_DATA_HOME` and log file. The stock-card fixture
has known Godot resource-teardown warnings; functional assertions pass.

## Device coverage

- Duty/RPM probes including stopped fan at 0% and restart at 10%.
- Manual, curve, Quiet, automatic handoff, service restart, crash/watchdog,
  suspend/resume, and reboot behavior.
- Native user visibility and controller focus through Guide/Home + B.
- Settings preserved across v0.4 updates and the v0.5 repository split.

The 95 C full-fan and 98 C recovery boundaries use simulated telemetry. The test
device was not deliberately heated to those thresholds. Quiet has no sustained
acoustic or gaming soak. Physical HX 370 validation remains outstanding.
