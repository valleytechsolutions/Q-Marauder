import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from qmarauder import ble, settings
from qmarauder.ble_data import decode, detections, proximity, uuid, validate_rules
from qmarauder.ble_worker import BlueZ

TARGET='00:11:22:33:44:55'


class BLETests(unittest.TestCase):
    def test_metadata_does_not_claim_packet_boundaries_or_verified_identity(self):
        row=decode(dict(address=TARGET,uuids=[uuid('1812')],manufacturer_data={'004c':'0215'+'00'*21}))
        self.assertEqual(row['signals'],['HID','Apple','iBeacon format'])
        self.assertFalse(row['identity_verified'])
        self.assertIn('boundaries unavailable',row['metadata_source'])

    def test_watchlists_use_public_oui_only_and_match_service_data(self):
        rules=validate_rules([dict(label='Vendor',kind='oui',value='00:11:22'),dict(label='Battery',kind='service',value='180F')])
        row=dict(address=TARGET,name='fixture',address_type='random',service_data={uuid('180f'):'64'})
        hits=detections([row],rules)
        self.assertEqual(hits[0]['matches'],['Battery (service)'])
        row['address_type']='public'
        self.assertEqual(len(detections([row],rules)[0]['matches']),2)
        self.assertIn('not verified',hits[0]['note'])

    def test_rules_and_parameters_are_bounded_and_no_shell_paths_accepted(self):
        prefs={**settings.DEFAULTS,'target':TARGET}
        for parameters in ([],{'path':'/org/bluez'}, {'uuid':'../../'}, {'uuid':'2a19','value':'f'}, {'uuid':'2a19','value':'ff'*513}):
            with self.assertRaises(ValueError): ble.request_for('ble-write',prefs,parameters)
        with self.assertRaises(ValueError): ble.request_for('ble-gatt',settings.DEFAULTS)
        with self.assertRaises(ValueError): validate_rules([dict(label='x',kind='name',value='x')]*33)
        request=ble.request_for('ble-write',prefs,dict(uuid='2A19',value='01ff',write_type='command'))
        self.assertEqual(request['uuid'],uuid('2a19'))
        self.assertEqual(request['target'],TARGET)

    def test_signal_is_unknown_without_fresh_samples_and_zero_is_valid(self):
        self.assertIsNone(proximity([])['latest'])
        self.assertEqual(proximity([{'rssi':0}])['latest'],0)
        self.assertEqual(proximity([{'rssi':v} for v in (-80,-79,-78,-60,-60,-59)])['trend'],'Stronger signal')

    def test_settings_upgrade_persists_theme_and_rejects_types(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory,'display-theme.json').write_text('3')
            self.assertEqual(settings.load(directory)['theme'],3)
            settings.save(directory,{**settings.DEFAULTS,'theme':1})
            self.assertEqual(settings.load(directory)['theme'],1)
            with self.assertRaises(ValueError): settings.validate({'theme':True})
            with self.assertRaises(ValueError): settings.validate({'target':'$(anything)'})

    def test_foreign_connection_is_not_disconnected(self):
        worker=BlueZ.__new__(BlueZ)
        worker.path='/org/bluez/hci0';worker.scanning=False;worker.owned_connection=None
        worker.bus=Mock();worker.interface=Mock()
        worker.objects=Mock(return_value={worker.path+'/dev_'+TARGET.replace(':','_'): {}})
        worker.properties=Mock(return_value={'Connected':True})
        with self.assertRaisesRegex(RuntimeError,'already connected'): worker.connect(TARGET)
        worker.close()
        worker.interface.assert_not_called()
        worker.bus.close.assert_called_once()

    def test_failed_connect_is_owned_for_cleanup(self):
        worker=BlueZ.__new__(BlueZ)
        worker.path='/org/bluez/hci0';worker.scanning=False;worker.owned_connection=None
        path=worker.path+'/dev_'+TARGET.replace(':','_')
        worker.bus=Mock();worker.objects=Mock(return_value={path:{}})
        worker.properties=Mock(return_value={'Connected':False})
        device=Mock();device.Connect.side_effect=RuntimeError('link failed')
        worker.interface=Mock(return_value=device)
        with self.assertRaisesRegex(RuntimeError,'link failed'): worker.connect(TARGET)
        worker.close();device.Disconnect.assert_called_once()

    def test_duplicate_characteristic_uuid_refuses_ambiguous_write(self):
        worker=BlueZ.__new__(BlueZ);worker.connect=Mock(return_value='/target')
        worker.interface=Mock()
        service={'org.bluez.GattService1':{'UUID':uuid('180f'),'Primary':True}}
        char={'org.bluez.GattCharacteristic1':{'UUID':uuid('2a19'),'Service':'/target/service','Flags':['write']}}
        worker.objects=Mock(return_value={'/target/service':service,'/target/a':char,'/target/b':char})
        with self.assertRaisesRegex(RuntimeError,'exactly one'):
            worker.gatt('ble-write',{'target':TARGET,'uuid':uuid('2a19'),'value':'00'})
        worker.interface.assert_not_called()

    def test_notification_failure_still_unsubscribes(self):
        worker=BlueZ.__new__(BlueZ);worker.connect=Mock(return_value='/target')
        worker.dbus=Mock();worker.dbus.Dictionary=lambda *args,**kw: {}
        worker.bus=Mock();worker.interface=Mock();worker.pump=Mock(side_effect=RuntimeError('interrupted'))
        char={'org.bluez.GattCharacteristic1':{'UUID':uuid('2a19'),'Service':'/target/service','Flags':['notify']}}
        worker.objects=Mock(return_value={'/target/a':char})
        with self.assertRaisesRegex(RuntimeError,'interrupted'):
            worker.gatt('ble-notify',{'target':TARGET,'uuid':uuid('2a19')})
        worker.interface.return_value.StopNotify.assert_called_once()
        worker.bus.add_signal_receiver.return_value.remove.assert_called_once()


if __name__=='__main__': unittest.main()
