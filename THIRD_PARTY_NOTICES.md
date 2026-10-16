# Third-party notices

The complete project/developer acknowledgments and each project's relationship to
Q-Marauder are collected in [CREDITS.md](CREDITS.md). This file records license and
redistribution boundaries; credits do not replace upstream notices.

The packet and Remote ID decoders are independent implementations based on public
protocol fields, BlueZ APIs and OpenDroneID documentation. No Unified Blue source
or signature table is distributed. Synthetic Remote ID fixture bytes were produced
from our test inputs with the Apache-2.0 OpenDroneID reference encoder; source hashes
and reproduction instructions are in `docs/DETECTION.md`. The reference encoder
itself is not bundled in the MIT application.

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

## BLE research references

[ChimeraBLE](https://github.com/MatthewKuKanich/ChimeraBLE) by Matthew Kukanich was
inspected at `2330423dae8f8fa163617172310784889d8972a7`. It declares GPL-3.0-or-later.
No ChimeraBLE implementation or generated vendor database is distributed here.
The installer separately downloads Wireshark's `manuf` registry and selects its
MA-L /24 entries, matching ChimeraBLE's documented list workflow. The cached data
retains its source terms and is excluded from this project's MIT grant; see
[OUI provenance and updating](docs/OUI.md).

The HID parser is independently implemented from the published
[USB HID 1.11 specification](https://www.usb.org/sites/default/files/hid1_11.pdf).
The BLE workers are independent BlueZ implementations; this MIT grant does not
apply to ChimeraBLE or its dependencies.

[Unified Blue](https://github.com/colonelpanichacks/oui-spy-unified-blue) by
Colonel Panic was inspected at `6e5e2829540925ff1ab5fa6d0d365378818ed56e`.
No repository-wide license was found in that tree. Individual OpenDroneID notices
do not establish a license for the entire project. No source or signature database
has been imported. See [feature status](docs/BLE-PARITY.md).

Debian's separately installed dbus-python and PyGObject retain their own licenses;
their binaries/source are not bundled in this release.

## Brand assets

`qmarauder/web/assets/bwm.png`, `marauder.webp`, `biscuit.png`, and `valleytech.png`
were supplied by the project owner for startup branding and theme backgrounds,
and are included unchanged. They are excluded
from this project's MIT grant. Their respective owners retain rights to the marks
and artwork; this repository does not grant trademark rights or imply endorsement.

## Hardware photographs

The original assembly and pre-initialization photographs in `docs/images/` were
provided by the project owner for this repository's instructions. They are excluded
from the MIT code grant; no rights to background objects or visible third-party
marks are asserted. Captions distinguish the pre-firmware state from working software.
The browser startup and Settings screenshots contain the same supplied brand assets and carry
their artwork-rights exclusions.

The [UI gallery](docs/GALLERY.md) adds actual browser screenshots and clearly labeled
software renders of the native TFT drawing code. The renders are not photographs
or evidence of additional hardware validation. Their embedded artwork retains the
same exclusions. The renderer uses separately installed Adafruit GFX; its source is
not bundled in the documentation tooling.

## Arduino bridge

The MCU targets use separately installed Arduino_RouterBridge.
The RouterBridge library and Arduino platform retain their upstream licenses.
No Arduino runtime binaries are redistributed in this alpha source package.

## Optional USB radio modules

The build helper downloads pinned Arduino Linux source separately. Linux USB/IP
and mt76/mt7921 modules retain their upstream GPL licenses; they are not MIT and
no compiled kernel module is bundled in this source release. Debian's MediaTek
firmware and usbipd-win retain their respective licenses. The repository includes
the exact source commit, archive digest and module-build recipe.

## Native TFT

ILI9486/ILI9488 initialization parameters in `firmware/uno_shield/Parallel9486.h`
are adapted from David Prentice's MCUFRIEND_kbv. Its notices are retained in
`licenses/MCUFRIEND.txt`. Adafruit GFX is installed separately and retains its BSD
license. The resistive touch measurement follows the published Adafruit TouchScreen
circuit method. Native menu labels reference the pinned Marauder source and retain
the upstream MIT notice. No upstream radio attack implementation is included.

`firmware/uno_shield/LogoData.h` is a generated encoding of the supplied artwork;
the same artwork-rights exclusion as the original images applies to this header.
The logo converter's code is MIT licensed; conversion does not change artwork rights.
