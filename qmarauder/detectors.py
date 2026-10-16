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
    dict(name='Packet detector', action='packet-detector', status='partial', detail='Same-report Meta company + FD5F service matching, Flock and Axon candidates from HCI advertising reports. Broadcast identity remains unverified.'),
    dict(name='Foxhunter', action='ble-foxhunt', status='partial', detail='Selected target RSSI, 20-second window. Signal trend is not distance; audio hardware is not fitted.'),
    dict(name='AXEOFF BLE', action='ble-axon', status='partial', detail='Axon/TASER public identifiers. Active discovery; no Wi-Fi matching or passive-scan claim.'),
    dict(name='AXEOFF Wi-Fi', action='axon-wifi', status='partial', detail='Axon Enterprise transmitter OUI in received management frames. Samples channels 1/6/11 on an idle monitor radio; connected radios stay on their channel. Identity unverified.'),
    dict(name='Flock Wi-Fi', action='flock-wifi', status='partial', detail='Registered Flock transmitter OUI; receive windows on channels 1/6/11 with an idle monitor adapter. Connected radios remain on their own channel. No generic Qualcomm fingerprint claim.'),
    dict(name='Flock BLE', action='flock-ble', status='partial', detail='Flock service, name patterns and public OUI evidence from individual reports. XUNTONG company alone never triggers a match. 12-second bounded capture.'),
    dict(name='Wi-Fi PCAP', action='wifi-capture', status='partial', detail='8-second radiotap capture, 512 KiB / 2000-packet limit, PCAP export on the configured lab channel. Flock/Sky Spy Wi-Fi use separate channel-sampling jobs. Requires the updated radio helper.'),
    dict(name='Sky Spy Wi-Fi', action='sky-wifi', status='partial', detail='OpenDroneID beacon and NAN decoding: Basic ID, Location, Authentication, Self ID, System and Operator ID. Channels 1/6/11 or connected channel. Requires a working monitor adapter.'),
    dict(name='Sky Spy BLE', action='sky-ble', status='partial', detail='Remote ID FFFA service-data messages from complete legacy/extended HCI reports. Broadcast claims are unverified. Incomplete extended fragments are retained in PCAP but not decoded.'),
    dict(name='BLE Sniff', action='ble-sniff', status='partial', detail='12-second received HCI advertisement PCAP (linktype 201), with 8-second BlueZ discovery. Scan requests may transmit. No connection sniffing or link-layer channel/CRC metadata.'),
]
