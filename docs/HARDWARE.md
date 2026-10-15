# UNO Q bring-up evidence

Observed on the connected development board on 2026-10-15. Device serial, local
network names, addresses, and scan logs are intentionally omitted from the repository.

| Item | Evidence / result |
| --- | --- |
| USB | Arduino VID 2341 / PID 0078, ADB interface and serial interface |
| OS | Debian GNU/Linux 13 (trixie), aarch64 |
| Kernel | 6.16.0-geffa8626771a |
| MCU core | arduino:zephyr 0.11.0-rc5; FQBN arduino:zephyr:unoq |
| Wi-Fi | wlan0, ath10k_snoc / ath10k_core / mac80211 |
| Bands | 2.4 and 5 GHz frequencies advertised by phy0 |
| Monitor | Advertised by iw phy; capture not exercised |
| Injection | Not tested; not inferred from monitor support |
| Bluetooth | BlueZ controller powered; central/peripheral roles advertised |
| Display | Red 3.5-inch parallel UNO shield; register D3 reports 0x9486; native GUI renders |
| Touch | XP=D6, XM=A2, YP=A1, YM=D7; owner confirmed two-point calibration and navigation |
| Orientation | Portrait software reflection setup under validation; see DISPLAY.md |
| GPS | No receiver/fix validated |
| Privilege | ADB user arduino; sudo requires the user's password |
| Boot service | No systemd user session/linger on this board; boot enablement needs admin setup |

## Completed acceptance checks

- Actual Wi-Fi discovery returned access points in both bands (18 in the first scan).
- BlueZ LE discovery returned 28 devices in its first bounded scan window.
- Repeated survey collection and stop completed; records survived a process restart.
- All 30 automated checks passed on Windows Python 3.13 and the board's Python 3.13,
  including orientation persistence and rejection of mismatched touch calibration.
- Native TFT firmware compiled and flashed with the matching factory runtime retained.
  The owner confirmed the physical dashboard and subsequent portrait touch navigation.
  Display mirroring remains under validation; successful uploads do not verify appearance.
- The source installer and USB forwarding were exercised on this board.
- These results do not validate final TFT orientation, GPS, raw capture, injection, or boot service.

`iw` was absent. For read-only probing, Debian's arm64 `iw` package was downloaded
and extracted under the user's cache without installing a system package. This
does not change interface mode, transmit frames, or establish capture capability.

Official references:

- [UNO Q hardware](https://docs.arduino.cc/hardware/uno-q/)
- [UNO Q datasheet](https://docs.arduino.cc/resources/datasheets/ABX00162-datasheet.pdf)
- [UNO Q pinout](https://docs.arduino.cc/resources/pinouts/ABX00162-full-pinout.pdf)
- [Arduino flashing procedure](https://docs.arduino.cc/software/app-lab/configure/flash/)
- [Arduino RouterBridge](https://github.com/arduino-libraries/Arduino_RouterBridge)

The UNO-format MCU GPIO uses 3.3 V logic. A0/A1 are not 5 V tolerant. Separate MPU
signals can use 1.8 V logic. Shield physical fit is not electrical compatibility.
