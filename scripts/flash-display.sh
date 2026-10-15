#!/bin/sh
# Tested factory-core upload. Debian and the Zephyr runtime are preserved.
set -eu
umask 077
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
core_version=$(arduino-cli core list | awk '$1 == "arduino:zephyr" {print $2}')
if [ "$core_version" != '0.11.0-rc5' ]; then
  echo 'This helper is validated only for factory zephyr 0.11.0-rc5; see firmware/README.md.' >&2
  exit 1
fi
if ! tr '\000' '\n' < /proc/device-tree/model | grep -q 'Arduino.*Imola'; then
  echo 'Expected the Arduino UNO Q Linux environment.' >&2
  exit 1
fi
build="$HOME/.cache/q-marauder-tft-build"
data="$HOME/.local/share/q-marauder"
mkdir -p "$data"
arduino-cli lib install 'Arduino_RouterBridge@0.4.3' 'Arduino_RPClite@0.3.1' \
  'MsgPack@0.4.2' 'Adafruit GFX Library@1.12.6' 'Adafruit BusIO@1.17.4'
arduino-cli compile --fqbn arduino:zephyr:unoq --build-path "$build" "$root/firmware/uno_shield"
backup="$data/mcu-before-q-marauder.bin"
if [ ! -f "$backup" ]; then
  # Fixed address/length for the UNO Q STM32U585's 2 MiB internal flash.
  /opt/openocd/bin/openocd -d2 -s /opt/openocd \
    -s /opt/openocd/share/openocd/scripts -f openocd_gpiod.cfg \
    -c "telnet port disabled; gdb port disabled; tcl port disabled; init; halt; dump_image {$backup.tmp} 0x08000000 0x200000; resume; shutdown"
  test "$(wc -c < "$backup.tmp")" -eq 2097152
  mv "$backup.tmp" "$backup"
  sha256sum "$backup" > "$backup.sha256"
fi
test "$(wc -c < "$backup")" -eq 2097152
echo "Recovery backup: $backup"
reopen() { arduino-router-cli '$/serial/open' /dev/ttyHS1 >/dev/null; }
trap reopen EXIT
arduino-router-cli '$/serial/close' /dev/ttyHS1 >/dev/null
"$HOME/.arduino15/packages/arduino/tools/remoteocd/0.0.2-rc.1/remoteocd" \
  upload -a 0x80F0000 "$build/uno_shield.ino.elf-zsk.bin"
reopen
trap - EXIT
echo 'MCU uploaded. With USB at the bottom, select the readable orientation, then tap/release the three calibration circles.'
echo 'Run python3 -m qmarauder serve to connect the native menu to Linux.'
