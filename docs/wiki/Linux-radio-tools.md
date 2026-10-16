# Linux radio tools

Q-Marauder is beginning a Wi-Fi/Bluetooth workflow port of
[Raspyjack by 7h30th3r0n3](https://github.com/7h30th3r0n3/Raspyjack).

- **Desktop:** Applications → Q-Marauder Lab → Lab → Linux radio tools.
- **Portrait TFT:** Home / Wi-Fi / Bluetooth → Linux tools.
- **Feature status:** Linux tools → Port inventory on TFT, or Raspyjack wireless port inventory in the desktop workspace.

The eight tools are **Radio interfaces**, **Wi-Fi security survey**, **Bluetooth
controllers**, **Bluetooth Classic scan**, **Wi-Fi channel survey**, **Wi-Fi scan
changes**, **BLE advert summary** and **Saved Bluetooth devices**. Reports are shared
between both interfaces, saved locally and exportable as JSON. The status inventory
tracks 45 wireless entries; it is not a claim that all 45 are working.

On the TFT, page 2 contains the four new survey/cache tools. Page 3 → **Saved Linux
reports → a report → OPEN** opens history without rerunning its job. The owner
confirmed channel survey and saved-report navigation on the physical TFT.
On desktop, **Show tools** filters by radio and **Saved Linux reports** opens history.
Follow the [step-by-step survey guide](https://github.com/valleytechsolutions/Q-Marauder/blob/main/docs/SURVEY-TOOLS.md).

![Desktop Wi-Fi tools, actual browser capture](https://raw.githubusercontent.com/valleytechsolutions/Q-Marauder/main/docs/images/desktop-wifi-tools.jpg)
![Portrait survey menu, software render](https://raw.githubusercontent.com/valleytechsolutions/Q-Marauder/main/docs/images/tft/linux-analysis.png)

The Debian launcher now prefers a native GTK/WebKit application window, embedding
the complete Q-Marauder interface. A Chromium app-window fallback is retained.
The portrait screen continues to render locally on the STM32.

![Portrait Linux tools menu software render](https://raw.githubusercontent.com/valleytechsolutions/Q-Marauder/main/docs/images/tft/linux-tools.png)

Portrait images are software renders from current firmware drawing code, not panel
photographs. The desktop image shows the shared console in a browser; HDMI and the
native application window still need a physical-monitor acceptance check.

See the [full integration guide](https://github.com/valleytechsolutions/Q-Marauder/blob/main/docs/RASPYJACK.md)
for dependencies, update steps, scope and limitations. RFID/NFC, sub-GHz and SDR
are outside this port's scope. The Raspyjack installer and arbitrary payload runner
are not installed on the UNO Q.
