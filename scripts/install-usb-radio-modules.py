"""Install the exact-kernel module build, preserving the original kernel modules."""
import os
from pathlib import Path
import shutil
import subprocess

def main():
    release = os.uname().release
    if os.geteuid() != 0 or release != "6.16.0-geffa8626771a":
        raise SystemExit("Use sudo on the validated UNO Q factory kernel only.")
    source = Path("/home/arduino/.cache/qm-radio-build/source")
    modules = sorted((source / "drivers/usb/usbip").rglob("*.ko")) + sorted((source / "drivers/net/wireless/mediatek/mt76").rglob("*.ko"))
    expected = {"usbip-core.ko", "vhci-hcd.ko", "mt76.ko", "mt76-usb.ko", "mt76-connac-lib.ko", "mt792x-lib.ko", "mt792x-usb.ko", "mt7921-common.ko", "mt7921e.ko", "mt7921u.ko"}
    if len(modules) != 10 or {m.name for m in modules} != expected:
        raise SystemExit("Build all modules with build-usb-radio.py first.")
    reference = subprocess.check_output(["modinfo", "-F", "vermagic", "ath10k_core"], text=True).strip()
    for module in modules:
        if subprocess.check_output(["modinfo", "-F", "vermagic", str(module)], text=True).strip() != reference:
            raise SystemExit(f"Kernel vermagic mismatch: {module.name}")
    if Path("/sys/module/mt76").exists():
        raise SystemExit("An mt76 module is already loaded. Detach the Alfa and unload unused mt7921 modules before updating; do not force-unload a live radio.")
    dest = Path("/lib/modules") / release / "updates/q-marauder"
    dest.mkdir(parents=True, exist_ok=True)
    for module in modules:
        temporary = dest / (module.name + ".new")
        shutil.copyfile(module, temporary)
        temporary.chmod(0o644)
        temporary.replace(dest / module.name)
    subprocess.run(["depmod", "-a", release], check=True)
    option = Path('/etc/modprobe.d/q-marauder-usb.conf')
    option.write_text('options mt76_usb disable_usb_sg=1\n')
    option.chmod(0o644)
    for name in ("vhci_hcd", "mt7921u"):
        subprocess.run(["modprobe", name], check=True)
    print("Modules installed and loaded. Original kernel files are retained. See docs/USB-RADIO.md to attach the Alfa.")

if __name__ == "__main__":
    main()
