"""Isolated BlueZ D-Bus jobs. No pairing, adapter resets or foreign connections changed."""
import json
import signal
import sys
import time
from .ble_data import decode, proximity, uuid
from .settings import validate


def plain(value):
    if isinstance(value, dict): return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return [plain(v) for v in value]
    if isinstance(value, str): return str(value)
    if isinstance(value, (int, float)): return int(value)
    return str(value)


class BlueZ:
    def __init__(self, adapter):
        try:
            import dbus
            from dbus.mainloop.glib import DBusGMainLoop
            from gi.repository import GLib
        except ImportError as exc:
            raise RuntimeError('BLE Lab needs python3-dbus and python3-gi. See docs/BLE.md.') from exc
        self.dbus, self.GLib = dbus, GLib
        DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SystemBus(private=True)
        self.path = '/org/bluez/' + adapter
        self.manager = self.interface('/', 'org.freedesktop.DBus.ObjectManager')
        self.adapter = self.interface(self.path, 'org.bluez.Adapter1')
        self.scanning = False
        self.owned_connection = None
        objects = self.objects()
        if self.path not in objects or not objects[self.path].get('org.bluez.Adapter1', {}).get('Powered'):
            raise RuntimeError(f'{adapter} is absent or powered off')

    def interface(self, path, name):
        return self.dbus.Interface(self.bus.get_object('org.bluez', path), name)

    def objects(self):
        return self.manager.GetManagedObjects(timeout=5)

    def properties(self, path, name):
        return self.interface(path, 'org.freedesktop.DBus.Properties').GetAll(name, timeout=5)

    def pump(self, duration, until=None):
        deadline = time.monotonic() + duration
        context = self.GLib.MainContext.default()
        while time.monotonic() < deadline:
            for _ in range(100):
                if not context.pending(): break
                context.iteration(False)
            if until and until(): return
            time.sleep(.025)

    def row(self, properties):
        return decode(dict(kind='ble', address=str(properties['Address']).upper(),
            address_type=str(properties.get('AddressType', 'unknown')),
            name=str(properties.get('Name', ''))[:248],
            rssi=int(properties['RSSI']) if 'RSSI' in properties else None,
            tx_power=int(properties['TxPower']) if 'TxPower' in properties else None,
            appearance=int(properties['Appearance']) if 'Appearance' in properties else None,
            uuids=[str(u).lower() for u in properties.get('UUIDs', [])][:64],
            manufacturer_data={f'{int(k):04x}': bytes(v).hex()[:2048] for k,v in properties.get('ManufacturerData', {}).items()},
            service_data={str(k).lower(): bytes(v).hex()[:2048] for k,v in properties.get('ServiceData', {}).items()}))

    def scan(self, seconds=8, target=''):
        cached = {str(p): dict(v.get('org.bluez.Device1', {})) for p,v in self.objects().items() if str(p).startswith(self.path+'/dev_')}
        seen, samples = {}, []
        started = time.monotonic()
        def changed(interface, values, invalidated, path=None):
            path = str(path)
            if interface != 'org.bluez.Device1' or not path.startswith(self.path+'/dev_'): return
            props = cached.setdefault(path, {})
            props.update(values)
            for key in invalidated: props.pop(str(key), None)
            if 'Address' not in props or not any(key in values for key in ('RSSI','ManufacturerData','ServiceData','Name','UUIDs')): return
            row = self.row(props)
            if target and row['address'] != target: return
            if len(seen) < 500 or row['address'] in seen: seen[row['address']] = row
            if 'RSSI' in values and len(samples) < 1000:
                samples.append(dict(seconds=round(time.monotonic()-started, 2), rssi=int(values['RSSI'])))
        def added(path, interfaces):
            if 'org.bluez.Device1' in interfaces: changed('org.bluez.Device1', interfaces['org.bluez.Device1'], [], path)
        handles = [self.bus.add_signal_receiver(changed, signal_name='PropertiesChanged', dbus_interface='org.freedesktop.DBus.Properties', path_keyword='path'),
                   self.bus.add_signal_receiver(added, signal_name='InterfacesAdded', dbus_interface='org.freedesktop.DBus.ObjectManager')]
        try:
            self.adapter.SetDiscoveryFilter(self.dbus.Dictionary({'Transport':'le', 'DuplicateData':self.dbus.Boolean(True)}, signature='sv'), timeout=5)
            self.adapter.StartDiscovery(timeout=5)
            self.scanning = True
            self.pump(seconds)
        finally:
            for handle in handles: handle.remove()
            if self.scanning:
                self.adapter.StopDiscovery(timeout=5)
                self.scanning = False
        rows = sorted(seen.values(), key=lambda row: row['rssi'] if row['rssi'] is not None else -999, reverse=True)
        return dict(rows=rows, **proximity(samples))

    def connect(self, address):
        path = self.path+'/dev_'+address.replace(':', '_')
        if path not in self.objects(): self.scan(5, address)
        if path not in self.objects(): raise RuntimeError('Target not observed on this adapter; scan and select it again')
        props = self.properties(path, 'org.bluez.Device1')
        if props.get('Connected'): raise RuntimeError('Target is already connected; disconnect its existing session before using BLE Lab')
        self.owned_connection = path
        self.interface(path, 'org.bluez.Device1').Connect(timeout=15)
        self.pump(12, lambda: bool(self.properties(path, 'org.bluez.Device1').get('ServicesResolved')))
        if not self.properties(path, 'org.bluez.Device1').get('ServicesResolved'):
            raise RuntimeError('GATT services did not resolve; pairing may be required on the device')
        return path

    def gatt(self, action, request):
        path = self.connect(request['target'])
        objects = self.objects()
        services, characteristics = [], []
        for key, interfaces in objects.items():
            if not str(key).startswith(path+'/'): continue
            if 'org.bluez.GattService1' in interfaces:
                p = interfaces['org.bluez.GattService1']
                services.append(dict(uuid=str(p['UUID']), primary=bool(p['Primary'])))
            if 'org.bluez.GattCharacteristic1' in interfaces:
                p = interfaces['org.bluez.GattCharacteristic1']
                service = objects.get(p['Service'], {}).get('org.bluez.GattService1', {})
                characteristics.append(dict(path=str(key), uuid=str(p['UUID']), service=str(service.get('UUID', '')),
                                            flags=[str(f) for f in p['Flags']], handle=int(p.get('Handle', 0))))
        if len(characteristics) > 256: raise RuntimeError('GATT table exceeds this alpha limit of 256 characteristics')
        result = dict(services=services, characteristics=characteristics, notifications=[])
        selected = [c for c in characteristics if c['uuid'].lower() == request.get('uuid', '').lower()]
        if action != 'ble-gatt':
            if len(selected) != 1: raise RuntimeError('Characteristic UUID must identify exactly one characteristic in this target')
            c = selected[0]
            interface = self.interface(c['path'], 'org.bluez.GattCharacteristic1')
            options = self.dbus.Dictionary({}, signature='sv')
            if action == 'ble-read':
                c['value'] = bytes(interface.ReadValue(options, timeout=5)).hex()
            elif action == 'ble-write':
                mode = request.get('write_type', 'request')
                flag = 'write' if mode == 'request' else 'write-without-response'
                if flag not in c['flags']: raise RuntimeError('Characteristic does not support this write type')
                options['type'] = mode
                interface.WriteValue(self.dbus.Array(bytes.fromhex(request['value']), signature='y'), options, timeout=5)
                c['write_completed'] = True
            elif action == 'ble-notify':
                events = result['notifications']
                def notification(iface, values, invalidated):
                    if iface == 'org.bluez.GattCharacteristic1' and 'Value' in values and len(events) < 256:
                        events.append(dict(time=time.time(), uuid=c['uuid'], value=bytes(values['Value']).hex()[:4096]))
                handle = self.bus.add_signal_receiver(notification, signal_name='PropertiesChanged', dbus_interface='org.freedesktop.DBus.Properties', path=c['path'])
                subscribed = False
                try:
                    interface.StartNotify(timeout=5); subscribed = True
                    self.pump(10)
                finally:
                    handle.remove()
                    if subscribed: interface.StopNotify(timeout=5)
            result['selected'] = c
        # Public clients use UUIDs, never arbitrary D-Bus object paths.
        for c in characteristics: c.pop('path', None)
        return result

    def close(self):
        try:
            if self.scanning: self.adapter.StopDiscovery(timeout=5)
            if self.owned_connection:
                self.interface(self.owned_connection, 'org.bluez.Device1').Disconnect(timeout=5)
        finally: self.bus.close()


def main():
    radio = None
    def stop(*_): raise RuntimeError('BLE job stopped or timed out')
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGALRM, stop)
    signal.alarm(50)
    try:
        request = json.loads(sys.stdin.read(8193))
        validate({k: request[k] for k in ('target','adapter')})
        action = request['action']
        radio = BlueZ(request['adapter'])
        if action in ('ble', 'ble-detect', 'ble-foxhunt'):
            result = radio.scan(20 if action == 'ble-foxhunt' else 8, request['target'] if action == 'ble-foxhunt' else '')
        elif action in ('ble-gatt','ble-read','ble-write','ble-notify'):
            result = radio.gatt(action, request)
        else: raise ValueError('Unknown BLE action')
        result.update(action=action, state='done', kind='ble-lab', address=request['target'],
                      note='BlueZ discovery may transmit scan requests. GATT jobs disconnect their own connection on completion.')
        radio.close(); radio = None
        print(json.dumps(result))
    except Exception as exc:
        if radio:
            try: radio.close()
            except Exception: pass
        print(json.dumps({'error': str(exc)[:300]}))
        sys.exit(1)


if __name__ == '__main__': main()
