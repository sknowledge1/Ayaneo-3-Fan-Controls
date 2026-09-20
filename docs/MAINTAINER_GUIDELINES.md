# Maintainer guidance and submission status

Checked on 2026-09-20. These are published guidelines, not an endorsement or
approval of this implementation by any maintainer.

## Bazzite and stock interface

Bazzite tracks fan controls as an OGUI plugin in
[issue #5791](https://github.com/ublue-os/bazzite/issues/5791). The native frontend
uses OGUI's documented Plugin API 2.0 and `add_to_quick_bar`, with stock dropdown,
slider, and button scenes. It does not depend on Decky or replace the installed
OGUI binary, kernel, InputPlumber, or power controls.

OGUI's [best practices](https://github.com/ShadowBlip/OpenGamepadUI/blob/115e93994aa32c370d88dd39fec84d4c085062c2/docs/documentation/contributing/best_practices.md)
favor an existing issue, narrow scope, decoupled components, and minimal external
dependencies. Its [style guide](https://github.com/ShadowBlip/OpenGamepadUI/blob/115e93994aa32c370d88dd39fec84d4c085062c2/docs/documentation/contributing/code_style_guidelines.md)
requires type annotations. This plugin uses typed GDScript and signals. A bounded
client request runs off the UI thread; the existing standard-library Python fan
service remains the sole writer. Python is already present in the tested Bazzite image.

[OGUI issue #505](https://github.com/ShadowBlip/OpenGamepadUI/issues/505) proposes
putting fan support in PowerStation. That is a suggested upstream backend direction,
not an existing public fan API. This local integration uses a separate supervised
service while leaving PowerStation's TDP ownership unchanged. It must not be
represented as an accepted PowerStation implementation.

The plugin ZIP uses the documented `plugins/<id>/plugin.json` resource-pack layout
and user plugin directory. The source remains readable. Official OGUI store
inclusion requires its own [registry review](https://github.com/ShadowBlip/OpenGamepadUI/blob/115e93994aa32c370d88dd39fec84d4c085062c2/docs/documentation/plugins/submitting.md).
Bazzite image inclusion likewise requires maintainer review. Local compatibility
testing is not proof of future image inclusion.

## Official Decky store

The [submission rules](https://wiki.deckbrew.xyz/en/plugin-dev/submitting-plugins)
currently reject plugins using LLM-based code.
This project includes code generated with Codex. Its provenance will be disclosed;
official-store eligibility cannot be claimed under that published wording.
Do not conceal authorship or submit a false compliance declaration.

Other requirements from the [review process](https://wiki.deckbrew.xyz/en/plugin-dev/review-and-testing)
and [plugin database](https://github.com/SteamDeckHomebrew/decky-plugin-database):

- A public source repository, license, and inspectable dependencies.
- An npm-compatible package name and a pnpm v9 lockfile.
- A database PR containing both the `.gitmodules` entry and pinned git submodule.
- Required configuration/dependencies included in the reviewed package.
- Appropriate real SteamOS testing; the AYANEO/Bazzite tests do not replace it.
- Approval from the Decky team before inclusion in the official store.

The working Decky frontend currently relies on the separately installed fan
service. That dependency and its installation must be reviewed as part of any
submission. Preparing metadata or a release archive does not satisfy the policy,
hardware-testing, or maintainer-approval requirements by itself.

## GitHub publication

The requested public repository slug is `Ayaneo-3-Fan-Controls`, with the project
title "Ayaneo 3 Fan Controls". Publish an explicit allowlist of source, licenses,
build instructions, and sanitized test summaries. Exclude `.tools`, SSH host data,
device inventory, personal paths, account information, and raw logs/screenshots.

The user completed GitHub's device-authorization flow. The public repository was
created at https://github.com/sknowledge1/Ayaneo-3-Fan-Controls. Store acceptance
remains a separate review decision; repository creation does not resolve the
published Decky policy or required SteamOS testing.
