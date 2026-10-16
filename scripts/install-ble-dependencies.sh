#!/bin/sh
set -eu
case "$(cat /proc/device-tree/model 2>/dev/null | tr -d '\000')" in
  *Arduino*Imola*) ;;
  *) echo 'This helper targets the UNO Q Debian system.' >&2; exit 1 ;;
esac
sudo apt-get update
sudo apt-get install -y python3-dbus python3-gi
python3 -c 'import dbus; from gi.repository import GLib; print("BLE Lab dependencies ready")'
