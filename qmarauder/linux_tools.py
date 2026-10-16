"""Small Linux radio jobs shared by the desktop and portrait display.

Raspyjack's workflows are the reference, not an executable payload directory.
All commands here are fixed, bounded argument vectors; reports remain local.
"""
import json
from pathlib import Path
import re
from . import ble, radio

TOOLS = (
    dict(id='linux-interfaces', name='Radio interfaces', group='Wi-Fi', display_action=48,
         detail='Wireless interfaces, driver, addresses and lifetime byte counters. Read only.'),
    dict(id='wifi-audit', name='Wi-Fi security survey', group='Wi-Fi', display_action=49,
         detail='NetworkManager AP discovery with security and channel summaries. May send probe requests.'),
    dict(id='bt-controllers', name='Bluetooth controllers', group='Bluetooth', display_action=50,
         detail='Controller power, discoverability, pairing state and supported roles. Read only.'),
    dict(id='bt-classic', name='Bluetooth Classic scan', group='Bluetooth', display_action=51,
         detail='Eight-second BR/EDR discovery on the selected Bluetooth adapter. No pairing or connections.'),
    dict(id='wifi-channels', name='Wi-Fi channel survey', group='Wi-Fi', display_action=54,
         detail='Observed AP counts and signal quality by band/channel. Counts are not channel utilization.'),
    dict(id='wifi-changes', name='Wi-Fi scan changes', group='Wi-Fi', display_action=55,
         detail='Compare with the previous successful Linux Wi-Fi survey: new, not seen and changed BSSIDs.'),
    dict(id='ble-summary', name='BLE advert summary', group='Bluetooth', display_action=56,
         detail='Eight-second LE discovery with company, service and address-type summaries. Scan requests may transmit.'),
    dict(id='bt-devices', name='Saved Bluetooth devices', group='Bluetooth', display_action=57,
         detail='Read cached devices, pairing, trust and connection state on the selected adapter. No scanning or changes.'),
)
ACTIONS = tuple(tool['id'] for tool in TOOLS)


def card(title, summary, detail):
    return dict(title=str(title), summary=str(summary), detail=str(detail))


def security_class(value):
    text = str(value).upper().strip()
    if not text or text in ('--', 'OPEN', 'NONE'): return 'Open'
    if 'WEP' in text: return 'WEP'
    if 'WPA3' in text: return 'WPA2/WPA3' if 'WPA2' in text else 'WPA3'
    if 'WPA2' in text: return 'WPA2'
    if 'WPA' in text: return 'WPA1'
    if 'OWE' in text: return 'OWE'
    return 'Unknown'


def wifi_summary(networks):
    security, channels, groups = {}, {}, {}
    for ap in networks:
        label = security_class(ap.get('security', 'Unknown'))
        security[label] = security.get(label, 0) + 1
        channel = f"{ap['band']} / CH {ap['channel']}"
        channels[channel] = channels.get(channel, 0) + 1
        if ap.get('name'): groups.setdefault(ap['name'], set()).add(label)
    mixed = sorted(name for name, modes in groups.items() if len(modes) > 1)
    rows = [card('Survey summary', f'{len(networks)} access points',
                 f"{sum(not ap.get('name') for ap in networks)} hidden names; {len(channels)} observed band/channel pairs. AP count is not RF utilization."),
            card('Security advertised', ', '.join(f'{k}: {v}' for k, v in sorted(security.items())) or 'No observations',
                 'Advertised modes do not prove encryption quality or a vulnerability. OWE encrypts without authenticating the network.'),
            card('Mixed-mode names', str(len(mixed)),
                 'Mixed security alone does not establish an evil twin. SSIDs: '+(', '.join(mixed) or 'none observed')+'.')]
    rows += [card(channel, f'{count} access points', 'Observed AP count in this survey; not airtime or interference.')
             for channel, count in sorted(channels.items())]
    rows += [card(ap.get('name') or 'Hidden network', f"{ap['security']} / CH {ap['channel']}",
                  f"{ap['address']}; {ap['band']}; signal quality {ap['signal']}%, not dBm.") for ap in networks]
    return dict(rows=rows, networks=networks, security=security, channels=channels, mixed_security_names=mixed,
                note='NetworkManager survey; no monitor capture, client enumeration or channel hopping. Results are observations, not vulnerability findings.')


