import json
import queue
import threading
import types
import unittest
from unittest.mock import Mock, patch
from qmarauder.pairing import PairingBroker, validate_reply, call
from qmarauder.pair_worker import pair


class PairingTests(unittest.TestCase):
    def setUp(self):
        self.state={}
        self.broker=PairingBroker(threading.RLock(),self.state)
        self.broker.start()
        self.prompt={'id':'a'*32,'kind':'passkey'}
        self.broker.publish(self.prompt)

    def test_passkey_is_not_exposed_in_public_state_or_retained(self):
        self.broker.respond({'id':'a'*32,'accept':True,'code':'012345'})
        self.assertNotIn('012345',json.dumps(self.state))
        self.assertEqual(self.broker.replies.get_nowait()['code'],'012345')
        self.assertTrue(self.state['pairing']['answered'])
        with self.assertRaises(RuntimeError): self.broker.respond({'id':'a'*32,'accept':False})
        self.broker.finish()
        self.assertIsNone(self.state['pairing'])

    def test_expired_answers_do_not_authorize_new_prompt(self):
        self.broker.publish({'id':'b'*32,'kind':'confirm','code':'987654'})
        with self.assertRaises(RuntimeError): self.broker.respond({'id':'a'*32,'accept':True,'code':'012345'})
        self.assertTrue(self.broker.replies.empty())
        self.assertNotIn('answered',self.state['pairing'])
        self.broker.respond({'id':'b'*32,'accept':False})
        self.assertFalse(self.broker.replies.get_nowait()['accept'])

    def test_cancellation_clears_queued_secret_and_ignores_late_prompts(self):
        self.broker.respond({'id':'a'*32,'accept':True,'code':'012345'})
        self.broker.cancel()
        self.assertTrue(self.broker.replies.empty())
        self.broker.publish(self.prompt)
        self.assertIsNone(self.state['pairing'])
        with self.assertRaises(RuntimeError): self.broker.respond({'id':'a'*32,'accept':True,'code':'012345'})
        self.broker.finish();self.broker.start()
        self.assertFalse(self.broker.cancelled.is_set())

    def test_reply_types_digits_lengths_and_display_only(self):
        for code in ('12345','1234567','１２３４５６','12x456',123456):
            with self.assertRaises(ValueError): validate_reply('passkey',{'accept':True,'code':code})
        for answer in ({'accept':'yes'}, {'accept':True,'cmd':'shell'}, {'accept':True,'code':'123456'}):
            with self.assertRaises(ValueError): validate_reply('confirm',answer)
        with self.assertRaises(ValueError): validate_reply('display',{'accept':True})
        self.assertEqual(validate_reply('passkey',{'accept':True,'code':'000001'})['code'],'000001')

    def test_worker_launch_failure_always_clears_prompt(self):
        with patch('qmarauder.pairing.subprocess.Popen',side_effect=OSError('unavailable')):
            with self.assertRaises(OSError): call({},self.broker)
        self.assertFalse(self.broker.active)
        self.assertIsNone(self.state['pairing'])

    def test_agent_rejects_foreign_device_and_never_auto_confirms(self):
        registry={}
        class Object:
            def __init__(self,*args): registry['agent']=self
            def remove_from_connection(self): registry['removed']=True
        dbus=types.ModuleType('dbus');service=types.ModuleType('dbus.service')
        dbus.service=service;dbus.DBusException=type('DBusException',(Exception,),{})
        service.Object=Object;service.method=lambda *a,**kw: lambda method: method
        radio=Mock();radio.path='/org/bluez/hci0';radio.owned_connection=None
        target=radio.path+'/dev_00_11_22_33_44_55'
        radio.objects.return_value={target:{}}
        radio.properties.return_value={'Connected':False,'Paired':False}
        manager,device=Mock(),Mock()
        radio.interface.side_effect=[manager,device]
        accepted,foreign_error,selected_error=Mock(),Mock(),Mock()
        def pairing(**kwargs):
            agent=registry['agent']
            agent.RequestConfirmation('/foreign',123456,accepted,foreign_error)
            foreign_error.assert_called_once()
            agent.RequestConfirmation(target,123456,accepted,selected_error)
            accepted.assert_not_called();selected_error.assert_not_called()
            failure=Mock();failure.get_dbus_name.return_value='org.bluez.Error.AuthenticationCanceled'
            kwargs['error_handler'](failure)
        device.Pair.side_effect=pairing
        with patch.dict('sys.modules',{'dbus':dbus,'dbus.service':service}), patch('qmarauder.pair_worker.threading.Thread'), patch('qmarauder.pair_worker.emit') as output:
            with self.assertRaisesRegex(RuntimeError,'AuthenticationCanceled'): pair(radio,'00:11:22:33:44:55')
        manager.RegisterAgent.assert_called_once_with('/org/qmarauder/PairingAgent','KeyboardDisplay',timeout=5)
        manager.RequestDefaultAgent.assert_not_called()
        manager.UnregisterAgent.assert_called_once()
        device.CancelPairing.assert_called_once()
        accepted.assert_not_called()
        prompts=[c.kwargs['prompt'] for c in output.call_args_list if c.args[0]=='prompt']
        self.assertEqual(len(prompts),1)
        self.assertEqual(prompts[0]['kind'],'confirm')
        self.assertEqual(prompts[0]['code'],'123456')
        self.assertTrue(registry['removed'])

    def test_agent_delivers_passkey_and_keeps_existing_bond(self):
        registry, events = {}, []
        class Object:
            def __init__(self,*args): registry['agent']=self
            def remove_from_connection(self): registry['removed']=True
        dbus=types.ModuleType('dbus');service=types.ModuleType('dbus.service')
        dbus.service=service;dbus.DBusException=type('DBusException',(Exception,),{});dbus.UInt32=int
        service.Object=Object;service.method=lambda *a,**kw: lambda method: method
        radio=Mock();radio.path='/org/bluez/hci0';radio.owned_connection=None
        target=radio.path+'/dev_00_11_22_33_44_55'
        radio.objects.return_value={target:{}}
        radio.properties.side_effect=[{'Paired':False,'Connected':False},{'Paired':True,'Bonded':True,'ServicesResolved':True}]
        manager,device=Mock(),Mock();radio.interface.side_effect=[manager,device]
        radio.GLib.idle_add.side_effect=lambda callback,*args: events.append((callback,args))
        accepted,denied=Mock(),Mock()
        def on_pair(**kwargs):
            accepted.side_effect=lambda value: kwargs['reply_handler']()
            registry['agent'].RequestPasskey(target,accepted,denied)
        device.Pair.side_effect=on_pair
        def emit(kind,**values):
            if kind=='prompt': registry['prompt']=values['prompt']
        def run():
            # A real browser reply arrives only after BlueZ asks for a passkey.
            prompt=registry['prompt']
            incoming=json.dumps(dict(type='answer',id=prompt['id'],accept=True,code='000001'))+'\n'
            with patch('qmarauder.pair_worker.sys.stdin') as stdin:
                stdin.readline.side_effect=[incoming,'']
                registry['reader']()
            events[0][0](*events[0][1])
        radio.GLib.MainLoop.return_value.run.side_effect=run
        def thread(*args,**kwargs): registry['reader']=kwargs['target'];return Mock()
        with patch.dict('sys.modules',{'dbus':dbus,'dbus.service':service}), patch('qmarauder.pair_worker.threading.Thread',side_effect=thread), patch('qmarauder.pair_worker.emit',side_effect=emit):
            result=pair(radio,'00:11:22:33:44:55')
        accepted.assert_called_once_with(1);denied.assert_not_called()
        self.assertTrue(result['paired']);self.assertTrue(result['bonded'])
        device.CancelPairing.assert_not_called()
        manager.UnregisterAgent.assert_called_once()
        self.assertTrue(registry['removed'])
        self.assertNotIn('000001',json.dumps(result))

    def test_existing_bond_does_not_register_agent_or_take_connection(self):
        dbus=types.ModuleType('dbus');service=types.ModuleType('dbus.service');dbus.service=service
        radio=Mock();radio.path='/org/bluez/hci0';radio.owned_connection=None
        radio.objects.return_value={radio.path+'/dev_00_11_22_33_44_55':{}}
        radio.properties.return_value={'Paired':True,'Bonded':True,'Connected':True}
        with patch.dict('sys.modules',{'dbus':dbus,'dbus.service':service}):
            result=pair(radio,'00:11:22:33:44:55')
        self.assertTrue(result['already_paired'])
        self.assertIsNone(radio.owned_connection)
        radio.interface.assert_not_called()


if __name__=='__main__': unittest.main()
