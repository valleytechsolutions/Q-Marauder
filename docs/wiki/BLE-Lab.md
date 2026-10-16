# BLE Lab

## Select and pair

1. Enable Bluetooth on the peripheral you own and keep it nearby.
2. Run BLE discovery. Choose **Use as target** in the browser, or tap the device
   row then **USE** on the TFT.
3. Choose **Pair selected device** if the peripheral requires bonding.
4. Enter its current code on the TFT or in the browser; confirm comparisons only
   when they match. Old codes from expired attempts cannot be reused.
5. Open GATT inventory and choose a characteristic.

The pairing agent is scoped to the selected device. It does not become the global
agent, mark all devices trusted, automatically accept comparisons or remove bonds.

## Inspect

| Tool | Result |
| --- | --- |
| GATT inventory | Services, characteristic UUIDs/flags, descriptors and reported MTU |
| GATT snapshot | Bounded readable-value and descriptor snapshot, including per-value failures |
| Read / write | A unique characteristic UUID; duplicate UUIDs are refused |
| Listen notifications | Ten-second window; values and timestamps saved in JSON |
| Inspect HID map | Parsed report IDs, input/output/feature fields and byte sizes |
| Listen HID reports | Ten-second input-report window decoded using Report Reference descriptors |
| Track signal | Twenty seconds of fresh RSSI, peak and trend; not a distance estimate |

Every GATT job opens its own connection and closes only that connection afterward.
An existing foreign connection is refused. Zero notifications can simply mean no
value changed. HID decoding emits usage IDs and axis values, not OS keyboard events.
Unsupported or ambiguous layouts are reported rather than guessed.

The development Momentum Flipper has verified pairing, reconnects, reads, harmless
RPC ping writes/indications and a snapshot of **5 services, 15 characteristics and
6 descriptors**. It does not expose a HID service, so HID hardware verification
requires a separate BLE keyboard, mouse or gamepad.

## Vendor lookup

The same Wireshark /24 source used by ChimeraBLE supplies vendor hints. The initial
installed snapshot has **40,099 prefixes**. Random/private BLE addresses are not
matched by prefix. Advertising company IDs and OUI vendors are separate signals;
neither proves a device's identity.

Clone/emulation/proxy, manual MTU negotiation and comprehensive bond management
remain unfinished. See the [complete status matrix](https://github.com/valleytechsolutions/Q-Marauder/blob/main/docs/BLE-PARITY.md).

![Verified browser pairing result from the previous build](https://raw.githubusercontent.com/valleytechsolutions/Q-Marauder/main/docs/images/ble-paired.jpg)
