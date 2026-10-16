import io
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import Mock, patch
from qmarauder import capture, lab_helper, packets, remote_id
from qmarauder.display_results import result_page


def legacy(data, address=bytes.fromhex('001122334455'), address_type=0):
    payload=b'\x02\x01\x00'+bytes([address_type])+address[::-1]+bytes([len(data)])+data+b'\xd8'
    return b'\x04\x3e'+bytes([len(payload)])+payload


def pcap(link, records):
    raw=bytearray(struct.pack('<IHHIIII',0xa1b2c3d4,2,4,0,0,4096,link))
    for packet in records: raw.extend(struct.pack('<IIII',100,0,len(packet),len(packet))+packet)
    return raw


class PacketTests(unittest.TestCase):
    def test_hci_packet_boundary_meta_match_never_combines_scan_responses(self):
        company=bytes.fromhex('03ff530d'); service=bytes.fromhex('03035ffd')
        separate=pcap(201,[b'\0\0\0\1'+legacy(data) for data in (company,service)])
        self.assertFalse(capture.analyze(separate,'packet-detector')['detections'])
        combined=pcap(201,[b'\0\0\0\1'+legacy(company+service)])
        hits=capture.analyze(combined,'packet-detector')['detections']
        self.assertEqual(len(hits),1); self.assertIn('same advertising report',hits[0]['matches'][0])

    def test_flock_requires_specific_evidence_not_module_vendor(self):
        row=dict(address='B4:1E:52:11:22:33',address_type='random',name='',manufacturer_data={'09c8':'00'},uuids=[])
        self.assertFalse(capture.match_ble(row))
        self.assertTrue(capture.match_ble({**row,'address_type':'public'}))
        self.assertTrue(capture.match_ble({**row,'name':'Penguin-1234567890'}))
        self.assertFalse(capture.match_ble({**row,'name':'Penguin-123'}))
        self.assertTrue(capture.match_ble({**row,'uuids':[capture.FLOCK_SERVICE]}))

    def test_extended_report_fragments_never_trigger_detector(self):
        data=bytes.fromhex('03ff530d03035ffd')
        def extended(event):
            body=b'\x0d\x01'+struct.pack('<H',event)+b'\0'+bytes.fromhex('554433221100')+b'\x01\x01\x01\x00\xd8\0\0\0'+b'\0'*6+bytes([len(data)])+data
            return b'\x04\x3e'+bytes([len(body)])+body
        self.assertTrue(packets.hci_reports(extended(0))[0]['complete'])
        self.assertFalse(packets.hci_reports(extended(32))[0]['complete'])
        result=capture.analyze(pcap(201,[b'\0\0\0\1'+extended(32)]),'packet-detector')
        self.assertEqual(result['incomplete'],1);self.assertFalse(result['detections'])

    def test_malformed_packets_do_not_escape_or_create_matches(self):
        valid=legacy(bytes.fromhex('03ff530d'))
        for end in range(len(valid)):
            result=capture.analyze(pcap(201,[b'\0\0\0\1'+valid[:end]]),'packet-detector')
            self.assertFalse(result['detections'])
        self.assertFalse(packets.hci_reports(legacy(b'\x05\xff\x53'))[0]['complete'])
        for raw in (b'',pcap(201,[])[:-1],pcap(201,[b'abc'])[:-1]):
            with self.assertRaises(ValueError): packets.pcap_records(raw)

    def test_reference_encoder_messages(self):
        fixtures=dict(line.split() for line in (Path(__file__).parent/'fixtures/remote_id.txt').read_text().splitlines())
        rows={name:remote_id.decode(bytes.fromhex(raw))[0] for name,raw in fixtures.items()}
        self.assertEqual(rows['basic']['uas_id'],'QM-SYNTHETIC-001')
        location=rows['location']
        for key,expected in dict(latitude=1.25,longitude=-2.5,direction_deg=270,horizontal_mps=70.5,vertical_mps=-2,altitude_baro_m=100,altitude_geo_m=120.5,height_m=50,seconds_after_hour=123.4).items():
            self.assertAlmostEqual(location[key],expected,places=3)
        self.assertEqual(location['height_reference'],'ground')
        for key in ('direction_deg','horizontal_mps','vertical_mps','altitude_baro_m','height_m','seconds_after_hour'):
            self.assertIsNone(rows['unknown'][key],key)
        self.assertEqual(rows['auth']['auth_data'],'5a'*17);self.assertFalse(rows['auth']['signature_verified'])
        self.assertEqual(rows['self']['description'],'SYNTHETIC TEST ONLY')
        self.assertEqual(rows['system']['area_radius_m'],30);self.assertEqual(rows['system']['eu_category'],1)
        self.assertEqual(rows['system']['latitude'],1.5);self.assertEqual(rows['system']['operator_altitude_m'],12)
        self.assertEqual(rows['operator']['operator_id'],'QM-TEST-OPERATOR')
        pack=b'\xf2\x19'+bytes([len(fixtures)])+b''.join(bytes.fromhex(v) for v in fixtures.values())
        self.assertEqual(len(remote_id.decode(pack)),7)
        with self.assertRaises(ValueError): remote_id.decode(pack[:-1])

    def test_remote_id_transport_headers_and_truncation(self):
        basic=b'\x02\x12QM-SYNTHETIC-001'+b'\0'*7
        self.assertEqual(len(basic),25)
        ble=b'\x1e\x16\xfa\xff\x0d\x01'+basic
        result=capture.analyze(pcap(201,[b'\0\0\0\1'+legacy(ble)]),'sky-ble')
        self.assertEqual(result['remote_id'][0]['uas_id'],'QM-SYNTHETIC-001')
        pack=b'\xf2\x19\x01'+basic
        vendor=b'\xfa\x0b\xbc\x0d\x01'+pack
        frame=dict(subtype=8,body=b'\0'*12+bytes([221,len(vendor)])+vendor)
        self.assertEqual(list(remote_id.wifi_payloads(frame)),[pack])
        value=b'\x88\x69\x19\x9d\x92\x09\x01\0\x10'+bytes([len(pack)+1])+b'\x01'+pack
        nan=b'\x04\x09\x50\x6f\x9a\x13\x03'+struct.pack('<H',len(value))+value
        self.assertEqual(list(remote_id.wifi_payloads(dict(subtype=13,body=nan))),[pack])
        self.assertFalse(list(remote_id.wifi_payloads(dict(subtype=13,body=nan[:-1]))))

    def test_native_capture_results_include_counts_empty_and_errors(self):
        report=dict(state='done',action='ble-sniff',captured=3,reports=3,note='fixture',detections=[],remote_id=[])
        total,status,payload=result_page({'packet_lab':report},7,0,True)
        self.assertEqual(total,3);self.assertIn('3 packets',payload);self.assertIn('0 candidates',payload)
        self.assertIn('missing',result_page({'packet_lab':{'state':'error','error':'missing'}},7,0)[2])

    def test_flock_wifi_uses_transmitter_not_destination(self):
        target=bytes.fromhex('b41e52112233');other=bytes.fromhex('001122334455')
        frame=lab_helper.management_frame(8,target,other,other,1,b'\0'*12)
        self.assertFalse(capture.analyze(pcap(127,[frame]),'flock-wifi')['detections'])
        frame=lab_helper.management_frame(8,other,target,target,1,b'\0'*12)
        self.assertEqual(len(capture.analyze(pcap(127,[frame]),'flock-wifi')['detections']),1)
        self.assertFalse(capture.analyze(pcap(127,[frame]),'axon-wifi')['detections'])
        axon=bytes.fromhex('0025df112233')
        frame=lab_helper.management_frame(8,other,axon,axon,1,b'\0'*12)
        self.assertEqual(len(capture.analyze(pcap(127,[frame]),'axon-wifi')['detections']),1)

    @patch.object(lab_helper.socket,'AF_PACKET',17,create=True)
    @patch.object(lab_helper.socket,'PACKET_OUTGOING',4,create=True)
    def test_wifi_discovery_never_retunes_connected_radio(self):
        profile=dict(interface='wlan1',ssid='fixture',bssids=['00:11:22:33:44:55'])
        calls=[]
        def command(*args):
            calls.append(args)
            return 'Connected to fixture\nfreq: 2412' if args[-1]=='link' else 'channel 1 (2412 MHz)'
        radio=Mock();radio.__enter__=Mock(return_value=radio);radio.__exit__=Mock(return_value=False)
        radio.recvfrom.side_effect=lab_helper.socket.timeout
        ticks=iter(range(100))
        def exists(path): return str(path).endswith('wlan1')
        with patch.object(lab_helper.Path,'exists',exists),patch.object(lab_helper,'command',side_effect=command),patch.object(lab_helper.socket,'socket',return_value=radio),patch.object(lab_helper.time,'monotonic',side_effect=lambda:next(ticks)):
            report=lab_helper.capture_discovery(profile)
        self.assertEqual(report['channels'],[2412]);radio.send.assert_not_called()
        self.assertFalse(any('freq' in c or 'down' in c or 'nmcli' in c for c in calls))
        self.assertEqual(calls[-1],('iw','dev','qmmon','del'))

    def test_discovery_setup_failure_restores_idle_radio(self):
        profile=dict(interface='wlan1',ssid='fixture',bssids=['00:11:22:33:44:55'])
        calls=[]
        def command(*args):
            calls.append(args)
            if 'NM-MANAGED' in ' '.join(args): return 'yes'
            if args==('ip','link','set','qmmon','up'): raise RuntimeError('fixture failure')
            return 'Not connected'
        with patch.object(lab_helper.Path,'exists',lambda p:str(p).endswith('wlan1')),patch.object(lab_helper,'command',side_effect=command):
            with self.assertRaisesRegex(RuntimeError,'fixture failure'):lab_helper.capture_discovery(profile)
        self.assertEqual(calls[-2:],[('iw','dev','qmmon','del'),('nmcli','device','set','wlan1','managed','yes')])

    @patch.object(lab_helper.socket,'AF_UNIX',1,create=True)
    def test_ble_capture_handshake_starts_discovery_after_ready(self):
        from qmarauder import lab
        radio=Mock();radio.__enter__=Mock(return_value=radio);radio.__exit__=Mock(return_value=False)
        radio.makefile.return_value=io.BytesIO(b'{"ready":true}\n{"captured":0}\n');ready=Mock()
        with patch.object(lab,'SOCKET') as path,patch.object(lab.socket,'socket',return_value=radio):
            path.exists.return_value=True
            self.assertEqual(lab.call('ble-capture-0',ready)['captured'],0)
        ready.assert_called_once()

    @patch.object(lab_helper.socket,'AF_BLUETOOTH',31,create=True)
    @patch.object(lab_helper.socket,'BTPROTO_HCI',1,create=True)
    def test_hci_receiver_filters_secrets_and_sends_no_commands(self):
        radio=Mock();radio.__enter__=Mock(return_value=radio);radio.__exit__=Mock(return_value=False)
        values=iter([b'\x04\x3e\x02\x05\x01',legacy(bytes.fromhex('03ff530d'))])
        def receive(_):
            try: return next(values)
            except StopIteration: raise lab_helper.socket.timeout
        radio.recv.side_effect=receive
        ticks=iter(range(100));ready=Mock()
        with patch.object(lab_helper.socket,'socket',return_value=radio),patch.object(lab_helper.time,'monotonic',side_effect=lambda:next(ticks)):
            report=lab_helper.capture_ble(0,ready)
        self.assertEqual(report['captured'],1);ready.assert_called_once();radio.send.assert_not_called()
        self.assertEqual(report['linktype'],201)
