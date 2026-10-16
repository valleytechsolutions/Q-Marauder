#!/usr/bin/python3 -I
"""Root-owned, fixed-command helper for a configured lab radio and AP allowlist.

Installed as a standalone file: never import code from the user's checkout as root.
Recon returns aggregate metadata only. Transmit jobs are bounded and require an
explicit root-owned lab profile; deauth also requires a recent directed-probe response.
"""
import json
import base64
import os
from pathlib import Path
import re
import secrets
import signal
import socket
import struct
import subprocess
import sys
import time
from contextlib import contextmanager

CONFIG = Path("/etc/q-marauder/lab.json")
STATE = Path("/var/lib/q-marauder-radio")
MONITOR = "qmmon"
TOOLS = {"iw": "/usr/sbin/iw", "ip": "/usr/sbin/ip", "nmcli": "/usr/bin/nmcli"}


def socket_action(stream):
    line = stream.readline(32)
    if line not in ("status\n", "recon\n", "injection\n", "deauth\n", "capture\n"):
        raise ValueError("Expected one fixed radio action")
    return line.strip()


@contextmanager
def exclusive_radio():
    import fcntl
    STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (STATE / "job.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("A lab radio job is already running") from exc
        yield


def command(*args):
    result = subprocess.run([TOOLS[args[0]], *args[1:]], capture_output=True, text=True,
                            timeout=4, env={"PATH": "/usr/sbin:/usr/bin", "LC_ALL": "C"}, cwd="/")
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout).strip()[:300])
    return result.stdout


def validate_profile(profile):
    if not isinstance(profile, dict) or set(profile) != {"interface", "ssid", "bssids"}:
        raise ValueError("Expected interface, ssid and bssids")
    if not isinstance(profile["interface"], str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,15}", profile["interface"]) or profile["interface"] == MONITOR:
        raise ValueError("Invalid lab interface")
    if not isinstance(profile["ssid"], str) or not 1 <= len(profile["ssid"].encode()) <= 32 or "\x00" in profile["ssid"]:
        raise ValueError("Invalid lab SSID")
    addresses = profile["bssids"]
    if not isinstance(addresses, list) or not 1 <= len(addresses) <= 16:
        raise ValueError("Configure 1 to 16 lab BSSIDs")
    for address in addresses:
        if not isinstance(address, str) or not re.fullmatch(r"(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}", address):
            raise ValueError("Invalid lab BSSID")
        if int(address[:2], 16) & 1 or address == "00:00:00:00:00:00":
            raise ValueError("Lab BSSID must be unicast")
    return {**profile, "bssids": [a.upper() for a in addresses]}


def load_profile():
    stat = CONFIG.stat()
    if stat.st_uid != 0 or stat.st_mode & 0o022:
        raise RuntimeError("Lab profile must be root-owned and not writable by other users")
    return validate_profile(json.loads(CONFIG.read_text()))


def split_fields(line):
    fields, value, escaped = [], [], False
    for char in line:
        if escaped:
            value.append(char); escaped = False
        elif char == "\\":
            escaped = True
        elif char == ":":
            fields.append("".join(value)); value = []
        else:
            value.append(char)
    return fields + ["".join(value)]


def target_for(profile):
    interface = profile["interface"]
    link = command("iw", "dev", interface, "link")
    frequency = re.search(r"freq:\s*(\d+)", link)
    connected = "Connected to " in link
    if connected and not frequency:
        raise RuntimeError("Cannot determine connected channel; refusing to retune")
    rows = command("nmcli", "--terse", "--escape", "yes", "--fields", "BSSID,SSID,FREQ,SIGNAL",
                   "device", "wifi", "list", "ifname", interface, "--rescan", "no")
    candidates = []
    for line in rows.splitlines():
        fields = split_fields(line)
        if len(fields) != 4:
            continue
        address, ssid, mhz, strength = fields
        if address.upper() not in profile["bssids"] or ssid != profile["ssid"]:
            continue
        try:
            mhz, strength = int(mhz.split()[0]), int(strength)
        except (ValueError, IndexError):
            continue
        if connected and mhz != int(frequency[1]):
            continue
        if 2400 <= mhz <= 5900:
            candidates.append(dict(bssid=address.upper(), frequency=mhz, signal=strength))
    if not candidates:
        raise RuntimeError("No configured lab AP on the usable channel. Scan APs first; another channel needs a separate radio.")
    return max(candidates, key=lambda r: r["signal"]), connected


