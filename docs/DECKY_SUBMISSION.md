# Official Decky submission status

Plugin display name: **Ayaneo3 Fans**. It supports all AYANEO 3 CPU variants;
the shared service remains a required dependency. Native OGUI is a separate frontend.

**Not eligible for an approval claim at this time.**

The [published submission rules](https://wiki.deckbrew.xyz/en/plugin-dev/submitting-plugins)
say: "We do not accept any plugin that uses any LLM based code". This project
includes Codex-generated code. Its origin must not be hidden or mislabeled.
Maintainer clarification or a policy change is needed before claiming eligibility
under that wording.

## Technical preparation

| Requirement | Status |
| --- | --- |
| Public source repository | Available |
| Root `plugin.json`, `package.json`, `main.py` | Included |
| pnpm lockfile version 9 | Included; no npm dependencies are fetched |
| Build output `dist/index.js` | Reproducibly built from readable source |
| License and dependency source | MIT project; LGPL API source and license included |
| Plugin runtime archive | Built with `scripts/build-decky-package.py` |
| External service dependency | Explicitly documented; install the shared service first; OGUI frontend not required |
| Hardware eligibility | All AYANEO 3 CPU variants; rejects other device families or missing/invalid fan telemetry |
| AYANEO 3 / Bazzite validation | Recorded in VALIDATION.md |
| Required real SteamOS validation | Pending; Bazzite tests are not a substitute |
| AI/LLM policy compliance | Cannot be claimed under current wording |
| Maintainer review and approval | Not obtained |

## Submission mechanism, once blockers are resolved

The [plugin database](https://github.com/SteamDeckHomebrew/decky-plugin-database)
requires a pull request adding this repository as a pinned git submodule under
`plugins/ay3-fancontrol`, with the corresponding `.gitmodules` entry. Point to an
exact reviewed commit and version. Follow the current PR template and
[testing requirements](https://wiki.deckbrew.xyz/en/plugin-dev/review-and-testing).

Do not submit a checklist asserting tests, policy compliance, or approval that have
not occurred. No official-store listing is implied by the public repository or ZIP.
