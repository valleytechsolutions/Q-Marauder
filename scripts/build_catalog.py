"""Generate the versioned compatibility inventory from explicit port decisions."""
import json
from pathlib import Path

entries = []


def add(category, status, names, detail):
    for name, slug in names:
        entries.append(dict(id=slug, name=name, category=category, status=status, detail=detail,
                            source=f"https://github.com/justcallmekoko/ESP32Marauder/wiki/{slug}"))


add("Wi-Fi", "implemented", [("Access point survey", "scan-aps"), ("AP details", "view-ap-info")],
    "NetworkManager scan with SSID, BSSID, band, channel, security, and signal quality. No station capture.")
add("Wi-Fi", "partial", [("Channel analyzer", "channel-analyzer"), ("Signal monitor", "signal-monitor")],
    "AP counts by channel and signal quality snapshots. Packet utilization and continuous target tracking are pending.")
add("Bluetooth", "partial", [("BLE discovery", "bluetooth-sniffer")],
    "BlueZ discovery with fresh names/RSSI, address type, service UUIDs, manufacturer/service data and small independent fingerprints. Aggregated properties, not raw packets.")
add("Field collection", "partial", [("Wardrive", "wardrive"), ("Recon missions", "recon")],
    "Durable repeated Wi-Fi surveys, fresh gpsd fixes, and CSV/JSON export. BLE missions, WiGLE, GPX, and geofences remain.")
add("Wi-Fi capture", "planned", [("Station scan", "scan-stations"), ("Combined AP/station scan", "scan-all"),
    ("Probe request capture", "probe-request-sniff"), ("Beacon capture", "beacon-sniff"), ("Raw PCAP capture", "raw-sniff"),
    ("Deauthentication detection", "deauth-sniff"), ("EAPOL / PMKID capture", "eapol-pmkid-scan"),
    ("Packet counter", "packet-count"), ("Packet monitor", "packet-monitor"), ("SAE commit capture", "sniffsae")],
    "Requires a validated monitor interface and capture backend. Driver advertises monitor mode; on-air capture is unverified.")
add("Tracking", "planned", [("Fox hunt", "fox-hunt"), ("Pwnagotchi detection", "detect-pwnagotchi"),
    ("Remote ID aircraft detection", "remote-id"), ("CSI motion monitor", "csi-motion-monitor")],
    "Needs packet/advertisement decoding and recorded validation fixtures. CSI additionally depends on driver telemetry.")
add("Network testing", "planned", [("Ping scan", "ping-scan"), ("ARP scan", "arp-scan"),
    ("Port scan", "port-scan"), ("SSH discovery", "ssh-scan"), ("Telnet discovery", "telnet-scan")],
    "Linux backend pending; use an explicit owned/authorized network scope and bounded jobs.")
add("Active Wi-Fi tests", "planned", [("Beacon list test", "beacon-spam-list"), ("Random beacon test", "beacon-spam-random"),
    ("Rick Roll beacon", "rick-roll-beacon"), ("Probe request flood", "probe-request-flood"),
    ("Deauthentication test", "deauth-flood"), ("AP clone test", "ap-clone-spam"),
    ("Bad Message", "bad-msg"), ("Association sleep test", "association-sleep-attack"),
    ("SAE commit flood", "sae-commit-flood"), ("Channel switch test", "channel-switch"), ("Quiet Time", "quiet-time")],
    "Not implemented. Raw transmission needs separate driver/firmware validation, explicit target scope, duration limits, and a stop control.")
add("Access point testing", "planned", [("Evil Portal", "evilportal"), ("Karma", "karma")],
    "Not implemented. Requires an isolated AP/network backend and separation from the management connection.")
add("Bluetooth analysis", "planned", [("Bluetooth analyzer", "bluetooth-analyzer"), ("BLE wardrive", "bluetooth-wardrive"),
    ("Flipper detection", "flipper-sniff"), ("AirTag discovery", "airtag-sniff"), ("AirTag monitor", "airtag-monitor"),
    ("iBeacon analysis", "ibeacon-sniff"), ("Card skimmer heuristics", "detect-card-skimmers"),
    ("Flock heuristics", "flock-sniff"), ("Flock wardrive", "flock-wardrive"), ("Meta device heuristics", "meta-detect")],
    "Needs manufacturer/service-data decoding and fixture-tested signatures. Advertisements alone cannot prove device identity.")
add("Active BLE tests", "planned", [("Sour Apple", "sour-apple"), ("Swift Pair advertisements", "swiftpair-spam"),
    ("Samsung advertisements", "samsung-ble-spam"), ("Flipper advertisements", "flipper-ble-spam"),
    ("Combined BLE tests", "bt-spam-all"), ("AirTag emulation", "spoof-airtag"), ("Find My sound", "findmy-sound")],
    "Not implemented. BlueZ advertising support does not establish ESP32 payload/behavior parity.")
add("GPS", "partial", [("GPS fix", "gps-data")],
    "Reads fresh 2D/3D TPV fixes from local gpsd. Physical receiver not yet connected or validated.")
