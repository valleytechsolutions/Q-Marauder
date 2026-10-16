"""Stop only the preview process created from this exact source checkout."""
import os
from pathlib import Path
import signal
import sys
import time

root = Path(__file__).resolve().parents[1]
pidfile = Path.home() / ".local/share/q-marauder/preview.pid"
if not pidfile.exists():
    print("No preview PID file; nothing to stop")
    sys.exit(0)
pid = int(pidfile.read_text().strip())
proc = Path("/proc") / str(pid)
if not proc.exists():
    pidfile.unlink(missing_ok=True)
    print("Preview has already stopped")
    sys.exit(0)
args = (proc / "cmdline").read_bytes().split(b"\0")
record = pidfile.with_name('preview-root.txt')
recorded = Path(record.read_text()).resolve() if record.exists() else root
releases = (Path.home()/'.local/lib/q-marauder/releases').resolve()
allowed = recorded == root or (recorded.parent == releases and len(recorded.name)==16 and all(c in '0123456789abcdef' for c in recorded.name))
if b"-m" not in args or b"qmarauder" not in args or not allowed or (proc / "cwd").resolve() != recorded:
    raise SystemExit("PID no longer identifies this checkout's preview; refusing to signal it")
os.kill(pid, signal.SIGINT)
for _ in range(280):
    if not proc.exists() or (proc / "stat").read_text().split()[2] == "Z":
        print("Preview stopped; observations retained")
        pidfile.unlink(missing_ok=True)
        break
    time.sleep(0.25)
else:
    raise SystemExit("Preview is still stopping; inspect it before retrying")
