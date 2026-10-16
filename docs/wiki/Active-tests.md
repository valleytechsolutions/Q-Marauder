# Active tests

Q-Marauder does not yet provide every upstream attack or spam mode. A menu label
does not mean an operation has a backend or that RF transmission has been verified.

- **GATT read/write:** select your BLE device → USE → GATT inventory → select a
  characteristic → USE. Read, write with response, write without response and
  notification observation are available. Harmless Flipper RPC exchanges were verified.
- **BLE beacon test:** Bluetooth → Bluetooth Attacks → BLE beacon test. It registers
  three QM-LAB names for two seconds each. BACK → Stop beacon test cancels early;
  the browser has a Stop button. Controller acceptance and cleanup were verified,
  but the independent PC receiver did not confirm RF reception.
- **Wi-Fi injection check:** WiFi → Attacks → Injection check. Requires the local
  authorized AP profile and a working monitor radio. Ten probes are bounded; only
  a received reply from the selected AP to the unique test source counts as evidence.
- **Lab deauth:** three frames, gated behind a successful injection check within
  ten minutes on the same AP/channel/interface. It remains unvalidated on this setup.

Platform BLE popup/crash spam, Wi-Fi floods/portals, GATT proxy/emulation and other
attack families remain planned. No broad attack is started by a detection mode.

For setup and the rollout blockers, read the
[active-test matrix](https://github.com/valleytechsolutions/Q-Marauder/blob/main/docs/ACTIVE-TESTS.md).
The LED matrix settings request is queued after the security rollout work.
