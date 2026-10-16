import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock, patch
from qmarauder import linux_tools
from qmarauder.ble_worker import BlueZ
from qmarauder.display import DisplayLink
from qmarauder.display_results import result_page
from qmarauder.native_app import same_origin
from qmarauder.service import Service


class LinuxToolTests(unittest.TestCase):
    def test_survey_separates_owe_unknown_and_security_changes(self):
        networks = [dict(name=name, security=security, address=f'02:00:00:00:00:{i:02x}', band='2.4 GHz', channel=1, signal=50)
                    for i,(name,security) in enumerate([('lab','WPA2'),('lab','WPA2 WPA3'),('guest','OWE'),('','Open'),('unknown','?'),('legacy','WEP')])]
        report = linux_tools.wifi_summary(networks)
        self.assertEqual(report['security'], {'WPA2':1,'WPA2/WPA3':1,'OWE':1,'Open':1,'Unknown':1,'WEP':1})
        self.assertEqual(report['mixed_security_names'], ['lab'])
        self.assertEqual(report['channels'], {'2.4 GHz / CH 1':6})
        self.assertIn('does not establish an evil twin', report['rows'][2]['detail'])
        self.assertEqual(linux_tools.wifi_summary([])['security'], {})

    def test_controller_properties_are_read_without_power_changes(self):
        listing='Controller 02:00:00:00:00:01 Test [default]\nController not-a-mac invalid'
        body='Controller 02:00:00:00:00:01\n\tAlias: Test\n\tPowered: no\n\tPairable: yes\n\tRoles: central\n\tRoles: peripheral'
        with patch('qmarauder.radio.run', side_effect=[listing,body]) as run:
            report=linux_tools.controllers()
        self.assertEqual(report['controllers'][0]['powered'],'no')
        self.assertEqual(report['controllers'][0]['roles'],'central, peripheral')
        self.assertEqual(run.call_args_list[1].args[0],['bluetoothctl','show','02:00:00:00:00:01'])
        with self.assertRaises(RuntimeError): linux_tools.parse_controller('No controller available','')

    def test_interface_snapshot_does_not_include_wired_devices(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/'wlan0/wireless').mkdir(parents=True); (root/'eth0').mkdir()
            with patch('qmarauder.radio.run',return_value='[{"ifname":"wlan0","addr_info":[{"local":"192.0.2.1"}]}]'):
                result=linux_tools.interfaces(root)
        self.assertEqual(len(result['interfaces']),1)
        self.assertEqual(result['interfaces'][0]['addresses'],['192.0.2.1'])
        self.assertEqual(result['interfaces'][0]['rx_bytes'],'unknown')

    def test_classic_scan_requests_bredr_and_releases_its_discovery(self):
        worker=object.__new__(BlueZ); worker.path='/org/bluez/hci1'; worker.scanning=False
        worker.dbus=Mock(Dictionary=lambda value,**_:value,Boolean=bool)
        worker.adapter=Mock(); worker.bus=Mock(); worker.objects=lambda:{}
        worker.pump=Mock(side_effect=RuntimeError('fixture failure'))
        with self.assertRaisesRegex(RuntimeError,'fixture failure'): worker.scan(8,transport='bredr')
        self.assertEqual(worker.adapter.SetDiscoveryFilter.call_args.args[0]['Transport'],'bredr')
        worker.adapter.StopDiscovery.assert_called_once()
        self.assertFalse(worker.scanning)
        self.assertEqual(worker.bus.add_signal_receiver.return_value.remove.call_count,2)

    def test_classic_action_uses_selected_adapter_without_gatt_target(self):
        with patch('qmarauder.ble.call',return_value={'rows':[]}) as call:
            report=linux_tools.run('bt-classic',{'adapter':'hci1','target':'02:00:00:00:00:01'})
        call.assert_called_once_with({'action':'bt-classic','adapter':'hci1','target':''})
        self.assertEqual(report['devices'],[])
        self.assertIn('0 fresh',report['rows'][0]['summary'])
        with self.assertRaises(ValueError): linux_tools.run('arbitrary-shell',{})

    def test_linux_reports_paginate_and_sanitize_radio_text(self):
        report={'rows':[linux_tools.card('name\t\n'+str(i),'s'*80,'d'*250) for i in range(6)]}
        total,_,payload=result_page({'linux_report':report},8,0,True)
        self.assertEqual(total,6); self.assertEqual(len(payload.splitlines()),4)
        self.assertLessEqual(len(payload),1047)
        self.assertTrue(all(len(line.split('\t'))==4 for line in payload.splitlines()))
        self.assertEqual(len(result_page({'linux_report':report},8,1,True)[2].splitlines()),2)
        link=DisplayLink(Mock(),Path('unused'),Mock(return_value=True))
        link.handle_action('1,51');link.handle_action('1,51')
        link.service.submit.assert_called_once_with('bt-classic')

    def test_report_persists_without_repeating_job_after_restart(self):
        with tempfile.TemporaryDirectory() as directory, patch('qmarauder.radio.diagnostics',return_value={}), patch('qmarauder.linux_tools.run',return_value={'state':'done','kind':'linux-tool','action':'bt-controllers','rows':[]}) as run:
            service=Service(directory)
            try:
                service.submit('bt-controllers')
                deadline=time.monotonic()+3
                while service.snapshot()['busy'] and time.monotonic()<deadline: time.sleep(.01)
                report=service.snapshot()['linux_report']
                self.assertEqual(json.loads(service.store.export(report['session'],'json'))[0]['action'],'bt-controllers')
            finally: service.close()
            service=Service(directory)
            try:
                self.assertEqual(service.snapshot()['linux_report']['state'],'done')
                self.assertEqual(service.snapshot()['updated'], report['updated'])
                self.assertIsNone(service.snapshot()['busy']);run.assert_called_once()
            finally: service.close()

    def test_desktop_origin_rejects_external_and_credential_urls(self):
        home='http://127.0.0.1:8787/?desktop=1'
        self.assertTrue(same_origin('http://127.0.0.1:8787/api/export/example.json',home))
        for candidate in ('https://example.com','file:///etc/passwd','http://127.0.0.1:8788/',
                          'http://user@127.0.0.1:8787/','http://127.0.0.1:bad/','javascript:alert(1)'):
            self.assertFalse(same_origin(candidate,home))

    def test_portrait_inventory_is_status_only_and_filters_non_wireless_entries(self):
        state={'features':[{'name':'Example','status':'planned','detail':'Not ported','category':'Raspyjack / Wi-Fi'},
                           {'name':'Other','status':'planned','detail':'Unrelated','category':'Device'}]}
        total,status,payload=result_page(state,9,0,True)
        self.assertEqual(total,1)
        self.assertIn('not a tool launcher',status)
        self.assertEqual(payload,'Example\tPLANNED\tNot ported\t')
