# Validation

Tested hardware: AYANEO 3, Ryzen 7 8840U, BIOS 1.00. Tested software: Bazzite Deck
44.20260919.0, kernel 7.2.4-ogc3.1.fc44.x86_64, OGUI 0.46.1, Decky 3.2.9.

## Automated checks

- 31 backend tests cover hardware identity, path changes, configuration bounds,
  sensor/write faults, stale telemetry, recovery, intentional zero duty, restart
  grace, and encoded native transport.
- 22 native menu checks cover standard widgets, pending edits, zero minimum,
  reconnection, Plugin API registration, and the actual stock Quick Bar card.
- Two hardware-free native transport tests verify zero and curve payloads through
  Godot's process API and the backend decoder.
- The corrected native client successfully reapplied the existing user-selected
  curve through the real service without substituting a test setting, including
  with Decky stopped.
- The stock-card test fixture emits resource-teardown warnings from its isolated
  stock-resource setup; its functional assertions pass.

## Device checks

- Duty probes measured approximately 2780/3800/4680/5470 RPM at 40/60/80/100%.
- A bounded cool-idle probe measured zero RPM at 0% and 1%, then restart at 10%
  (about 713 RPM), 20% (about 1513 RPM), and 30% (about 2091 RPM).
- Manual and curve operation, SIGKILL recovery, watchdog recovery, and saved
  settings across service restart were exercised.
- A bounded four-worker CPU load increased commanded duty as temperature rose;
  the initial test observed 47.4-82.1 C and 45-96% duty with the menu closed.
- Suspend/resume and reboot behavior were exercised for the shared service.
- After a normal reboot, the unmodified stock OGUI runtime initialized the native
  plugin and registered its Fan Controls quick-access card without script errors.

The broader native multi-mode live test was rejected by automatic safety review
after an earlier argument-transport bug. It was replaced with package inspection,
hardware-free transport tests, and an unchanged-setting live roundtrip. That
rejected test is not presented as a successful run.

## Limits

Other CPU/device variants, a long gaming soak, physical AC/battery transitions,
future Bazzite updates, and the official SteamOS test matrix are not validated.
Neither Bazzite nor Decky maintainers have approved this project.
