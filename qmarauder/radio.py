"""Bounded, shell-free Linux adapters. Radio work never runs in HTTP threads."""
from __future__ import annotations
import os
import re
import shutil
import subprocess
import gzip
from pathlib import Path
from . import lab


def kernel_support():
    release = os.uname().release if hasattr(os, "uname") else "unknown"
    config, source = "", None
    for path in (Path("/proc/config.gz"), Path("/boot") / f"config-{release}"):
        try:
            config = gzip.decompress(path.read_bytes()).decode() if path.suffix == ".gz" else path.read_text()
            source = str(path)
            break
        except (OSError, ValueError, UnicodeError):
            continue
    options = {}
    for name in ("USBIP_CORE", "USBIP_VHCI_HCD", "MT7921U"):
        match = re.search(rf"^CONFIG_{name}=([ym])$", config, re.M)
        options[name] = match[1] if match else "disabled" if source else "unknown"
    modules = {}
    for name in ("usbip_core", "vhci_hcd", "mt7921u"):
        loaded = (Path("/sys/module") / name).is_dir()
        available = loaded
        if not available and shutil.which("modinfo"):
            try:
                result = subprocess.run(["modinfo", "-F", "filename", name], capture_output=True, timeout=3)
                available = result.returncode == 0
            except (OSError, subprocess.TimeoutExpired):
                pass
        modules[name] = dict(loaded=loaded, available=available)
    return dict(release=release, config_source=source, options=options, modules=modules)


def run(argv: list[str], timeout: int = 20) -> str:
    try:
        result = subprocess.run(argv, capture_output=True, text=True, errors="replace",
                                timeout=timeout, env={**os.environ, "LC_ALL": "C"})
    except FileNotFoundError as exc:
        raise RuntimeError(f"Required tool is missing: {argv[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"{Path(argv[0]).name} timed out") from exc
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or f"Exit {result.returncode}").strip()[:500])
    return result.stdout


def split_nmcli(line: str) -> list[str]:
    fields, field, escaped = [], [], False
    for char in line:
        if escaped:
            field.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == ":":
            fields.append("".join(field))
            field = []
        else:
            field.append(char)
    if escaped:
        field.append("\\")
    return fields + ["".join(field)]


def parse_wifi(output: str) -> list[dict]:
    networks = {}
    for line in output.splitlines():
        parts = split_nmcli(line)
        if len(parts) != 6:
            continue
        mac, ssid, channel, frequency, signal, security = parts
        if not re.fullmatch(r"(?:[\da-fA-F]{2}:){5}[\da-fA-F]{2}", mac):
            continue
        try:
            mhz = int(frequency.split()[0])
            row = dict(address=mac.upper(), name=ssid, channel=int(channel), frequency=mhz,
                       signal=max(0, min(100, int(signal))), security=security or "Open",
                       band="5 GHz" if 4900 <= mhz < 5925 else "2.4 GHz" if mhz < 2500 else "6 GHz",
                       kind="wifi")
        except (ValueError, IndexError):
            continue
        networks[row["address"]] = row
    return sorted(networks.values(), key=lambda row: row["signal"], reverse=True)


def wifi_scan(rescan: bool = True) -> list[dict]:
    return parse_wifi(run(["nmcli", "--terse", "--escape", "yes", "--fields",
                           "BSSID,SSID,CHAN,FREQ,SIGNAL,SECURITY", "device", "wifi", "list",
                           "--rescan", "yes" if rescan else "no"], timeout=30))


def parse_ble(output: str) -> list[dict]:
    devices = {}
    output = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", output)
    for line in output.splitlines():
        match = re.search(r"Device ((?:[\dA-Fa-f]{2}:){5}[\dA-Fa-f]{2}) (.*)", line)
        if not match:
            continue
        mac, value = match.groups()
        row = devices.setdefault(mac.upper(), dict(address=mac.upper(), name="", kind="ble", rssi=None))
        if value.startswith("RSSI:"):
            rssi = re.search(r"\((-?\d+)\)|RSSI:\s*(-?\d+)\s*$", value)
            if rssi:
                row["rssi"] = int(rssi.group(1) or rssi.group(2))
        elif value.startswith(("Name:", "Alias:")):
            row["name"] = value.split(":", 1)[1].strip()
        elif "[NEW]" in line and not value.startswith("(random)"):
            row["name"] = value.strip()
    return list(devices.values())


def ble_scan() -> list[dict]:
    # BlueZ releases this client's discovery session when bluetoothctl exits.
    output = run(["bluetoothctl", "--timeout", "8", "scan", "le"], timeout=13)
    if re.search(r"Failed|not available|not ready", output, re.I):
        raise RuntimeError(output.strip()[-500:])
    return parse_ble(output)


def diagnostics() -> dict:
    iw = shutil.which("iw")
    local_iw = Path.home() / ".cache/q-marauder/probe/usr/sbin/iw"
    if not iw and local_iw.exists():
        iw = str(local_iw)
    evidence = "iw is not installed; capability not measured"
    monitor = None
    if iw:
        try:
            evidence = run([iw, "phy"])
            monitor = bool(re.search(r"^\s*\* monitor\s*$", evidence, re.M))
        except RuntimeError as exc:
            evidence = str(exc)
    interfaces = []
    net = Path("/sys/class/net")
    if net.exists():
        for dev in net.iterdir():
            if (dev / "wireless").exists() or (dev / "phy80211").exists():
                driver = dev / "device/driver"
                interfaces.append(dict(name=dev.name, driver=driver.resolve().name if driver.exists() else "unknown"))
    effective = 0
    try:
        status = Path("/proc/self/status").read_text()
        effective = int(re.search(r"^CapEff:\s*([0-9a-fA-F]+)$", status, re.M)[1], 16)
    except (OSError, TypeError, ValueError):
        pass
    return dict(interfaces=interfaces, monitor_advertised=monitor, capture_verified=False, lab=lab.status(),
                privileges=dict(net_admin=bool(effective & (1 << 12)), net_raw=bool(effective & (1 << 13))),
                injection_verified=False, display_verified=False, tools={name: bool(shutil.which(name))
                for name in ("nmcli", "bluetoothctl", "gpsd", "tcpdump")},
                iw_evidence=evidence, kernel=kernel_support(), platform=os.uname().machine if hasattr(os, "uname") else os.name)
