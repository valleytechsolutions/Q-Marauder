import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from qmarauder import survey_analysis as analysis
from qmarauder.ble_worker import BlueZ
from qmarauder.display import DisplayLink
from qmarauder.display_results import result_page
from qmarauder.service import Service
from qmarauder.storage import Store


def ap(address, **values):
    return dict(address=address, name='Fixture', security='WPA2', band='2.4 GHz', channel=1, signal=50, **values)


class SurveyAnalysisTests(unittest.TestCase):
    def test_channels_separate_same_channel_number_in_different_bands(self):
        first=ap('02:00:00:00:00:01'); second={**first,'address':'02:00:00:00:00:02','band':'6 GHz','signal':90}
        result=analysis.channels([first,second])
        self.assertEqual([(r['band'],r['count'],r['strongest']) for r in result['channels']], [('2.4 GHz',1,50),('6 GHz',1,90)])
        self.assertEqual(analysis.channels([])['channels'],[])
        self.assertIn('not airtime',result['rows'][0]['detail'])

    def test_comparison_needs_baseline_and_tracks_changes_by_bssid(self):
        old=ap('02:00:00:00:00:01'); missing={**old,'address':'02:00:00:00:00:02'}
        current={**old,'security':'Open','channel':6,'signal':64}
        new={**old,'address':'02:00:00:00:00:03'}
        baseline={'networks':[old,missing],'session':'a'*32,'updated':'2026-01-01T00:00:00+00:00'}
        first=analysis.changes([old],None)
        self.assertTrue(first['baseline_created']); self.assertEqual(first['added'],[])
        result=analysis.changes([current,new],baseline)
        self.assertEqual(result['added'],[new]); self.assertEqual(result['not_seen'],[missing])
        self.assertEqual(set(result['changed'][0]['fields']),{'security','channel'})
        self.assertEqual(result['baseline_session'],'a'*32)
        current['signal']=65
        self.assertIn('signal',analysis.changes([current],baseline)['changed'][0]['fields'])
        self.assertEqual(len(analysis.changes([],baseline)['not_seen']),2)
        self.assertEqual(len(analysis.changes([old],{'networks':[]})['added']),1)

    def test_ble_counts_addresses_once_per_service_and_keeps_unknown_ids(self):
        service='0000180f-0000-1000-8000-00805f9b34fb'
        row={'address':'02:00:00:00:00:01','address_type':'random','manufacturer_data':{'ffff':'00'},'uuids':[service,service],'service_data':{service:'01'}}
        result=analysis.advertisements([row])
        self.assertEqual(result['services'],{service:1})
        self.assertEqual(result['companies'],{'ffff':1})
        self.assertEqual(result['address_types'],{'random':1})
        self.assertIn('Company 0xFFFF',[item['title'] for item in result['rows']])
        self.assertEqual(analysis.advertisements([])['devices'],[])

    def test_saved_devices_reads_selected_adapter_without_connecting(self):
        worker=object.__new__(BlueZ); worker.path='/org/bluez/hci1'; worker.adapter=Mock()
        worker.objects=lambda:{
            '/org/bluez/hci0/dev_other':{'org.bluez.Device1':{'Address':'02:00:00:00:00:01'}},
            '/org/bluez/hci1/dev_ours':{'org.bluez.Device1':{'Address':'02:00:00:00:00:02','Alias':'Fixture','Paired':True,'Trusted':False,'Connected':False,'UUIDs':['service']}},
            '/org/bluez/hci1':{'org.bluez.Adapter1':{}}}
        result=worker.saved_devices()['rows']
        self.assertEqual(len(result),1); self.assertTrue(result[0]['paired']); self.assertFalse(result[0]['trusted'])
        self.assertEqual(worker.adapter.mock_calls,[])
        self.assertIn('saved entries',analysis.known_devices(result)['rows'][0]['summary'])

    def test_wifi_baseline_skips_failed_and_unfinished_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            store=Store(directory)
            self.assertIsNone(store.latest_wifi_report())
            first=store.start('wifi-audit'); store.append(first,[dict(state='done',networks=[],session=first)]); store.stop(first)
            failed=store.start('wifi-changes');store.append(failed,[dict(state='error')]);store.stop(failed)
            active=store.start('wifi-channels');store.append(active,[dict(state='done',networks=[ap('02:00:00:00:00:01')])])
            self.assertEqual(store.latest_wifi_report()['session'],first)
            self.assertEqual(len(store.linux_history()),3)

    def test_saved_report_open_does_not_run_radio_and_rejects_wrong_session(self):
        with tempfile.TemporaryDirectory() as directory, patch('qmarauder.radio.diagnostics',return_value={}):
            service=Service(directory)
            try:
                identity=service.store.start('wifi-channels')
                service.store.append(identity,[dict(action='wifi-channels',state='done',rows=[],session=identity)])
                service.store.stop(identity)
                with patch('qmarauder.linux_tools.run') as run:
                    service.submit('linux-open',{'session':identity})
                    self.assertTrue(service.snapshot()['linux_report']['viewing_saved'])
                    self.assertIsNone(service.snapshot()['busy']); run.assert_not_called()
                other=service.store.start('ble');service.store.stop(other)
                for invalid in ('../bad',other,'f'*32):
                    with self.assertRaises(ValueError): service.submit('linux-open',{'session':invalid})
                with self.assertRaises(ValueError): service.submit('linux-open',{'session':identity,'command':'no'})
                service.state['busy']='wifi'
                with self.assertRaises(RuntimeError):service.submit('linux-open',{'session':identity})
            finally: service.close()

    def test_history_protocol_retains_identity_and_deduplicates_retries(self):
        entries=[dict(id=f'{i:032x}',action='wifi-channels',state='done',updated='2026-01-01T00:00:00+00:00') for i in range(6)]
        total,status,payload=result_page({'linux_history':entries},10,1,True)
        self.assertEqual(total,6); self.assertEqual(len(payload.splitlines()),2)
        self.assertEqual(payload.splitlines()[0].split('\t')[3],entries[4]['id'])
        service=Mock(); link=DisplayLink(service,Path('unused'),Mock(return_value=True))
        request='9,59,'+entries[4]['id']
        link.handle_action(request);link.handle_action(request)
        service.submit.assert_called_once_with('linux-open',{'session':entries[4]['id']})
        self.assertEqual(result_page({'linux_history':[]},10,0,True)[0],1)

    def test_interrupted_history_report_is_visible_without_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            store=Store(directory); identity=store.start('ble-summary')
            store=Store(directory)
            self.assertEqual(store.linux_history()[0]['state'],'interrupted')
            self.assertEqual(store.linux_report(identity)['state'],'error')
