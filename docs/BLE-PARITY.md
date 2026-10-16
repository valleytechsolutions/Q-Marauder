# BLE feature status

This file separates executable backends from future work. An upstream feature
name in a menu or catalog is not evidence that the feature runs on UNO Q.

## ChimeraBLE

Reference: [Matthew Kukanich's ChimeraBLE](https://github.com/MatthewKuKanich/ChimeraBLE),
inspected commit `2330423dae8f8fa163617172310784889d8972a7`.

| Workflow | Q-Marauder status |
| --- | --- |
| Scan, list, device info | Working BlueZ discovery and metadata; physical Flipper observation verified |
| Advertising decoding / vendor fingerprints | Selected company/service mappings and iBeacon format; [same OUI source and /24 list as ChimeraBLE](OUI.md), with all 40,099 entries checked against its generator; no full raw AD parser |
| Foxhunt | Bounded RSSI samples, peak and trend; continuous audio feedback pending |
| Connect / disconnect | Per-job owned connections; existing connections refused |
| MTU / security / bonds | BlueZ-managed MTU; selected-device browser pairing and bonded reconnect verified on a Flipper; custom MTU and bond management pending |
| GATT dump | Inventory and bounded value/descriptor snapshot verified on a Flipper: 5 services, 15 characteristics, 6 descriptors and 20 reads; 24-second read budget |
| Read / write / write-without-response | Implemented by unique UUID; battery read and both write modes physically verified with harmless Flipper RPC pings |
| Subscribe / unsubscribe | 10-second capture and cleanup; received Flipper RPC indications verified with a diagnostic ping; general multi-operation sessions pending |
| HID maps / input streams | Report-map parser and 10-second input observation implemented; keyboard/mouse fixtures pass. Physical HID peripheral validation remains |
| Clone profiles / advertise / MAC spoof | Pending |
| Proxy / MITM / honeypot | Pending |
| JSON / CLI / native UI | JSON archive, portrait target/characteristic selection, read/write/notify, snapshot, HID, pairing keypad and adapter selection; command-language parity and native watchlist editor pending |

ChimeraBLE declares GPL-3.0-or-later. Its code and vendor databases have not been
copied into Q-Marauder's MIT application. The installer fetches the external
Wireshark registry separately, with source metadata and its own terms.
Implementations here use BlueZ APIs
independently. A future source integration must preserve its actual license;
renaming a module does not relicense it.

## Unified Blue

Reference: [Colonel Panic's Unified Blue](https://github.com/colonelpanichacks/oui-spy-unified-blue),
inspected commit `6e5e2829540925ff1ab5fa6d0d365378818ed56e`.

| Mode | Q-Marauder status |
| --- | --- |
| Detector | Five configurable watchlist classes plus public Axon/TASER identifier presets; same-packet Meta composite and buzzer alerts pending |
| Foxhunter | Bounded signal tracking; continuous audio pending |
| Flock-You | Pending: combined Wi-Fi/BLE signatures and channel scheduling |
| Wi-Fi PCAP | 8-second radiotap PCAP export, 512 KiB / 2000-packet bound; 321-packet live capture verified. Configured lab channel only; rolling capture/hopping pending |
| Sky Spy | Pending: Remote ID capture/decoding and recorded validation fixtures |
| BLE Sniff | Pending: passive raw advertising capture and correct PCAP framing |
| AXEOFF | BLE identifier candidates implemented; active BlueZ discovery. Wi-Fi signatures, passive capture and headless audio alerts pending |

No repository-wide license was found in the inspected Unified Blue tree. Some
OpenDroneID files carry their own Apache notices; those do not license the whole
firmware. No implementation or signature database was copied. Obtain an explicit
license before importing source, or continue independent implementations.

## What full parity requires

Pairing and protected GATT operations have a confirmed Flipper session; other
peripherals and pairing methods still need physical validation.
Peripheral/central concurrency and controller address control must be validated
on the actual BlueZ controllers. Passive detectors need raw packet backends,
fixtures and field validation; aggregated properties cannot prove that two fields
occurred in one advertisement. Audio modes need a supported output device from
the [BOM](BOM.md). The project does not currently claim complete parity with either upstream.
