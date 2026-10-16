# Detection and capture

Open **Lab → Detection modes** on the desktop, or **Counter surveillance** on the
portrait TFT. Each tool states its actual receive method and limitations.

| Mode | Current behavior |
| --- | --- |
| Detector | User watchlist plus Axon/TASER identifier presets; BlueZ discovery |
| AXEOFF BLE | Public OUI, company ID and service-UUID candidate matches |
| Foxhunter | Bounded selected-address RSSI tracking |
| Wi-Fi PCAP | Eight-second radiotap capture on the configured lab channel; export in Field log |
| Flock-You Wi-Fi | Not implemented |
| Sky Spy Remote ID | Not implemented |
| BLE Sniff PCAP | Not implemented |

BlueZ discovery may transmit scan requests and aggregates properties across
advertisements. These scans are **not** the passive BLE mode from Unified Blue.
Same-advertisement Meta composite matching is not claimed. A candidate match does
not verify surveillance equipment, ownership or activity. No matches do not prove
the absence of a device.

## Wi-Fi capture

1. Configure the radio helper for your lab using the
   [lab guide](https://github.com/valleytechsolutions/Q-Marauder/blob/main/docs/LAB.md).
   Existing installs must update the helper for the new `capture` action.
2. Keep the supported monitor adapter attached. The onboard radio has not passed
   monitor receive tests; a PC-forwarded Alfa depends on that PC connection.
3. Run **Wi-Fi PCAP**. It uses the configured AP's channel and transmits no frames
   itself. Other system traffic is not disabled by this statement.
4. Open **Field log → PCAP** for that session. Read it with Wireshark.

Capture is capped at **512 KiB or 2,000 packets**, with a 4,096-byte snapshot length.
The report says whether the storage limit was reached. Captures may include nearby
traffic on the selected channel; treat exported files as private. Channel hopping,
rolling continuous capture and raw BLE link-layer export remain pending.

The existing injection check and bounded deauthentication lab test are separate
tools. Monitor reception does not prove injection, and injection does not prove
client disconnection. No broad attack is started by opening a detection mode.
