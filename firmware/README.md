# Native display firmware

`uno_shield` renders the real ILI9486 UNO shield in portrait, with a startup logo
screen, Marauder-style menu hierarchy, direct-touch rows, and BWM/Marauder/Biscuit Shop/Valleytech themes. It uses
the UNO Q STM32, with radio work and storage on Debian. See [hardware evidence and
touch validation](../docs/DISPLAY.md) before using another shield.

On the tested factory core, from the repository root on the board:

```sh
sh scripts/flash-display.sh
```

The helper builds first, backs up the MCU flash once, then flashes only the sketch.
It refuses an untested core version. It does not reinstall Debian or replace the
matching Zephyr runtime. The backup stays local and must never be published.

Keep the Linux application and display firmware from the same revision (the native
bridge uses protocol 11). With USB at the bottom, the BWM logo and animated loader
open the menu automatically. Startup uses a reference touch profile and silently
restores the saved orientation, calibration and theme through Linux.
**Settings → Calibrate touch** and **Settings → Screen orientation** remain available
for manual adjustment. Vertical-only calibrations from older builds are not reused.

To build without uploading:

```sh
arduino-cli lib install 'Arduino_RouterBridge@0.4.3' 'Arduino_RPClite@0.3.1' \
  'MsgPack@0.4.2' 'Adafruit GFX Library@1.12.6' 'Adafruit BusIO@1.17.4'
arduino-cli compile --fqbn arduino:zephyr:unoq firmware/uno_shield
```

`MenuData.h` is generated from the upstream checkout pinned in the notices, by
`scripts/build-tft-menus.py`. `LogoData.h` is generated from supplied source artwork
by `scripts/encode-tft-logos.py` (Pillow is a build-time dependency only). These
headers are checked in; normal firmware builds do not need either generator.

The touch transform and menu hit targets can be checked without the MCU runtime:

```sh
g++ -std=c++17 -I firmware/uno_shield tests/native_touch_test.cpp -o /tmp/qm-touch-test
/tmp/qm-touch-test
```

`bridge_probe` is the earlier GPIO-free diagnostic scaffold. It does not drive a TFT.
