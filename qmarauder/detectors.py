"""Evidence-labelled detector presets; public protocol identifiers, not identity claims."""
from .ble_data import detections, uuid

AXON_RULES = [dict(label='Axon/TASER candidate', kind='oui', value='00:25:DF'),
              dict(label='TASER company identifier', kind='company', value='034d')]
AXON_RULES += [dict(label='Axon-associated service', kind='service', value=uuid(u)) for u in ('fc81','fe6b','fe6c')]


def evaluate(rows, mode, rules=()):
    chosen = AXON_RULES if mode == 'ble-axon' else [*AXON_RULES, *rules]
    hits = detections(rows, chosen)
    for hit in hits:
        hit.update(detector=mode, confidence='candidate', source='BlueZ aggregated metadata',
                   note='Identifier match only. Identity and surveillance activity are unverified. This scan may transmit scan requests.')
    return hits


MODES = [
    dict(name='Detector', action='ble-detector', status='partial', detail='Public identifier presets plus your watchlist. Meta same-packet verification is unavailable in aggregated BlueZ data.'),
    dict(name='Foxhunter', action='ble-foxhunt', status='partial', detail='Selected target RSSI, 20-second window. Signal trend is not distance; audio hardware is not fitted.'),
    dict(name='AXEOFF BLE', action='ble-axon', status='partial', detail='Axon/TASER public identifiers. Active discovery; no Wi-Fi matching or passive-scan claim.'),
    dict(name='Flock-You Wi-Fi', action=None, status='blocked', detail='Requires a monitor capture backend and validated Wi-Fi signatures; BLE company ID alone is insufficient.'),
    dict(name='Wi-Fi PCAP', action='wifi-capture', status='partial', detail='8-second radiotap capture, 512 KiB / 2000-packet limit, PCAP export. Uses the configured lab channel; channel hopping is pending. Requires the updated radio helper.'),
    dict(name='Sky Spy', action=None, status='blocked', detail='Requires raw Remote ID beacon payloads. No drone receiver has been verified in this build.'),
    dict(name='BLE Sniff', action=None, status='blocked', detail='Raw HCI/advertisement capture is not implemented. BlueZ device lists are not link-layer PCAP.'),
]
