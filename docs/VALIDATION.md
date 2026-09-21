# Validation

Tested hardware: AYANEO 3, Ryzen 7 8840U, BIOS 1.00. Tested software: Bazzite Deck
44.20260919.0, kernel 7.2.4-ogc3.1.fc44.x86_64, OGUI 0.46.1, Decky 3.2.9.

## Model eligibility in v0.4.0

All AYANEO 3 CPU variants are allowed. The backend and proposed distribution
helper no longer read or filter CPU names. The shared `ayaneo_ec` fan-path and
`k10temp` Tctl checks still apply. Fake-hardware tests cover HX 370, arbitrary CPU
names, product identity with a different board name, absent cpuinfo, and refusal when valid temperature telemetry is missing.
Only the 8840U unit has been physically tested here; enabling other variants is
not a claim that they have had hardware or thermal validation.

v0.4.0 also renames the Decky frontend to Ayaneo3 Fans and adds a backend-only
installer route. Five installer tests use an isolated filesystem and mocked service
calls to verify frontend selection, preserved settings/files, and invalid flags.

## Automated checks

- v0.3.1 adds a regression test using the actual installed OGUI overlay filter and
  stock expanding card. v0.3.0 failed tag selection and controller-focus checks:
  it used `quick_bar` instead of `quick-bar` and lacked the expected FocusGroup.
  These are corrected in v0.3.1. Earlier registration logs alone did not establish
  a reachable menu in the user's Steam overlay.
- Native test runs now use an isolated `XDG_DATA_HOME` and explicit `--log-file`.
  Running against the stock PCK with only `--path` still uses the normal OGUI
  user-data directory; that can overwrite the running session's Godot log.
- 43 backend tests cover hardware identity, path changes, configuration bounds,
  sensor/write faults, stale telemetry, recovery, intentional zero duty, restart
  grace, and encoded native transport. v0.3.0 adds Quiet outputs, preservation of
  custom settings, restart hysteresis, immediate heating response, and full duty
  at 95 C through just below the 98 C recovery boundary for all software modes.
- 30 native menu checks cover standard widgets, pending edits, zero minimum,
  Quiet selection/preview, the 95 C endpoint, reconnection, Plugin API registration,
  and the actual stock Quick Bar card.
- Three hardware-free native transport tests verify zero, custom curve, and Quiet
  payloads through Godot's process API and the backend decoder.
- Two Decky callback tests use an isolated Node VM with hook stubs to verify
  Quiet selection across polling/remounts, apply payloads, custom-setting
  preservation, and the fixed 95 C endpoint. They do not use a browser or hardware.
- The corrected native client successfully reapplied the existing user-selected
  curve through the real service without substituting a test setting, including
  with Decky stopped.
- The stock-card test fixture emits resource-teardown warnings from its isolated
  stock-resource setup; its functional assertions pass.

## Device checks

For v0.3.1, the user confirmed Fan Controls appears in the actual stock overlay
when opened with Guide/Home + B. The RC path they initially used did not expose
the menu. The update preserves Quiet and the custom values. The new overlay
fixture passes eight checks, including expansion and controller focus into both
the main controls and custom-curve sliders. No input mappings were changed.

For v0.3.0, installation and a normal reboot preserved the selected automatic
mode and saved custom settings. The installed native ZIP matched the tested
archive; stock OGUI initialized it and registered Fan Controls without script
errors. An unchanged-current-configuration roundtrip through the native client
passed against the updated service, with no controller fault.

The duty/load/lifecycle probes below were performed for v0.1/v0.2. They validate
the shared hardware/recovery path; they are not a thermal soak of the Quiet preset.

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

The new 95/98 C boundaries were tested with simulated telemetry. The device was
not deliberately heated to those limits. Quiet has not had a sustained gaming
soak or an acoustic measurement; the preset describes commanded duty, not a
guaranteed noise level or maximum observed CPU temperature.
