# Installation, startup, and recovery

New users: start with the [illustrated Windows installer guide](GETTING-STARTED.md)
and [bill of materials](BOM.md). This page covers manual deployment and recovery.

## Keep Arduino Debian as the board-support base

The first release is a user-space application, not a replacement Linux image. Use
Arduino's supported Debian image for bootloader, kernel, device tree, radio firmware,
and MCU tooling. A browser flasher for ESP32 serial bootloaders cannot be repurposed
for the UNO Q by changing a device ID.

The immediate easy path is USB ADB deployment (`Deploy-UnoQ.ps1`) or SSH + clone.
The app runs without pip dependencies. Python 3.11+ is required, along with `nmcli`
and `bluetoothctl` for the corresponding radio actions. `iw` is optional for
capability diagnostics; `gpsd` plus a supported GNSS receiver is required for positions.

## Install and run

Run `sh scripts/install.sh` as the normal board user. It stores an immutable revision
under `~/.local/lib/q-marauder/releases`, switches `current` atomically, and creates
`~/.local/bin/q-marauder`. Observations are separate under `~/.local/share/q-marauder`.
Old revisions remain available. Installation does not start radio collection.

Run `~/.local/bin/q-marauder serve`. Or, for an unprivileged background preview from
the source checkout, run `python3 scripts/start.py`. Its log and PID are in the data
directory. The preview is temporary and does not survive a reboot automatically.
`start.py` deliberately does not terminate another process using port 8787.

To update a running preview, run `python3 scripts/stop-preview.py` from its source
checkout, then rerun `scripts/start.py`. The stop helper verifies the PID's command
line and checkout before signaling it. For a systemd install, restart the service after
installing a new revision. Do not run two consoles against the same data directory.

## Start on boot

The standard service profile targets `/home/arduino` and the `arduino` user. Run
`sh scripts/enable-boot.sh` on Debian after stopping the preview. The command uses
sudo interactively to install/enable `q-marauder.service`. Enter any sudo password
in your own board terminal, not in a chat or source file.

The service is unprivileged, uses a read-only home mount except its data directory,
and starts no radio job on boot. This unit has not yet been enabled on the original
development board; the working source preview still needs manual startup after reboot.
The optional [radio helper](LAB.md) has a separate socket-activated service. Installing
it does not enable console boot startup. Its socket works with the console unit's
existing no-new-privileges restriction; do not remove that restriction to enable sudo.

Check `systemctl status q-marauder` and `journalctl -u q-marauder`. Use USB forwarding
or SSH tunneling to view the UI. Do not expose the unauthenticated console on a LAN.

## Rollback

Stop the service, repoint `~/.local/lib/q-marauder/current` to a retained revision,
then restart it. This alpha has one schema version; future migrations must ship with
backup/compatibility rules. Export and back up records before major upgrades.

## Uninstall

Stop/disable the service if enabled and remove its systemd unit. The application and
data live in separate, clearly named directories. Archive observations before
removing the data directory. No Arduino partitions, Wi-Fi profiles, bootloader, or
existing MCU firmware are modified by the application installer.

## Native shield firmware

The separate `sh scripts/flash-display.sh` helper does replace the MCU sketch. It
compiles first and saves a private full-flash recovery backup in the data directory.
It currently accepts only the tested factory Zephyr core; it is not a universal
flasher for every UNO Q software version. See [firmware setup](../firmware/README.md).
After upload, follow the TFT's orientation selection and three-circle touch calibration. Start the Linux
console to enable live menu actions and save calibration across MCU resets.

For a previously working screen that remains blank after a restart, use
**Repair-Display.cmd** on Windows, or `sh scripts/reset-display.sh` on the board
with the console running. This restarts only the MCU through Arduino's OpenOCD
reset path; it does not write flash. The bridge restores saved display settings.
The reset helper disables OpenOCD's network listeners during this operation.

## Image recovery and future web installation

Arduino's [official flasher](https://docs.arduino.cc/software/app-lab/configure/flash/)
replaces the OS and stored data. Use it only as an explicit recovery/reimage step.
There is no Q-Marauder OS image in this release.

The Windows launcher checks board identity and the supported display core, then
runs the source installer and TFT uploader. ZIP and tar.gz releases include the
same allowlisted source files and SHA-256 checksums. Signed releases and broader
runtime support remain future work. A genuine browser-only flasher needs demonstrated USB/bootloader support
and recovery testing; a button that merely downloads a file is not a web flasher.
