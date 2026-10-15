"""Read a fresh TPV fix from a local gpsd without inventing a location."""
import datetime as dt
import json
import math
import socket
import time


def validate_fix(message: dict, now: dt.datetime | None = None) -> dict | None:
    try:
        if message.get("class") != "TPV" or int(message.get("mode", 0)) < 2:
            return None
        lat, lon = float(message["lat"]), float(message["lon"])
        if not math.isfinite(lat) or not math.isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
            return None
        timestamp = dt.datetime.fromisoformat(message["time"].replace("Z", "+00:00"))
        age = ((now or dt.datetime.now(dt.timezone.utc)) - timestamp).total_seconds()
        if not 0 <= age <= 15:
            return None
        return {"lat": lat, "lon": lon, "time": message["time"], "mode": int(message["mode"])}
    except (KeyError, TypeError, ValueError, OverflowError):
        return None


def read_fix() -> dict | None:
    try:
        with socket.create_connection(("127.0.0.1", 2947), timeout=0.6) as connection:
            connection.sendall(b'?WATCH={"enable":true,"json":true};\n')
            connection.settimeout(0.6)
            deadline, pending = time.monotonic() + 1.5, b""
            while time.monotonic() < deadline:
                try:
                    chunk = connection.recv(8192)
                except socket.timeout:
                    continue
                if not chunk:
                    break
                pending += chunk
                if len(pending) > 65536:
                    return None
                while b"\n" in pending:
                    line, pending = pending.split(b"\n", 1)
                    try:
                        value = json.loads(line)
                        fix = validate_fix(value) if isinstance(value, dict) else None
                        if fix:
                            return fix
                    except (ValueError, UnicodeError):
                        pass
    except OSError:
        pass
    return None
