# Desktop lab

![Q-Marauder Lab workspace](https://raw.githubusercontent.com/valleytechsolutions/Q-Marauder/main/docs/images/desktop-lab.jpg)

The Debian installer adds **Q-Marauder Lab** to the Applications menu. Connect an
HDMI monitor through a powered USB-C hub supporting DisplayPort Alt Mode, attach a
keyboard/mouse, sign into XFCE, then open the app.

```sh
~/.local/bin/q-marauder desktop
```

It reuses the local service or starts it on demand and opens a Chromium application
window. The Lab workspace contains radio recon, BLE reverse engineering, lab radio
tests, detector modes and evidence exports. It shares settings and jobs with the
portrait display. Closing the window leaves the service running for the TFT.

The development board already has XFCE and Chromium. The launcher and workspace
are installed; physical HDMI/hub validation is still outstanding.

**Changing USB arrangements matters:** unplugging the PC cable removes ADB and
the PC-forwarded Alfa. A standalone desk setup needs the radio directly on the
powered hub and its interface/profile rechecked.

[Detailed desktop and hub guide](https://github.com/valleytechsolutions/Q-Marauder/blob/main/docs/DESKTOP.md) ·
[Power choices](https://github.com/valleytechsolutions/Q-Marauder/wiki/Power-and-BOM)
