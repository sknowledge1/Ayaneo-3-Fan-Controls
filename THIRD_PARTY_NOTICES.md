# Third-party notices

`vendor/decky-api-1.1.3` contains the official `@decky/api` 1.1.3 source distributed
by Steam Deck Homebrew under its LGPL license. The original license is retained
both there and in `LICENSE.decky-api`.

The build script injects this plugin's manifest, removes the empty types re-export,
and combines the API source with the readable frontend. Original source is included
so the dependency remains inspectable and replaceable.

The hardware design follows the publicly documented AYANEO kernel hwmon interface
and the existing HHD/PowerControl device-adapter pattern. Their driver/backend code
is not bundled in this project. Stock OGUI resources are supplied by the installed
OGUI package, not redistributed in the plugin ZIP.
