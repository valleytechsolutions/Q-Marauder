"""Build only USB/IP and MT7921 modules for the validated Arduino factory kernel."""
import gzip
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import urllib.request

KERNEL = "6.16.0-geffa8626771a"
COMMIT = "effa8626771ad31536aafd3a5aa94cad7e528e23"
DIGEST = "148030b6653c790850bb6438a30925433418df2a7a4314fa84a6c2ac5a65caf0"

def main():
    if os.name != "posix" or os.uname().release != KERNEL or os.geteuid() == 0:
        raise SystemExit(f"Run without sudo on the UNO Q using kernel {KERNEL}; other kernels are not supported.")
    if Path.home() != Path("/home/arduino"):
        raise SystemExit("This alpha build recipe targets the standard arduino account.")
    model = Path("/proc/device-tree/model").read_text()
    if "Arduino" not in model or "Imola" not in model:
        raise SystemExit("Expected an Arduino UNO Q")
    config = gzip.decompress(Path("/proc/config.gz").read_bytes()).decode()
    if "# CONFIG_MODVERSIONS is not set" not in config or "CONFIG_GCC_VERSION=130300" not in config:
        raise SystemExit("Unexpected kernel ABI/toolchain configuration; refusing this recipe.")
    base = Path.home() / ".cache/qm-radio-build"
    base.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(base).free < 800 * 1024**2:
        raise SystemExit("At least 800 MiB free space is required for the selective source build.")
    subprocess.run(["sudo", "apt-get", "update"], check=True)
    subprocess.run(["sudo", "apt-get", "install", "-y", "--no-install-recommends", "gcc-13", "make", "bc", "flex", "bison", "libelf-dev", "libssl-dev", "usbip", "firmware-mediatek", "iptables"], check=True)
    archive = base / "linux.tar.gz"
    def digest(path):
        with path.open("rb") as stream:
            return hashlib.file_digest(stream, "sha256").hexdigest()
    if not archive.exists() or digest(archive) != DIGEST:
        print("Downloading pinned Arduino kernel source (about 241 MiB).", flush=True)
        temporary = archive.with_suffix(".download")
        with urllib.request.urlopen(f"https://codeload.github.com/arduino/linux-qcom/tar.gz/{COMMIT}", timeout=60) as response, temporary.open("wb") as output:
            shutil.copyfileobj(response, output)
        if digest(temporary) != DIGEST:
            raise SystemExit("Kernel source checksum mismatch; nothing will be compiled or installed.")
        temporary.replace(archive)
    dest = base / "source"
    dest.mkdir(exist_ok=True)
    prefixes = ("include/", "scripts/", "arch/arm64/", "kernel/", "certs/", "lib/",
                "drivers/usb/usbip/", "drivers/net/wireless/mediatek/mt76/",
                "tools/include/", "tools/build/", "tools/scripts/", "arch/x86/entry/syscalls/")
    print("Extracting build inputs; compiling may take several minutes.", flush=True)
    with tarfile.open(archive) as tar:
        for member in tar:
            parts = member.name.split("/", 1)
            if len(parts) != 2 or not parts[1]:
                continue
            name = parts[1]
            if "/" not in name or name.startswith(prefixes) or name.rsplit("/", 1)[-1].startswith(("Kconfig", "Makefile", "Kbuild")):
                member.name = name
                tar.extract(member, dest, filter="data")
    (dest / ".config").write_text(config)
    subprocess.run(["scripts/config", "--disable", "LOCALVERSION_AUTO", "--set-str", "LOCALVERSION", "-geffa8626771a", "--module", "USBIP_CORE", "--module", "USBIP_VHCI_HCD", "--module", "MT7921U"], cwd=dest, check=True)
    make = ["make", "-j2", "CC=gcc-13", "HOSTCC=gcc-13"]
    subprocess.run([*make, "olddefconfig"], cwd=dest, check=True)
    version = subprocess.check_output(["make", "-s", "CC=gcc-13", "kernelrelease"], cwd=dest, text=True).strip()
    if version != KERNEL:
        raise SystemExit("Generated kernel release does not match the running kernel.")
    subprocess.run([*make, "modules_prepare"], cwd=dest, check=True)
    # This exact factory config has MODVERSIONS disabled and no supplied symvers.
    # Kernel exports are checked by modprobe at load; internal dependencies are built together.
    for part in ("drivers/usb/usbip", "drivers/net/wireless/mediatek/mt76"):
        subprocess.run([*make, "KBUILD_MODPOST_WARN=1", "M=" + part, "modules"], cwd=dest, check=True)
    print("Build complete. Install with: sudo python3 scripts/install-usb-radio-modules.py")

if __name__ == "__main__":
    main()
