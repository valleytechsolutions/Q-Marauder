import unittest
from qmarauder import hid
from qmarauder.detectors import evaluate


class HIDTests(unittest.TestCase):
    KEYBOARD = bytes.fromhex('05010906a101050719e029e71500250175019508810295017508810195067508150025650507190029658100c0')

    def test_keyboard_modifiers_and_array_usage(self):
        layout = hid.descriptor(self.KEYBOARD)
        self.assertEqual(layout['reports'], [dict(id=0,kind='input',bytes=8)])
        decoded = hid.report(layout, bytes.fromhex('0200040500000000'))
        self.assertEqual(decoded['keyboard_usages'], [0xe1,4,5])
        with self.assertRaisesRegex(ValueError, 'Truncated'): hid.report(layout, b'\x02')

    def test_report_reference_id_and_signed_relative_axis(self):
        layout = hid.descriptor(bytes.fromhex('05010930a10185021581257f750895018106c0'))
        decoded = hid.report(layout, b'\xfe', 2)
        self.assertEqual(decoded['fields'][0]['value'], -2)
        self.assertTrue(decoded['fields'][0]['relative'])
        with self.assertRaises(ValueError): hid.report(layout, b'\xfe', 1)

    def test_malformed_and_oversized_maps_are_rejected(self):
        for value in ('xx', b'\x75', b'\xfe\x02', b'\xfe\x02\x01\x00', b'\xc0', b'\xb4', bytes.fromhex('752195ff8100'), b'0'*4097):
            with self.assertRaises(ValueError): hid.descriptor(value)

    def test_array_uses_logical_index_into_explicit_usage_list(self):
        layout=hid.descriptor(bytes.fromhex('050719e029e115012502750895018100'))
        decoded=hid.report(layout,b'\x01')
        self.assertEqual(decoded['keyboard_usages'],[0xe0])
        self.assertIsNone(hid.report(layout,b'\x03')['fields'][0]['usage'])

    def test_random_address_prefix_is_not_axon_evidence(self):
        row = dict(address='00:25:DF:00:00:01',address_type='random',manufacturer_data={},uuids=[])
        self.assertEqual(evaluate([row], 'ble-axon'), [])
        row['manufacturer_data'] = {'034d':'00'}
        hits = evaluate([row], 'ble-axon')
        self.assertEqual(hits[0]['confidence'], 'candidate')
        self.assertIn('may transmit', hits[0]['note'])
