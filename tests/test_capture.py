import base64
import socket
import struct
import tempfile
import unittest
from unittest.mock import Mock, patch
from qmarauder import lab_helper as helper
from qmarauder.storage import Store


class CaptureTests(unittest.TestCase):
    @patch.object(socket, 'AF_PACKET', 17, create=True)
    @patch.object(socket, 'PACKET_OUTGOING', 4, create=True)
    def test_capture_writes_real_radiotap_pcap_and_never_sends(self):
        profile=dict(interface='wlan1',ssid='fixture',bssids=['00:11:22:33:44:55'])
        mac=bytes.fromhex('001122334455')
        packet=helper.management_frame(8,b'\xff'*6,mac,mac,1,b'\x00'*12)
        radio=Mock();radio.__enter__=Mock(return_value=radio);radio.__exit__=Mock(return_value=False)
        packets=iter([(packet,('qmmon',0,4)),(packet,('qmmon',0,0))])
        def receive(size):
            try: return next(packets)
            except StopIteration: raise socket.timeout
        radio.recvfrom.side_effect=receive
        ticks=iter(i/10 for i in range(1000))
        with patch.object(helper,'target_for',return_value=(dict(bssid=profile['bssids'][0],frequency=2412),True)), patch.object(helper.Path,'exists',return_value=False), patch.object(helper,'command',return_value='channel 1 (2412 MHz)'), patch.object(helper.socket,'socket',return_value=radio), patch.object(helper.time,'monotonic',side_effect=lambda:next(ticks)):
            result=helper.execute('capture',profile)
        radio.send.assert_not_called()
        self.assertEqual(result['captured'],1)
        raw=base64.b64decode(result['pcap'],validate=True)
        self.assertEqual(struct.unpack_from('<I',raw,20)[0],127)
        self.assertEqual(struct.unpack_from('<II',raw,32),(len(packet),len(packet)))
        self.assertEqual(raw[40:],packet)

    def test_capture_export_is_session_scoped(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(root); session=store.start('wifi-capture')
            pcap=struct.pack('<IHHIIII',0xa1b2c3d4,2,4,0,0,4096,127)
            store.save_capture(session,pcap)
            self.assertTrue(store.sessions()[0]['pcap'])
            self.assertEqual(store.export(session,'pcap'),pcap)
            with self.assertRaises(KeyError): store.export('0'*32,'pcap')
            with self.assertRaises(ValueError): store.save_capture('../../x',pcap)
            with self.assertRaises(ValueError): store.save_capture(session,b'\0'*524289)
