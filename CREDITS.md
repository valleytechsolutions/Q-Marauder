# Credits and acknowledgments

Q-Marauder is maintained by [Valleytech Solutions](https://github.com/valleytechsolutions).
It brings a Debian console and a portrait touchscreen to the Arduino UNO Q. Its
development relies on the projects, developers, documentation and tools below.

The relationship column distinguishes adapted code, independent implementations,
runtime dependencies and research references. A credit does not imply endorsement
or complete feature parity. Contributor lists and copyright holders remain in each
upstream project's history and notices.

## Firmware and research foundations

| Project | People and organizations | Contribution to Q-Marauder |
| --- | --- | --- |
| [ESP32 Marauder](https://github.com/justcallmekoko/ESP32Marauder) | **JustCallMeKoko** and contributors | Foundation for the feature inventory and menu vocabulary. The Debian backends are new implementations; this is not a complete ESP32 firmware port. The upstream MIT notice is retained in [licenses](licenses/ESP32Marauder-MIT.txt). |
| [Raspyjack](https://github.com/7h30th3r0n3/Raspyjack) | **7h30th3r0n3** and contributors; upstream also acknowledges **dagnazty**, **Hosseios** and **m0usem0use** | Wireless Linux workflow and feature-inventory reference. First independently implemented tools cover interface status, Wi-Fi security summaries, controller inspection and BR/EDR discovery. Upstream payload code, Raspberry Pi drivers, WebUI and bundled third-party tools are not imported. [Port status](docs/RASPYJACK.md) and [retained MIT notice](licenses/Raspyjack-MIT.txt). |
| [ChimeraBLE](https://github.com/MatthewKuKanich/ChimeraBLE) | **Matthew Kukanich** and contributors | BLE lab workflows and OUI-list compatibility reference. Q-Marauder independently uses BlueZ and downloads the same Wireshark MA-L /24 source. No ChimeraBLE implementation or generated vendor table is bundled. |
| [OUI-SPY Unified Blue](https://github.com/colonelpanichacks/oui-spy-unified-blue) | **Colonel Panic** and contributors | Detection-mode research and feature comparison, including Flock and Sky Spy. Q-Marauder uses independent protocol decoders and candidate rules; no upstream source or signature table is imported. |
| [flock-you](https://github.com/wgreenberg/flock-you) | **Will Greenberg** | Research lineage acknowledged by Unified Blue for the XUNTONG BLE company identifier. This identifier alone is not treated as a confirmed Flock detection. |
| [Unified Blue research acknowledgments](https://github.com/colonelpanichacks/oui-spy-unified-blue#readme) | **NitekryDPaul** and **DeFlockJoplin** | Upstream credits for broader Wi-Fi OUI / information-element research. These are research-lineage acknowledgments; their signature lists have not been imported into Q-Marauder. |

The inspected revisions, license boundaries and detection limits are recorded in
[third-party notices](THIRD_PARTY_NOTICES.md), [BLE feature status](docs/BLE-PARITY.md),
[OUI provenance](docs/OUI.md) and [detection evidence](docs/DETECTION.md).
Dragon Detector and Squachwach remain requested integration targets, rather than
bundled implementations.

## Display, touch and Arduino bridge

| Project | Credit | Use |
| --- | --- | --- |
| [MCUFRIEND_kbv](https://github.com/prenticedavid/MCUFRIEND_kbv) | **David Prentice** and contributors | ILI9486/ILI9488 initialization parameters adapted in the parallel display driver. [Retained notices](licenses/MCUFRIEND.txt) also acknowledge Arduino and Adafruit. |
| [Adafruit GFX](https://github.com/adafruit/Adafruit-GFX-Library) | **Adafruit Industries** and contributors | Drawing primitives and text rendering on the TFT; separately installed version 1.12.6. Also used by the documentation's software renderer. |
| [Adafruit BusIO](https://github.com/adafruit/Adafruit_BusIO) | **Adafruit Industries** and contributors | Separately installed dependency of the display toolchain, version 1.17.4. |
| [Adafruit TouchScreen](https://github.com/adafruit/Adafruit_TouchScreen) | **Adafruit Industries** and contributors | Published resistive-touch circuit method used as a reference for the independent touch reader. |
| [GNU FreeFont](https://www.gnu.org/software/freefont/) | GNU FreeFont contributors | FreeSans font lineage used through Adafruit GFX. Font and upstream library terms remain separate from the application's MIT license. |
| [Arduino_RouterBridge](https://github.com/arduino-libraries/Arduino_RouterBridge) | **Arduino** and contributors | Linux-to-MCU communication; separately installed version 0.4.3. |
| [Arduino_RPClite](https://github.com/arduino-libraries/Arduino_RPClite) | **Arduino**, **Lucio Rossi (eigen-value)** and contributors | Bridge dependency, version 0.3.1. |
| [MsgPack](https://github.com/hideakitai/MsgPack), [ArxContainer](https://github.com/hideakitai/ArxContainer), [ArxTypeTraits](https://github.com/hideakitai/ArxTypeTraits), [DebugLog](https://github.com/hideakitai/DebugLog) | **hideakitai** and contributors | Separately installed bridge serialization/support dependencies: 0.4.2, 0.7.0, 0.3.2 and 0.8.4 respectively in the tested toolchain. |

## Protocols, registries and validation references

| Project or specification | Credit | Use |
| --- | --- | --- |
| [OpenDroneID core C](https://github.com/opendroneid/opendroneid-core-c) and [transmitter Linux](https://github.com/opendroneid/transmitter-linux) | OpenDroneID contributors; **Intel Corporation** and **Gabriel Cox** in the inspected reference encoder notices | Public Remote ID definitions and reference-encoder fixtures for the independent decoder. The Apache-2.0 encoder is not bundled in the MIT application. |
| [Wireshark](https://www.wireshark.org/about.html) / `manuf` | Wireshark contributors and **IEEE** registration assignments | External manufacturer registry used for public-address OUI hints. The installer caches the registry separately with provenance and its source terms. |
| [Bluetooth Assigned Numbers](https://www.bluetooth.com/specifications/assigned-numbers/) | **Bluetooth SIG** | Company identifiers, UUIDs and advertising field definitions. |
| [USB HID 1.11](https://www.usb.org/document-library/device-class-definition-hid-111) | **USB Implementers Forum** | Reference for the independently implemented HID report-map parser. |
| [libpcap / tcpdump](https://www.tcpdump.org/) | The Tcpdump Group and contributors | PCAP/link-layer format documentation and interoperability reference; Q-Marauder's packet writer is independent. |
| [Flipper Zero firmware](https://github.com/flipperdevices/flipperzero-firmware) and [protobuf definitions](https://github.com/flipperdevices/flipperzero-protobuf) | **Flipper Devices** and contributors | GATT/serial-profile reference and harmless RPC validation against the owner's test device. |
| [Momentum firmware](https://github.com/Next-Flip/Momentum-Firmware) | **Next-Flip / Momentum contributors** | Firmware running on the owned Flipper used for pairing and GATT validation. It is not a Q-Marauder dependency or imported port. |
| [Aircrack-ng](https://github.com/aircrack-ng/aircrack-ng) | Aircrack-ng contributors | Independent injection-check tooling and documentation used during radio investigation; not the application backend. |
| [Bleak](https://github.com/hbldh/bleak) | Bleak contributors | Independent PC-side BLE observation during validation; not a runtime dependency. |

## Platform, runtime and development tools

| Projects | Credit and relationship |
| --- | --- |
| [UNO Q](https://docs.arduino.cc/hardware/uno-q/), [Arduino CLI](https://github.com/arduino/arduino-cli), [ArduinoCore-zephyr](https://github.com/arduino/ArduinoCore-zephyr), [Arduino Linux](https://github.com/arduino/linux-qcom) | **Arduino** and contributors provide the board platform, installation/build tools and kernel sources. **Qualcomm** and **STMicroelectronics** provide the processor platforms used by the board. |
| [Zephyr](https://www.zephyrproject.org/), [Linux](https://www.kernel.org/), [Debian](https://www.debian.org/) | Their maintainers and communities provide the MCU operating environment, kernel, USB/IP and mt76/mt7921 drivers, and Debian system. Their licenses remain their own. |
| [BlueZ](https://www.bluez.org/), [NetworkManager](https://networkmanager.dev/) | Maintainers and contributors provide the Bluetooth and Wi-Fi system APIs used by the application. |
| [D-Bus / dbus-python](https://dbus.freedesktop.org/doc/dbus-python/), [PyGObject](https://pygobject.gnome.org/) | D-Bus and **GNOME** contributors provide the separately installed BLE bindings and event-loop integration. |
| [GTK](https://www.gtk.org/) and [WebKitGTK](https://webkitgtk.org/) | GTK/GNOME and WebKit contributors provide the native Debian app window and embedded local interface. Installed separately, with their own licenses. |
| [Python](https://www.python.org/), [SQLite](https://www.sqlite.org/) | **Python Software Foundation**, Python contributors and SQLite developers provide the application language, standard library and local database. |
| [gpsd](https://gpsd.io/), [systemd](https://systemd.io/), [Xfce](https://www.xfce.org/), [Chromium](https://www.chromium.org/) | Respective contributors provide optional position, service and desktop components. |
| [Android Platform-Tools / ADB](https://developer.android.com/tools/releases/platform-tools) | **Android Open Source Project / Google** and contributors provide the USB deployment and forwarding tools; installed separately. |
| [OpenOCD](https://openocd.org/) and Arduino's remote upload integration | OpenOCD and Arduino contributors provide MCU upload/debug tooling. |
| [usbipd-win](https://github.com/dorssel/usbipd-win) | **dorssel** and contributors provide the Windows USB/IP bridge used by the experimental PC-connected Alfa setup. |
| [GCC](https://gcc.gnu.org/), [Git](https://git-scm.com/), [setuptools](https://setuptools.pypa.io/), [Pillow](https://python-pillow.github.io/), [GitHub Actions](https://github.com/features/actions) | Their maintainers and contributors provide compilation, version control, packaging, artwork encoding and continuous-integration tools. |

## Artwork, photographs and UI images

The project owner supplied the **BWM / Black Wire Militia**, **Marauder**,
**Biscuit Shop** and **Valleytech** theme artwork, plus development-board photographs.
The original Marauder artwork's illustrator has not been independently identified;
the repository does not invent an artist credit or grant rights it does not hold.
The respective owners retain artwork and trademark rights.

The [UI gallery](docs/GALLERY.md) distinguishes actual browser screenshots,
source-rendered TFT previews and physical assembly photographs. Screenshots and
generated logo encodings retain the original artwork exclusions.

## Licenses and corrections

[MIT](LICENSE) applies to Q-Marauder's application code. It does not relicense the
operating system, dependencies, externally downloaded registries, fonts or artwork.
See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and [licenses/](licenses/).

If a credit or relationship is missing or inaccurate, please
[open an issue](https://github.com/valleytechsolutions/Q-Marauder/issues) with the
project link and the affected Q-Marauder file or feature so it can be corrected.
