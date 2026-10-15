"""Build a source release using an allowlist; never bundle local survey data."""
import gzip
import hashlib
import io
from pathlib import Path
import tarfile

root = Path(__file__).resolve().parents[1]
allowed = ["qmarauder", "scripts", "firmware", "packaging", "docs", "licenses", "tests", "README.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "pyproject.toml"]
files = []
for name in allowed:
    path = root / name
    files.extend(path.rglob("*") if path.is_dir() else [path])
files = sorted(file for file in files if file.is_file() and "__pycache__" not in file.parts and file.suffix != ".pyc")
out = root / "dist"
out.mkdir(exist_ok=True)
target = out / "q-marauder-0.1.0-source.tar.gz"
with target.open("wb") as raw:
    with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode="w") as tar:
            for file in files:
                relative = file.relative_to(root).as_posix()
                data = file.read_bytes()
                entry = tarfile.TarInfo("q-marauder-0.1.0/" + relative)
                entry.size=len(data)
                entry.mode=0o755 if file.suffix == ".sh" else 0o644
                entry.mtime=0
                tar.addfile(entry, io.BytesIO(data))
digest=hashlib.sha256(target.read_bytes()).hexdigest()
(out / "SHA256SUMS").write_text(f"{digest}  {target.name}\n", encoding="ascii")
print(f"{target.name}: {len(files)} files; SHA256 {digest}")
