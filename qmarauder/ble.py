"""Validated entry to the separate D-Bus process."""
import json
import re
import subprocess
import sys
from .ble_data import uuid
from .settings import validate

ACTIONS = ('ble-detect', 'ble-foxhunt', 'ble-gatt', 'ble-read', 'ble-write', 'ble-notify', 'ble-pair')


def request_for(action, preferences, parameters=None):
    parameters = {} if parameters is None else parameters
    if not isinstance(parameters, dict) or set(parameters) - {'uuid','value','write_type'}:
        raise ValueError('Unknown BLE parameters')
    if action not in ('ble', *ACTIONS): raise ValueError('Unknown BLE action')
    validate({k: preferences[k] for k in ('target','adapter')})
    if action not in ('ble','ble-detect') and not preferences['target']:
        raise ValueError('Select your BLE test device in Settings first')
    result = dict(action=action, adapter=preferences['adapter'], target=preferences['target'])
    if action in ('ble-read','ble-write','ble-notify'):
        result['uuid'] = uuid(parameters.get('uuid', ''))
    if action == 'ble-write':
        value = parameters.get('value', '')
        if not isinstance(value, str) or not re.fullmatch(r'(?:[0-9a-fA-F]{2}){1,512}', value):
            raise ValueError('Write value must be 1–512 bytes of hexadecimal')
        mode = parameters.get('write_type', 'request')
        if mode not in ('request','command'): raise ValueError('Unknown write type')
        result.update(value=value, write_type=mode)
    return result


def call(request):
    process = subprocess.Popen([sys.executable, '-m', 'qmarauder.ble_worker'], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        output, errors = process.communicate(json.dumps(request), timeout=56)
    except subprocess.TimeoutExpired:
        process.terminate()
        try: process.communicate(timeout=7)
        except subprocess.TimeoutExpired:
            process.kill(); process.communicate()
        raise RuntimeError('BLE worker timed out; inspect the target connection before retrying')
    try: result = json.loads(output)
    except ValueError: raise RuntimeError('BLE worker did not return a valid result') from None
    if process.returncode or result.get('error'):
        raise RuntimeError(result.get('error', 'BLE worker failed'))
    return result
