"""Small local preferences; all input is validated before persistence."""
import json
from pathlib import Path
from .ble_data import MAC, validate_rules

THEMES = ('BWM', 'Marauder', 'Biscuit Shop', 'Valleytech')
DEFAULTS = dict(theme=0, target='', adapter='hci0', rules=[])


def validate(values):
    if not isinstance(values, dict) or set(values) - set(DEFAULTS):
        raise ValueError('Unknown setting')
    result = dict(values)
    if 'theme' in values and (type(values['theme']) is not int or values['theme'] not in range(4)):
        raise ValueError('Choose one of the four themes')
    if 'target' in values:
        if not isinstance(values['target'], str) or values['target'] and not MAC.fullmatch(values['target']):
            raise ValueError('Select a valid BLE target address')
        result['target'] = values['target'].upper()
    if 'adapter' in values and values['adapter'] not in ('hci0', 'hci1'):
        raise ValueError('Choose hci0 or hci1')
    if 'rules' in values: result['rules'] = validate_rules(values['rules'])
    return result


def load(root):
    try: saved = validate(json.loads((Path(root)/'settings.json').read_text()))
    except (OSError, ValueError, TypeError): saved = {}
    try:
        theme = json.loads((Path(root)/'display-theme.json').read_text())
        if 'theme' not in saved: saved.update(validate({'theme': theme}))
    except (OSError, ValueError, TypeError): pass
    return {**DEFAULTS, **saved}


def save(root, values):
    path = Path(root)/'settings.json'
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(validate(values)), encoding='utf-8')
    temporary.chmod(0o600)
    temporary.replace(path)
