# Fan service protocol 1

The shared service owns the AYANEO 3 fan and accepts newline-delimited JSON over
the local Unix socket `/run/ay3-fancontrol/control.sock`.

## Requests

Read current state:

```json
{"operation":"status"}
```

Replace the complete saved configuration:

```json
{
  "operation": "configure",
  "config": {
    "mode": "quiet",
    "percent": 15,
    "curve": [10, 30, 40, 70, 100]
  }
}
```

`mode` is one of `auto`, `manual`, `curve`, or `quiet`. Percentages are integers
from 0 through 100. The five custom values must be nondecreasing and end at 100.
Unknown keys and request shapes are rejected. Requests are limited to 4096 bytes.

## Successful response

Every successful status/configure response contains:

- `ok: true`
- `api_version: 1`
- service `version`
- complete `config`
- temperature `anchors` and backend-owned `quiet_points`
- `full_speed_c`, `recovery_c`, and minimum duty fields
- current `telemetry`, `sample_age_s`, `effective_percent`, and `fault`
- `automatic_verified`

A configure response describes the state after applying or safely recovering from
the request. `ok: false` includes a user-facing `error` and never represents a
successful configuration write.

## Compatibility

v0.4 responses omitted `api_version` but used the same request and configuration
schema. v0.5 clients accept a missing version only when the known protocol-1
configuration shape is present, then normalize it to version 1. Any explicit
version other than 1 is rejected before clients send configuration writes.

Clients must treat telemetry older than five seconds as unavailable and must not
derive fan ownership from a PWM value in firmware automatic mode.
