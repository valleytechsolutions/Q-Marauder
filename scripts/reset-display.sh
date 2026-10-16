#!/bin/sh
# Restart the installed MCU sketch without writing flash or changing saved settings.
set -eu
if ! tr '\000' '\n' < /proc/device-tree/model | grep -q 'Arduino.*Imola'; then
  echo 'Expected the Arduino UNO Q Linux environment.' >&2
  exit 1
fi
test -x /opt/openocd/bin/openocd
reopen() { arduino-router-cli '$/serial/open' /dev/ttyHS1 >/dev/null; }
trap reopen EXIT
arduino-router-cli '$/serial/close' /dev/ttyHS1 >/dev/null
/opt/openocd/bin/openocd -d2 -s /opt/openocd -f openocd_gpiod.cfg \
  -c 'telnet port disabled; gdb port disabled; tcl port disabled; reset_config srst_only srst_push_pull; init; reset; shutdown'
reopen
trap - EXIT
echo 'Display MCU restarted. The Linux console will restore saved portrait and touch settings.'
