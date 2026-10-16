"""Bounded BlueZ laboratory advertisements with owned-registration cleanup."""
import time

TEST_UUID = 'c0f27d28-8080-42c4-9c13-7c46e5bb0001'


def run(radio):
    import dbus
    import dbus.service
    manager = radio.interface(radio.path, 'org.bluez.LEAdvertisingManager1')
    props = radio.properties(radio.path, 'org.bluez.LEAdvertisingManager1')
    if int(props.get('ActiveInstances',0)) >= int(props.get('SupportedInstances',0)):
        raise RuntimeError('No free BlueZ advertising instance on the selected controller')

    class Advertisement(dbus.service.Object):
        def __init__(self, sequence):
            self.path = '/org/qmarauder/lab/advertisement'+str(sequence)
            self.name = 'QM-LAB-'+str(sequence)
            super().__init__(radio.bus, self.path)

        @dbus.service.method('org.freedesktop.DBus.Properties', in_signature='s', out_signature='a{sv}')
        def GetAll(self, interface):
            if interface != 'org.bluez.LEAdvertisement1': return {}
            return {'Type':'broadcast', 'LocalName':self.name,
                    'ServiceUUIDs':dbus.Array([TEST_UUID], signature='s'), 'Timeout':dbus.UInt16(4)}

        @dbus.service.method('org.bluez.LEAdvertisement1', in_signature='', out_signature='')
        def Release(self): pass

    registered = 0
    started = time.monotonic()
    for sequence in range(1,4):
        advertisement = Advertisement(sequence)
        result = []
        try:
            manager.RegisterAdvertisement(advertisement.path, dbus.Dictionary({}, signature='sv'),
                reply_handler=lambda: result.append(True), error_handler=lambda exc: result.append(str(exc)), timeout=5)
            radio.pump(6, until=lambda:bool(result))
            if not result or result[0] is not True:
                raise RuntimeError(str(result[0]) if result else 'Advertising registration timed out')
            registered += 1
            radio.pump(2)
        finally:
            # Unregister even after timeout; BlueZ might have completed registration
            # after the last event dispatch. Bus disconnect is a final cleanup net.
            try: manager.UnregisterAdvertisement(advertisement.path, timeout=3)
            except dbus.exceptions.DBusException: pass
            advertisement.remove_from_connection()
    return dict(registered=registered, seconds=round(time.monotonic()-started,2), rf_verified=False,
        note='Three QM-LAB test names advertised for two seconds each, then removed. Registration confirms controller acceptance; use a second receiver to verify RF. No platform popup or crash payloads.')
