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
The driver initializes pins through Arduino, then uses masked STM32 GPIO set/reset
writes for the parallel data bus and write strobe. Compile-time assertions check
the core's device-tree mapping before enabling this path; unrelated pins are not
modified. The selected
ILI9486 profile uses RGB565 and native portrait **320 x 480**. Data register reads
only switch D2-D9 to inputs. All excitation is the MCU's own 3.3 V; A0/A1 must not
receive an external 5 V signal. Do not assume a different shield shares this map.

The calibration-screen redraw measured about 1,077 ms through per-pin Arduino
writes and 229 ms with the verified STM32 bus path and current font. This is one
measured screen, not a guaranteed frame rate for all menus.

Tested MCU core: `arduino:zephyr@0.11.0-rc5`, the development board's factory core,
with its matching Zephyr runtime retained. Libraries: Arduino_RouterBridge 0.4.3,
Arduino_RPClite 0.3.1, MsgPack 0.4.2, Adafruit GFX 1.12.6, Adafruit BusIO 1.17.4.
Arduino's current public core has a different upload layout; its compatibility
must be tested separately before publishing a universal firmware binary.

## Portrait interaction

- Tap a menu row directly to open it. Four 300 x 64 pixel rows appear per page.
- A 56-pixel footer provides **Back**, **Previous**, and **Next** buttons. Page controls
  are inactive at the ends; gaps between targets do not activate neighboring items.
- On the main menu the left footer button opens **Themes**. Details have a Back button.
- FreeSans menu text, wrapped long labels, and large targets support finger input.
- 15 groups / 137 selections follow Marauder's main menu branches, including Wi-Fi
  Sniffers, Scanners, Attacks and General; Bluetooth Sniffers and Attacks; GPS and Device.
- Unported leaves show **Port planned**. Menu presence does not mean backend parity.
- Scan APs, BLE discovery, survey start and stop route to the existing Linux worker.
  Results/exports remain in the USB console; native result-list screens are pending.
- Supplied BWM and Marauder artwork is encoded for the physical startup screen.
  This is MCU application startup, not a replacement Linux bootloader screen.
- **BWM** (red/graphite), **Marauder** (crimson/steel), and **Cyber** (cyan/midnight)
  themes apply immediately and persist through Linux. A faint supplied BWM emblem
  sits behind the menu text. Themes are also under Device / Settings / Themes.

First use starts with four portrait orientation candidates. Hold the USB connector
at the bottom and wait for upright, normally readable text, then tap anywhere.
Each candidate stays on screen for seven seconds after drawing. The test uses
software coordinate reflections with a fixed MADCTL value of `0x08`; X/Y reflection
bits apply to every solid rectangle, including individual glyph pixels and logo runs.
The panel accepted hardware MADCTL changes in register readback, but the owner
reported mirror-written letters in all four hardware candidates. A software profile
therefore needs visual validation rather than inference from the controller ID.

The subsequent touch screen presents three circles: upper left, upper right, and
lower left. Press and release each center. These measurements produce a two-axis
affine map that handles axis swapping, reflection, and skew. Degenerate or closely
spaced targets are rejected. Version-2 calibration stores all six raw coordinates;
the earlier vertical-only calibration cannot be reused. Taps activate on release,
with stable-sample filtering and a 100 ms release debounce. A held touch cannot
repeat actions, and dragging into another target cancels the selection. Resistive
panels need physical pressure.

The initial touch profile is XP=D6, XM=A2, YP=A1, YM=D7. The factory ADC implementation
does not restore analog pad mode after digital GPIO use; the touch reader explicitly
restores PA5/PA6 analog mode before sampling, then restores the LCD bus. Touch must
be checked on each shield; LCD controller identification alone does not
verify a touch pinout. A different touch wiring requires a separate profile.

On 2026-10-15 the owner confirmed upright, readable text with software profile `1`
(X reflection, no Y reflection). That orientation and the earlier calibration
restored after an MCU-only reset with Linux still running. The owner subsequently
requested direct touch because the three-zone navigation was confusing. The new
direct-touch build, themes, and two-axis calibration require physical acceptance;
orientation remains unchanged. An orientation change starts fresh touch calibration.

## Linux connection

`qmarauder.display` uses the installed `arduino-router-cli` against the local router
socket. It sends bounded counts/status and polls a four-action allowlist. It does
not stream framebuffers or run shell command strings from the MCU. The TFT shows
an offline/stale state after 15 seconds without updates. Protocol `qm-display/5`
adds direct touch and themes. The Linux service saves `display-orientation.json`,
`display-theme.json`, and `touch-calibration.json` under `~/.local/share/q-marauder`. Calibration records
include the orientation and restore only when it matches; old records without an
orientation are intentionally ignored. The MCU also rejects saved calibration
after a manual orientation choice, so a fresh setup cannot silently reuse old values.
Without the Linux service, setup repeats after MCU reset.

Flashing interrupts the serial RPC stream. Close and reopen it through the router's
documented `$/serial/close` and `$/serial/open` calls around upload. Do not change
socket permissions or replace the router service to make communication work.

## Remaining verification

Direct-touch accuracy, theme/logo appearance, cold boot,
long-running touch reliability, and modern-core builds must be recorded before a
general hardware release. The Linux service currently needs manual start or the
documented systemd setup. The MCU firmware remains flashed, but restoring its saved
orientation and calibration requires the Linux bridge.