add("GPS", "planned", [("NMEA stream", "nmea-stream"), ("GPX tracker / POI", "gps-tracker"), ("Survey geofences", "wardrive-geofences")],
    "Requires receiver bring-up and route/geofence implementation.")
add("Management", "planned", [("Target selection", "select-aps"), ("Station selection", "select-stations"),
    ("SSID lists", "add-ssid"), ("SSID generation", "generate-ssids"), ("Clear SSIDs", "clear-ssids"),
    ("Clear APs", "clear-aps"), ("MAC configuration", "set-macs"), ("Wi-Fi profiles", "join"),
    ("Portal file selection", "select-ep-html-file"), ("Direct upload", "direct-upload")],
    "Port pending. Existing NetworkManager profiles are not changed by this alpha.")
add("Device", "partial", [("Device information", "device-info"), ("CLI", "cli"), ("Update / installation", "update-firmware"),
    ("File archive", "sd-file-browser")],
    "Diagnostics, local CLI, source installer, and session exports exist. Signed image updates and general file management are pending.")
add("Device", "planned", [("Settings", "settings"), ("Backup / restore", "spiffs-backup-and-restore"),
    ("Touch UI / brightness", "menu-navigation"), ("Flipper companion", "flipper-zero")],
    "Requires Linux-specific storage/interface mapping and validated display hardware; ESP32 partitions are not portable.")
for name in ("Dragon Detector", "Axeoff", "Squachwach"):
    entries.append(dict(id=name.lower().replace(" ", "-"),name=name,category="Future detectors",status="planned",
                        detail="Integration slot reserved. Original repository, license, protocol, and test data are needed.",source=None))
root = Path(__file__).resolve().parents[1]
for entry in entries:
    if entry["id"] in ("packet-count", "deauth-sniff", "scan-stations"):
        entry.update(status="partial", detail="Optional lab helper counts configured-AP frames, deauth frames and observed clients. External MT7921 monitor reception verified on 2.4/5 GHz; stock onboard monitor tests returned zero packets. No general station inventory or PCAP export.")
    elif entry["id"] == "deauth-flood":
        entry.update(status="partial", detail="Bounded 3-frame lab test implemented behind a configured AP allowlist and recent directed-probe response gate. Not a flood; RF injection and client effect remain unvalidated on UNO Q.")
    elif entry["id"] in ("settings", "menu-navigation"):
        entry.update(status="partial", detail="Settings contains four artwork themes shared by browser and portrait TFT, BLE target/adapter selection and watchlists. Direct touch and saved calibration work. Brightness control is pending.")
for slug,name,status,detail in [
    ('ble-gatt','GATT inspection / read / write / notify','partial','Bounded BlueZ jobs for one selected target; refuses foreign connections and disconnects its own. Inventory, characteristic reads/writes and 10-second notifications implemented; physical GATT validation pending.'),
    ('ble-foxhunt','BLE signal tracking','partial','20-second selected-address RSSI samples, peak and trend; no distance estimate. Continuous audio tracking remains.'),
    ('ble-hid','HID report decoding','planned','HID service classification exists; report-map parsing and live input decoding are not implemented.'),
    ('ble-security','Pairing and bond management','planned','Interactive pairing agent and per-target bond management pending; no automatic bond removal.'),
    ('ble-emulate','GATT cloning / emulation / proxy','planned','Needs independently implemented peripheral services, controller validation and authorized host tests. No cloning, MAC spoofing or MITM backend is present.')]:
    entries.append(dict(id=slug,name=name,category='BLE Lab',status=status,detail=detail,source='https://github.com/MatthewKuKanich/ChimeraBLE'))
for slug,name,status,detail in [
    ('watchlist','BLE watchlist detector','partial','Configurable exact address, public OUI, company ID, service UUID and name matches. Native/browser result pages and JSON history. No verified surveillance classification; no same-packet composite matching.'),
    ('unified-foxhunter','Unified Blue Foxhunter parity','partial','Bounded selected-address BLE signal tracking. Continuous audio/LED behavior is not implemented.'),
    ('unified-flock','Flock-You mode','planned','Wi-Fi IE/probe fingerprints, passive BLE signatures, duty cycling and persisted detector sessions pending.'),
    ('unified-pcap','Unified Blue Wi-Fi PCAP mode','planned','Rolling PCAP export and general channel hopping pending. Existing lab packet counters are a separate bounded tool.'),
    ('unified-skyspy','Sky Spy Remote ID','planned','Raw Wi-Fi capture integration, ASTM F3411 decoder and reference telemetry fixtures needed.'),
    ('unified-blesniff','BLE advertising PCAP','planned','BlueZ aggregated discovery is not passive raw advertising capture; HCI report capture and correct PCAP framing needed.'),
    ('unified-axeoff','AXEOFF mode','planned','Combined BLE/Wi-Fi signatures, continuous headless operation and audio alerts pending.')]:
    entries.append(dict(id=slug,name=name,category='Unified Blue parity',status=status,detail=detail,source='https://github.com/colonelpanichacks/oui-spy-unified-blue'))
(root / "qmarauder/features.json").write_text(json.dumps(entries, indent=2)+"\n", encoding="utf-8")
print(f"Wrote {len(entries)} capability records")
