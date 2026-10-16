# Bill of materials

Quantities below build one development unit. There are no affiliate links. Prices
are omitted because they vary; verify the exact part and connector before ordering.

| Qty | Part | Required specification | Validation |
| --- | --- | --- | --- |
| 1 | [Arduino UNO Q](https://docs.arduino.cc/hardware/uno-q/) | Arduino Debian installed; STM32 UNO headers; the tested display runtime is Zephyr 0.11.0-rc5 | Actual development board tested; not interchangeable with UNO R3/R4 |
| 1 | 3.5-inch UNO TFT touch shield | Red dual-header, 8-bit parallel 320×480 shield; tested with ILI9486-compatible initialization and resistive touch | Unbranded sample tested. Similar-looking SPI/ILI9488 modules and different clone pinouts are not verified |
| 1 | USB data cable | PC connector to USB-C on UNO Q; adequate power and data support | Used for power, ADB and optional radio forwarding |
| 1 | Windows PC | USB port, Internet, Google Platform-Tools; administrator access for optional usbipd setup | Windows installation path provided |
| 1 | Wi-Fi connection | For the UNO Q's first setup and library/package downloads | Onboard 2.4 and 5 GHz discovery observed |

## Optional radio and expansion parts

| Qty | Part | Purpose / limitation |
| --- | --- | --- |
| 1 | ALFA USB adapter with MediaTek `0e8d:7961` ID | PC-forwarded scanning and monitor reception tested; injection unverified. USB ID identifies the chipset family, not exact AXM/AXML retail model. See [live support evidence](USB-RADIO.md) before purchasing. |
| 1 | Powered USB-C hub with USB-A and suitable power input | Future direct-radio connection to UNO Q. Exact hub, power supply and simultaneous management path are not yet validated. Not needed for the PC-forwarding setup. |
| 1 | GNSS receiver supported by gpsd | Future wardriving coordinates; no receiver is validated and no position is invented without a fix. |
| 1 | Nonconductive enclosure, spacers and fasteners | Protect the exposed boards while leaving connectors accessible. No enclosure dimensions or printable design are validated yet. |

The display is driven by the **STM32**, while Debian on the Qualcomm processor owns
Wi-Fi, Bluetooth and storage. Connecting the shield does not make it a Linux HDMI
display. Read [hardware evidence](HARDWARE.md) and [display wiring](DISPLAY.md).

For photos and assembly instructions, see [Get started](GETTING-STARTED.md).
