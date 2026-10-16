"""Build a source release using an allowlist; never bundle local survey data."""
import gzip
import hashlib
import io
from pathlib import Path
import tarfile
import zipfile

root = Path(__file__).resolve().parents[1]
allowed = ["qmarauder", "scripts", "firmware", "packaging", "docs", "licenses", "tests", "README.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "pyproject.toml", "Install-QMarauder.cmd", "Start-QMarauder.cmd"]
files = []
for name in allowed:
    path = root / name
    files.extend(path.rglob("*") if path.is_dir() else [path])
files = sorted(file for file in files if file.is_file() and "__pycache__" not in file.parts and file.suffix != ".pyc")
def payload(file):
    data = file.read_bytes()
    # Match the repository's LF text policy on both Windows and Linux builds.
    return data if file.suffix.lower() in (".png", ".jpg", ".webp") else data.replace(b"\r\n", b"\n")
out = root / "dist"
out.mkdir(exist_ok=True)
target = out / "q-marauder-0.1.0-source.tar.gz"
with target.open("wb") as raw:
    with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode="w") as tar:
            for file in files:
                relative = file.relative_to(root).as_posix()
                data = payload(file)
                entry = tarfile.TarInfo("q-marauder-0.1.0/" + relative)
                entry.size=len(data)
                entry.mode=0o755 if file.suffix == ".sh" else 0o644
                entry.mtime=0
                tar.addfile(entry, io.BytesIO(data))
zip_target = target.with_name("q-marauder-0.1.0-source.zip")
with zipfile.ZipFile(zip_target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for file in files:
        entry = zipfile.ZipInfo("q-marauder-0.1.0/" + file.relative_to(root).as_posix())
        entry.compress_type = zipfile.ZIP_DEFLATED
        entry.external_attr = (0o755 if file.suffix == ".sh" else 0o644) << 16
        archive.writestr(entry, payload(file))
checksums = []
for artifact in (target, zip_target):
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    checksums.append(f"{digest}  {artifact.name}\n")
    print(f"{artifact.name}: {len(files)} files; SHA256 {digest}")
(out / "SHA256SUMS").write_text("".join(checksums), encoding="ascii")
