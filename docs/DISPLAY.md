# Native UNO shield display

The connected red 3.5-inch UNO-format shield **renders the Q-Marauder GUI**. The
owner confirmed the first native dashboard on 2026-10-15. The MCU subsequently
read controller ID `0x9486` through register `0xD3`. This supersedes the earlier
SPI-module identification from the mismatching AliExpress listing.

## Tested wiring and platform

| Shield signal | UNO Q header |
| --- | --- |
| LCD D0, D1 | D8, D9 |
| LCD D2 through D7 | D2 through D7 |
| RD, WR, DC, CS, RESET | A0, A1, A2, A3, A4 |
| SD chip select | D10, held high |

This is the standard [MCUFRIEND UNO bus](https://github.com/prenticedavid/MCUFRIEND_kbv/blob/master/utility/mcufriend_shield.h).
The driver uses Arduino GPIO calls rather than AVR port registers. The selected
ILI9486 profile uses RGB565 and native portrait **320 x 480**. Data register reads
only switch D2-D9 to inputs. All excitation is the MCU's own 3.3 V; A0/A1 must not
receive an external 5 V signal. Do not assume a different shield shares this map.

Tested MCU core: `arduino:zephyr@0.11.0-rc5`, the development board's factory core,
with its matching Zephyr runtime retained. Libraries: Arduino_RouterBridge 0.4.3,
Arduino_RPClite 0.3.1, MsgPack 0.4.2, Adafruit GFX 1.12.6, Adafruit BusIO 1.17.4.
Arduino's current public core has a different upload layout; its compatibility
must be tested separately before publishing a universal firmware binary.

## Portrait interaction

- Top 72 pixels: **Up**. Bottom 64 pixels: **Down**. Center: **Select**.
- Five large rows per page, 2x text, wrapped long labels, a cyan selection highlight.
- A Back item returns to the parent menu. On a detail page, a tap returns to the menu.
- 14 groups / 132 selections follow Marauder's main menu branches, including Wi-Fi
  Sniffers, Scanners, Attacks and General; Bluetooth Sniffers and Attacks; GPS and Device.
- Unported leaves show **Port planned**. Menu presence does not mean backend parity.
- Scan APs, BLE discovery, survey start and stop route to the existing Linux worker.
  Results/exports remain in the USB console; native result-list screens are pending.
- Supplied BWM and Marauder artwork is encoded for the physical startup screen.
  This is MCU application startup, not a replacement Linux bootloader screen.

The first-use touch screen asks for a press/release in the top pad and then the
bottom pad. The larger raw-axis difference determines the vertical axis and its
direction. Only one coordinate is needed for this three-zone interaction. Calibration
requires at least 250 ADC counts of separation. A held press generates one event;
release debounce prevents repeated selection. Resistive panels need physical pressure.

The initial touch profile is XP=D6, XM=A2, YP=A1, YM=D7. The factory ADC implementation
does not restore analog pad mode after digital GPIO use; the touch reader explicitly
restores PA5/PA6 analog mode before sampling, then restores the LCD bus. Touch still
requires physical acceptance testing; LCD controller identification alone does not
verify a touch pinout. A different touch wiring requires a separate profile.

## Linux connection

`qmarauder.display` uses the installed `arduino-router-cli` against the local router
socket. It sends bounded counts/status and polls a four-action allowlist. It does
not stream framebuffers or run shell command strings from the MCU. The TFT shows
an offline/stale state after 15 seconds without updates. Calibration is saved in
`~/.local/share/q-marauder/touch-calibration.json` and restored by the Linux service.

Flashing interrupts the serial RPC stream. Close and reopen it through the router's
documented `$/serial/close` and `$/serial/open` calls around upload. Do not change
socket permissions or replace the router service to make communication work.

## Remaining verification

Physical touch calibration/navigation, orientation and logo appearance, cold boot,
long-running touch reliability, and modern-core builds must be recorded before a
general hardware release. The Linux service currently needs manual start or the
documented systemd setup; the MCU menu itself survives reset independently.
