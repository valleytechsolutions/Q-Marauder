# Troubleshooting

| Symptom | What to check |
| --- | --- |
| White or blank TFT | Check the exact shield/pinout, running MCU sketch and Linux bridge. Use `Repair-Display.cmd` for an already working installation; do not erase Debian. |
| Text mirrored or upside down | Restore the saved software orientation; USB belongs at the bottom. Do not randomly change MADCTL bits on a working clone panel. |
| Touch inaccurate | Settings → Calibrate touch. Press/release each circle, without holding through the next target. |
| No BLE results | Scan BLE or press SCAN on an empty results page. Cached lists are labelled. A completed scan can legitimately find zero fresh devices. |
| GATT tools ask for a target | BLE results → device → USE. Then GATT inventory → characteristic → USE. |
| Pairing code never appears | Keep the peer unlocked on its home screen, exit Bluetooth apps, cancel the expired attempt and retry. Use only the new code. |
| No notifications | Change a value on your own test peripheral during the window. A zero-event window is not automatically an error. |
| Vendor says unknown | Check Settings registry status. Private/random addresses deliberately receive no prefix vendor. |
| Capture action rejected | Update the installed radio helper. Source/application updates alone do not replace root-owned helper code. |
| BLE PCAP asks for setup | Run Enable-BLELab, then Enable-LabRadio → 1. BLE capture does not require a Wi-Fi AP profile. |
| Flock/Sky Spy reports zero matches | Check packet counts and coverage. Zero matches is a valid result, not proof that surveillance equipment or aircraft are absent. |
| Wi-Fi radio absent | Verify Windows sees the Alfa, reconnect it if needed, then run Connect-Alfa. Refresh readiness after attaching. A driver installed on disk is not an attached radio. |
| Beacon test registers but receiver sees nothing | Controller acceptance does not establish RF reception. This remains unverified on the development setup; do not infer spam functionality. |
| Capture returns zero packets | Verify the external adapter, monitor channel and forwarding. Do not equate advertised monitor support with reception. |
| Desktop app fails from ADB | Launch inside the signed-in graphical desktop. ADB alone does not provide a DISPLAY/Wayland session. |
| Alfa disappears in desk mode | Moving USB from PC to hub ends PC USB/IP forwarding. Attach/test the radio directly on the hub. |

Use System → Recheck for a diagnostics report. Remove private addresses, SSIDs,
coordinates, pairing codes and capture files before sharing an issue publicly.
Never post the Debian password.
