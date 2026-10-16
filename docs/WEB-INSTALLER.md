# Can UNO Q use a web flasher?

**A browser application installer is feasible in principle; a complete browser
OS flasher is a separate, unvalidated project.** No working browser installer is
shipped with this alpha. The supported route is the [Windows USB installer](GETTING-STARTED.md).

UNO Q combines a Debian Linux system and a separate STM32 display sketch. An
ESP32 Web Serial flasher cannot flash this hardware.

## Recommended browser route: initialized Debian

A future HTTPS page could use WebUSB with an ADB implementation to:

1. Ask the user to select the initialized UNO Q and authorize its ADB connection.
2. Verify board model, account, free space and supported Arduino core.
3. Transfer a versioned release after checking its pinned digest.
4. Install the Linux application; preserve data and the original MCU backup.
5. Compile/upload only the compatible TFT sketch and verify bridge protocol.
6. Report separate application, TFT and saved-calibration status.

This follows the existing installer's architecture. It is a design proposal, not
an assertion that this board's USB interface has passed browser tests. It needs
Chrome/Edge hardware testing on supported host OSes, ADB authentication, reliable
transfer/reconnect behavior and interrupted-upload recovery. The desktop ADB
server may already own the USB interface; taking it over can interrupt the console
and PC-forwarded radio. Windows driver/interface requirements also need testing.

WebUSB requires a secure context and a user gesture/device chooser. These browser
permissions cannot be silently pre-approved. A browser UI backed by the existing
local installer is another option, but still requires installing a local helper;
it would need loopback authentication, same-origin checks and fixed operations.

## Complete Debian installation / recovery

Arduino's official `arduino-flasher-cli flash unoq` uses an embedded **qdl**
component for the Qualcomm download path. A browser recovery flasher would need
that protocol, USB re-enumeration, image compatibility checks and tested recovery
from interruption. Do not replace it with an ESP32 `.bin` upload page.

Keep official Arduino tooling for initial setup and recovery while developing the
application installer. That avoids promising a one-click browser recovery path
that has not been validated.

Sources: [Arduino flasher CLI](https://github.com/arduino/arduino-flasher-cli),
[UNO Q image update guide](https://docs.arduino.cc/tutorials/uno-q/update-image/),
[Chrome WebUSB requirements](https://developer.chrome.com/docs/capabilities/usb).
