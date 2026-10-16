"""Unprivileged packet analysis and bounded receiver orchestration."""
import base64
from concurrent.futures import ThreadPoolExecutor
import re
from . import ble, lab, packets, remote_id

ACTIONS = ('flock-wifi', 'flock-ble', 'sky-wifi', 'sky-ble', 'ble-sniff', 'packet-detector', 'axon-wifi')
FLOCK_SERVICE = 'e8ccbb38-9532-46a8-9fe5-1814df172e6f'


def match_ble(row):
    evidence = []
    name = row.get('name', '')
    services = set(row.get('uuids', [])) | set(row.get('service_data', {}))
    companies = row.get('manufacturer_data', {})
    public = row.get('address_type') == 'public'
    if public and row['address'].startswith('B4:1E:52:'): evidence.append('Flock Safety registered public OUI')
    if FLOCK_SERVICE in services: evidence.append('Flock accessory service UUID')
    if re.fullmatch(r'Penguin-\d{10}', name): evidence.append('Flock-associated Penguin name pattern')
    if name == 'FS Ext Battery': evidence.append('Flock-associated battery name')
    if re.fullmatch(r'\d{10}', name) and '09c8' in companies:
        evidence.append('Flock candidate: numeric name + XUNTONG company (not unique)')
    # Common module OUIs, Nordic DFU and company 09c8 alone are not Flock evidence.
    if public and row['address'].startswith('00:25:DF:'): evidence.append('Axon Enterprise registered public OUI')
    if '034d' in companies: evidence.append('TASER company identifier')
    if any(f'0000{u}-0000-1000-8000-00805f9b34fb' in services for u in ('fc81','fe6b','fe6c')):
        evidence.append('Axon-associated service')
    if '0d53' in companies and '0000fd5f-0000-1000-8000-00805f9b34fb' in services:
        evidence.append('Meta company + FD5F service in the same advertising report')
    return evidence


def analyze(raw, mode):
    link, records = packets.pcap_records(raw)
    detections, remote, advertisements = {}, {}, {}
    malformed, partial, reports = 0, 0, 0
    for timestamp, packet in records:
        try:
            if link == 201:
                if packet[:4] != b'\0\0\0\1': raise ValueError('Expected received HCI event')
                rows = packets.hci_reports(packet[4:])
            elif link == 127:
                frame = packets.wifi_management(packet)
                if not frame: continue
                evidence = []
                if frame['address'].startswith('B4:1E:52:'): evidence.append('Flock Safety registered transmitter OUI')
                if frame['address'].startswith('00:25:DF:'): evidence.append('Axon Enterprise registered transmitter OUI')
                rows = [dict(address=frame['address'], name='', complete=True, wifi=True, evidence=evidence)]
            else: raise ValueError('Unsupported capture linktype')
            for row in rows:
                reports += 1
                if not row['complete']: partial += 1; continue
                evidence = row.get('evidence', []) if row.get('wifi') else match_ble(row)
                if mode.startswith('flock'): evidence = [v for v in evidence if 'Flock' in v]
                if mode == 'axon-wifi': evidence = [v for v in evidence if 'Axon' in v]
                if evidence and not mode.startswith('sky'):
                    key = row['address']
                    old = detections.get(key)
                    if old:
                        old['matches'] = sorted(set(old['matches']+evidence)); old['last_seen'] = timestamp; old['packets'] += 1
                    elif len(detections) < 256:
                        detections[key] = dict(address=key, name=row.get('name',''), matches=evidence,
                            confidence='candidate', source='received Wi-Fi frame' if row.get('wifi') else 'single HCI advertising report',
                            first_seen=timestamp, last_seen=timestamp, packets=1,
                            note='Broadcast identifiers can be spoofed. Vendor/signature match is not verified identity or surveillance activity.')
                payloads = remote_id.wifi_payloads(frame) if row.get('wifi') else remote_id.ble_payloads(row)
                for payload in payloads:
                    try:
                        for message in remote_id.decode(payload):
                            key = (row['address'], message['type'], message.get('page',0), message.get('id_type',0))
                            if len(remote) < 256 or key in remote:
                                remote[key] = dict(message, address=row['address'], received=timestamp,
                                    transport='Wi-Fi' if row.get('wifi') else 'BLE', verified=False)
                    except ValueError: malformed += 1
                if not row.get('wifi') and (len(advertisements) < 200 or row['address'] in advertisements):
                    advertisements[row['address']] = {**row, 'raw': row['raw'][:128], 'last_seen':timestamp}
        except ValueError: malformed += 1
    return dict(detections=list(detections.values()), remote_id=list(remote.values()),
                advertisements=list(advertisements.values()), reports=reports, malformed=malformed, incomplete=partial)


