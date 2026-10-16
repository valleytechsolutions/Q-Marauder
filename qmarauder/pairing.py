"""Transient pairing prompts and an isolated, bounded worker transport.

Passkeys travel over process pipes only. They are never put in session reports,
preferences, log messages or public reply state.
"""
import json
import queue
import re
import subprocess
import sys
import threading
import time

PROMPTS = ('passkey', 'pin', 'confirm', 'authorize', 'display')


def validate_reply(kind, answer):
    if not isinstance(answer, dict) or set(answer) - {'id', 'accept', 'code'}:
        raise ValueError('Invalid pairing reply')
    if type(answer.get('accept')) is not bool:
        raise ValueError('Choose accept or reject')
    result = {'id': answer.get('id'), 'accept': answer['accept']}
    if not answer['accept']:
        return result
    code = answer.get('code', '')
    if kind == 'display':
        raise ValueError('Enter the displayed code on the other device; no local confirmation is required')
    if kind == 'passkey':
        if not isinstance(code, str) or not re.fullmatch(r'[0-9]{6}', code):
            raise ValueError('Enter the six digits shown on your device')
        result['code'] = code
    elif kind == 'pin':
        if not isinstance(code, str) or not re.fullmatch(r'[ -~]{1,16}', code):
            raise ValueError('Enter the device PIN (1–16 printable characters)')
        result['code'] = code
    elif kind not in ('confirm', 'authorize'):
        raise ValueError('Unknown pairing prompt')
    elif code:
        raise ValueError('This prompt requires confirmation, not a code')
    return result


class PairingBroker:
    def __init__(self, lock, state):
        self.lock, self.state = lock, state
        self.replies = queue.Queue(maxsize=1)
        self.cancelled = threading.Event()
        self.active = False

    def _drain(self):
        while True:
            try: self.replies.get_nowait()
            except queue.Empty: return

    def start(self):
        with self.lock:
            self._drain()
            self.cancelled.clear()
            self.active = True
            self.state['pairing'] = None

    def publish(self, prompt):
        if prompt is not None:
            if (not isinstance(prompt, dict) or prompt.get('kind') not in PROMPTS or
                    not re.fullmatch(r'[0-9a-f]{32}', str(prompt.get('id', '')))):
                raise RuntimeError('Invalid pairing prompt from worker')
            prompt = {k: prompt[k] for k in ('id','kind','code','entered') if k in prompt}
            if 'code' in prompt and not re.fullmatch(r'[ -~]{1,16}', str(prompt['code'])):
                raise RuntimeError('Invalid displayed pairing code')
        with self.lock:
            if self.active and not self.cancelled.is_set():
                self._drain()
                self.state['pairing'] = prompt

    def respond(self, answer):
        with self.lock:
            current = self.state.get('pairing')
            if (not self.active or self.cancelled.is_set() or not current or current.get('answered') or
                    not isinstance(answer, dict) or answer.get('id') != current['id']):
                raise RuntimeError('Pairing prompt expired or already answered')
            reply = validate_reply(current['kind'], answer)
            self.replies.put_nowait(reply)
            # Never copy an entered PIN/passkey into state returned by /api/state.
            self.state['pairing'] = {**current, 'answered': True}

    def cancel(self):
        with self.lock:
            if not self.active: raise RuntimeError('No pairing job is active')
            self.cancelled.set()
            self._drain()
            self.state['pairing'] = None

    def finish(self):
        with self.lock:
            self.active = False
            self._drain()
            self.state['pairing'] = None


def call(request, broker):
    broker.start()
    process = None
    reader = None
    messages = queue.Queue()
    try:
        process = subprocess.Popen([sys.executable, '-m', 'qmarauder.pair_worker'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, bufsize=1)
        process.stdin.write(json.dumps(request)+'\n'); process.stdin.flush()
        def read():
            try:
                for _ in range(200):
                    line = process.stdout.readline(8193)
                    if not line: break
                    if len(line) > 8192:
                        messages.put({'type':'error'}); return
                    try: messages.put(json.loads(line))
                    except ValueError: messages.put({'type':'error'}); return
            finally: messages.put(None)
        reader = threading.Thread(target=read, daemon=True)
        reader.start()
        deadline, cancel_at = time.monotonic()+130, None
        while time.monotonic() < deadline:
            if broker.cancelled.is_set() and cancel_at is None:
                process.stdin.write('{"type":"cancel"}\n'); process.stdin.flush()
                cancel_at = time.monotonic()
            if cancel_at and time.monotonic()-cancel_at > 8:
                raise RuntimeError('Pairing cancelled')
            try: reply = broker.replies.get_nowait()
            except queue.Empty: reply = None
            if reply and cancel_at is None:
                process.stdin.write(json.dumps({'type':'answer', **reply})+'\n'); process.stdin.flush()
            try: event = messages.get(timeout=.1)
            except queue.Empty: continue
            if not isinstance(event, dict): raise RuntimeError('Pairing worker stopped without a result')
            if event.get('type') == 'prompt': broker.publish(event['prompt'])
            elif event.get('type') == 'clear': broker.publish(None)
            elif event.get('type') == 'result':
                result = event['result']
                process.wait(timeout=7)
                if result.get('error'): raise RuntimeError(result['error'])
                if process.returncode: raise RuntimeError('Pairing worker failed')
                return result
            else: raise RuntimeError('Invalid pairing worker response')
        raise RuntimeError('Pairing timed out')
    finally:
        try:
            if process:
                if process.poll() is None:
                    process.terminate()
                    try: process.wait(timeout=7)
                    except subprocess.TimeoutExpired:
                        process.kill(); process.wait(timeout=3)
                if process.stdin:
                    try: process.stdin.close()
                    except BrokenPipeError: pass
                if reader: reader.join(timeout=1)
                if process.stdout: process.stdout.close()
        finally: broker.finish()
