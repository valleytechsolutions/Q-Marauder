# Release validation and rollout limits

Recorded for the packet-detection alpha, 2026-10-16. These checks do not certify
every UNO Q image, shield clone, adapter, peer or power configuration.

| Check | Evidence |
| --- | --- |
| Windows unit suite | 106 tests, one POSIX-only skip |
| UNO Q Debian unit suite | 106 tests, no skip |
| Portrait native geometry | Direct-hit navigation/keypad C++ checks pass |
| MCU build | Factory Zephyr 0.11.0-rc5; 120,272-byte sketch, 3,640-byte globals |
| Saved screen setup | Linux bridge restores portrait orientation, calibration and theme |
| HCI receive | 44–49 actual advertising reports in initial windows, valid exported linktype-201 PCAPs |
| Detection runtime | Flock BLE, Sky Spy BLE and packet detector completed; zero candidate/RID matches in these windows |
| Protocol fixtures | OpenDroneID reference encoder supplies synthetic Basic ID, Location, unknown values, Authentication, Self ID, System and Operator ID messages |
| False-positive handling | Separate reports cannot form a Meta composite; generic XUNTONG company alone and random-address OUIs do not establish Flock candidates |
| BLE beacon test | Three successful controller registrations; HCI enable/disable commands accepted; cancellation and zero leftover instances checked. Independent RF receiver did not confirm reception |
| Wi-Fi receive baseline | Earlier single-channel external-Alfa capture verified; new channel sampling awaits live validation while adapter is absent |
| Fresh release install | Extracted source archive into a temporary directory; two installs create one immutable revision and preserve a user-data sentinel; desktop entry and installed HTTP startup checked. The existing OUI cache was reused; this was not a cold network-download test |
| Isolation during clean test | No radio job started; the test HTTP server omitted the physical display bridge to preserve the owner's screen state |
| Publication | ZIP/tar payload equivalence, documentation links and private-data exclusion checked |

Read [Active tests](ACTIVE-TESTS.md) and [Detection](DETECTION.md) for exact coverage.
New portrait packet pages are compiled/flashed and covered by bridge/geometry tests;
the owner still needs to accept their behavior by touch. Earlier Wi-Fi results and
BLE device/characteristic selection/read workflows were physically accepted.

Not validated: physical Flock/drone targets, raw BLE link-layer/connection capture,
extended advertisement reassembly, independent TX on this Bluetooth controller,
Wi-Fi injection/client effects, every upstream attack family, arbitrary factory
core versions, HDMI and UPS hardware, and unattended console boot on this board.
The LED matrix settings request remains queued behind the security rollout work.

## Raspyjack wireless first slice — October 16, 2026

The new Linux interface, Wi-Fi security survey and Bluetooth controller reports
completed on the UNO Q. The test window observed one wireless interface, 18 APs
and one Bluetooth controller. Eight-second BR/EDR discovery completed with zero
fresh devices; a positive Classic-device discovery/SDP test remains outstanding.
All four jobs saved reports and their JSON exports were verified through the local
HTTP API. No new attack job was run by these checks.

The final `qm-display/9` build compiled at 120,644 bytes of flash (3,640-byte globals)
and uploaded, including the 45-entry portrait port inventory.
The Linux bridge confirmed the display reconnected with saved touch calibration.
Physical tap acceptance of the new menu still needs the owner. GTK 3 and WebKitGTK
2.48 bindings load on the board; the native desktop shell and its export handling
still require a physical monitor/session acceptance check. No HDMI test is claimed.

The suite passed 115 tests on Debian, with one POSIX-only skip on Windows.
The current portrait menu render is generated from the firmware drawing code;
it is not a photograph or physical touch acceptance evidence.

## Touchscreen survey and history update — October 16, 2026

- 123 tests passed on UNO Q Debian; Windows passed with one POSIX-only skip.
- Live channel survey: 19 APs over 9 band/channel groups. Comparison used that
  saved session as its baseline and completed successfully.
- Eight-second LE summary: 27 observed addresses. Local BlueZ device cache: 20
  entries. Neither count establishes a number of unique physical devices.
- All four new reports exported through the local HTTP API. Opening a saved report
  preserved the session count and left the radio worker idle.
- The owner confirmed both channel-survey results and saved-report OPEN using the
  physical portrait TFT. Protocol `qm-display/10` reconnected with calibration intact.
- MCU build/upload: 120,944-byte sketch, 3,648-byte globals, tested factory core.
- Eight gallery scenes render from current firmware code with recorded source
  provenance. Desktop captures show the actual browser console; native window,
  HDMI/hub and UPS hardware acceptance remain outstanding.

No new attack or injection validation was performed for this update.
