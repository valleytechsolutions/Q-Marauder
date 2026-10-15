# Marauder parity and roadmap

The inventory in `qmarauder/features.json` is the executable source of status for
the Modules view. Regenerate with `python3 scripts/build_catalog.py`. It records
81 named capabilities/integration targets, including management and future detectors.
This is an inventory, not an assertion that all upstream implementation details
have already been mapped or that every wiki URL is a standalone page.

## Release stages

| Stage | Exit evidence |
| --- | --- |
| Foundation (current alpha) | Linux console, real AP/BLE discovery, durable exports, diagnostics, USB install |
| Display | Exact shield electrical/pin profile, native STM32 renderer, touch calibration, logos, cold-boot test |
| Capture | Monitor creation, valid radiotap/802.11 PCAP, EAPOL/PMKID/SAE decoding, deauth detection, packet loss tests |
| Field collection | USB GPS fix, GPX/WiGLE exporters, BLE missions, target tracking, geofences, offline map |
| Active-test parity | Per-feature Linux backend, verified radio capability, bounded scoped jobs and cancellation |
| Detector packs | Named project source/license review, decoded payloads, signature fixtures, false-positive checks |
| Distribution | Signed source/package releases, reproducible arm64 image recipe, tested recovery and upgrade |

## Compatibility decisions

The optional lab helper now provides an eight-second metadata recon job, ten
directed injection probes and a three-frame deauthentication test. These are
implemented subsets with automated tests. Admin setup is complete on the test board,
but live stock-radio tests returned no monitor packets or directed responses.
They do not establish all Marauder recon/attack behavior. See [lab setup](LAB.md).
Wardriving expansion is deferred while scanning and lab radio work are validated.

- Scan APs maps to NetworkManager. Scanning stations and sniffing frames need monitor capture.
- Channel chart currently counts visible APs; it is not packet/channel utilization.
- Raw capture and handshake analysis must consume real captures and retain provenance.
- Linux nl80211/BlueZ replace ESP32-only APIs. Copying `WiFiScan.cpp` cannot make Qualcomm radios behave as ESP32.
- AP/portal tests require management-link separation and an isolated network configuration.
- BLE advertising tests require a BlueZ/HCI backend; advertised controller support is not payload parity.
- GPS uses gpsd on Linux. UNO Q has no validated on-board GNSS receiver in this setup.
- eMMC files/SQLite replace ESP32 SPIFFS/SD storage. MCU firmware and Linux upgrades are separate artifacts.
- Flipper/serial compatibility needs a deliberate protocol implementation and parser tests.
- CSI motion features may require telemetry absent from the installed radio firmware.
- The 5 GHz band includes driver/regulatory restrictions; no release should claim every channel is usable.

## Future detectors

Dragon Detector, Axeoff, and Squachwach are requested integration names. Their
repositories, licenses, hardware needs, and earlier work were not supplied in this
chat. They currently have no detector implementation. Obtain those sources before
deciding whether to embed, adapt, or run them as isolated services.

Upstream baseline: [Marauder applications](https://github.com/justcallmekoko/ESP32Marauder/wiki/applications).
Upstream source and wiki commits are pinned in `THIRD_PARTY_NOTICES.md`.