def interfaces(net_root=Path('/sys/class/net')):
    if not net_root.exists(): raise RuntimeError('Wireless interface reports require Linux sysfs.')
    addresses = json.loads(radio.run(['ip', '-j', 'address', 'show'], timeout=5))
    by_name = {entry.get('ifname'): entry for entry in addresses}
    rows, devices = [], []
    for dev in sorted(net_root.iterdir())[:64]:
        if not ((dev/'wireless').exists() or (dev/'phy80211').exists()): continue
        def read(name):
            try: return (dev/name).read_text().strip()[:100]
            except OSError: return 'unknown'
        driver = dev/'device/driver'
        ips = [str(info.get('local', '')) for info in by_name.get(dev.name, {}).get('addr_info', [])][:16]
        record = dict(name=dev.name, driver=driver.resolve().name if driver.exists() else 'unknown',
                      state=read('operstate'), rx_bytes=read('statistics/rx_bytes'),
                      tx_bytes=read('statistics/tx_bytes'), addresses=ips)
        devices.append(record)
        rows.append(card(dev.name, record['driver']+' / '+record['state'],
                         'Addresses: '+(', '.join(ips) or 'none')+f"; RX {record['rx_bytes']} / TX {record['tx_bytes']} bytes since interface creation."))
    if not rows: rows = [card('No Wi-Fi interfaces', 'Not detected', 'Attach a supported radio or inspect System diagnostics.')]
    return dict(rows=rows, interfaces=devices, note='Read-only Linux interface snapshot. Driver presence does not prove monitor reception or injection.')


def parse_controller(text, address):
    values = {}
    for line in text.splitlines():
        match = re.match(r'\s*(Name|Alias|Powered|Discoverable|Pairable|Discovering|Roles):\s*(.+)', line)
        if match: values.setdefault(match[1].lower(), []).append(match[2].strip())
    if 'powered' not in values: raise RuntimeError('BlueZ returned no controller properties.')
    return dict(address=address, **{key: ', '.join(value) for key, value in values.items()})


def controllers():
    output = radio.run(['bluetoothctl', 'list'], timeout=5)
    addresses = list(dict.fromkeys(re.findall(r'^Controller ([0-9A-Fa-f:]{17})\s', output, re.M)))[:4]
    if not addresses: raise RuntimeError('BlueZ reports no Bluetooth controllers.')
    devices, rows = [], []
    for address in addresses:
        if not re.fullmatch(r'(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}', address): continue
        value = parse_controller(radio.run(['bluetoothctl', 'show', address], timeout=5), address)
        devices.append(value)
        rows.append(card(value.get('alias', value.get('name', address)),
                         'Powered '+value['powered']+' / discovering '+value.get('discovering', '?'),
                         f"{address}; discoverable {value.get('discoverable', '?')}; pairable {value.get('pairable', '?')}; roles {value.get('roles', 'not reported')}."))
    if not devices: raise RuntimeError('BlueZ returned no valid controller addresses.')
    return dict(rows=rows, controllers=devices, note='Controller properties only. No power, pairing or discoverability settings were changed.')


def run(action, preferences, baseline=None):
    from . import survey_analysis
    if action not in ACTIONS: raise ValueError('Unknown Linux radio tool')
    if action == 'linux-interfaces': report = interfaces()
    elif action == 'wifi-audit': report = wifi_summary(radio.wifi_scan())
    elif action == 'bt-controllers': report = controllers()
    elif action == 'wifi-channels': report = survey_analysis.channels(radio.wifi_scan())
    elif action == 'wifi-changes': report = survey_analysis.changes(radio.wifi_scan(), baseline)
    elif action == 'ble-summary':
        result = ble.call(dict(action='ble', adapter=preferences['adapter'], target=''))
        report = survey_analysis.advertisements(result['rows'])
    elif action == 'bt-devices':
        result = ble.call(dict(action='bt-devices', adapter=preferences['adapter'], target=''))
        report = survey_analysis.known_devices(result['rows'])
    else:
        result = ble.call(dict(action='bt-classic', adapter=preferences['adapter'], target=''))
        devices = result['rows']
        report = dict(devices=devices, adapter=preferences['adapter'],
                      rows=[card('BR/EDR discovery', f'{len(devices)} fresh observations / 8 sec',
                                 'Only discoverable devices may respond. No result does not prove absence. SDP enumeration is not implemented yet.')]+
                           [card(row.get('name') or 'Unnamed device', row['address'],
                                 f"RSSI {row.get('rssi')} dBm; class {row.get('device_class', 'unknown')}; "
                                 f"{len(row.get('uuids', []))} cached/advertised service UUIDs.") for row in devices],
                      note='Requested BR/EDR discovery through BlueZ. Other discovery clients can affect combined filters. No pairing, connection or SDP query was performed.')
    report.update(action=action, kind='linux-tool', state='done')
    return report


def display_rows(report):
    if not report: return [('Linux tools', 'Choose a tool', 'Open Linux tools from Home, Wi-Fi or Bluetooth.')]
    if report.get('state') == 'running': return [('Working', 'Please wait', 'This bounded Linux job stops automatically.')]
    if report.get('state') == 'error': return [('Tool failed', 'Tap for details', report.get('error', 'Unknown error'))]
    return [(row['title'], row['summary'], row['detail']) for row in report.get('rows', [])]
