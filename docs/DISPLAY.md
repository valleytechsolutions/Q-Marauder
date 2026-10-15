# ILI9486 shield bring-up

**Blocked on exact shield identification. No display pins have been driven and no
MCU flash has been performed by this project.**

ILI9486 identifies a display controller, not the board's wiring. UNO shields can
use an 8-bit parallel bus with shared analog control/touch pins; other 3.5-inch
boards use SPI or different controllers. Need the product link/model, PCB revision,
pin labels, and touch controller before selecting a driver.

1. Confirm bus and voltage/level-shifting schematic, especially any A0/A1 connections.
2. Record data/control/reset/backlight pins and input controller.
3. Compile a GPIO-safe diagnostic bridge sketch, then select a verified pin profile.
4. Test reset, controller identification where readable, and static RGB color bars.
5. Confirm rotation, address window, pixel order, and full 480×320 coverage.
6. Measure fill speed and available SRAM; implement clipped incremental rendering.
7. Display original BWM and Marauder assets side by side at MCU startup.
8. Calibrate touch, restore shared pins after sampling, and test boundary taps.
9. Add the Linux view-model bridge, reconnect behavior, and visible stale/offline state.
10. Test boot, reboot, disconnect/reconnect, and several hours of display operation.

The current browser startup screen uses unchanged source images. It is not a
bootloader splash, Plymouth configuration, or a verified TFT boot logo. Linux boot
branding can follow after the physical display has a working native renderer.
