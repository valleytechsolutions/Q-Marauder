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
    helper = capabilities.get('lab', {})
    wifi_absent = helper.get('configured') and helper.get('interface_present') is False
    return [
        ("Wi-Fi discovery", "Ready" if tools.get("nmcli") and interfaces else "Unavailable",
         adapters + ". AP discovery uses NetworkManager. Select Scan APs in Wi-Fi."),
        ("BLE discovery", "BlueZ available" if tools.get("bluetoothctl") else "BlueZ tool missing",
         "Select Scan BLE in Bluetooth. This lists discovered devices and signal strength; it is not raw Bluetooth packet capture."),
        ("Monitor capture", monitor_text,
         f"Driver monitor support: {monitor_text}. NET_ADMIN: {'yes' if privileges.get('net_admin') else 'missing'}. "
         f"NET_RAW: {'yes' if privileges.get('net_raw') else 'missing'} in console. Use Lab packet recon for measured results from the separate radio worker."),
        ("Lab helper", "Wi-Fi radio absent / BLE ready" if wifi_absent and helper.get('hci_capture') else "Configured / test next" if capabilities.get("lab", {}).get("configured") else "Admin setup required",
         "BLE packet capture is available. Reconnect/configure the Wi-Fi monitor adapter before Wi-Fi tests." if wifi_absent else "Run Lab packet recon, then Injection check. A response permits a bounded 3-frame deauth test. "
         "Monitor support alone does not prove injection." if capabilities.get("lab", {}).get("configured")
         else capabilities.get("lab", {}).get("reason", "See docs/LAB.md for one-time admin setup. No raw radio job has been run.")),
        ("MT7921 USB adapter", "Attached / driver loaded" if usb_attached else "Module available" if usb_module.get("available") else "Driver missing" if usb_support == "disabled" else "Driver configured" if usb_support in ("y", "m") else "Not measured",
         "An MT7921 USB radio is attached to Linux. Capture and injection results are in Lab report." if usb_attached else "A PC adapter needs USB/IP forwarding and a matching Linux driver. See USB radio setup."),
    ]


