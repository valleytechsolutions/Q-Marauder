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
| Monitor | Advertised, but shared and dedicated monitor tests returned zero receive packets |
| Injection | Ten directed probes submitted, zero responses; RF injection unverified |
| Bluetooth | BlueZ controller powered; central/peripheral roles advertised |
| Display | Red 3.5-inch parallel UNO shield; register D3 reports 0x9486; native GUI renders |
| Touch | XP=D6, XM=A2, YP=A1, YM=D7; owner confirmed direct touch after three-target calibration |
| Orientation | Owner confirmed upright/readable portrait; current saved software-reflection profile 2 |
| GPS | No receiver/fix validated |
| Privilege | Unprivileged console; fixed-action root radio socket installed and tested |
| Boot service | Radio socket enabled; console boot service not enabled, source preview remains in use |
| PC USB radio | 0e8d:7961 (MT7921 family), imported through usbipd/ADB; scans and monitor receive verified |
| USB radio kernel support | Factory config disables MT7921U/USB-IP; exact-source supplemental modules now loaded |

## Completed acceptance checks

- Actual Wi-Fi discovery returned access points in both bands (18 in the first scan).
- BlueZ LE discovery returned 28 devices in its first bounded scan window.
- Repeated survey collection and stop completed; records survived a process restart.
- All 55 automated Python checks passed on the board; Windows passed 54 and skipped
  the Linux-specific file-lock check. Coverage includes
  orientation/theme persistence and rejection of legacy or invalid touch calibration.
- Native C++ checks passed on the board for affine calibration with normal,
  reversed, and swapped axes, plus row/button boundaries and disabled page controls.
- Native TFT firmware compiled and flashed with the matching factory runtime retained.
  The owner confirmed the physical dashboard and subsequent portrait touch navigation.
  The owner subsequently confirmed upright, readable text with software orientation.
  Profile 1 and the earlier vertical touch calibration were saved and automatically restored
  after an MCU-only reset, verified by RPC with the Linux service still running.
- Fresh verification found 16 Wi-Fi APs across 2.4/5 GHz and 28 BLE devices;
  the hardware is functional for the implemented discovery backends.
- The source installer and USB forwarding were exercised on this board.
- Protocol-6 firmware compiled at 115,160 bytes of program storage and 3,500 bytes
  of static globals. Saved orientation, two-axis touch calibration and theme restored
  after upload. The owner confirmed Wi-Fi result rows and device details on the TFT.
- Fresh discovery returned 17 Wi-Fi APs across both bands and 26 BLE devices;
  a later native Wi-Fi scan returned 20 APs. Counts vary with nearby activity.
- Factory bridge RPCs reject oversized requests; 128-character result chunks
  resolved the initial empty-results failure. Complete pages commit atomically.
- Later source-preview verification returned 16 APs across both bands and 19 BLE
  devices; saved orientation, affine calibration and Valleytech theme matched RPC.
- Installed the fixed-action socket worker and verified configuration access without
  sudo from the application. Lab reports now persist across application restarts.
- Later PC-forwarded Alfa tests verified real monitor reception on both lab bands.
  Injection received no matching responses, including an independent Aircrack-ng check.
- Windows installation launcher exercised end to end: board/core detection,
  application update, own-preview restart, full 2 MiB MCU backup, compile and sketch
  upload succeeded. The original matching runtime was retained.
- 57 Python tests passed on Debian; Windows passed 56 with the POSIX lock test skipped.
- The socket-activated worker returned real external-radio capture counters through
  the console API, with report persistence and NetworkManager ownership restored.
- These results do not validate cold boot, GPS, injection, or console boot startup.

`iw` was initially absent. For read-only probing, Debian's arm64 `iw` package was downloaded
and extracted under the user's cache without installing a system package. This
did not establish capture capability. The later authorized admin setup installed
the system package and bounded lab helper. Monitor tuning was accepted in a
dedicated test but still returned zero packets; normal Wi-Fi connectivity was restored.
See [lab evidence](LAB.md) and [external-radio requirements](USB-RADIO.md).

Official references:

- [UNO Q hardware](https://docs.arduino.cc/hardware/uno-q/)
- [UNO Q datasheet](https://docs.arduino.cc/resources/datasheets/ABX00162-datasheet.pdf)
- [UNO Q pinout](https://docs.arduino.cc/resources/pinouts/ABX00162-full-pinout.pdf)
- [Arduino flashing procedure](https://docs.arduino.cc/software/app-lab/configure/flash/)
- [Arduino RouterBridge](https://github.com/arduino-libraries/Arduino_RouterBridge)

The UNO-format MCU GPIO uses 3.3 V logic. A0/A1 are not 5 V tolerant. Separate MPU
signals can use 1.8 V logic. Shield physical fit is not electrical compatibility.
