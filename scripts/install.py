"""Install an immutable application revision; preserve observations and old revisions."""
import datetime as dt
import hashlib
from pathlib import Path
import os
import shutil
import sys

if sys.platform != "linux":
    raise SystemExit("Run this installer on the UNO Q's Debian system.")
if os.geteuid() == 0:
    raise SystemExit("Run as the normal board user, without sudo.")
root = Path(__file__).resolve().parents[1]
source = root / "qmarauder"
files = sorted(file for file in source.rglob("*") if file.is_file() and "__pycache__" not in file.parts)
hasher = hashlib.sha256()
for file in files:
    hasher.update(file.relative_to(source).as_posix().encode())
    hasher.update(file.read_bytes())
revision = hasher.hexdigest()[:16]
base = Path.home() / ".local/lib/q-marauder"
release = base / "releases" / revision
release.parent.mkdir(parents=True, exist_ok=True)
if not release.exists():
    temporary = release.with_name(revision + f".tmp-{os.getpid()}")
    temporary.mkdir()
    shutil.copytree(source, temporary / "qmarauder", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
        shutil.copy2(root / name, temporary / name)
    shutil.copytree(root / "licenses", temporary / "licenses")
    temporary.rename(release)
# Windows ADB transfers can mark every source file executable/world-writable.
# Normalize the installed tree instead of preserving those transfer permissions.
release.chmod(0o755)
for installed in release.rglob("*"):
    installed.chmod(0o755 if installed.is_dir() else 0o644)
link = base / f".current-{os.getpid()}"
link.symlink_to(release, target_is_directory=True)
link.replace(base / "current")
binary = Path.home() / ".local/bin/q-marauder"
binary.parent.mkdir(parents=True, exist_ok=True)
binary.write_text("#!/usr/bin/python3\nimport sys\nsys.path.insert(0, " + repr(str(base / "current")) + ")\nfrom qmarauder.__main__ import main\nmain()\n")
binary.chmod(0o755)
data = Path.home() / ".local/share/q-marauder"
data.mkdir(parents=True, exist_ok=True, mode=0o700)
print(f"Installed revision {revision}\nRun: {binary} serve\nData stays in: {data}\nPrevious revisions are retained in: {release.parent}")
print("For boot startup on the standard arduino account: sh scripts/enable-boot.sh (requires sudo).")
