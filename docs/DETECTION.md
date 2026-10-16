# Packet detection and BLE capture

Q-Marauder now has independent packet decoders and executable receive jobs for
Flock candidates, Remote ID and BLE advertisements. These are bounded tools, not
a claim of complete Unified Blue parity or confirmed surveillance identity.

## Install once, then use the screen

1. Install the current application **and TFT sketch** with `Install-QMarauder.cmd`.
2. Run `scripts/Enable-BLELab.cmd` for Debian's D-Bus bindings.
3. Run `scripts/Enable-LabRadio.cmd`. Choose **1** for BLE capture and helper updates.
   This retains an existing Wi-Fi profile; none is required for BLE capture.
4. For Wi-Fi capture, attach a supported monitor radio and run that launcher again,
   choosing **2**. Select the radio and your owned/authorized AP in the interactive
   list. The profile stays private on the board. Enter the Debian password locally.
5. Open **Counter surveillance** on the portrait TFT, or **Lab → Detection modes**
   in the browser. Tap the mode once and wait for the bounded receive window.

| Portrait selection | What it actually receives and analyzes |
| --- | --- |
| Packet detector | Individual HCI reports: Meta company + FD5F in the same report; Axon and Flock identifiers |
| Flock BLE | Flock-associated public OUI, accessory service, and specific name patterns; generic XUNTONG company alone does not match |
| Flock Wi-Fi | Flock Safety registered transmitter OUI B4:1E:52 in management frames; generic Qualcomm OUIs are not classified as Flock |
| AXEOFF Wi-Fi | Axon Enterprise transmitter OUI 00:25:DF in management frames; candidate evidence only |
| Sky Spy BLE | FFFA Remote ID service data in complete legacy or extended advertising reports |
| Sky Spy Wi-Fi | OpenDroneID beacon vendor elements and NAN service descriptors |
| BLE Sniff PCAP | Received HCI advertising events, device summaries and a downloadable PCAP |
| Wi-Fi PCAP | Eight-second radiotap capture on the configured lab AP channel |

Tap a result for details; use PREV/NEXT for further pages. Capture count, report
count, receiver coverage and truncation limits appear even if there are **zero
matches**. Remote ID pages show ID, location, movement, operator/system and
authentication fields. The newest packet report survives an application restart;
opening the screen does not repeat the job. Download **PCAP** and **JSON** from
the browser's Packet analysis panel or **Field log**.

<img src="images/packet-detection.png" width="780" alt="Actual desktop detector workspace with Flock, Sky Spy and BLE capture controls and a completed 46-report capture with zero matches">

*Actual browser workspace, not a photograph of the TFT. This run received 46
advertising reports and found zero detector matches.*

## Coverage and evidence

BLE capture opens a receive-only HCI socket before starting an eight-second BlueZ
discovery window. The socket closes after twelve seconds. BlueZ may transmit scan
requests. Only LE legacy/extended advertising events are stored; connection traffic,
keys, ACL data and other controller events are excluded. The PCAP uses **linktype
201 (Bluetooth HCI H4 with direction header)**, which Wireshark can decode. It is
not linktype 256, a channel-37/38/39 air sniffer, or a decoder of arbitrary nearby
BLE connections. Incomplete extended fragments remain in the PCAP but do not create
matches. Extended fragment reassembly is pending.

The Wi-Fi detector jobs use twelve one-second receive windows over channels
**1/6/11** on an idle adapter. A connected adapter stays on its existing channel;
the job never retunes or disconnects a connected management radio. These jobs store
management frames only and restore NetworkManager ownership after normal completion
or handled errors. Channels outside this set, rolling logging and radio duty-cycle
parity are not implemented. The standalone Wi-Fi PCAP action retains its original
single-lab-channel behavior.

Each PCAP is limited to **512 KiB / 2,000 packets**. Analyses retain up to 256
candidate/message keys and 200 advertiser summaries. Full captured payloads are
in the private PCAP; screen summaries are bounded. Short windows and storage limits
can miss devices. No match does not establish absence.

Flock detections are candidate evidence. Public OUIs can be spoofed; company IDs
often identify a module supplier. The broad community Wi-Fi IE fingerprint database
has not been imported or independently validated. This mode is deliberately narrower
than Unified Blue's Flock-You coverage.

Sky Spy decodes Basic ID, Location, Authentication, Self ID, System, Operator ID and
message packs. Supported protocol versions are 1 and 2. Authentication bytes are
displayed but **signatures are not verified**. Location is an unverified broadcast
claim, not an independently measured aircraft position. Unknown position/speed/altitude
values are represented explicitly rather than invented.

## Measured status, 2026-10-16

Real UNO Q BLE capture runs saved 44–49 HCI advertising reports per window, with zero
malformed or incomplete reports in those runs. Flock BLE, Sky Spy BLE and Packet
detector completed and exported captures. No Flock or Remote ID signature was observed
in those windows. Decoder fixtures cover known positives, negatives, packet boundaries,
malformed input and all six Remote ID message families. This is **not field validation
against a real Flock device or drone**.

The external Alfa previously passed single-channel monitor reception. During this
release's validation it stopped enumerating on Windows and was unavailable to the
UNO Q. The new Wi-Fi channel-sampling jobs pass automated cleanup/channel tests but
still need a live adapter test. The stock ath10k_snoc radio previously returned zero
monitor packets. Do not treat a successful compile as verified RF operation.

## Protocol references and fixture reproduction

Implementations are independent Python code. No Unified Blue implementation or
signature table is bundled. References:

- [Unified Blue mode descriptions](https://github.com/colonelpanichacks/oui-spy-unified-blue)
- [OpenDroneID protocol structures and reference encoder](https://github.com/opendroneid/opendroneid-core-c/tree/master/libopendroneid)
- [OpenDroneID BLE transport framing](https://github.com/opendroneid/transmitter-linux/blob/master/bluetooth.c)
- [BlueZ HCI definitions](https://github.com/bluez/bluez/blob/master/lib/bluetooth/hci.h)
- [PCAP link type registry draft](https://www.ietf.org/archive/id/draft-ietf-opsawg-pcaplinktype-13.html)

`tests/fixtures/remote_id.txt` contains synthetic messages generated by our
`tests/reference_odid.c` through the Apache-2.0 OpenDroneID C encoder. Nothing was
transmitted. The exact reference files used were `src/opendroneid.c` and
`src/opendroneid.h` from Unified Blue commit
`6e5e2829540925ff1ab5fa6d0d365378818ed56e`, retaining their individual Apache notices
in the separate reference checkout. SHA-256 hashes:

```
opendroneid.c 3a65a19075129ff61eb26cea37adaadc17e7911aa5e09a3722c704fb0d355b74
opendroneid.h da6f25a2c6a76302437c43d9ba01a72216038f5c2562cbbaa9073b46d7ddee0d
```

With those files in a temporary directory, reproduce on Linux:

```sh
gcc -I /path/to/reference tests/reference_odid.c /path/to/reference/opendroneid.c -lm -o /tmp/qm-odid-fixture
/tmp/qm-odid-fixture
python3 -m unittest discover -s tests -q
```

Captures and reports can contain nearby identifiers and precise broadcast positions.
They are local by default and excluded from release packages. Review any export
before publishing it.
