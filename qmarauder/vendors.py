"""OUI lookup from the same Wireshark MA-L data source used by ChimeraBLE.

The registry is installed separately; this module contains no upstream table or code.
Random/private/local addresses never receive an IEEE vendor attribution.
"""
from functools import lru_cache
import json
from pathlib import Path
import re

SOURCE = 'https://www.wireshark.org/download/automated/data/manuf'
DATABASE = Path.home()/'.local/share/q-marauder/vendors/oui.json'


def parse_manuf(text):
    result = {}
    for line in text.splitlines():
        columns = line.split('\t')
        if len(columns) < 2: continue
        prefix = columns[0].strip().upper()
        if not re.fullmatch(r'(?:[0-9A-F]{2}:){2}[0-9A-F]{2}', prefix): continue
        name = (columns[2].strip() if len(columns) > 2 else '') or columns[1].strip()
        if name and len(name) <= 256 and not any(ord(c) < 32 for c in name): result[prefix] = name
    return result


@lru_cache(maxsize=1)
def database():
    try:
        if DATABASE.stat().st_size > 8_000_000: return {}
        payload = json.loads(DATABASE.read_text(encoding='utf-8'))
        entries = payload['entries']
        if not isinstance(entries, dict) or len(entries) > 100000: return {}
        if any(not re.fullmatch(r'(?:[0-9A-F]{2}:){2}[0-9A-F]{2}', k) or not isinstance(v,str) or len(v)>256 for k,v in entries.items()): return {}
        return payload
    except (OSError, ValueError, KeyError, TypeError): return {}


def status():
    db = database()
    return dict(available=bool(db), entries=len(db.get('entries', {})), source=db.get('source', SOURCE),
                sha256=db.get('sha256'), updated=db.get('updated'), scope='MA-L /24; same source and prefix selection as ChimeraBLE')


def lookup(address, address_type='public'):
    if not isinstance(address,str) or not re.fullmatch(r'(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}',address): return None
    if address_type != 'public' or int(address[:2],16) & 3 or address == '00:00:00:00:00:00': return None
    return database().get('entries', {}).get(address[:8].upper())
