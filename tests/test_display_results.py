import tempfile
import threading
import unittest
from unittest.mock import Mock
from qmarauder.display import DisplayLink
from qmarauder.display_results import result_page


class ResultTests(unittest.TestCase):
    def test_untrusted_names_cannot_create_rows_and_pages_are_bounded(self):
        rows = [dict(name="A\tB\n\x1b\x00\u2603" + "x" * 90, address=f"00:11:22:33:44:{i:02x}",
                     channel=36, band="5 GHz", signal=80, security="WPA2") for i in range(7)]
        total, status, payload = result_page({"wifi": rows}, 1, 0)
        self.assertEqual(total, 7)
        self.assertEqual(len(payload.splitlines()), 4)
        self.assertLessEqual(len(payload), 1047)
        self.assertNotIn("\x00", payload)
        for line in payload.splitlines():
            self.assertEqual(len(line.split("\t")), 3)
            self.assertLessEqual(len(line.split("\t")[0]), 32)
        self.assertEqual(len(result_page({"wifi": rows}, 1, 1)[2].splitlines()), 3)
        self.assertEqual(result_page({"wifi": rows}, 1, 2)[2], "")

    def test_status_does_not_present_old_results_as_new_or_cross_radio_errors(self):
        state = dict(wifi=[dict(name="Lab")], busy="wifi")
        self.assertIn("previous", result_page(state, 1, 0)[1])
        state.update(busy=None, scan_status={"ble": {"state": "error"}})
        self.assertNotIn("error", result_page(state, 1, 0)[1])
        state["scan_status"]["wifi"] = {"state": "error"}
        self.assertIn("error", result_page(state, 1, 0)[1])

    def test_no_fabricated_ble_signal_or_radio_success(self):
        payload = result_page({"ble": [dict(name="Tag", rssi=None)]}, 2, 0)[2]
        self.assertIn("RSSI unavailable", payload)
        payload = result_page({"capabilities": {"monitor_advertised": True}}, 3, 0)[2]
        self.assertIn("Advertised / unverified", payload)
        self.assertIn("Admin setup required", payload)
        payload = result_page({"lab": {"state": "done", "action": "deauth", "sent": 3}}, 4, 0)[2]
        self.assertIn("do not validate injection", payload)

    def test_bridge_retries_stale_page_and_avoids_resending_identical_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            service = Mock(lock=threading.RLock(), state={"display": {}})
            views = iter(["7,1,0", "8,1,0", "8,1,0"])
            def reply(method, *args):
                if method == "qm.view": return next(views)
                if method == "qm.resultChunk": return True
                return args[0] == 8
            call = Mock(side_effect=reply)
            link = DisplayLink(service, directory, call)
            state = {"wifi": [dict(name="Lab")]}
            link.sync_results(state)
            self.assertIsNone(link.last_result)
            link.sync_results(state)
            self.assertEqual(link.last_result[0], 8)
            link.sync_results(state)
            self.assertEqual(sum(c.args[0] == "qm.results" for c in call.call_args_list), 2)
            for call in call.call_args_list:
                if call.args[0] == "qm.resultChunk": self.assertLessEqual(len(call.args[3]), 128)

    def test_supplemental_usb_module_is_not_reported_missing(self):
        state = {"capabilities": {
            "interfaces": [{"name": "wlan1", "driver": "mt7921u"}],
            "kernel": {"options": {"MT7921U": "disabled"},
                       "modules": {"mt7921u": {"loaded": True, "available": True}}}}}
        payload = result_page(state, 3, 1)[2]
        self.assertIn("Attached / driver loaded", payload)
        self.assertNotIn("Driver missing", payload)

    def test_failed_chunk_never_commits_a_partial_page(self):
        with tempfile.TemporaryDirectory() as directory:
            link = DisplayLink(Mock(), directory, Mock(side_effect=["7,1,0", False]))
            link.sync_results({"wifi": [dict(name="Lab")]})
            self.assertIsNone(link.last_result)
            self.assertEqual(link.call.call_count, 2)

    def test_fourth_theme_persists_without_changing_orientation(self):
        with tempfile.TemporaryDirectory() as directory:
            service = Mock(lock=threading.RLock(), state={"display": {}})
            link = DisplayLink(service, directory, Mock(side_effect=["3", "unset", True]))
            link.orientation = 1
            link.sync_theme()
            self.assertEqual(service.state["display"]["theme"], "Valleytech")
            link.sync_theme()
            link.call.assert_called_with("qm.restoreTheme", 3)
            self.assertEqual(link.orientation, 1)


if __name__ == "__main__":
    unittest.main()
