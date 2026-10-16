"""BlueZ agent scoped to a single explicit pairing job and selected device."""
import json
import signal
import sys
import threading
import time
import uuid
from .ble_worker import BlueZ
from .pairing import validate_reply
from .settings import validate


def emit(kind, **values):
    print(json.dumps({'type':kind, **values}), flush=True)


def pair(radio, address):
    import dbus.service
    path = radio.path+'/dev_'+address.replace(':','_')
    if path not in radio.objects(): radio.scan(6, address)
    if path not in radio.objects(): raise RuntimeError('Target not observed; discover it again before pairing')
    properties = radio.properties(path, 'org.bluez.Device1')
    if properties.get('Paired'):
        return dict(paired=True, already_paired=True, bonded=bool(properties.get('Bonded')), services_resolved=bool(properties.get('ServicesResolved')))
    if properties.get('Connected'):
        raise RuntimeError('Target already connected; disconnect its existing session before pairing')
    loop = radio.GLib.MainLoop()
    outcome, pending = {}, {}
    agent_path = '/org/qmarauder/PairingAgent'
    manager = radio.interface('/org/bluez', 'org.bluez.AgentManager1')
    device = radio.interface(path, 'org.bluez.Device1')
    active = True
    started = time.monotonic()
    response_sent = False

    class Rejected(dbus.DBusException):
        _dbus_error_name = 'org.bluez.Error.Rejected'

    def clear():
        pending.clear()
        emit('clear')

    def target_only(target):
        if str(target) != path: raise Rejected('This agent only handles its selected target')

    def ask(target, kind, reply, error, code=None):
        try:
            target_only(target)
            if pending: raise Rejected('A pairing prompt is already pending')
            prompt = dict(id=uuid.uuid4().hex, kind=kind)
            if code is not None: prompt['code'] = str(code)
            pending.update(prompt=prompt, reply=reply, error=error)
            emit('prompt', prompt=prompt)
        except Rejected as exc: error(exc)

    class Agent(dbus.service.Object):
        @dbus.service.method('org.bluez.Agent1', in_signature='', out_signature='')
        def Release(self): clear()

        @dbus.service.method('org.bluez.Agent1', in_signature='o', out_signature='u', async_callbacks=('reply','error'))
        def RequestPasskey(self, target, reply, error): ask(target, 'passkey', reply, error)

        @dbus.service.method('org.bluez.Agent1', in_signature='o', out_signature='s', async_callbacks=('reply','error'))
        def RequestPinCode(self, target, reply, error): ask(target, 'pin', reply, error)

        @dbus.service.method('org.bluez.Agent1', in_signature='ou', out_signature='', async_callbacks=('reply','error'))
        def RequestConfirmation(self, target, passkey, reply, error):
            ask(target, 'confirm', reply, error, f'{int(passkey):06d}')

        @dbus.service.method('org.bluez.Agent1', in_signature='o', out_signature='', async_callbacks=('reply','error'))
        def RequestAuthorization(self, target, reply, error): ask(target, 'authorize', reply, error)

        @dbus.service.method('org.bluez.Agent1', in_signature='os', out_signature='', async_callbacks=('reply','error'))
        def AuthorizeService(self, target, service, reply, error): ask(target, 'authorize', reply, error)

        @dbus.service.method('org.bluez.Agent1', in_signature='ouq', out_signature='')
        def DisplayPasskey(self, target, passkey, entered):
            target_only(target)
            emit('prompt', prompt=dict(id=uuid.uuid4().hex,kind='display',code=f'{int(passkey):06d}',entered=int(entered)))

        @dbus.service.method('org.bluez.Agent1', in_signature='os', out_signature='')
        def DisplayPinCode(self, target, pincode):
            target_only(target)
            emit('prompt', prompt=dict(id=uuid.uuid4().hex,kind='display',code=str(pincode)))

        @dbus.service.method('org.bluez.Agent1', in_signature='', out_signature='')
        def Cancel(self):
            if pending: pending['error'](Rejected('Pairing was cancelled'))
            clear()

    def failed(error):
        # Include only BlueZ error class, never a passkey/PIN or remote-supplied text.
        name = error.get_dbus_name() if hasattr(error, 'get_dbus_name') else 'PairingFailed'
        progress = 'after a response was submitted' if response_sent else 'before a response was submitted'
        outcome['error'] = f'Pairing failed: {name} ({round(time.monotonic()-started)}s, {progress}). Retry with a fresh code entered directly in the browser.'
        loop.quit()

    def complete():
        outcome['success'] = True
        loop.quit()

    def cancel(message='Pairing cancelled'):
        outcome['error'] = message
        loop.quit()
        return False

    def answer(event):
        nonlocal response_sent
        if not active: return False
        if event.get('type') == 'cancel': return cancel()
        if event.get('type') != 'answer' or not pending: return False
        prompt = pending['prompt']
        if event.get('id') != prompt['id']: return False
        try:
            reply = validate_reply(prompt['kind'], {k:event[k] for k in ('id','accept','code') if k in event})
        except ValueError:
            return cancel('Invalid pairing response; start a new pairing attempt')
        success, error = pending['reply'], pending['error']
        clear()
        response_sent = True
        if not reply['accept']: error(Rejected('Pairing rejected by the user'))
        elif prompt['kind'] == 'passkey': success(dbus.UInt32(int(reply['code'])))
        elif prompt['kind'] == 'pin': success(reply['code'])
        else: success()
        return False

    def read_input():
        while active:
            line = sys.stdin.readline(4097)
            if not line or len(line)>4096:
                radio.GLib.idle_add(cancel); return
            try: event=json.loads(line)
            except ValueError:
                radio.GLib.idle_add(cancel); return
            if not isinstance(event, dict):
                radio.GLib.idle_add(cancel); return
            radio.GLib.idle_add(answer, event)

    agent = Agent(radio.bus, agent_path)
    registered = False
    try:
        manager.RegisterAgent(agent_path, 'KeyboardDisplay', timeout=5)
        registered = True
        # Do not become the global/default agent or alter Trusted/Discoverable.
        radio.owned_connection = path
        threading.Thread(target=read_input, daemon=True).start()
        timer = radio.GLib.timeout_add_seconds(100, lambda: cancel('Pairing timed out'))
        try:
            device.Pair(reply_handler=complete, error_handler=failed, timeout=105)
            loop.run()
        finally: radio.GLib.source_remove(timer)
        if outcome.get('error'): raise RuntimeError(outcome['error'])
        properties = radio.properties(path, 'org.bluez.Device1')
        if not properties.get('Paired'): raise RuntimeError('BlueZ did not confirm pairing')
        return dict(paired=True, bonded=bool(properties.get('Bonded')), services_resolved=bool(properties.get('ServicesResolved')))
    finally:
        active = False
        if not outcome.get('success'):
            try: device.CancelPairing(timeout=5)
            except dbus.DBusException: pass
        if registered:
            try: manager.UnregisterAgent(agent_path, timeout=5)
            except dbus.DBusException: pass
        agent.remove_from_connection()
        clear()


def main():
    radio = None
    result = None
    def stop(*_): raise RuntimeError('Pairing stopped or timed out')
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGALRM, stop)
    signal.alarm(120)
    try:
        request = json.loads(sys.stdin.readline(4097))
        validate({k:request[k] for k in ('target','adapter')})
        if request.get('action')!='ble-pair' or not request['target']: raise ValueError('Invalid pairing request')
        radio = BlueZ(request['adapter'])
        result = pair(radio, request['target'])
        result.update(action='ble-pair', state='done', kind='ble-lab', address=request['target'],
            note='BlueZ reports the selected device paired. Q-Marauder does not store passkeys or set Trusted. '+
                 ('The existing pairing was left unchanged.' if result.get('already_paired') else 'BlueZ retains the bond; the job connection is closed.'))
    except Exception as exc: result = {'error':str(exc)[:300]}
    finally:
        if radio:
            try: radio.close()
            except Exception:
                if result and not result.get('error'): result['note'] += ' Disconnect could not be confirmed.'
    emit('result', result=result)
    if result.get('error'): sys.exit(1)


if __name__=='__main__': main()
