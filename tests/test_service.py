import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from qmarauder.service import Service
from qmarauder.locking import instance_lock


def wait_for(predicate):
    deadline = time.monotonic() + 4
    while time.monotonic() < deadline:
        if predicate(): return
        time.sleep(0.02)
    raise AssertionError("Worker did not reach expected state")


class ServiceTests(unittest.TestCase):
    def test_serialization_and_stop_during_scan(self):
        entered, release = threading.Event(), threading.Event()
        def scan():
            entered.set(); release.wait(3)
            return [dict(name="fixture",address="00:11:22:33:44:55",kind="wifi")]
        with tempfile.TemporaryDirectory() as data, patch("qmarauder.radio.diagnostics",return_value={}), patch("qmarauder.radio.wifi_scan",side_effect=scan), patch("qmarauder.gps.read_fix",return_value=None):
            service=Service(data)
            try:
                service.submit("mission-start")
                self.assertTrue(entered.wait(2))
                with self.assertRaises(RuntimeError):service.submit("ble")
                service.submit("mission-stop")
                release.set()
                wait_for(lambda:service.snapshot()["mission"] is None)
                sessions=service.store.sessions()
                self.assertEqual(sessions[0]["observations"],1)
                self.assertIsNotNone(sessions[0]["ended"])
            finally:
                release.set();service.close()

    def test_adapter_failure_is_reported_and_session_closed(self):
        with tempfile.TemporaryDirectory() as data, patch("qmarauder.radio.diagnostics",return_value={}), patch("qmarauder.radio.wifi_scan",side_effect=RuntimeError("device missing")):
            service=Service(data)
            try:
                service.submit("wifi")
                wait_for(lambda:service.snapshot()["busy"] is None)
                self.assertEqual(service.snapshot()["error"],"device missing")
                self.assertIsNotNone(service.store.sessions()[0]["ended"])
            finally:service.close()

    def test_exclusive_data_directory_lock(self):
        with tempfile.TemporaryDirectory() as data:
            with instance_lock(data):
                with self.assertRaises(RuntimeError):
                    with instance_lock(data):pass
            with instance_lock(data):pass
