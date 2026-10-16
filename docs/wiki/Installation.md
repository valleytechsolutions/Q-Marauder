# Installation

Q-Marauder installs on Arduino's existing Debian system and uploads a separate
MCU sketch for the TFT. It does **not** erase the OS or use ESP32 flash offsets.

1. With power off, fit the supported parallel dual-header 3.5-inch UNO shield.
2. Complete Arduino App Lab's initial UNO Q setup and Wi-Fi configuration.
3. Download the latest [release ZIP](https://github.com/valleytechsolutions/Q-Marauder/releases) and Extract All.
4. Put Google's Platform-Tools in `.tools/platform-tools`, or use an installed `adb`.
5. Connect the board directly to the Windows PC with a data-capable USB cable.
6. Double-click `Install-QMarauder.cmd`. Keep power connected through the build and upload.
7. If prompted, choose upright portrait orientation with USB at the bottom, then
   press and release the three touch calibration targets.
8. Run `scripts/Enable-BLELab.cmd` once for Debian's D-Bus bindings.

The display uploader accepts the tested **Zephyr 0.11.0-rc5** core. It stops if the
core differs; do not force a runtime downgrade. The installer saves a full MCU
recovery backup on the board and retains prior Linux application revisions.

For an application-only update from PowerShell in the extracted source folder:

```powershell
.\scripts\Install-Windows.ps1 -AppOnly
```

After reboot, `Start-QMarauder.cmd` starts the PC-tethered console. The desktop
launcher can start it from XFCE. Unattended handheld boot needs the separately
documented boot-service setup; installation alone does not enable that service.

The OUI database downloads once if absent. Offline installation still runs scans
without vendor lookup; see [OUI instructions](https://github.com/valleytechsolutions/Q-Marauder/blob/main/docs/OUI.md).

[Illustrated full guide and recovery](https://github.com/valleytechsolutions/Q-Marauder/blob/main/docs/GETTING-STARTED.md) ·
[Browser installer assessment](https://github.com/valleytechsolutions/Q-Marauder/blob/main/docs/WEB-INSTALLER.md)

A WebUSB/ADB installer is technically a possible future frontend after first-board
setup. No browser-only UNO Q OS flasher is shipped in this release.
