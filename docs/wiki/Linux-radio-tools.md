# Linux radio tools

Q-Marauder is beginning a Wi-Fi/Bluetooth workflow port of
[Raspyjack by 7h30th3r0n3](https://github.com/7h30th3r0n3/Raspyjack).

- **Desktop:** Applications → Q-Marauder Lab → Lab → Linux radio tools.
- **Portrait TFT:** Home / Wi-Fi / Bluetooth → Linux tools.
- **Feature status:** Linux tools → Port inventory on TFT, or Raspyjack wireless port inventory in the desktop workspace.

The first tools are **Radio interfaces**, **Wi-Fi security survey**, **Bluetooth
controllers** and an eight-second **Bluetooth Classic scan**. Reports are shared
between both interfaces, saved locally and exportable as JSON. The status inventory
tracks 45 wireless entries; it is not a claim that all 45 are working.

The Debian launcher now prefers a native GTK/WebKit application window, embedding
the complete Q-Marauder interface. A Chromium app-window fallback is retained.
The portrait screen continues to render locally on the STM32.

![Portrait Linux tools menu software render](https://raw.githubusercontent.com/valleytechsolutions/Q-Marauder/main/docs/images/tft/linux-tools.png)

Software render from current firmware drawing code, not a photograph of the panel.

See the [full integration guide](https://github.com/valleytechsolutions/Q-Marauder/blob/main/docs/RASPYJACK.md)
for dependencies, update steps, scope and limitations. RFID/NFC, sub-GHz and SDR
are outside this port's scope. The Raspyjack installer and arbitrary payload runner
are not installed on the UNO Q.
