#!/bin/sh
# Explicit optional administrative step; does not flash or repartition the board.
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ "$(id -un)" != arduino ]; then
  printf '%s\n' 'This service profile targets the standard arduino account. Adapt the unit for another account.' >&2
  exit 1
fi
if [ ! -f /home/arduino/.local/lib/q-marauder/current/qmarauder/__main__.py ]; then
  printf '%s\n' 'Run sh scripts/install.sh first.' >&2
  exit 1
fi
if curl -fsS http://127.0.0.1:8787/api/state >/dev/null 2>&1; then
  printf '%s\n' 'A preview is already using port 8787. Stop that preview before enabling the boot service.' >&2
  exit 1
fi
sudo install -m 0644 "$SCRIPT_DIR/../packaging/q-marauder.service" /etc/systemd/system/q-marauder.service
sudo systemctl daemon-reload
sudo systemctl enable --now q-marauder.service
systemctl --no-pager status q-marauder.service
