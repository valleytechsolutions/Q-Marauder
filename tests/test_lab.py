import json
import io
import os
import socket
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from qmarauder import lab, lab_helper as helper

PROFILE = {"interface": "wlan0", "ssid": "Fixture lab", "bssids": ["02:11:22:33:44:55"]}
BSSID = bytes.fromhex("021122334455")
SOURCE = bytes.fromhex("021234567890")


class LabTests(unittest.TestCase):
    def setUp(self):
        # These Linux constants are absent on the Windows development host.
        for name, value in (("AF_PACKET", 17), ("PACKET_OUTGOING", 4), ("AF_UNIX", 1)):
            patcher = patch.object(helper.socket, name, value, create=True)
            patcher.start(); self.addCleanup(patcher.stop)

    def test_profile_rejects_command_text_and_non_lab_address(self):
        self.assertEqual(helper.validate_profile(PROFILE), PROFILE)
        for change in ({"interface": "wlan0;id"}, {"interface": "qmmon"}, {"interface": None},
                       {"ssid": "x" * 33}, {"bssids": ["FF:FF:FF:FF:FF:FF"]}, {"bssids": []}):
            with self.assertRaises(ValueError): helper.validate_profile({**PROFILE, **change})
        with self.assertRaises(ValueError): lab.call("arbitrary-command")

    def test_socket_accepts_only_one_fixed_action(self):
        self.assertEqual(helper.socket_action(io.StringIO("recon\n")), "recon")
        for value in ("", "recon", "recon --interface wlan1\n", "recon;id\n", "x" * 100, "--socket\n"):
            with self.assertRaises(ValueError): helper.socket_action(io.StringIO(value))

    @unittest.skipUnless(os.name == "posix", "Linux file-lock behavior")
    def test_radio_lock_rejects_overlap_and_releases_after_exception(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(helper, "STATE", Path(directory)):
            with self.assertRaisesRegex(RuntimeError, "interrupted"):
                with helper.exclusive_radio():
                    with self.assertRaisesRegex(RuntimeError, "already running"):
                        with helper.exclusive_radio(): pass
                    raise RuntimeError("interrupted")
            with helper.exclusive_radio(): pass

    def test_socket_transport_rejects_invalid_or_oversized_reports(self):
        for payload in (b'not json\n', b'[]\n', b'{"error":"Radio busy"}\n', b'x' * 16385):
            radio = Mock()
            radio.__enter__ = Mock(return_value=radio); radio.__exit__ = Mock(return_value=False)
            radio.makefile.return_value = io.BytesIO(payload)
            with patch.object(lab, "SOCKET") as path, patch.object(lab.socket, "socket", return_value=radio):
                path.exists.return_value = True
                with self.assertRaises(RuntimeError): lab.call("status")
                radio.sendall.assert_called_once_with(b"status\n")

    def test_socket_status_does_not_invoke_sudo(self):
        radio = Mock()
        radio.__enter__ = Mock(return_value=radio); radio.__exit__ = Mock(return_value=False)
        radio.makefile.return_value = io.BytesIO(b'{"configured":true}\n')
        with patch.object(lab, "SOCKET") as path, patch.object(lab.socket, "socket", return_value=radio), patch.object(lab.subprocess, "run") as run:
            path.exists.return_value = True
            self.assertTrue(lab.status()["configured"])
            run.assert_not_called()

    def test_unverified_monitor_channel_blocks_transmission_and_cleans_up(self):
        for info in ("type monitor", "channel 48 (5240 MHz)"):
            with patch.object(helper, "target_for", return_value=(dict(bssid=PROFILE["bssids"][0], frequency=2412), True)), patch.object(helper.Path, "exists", return_value=False), patch.object(helper, "command", return_value=info) as command, patch.object(helper.socket, "socket") as radio:
                with self.assertRaisesRegex(RuntimeError, "transmission blocked"): helper.execute("injection", PROFILE)
                radio.assert_not_called()
                self.assertEqual(command.call_args_list[-1].args, ("iw", "dev", "qmmon", "del"))

    def test_target_requires_allowlisted_bssid_ssid_and_connected_channel(self):
        scan = (r"02\:11\:22\:33\:44\:55:Fixture lab:2412 MHz:70" + "\n" +
                r"02\:11\:22\:33\:44\:66:Fixture lab:5180 MHz:99")
        with patch.object(helper, "command", side_effect=["Connected to ap\n freq: 2412", scan]):
            target, connected = helper.target_for(PROFILE)
            self.assertEqual(target["bssid"], PROFILE["bssids"][0])
            self.assertTrue(connected)
        for scan in (scan.replace("Fixture lab", "Unrelated"), scan.replace("2412 MHz", "5180 MHz")):
            with patch.object(helper, "command", side_effect=["Connected to ap\n freq: 2412", scan]):
                with self.assertRaises(RuntimeError): helper.target_for(PROFILE)

    def test_radiotap_parser_and_probe_destination(self):
        packet = helper.management_frame(5, SOURCE, BSSID, BSSID, 7, b"")
        decoded = helper.decode_frame(packet)
        self.assertEqual(decoded["subtype"], 5)
        self.assertEqual(decoded["destination"], SOURCE)
        self.assertEqual(decoded["bssid"], BSSID)
        for bad in (b"", b"\x00" * 20, b"\x00\x00\xff\xff" + b"\x00" * 100):
            self.assertIsNone(helper.decode_frame(bad))

    def test_deauth_requires_recent_matched_evidence_before_creating_monitor(self):
        target = dict(bssid=PROFILE["bssids"][0], frequency=2412)
        for evidence in ({}, {"bssid": target["bssid"], "frequency": 2412, "interface": "wlan0", "time": 1}):
            with patch.object(helper, "target_for", return_value=(target, True)), patch.object(helper.Path, "read_text", return_value=json.dumps(evidence)), patch.object(helper, "command", return_value="channel 48 (5240 MHz)") as command:
                with self.assertRaises(RuntimeError): helper.execute("deauth", PROFILE)
            command.assert_not_called()

    def test_monitor_cleanup_on_socket_failure_preserves_managed_connection(self):
        with patch.object(helper, "target_for", return_value=(dict(bssid=PROFILE["bssids"][0], frequency=2412), True)), patch.object(helper.Path, "exists", return_value=False), patch.object(helper, "command", return_value="channel 48 (5240 MHz)") as command, patch.object(helper.socket, "socket", side_effect=OSError("unsupported")):
            with self.assertRaises(OSError): helper.execute("recon", PROFILE)
            self.assertEqual(command.call_args_list[-1].args, ("iw", "dev", "qmmon", "del"))
            self.assertFalse(any("freq" in c.args or "down" in c.args for c in command.call_args_list))

    def test_injection_has_fixed_limit_and_requires_received_target_response(self):
        radio = Mock()
        radio.__enter__ = Mock(return_value=radio)
        radio.__exit__ = Mock(return_value=False)
        radio.send.side_effect = lambda packet: len(packet)
        radio.recvfrom.side_effect = socket.timeout
        ticks = iter(i / 10 for i in range(1000))
        with patch.object(helper, "target_for", return_value=(dict(bssid=PROFILE["bssids"][0], frequency=5180), True)), patch.object(helper.Path, "exists", return_value=False), patch.object(helper, "command", return_value="channel 36 (5180 MHz)"), patch.object(helper.socket, "socket", return_value=radio), patch.object(helper.time, "monotonic", side_effect=lambda: next(ticks)):
            report = helper.execute("injection", PROFILE)
        self.assertEqual(report["sent"], 10)
        self.assertFalse(report["injection_observed"])
        self.assertFalse(report["capture_observed"])
        self.assertEqual(radio.send.call_count, 10)
        for call in radio.send.call_args_list:
            frame = helper.decode_frame(call.args[0])
            self.assertEqual(frame["destination"], BSSID)
            self.assertEqual(frame["subtype"], 4)

    def test_deauth_is_three_frames_and_never_claims_disconnect(self):
        radio = Mock()
        radio.__enter__ = Mock(return_value=radio); radio.__exit__ = Mock(return_value=False)
        radio.send.side_effect = lambda packet: len(packet)
        radio.recvfrom.side_effect = socket.timeout
        evidence = {"bssid": PROFILE["bssids"][0], "interface": "wlan0", "frequency": 2412, "time": 1000}
        ticks = iter(i / 20 for i in range(1000))
        with patch.object(helper, "target_for", return_value=(dict(bssid=PROFILE["bssids"][0], frequency=2412), True)), patch.object(helper.Path, "exists", return_value=False), patch.object(helper.Path, "read_text", return_value=json.dumps(evidence)), patch.object(helper, "command", return_value="channel 1 (2412 MHz)"), patch.object(helper.socket, "socket", return_value=radio), patch.object(helper.time, "monotonic", side_effect=lambda: next(ticks)), patch.object(helper.time, "time", return_value=1001):
            report = helper.execute("deauth", PROFILE)
        self.assertEqual(report["sent"], 3)
        self.assertIn("not verified", report["note"])
        for call in radio.send.call_args_list:
            frame = helper.decode_frame(call.args[0])
            self.assertEqual(frame["source"], BSSID)
            self.assertEqual(frame["subtype"], 12)

    def test_only_received_directed_response_records_injection_evidence(self):
        radio = Mock()
        radio.__enter__ = Mock(return_value=radio); radio.__exit__ = Mock(return_value=False)
        radio.send.side_effect = lambda packet: len(packet)
        response = helper.management_frame(5, SOURCE, BSSID, BSSID, 7, b"")
        unrelated = helper.management_frame(5, SOURCE, b"\x02" * 6, b"\x02" * 6, 8, b"")
        packets = iter([(response, ("qmmon", 0, 4)), (unrelated, ("qmmon", 0, 0)), (response, ("qmmon", 0, 0))])
        def receive(_size):
            try: return next(packets)
            except StopIteration: raise socket.timeout
        radio.recvfrom.side_effect = receive
        ticks = iter(i / 10 for i in range(1000))
        with tempfile.TemporaryDirectory() as directory, patch.object(helper, "STATE", Path(directory)), patch.object(helper, "target_for", return_value=(dict(bssid=PROFILE["bssids"][0], frequency=5180), True)), patch.object(helper.Path, "exists", return_value=False), patch.object(helper, "command", return_value="channel 36 (5180 MHz)"), patch.object(helper.socket, "socket", return_value=radio), patch.object(helper.secrets, "token_bytes", return_value=SOURCE[1:]), patch.object(helper.time, "monotonic", side_effect=lambda: next(ticks)):
            report = helper.execute("injection", PROFILE)
            evidence = json.loads((Path(directory) / "injection.json").read_text())
        self.assertTrue(report["injection_observed"])
        self.assertEqual(report["probe_responses"], 1)
        self.assertEqual(evidence["bssid"], PROFILE["bssids"][0])
        self.assertEqual(evidence["frequency"], 5180)


if __name__ == "__main__":
    unittest.main()
