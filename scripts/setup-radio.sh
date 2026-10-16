#!/bin/sh
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
printf '1. Install/update BLE capture (retain existing Wi-Fi profile)\n2. Choose a Wi-Fi lab radio and access point\nSelection [1]: '
read -r selection
case "$selection" in
  2) python3 "$SCRIPT_DIR/configure-lab.py"
     exec sudo python3 "$SCRIPT_DIR/install-radio-helper.py" --profile "$HOME/.local/share/q-marauder/lab-profile.json" ;;
  1|'') exec sudo python3 "$SCRIPT_DIR/install-radio-helper.py" ;;
  *) printf 'Cancelled. No helper changes made.\n'; exit 1 ;;
esac
