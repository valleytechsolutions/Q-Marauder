import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from qmarauder.display import DisplayLink, calibration_values, orientation_value, rpc


class DisplayTests(unittest.TestCase):
    def test_affine_calibration_and_rejected_legacy_or_degenerate_targets(self):
        self.assertEqual(calibration_values("v2,150,180,850,180,150,880"), (150,180,850,180,150,880))
        self.assertEqual(calibration_values("v2,850,880,150,880,850,180"), (850,880,150,880,850,180))
        for value in ("0,1,2", "1,900,100", "v2,0,0,500,500,1000,1000",
                      "v2,0,0,1024,0,0,900", "v2,0,0,10,0,0,10", None):
            with self.assertRaises(ValueError): calibration_values(value)

    def test_ack_retry_does_not_repeat_radio_action(self):
        service=Mock()
        call=Mock(side_effect=[ConnectionError("lost"), True, True])
        link=DisplayLink(service, Path("unused"), call)
        with self.assertRaises(ConnectionError): link.handle_action("7,1")
        link.handle_action("7,1")
        service.submit.assert_called_once_with("wifi")
        link.handle_action("7,0")
        link.handle_action("8,99")
        service.submit.assert_called_once()

    def test_calibration_is_persisted_and_restored(self):
        with tempfile.TemporaryDirectory() as directory:
            service=Mock()
            service.lock=__import__('threading').RLock()
            service.state={"display":{}}
            value="v2,150,180,850,180,150,880"
            link=DisplayLink(service,directory,Mock(return_value=value))
            link.orientation=3
            link.sync_calibration()
            self.assertEqual(json.loads(link.path.read_text()),
                             {"orientation":3,"calibration":value})
            restore=Mock(side_effect=["uncalibrated",True])
            second=DisplayLink(service,directory,restore)
            second.orientation=3
            second.sync_calibration()
            restore.assert_called_with("qm.restoreCalibration",150,180,850,180,150,880)

    def test_calibration_from_another_orientation_or_legacy_is_not_restored(self):
        with tempfile.TemporaryDirectory() as directory:
            service=Mock()
            service.lock=__import__('threading').RLock()
            service.state={"display":{}}
            for record in ("0,125,905", {"orientation":3,"calibration":"0,125,905"},
                           {"orientation":0,"calibration":"v2,150,180,850,180,150,880"}):
                call=Mock(return_value="uncalibrated")
                link=DisplayLink(service,directory,call)
                link.orientation=3
                link.path.write_text(json.dumps(record))
                link.sync_calibration()
                call.assert_called_once_with("qm.calibration")

    def test_orientation_persists_and_restores_after_mcu_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            service=Mock()
            service.lock=__import__('threading').RLock()
            service.state={"display":{}}
            call=Mock(side_effect=["3", "unset", True, "3"])
            link=DisplayLink(service,directory,call)
            self.assertTrue(link.sync_orientation())
            self.assertEqual(json.loads(link.orientation_path.read_text()),3)
            link.restore_attempted=True
            self.assertFalse(link.sync_orientation())
            call.assert_called_with("qm.restoreOrientation",3)
            self.assertFalse(link.restore_attempted)
            self.assertIsNone(link.orientation)
            self.assertTrue(link.sync_orientation())

    def test_orientation_rejects_invalid_axes(self):
        for value in (0,1,2,3,"0","1","2","3"):
            self.assertEqual(orientation_value(value),int(value))
        for value in (True,None,8,72,136,200,"3;reset","03",3.0):
            with self.assertRaises(ValueError): orientation_value(value)

    def test_theme_persists_and_restores_after_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            service=Mock()
            service.lock=__import__('threading').RLock()
            service.state={"display":{}}
            call=Mock(side_effect=["1","unset",True])
            link=DisplayLink(service,directory,call)
            link.sync_theme()
            self.assertEqual(json.loads(link.theme_path.read_text()),1)
            self.assertEqual(service.state["display"]["theme"],"Marauder")
            link.sync_theme()
            call.assert_called_with("qm.restoreTheme",1)

    def test_invalid_saved_theme_uses_bwm_default(self):
        with tempfile.TemporaryDirectory() as directory:
            link=DisplayLink(Mock(),directory,Mock(side_effect=["unset",True]))
            link.theme_path.write_text('999')
            link.sync_theme()
            link.call.assert_called_with("qm.restoreTheme",0)

    def test_rpc_uses_argument_list_and_detects_rejection(self):
        result=Mock(returncode=0,stdout='Got RPC response: true\n')
        with patch("qmarauder.display.subprocess.run",return_value=result) as run:
            self.assertTrue(rpc("qm.update",1,2,3,False,"literal $() ; text"))
            self.assertEqual(run.call_args.args[0][-1],"str:literal $() ; text")
            self.assertNotIn("shell",run.call_args.kwargs)
            result.stdout="Got RPC error: invalid"
            with self.assertRaises(ConnectionError): rpc("qm.update")

    def test_menu_tree_reachable_and_fixed_backend_allowlist(self):
        import re
        data=(Path(__file__).resolve().parents[1]/"firmware/uno_shield/MenuData.h").read_text()
        entries=re.findall(r'\{(\d+),"([^"]+)",(-?\d+),(\d+)\}',data)
        menus={int(e[0]) for e in entries}
        reachable={0}
        for _ in menus:
            reachable |= {int(child) for menu,_,child,_ in entries if int(menu) in reachable and int(child)>=0}
        self.assertEqual(reachable,menus)
        self.assertEqual(len(entries),137)
        self.assertTrue({"BWM","Marauder","Cyber"}.issubset({entry[1] for entry in entries}))
        for menu,title,child,action in entries:
            if "Attack" in title or "Flood" in title or "Spam" in title:
                self.assertEqual(int(action),0)


if __name__=="__main__": unittest.main()
