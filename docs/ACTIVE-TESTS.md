# Active test status and how-to

This alpha is not ready to claim all Marauder/ChimeraBLE attacks or spam modes.
The table records executable behavior and the evidence still needed.

| Test | Use it | Current evidence |
| --- | --- | --- |
| GATT read/write, with and without response | Select a BLE device → USE → GATT inventory → characteristic → USE → Read/Write | Flipper battery read and harmless RPC writes/indications verified |
| Pair selected device | BLE tools → Pair; enter the fresh code | Browser pairing and bonded reconnect verified |
| BLE beacon test | Bluetooth → Bluetooth Attacks → BLE beacon test | Three QM-LAB names register for two seconds each; controller commands succeed and all registrations are removed. Independent PC receiver did not confirm RF reception |
| Stop beacon test | BACK → Stop beacon test, or browser Stop button | Cancellation exercised; zero advertising instances remained afterward |
| Wi-Fi injection check | WiFi → Attacks → Injection check | Ten bounded directed-SSID probes; no matching received AP replies in previous tests. RF injection remains unverified |
| Wi-Fi deauth | WiFi → Attacks → Lab deauth (3 frames) | Implemented, but blocked until a recent successful injection check on the same authorized AP/channel. No client-disconnect validation |
| Platform BLE popup/crash spam | Planned entries only | Not implemented; QM-LAB advertisements do not establish payload/behavior parity |
| Wi-Fi beacon/probe floods, portals, AP cloning, SAE and other attack families | Planned entries only | Not implemented or validated on this radio/backend |
| GATT proxy, cloning and MAC spoofing | Planned | Not implemented |

Use [radio setup](LAB.md) for the local AP allowlist and [BLE Lab](BLE.md) for
selected-target operations. The Wi-Fi profile wizard selects one exact AP BSSID;
multiple authorized APs can be configured explicitly in the local profile. Names
alone never authorize a Wi-Fi target. Shared management connections are preserved.

Opening an attack menu does not start a job. Transmit tests are separate from
detection modes. The beacon test has a fixed laboratory UUID and names; it does
not impersonate Apple, Samsung, Microsoft or tracking networks. A successful
BlueZ registration or socket send confirms software/controller acceptance, not
over-the-air reception or an effect on a client.

The external Alfa was missing from Windows and the UNO Q during the current
validation. Reconnect the adapter, run `scripts/Connect-Alfa.cmd`, refresh Test
readiness and repeat receive/injection checks before considering Wi-Fi transmit
features usable. A PC-forwarded radio requires the PC to remain attached.

Release blockers for full rollout: reliable monitor-radio enumeration and reboot
recovery, independently observed TX, physical Flock/Remote ID/HID fixtures, extended
stability testing, and the still-planned attack/emulation families. The requested
Settings controls for the UNO Q LED matrix are queued after the security rollout
work; this release does not add matrix controls.