def decode_frame(packet):
    if len(packet) < 8 or packet[0] != 0:
        return None
    length = struct.unpack_from("<H", packet, 2)[0]
    if length < 8 or len(packet) < length + 24:
        return None
    frame = packet[length:]
    control = struct.unpack_from("<H", frame)[0]
    kind, subtype, ds = (control >> 2) & 3, (control >> 4) & 15, (control >> 8) & 3
    if kind not in (0, 2) or (kind == 2 and ds == 3):
        return None
    a1, a2, a3 = frame[4:10], frame[10:16], frame[16:22]
    bssid = a3 if kind == 0 or ds == 0 else a1 if ds == 1 else a2
    station = a2 if ds == 1 else a1 if ds == 2 else None
    return dict(kind=kind, subtype=subtype, bssid=bssid, destination=a1, source=a2,
                station=station, sequence=frame[22:24])


def management_frame(subtype, destination, source, bssid, sequence, body):
    return (b"\x00\x00\x08\x00\x00\x00\x00\x00" +
            struct.pack("<HH", subtype << 4, 0) + destination + source + bssid +
            struct.pack("<H", (sequence & 4095) << 4) + body)


def execute(action, profile):
    target, connected = target_for(profile)
    bssid = bytes.fromhex(target["bssid"].replace(":", ""))
    if action == "deauth":
        try:
            evidence = json.loads((STATE / "injection.json").read_text())
        except (OSError, ValueError):
            evidence = {}
        if (evidence.get("bssid") != target["bssid"] or evidence.get("interface") != profile["interface"]
                or evidence.get("frequency") != target["frequency"]
                or not 0 <= time.time() - evidence.get("time", 0) <= 600):
            raise RuntimeError("Run a successful injection check on this lab AP first (valid for 10 minutes)")
    if Path("/sys/class/net", MONITOR).exists():
        raise RuntimeError("qmmon already exists; inspect it before retrying")
    created, restore_management = False, False
    source = b"\x02" + secrets.token_bytes(5)
    try:
        # An idle USB adapter still scans under NetworkManager, which can prevent
        # channel tuning or move the monitor during a test. Never detach a connected
        # management radio. Restore ownership even when setup/capture fails.
        if not connected:
            managed = command("nmcli", "--get-values", "GENERAL.NM-MANAGED", "device", "show", profile["interface"]).strip()
            if managed == "yes":
                command("nmcli", "device", "set", profile["interface"], "managed", "no")
                restore_management = True
                command("ip", "link", "set", profile["interface"], "down")
        command("iw", "dev", profile["interface"], "interface", "add", MONITOR, "type", "monitor")
        created = True
        if action == "injection":
            command("ip", "link", "set", MONITOR, "address", source.hex(":"))
        command("ip", "link", "set", MONITOR, "up")
        if not connected:
            command("iw", "dev", MONITOR, "set", "freq", str(target["frequency"]))
        monitor_info = command("iw", "dev", MONITOR, "info")
        monitor_frequency = re.search(r"\((\d+) MHz\)", monitor_info)
        actual_frequency = int(monitor_frequency[1]) if monitor_frequency else None
        if action in ("injection", "deauth") and actual_frequency != target["frequency"]:
            raise RuntimeError("Monitor channel is not verified on the configured lab AP; transmission blocked")
        # A unique locally administered source makes replies attributable to this test,
        # rather than the managed interface's unrelated background probes.
        stats = dict(action=action, bssid=target["bssid"], frequency=target["frequency"],
                     interface=profile["interface"], monitor_frequency=actual_frequency,
                     received=0, decoded=0, frames=0, beacons=0, deauth_seen=0, stations=0, sent=0, probe_responses=0)
        stations, responses = set(), set()
        capture = bytearray(struct.pack('<IHHIIII',0xa1b2c3d4,2,4,0,0,4096,127))
        captured = 0
        with socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3)) as radio:
            radio.settimeout(0.1)
            radio.bind((MONITOR, 0))
            end = time.monotonic() + (8 if action in ("recon", "injection", "capture") else 2)
            next_send = 0
            while time.monotonic() < end:
                now = time.monotonic()
                if action == "injection" and stats["sent"] < 10 and now >= next_send:
                    ssid = profile["ssid"].encode()
                    rates = b"\x01\x08\x8c\x12\x98\x24\xb0\x48\x60\x6c" if target["frequency"] >= 4900 else b"\x01\x08\x82\x84\x8b\x96\x0c\x12\x18\x24\x32\x04\x30\x48\x60\x6c"
                    body = bytes([0, len(ssid)]) + ssid + rates
                    # Directed SSID discovery uses broadcast receiver/BSSID fields.
                    # Count only replies from the configured AP to this unique source.
                    frame = management_frame(4, b"\xff" * 6, source, b"\xff" * 6, stats["sent"], body)
                    if radio.send(frame) != len(frame):
                        raise RuntimeError("Incomplete probe transmission")
                    stats["sent"] += 1; next_send = now + 0.3
                elif action == "deauth" and stats["sent"] < 3 and now >= next_send:
                    frame = management_frame(12, b"\xff" * 6, bssid, bssid, stats["sent"], b"\x07\x00")
                    if radio.send(frame) != len(frame):
                        raise RuntimeError("Incomplete deauthentication transmission")
                    stats["sent"] += 1; next_send = now + 0.3
                try:
                    packet, sender = radio.recvfrom(65535 if action == 'capture' else 4096)
                except socket.timeout:
                    continue
                # AF_PACKET packet type 4 is local outgoing traffic, not RF reception.
                if sender[2] == socket.PACKET_OUTGOING:
                    continue
                stats["received"] += 1
                if action == 'capture' and len(capture)+min(len(packet),4096)+16 <= 524288 and captured < 2000:
                    timestamp = time.time_ns()
                    capture.extend(struct.pack('<IIII', timestamp//1_000_000_000, timestamp%1_000_000_000//1000, min(len(packet),4096), len(packet)))
                    capture.extend(packet[:4096]); captured += 1
                frame = decode_frame(packet)
                stats["decoded"] += frame is not None
                if not frame or frame["bssid"] != bssid:
                    continue
                stats["frames"] += 1
                if frame["kind"] == 0:
                    stats["beacons"] += frame["subtype"] == 8
                    stats["deauth_seen"] += frame["subtype"] == 12
                    if (action == "injection" and stats["sent"] and frame["subtype"] == 5
                            and frame["source"] == bssid and frame["destination"] == source and len(responses) < 64):
                        responses.add(frame["sequence"])
                station = frame["station"]
                if station and not station[0] & 1 and station != bssid and len(stations) < 256:
                    stations.add(station)
        stats.update(stations=len(stations), probe_responses=len(responses))
        if action == 'capture':
            stats.update(pcap=base64.b64encode(capture).decode('ascii'), captured=captured,
                         capture_limit_reached=captured < stats['received'], linktype=127)
        stats["capture_observed"] = stats["frames"] > 0
        stats["injection_observed"] = action == "injection" and bool(responses)
        if stats["injection_observed"]:
            STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
            (STATE / "injection.json").write_text(json.dumps({"bssid": target["bssid"],
                "interface": profile["interface"], "frequency": target["frequency"], "time": time.time()}))
        stats["note"] = ("Frames submitted; client disconnect not verified. PMF may prevent effects." if action == "deauth"
                         else "Directed responses received." if stats["injection_observed"]
                         else "No directed response; injection remains unverified." if action == "injection"
                         else "No receive packets returned by the monitor interface; capture is unverified." if not stats["received"]
                         else "Passive lab metadata only; no packet payloads stored.")
        if action == 'capture': stats['note'] = '8-second receive capture on the configured lab channel; nearby traffic may be included. No frames transmitted by this job. No channel hopping.'
        return stats
    finally:
        try:
            if created:
                command("iw", "dev", MONITOR, "del")
        finally:
            if restore_management:
                command("nmcli", "device", "set", profile["interface"], "managed", "yes")


def main():
    os.umask(0o077)
    if os.geteuid() != 0 or len(sys.argv) != 2 or sys.argv[1] not in ("status", "recon", "injection", "deauth", "capture", "--socket"):
        raise SystemExit("Use the installed helper with one fixed action")
    def stop(_signal, _frame):
        raise RuntimeError("Lab test interrupted")
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGALRM, stop)
    signal.alarm(35)
    try:
        action = socket_action(sys.stdin) if sys.argv[1] == "--socket" else sys.argv[1]
        profile = load_profile()
        if action == "status":
            result = dict(configured=True, interface=profile["interface"], target_count=len(profile["bssids"]), capture_supported=True)
        else:
            with exclusive_radio():
                result = execute(action, profile)
        print(json.dumps(result))
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(json.dumps({"error": str(exc)[:300]}))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
