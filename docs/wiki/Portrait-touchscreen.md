# Portrait touchscreen

Hold the board with USB at the bottom. Tap a card and release; dragging off the
card cancels that press. Four large rows fit on each page. BACK, PREV and NEXT
remain at the bottom, with disabled page controls inactive.

## First useful operations

- **WiFi → Scan APs:** wait for the scan, then tap a network for channel, signal and security.
- **Bluetooth → Scan BLE:** wait for results, tap your device and choose **USE**.
- **Bluetooth → BLE tools → GATT inventory:** tap a characteristic and **USE**,
  then **Read value** or **Listen notifications**.
- **Settings → Themes:** BWM, Marauder, Biscuit Shop or Valleytech. Browser and TFT
  share the same saved choice.

Empty Wi-Fi/BLE result screens have **SCAN** in the lower right. Saved observations
after a service restart are labelled; rescan before assuming a device is still nearby.

## BLE controls

BLE tools includes Pair selected device, GATT inventory, GATT snapshot, RSSI
tracking, HID map inspection and HID report listening. GATT snapshots read bounded
characteristic and descriptor values; errors are part of the report.

Pairing opens a keypad on the TFT when the peer requests a code. Enter the **new**
code and SEND before it expires. KEYS changes character pages for a text PIN.
Code comparison asks for an explicit ACCEPT; CANCEL stops pairing. Pairing codes
are not stored in session history.

Choose a characteristic from its result row before using Characteristic tools.
Write hex value requests a response; Write no response uses a command. The TFT
accepts at most 48 bytes per write. Use documented values for your selected test
peripheral. The browser supports longer bounded writes. The device can reject a
write even when it advertises writable flags.

## Detectors and capture

**Counter surveillance** includes Packet detector, Flock Wi-Fi, Flock BLE, Sky Spy
Wi-Fi, Sky Spy BLE and BLE Sniff PCAP, alongside watchlists/RSSI/Wi-Fi PCAP. Tap a
mode once; results appear after its bounded window. Tap rows for evidence or Remote
ID telemetry and use PREV/NEXT for further pages. Zero matches still shows receive
counts and coverage. PCAP files download from Field log in the browser/desktop.

**Bluetooth → Bluetooth Attacks → BLE beacon test** registers three QM-LAB names,
two seconds each. BACK → **Stop beacon test** stops it early. This is a bounded
advertising test; platform popup/crash spam is not implemented or claimed.

If touch coordinates are wrong, use **Settings → Calibrate touch**. The saved
orientation and calibration are restored by the running Linux service.

Watchlist editing and file export remain browser/desktop workflows. Continuous
audio, BLE link-layer/connection sniffing and every upstream attack are not available on the TFT
merely because a corresponding label appears in the menu.
