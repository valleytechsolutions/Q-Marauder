# External USB radio support

## Observed development setup, 2026-10-15

The PC detects a USB device with vendor/product ID **0e8d:7961**. The Linux
`mt7921u` driver matches that ID. It is consistent with the MediaTek MT7921 family
used by ALFA AWUS036AXM/AXML products; the USB ID alone does not identify the exact
retail model. Windows currently reports driver errors for its Wi-Fi and Bluetooth
interfaces. The PC's existing network adapters remain connected.

The UNO Q runs kernel `6.16.0-geffa8626771a`. Its live `/proc/config.gz` reports:

| Option | Current build | Consequence |
| --- | --- | --- |
| `CONFIG_MT7921E=m` | PCIe driver | Does not drive the USB adapter |
| `CONFIG_MT7921U` | Disabled | Matching USB Wi-Fi driver missing |
| `CONFIG_USBIP_CORE` | Disabled | USB/IP forwarding unavailable |
| `CONFIG_USBIP_VHCI_HCD` | Disabled | No USB/IP client controller |

The board has no matching kernel build/header tree installed. This PC has neither
usbipd-win nor a usable WSL/Linux VM environment. Installing an ordinary Windows
Wi-Fi driver would not provide Linux monitor capture or make the dongle available
to the UNO Q. No USB forwarding or external-radio RF validation has succeeded yet.

## Connection paths

1. **Direct connection:** a USB-C hub with external power delivery connects the
   adapter to the UNO Q. The board still needs a matching `mt7921u` driver and
   firmware, and a working network management path before disconnecting PC USB.
2. **PC USB forwarding:** usbipd-win exports only the selected dongle; a Linux
   USB/IP client imports it. The UNO Q needs the USB/IP modules plus `mt7921u`.
   Windows installation/binding requires administrator access. This path remains
   PC-dependent and has not been validated by this project.
3. **Linux companion:** a separate Linux machine/VM owns the adapter and performs
   radio work. A scoped companion protocol would be needed to control it from the
   TFT; that backend is not implemented.

A matching kernel/module build must use the exact Arduino kernel source, config,
symbol versions and toolchain requirements. A random ARM64 Wi-Fi module is not a
compatible substitute. Keep the working stock image and recovery path until an
alternative build has been tested. No replacement kernel is included here.

## Read-only preflight

From Windows PowerShell in the source checkout:

```powershell
.\scripts\Check-UsbRadio.ps1
```

This prints USB hardware IDs and driver status, usbipd availability, and the board's
kernel support when the installed application is reachable over ADB. It omits USB
serial numbers, wireless identifiers and credentials. It changes no configuration.
On Debian, `q-marauder doctor` also includes the kernel support check.

After an adapter is actually available to Linux, validate discovery, passive receive
packets, channel selection and directed responses before claiming capture/injection
support. A tri-band specification alone proves none of those functions. Current lab
tests cover configured 2.4/5 GHz APs; 6 GHz active tests are not implemented.

Sources: [ALFA AWUS036AXML specifications](https://www.alfa.com.tw/products/awus036axml),
[Linux 6.16 mt7921u USB IDs](https://github.com/torvalds/linux/blob/v6.16/drivers/net/wireless/mediatek/mt76/mt7921/usb.c),
[usbipd-win setup](https://github.com/dorssel/usbipd-win), and
[Arduino USB peripheral setup](https://docs.arduino.cc/hardware/uno-q/).
