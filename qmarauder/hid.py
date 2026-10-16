"""Bounded HID report-descriptor parser, independently implemented from USB HID 1.11.

Reports are observations of the selected peripheral; no OS keyboard events are sent.
"""


def descriptor(data):
    if not isinstance(data, bytes) or len(data) > 4096:
        raise ValueError('HID report map must contain at most 4096 bytes')
    fields, offsets, stack, warnings = [], {}, [], []
    state = dict(page=0, size=0, count=0, report=0, minimum=0, maximum=0)
    usages, low, high, pos, depth = [], None, None, 0, 0
    while pos < len(data):
        prefix = data[pos]; pos += 1
        if prefix == 0xfe:
            if pos + 2 > len(data): raise ValueError('Truncated HID long item')
            length = data[pos]; pos += 2
            if pos + length > len(data): raise ValueError('Truncated HID long payload')
            pos += length; warnings.append('Long item skipped'); continue
        size = (0, 1, 2, 4)[prefix & 3]
        if pos + size > len(data): raise ValueError('Truncated HID item')
        raw = data[pos:pos + size]; pos += size
        value = int.from_bytes(raw, 'little')
        tag, kind = prefix >> 4, (prefix >> 2) & 3
        if kind == 1:
            if tag in (0, 7, 8, 9): state[{0:'page',7:'size',8:'report',9:'count'}[tag]] = value
            elif tag == 1: state['minimum'] = int.from_bytes(raw, 'little', signed=True)
            elif tag == 2: state['maximum'] = int.from_bytes(raw, 'little', signed=state['minimum'] < 0)
            elif tag == 10:
                if len(stack) >= 16: raise ValueError('HID global stack too deep')
                stack.append(dict(state))
            elif tag == 11:
                if not stack: raise ValueError('HID global stack underflow')
                state = stack.pop()
            if tag == 8 and not 1 <= value <= 255: raise ValueError('Invalid HID report ID')
        elif kind == 2:
            if tag == 0:
                if len(usages) >= 256: raise ValueError('Too many HID usages')
                usages.append(value)
            elif tag == 1: low = value
            elif tag == 2: high = value
        elif kind == 0:
            if tag in (8, 9, 11):
                report_kind = {8:'input',9:'output',11:'feature'}[tag]
                key = (state['report'], report_kind)
                bits = state['size'] * state['count']
                if state['size'] > 32 or state['count'] > 256 or offsets.get(key, 0) + bits > 8192:
                    raise ValueError('HID report exceeds decoder bounds')
                if len(fields) >= 256: raise ValueError('Too many HID fields')
                fields.append({**state, 'kind':report_kind, 'offset':offsets.get(key, 0),
                               'flags':value, 'usages':usages[:], 'usage_min':low, 'usage_max':high})
                offsets[key] = offsets.get(key, 0) + bits
            elif tag == 10:
                depth += 1
                if depth > 32: raise ValueError('HID collections too deep')
            elif tag == 12:
                depth -= 1
                if depth < 0: raise ValueError('HID collection underflow')
            usages, low, high = [], None, None
    if depth or stack: warnings.append('Unclosed HID collection or global stack')
    return dict(fields=fields, warnings=warnings,
                reports=[dict(id=key[0], kind=key[1], bytes=(bits+7)//8) for key,bits in offsets.items()])


def report(layout, data, report_id=0, kind='input'):
    """BLE Report Reference supplies report_id; BLE values omit the ID byte."""
    result, keyboard = [], []
    integer = int.from_bytes(data, 'little')
    fields = [f for f in layout['fields'] if f['report'] == report_id and f['kind'] == kind]
    if not fields: raise ValueError('No matching HID report layout')
    for f in fields:
        if f['offset'] + f['size'] * f['count'] > len(data)*8:
            raise ValueError('Truncated HID report')
        if f['flags'] & 1: continue  # Constant padding.
        for index in range(f['count']):
            value = (integer >> (f['offset'] + index*f['size'])) & ((1 << f['size'])-1)
            if f['minimum'] < 0 and f['size'] and value & (1 << (f['size']-1)): value -= 1 << f['size']
            variable = bool(f['flags'] & 2)
            usage_index = index if variable else value-f['minimum']
            usage = None
            if usage_index >= 0:
                if f['usages'] and (variable or usage_index < len(f['usages'])):
                    usage = f['usages'][min(usage_index,len(f['usages'])-1)]
                elif f['usage_min'] is not None and f['usage_max'] is not None:
                    candidate = f['usage_min'] + usage_index
                    if variable or candidate <= f['usage_max']: usage = min(candidate, f['usage_max'])
            page = usage >> 16 if usage is not None and usage > 0xffff else f['page']
            usage = usage & 0xffff if usage is not None else None
            result.append(dict(page=page, usage=usage, value=value, relative=bool(f['flags'] & 4)))
            if page == 7 and value and usage: keyboard.append(usage)
    return dict(report_id=report_id, fields=result, keyboard_usages=keyboard,
                note='Usage IDs only; no keyboard injection or locale-dependent text inference.')
