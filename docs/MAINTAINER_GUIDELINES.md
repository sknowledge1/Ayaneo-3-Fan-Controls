# Maintainer guidance

This is the native/service repository. Ayaneo3 Fans for Decky is separately
released and is not part of the OGUI store archive.

The native frontend uses OGUI Plugin API 2.0, the exact `quick-bar` tag, stock
widgets, and FocusGroup navigation. It is a thin client to one supervised service.
It does not replace OGUI, InputPlumber, PowerStation, the kernel driver, charging,
RGB, detachable-module, or TDP behavior.

The backend uses only the existing kernel hwmon contract. It validates AYANEO 3
identity, resolved `ayaneo_ec` physical paths, a unique Tctl sensor, mode/readback,
RPM, and temperature. Firmware automatic remains the default and recovery state.

Open questions for upstream review:

- accept the focused service initially or move ownership into PowerStation;
- approve 95 C full fan and 98 C firmware handoff for both known variants;
- approve the packaged authorization model;
- require physical HX 370 validation before stable image promotion.

The project includes Codex-assisted code and discloses that provenance. Terra and
Universal Blue policy clarification is required before submitting policy-covered
packaging or image changes. Local compatibility is not upstream approval.
