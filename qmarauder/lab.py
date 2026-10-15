"""Unprivileged adapter to the separately installed lab helper."""
import json
from pathlib import Path
import subprocess
import socket

HELPER = Path("/usr/local/libexec/q-marauder-radio")
SOCKET = Path("/run/q-marauder-radio.sock")
ACTIONS = {"lab-recon": "recon", "lab-injection": "injection", "lab-deauth": "deauth"}


def call(action):
    if action not in ("status", "recon", "injection", "deauth"):
        raise ValueError("Unknown lab action")
    if SOCKET.exists():
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                connection.settimeout(45)
                connection.connect(str(SOCKET))
                connection.sendall((action + "\n").encode("ascii"))
                with connection.makefile("rb") as stream:
                    payload = stream.readline(16385)
            if len(payload) > 16384 or not payload.endswith(b"\n"):
                raise ValueError("Invalid helper response")
            report = json.loads(payload)
        except (OSError, ValueError) as exc:
            raise RuntimeError("Radio service unavailable or returned an invalid report") from exc
        if not isinstance(report, dict) or report.get("error"):
            raise RuntimeError(str(report.get("error", "Radio helper failed"))[:300] if isinstance(report, dict) else "Invalid helper report")
        return report
    if not HELPER.is_file():
        raise RuntimeError("One-time admin radio setup is required; see docs/LAB.md")
    try:
        result = subprocess.run(["sudo", "-n", "--", str(HELPER), action], capture_output=True,
                                text=True, timeout=45, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("Lab helper unavailable or timed out") from exc
    try:
        report = json.loads(result.stdout)
    except ValueError as exc:
        raise RuntimeError("Radio helper permission is not configured; see docs/LAB.md") from exc
    if result.returncode or not isinstance(report, dict) or report.get("error"):
        raise RuntimeError(str(report.get("error", "Radio helper failed"))[:300] if isinstance(report, dict) else "Invalid helper report")
    return report


def status():
    try:
        return call("status")
    except RuntimeError as exc:
        return dict(configured=False, reason=str(exc))
