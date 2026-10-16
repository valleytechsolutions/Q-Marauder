"""Observation summaries: no identity, interference or vulnerability inference."""
from collections import Counter
from .ble_data import COMPANIES, SERVICES, BASE


def card(title, summary, detail):
    return dict(title=title, summary=summary, detail=detail)


def channels(networks):
    groups = {}
    for ap in networks:
        groups.setdefault((ap['band'], ap['channel']), []).append(ap)
    summary = []
    for (band, channel), aps in sorted(groups.items()):
        signals = [ap['signal'] for ap in aps]
        summary.append(dict(band=band, channel=channel, count=len(aps),
                            strongest=max(signals), average=round(sum(signals)/len(signals), 1)))
    rows = [card('Observed channels', f'{len(networks)} APs / {len(summary)} channels',
                 'AP count is not airtime or interference. Unobserved channels are not proven clear.')]
    rows += [card(f"{item['band']} / CH {item['channel']}",
                  f"{item['count']} APs / peak {item['strongest']}%",
                  f"Mean signal quality {item['average']}%. Quality percent is not dBm. Channel widths and overlap are not measured.")
             for item in summary]
    return dict(rows=rows, channels=summary, networks=networks,
                note='Fresh NetworkManager survey. Counts include observed AP BSSIDs, not clients or measured channel utilization.')


def changes(networks, baseline):
    before = {row['address']: row for row in (baseline or {}).get('networks', [])}
    after = {row['address']: row for row in networks}
    added, missing, changed = [], [], []
    if baseline is not None:
        added = [after[key] for key in sorted(after.keys()-before.keys())]
        missing = [before[key] for key in sorted(before.keys()-after.keys())]
        for address in sorted(before.keys() & after.keys()):
            old, new = before[address], after[address]
            fields = {key: {'before':old.get(key), 'after':new.get(key)}
                      for key in ('name','band','channel','security') if old.get(key) != new.get(key)}
            delta = new['signal'] - old['signal']
            if abs(delta) >= 15: fields['signal'] = dict(before=old['signal'], after=new['signal'])
            if fields: changed.append(dict(address=address, name=new.get('name',''), fields=fields))
    rows = [card('Survey comparison' if baseline is not None else 'Baseline saved',
                 f'{len(added)} new / {len(missing)} not seen / {len(changed)} changed' if baseline is not None else f'{len(networks)} APs recorded',
                 'Compare observations only. Not seen does not mean offline; changes do not establish an attack.' if baseline is not None
                 else 'Run Scan changes again to compare with this survey. No previous successful Wi-Fi tool report was available.')]
    if baseline is not None:
        rows.append(card('Previous survey', baseline.get('updated','Unknown time'),
                         'Latest successful Linux Wi-Fi survey, channel survey or comparison. Signal changes require at least 15 quality points.'))
    for label, entries in (('NEW', added), ('NOT SEEN', missing)):
        rows += [card(row.get('name') or 'Hidden network', label+f" / CH {row['channel']}", row['address']+'; '+row['security']) for row in entries]
    rows += [card(row['name'] or 'Hidden network', 'CHANGED / '+', '.join(row['fields']),
                  row['address']+'; '+'; '.join(f"{key}: {value['before']} -> {value['after']}" for key,value in row['fields'].items())) for row in changed]
    return dict(rows=rows, networks=networks, baseline_session=(baseline or {}).get('session'),
                baseline_time=(baseline or {}).get('updated'), baseline_created=baseline is None,
                added=added, not_seen=missing, changed=changed,
                note='Comparison by BSSID with the last successful Linux Wi-Fi tool report. NetworkManager results may include cached APs; this is not an evil-twin detector.')


def advertisements(devices):
    companies, services, address_types = Counter(), Counter(), Counter()
    for row in devices:
        address_types[row.get('address_type','unknown')] += 1
        companies.update(set(row.get('manufacturer_data', {})))
        services.update(set(row.get('uuids', [])) | set(row.get('service_data', {})))
    rows = [card('BLE address observations', f'{len(devices)} addresses / 8 sec',
                 'Addresses may rotate. BlueZ merges properties; these are not packet counts or verified device identities.'),
            card('Address types', ' / '.join(f'{k}: {v}' for k,v in sorted(address_types.items())) or 'No observations',
                 'Public/random describe addressing, not device trust. Private addresses cannot establish a manufacturer by OUI.')]
    for company, count in companies.most_common(128):
        label = COMPANIES.get(int(company,16), 'Company 0x'+company.upper())
        rows.append(card(label, f'{count} addresses / company 0x{company}', 'Advertised company identifier; identity unverified. One address may advertise several company IDs.'))
    for service, count in services.most_common(128):
        name = SERVICES.get(service[4:8], service) if service.startswith('0000') and service.endswith(BASE) else service
        rows.append(card(name, f'{count} addresses / service', service+'; cached/advertised service UUID, not a GATT read.'))
    rows += [card(row.get('name') or 'Unnamed advertiser', f"{row.get('rssi')} dBm" if row.get('rssi') is not None else 'RSSI unavailable',
                  row['address']+'; '+row.get('fingerprint','Unclassified')) for row in devices]
    return dict(rows=rows, devices=devices, companies=dict(companies), services=dict(services), address_types=dict(address_types),
                note='Eight-second LE discovery on the selected adapter; scan requests may transmit. Counts are per observed address. Top 128 company and service groups are shown; full counts are exported.')


def known_devices(devices):
    rows = [card('BlueZ device cache', f'{len(devices)} saved entries',
                 'Cached entries may be stale. This reads local BlueZ properties without scanning, pairing, connecting or changing trust.')]
    rows += [card(row['name'] or 'Unnamed device',
                  ('PAIRED' if row['paired'] else 'NOT PAIRED')+' / '+('CONNECTED' if row['connected'] else 'DISCONNECTED'),
                  row['address']+f"; trusted {row['trusted']}; blocked {row['blocked']}; {len(row['uuids'])} cached service UUIDs.") for row in devices]
    return dict(rows=rows, devices=devices,
                note='Local BlueZ cache on the selected adapter, at most 500 entries. Saved does not mean nearby. No device settings or connections were changed.')
