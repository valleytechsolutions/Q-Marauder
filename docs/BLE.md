# BLE Lab on UNO Q

The Debian backend uses BlueZ over D-Bus. The STM32 draws the portrait interface;
it does not run an ESP32 BLE stack. This is an independent, partial implementation
of workflows described by ChimeraBLE and Unified Blue, not either firmware running
on UNO Q. See [the complete status map](BLE-PARITY.md).

## Install once

After the normal Q-Marauder installation, double-click
`scripts/Enable-BLELab.cmd` on Windows. It finds one UNO Q and installs Debian's
`python3-dbus` and `python3-gi` packages. Enter the **board's Debian password** in
that window when requested. No password is saved. The board needs Internet access.
On the board directly, run `sh scripts/install-ble-dependencies.sh`.

These packages are already installed on the development UNO Q. Wi-Fi, display and
the browser console use the standard library; the new BLE jobs need these packages.

## Discovery and target selection

1. Open **Bluetooth → Discover BLE** in the USB browser console.
2. Find your device and select **Use as target**. Only that address is used by
   connection, characteristic and signal-tracking jobs.
3. **Settings → BLE test device** shows the saved selection and adapter.
   `hci0` is onboard on the tested setup; verify adapter numbering on other boards.
4. Choose **Track signal** or **Inspect GATT**. On the TFT these are under
   **Bluetooth → BLE foxhunt / GATT inventory**. Selection currently requires the browser.

Discovery returns names, RSSI, public/random address type, service UUIDs,
manufacturer/service data and a small set of fingerprints. These are **aggregated
BlueZ properties**, not individual raw advertisements. There is no claim of
passive-only scanning: BlueZ discovery can send scan requests. Fingerprints never
establish identity or surveillance activity. Private addresses can rotate; select
the new observation if your target changes address.

## GATT operations

Inspect GATT lists services and characteristics. Choose **Use UUID**, then Read,
Listen (10 seconds), or explicitly Write a hexadecimal value. Writes support
request and command modes and must be 1–512 bytes. The UUID must identify exactly
one characteristic; ambiguous duplicate UUIDs are refused. There is no arbitrary
D-Bus path or shell command API.

Every job has a deadline and disconnects its own connection on completion/error.
An already-connected target is refused so an existing session is not taken over.
Notification capture stops after 10 seconds and stores at most 256 events. Jobs
do not pair automatically, remove bonds, change adapter power or reset Bluetooth.
Pairing-dependent characteristics may fail. No generic write payload is safe for
every peripheral; use that device's protocol documentation.

Reports and notifications are in **Field log → JSON**. CSV contains summary fields;
use JSON for the full nested advertising/GATT data. Selecting a target does not
start a job. Restarting the console never repeats a write or notification request.

## Watchlist detection

Under **Settings → BLE watchlist**, add up to 32 named rules. Supported matches:
exact address, public OUI, company ID (four hex digits), service UUID (16-bit or
full), and case-insensitive name substring. OUI rules intentionally ignore random
addresses. Rules are OR matches; they do not implement same-packet composites.

Run **Bluetooth → Scan watchlist**, or **Counter surveillance → BLE watchlist scan**
on the TFT. Results explain which rules matched. A saved name rule for your own
test device is a useful end-to-end check. No vendor signature pack is enabled by default.

## Validation and limits

On 2026-10-15, the physical UNO Q's hci0 discovered the owner's Flipper Zero and
other advertising devices with real metadata. A configured name watchlist matched
the selected Flipper, and a 20-second signal window returned fresh RSSI samples.
The Flipper's GATT services did not
resolve within the bounded connection test. Consequently, discovery is physically
verified; GATT reads/writes/notifications remain **implemented, hardware validation
pending**. No write was sent to the Flipper. Mock tests cover ambiguous targets,
cleanup, notification failure and existing-connection refusal; they are not RF evidence.

If GATT fails, ensure Bluetooth is enabled on the device, disconnect its existing
phone session and inspect any pairing prompt. Do not clear other devices' bonds.
Interactive pairing, descriptor reads, HID decoding, clone/emulation and MITM are
not supplied in this build. RSSI tracking reports signal change, not distance.
