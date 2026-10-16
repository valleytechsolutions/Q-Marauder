"""Small, paginated native-screen views; radio identifiers stay on the device."""
import re


def plain(value, limit):
    # The MCU font is ASCII. Strip framing/control bytes from untrusted radio names.
    return re.sub(r"[^ -~]", "?", str(value))[:limit]


def readiness_rows(capabilities):
    tools = capabilities.get("tools", {})
    privileges = capabilities.get("privileges", {})
    interfaces = capabilities.get("interfaces", [])
    adapters = ", ".join(f"{r['name']} / {r['driver']}" for r in interfaces) or "No Wi-Fi adapter found"
    monitor = capabilities.get("monitor_advertised")
    monitor_text = "Advertised / unverified" if monitor else "Not advertised" if monitor is False else "Not measured"
    usb_support = capabilities.get("kernel", {}).get("options", {}).get("MT7921U", "unknown")
    usb_module = capabilities.get("kernel", {}).get("modules", {}).get("mt7921u", {})
    usb_attached = any(r.get("driver") == "mt7921u" for r in interfaces)
    return [
        ("Wi-Fi discovery", "Ready" if tools.get("nmcli") and interfaces else "Unavailable",
         adapters + ". AP discovery uses NetworkManager. Select Scan APs in Wi-Fi."),
        ("BLE discovery", "BlueZ available" if tools.get("bluetoothctl") else "BlueZ tool missing",
         "Select Scan BLE in Bluetooth. This lists discovered devices and signal strength; it is not raw Bluetooth packet capture."),
        ("Monitor capture", monitor_text,
         f"Driver monitor support: {monitor_text}. NET_ADMIN: {'yes' if privileges.get('net_admin') else 'missing'}. "
         f"NET_RAW: {'yes' if privileges.get('net_raw') else 'missing'} in console. Use Lab packet recon for measured results from the separate radio worker."),
        ("Lab helper", "Configured / test next" if capabilities.get("lab", {}).get("configured") else "Admin setup required",
         "Run Lab packet recon, then Injection check. A response permits a bounded 3-frame deauth test. "
         "Monitor support alone does not prove injection." if capabilities.get("lab", {}).get("configured")
         else capabilities.get("lab", {}).get("reason", "See docs/LAB.md for one-time admin setup. No raw radio job has been run.")),
        ("MT7921 USB adapter", "Attached / driver loaded" if usb_attached else "Module available" if usb_module.get("available") else "Driver missing" if usb_support == "disabled" else "Driver configured" if usb_support in ("y", "m") else "Not measured",
         "An MT7921 USB radio is attached to Linux. Capture and injection results are in Lab report." if usb_attached else "A PC adapter needs USB/IP forwarding and a matching Linux driver. See USB radio setup."),
    ]


def result_page(state, kind, page):
    if kind not in (1, 2, 3, 4) or not 0 <= page <= 2499:
        raise ValueError("Invalid display result page")
    if kind == 3:
        rows = readiness_rows(state.get("capabilities", {}))
        status = "Checking radio" if state.get("busy") == "diagnostics" else "Radio readiness"
    elif kind == 4:
        report = state.get("lab") or {}
        phase = report.get("state", "idle")
        status = "Lab test running..." if phase == "running" else "Lab test error" if phase == "error" else "Lab report"
        if phase in ("running", "idle", "error"):
            rows = [("Running test" if phase == "running" else "Test could not complete" if phase == "error" else "No lab test yet",
                     "Please wait" if phase == "running" else "Tap for details",
                     report.get("error") or "Use the lab controls under Wi-Fi / Sniffers and Wi-Fi / Attacks.")]
        else:
            if report.get("action") == "recon" and not report.get("capture_observed"):
                status = "No lab capture received"
            elif report.get("action") == "injection" and not report.get("injection_observed"):
                status = "Injection unverified"
            rows = [
                ("Lab access point", f"{report.get('frequency', '?')} MHz", report.get("bssid", "Unknown")),
                ("Packet reconnaissance", f"{report.get('frames', 0)} received / {report.get('stations', 0)} clients",
                 f"Beacons: {report.get('beacons', 0)}. Deauth frames observed: {report.get('deauth_seen', 0)}. "
                 "Only configured lab traffic is counted. Client count can be incomplete."),
                ("Transmit / responses", f"Sent {report.get('sent', 0)} / replies {report.get('probe_responses', 0)}",
                 "Injection observed in this test." if report.get("injection_observed") else "Transmission counts alone do not validate injection or client disconnection."),
                ("Test outcome", report.get("action", "Test"), report.get("note", "No outcome recorded")),
            ]
    else:
        key = "wifi" if kind == 1 else "ble"
        rows = []
        for row in state.get(key, [])[:9999]:
            name = row.get("name") or ("Hidden network" if kind == 1 else "Unnamed device")
            if kind == 1:
                summary = f"CH {row.get('channel', '?')} / {row.get('band', '?')} / {row.get('signal', '?')}%"
                details = f"{row.get('address', '?')}  {row.get('security', '?')}. {summary}. Signal is quality percent, not dBm."
            else:
                rssi = row.get("rssi")
                summary = f"RSSI {rssi} dBm" if rssi is not None else "RSSI unavailable"
                details = f"{row.get('address', '?')}  {summary}. Bluetooth LE discovery."
            rows.append((name, summary, details))
        scanning = state.get("busy") in (("wifi", "survey") if kind == 1 else ("ble",))
        status = "Scanning / previous results" if scanning and rows else "Scanning..." if scanning else f"{len(rows)} found / tap for details"
        if state.get("scan_status", {}).get(key, {}).get("state") == "error":
            status = "Scan error / see console"
    payload = "\n".join("\t".join(plain(value, limit) for value, limit in zip(row, (32, 46, 180)))
                        for row in rows[page * 4:page * 4 + 4])
    return min(len(rows), 9999), plain(status, 36), payload
