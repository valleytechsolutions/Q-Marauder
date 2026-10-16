"""Independent BLE metadata decoding and watchlist rules; no upstream firmware code."""
import re

BASE = '-0000-1000-8000-00805f9b34fb'
MAC = re.compile(r'(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}')
SERVICES = {'1800': 'Generic access', '1801': 'GATT', '180a': 'Device information',
            '180f': 'Battery', '1812': 'HID', '180d': 'Heart rate', '181a': 'Environmental sensing',
            'feaa': 'Eddystone', 'fe2c': 'Fast Pair', 'fcd2': 'BTHome', 'fd6f': 'Exposure notification'}
COMPANIES = {0x004c: 'Apple', 0x0006: 'Microsoft', 0x00e0: 'Google', 0x034d: 'TASER International',
             0x0d53: 'Luxottica Group'}


def uuid(value):
    value = str(value).lower().removeprefix('0x')
    if re.fullmatch(r'[0-9a-f]{4}', value):
        return '0000' + value + BASE
    if re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', value):
        return value
    raise ValueError('Use a 16-bit or full Bluetooth UUID')


def decode(row):
    """BlueZ properties are aggregated metadata, not a raw advertising packet."""
    row = dict(row)
    services = set(row.get('uuids', [])) | set(row.get('service_data', {}))
    signals = [SERVICES[u[4:8]] for u in sorted(services) if u.startswith('0000') and u.endswith(BASE) and u[4:8] in SERVICES]
    companies = row.get('manufacturer_data', {})
    for key in companies:
        company = int(key, 16)
        signals.append(COMPANIES.get(company, f'Company 0x{company:04X}'))
    apple = companies.get('004c', '')
    if apple.startswith('0215') and len(apple) >= 46:
        signals.append('iBeacon format')
    row['signals'] = signals
    row['fingerprint'] = ' / '.join(signals[:3]) or 'Unclassified advertiser'
    row['identity_verified'] = False
    row['metadata_source'] = 'BlueZ aggregated properties; packet boundaries unavailable'
    return row


def validate_rules(rules):
    if not isinstance(rules, list) or len(rules) > 32:
        raise ValueError('Use at most 32 watchlist rules')
    result = []
    for rule in rules:
        if not isinstance(rule, dict) or set(rule) != {'label', 'kind', 'value'}:
            raise ValueError('Each rule needs label, kind and value')
        label, kind, value = rule['label'], rule['kind'], rule['value']
        if not isinstance(label, str) or not 1 <= len(label) <= 40 or any(ord(c) < 32 for c in label):
            raise ValueError('Rule label must contain 1–40 printable characters')
        if not isinstance(value, str) or not 1 <= len(value) <= 80:
            raise ValueError('Invalid watchlist value')
        if kind == 'address':
            if not MAC.fullmatch(value): raise ValueError('Invalid Bluetooth address')
            value = value.upper()
        elif kind == 'oui':
            if not re.fullmatch(r'(?:[0-9a-fA-F]{2}:){2}[0-9a-fA-F]{2}', value): raise ValueError('Invalid OUI')
            value = value.upper()
        elif kind == 'company':
            if not re.fullmatch(r'(?:0x)?[0-9a-fA-F]{4}', value): raise ValueError('Use a four-digit company ID')
            value = value.lower().removeprefix('0x')
        elif kind == 'service': value = uuid(value)
        elif kind == 'name': value = value.casefold()
        else: raise ValueError('Unknown watchlist rule kind')
        result.append(dict(label=label, kind=kind, value=value))
    return result


def detections(rows, rules):
    hits = []
    for row in rows:
        reasons = []
        for rule in rules:
            kind, value = rule['kind'], rule['value']
            match = (kind == 'address' and row['address'] == value or
                     kind == 'oui' and row.get('address_type') == 'public' and row['address'].startswith(value+':') or
                     kind == 'company' and value in row.get('manufacturer_data', {}) or
                     kind == 'service' and value in (set(row.get('uuids', [])) | set(row.get('service_data', {}))) or
                     kind == 'name' and value in row.get('name', '').casefold())
            if match: reasons.append(f"{rule['label']} ({kind})")
        if reasons:
            hits.append({**row, 'kind': 'ble-detection', 'matches': reasons,
                         'note': 'Watchlist match; device identity and surveillance activity are not verified.'})
    return hits


def proximity(samples):
    values = [s['rssi'] for s in samples if isinstance(s.get('rssi'), (int, float))]
    if not values: return dict(samples=samples, latest=None, peak=None, trend='No fresh signal')
    change = sum(values[-3:])/len(values[-3:]) - sum(values[:3])/len(values[:3])
    return dict(samples=samples, latest=values[-1], peak=max(values),
                trend='Stronger signal' if len(values) >= 4 and change > 3 else
                      'Weaker signal' if len(values) >= 4 and change < -3 else 'Steady / insufficient change')
