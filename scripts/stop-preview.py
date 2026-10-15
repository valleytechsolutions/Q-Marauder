"""Stop only the preview process created from this exact source checkout."""
import os
from pathlib import Path
import signal
import time

root = Path(__file__).resolve().parents[1]
pidfile = Path.home() / ".local/share/q-marauder/preview.pid"
if not pidfile.exists():
    raise SystemExit("No preview PID file")
pid = int(pidfile.read_text().strip())
proc = Path("/proc") / str(pid)
if not proc.exists():
    raise SystemExit("Preview has already stopped")
args = (proc / "cmdline").read_bytes().split(b"\0")
if b"-m" not in args or b"qmarauder" not in args or (proc / "cwd").resolve() != root:
    raise SystemExit("PID no longer identifies this checkout's preview; refusing to signal it")
os.kill(pid, signal.SIGINT)
for _ in range(150):
    if not proc.exists() or (proc / "stat").read_text().split()[2] == "Z":
        print("Preview stopped; observations retained")
        break
    time.sleep(0.25)
else:
    raise SystemExit("Preview is still stopping; inspect it before retrying")
