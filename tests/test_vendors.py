import unittest
from unittest.mock import patch
from qmarauder import vendors


class VendorTests(unittest.TestCase):
    def test_same_prefix_scope_as_chimera_omits_longer_blocks(self):
        rows=vendors.parse_manuf('# comment\n00:11:22\tShort\tFull Vendor\nAA:BB:CC:00:00:00/28\tSkip\tNot MA-L\n00:22:33\tFallback\n')
        self.assertEqual(rows,{'00:11:22':'Full Vendor','00:22:33':'Fallback'})

    def test_no_attribution_for_private_local_multicast_or_unknown_addresses(self):
        with patch.object(vendors,'database',return_value={'entries':{'00:11:22':'Vendor','02:11:22':'Local','01:11:22':'Multicast'}}):
            self.assertEqual(vendors.lookup('00:11:22:33:44:55'),'Vendor')
            for address,kind in [('00:11:22:33:44:55','random'),('00:11:22:33:44:55','unknown'),('02:11:22:33:44:55','public'),('01:11:22:33:44:55','public'),('invalid','public')]:
                self.assertIsNone(vendors.lookup(address,kind))
