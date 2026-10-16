"""Independent ASTM/OpenDroneID broadcast decoder; protocol reference in docs.

Decoded broadcast claims are unverified; no authentication signature validation.
Only complete messages and known transport headers are accepted.
"""
import struct
from .packets import wifi_ies

NAMES = {0:'Basic ID', 1:'Location', 2:'Authentication', 3:'Self ID', 4:'System', 5:'Operator ID'}


def text(raw):
    return raw.split(b'\0', 1)[0].decode('ascii', errors='replace')


def altitude(raw):
    value = int.from_bytes(raw, 'little')
    return None if value == 0 else value * .5 - 1000


def coordinates(raw):
    lat, lon = struct.unpack('<ii', raw)
    lat, lon = lat/1e7, lon/1e7
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError('Remote ID coordinates out of range')
    return dict(latitude=lat, longitude=lon, location_valid=bool(lat or lon))


def decode(data):
    if not data: raise ValueError('Empty Remote ID message')
    kind, version = data[0] >> 4, data[0] & 15
    if version not in (1, 2): raise ValueError('Unsupported Remote ID version')
    if kind == 15:
        if len(data) < 3 or data[1] != 25 or not 1 <= data[2] <= 9 or len(data) != 3+25*data[2]:
            raise ValueError('Invalid Remote ID message pack')
        result = []
        for offset in range(3, len(data), 25):
            if data[offset] >> 4 == 15: raise ValueError('Nested message pack')
            result.extend(decode(data[offset:offset+25]))
        return result
    if len(data) != 25 or kind not in NAMES: raise ValueError('Unknown/incomplete Remote ID message')
    row = dict(type=NAMES[kind], version=version, raw=data.hex())
    if kind == 0:
        row.update(id_type=data[1] >> 4, aircraft_type=data[1] & 15,
                   uas_id=text(data[2:22]) if data[1] >> 4 in (1,2) else data[2:22].hex())
    elif kind == 1:
        direction = data[2] + (180 if data[1] & 2 else 0)
        speed = data[3] * (.75 if data[1] & 1 else .25) + (63.75 if data[1] & 1 else 0)
        vertical = struct.unpack('b', data[4:5])[0] * .5
        timestamp = int.from_bytes(data[21:23], 'little')
        row.update(coordinates(data[5:13]), status=data[1] >> 4, direction_deg=direction if direction < 360 else None,
                   horizontal_mps=None if speed == 255 else speed, vertical_mps=None if vertical == 63 else vertical,
                   altitude_baro_m=altitude(data[13:15]), altitude_geo_m=altitude(data[15:17]),
                   height_m=altitude(data[17:19]), height_reference='ground' if data[1] & 4 else 'takeoff',
                   seconds_after_hour=None if timestamp == 65535 else timestamp/10,
                   horizontal_accuracy=data[19] & 15, vertical_accuracy=data[19] >> 4,
                   speed_accuracy=data[20] & 15, baro_accuracy=data[20] >> 4, time_accuracy=data[23] & 15)
    elif kind == 2:
        page = data[1] & 15
        row.update(auth_type=data[1] >> 4, page=page, signature_verified=False,
                   auth_data=data[8 if page == 0 else 2:].hex())
        if page == 0:
            if data[2] > 15 or data[3] > 17+23*data[2]: raise ValueError('Invalid authentication length')
            row.update(last_page=data[2], length=data[3], timestamp_2019=int.from_bytes(data[4:8], 'little'))
    elif kind == 3: row.update(description_type=data[1], description=text(data[2:25]))
    elif kind == 4:
        row.update(coordinates(data[2:10]), operator_location_type=data[1] & 3, classification=(data[1] >> 2) & 7,
                   area_count=int.from_bytes(data[10:12], 'little'), area_radius_m=data[12]*10,
                   area_ceiling_m=altitude(data[13:15]), area_floor_m=altitude(data[15:17]),
                   eu_category=data[17] >> 4, eu_class=data[17] & 15,
                   operator_altitude_m=altitude(data[18:20]), timestamp_2019=int.from_bytes(data[20:24], 'little'))
    elif kind == 5: row.update(operator_id_type=data[1], operator_id=text(data[2:22]))
    return [row]


def ble_payloads(row):
    value = row.get('service_data', {}).get('0000fffa-0000-1000-8000-00805f9b34fb')
    if value:
        data = bytes.fromhex(value)
        if len(data) >= 2 and data[0] == 0x0d: yield data[2:]


def wifi_payloads(frame):
    body = frame['body']
    if frame['subtype'] in (5,8):
        for kind, value in wifi_ies(body[12:]):
            if kind == 221 and value[:4] == b'\xfa\x0b\xbc\x0d' and len(value) >= 6:
                yield value[5:]
    elif frame['subtype'] == 13 and body[:6] == b'\x04\x09\x50\x6f\x9a\x13':
        offset = 6
        while offset + 3 <= len(body):
            kind, length = body[offset], int.from_bytes(body[offset+1:offset+3], 'little')
            value = body[offset+3:offset+3+length]
            if len(value) != length: return
            offset += 3 + length
            # Service-info present, no optional matching/response/binding fields.
            if kind == 3 and len(value) >= 11 and value[:6] == b'\x88\x69\x19\x9d\x92\x09' and value[8] == 0x10:
                if value[9] == len(value)-10: yield value[11:]
