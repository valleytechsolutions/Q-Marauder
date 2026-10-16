"""Install the same /24 OUI registry source used by ChimeraBLE, without copying its GPL code."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys
from urllib.request import urlopen

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from qmarauder.vendors import SOURCE, DATABASE, parse_manuf

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source',type=Path,help='Use an existing Wireshark manuf text file offline')
parser.add_argument('--output',type=Path,default=DATABASE)
parser.add_argument('--if-missing',action='store_true')
args=parser.parse_args()
if args.if_missing and args.output.is_file():
    print('OUI database already installed; keeping the existing registry.'); sys.exit(0)
if args.source:
    raw=args.source.read_bytes()
else:
    with urlopen(SOURCE,timeout=35) as response: raw=response.read(12_000_001)
if len(raw)>12_000_000: raise SystemExit('Registry exceeds 12 MB input limit')
entries=parse_manuf(raw.decode('utf-8'))
if len(entries)<10000: raise SystemExit('Registry is incomplete; previous database kept')
args.output.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
result=dict(source=SOURCE,sha256=hashlib.sha256(raw).hexdigest(),updated=dt.datetime.now(dt.timezone.utc).isoformat(),
            reference='https://github.com/MatthewKuKanich/ChimeraBLE/blob/2330423dae8f8fa163617172310784889d8972a7/tools/make_oui_bin.py',
            entries=entries)
temporary=args.output.with_suffix('.tmp')
temporary.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True),encoding='utf-8')
temporary.chmod(0o600);temporary.replace(args.output)
print(f'Installed {len(entries)} MA-L OUI prefixes. Source SHA256: {result["sha256"]}')
