# Q-Marauder

**A Debian-native wireless field console for Arduino UNO Q.**

Black Wire Militia × Marauder-inspired tooling, with a graphite, cyan, and red UI.
MIT application code. Independent project; not an official JustCallMeKoko release.

> **0.1.0 foundation alpha — not a full Marauder port or flashable OS image.**
> Runs on the UNO Q's existing Debian installation. The native ILI9486 display now renders.
> Upright portrait, direct touch and theme switching are confirmed on the test shield; see [display setup](docs/DISPLAY.md) for the remaining checks.

## Works today

- Actual Wi-Fi AP discovery through NetworkManager, including observed 2.4/5 GHz networks.
- BlueZ BLE discovery with names, addresses, and RSSI where available.
- AP-count channel chart, filtering, device diagnostics, and an 81-entry port inventory.
- Repeated Wi-Fi survey sessions with SQLite persistence and CSV/JSON exports.
- Fresh gpsd position ingestion; no coordinates are fabricated when GPS is absent.
- A loopback-only dashboard accessed through USB ADB forwarding or an SSH tunnel.
- Original BWM and Marauder artwork in the application startup screen.
- Native 320 x 480 portrait firmware with direct row taps, large Back/page buttons,
  15 menu groups, and 147 selections. Unported functions are explicitly marked planned.
- BWM, Marauder, Biscuit Shop and Valleytech TFT themes with their supplied background artwork.
- Native Wi-Fi/BLE result pages with tap-to-open details.
- Optional bounded lab recon, injection-check and deauth backends, with local report
  history and a separate privileged worker. Stock-radio capture/injection tests have
  not succeeded; these RF functions are not verified. See [lab setup](docs/LAB.md).

## Quick start on the UNO Q

The supplied Arduino Debian image already provides Python, NetworkManager, and BlueZ.
No Python packages are required for the console.

```sh
git clone https://github.com/valleytechsolutions/Q-Marauder.git
cd Q-Marauder
python3 -m qmarauder doctor
python3 -m qmarauder serve
```

From a computer with Google's official platform-tools:

```sh
adb devices
adb -s YOUR_DEVICE_SERIAL forward tcp:8788 tcp:8787
```

Open **http://127.0.0.1:8788**. Alternatively use
`ssh -L 8788:127.0.0.1:8787 arduino@YOUR_BOARD`.
The console intentionally listens only on the board's loopback interface.

For a Windows USB deployment, run `scripts/Deploy-UnoQ.ps1` from a source checkout:

```powershell
.\scripts\Deploy-UnoQ.ps1 -Serial YOUR_DEVICE_SERIAL -AdbPath C:\path\to\adb.exe
```

For a persistent Linux install, use `sh scripts/install.sh`, then follow its output.
See [installation and recovery](docs/INSTALL.md) before enabling startup on boot.

## The hardware split matters

The Qualcomm QRB2210 runs the Linux radio backends, storage, and console. The STM32U585
owns the UNO shield headers. `firmware/uno_shield` drives the parallel ILI9486 shield
and exchanges small status/action messages with the Linux application. Follow
[display setup](firmware/README.md) for the tested factory core. The browser console
and the portrait TFT are separate renderers sharing the same radio worker.

The connected development board reports `ath10k_snoc`, 2.4/5 GHz channels, and monitor
mode support. Live monitor tests returned zero packets; ten directed probe
submissions returned no responses. Capture and injection remain **unverified**.
Advanced Marauder functions remain individually tracked in
[the parity plan](docs/PARITY.md) and the Modules view. A compatible external radio
is the next validation path. The detected PC-connected MT7921 adapter needs both a
Linux connection path and drivers missing from this board's current kernel. See
[USB radio support](docs/USB-RADIO.md).

## Development

```sh
python3 -m unittest discover -s tests -v
python3 scripts/build_catalog.py
python3 scripts/package.py
```

Use [architecture](docs/ARCHITECTURE.md), [display bring-up](docs/DISPLAY.md), and
[hardware evidence](docs/HARDWARE.md) to pick the next work item. Dragon Detector,
Axeoff, and Squachwach are reserved integration targets; their source repositories
and protocols still need to be identified.

Scans can contain identifiers and locations. Records stay on the device until you
export them. Use radio tests only in environments you own or are authorized to assess.
Do not commit local captures, credentials, or survey databases.

Application license: [MIT](LICENSE). Artwork and dependencies: [notices](THIRD_PARTY_NOTICES.md).
