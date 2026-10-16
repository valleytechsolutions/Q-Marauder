"""Install the fixed-command root helper and an explicit lab AP profile on Debian.

Run with sudo only after reviewing docs/LAB.md and the local JSON profile.
The profile and observations are never added to the source repository.
"""
import argparse
import json
import os
from pathlib import Path
import pwd
import re
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument("--profile", type=Path, help='Optional Wi-Fi lab profile; omit for BLE capture or to retain an existing profile')
parser.add_argument("--user", default="arduino")
args = parser.parse_args()
if os.geteuid() != 0:
    raise SystemExit("This one-time radio setup needs sudo; the console continues running unprivileged.")
if not re.fullmatch(r"[a-z_][a-z0-9_-]*", args.user) or pwd.getpwnam(args.user).pw_uid == 0:
    raise SystemExit("Choose a normal Debian account")
profile = json.loads(args.profile.read_text()) if args.profile else None
if profile is not None and (not isinstance(profile, dict) or set(profile) != {"interface", "ssid", "bssids"}):
    raise SystemExit("Profile must contain interface, ssid, bssids")
if profile is not None and (not isinstance(profile["interface"], str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,15}", profile["interface"]) or profile["interface"] == "qmmon"):
    raise SystemExit("Invalid interface")
if profile is not None and (not isinstance(profile["ssid"], str) or not 1 <= len(profile["ssid"].encode()) <= 32 or "\x00" in profile["ssid"]):
    raise SystemExit("Invalid SSID")
if profile is not None and (not isinstance(profile["bssids"], list) or not 1 <= len(profile["bssids"]) <= 16):
    raise SystemExit("Expected 1 to 16 BSSIDs")
for address in profile['bssids'] if profile is not None else []:
    if (not isinstance(address, str) or not re.fullmatch(r"(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}", address)
            or int(address[:2], 16) & 1 or address == "00:00:00:00:00:00"):
        raise SystemExit("Invalid unicast BSSID")
root = Path(__file__).resolve().parents[1]
os.umask(0o077)
subprocess.run(["/usr/bin/apt-get", "install", "-y", "iw", "iproute2", "sudo"], check=True)
helper = Path("/usr/local/libexec/q-marauder-radio")
helper.parent.mkdir(parents=True, exist_ok=True)
if helper.parent.stat().st_uid != 0 or helper.parent.stat().st_mode & 0o022:
    raise SystemExit("Helper directory must be root-owned and not writable by others")
# Atomic replacement also avoids following an existing destination symlink.
with tempfile.NamedTemporaryFile(dir=helper.parent, delete=False) as output:
    output.write((root / "qmarauder/lab_helper.py").read_bytes())
    temporary = Path(output.name)
temporary.chmod(0o755)
temporary.replace(helper)
config = Path("/etc/q-marauder")
config.mkdir(mode=0o700, exist_ok=True)
if config.is_symlink() or config.stat().st_uid != 0 or config.stat().st_mode & 0o022:
    raise SystemExit("Lab config directory must be root-owned and not writable by others")
if profile is not None:
    with tempfile.NamedTemporaryFile(dir=config, mode="w", delete=False) as output:
        json.dump(profile, output)
        temporary = Path(output.name)
    temporary.replace(config / "lab.json")
commands = ", ".join(f"{helper} {action}" for action in ('status','recon','injection','deauth','capture','wifi-discovery'))
with tempfile.NamedTemporaryFile(dir="/etc/sudoers.d", mode="w", delete=False) as output:
    output.write(f"{args.user} ALL=(root) NOPASSWD: {commands}\n")
    temporary = Path(output.name)
try:
    subprocess.run(["/usr/sbin/visudo", "-cf", str(temporary)], check=True)
    temporary.chmod(0o440)
    temporary.replace("/etc/sudoers.d/q-marauder-radio")
finally:
    temporary.unlink(missing_ok=True)
print("Installed fixed lab actions for", args.user)
socket_unit = (root / "packaging/q-marauder-radio.socket").read_text().replace("SocketGroup=arduino", f"SocketGroup={pwd.getpwnam(args.user).pw_gid}")
for name, content in (("q-marauder-radio.socket", socket_unit),
                      ("q-marauder-radio@.service", (root / "packaging/q-marauder-radio@.service").read_text())):
    destination = Path("/etc/systemd/system") / name
    with tempfile.NamedTemporaryFile(dir=destination.parent, mode="w", delete=False) as output:
        output.write(content)
        temporary = Path(output.name)
    temporary.chmod(0o644)
    temporary.replace(destination)
subprocess.run(["systemctl", "daemon-reload"], check=True)
subprocess.run(["systemctl", "enable", "--now", "q-marauder-radio.socket"], check=True)
print("Enabled local radio socket; no radio job starts until explicitly requested.")
print("Run Test readiness, then Lab packet recon, then Injection check on the TFT.")
print("This setup does not run radio tests or alter the managed Wi-Fi connection.")