def run(action, preferences):
    if action not in ACTIONS: raise ValueError('Unknown capture action')
    if action.endswith('wifi'):
        report = lab.call('wifi-discovery')
    else:
        request = ble.request_for('ble', preferences)
        future = []
        with ThreadPoolExecutor(max_workers=1) as worker:
            report = lab.call('ble-capture-'+request['adapter'][-1], on_ready=lambda: future.append(worker.submit(ble.call, request)))
            if not future: raise RuntimeError('Radio helper did not acknowledge capture readiness')
            future[0].result()  # Fail visibly if discovery failed; never call zero packets success.
    raw = base64.b64decode(report.pop('pcap'), validate=True)
    report.update(analyze(raw, action), action=action)
    return report, raw


def display_rows(report):
    phase = report.get('state')
    if phase != 'done':
        return [('Capture failed' if phase == 'error' else 'Receiving packets', 'Tap for details',
                 report.get('error') or 'Bounded job; results appear after the receive window. No continuous capture is running.')]
    rows = [('Capture saved', f"{report.get('captured',0)} packets / {report.get('reports',0)} reports", report.get('note','')),
            ('Detection summary', f"{len(report.get('detections',[]))} candidates / {len(report.get('remote_id',[]))} RID messages",
             'Candidate matches are unverified. Zero matches does not prove absence. Export PCAP and JSON from Field log.'),
            ('Receiver coverage', ', '.join(map(str,report.get('channels',[])))+' MHz' if report.get('channels') else report.get('adapter','HCI'),
             f"Malformed: {report.get('malformed',0)}. Incomplete reports: {report.get('incomplete',0)}. Capture limit: {'reached' if report.get('capture_limit_reached') else 'not reached'}.")]
    for hit in report.get('detections', []):
        rows.append((hit.get('name') or hit['address'], hit['matches'][0], '; '.join(hit['matches'])+'. '+hit['note']))
    for item in report.get('remote_id', []):
        if item['type'] == 'Location':
            position = f"Lat {item['latitude']} Lon {item['longitude']}." if item['location_valid'] else 'Position unavailable.'
            detail = position+f" Geo {item['altitude_geo_m']}m Baro {item['altitude_baro_m']}m Height {item['height_m']}m ({item['height_reference']})."
            rows.append(('RID Location', item['address'], detail))
            rows.append(('RID Movement', 'Broadcast claim / unverified',
                         f"Horizontal {item['horizontal_mps']}m/s Vertical {item['vertical_mps']}m/s Direction {item['direction_deg']}deg. Time {item['seconds_after_hour']}s after hour. Status {item['status']}."))
        else:
            fields = [f'{key}={value}' for key,value in item.items() if key not in ('raw','address','received','version','transport','verified','type')]
            detail = ''
            for field in fields:
                if len(detail)+len(field)+2 > 135 and detail:
                    rows.append(('RID '+item['type'], item['address'], detail)); detail=''
                detail += (', ' if detail else '')+field
            if detail: rows.append(('RID '+item['type'], item['address'], detail))
    if report.get('action') == 'ble-sniff':
        for item in report.get('advertisements', []):
            signal = f"RSSI {item['rssi']} dBm" if item.get('rssi') is not None else 'RSSI unavailable'
            rows.append((item.get('name') or item['address'], signal+' / '+item['address_type'],
                         item['address']+'. Companies: '+', '.join(item.get('manufacturer_data',{}))+'. Services: '+', '.join(item.get('uuids',[]))))
    return rows
