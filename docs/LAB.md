# Lab radio setup and current limits

Wi-Fi AP discovery and BLE discovery work through NetworkManager and BlueZ without
root. The native TFT now shows paginated results, signal values and device details.
The separate lab helper implements **passive packet metadata**, a **10-probe directed
injection check**, and a **3-frame deauthentication test**. These backends have automated
tests. The stock onboard radio returned **zero monitor packets and no directed
responses**. The PC-forwarded Alfa provides **verified monitor reception on
2.4/5 GHz**; injection remains unverified. These are not full Marauder
attack parity. Other unported menu entries remain marked planned.

## One-time Debian admin setup

Create a local JSON profile containing the exact interface, SSID and authorized AP
BSSIDs from a scan. Do not commit the profile or real identifiers. Example:

```json
{"interface":"wlan0","ssid":"YOUR LAB SSID","bssids":["02:11:22:33:44:55"]}
```

Review `qmarauder/lab_helper.py` and `scripts/install-radio-helper.py`, then run on
the UNO Q:

```sh
sudo python3 scripts/install-radio-helper.py --profile /path/to/local-lab-profile.json
```

This installs Debian's `iw`, `iproute2` and `sudo` packages if needed; copies a
standalone helper to `/usr/local/libexec/q-marauder-radio`; stores a root-owned
profile at `/etc/q-marauder/lab.json`; and grants the chosen normal account (default
`arduino`) passwordless access to four **exact helper commands** through
`/etc/sudoers.d/q-marauder-radio`. It does not grant arbitrary sudo access or run a
radio test during installation. The application itself remains unprivileged.

The installer also enables `q-marauder-radio.socket`. Its local Unix socket is
accessible to the selected account's primary group. Each connection starts a
separate, time-limited root helper that accepts only one of the four fixed actions.
The UI prefers this socket, so its boot unit can retain `NoNewPrivileges=true` and
an empty capability set. The root worker has only `NET_ADMIN` and `NET_RAW`, a
read-only system and a private state directory. A process lock prevents concurrent
radio jobs, including jobs started through the legacy sudo entry point.

The installer validates its sudoers file with `visudo` before activating it. It
does not enable the application's boot service. Removing the dedicated sudoers
file disables the legacy sudo entry point. To disable all access, also stop/disable
`q-marauder-radio.socket` and stop any active `q-marauder-radio@*.service` workers.

## Physical menu workflow

1. **WiFi → Scan APs**: collect a fresh list. Tap any result for its address,
   security and signal details. Signal is NetworkManager quality percent, not dBm.
2. **WiFi → Attacks → Test readiness**: inspect discovery, monitor advertisement,
   process privileges and helper setup.
3. **WiFi → Sniffers → Lab packet recon**: listen for eight seconds, counting
   configured lab frames, beacons, deauthentication frames and observed clients.
   No packet payloads or captures are saved by this helper.
4. **WiFi → Attacks → Injection check**: send at most ten probes naming the configured
   lab SSID, with standard broadcast receiver/BSSID fields. Only replies from the
   selected allowlisted AP count. A unique test source address and received AP responses
   distinguish radio reception from local transmit echoes. No response means
   inconclusive, not proof that every form of injection is unsupported.
5. **WiFi → Attacks → Lab deauth (3 frames)**: send three deauthentication frames
   only after a successful injection check on the same interface, AP and frequency
   within ten minutes. This can interrupt clients on that lab AP. A driver accepting
   frames is not proof of client disconnection; PMF may prevent the effect.

Transmit jobs also require the monitor interface to report the configured AP's
frequency. Missing or mismatched channel information blocks transmission.
The browser's **System → Lab radio tests** provides the same bounded actions.

The helper uses a temporary `qmmon` monitor interface and removes it after each job,
including errors. For a disconnected external adapter it temporarily releases that
device from NetworkManager and restores ownership afterward, preventing background
scans from retuning it. It does not stop NetworkManager or disconnect a connected
management interface. While that interface is connected, it only selects a configured AP on
the existing channel. Testing a different channel can require a separate radio.
An existing `qmmon` is treated as a conflict, never deleted automatically.

Every command has a timeout and each helper run has a 35-second watchdog. If a
hard system/process crash interrupts cleanup, inspect a leftover `qmmon` before
retrying. The UI serializes radio jobs. These short jobs terminate automatically;
interactive cancellation and packet capture/export are not implemented yet.
Completed and failed jobs are saved as lab sessions, with CSV/JSON report exports.
The latest report returns after an application restart. An interrupted job is shown
as an unknown outcome and is never silently resumed. This is local operational
history, not a tamper-resistant audit log.

## Validation status

- AP/BLE discovery: exercised on the development board.
- Native Wi-Fi results and details: owner confirmed on the physical TFT. BLE uses
  the same result renderer; its physical acceptance is still pending.
- Lab target validation, framing, cleanup, transmission bounds and evidence gate:
  automated fixtures pass.
- Admin setup and local fixed-action socket: installed and exercised.
- Stock `ath10k_snoc` monitor tests returned zero receive packets, including an
  isolated test with the managed connection disabled and channel tuning accepted.
- A directed probe check submitted ten frames but received no responses. Submission
  is not evidence of RF transmission. No deauthentication test was transmitted.
- External MT7921 USB radio: forwarding, AP scans and lab monitor reception verified.
  Ten-probe checks on 2.4/5 GHz and an independent Aircrack-ng check received no
  matching injection replies. Actual client-disconnect behavior remains unverified;
  no deauth test was transmitted. See [USB radio support](USB-RADIO.md).
- BLE attack families, portals, arbitrary frame attacks and full upstream parity:
  not implemented. Wardriving work is deferred.

References: [Linux wireless monitor interfaces](https://wireless.docs.kernel.org/en/latest/en/users/documentation/iw.html),
[Aircrack-ng injection-test interpretation](https://www.aircrack-ng.org/doku.php?id=injection_test),
and [deauthentication behavior](https://www.aircrack-ng.org/doku.php?id=deauthentication).

## Receive-only PCAP capture

Update the helper by running **scripts/Enable-LabRadio.cmd** after upgrading the
application; it uses the previously prepared local lab profile. If that file is
no longer present, upgrade from the board with
`sudo python3 scripts/install-radio-helper.py --profile /etc/q-marauder/lab.json`
to retain the existing root-owned profile. Use **Lab → Wi-Fi PCAP**, or **Counter surveillance → WiFi PCAP** on
the portrait TFT. It receives for eight seconds on the configured lab channel,
with a 512 KiB / 2000-packet storage limit; the capture action sends no packets.
It may include nearby traffic on that channel, not only the configured AP.
Download the session's **PCAP** from Field log; the file uses radiotap linktype 127.
A live run captured 321 packets, and all PCAP record lengths/radiotap headers
were checked in the 134,530-byte export. Rolling captures and channel hopping
remain unimplemented. Storage is bounded per capture; periodically manage old
records and files on the board.
