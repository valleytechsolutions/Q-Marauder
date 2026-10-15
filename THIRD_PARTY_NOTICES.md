# Third-party notices

Q-Marauder application code is MIT licensed. Debian, Linux, BlueZ, NetworkManager,
Arduino tools, and any separately installed dependencies retain their own licenses.
The complete operating system is not licensed as MIT merely because this application is.

## Marauder

This independent project is inspired by JustCallMeKoko's
[ESP32 Marauder](https://github.com/justcallmekoko/ESP32Marauder).
The feature inventory references upstream documentation; the Linux application is
new code, not a binary-compatible ESP32 firmware port. There is no claim of official
endorsement or full feature parity.

Upstream source inspected: `d3ceb28afeda1196ca27c13adeaa69ada52383f3`.
Wiki inspected: `57deeb79e3b40f44d5c885bb55a789bec58abb8d`.
Upstream's MIT notice is retained in `licenses/ESP32Marauder-MIT.txt`.
Preserve it whenever upstream code is incorporated in later ports.

## Brand assets

`qmarauder/web/assets/bwm.png` and `marauder.webp` were supplied by the project owner
for the requested startup branding and are included unchanged. They are excluded
from this project's MIT grant. Their respective owners retain rights to the marks
and artwork; this repository does not grant trademark rights or imply endorsement.

## Arduino bridge

The optional MCU diagnostic sketch uses separately installed Arduino_RouterBridge.
The RouterBridge library and Arduino platform retain their upstream licenses.
No Arduino runtime binaries are redistributed in this alpha source package.
