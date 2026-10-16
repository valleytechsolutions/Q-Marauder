# Detection and capture

Open **Lab → Detection modes** on the desktop, or **Counter surveillance** on the
portrait TFT. Run `scripts/Enable-BLELab.cmd`, then `scripts/Enable-LabRadio.cmd` →
**1** once for BLE capture. Choose **2** in the radio launcher to configure a Wi-Fi
monitor adapter and authorized AP. Updating the app alone does not update the root helper.

| Mode | Current behavior |
| --- | --- |
| Packet detector | HCI reports with same-report Meta company + FD5F matching; Flock/Axon candidates |
| Flock BLE | Specific service/name/public-OUI candidates; generic chipset company alone never matches |
| Flock Wi-Fi | Registered Flock transmitter OUI; channels 1/6/11 on an idle monitor radio, connected channel otherwise |
| Sky Spy BLE | Complete Remote ID FFFA advertisement messages |
| Sky Spy Wi-Fi | OpenDroneID beacons/NAN; Basic ID, Location, Authentication, Self ID, System, Operator ID |
| BLE Sniff PCAP | Received advertising events in HCI PCAP linktype 201; not BLE link-layer or connection sniffing |
| AXEOFF BLE | Public Axon/TASER identifier candidates through BlueZ discovery |
| AXEOFF Wi-Fi | Axon Enterprise transmitter OUI in management frames; same channel sampling and hardware limits as Flock Wi-Fi |
| Foxhunter | Twenty-second selected-target RSSI tracking |
| Wi-Fi PCAP | Eight-second radiotap capture on the configured lab channel |

Tap a mode once, wait for its receive window and open result rows for details.
The TFT shows packet counts, receiver coverage, evidence and Remote ID telemetry;
PREV/NEXT changes pages. Zero matches still produces a report. The latest packet report
is restored after restarting the app without repeating radio collection.

Download **PCAP** and **JSON** from Packet analysis or Field log. The limit is
512 KiB / 2,000 packets per capture. Files can contain nearby identifiers and
unverified broadcast locations; they remain private on the board by default.

BLE capture lasts twelve seconds and starts eight seconds of BlueZ discovery after
the HCI receiver is ready. Scan requests may transmit. Complete legacy and extended
reports are decoded; incomplete extended fragments are kept in PCAP but not matched.
Connection traffic and keys are excluded. This differs from Unified Blue's passive
link-layer capture. The broader community Wi-Fi fingerprint table is not included.

Real BLE captures saved 44–49 reports in validation windows. No actual Flock/drone
signature was seen; known positives and all six Remote ID families are covered by
synthetic reference-encoder fixtures. A candidate is not proof of surveillance.
Authentication signatures are not verified. Zero matches does not prove absence.

The new Wi-Fi sampling jobs still need live validation: the development Alfa stopped
enumerating on Windows. Earlier single-channel Alfa monitor capture was verified.
Onboard monitor reception and RF injection remain unverified. Keep the PC attached
when using a forwarded adapter.

[Detailed protocol/evidence guide](https://github.com/valleytechsolutions/Q-Marauder/blob/main/docs/DETECTION.md) ·
[Active test status](https://github.com/valleytechsolutions/Q-Marauder/blob/main/docs/ACTIVE-TESTS.md)
