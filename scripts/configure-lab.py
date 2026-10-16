"""Interactive, unprivileged local profile builder. Never publish its output."""
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from qmarauder.lab_helper import split_fields, validate_profile


def choose(items, prompt):
    for index,item in enumerate(items,1): print(f'{index}. {item}')
    value=input(prompt+' (number, or Enter to cancel): ').strip()
    if not value: raise SystemExit('Cancelled; profile unchanged.')
    if not value.isdecimal() or not 1 <= int(value) <= len(items): raise SystemExit('Invalid selection; profile unchanged.')
    return int(value)-1


def main():
    interfaces=sorted(p.name for p in Path('/sys/class/net').iterdir() if (p/'phy80211').exists() and p.name!='qmmon')
    if not interfaces: raise SystemExit('No Wi-Fi interfaces. Attach your radio first.')
    print('Select the radio for capture and scoped transmit tests. A separate monitor-capable USB radio is recommended.')
    interface=interfaces[choose(interfaces,'Radio')]
    result=subprocess.run(['nmcli','--terse','--escape','yes','--fields','BSSID,SSID,FREQ','device','wifi','list','ifname',interface,'--rescan','yes'],capture_output=True,text=True,timeout=30)
    if result.returncode: raise SystemExit('Wi-Fi scan failed: '+result.stderr[:300])
    rows=[]
    for line in result.stdout.splitlines():
        fields=split_fields(line)
        if len(fields)==3 and fields[1]: rows.append(fields)
    if not rows: raise SystemExit('No named access points found. Check radio and scan again.')
    selected=rows[choose([f'{name} / {address} / {freq}' for address,name,freq in rows],'Your authorized test AP')]
    address,ssid,_=selected
    print('Only this exact BSSID and SSID will be allowed for active Wi-Fi tests.')
    if input('Type LAB to save this owned/authorized target: ').strip()!='LAB': raise SystemExit('Cancelled; profile unchanged.')
    profile=validate_profile(dict(interface=interface,ssid=ssid,bssids=[address]))
    path=Path.home()/'.local/share/q-marauder/lab-profile.json'
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(profile));temporary.chmod(0o600);temporary.replace(path)
    print('Local profile saved. The setup launcher will install it with administrator permissions.')

if __name__=='__main__': main()
