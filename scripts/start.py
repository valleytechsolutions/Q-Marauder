"""Start an unprivileged preview on a Linux board; systemd is preferred for boot."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

root = Path(__file__).resolve().parents[1]
installed = Path.home()/'.local/lib/q-marauder/current'
if (installed/'qmarauder/__main__.py').is_file(): root = installed.resolve()
data = Path.home() / ".local/share/q-marauder"
data.mkdir(parents=True, exist_ok=True, mode=0o700)
try:
    with urllib.request.urlopen("http://127.0.0.1:8787/api/state", timeout=2) as response:
        print("Q-Marauder is already serving on port 8787")
        sys.exit(0)
except OSError:
    pass
os.umask(0o077)
with (data / "console.log").open("ab") as log:
    process = subprocess.Popen([sys.executable, "-m", "qmarauder", "serve"], cwd=root,
                               stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                               start_new_session=True)
(data / "preview.pid").write_text(str(process.pid))
(data / 'preview-root.txt').write_text(str(root))
for _ in range(20):
    time.sleep(0.25)
    if process.poll() is not None:
        raise SystemExit(f"Startup failed; inspect {data / 'console.log'}")
    try:
        with urllib.request.urlopen("http://127.0.0.1:8787/api/state", timeout=1) as response:
            print("Q-Marauder ready on loopback port 8787")
            break
    except OSError:
        continue
else:
    raise SystemExit("Startup timed out; check console.log")
