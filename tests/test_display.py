import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, call, patch
from qmarauder.display import DisplayLink, calibration_values, orientation_value, rpc


class DisplayTests(unittest.TestCase):
    def test_quiet_boot_restores_atomic_profile_before_any_default_is_saved(self):
        with tempfile.TemporaryDirectory() as directory:
            saved='v2,150,180,850,180,150,880'
            record={'orientation':3,'calibration':saved}
            service=Mock(state={'display':{}})
            service.lock=__import__('threading').RLock()
            service.snapshot.return_value=dict(error=None,stopping=False,busy=None,mission=None,
                                               wifi=[],ble=[],sessions=[],gps=None)
            rpc_call=Mock(side_effect=[True,True,True,'0,0','3','1',saved,'0,0,0'])
            link=DisplayLink(service,directory,rpc_call)
            link.quiet_boot=True
            link.orientation_path.write_text('3')
            link.path.write_text(json.dumps(record))
            link.cycle()
            self.assertEqual(rpc_call.call_args_list[:2],[
                call('qm.profilePending'),call('qm.restoreProfile',3,150,180,850,180,150,880)])
            self.assertEqual(json.loads(link.orientation_path.read_text()),3)
            self.assertEqual(json.loads(link.path.read_text()),record)

    def test_quiet_boot_missing_corrupt_or_mismatched_profile_uses_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            rpc_call=Mock(return_value=True)
            link=DisplayLink(Mock(),directory,rpc_call)
            link.sync_boot_profile()  # New installation: no files yet.
            rpc_call.assert_called_with('qm.acceptProfile')
            link.orientation_path.write_text('2')
            for record in ('broken',json.dumps({'orientation':1,'calibration':'v2,150,180,850,180,150,880'}),
                           json.dumps({'orientation':2,'calibration':'v2,0,0,1,1,2,2'})):
                link.path.write_text(record)
                rpc_call.reset_mock()
                link.sync_boot_profile()
                self.assertEqual(rpc_call.call_args_list,[call('qm.profilePending'),call('qm.acceptProfile')])

    def test_quiet_boot_manual_profile_is_not_replaced(self):
        link=DisplayLink(Mock(),Path('unused'),Mock(return_value=False))
        link.sync_boot_profile()
        link.call.assert_called_once_with('qm.profilePending')

    def test_quiet_boot_restore_failure_does_not_persist_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            record={'orientation':3,'calibration':'v2,150,180,850,180,150,880'}
            service=Mock()
            rpc_call=Mock(side_effect=[True,False,True,True])
            link=DisplayLink(service,directory,rpc_call)
            link.quiet_boot=True
            link.orientation_path.write_text('3')
            link.path.write_text(json.dumps(record))
            with self.assertRaises(ConnectionError): link.cycle()
            service.snapshot.assert_not_called()
            self.assertEqual(json.loads(link.path.read_text()),record)
            self.assertEqual(link.orientation_path.read_text(),'3')
            link.sync_boot_profile()  # Retried, with the original saved profile intact.
            self.assertEqual(rpc_call.call_args_list[1],rpc_call.call_args_list[3])

    def test_quiet_boot_invalid_status_stops_before_saving_defaults(self):
        for response in (None,0,1,'false','true'):
            link=DisplayLink(Mock(),Path('unused'),Mock(return_value=response))
            link.quiet_boot=True
            with self.assertRaises(ConnectionError): link.cycle()
            link.service.snapshot.assert_not_called()

    def test_native_characteristic_cannot_be_reused_for_another_target(self):
        characteristic='00002a19-0000-1000-8000-00805f9b34fb'
        target='00:11:22:33:44:55'
        state={'settings':{'target':target},'ble_lab':{'address':target,'characteristics':[{'uuid':characteristic}]}}
        service=Mock();service.snapshot.return_value=state
        link=DisplayLink(service,Path('unused'),Mock(return_value=True))
        link.handle_action('1,31,'+characteristic)
        link.handle_action('2,22')
        service.submit.assert_called_once_with('ble-read',{'uuid':characteristic})
        state['settings']['target']='00:11:22:33:44:66'
        link.handle_action('3,24,00')
        service.submit.assert_called_once()
        self.assertIn('Choose a characteristic',link.reply)
        link.handle_action('4,31,'+characteristic)
        self.assertIn('expired',link.reply)

    def test_native_pairing_ack_retry_submits_code_once(self):
        service=Mock();call=Mock(side_effect=[ConnectionError('lost'),True])
        link=DisplayLink(service,Path('unused'),call)
        with self.assertRaises(ConnectionError): link.handle_action('3,32,promptid:123456')
        link.handle_action('3,32,promptid:123456')
        service.pairing_reply.assert_called_once_with({'id':'promptid','accept':True,'code':'123456'})

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
            service=Mock(state={"display":{}})
            service.lock=__import__('threading').RLock()
            link=DisplayLink(service,directory,Mock(side_effect=["unset",True]))
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
        self.assertGreaterEqual(len(entries),152)
        self.assertIn(('0','Settings','12','0'), entries)
        self.assertTrue({"BWM","Marauder","Biscuit Shop","Valleytech"}.issubset({entry[1] for entry in entries}))
        for menu,title,child,action in entries:
            if "Attack" in title or "Flood" in title or "Spam" in title:
                self.assertEqual(int(action),0)

    def test_browser_theme_is_acked_and_native_change_is_saved(self):
        with tempfile.TemporaryDirectory() as directory:
            from qmarauder.settings import DEFAULTS, load
            service=Mock(state={'display':{},'settings':{**DEFAULTS,'theme':2},'pending_theme':2})
            service.lock=__import__('threading').RLock()
            call=Mock(side_effect=['0',True,'3'])
            link=DisplayLink(service,directory,call)
            link.sync_theme()
            self.assertIsNone(service.state['pending_theme'])
            call.assert_called_with('qm.setTheme',2)
            self.assertEqual(service.state['display']['theme'],'Biscuit Shop')
            link.sync_theme()
            self.assertEqual(load(directory)['theme'],3)


if __name__=="__main__": unittest.main()
