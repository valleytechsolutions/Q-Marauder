# Architecture and implementation boundaries

## Linux application

`qmarauder/radio.py` runs fixed argument vectors, never shell commands assembled from
radio names or web requests. `service.py` serializes radio jobs on one worker and
keeps the web thread responsive. Network names are untrusted input, rendered with
DOM text nodes rather than HTML. HTTP actions require a custom header and accept
only an explicit action allowlist. Host and Origin validation reduce localhost
request forgery and DNS-rebinding exposure; the service binds 127.0.0.1 only.

`storage.py` stores sessions separately, records each observation with UTC time,
and writes absent GPS positions as NULL. A restart closes incomplete sessions and
does not silently restart radio collection. CSV export escapes spreadsheet formulas.
`gps.py` accepts only fresh, finite, valid gpsd TPV positions. Data is under
`~/.local/share/q-marauder`, outside the source/install directory, with private file modes.

This alpha uses ordinary NetworkManager scanning, which can transmit probe requests.
It is not a passive sniffer. Wi-Fi signal is quality percent, not a measured dBm value.
BLE discovery is not raw BLE packet capture and is not a device-identity classifier.
The field survey currently repeats Wi-Fi scanning only. A scan that cannot start or
finish is surfaced as an error; a failed survey remains stoppable. Stop takes effect
after the bounded in-flight operation returns (up to about 32 seconds for Wi-Fi).

## Display architecture

Preferred next implementation: STM32-local rendering at 480×320 with persistent
fonts, palette, and converted logo assets in flash. Linux sends view models and small
updates through Arduino RouterBridge. The MCU sends touch/button events back.
A full RGB565 frame is 307,200 bytes; continuously streaming complete frames through
a serial RPC transport is a poor default. Measure the actual bridge throughput
before setting refresh budgets. Incremental redraw is required.

The desktop web console is an operator/development interface and visual reference.
The shield will not run a browser. It needs a native renderer, touch calibration,
font/logo encoding, and a verified driver. No claim is made that CSS is flashed to STM32.

The diagnostic bridge sketch registers only `qm.protocol` and `qm.status` and drives
no shield pins. It is a protocol smoke-test target, not a TFT firmware implementation.

## Privileged backends

Keep the UI/storage process unprivileged. Future monitor setup/capture should use a
small broker with fixed operations and independent capability checks. Never grant a
web service arbitrary sudo, root shell, or Docker access. Validate channel handling,
management-link coexistence, packet format, and capture loss on each hardware/driver
combination. Monitor advertisement is insufficient evidence for injection support.

Active-test jobs need explicit target parameters, duration/rate bounds, cancellation,
audit records, and the same capability checks used by the UI. Unsupported jobs should
return an explanation, not be silently emulated. There are no active-test endpoints
in this alpha.

## Detector packs

Each future detector should consume normalized Wi-Fi/BLE observations and return
evidence, a versioned signature/rule ID, confidence, and caveats. Preserve source
timestamps. Record fixtures for true positives and false positives. Avoid naming a
device as surveillance equipment solely from a spoofable SSID, MAC prefix, or name.
No Dragon Detector/Axeoff/Squachwach code or signatures have been imported yet.
