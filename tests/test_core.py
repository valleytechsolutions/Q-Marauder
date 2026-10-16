import datetime as dt
import json
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from qmarauder.gps import validate_fix
from qmarauder.radio import parse_wifi, parse_ble, split_nmcli
from qmarauder.radio import kernel_support
from qmarauder.storage import Store
from qmarauder.server import handler_for, local_authority


class ParsingTests(unittest.TestCase):
    def test_missing_kernel_config_is_unknown_not_supported(self):
        with patch("qmarauder.radio.Path.read_bytes", side_effect=FileNotFoundError), patch("qmarauder.radio.Path.read_text", side_effect=FileNotFoundError):
            result = kernel_support()
        self.assertIsNone(result["config_source"])
        self.assertEqual(set(result["options"].values()), {"unknown"})

    def test_kernel_config_distinguishes_usb_from_pcie_driver(self):
        import gzip
        config = b'CONFIG_MT7921E=m\n# CONFIG_MT7921U is not set\nCONFIG_USBIP_CORE=m\nCONFIG_USBIP_VHCI_HCD=y\n'
        with patch("qmarauder.radio.Path.read_bytes", return_value=gzip.compress(config)):
            result = kernel_support()["options"]
        self.assertEqual(result, {"USBIP_CORE": "m", "USBIP_VHCI_HCD": "y", "MT7921U": "disabled"})

    def test_nmcli_escaping(self):
        self.assertEqual(split_nmcli(r"a\:b:c\\d"), ["a:b", "c\\d"])

    def test_wifi_unicode_colon_hidden_and_invalid(self):
        result = parse_wifi("\n".join([
            r"AA\:BB\:CC\:DD\:EE\:FF:Lab\: Café:36:5180 MHz:79:WPA2",
            r"00\:11\:22\:33\:44\:55::1:2412 MHz:20:",
            "bad:row", r"AA\:BB\:CC\:DD\:EE\:FF:broken:x:invalid:3:WPA2"]))
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["name"], "Lab: Café")
        self.assertEqual(result[0]["band"], "5 GHz")
        self.assertEqual(result[1]["security"], "Open")

    def test_duplicate_bssid_latest(self):
        self.assertEqual(len(parse_wifi((r"AA\:BB\:CC\:DD\:EE\:FF:lab:1:2412 MHz:20:WPA2"+"\n")*2)), 1)

    def test_ble_rssi_hex_and_negative(self):
        output = "[NEW] Device AA:BB:CC:DD:EE:FF Test\n[CHG] Device AA:BB:CC:DD:EE:FF RSSI: 0xffffffc4 (-60)\n"
        result = parse_ble(output)
        self.assertEqual(result[0]["rssi"], -60)
        self.assertEqual(result[0]["name"], "Test")
        self.assertEqual(parse_ble("[CHG] Device AA:BB:CC:DD:EE:FF RSSI: -45")[0]["rssi"], -45)

    def test_advertised_name_not_html(self):
        result=parse_ble("[NEW] Device AA:BB:CC:DD:EE:FF <img onerror=alert(1)>")
        self.assertEqual(result[0]["name"], "<img onerror=alert(1)>")


class GPSTests(unittest.TestCase):
    def setUp(self):
        self.now = dt.datetime(2026, 10, 15, 12, 0, tzinfo=dt.timezone.utc)
        self.message = dict(class_="TPV", mode=3, lat=40, lon=-73, time="2026-10-15T12:00:00Z")
        self.message["class"] = self.message.pop("class_")

    def test_valid_fix(self):
        self.assertEqual(validate_fix(self.message, self.now)["lat"], 40)

    def test_no_stale_or_future_fix(self):
        for offset in (16, -10):
            self.assertIsNone(validate_fix(self.message, self.now+dt.timedelta(seconds=offset)))

    def test_no_nonfinite_invalid_or_no_fix(self):
        for key, value in [("lat", float("nan")), ("lon", 181), ("mode", 1), ("time", "invalid")]:
            self.assertIsNone(validate_fix({**self.message,key:value}, self.now))


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_session_separation_and_null_coordinates(self):
        a,b=self.store.start("wifi"),self.store.start("ble")
        self.store.append(a,[dict(kind="wifi",name="Lab")])
        self.assertEqual(json.loads(self.store.export(b,"json")),[])
        self.assertIsNone(json.loads(self.store.export(a,"json"))[0]["lat"])

    def test_csv_formula_and_comma(self):
        session=self.store.start("wifi")
        self.store.append(session,[dict(name='=HYPERLINK("bad")',address="a,b")])
        text=self.store.export(session,"csv").decode()
        self.assertIn("'=HYPERLINK",text)
        self.assertIn('"a,b"',text)

    def test_restart_closes_sessions(self):
        self.store.start("wifi")
        self.assertIsNotNone(Store(self.temp.name).sessions()[0]["ended"])

    def test_missing_session(self):
        with self.assertRaises(KeyError): self.store.export("a"*32,"json")


class HTTPTests(unittest.TestCase):
    def setUp(self):
        from unittest.mock import Mock
        self.service=Mock()
        self.service.snapshot.return_value={"wifi":[]}
        self.server=ThreadingHTTPServer(("127.0.0.1",0),handler_for(self.service))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.base=f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join()

    def request(self,path,body=None,headers=None):
        request=urllib.request.Request(self.base+path,data=body,headers=headers or {})
        try:
            with urllib.request.urlopen(request) as response:return response.status,response.read()
        except urllib.error.HTTPError as response:return response.code,response.read()

    def test_dns_rebinding_rejected(self):
        self.assertEqual(self.request("/api/state",headers={"Host":"attacker.example"})[0],403)

    def test_cross_origin_rejected(self):
        headers={"Content-Type":"application/json","X-QM-Request":"1","Origin":"https://attacker.example"}
        self.assertEqual(self.request("/api/action",b'{"action":"wifi"}',headers)[0],403)
        self.service.submit.assert_not_called()

    def test_no_simple_post(self):
        self.assertEqual(self.request("/api/action",b'{"action":"wifi"}')[0],403)

    def test_valid_action(self):
        headers={"Content-Type":"application/json","X-QM-Request":"1"}
        self.assertEqual(self.request("/api/action",b'{"action":"wifi"}',headers)[0],202)
        self.service.submit.assert_called_once_with("wifi")

    def test_settings_and_ble_action_keep_same_origin_guard(self):
        headers={"Content-Type":"application/json","X-QM-Request":"1"}
        self.assertEqual(self.request('/api/settings',b'{"theme":2}',headers)[0],200)
        self.service.set_settings.assert_called_once_with({'theme':2})
        self.assertEqual(self.request('/api/settings',b'{"theme":1}',{**headers,'Origin':'https://other.example'})[0],403)
        self.service.set_settings.assert_called_once()
        self.assertEqual(self.request('/api/action',b'{"action":"ble-read","parameters":{"uuid":"2a19"}}',headers)[0],202)
        self.service.submit.assert_called_once_with('ble-read',{'uuid':'2a19'})

    def test_path_traversal_rejected(self):
        self.assertEqual(self.request("/../../.env")[0],404)

    def test_malformed_json(self):
        self.assertEqual(self.request("/api/action",b"[]",{"Content-Type":"application/json","X-QM-Request":"1"})[0],400)

    def test_authority_parser(self):
        self.assertTrue(local_authority("127.0.0.1:8787"))
        for host in ("evil.com","localhost.evil.com","evil@localhost","localhost/evil"):
            self.assertFalse(local_authority(host))


if __name__ == "__main__": unittest.main()