def result_page(state, kind, page, controls=False):
    if kind not in (1, 2, 3, 4, 5, 6, 7, 8, 9) or not 0 <= page <= 2499:
        raise ValueError("Invalid display result page")
    if kind == 9:
        rows = [(entry['name'], entry['status'].upper(), entry['detail']) for entry in state.get('features', []) if entry['category'].startswith('Raspyjack / ')]
        status = 'Port status / not a tool launcher'
    elif kind == 8:
        from .linux_tools import display_rows
        report = state.get('linux_report') or {}
        rows = display_rows(report)
        status = 'Linux task running...' if report.get('state') == 'running' else 'Linux report / tap details'
    elif kind == 7:
        from .capture import display_rows
        report = state.get('packet_lab') or {}
        rows = display_rows(report)
        status = 'Receiving / please wait' if report.get('state') == 'running' else 'Capture / tap for details'
    elif kind in (5, 6):
        report = state.get('ble_lab') or {}
        status = 'BLE task running...' if report.get('state') == 'running' else 'BLE lab / tap details'
        if report.get('state') == 'error':
            rows = [('BLE task failed', 'Tap for details', report.get('error', 'Unknown error'))]
        elif report.get('state') == 'running':
            rows = [('Working', 'Please wait', 'The bounded BLE job stops automatically.')]
        elif kind == 6:
            rows = [(r.get('name') or 'Unnamed advertiser', ', '.join(r['matches']), r['address']+'. '+r['note']) for r in state.get('detections', [])]
            if not rows: rows = [('No watchlist matches', 'Configure rules in Settings', 'No match does not prove the absence of surveillance equipment.')]
        elif report.get('action') == 'ble-advertise':
            rows = [('BLE advertising test', 'Stopped' if report.get('state') == 'stopped' else str(report.get('registered',0))+' registrations', report.get('note',''))]
        elif report.get('action') == 'ble-foxhunt':
            signal = f"{report['latest']} dBm" if report.get('latest') is not None else 'No fresh signal'
            peak = f"{report['peak']} dBm" if report.get('peak') is not None else 'unavailable'
            rows = [('Selected BLE target', report.get('address',''), 'Signal strength varies with reflections and orientation; this is not a distance measurement.'),
                    ('RSSI tracking', signal, f"Peak: {peak}. {report.get('trend', '')}. {len(report.get('samples', []))} fresh samples.")]
        else:
            rows = [(c['uuid'], ' / '.join(c['flags']),
                     'Write completed' if c.get('write_completed') else 'Value: '+c['value'] if 'value' in c else c.get('read_error') or 'Service: '+c['service'],
                     c['uuid']) for c in report.get('characteristics', [])]
            rows += [('Descriptor '+d['uuid'][:8], d.get('value') or ' / '.join(d.get('flags', [])),
                      d.get('read_error') or 'Characteristic: '+d['characteristic']) for d in report.get('descriptors', [])]
            if report.get('hid'):
                rows.insert(0, ('HID report maps', f"{len(report['hid'])} layouts decoded", '; '.join(f"{r['kind']} ID {r['id']}: {r['bytes']} bytes" for layout in report['hid'].values() for r in layout['reports'])))
            if report.get('action') == 'ble-pair' and report.get('state') == 'done':
                rows = [('Pairing complete', 'Ready for GATT inspection', 'The selected device is paired. Return to BLE tools to inspect its services.')]
            if report.get('action') in ('ble-notify','ble-hid-listen'):
                rows.insert(0, ('Notification window', f"{len(report.get('notifications', []))} events / 10 seconds",
                                'Last value: '+report['notifications'][-1]['value'] if report.get('notifications') else 'No value changes received during this window. This does not indicate a failed subscription.'))
            if report.get('action') == 'ble-hid-listen':
                for event in report.get('notifications', [])[-8:]:
                    decoded = event.get('decoded', {})
                    description = event.get('decode_error') or '; '.join(
                        f"page {f['page']} usage {f['usage']}: {f['value']}" for f in decoded.get('fields', []) if f['value']) or 'All observed values are zero.'
                    rows.append(('HID input', 'Report ID '+str(decoded.get('report_id','?')), description))
            if not rows: rows = [('BLE Lab', 'Choose a device from BLE results', 'Scan BLE, tap your device, and tap USE. Then open BLE tools for pairing, GATT and signal tracking.')]
    elif kind == 3:
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
            if report.get('action') == 'capture':
                rows = [('Wi-Fi PCAP saved', f"{report.get('captured',0)} packets / 8 sec", 'Download this session as PCAP in Field log. Radiotap / linktype 127. Nearby traffic may be included.'),
                        ('Channel', str(report.get('monitor_frequency') or 'Unknown')+' MHz', 'Single configured lab channel; no channel hopping.'),
                        ('Capture limit', 'Reached' if report.get('capture_limit_reached') else 'Within budget', 'At most 512 KiB / 2000 packets. No packets are transmitted by this capture job.')]
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
                signal = f"RSSI {rssi} dBm" if rssi is not None else "RSSI unavailable"
                summary = signal + (' / '+row['oui_vendor'] if row.get('oui_vendor') else '')
                details = f"{row.get('address', '?')}  {signal}. {('OUI: '+row['oui_vendor']) if row.get('oui_vendor') else row.get('fingerprint', 'Bluetooth LE discovery')}. Identity unverified."
            rows.append((name, summary, details, row.get('address','') if kind == 2 else ''))
        scanning = state.get("busy") in (("wifi", "survey") if kind == 1 else ("ble",))
        status = "Scanning / previous results" if scanning and rows else "Scanning..." if scanning else f"{len(rows)} found / tap for details"
        if state.get("scan_status", {}).get(key, {}).get("state") == "error":
            status = "Scan error / see console"
        elif state.get('scan_status', {}).get(key, {}).get('state') == 'cached':
            status = 'Saved results / rescan for current'
    if controls: rows = [(*row, '') if len(row) == 3 else row for row in rows]
    payload = "\n".join("\t".join(plain(value, limit) for value, limit in zip(row, (32, 46, 140, 36) if controls else (32, 46, 180)))
                        for row in rows[page * 4:page * 4 + 4])
    return min(len(rows), 9999), plain(status, 36), payload
