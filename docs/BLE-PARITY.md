# BLE feature status

This file separates executable backends from future work. An upstream feature
name in a menu or catalog is not evidence that the feature runs on UNO Q.

## ChimeraBLE

Reference: [Matthew Kukanich's ChimeraBLE](https://github.com/MatthewKuKanich/ChimeraBLE),
inspected commit `2330423dae8f8fa163617172310784889d8972a7`.

| Workflow | Q-Marauder status |
| --- | --- |
| Scan, list, device info | Working BlueZ discovery and metadata; physical Flipper observation verified |
| Advertising decoding / vendor fingerprints | Partial: selected company/service mappings and iBeacon format; no full AD parser or vendor database |
| Foxhunt | Bounded RSSI samples, peak and trend; continuous audio feedback pending |
| Connect / disconnect | Per-job owned connections; existing connections refused |
| MTU / security / bonds | BlueZ-managed MTU; custom MTU and interactive security/bond UI pending |
| GATT dump | Service/characteristic inventory implemented; full value/descriptor snapshot pending |
| Read / write / write-without-response | Implemented by unique UUID; physical validation pending |
| Subscribe / unsubscribe | Bounded notification capture and cleanup implemented; physical validation pending |
| HID maps / input streams | Pending |
| Clone profiles / advertise / MAC spoof | Pending |
| Proxy / MITM / honeypot | Pending |
| JSON / CLI / native UI | JSON archive and web/TFT controls; command-language parity pending |

ChimeraBLE declares GPL-3.0-or-later. Its code and vendor databases have not been
copied into Q-Marauder's MIT application. Implementations here use BlueZ APIs
independently. A future source integration must preserve its actual license;
renaming a module does not relicense it.

## Unified Blue

Reference: [Colonel Panic's Unified Blue](https://github.com/colonelpanichacks/oui-spy-unified-blue),
inspected commit `6e5e2829540925ff1ab5fa6d0d365378818ed56e`.

| Mode | Q-Marauder status |
| --- | --- |
| Detector | Five configurable watchlist classes; no vendor presets, same-packet Meta composite or buzzer alerts |
| Foxhunter | Bounded signal tracking; continuous audio pending |
| Flock-You | Pending: combined Wi-Fi/BLE signatures and channel scheduling |
| Wi-Fi PCAP | Pending: general rolling PCAP/export; existing lab counters are separate |
| Sky Spy | Pending: Remote ID capture/decoding and recorded validation fixtures |
| BLE Sniff | Pending: passive raw advertising capture and correct PCAP framing |
| AXEOFF | Pending: combined BLE/Wi-Fi signatures and headless alerts |

No repository-wide license was found in the inspected Unified Blue tree. Some
OpenDroneID files carry their own Apache notices; those do not license the whole
firmware. No implementation or signature database was copied. Obtain an explicit
license before importing source, or continue independent implementations.

## What full parity requires

Pairing and protected GATT operations need a confirmed physical device session.
Peripheral/central concurrency and controller address control must be validated
on the actual BlueZ controllers. Passive detectors need raw packet backends,
fixtures and field validation; aggregated properties cannot prove that two fields
occurred in one advertisement. Audio modes need a supported output device from
the [BOM](BOM.md). The project does not currently claim complete parity with either upstream.
