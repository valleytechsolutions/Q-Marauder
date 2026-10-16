# Survey tools and saved reports

Eight Linux tools share one job queue, reports and local history between the
portrait TFT and Q-Marauder Lab. This guide describes code on `main`; older release
archives may not contain these additions. Update both the app and MCU using the
[Windows USB installer](GETTING-STARTED.md). The current protocol is `qm-display/10`.

## Portrait touchscreen

Open **Home → Linux tools**, or **Wi-Fi / Bluetooth → Linux tools**.

| Page | Controls |
| --- | --- |
| 1 | Radio interfaces, Wi-Fi security survey, Bluetooth controllers, Bluetooth Classic scan |
| 2 | Wi-Fi channel survey, Wi-Fi scan changes, BLE advert summary, Saved Bluetooth devices |
| 3 | Linux report, Saved Linux reports, Port inventory |

Tap a tool and wait for its bounded job to finish. Tap a report row to read details.
**BACK** returns to the list, then to the menu; **PREV/NEXT** page through results.
For history, tap **Saved Linux reports → a report → OPEN**. Back from that report
returns to the same history page. Opening a saved report does not run the tool again.
History contains up to 100 recent Linux reports; other session types remain in
the desktop Field log. An interrupted report is labelled as such, not rerun.

<img src="images/tft/linux-analysis.png" width="256" alt="Current portrait survey tools page">
<img src="images/tft/linux-history-menu.png" width="256" alt="Current portrait saved-report menu">

These are renders of the firmware drawing code. The owner confirmed the channel
survey and saved-report OPEN workflow on the physical panel on October 16, 2026.

## Wi-Fi channel survey and changes

**Channel survey** groups observed BSSIDs by band and channel. It reports the AP
count and strongest/mean signal quality percentage. It does not measure airtime,
channel widths or interference, and an unobserved channel is not proven clear.

**Scan changes** compares a fresh NetworkManager survey with the latest successful
Linux **Wi-Fi security survey**, **Wi-Fi channel survey** or **Wi-Fi scan changes**
report. With no baseline, it saves one and says so. A successful empty survey is
still a baseline; failed/incomplete jobs are skipped.

- **New:** BSSID appears in the new report only.
- **Not seen:** BSSID appears in the baseline only; it may still be present.
- **Changed:** same BSSID changed name, band, channel or advertised security, or
  signal quality moved by at least 15 percentage points.

The comparison records the baseline time and session. NetworkManager may retain
cached observations, and changing signal or advertised security does not establish
an evil twin or other attack. Wi-Fi discovery may send probe requests.

## Bluetooth summaries

**BLE advert summary** uses the adapter selected under **Settings → BLE adapter**.
Eight seconds of LE discovery feed company-ID, service-UUID and address-type
counts, followed by individual address observations. A service appearing in both
UUIDs and service data counts once per address. Random addresses may rotate;
advertised identifiers are claims and are not proof of device identity.
BlueZ aggregates properties, so this is not packet-level capture. Up to 128 company
and 128 service groups are shown; JSON preserves all group counts.

**Saved Bluetooth devices** reads the selected adapter's local BlueZ cache. It shows
paired, connected, trusted and blocked state and cached service UUID counts.
It does not scan, connect, pair, unpair or change trust. Cached entries may be stale
and do not prove a device is nearby. The current worker requires the selected
controller to be powered on; it does not turn it on automatically.

These backends use the documented [BlueZ Device API](https://bluez.readthedocs.io/en/latest/device-api/)
and [Adapter API](https://bluez.readthedocs.io/en/latest/adapter-api/).

## Desktop application

On Debian open **Applications → Q-Marauder Lab → Lab → Linux radio tools**.
Use **Show tools** to choose All radios, Wi-Fi or Bluetooth. Running a tool scrolls
to its report. Expand **Saved Linux reports** and choose one to reopen it. The
**SAVED** marker distinguishes reopened results; **Download JSON** exports the
complete stored report. Radio names and addresses stay in local data until exported.

![Wi-Fi tools in the running console](images/desktop-wifi-tools.jpg)
![Bluetooth tools in the running console](images/desktop-bluetooth-tools.jpg)

Actual browser captures of the shared desktop interface. The native GTK/WebKit
app hosts this UI; these are not photographs of an attached HDMI display.
See [Desktop setup](DESKTOP.md) and [Validation](VALIDATION.md) for hardware limits.
