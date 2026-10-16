"""Attach the PC-exported MT7921 over a localhost ADB reverse tunnel."""
import os
from pathlib import Path
import re
import subprocess
import sys
import time

def radios():
    return [p.name for p in Path("/sys/class/net").iterdir() if (p / "device/driver").resolve().name == "mt7921u"]

def main():
    if os.geteuid() != 0 or len(sys.argv) != 2 or not re.fullmatch(r"\d+-\d+(?:\.\d+)*", sys.argv[1]):
        raise SystemExit("Use: sudo python3 scripts/attach-usb-radio.py WINDOWS_BUS_ID")
    # adbd binds reverse TCP listeners on all interfaces. Restrict this one port
    # to the board's loopback without changing any existing firewall tables.
    rule = ["!", "-i", "lo", "-p", "tcp", "--dport", "3240", "-j", "DROP"]
    # Factory kernel provides xtables, not nftables. Add only these two rules.
    for firewall in ("iptables-legacy", "ip6tables-legacy"):
        exists = subprocess.run([firewall, "-w", "5", "-C", "INPUT", *rule], capture_output=True)
        if exists.returncode == 1:
            subprocess.run([firewall, "-w", "5", "-I", "INPUT", "1", *rule], check=True)
        elif exists.returncode:
            raise SystemExit(f"Cannot inspect {firewall}; refusing an exposed reverse tunnel.")
    for module in ("vhci_hcd", "mt7921u"):
        subprocess.run(["modprobe", module], check=True)
    current = radios()
    if len(current) > 1:
        raise SystemExit("More than one MT7921 radio found; select manually.")
    if not current:
        listing = subprocess.check_output(["usbip", "list", "-r", "127.0.0.1"], text=True, timeout=10)
        if not re.search(r"^\s*" + re.escape(sys.argv[1]) + r":.*\(0e8d:7961\)", listing, re.M | re.I):
            raise SystemExit("The selected export is not the expected MediaTek radio.")
        subprocess.run(["usbip", "attach", "-r", "127.0.0.1", "-b", sys.argv[1]], check=True, timeout=15)
        for _ in range(30):
            current = radios()
            if current: break
            time.sleep(1)
    if len(current) != 1:
        raise SystemExit("USB was attached but the radio did not appear. Inspect dmesg and usbip port before retrying.")
    subprocess.run(["nmcli", "device", "set", current[0], "autoconnect", "no"], check=True, timeout=10)
    print(f"Alfa ready: {current[0]}. Use this interface in your local lab profile. This command does not run a test.")

if __name__ == "__main__":
    main()
