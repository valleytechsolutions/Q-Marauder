"""Bounded decoders for received HCI advertisements and 802.11 management data.

These parse packet boundaries, never BlueZ's merged Device1 properties.
"""
import struct
import uuid


def pcap_records(raw):
    if len(raw) < 24 or len(raw) > 524288 or raw[:4] != b'\xd4\xc3\xb2\xa1':
        raise ValueError('Unsupported or oversized PCAP')
    major, minor, _, _, snap, link = struct.unpack_from('<HHIIII', raw, 4)
    if (major, minor) != (2, 4) or snap > 65535:
        raise ValueError('Invalid PCAP header')
    offset, records = 24, []
    while offset < len(raw):
        if offset + 16 > len(raw): raise ValueError('Truncated PCAP record')
        seconds, micros, size, original = struct.unpack_from('<IIII', raw, offset)
        offset += 16
        if size > snap or size > original or micros >= 1000000 or offset + size > len(raw):
            raise ValueError('Invalid PCAP packet length')
        records.append((seconds + micros / 1e6, raw[offset:offset+size]))
        offset += size
        if len(records) > 2000: raise ValueError('Too many PCAP records')
    return link, records


def ad_fields(data):
    result, offset = [], 0
    while offset < len(data):
        size = data[offset]
        if not size: break
        if offset + size + 1 > len(data): raise ValueError('Truncated advertising field')
        result.append((data[offset+1], data[offset+2:offset+1+size]))
        offset += size + 1
    return result


def advertisement(data):
    """Decode one complete advertising report, without combining scan responses."""
    result = dict(name='', uuids=[], manufacturer_data={}, service_data={})
    for kind, value in ad_fields(data):
        if kind in (8, 9): result['name'] = value.decode('utf-8', errors='replace')[:248]
        elif kind in (2, 3, 4, 5, 6, 7):
            width = 2 if kind < 4 else 4 if kind < 6 else 16
            if len(value) % width: raise ValueError('Incomplete service UUID')
            for offset in range(0, len(value), width):
                part = value[offset:offset+width]
                result['uuids'].append(str(uuid.UUID(bytes=part[::-1])) if width == 16 else f'{int.from_bytes(part,"little"):08x}-0000-1000-8000-00805f9b34fb')
        elif kind == 255 and len(value) >= 2:
            result['manufacturer_data'][f'{int.from_bytes(value[:2],"little"):04x}'] = value[2:].hex()
        elif kind in (0x16, 0x20, 0x21):
            width = {0x16:2, 0x20:4, 0x21:16}[kind]
            if len(value) < width: raise ValueError('Incomplete service data UUID')
            key = str(uuid.UUID(bytes=value[:width][::-1])) if width == 16 else f'{int.from_bytes(value[:width],"little"):08x}-0000-1000-8000-00805f9b34fb'
            result['service_data'][key] = value[width:].hex()
    return result


def hci_reports(packet):
    """H4 LE advertising events only. Unknown/fragmented reports are not decoded."""
    if len(packet) < 5 or packet[:2] != b'\x04\x3e' or packet[2] != len(packet)-3:
        raise ValueError('Not a complete LE meta event')
    subtype, count, offset, rows = packet[3], packet[4], 5, []
    if subtype not in (2, 13): return []
    for _ in range(count):
        fixed = 9 if subtype == 2 else 24
        if offset + fixed > len(packet): raise ValueError('Truncated advertisement report')
        if subtype == 2:
            event, address_type = packet[offset:offset+2]
            address = packet[offset+2:offset+8][::-1].hex(':').upper()
            length = packet[offset+8]
            start, end = offset+9, offset+9+length
            if end >= len(packet): raise ValueError('Missing RSSI/data')
            rssi, offset, complete = packet[end], end+1, True
        else:
            event = int.from_bytes(packet[offset:offset+2], 'little')
            address_type = packet[offset+2]
            address = packet[offset+3:offset+9][::-1].hex(':').upper()
            rssi, length = packet[offset+13], packet[offset+23]
            start, end = offset+24, offset+24+length
            if end > len(packet): raise ValueError('Truncated extended data')
            offset, complete = end, ((event >> 5) & 3) == 0
        row = dict(address=address, address_type='public' if address_type in (0,2) else 'random' if address_type in (1,3) else 'anonymous',
                   rssi=None if rssi == 127 else rssi-256 if rssi > 127 else rssi,
                   complete=complete, event_type=event, extended=subtype == 13, raw=packet[start:end].hex())
        if complete:
            try: row.update(advertisement(packet[start:end]))
            except ValueError as exc: row.update(complete=False, decode_error=str(exc))
        rows.append(row)
    if offset != len(packet): raise ValueError('Unexpected HCI trailing bytes')
    return rows


def wifi_management(packet):
    if len(packet) < 8 or packet[0] != 0: return None
    length = int.from_bytes(packet[2:4], 'little')
    if length < 8 or length + 24 > len(packet): return None
    frame = packet[length:]
    control = int.from_bytes(frame[:2], 'little')
    # Reject protected, fragmented and non-management frames.
    if control & 0x440f or frame[22] & 15: return None
    return dict(subtype=(control >> 4) & 15, address=frame[10:16].hex(':').upper(),
                destination=frame[4:10].hex(':').upper(), body=frame[24:])


def wifi_ies(data):
    offset = 0
    while offset + 2 <= len(data):
        kind, length = data[offset:offset+2]
        if offset+2+length > len(data): return
        yield kind, data[offset+2:offset+2+length]
        offset += length + 2
