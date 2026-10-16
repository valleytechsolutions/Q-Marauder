"""Optional native TFT bridge via Arduino's locally installed router CLI."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import threading
from .display_results import result_page
from . import settings

ACTIONS = {1: "wifi", 2: "ble", 3: "mission-start", 4: "mission-stop", 14: "diagnostics",
           15: "lab-recon", 16: "lab-injection", 17: "lab-deauth",
           18: 'ble-detect', 19: 'ble-foxhunt', 20: 'ble-gatt', 21: 'ble-pair',
           22: 'ble-read', 23: 'ble-notify', 24: 'ble-write', 25: 'ble-snapshot',
           26: 'ble-hid', 27: 'ble-axon', 28: 'ble-detector', 36: 'ble-hid-listen', 37: 'wifi-capture', 38:'ble-write',
           39:'flock-wifi', 40:'flock-ble', 41:'sky-wifi', 42:'sky-ble', 43:'ble-sniff', 44:'packet-detector',
           45:'ble-advertise',46:'ble-advert-stop',47:'axon-wifi',
           48:'linux-interfaces',49:'wifi-audit',50:'bt-controllers',51:'bt-classic',
           54:'wifi-channels',55:'wifi-changes',56:'ble-summary',57:'bt-devices'}
ORIENTATIONS = (0, 1, 2, 3)  # Software reflections: bit 0 = X, bit 1 = Y.


def orientation_value(value):
    if isinstance(value, str) and value in tuple(map(str, ORIENTATIONS)):
        return int(value)
    if type(value) is int and value in ORIENTATIONS:
        return value
    raise ValueError("Invalid portrait orientation")


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value), encoding="utf-8")
    temporary.replace(path)


def rpc(method, *arguments):
    encoded = ["true" if arg is True else "false" if arg is False else
               str(arg) if isinstance(arg, int) else "str:" + str(arg) for arg in arguments]
    result = subprocess.run(["arduino-router-cli", method, *encoded], capture_output=True,
                            text=True, timeout=6, check=False)
    marker = "Got RPC response: "
    if result.returncode or marker not in result.stdout:
        raise ConnectionError("Native display did not acknowledge the request")
    return json.loads(result.stdout.split(marker, 1)[1].strip())


def calibration_values(value):
    if not isinstance(value, str) or not re.fullmatch(r"v2(?:,\d{1,4}){6}", value):
        raise ValueError("Invalid touch calibration")
    values = tuple(map(int, value.split(",")[1:]))
    if any(not 0 <= v <= 1023 for v in values):
        raise ValueError("Invalid touch range")
    x0, y0, x1, y1, x2, y2 = values
    if abs((x1-x0)*(y2-y0)-(y1-y0)*(x2-x0)) < 60000:
        raise ValueError("Touch targets are too close or collinear")
    return values


class DisplayLink:
    def __init__(self, service, data_dir, call=rpc):
        self.service, self.call = service, call
        self.path = Path(data_dir) / "touch-calibration.json"
        self.orientation_path = Path(data_dir) / "display-orientation.json"
        self.theme_path = Path(data_dir) / "display-theme.json"
        self.stop = threading.Event()
        self.thread = None
        self.handled = None
        self.reply = ""
        self.restore_attempted = False
        self.saved = None
        self.orientation = None
        self.orientation_restore_attempted = False
        self.saved_orientation = None
        self.saved_theme = None
        self.last_result = None
        self.controls = False
        self.characteristic = ''
        self.characteristic_target = ''
        self.pair_prompt = None

    def start(self):
        if not shutil.which("arduino-router-cli") or not Path("/var/run/arduino-router.sock").exists():
            return
        self.thread = threading.Thread(target=self.run, name="tft-bridge", daemon=True)
        self.thread.start()

    def status(self, **values):
        with self.service.lock:
            self.service.state["display"].update(values)

    def handle_action(self, value):
        if not isinstance(value, str) or not re.fullmatch(r"\d{1,10},\d{1,2}(?:,[ -~]{0,132})?", value):
            raise ValueError("Invalid display action")
        parts = value.split(',', 2)
        sequence, action = map(int, parts[:2])
        argument = parts[2] if len(parts) > 2 else ''
        if action == 0:
            self.handled = None
            return
        if self.handled != (sequence, action):
            try:
                if action == 30:
                    self.service.set_settings({'target': argument})
                    self.characteristic = ''
                elif action == 59:
                    self.service.submit('linux-open', {'session':argument})
                elif action == 31:
                    from .ble_data import uuid
                    candidate = uuid(argument)
                    state = self.service.snapshot()
                    report = state.get('ble_lab') or {}
                    if not state['settings']['target'] or report.get('address') != state['settings']['target'] or candidate not in [c['uuid'] for c in report.get('characteristics', [])]:
                        raise ValueError('GATT results expired. Inspect the selected device again.')
                    self.characteristic = candidate
                    self.characteristic_target = state['settings']['target']
                elif action == 32:
                    identity, code = argument.split(':', 1)
                    self.service.pairing_reply(dict(id=identity, accept=True, **({'code':code} if code else {})))
                elif action == 33: self.service.cancel_pairing()
                elif action in (34, 35): self.service.set_settings({'adapter': 'hci'+str(action-34)})
                elif action in (22,23,24,38):
                    if not self.characteristic or self.service.snapshot()['settings']['target'] != self.characteristic_target:
                        raise ValueError('Choose a characteristic from the current GATT results first.')
                    parameters = {'uuid': self.characteristic}
                    if action in (24,38): parameters.update(value=argument, write_type='command' if action==38 else 'request')
                    self.service.submit(ACTIONS[action], parameters)
                elif action in ACTIONS: self.service.submit(ACTIONS[action])
                else: raise ValueError('This action is not supported.')
                self.reply = 'Task accepted.'
            except (RuntimeError, ValueError) as exc:
                self.reply = str(exc)[:120]
            # Keep the result until acknowledged, even across a transient RPC error.
            self.handled = (sequence, action)
        if self.call("qm.ack", sequence, self.reply) is not True:
            raise ConnectionError("Display action acknowledgement failed")

    def sync_orientation(self):
        value = self.call("qm.orientation")
        if value == "unset":
            # A fast MCU restart may happen without a failed RPC request.
            if self.orientation is not None:
                self.orientation_restore_attempted = False
                self.restore_attempted = False
                self.saved = None
            self.orientation = None
            self.status(orientation="setup", touch="uncalibrated")
            if not self.orientation_restore_attempted:
                self.orientation_restore_attempted = True
                try:
                    saved = orientation_value(json.loads(self.orientation_path.read_text(encoding="utf-8")))
                except (OSError, ValueError, TypeError):
                    return False
                self.call("qm.restoreOrientation", saved)
            return False
        value = orientation_value(value)
        if value != self.orientation:
            self.orientation = value
            self.restore_attempted = False
            self.saved = None
        if value != self.saved_orientation:
            save_json(self.orientation_path, value)
            self.saved_orientation = value
        self.status(orientation=value)
        return True

    def sync_theme(self):
        with self.service.lock:
            pending = self.service.state.get('pending_theme')
        value = self.call("qm.theme")
        if type(pending) is int and pending in range(4):
            if self.call('qm.setTheme', pending) is not True:
                raise ConnectionError('Display did not apply the selected theme')
            value = str(pending)
            with self.service.lock:
                if self.service.state.get('pending_theme') == pending:
                    self.service.state['pending_theme'] = None
        if value == "unset":
            try:
                saved = json.loads(self.theme_path.read_text(encoding="utf-8"))
                if type(saved) is not int or saved not in (0, 1, 2, 3):
                    saved = 0
            except (OSError, ValueError, TypeError):
                saved = 0
            self.call("qm.restoreTheme", saved)
            return
        if value not in ("0", "1", "2", "3"):
            raise ValueError("Invalid display theme")
        value = int(value)
        if value != self.saved_theme:
            save_json(self.theme_path, value)
            self.saved_theme = value
        self.status(theme=("BWM", "Marauder", "Biscuit Shop", "Valleytech")[value])
        with self.service.lock:
            if 'settings' in self.service.state and self.service.state.get('pending_theme') is None:
                if self.service.state['settings']['theme'] != value:
                    self.service.state['settings']['theme'] = value
                    settings.save(self.theme_path.parent, self.service.state['settings'])

    def sync_calibration(self):
        if self.orientation is None:
            return
        value = self.call("qm.calibration")
        if value == "uncalibrated":
            self.status(touch="uncalibrated")
            if not self.restore_attempted:
                self.restore_attempted = True
                try:
                    saved = json.loads(self.path.read_text(encoding="utf-8"))
                    # Legacy calibration has no orientation and cannot safely be reused.
                    if not isinstance(saved, dict) or saved.get("orientation") != self.orientation:
                        return
                    values = calibration_values(saved.get("calibration"))
                except (OSError, ValueError, TypeError):
                    return
                self.call("qm.restoreCalibration", *values)
            return
        calibration_values(value)
        record = {"orientation": self.orientation, "calibration": value}
        if record != self.saved:
            save_json(self.path, record)
            self.saved = record
        self.status(touch="calibrated")

    def sync_results(self, state):
        request = self.call("qm.view")
        if not isinstance(request, str) or not re.fullmatch(r"\d{1,10},(?:[0-9]|10),\d{1,4}", request):
            raise ValueError("Invalid display view")
        sequence, kind, page = map(int, request.split(","))
        if kind == 0:
            self.last_result = None
            return
        total, status, payload = result_page(state, kind, page, controls=self.controls)
        current = (sequence, total, status, payload)
        if current != self.last_result:
            # Factory RouterBridge accepts only 256-byte RPC packets. Stage ASCII
            # chunks, then commit the page atomically; never stream a whole page.
            for offset in range(0, max(1, len(payload)), 128):
                if self.call("qm.resultChunk", sequence, offset, payload[offset:offset + 128]) is not True:
                    return
            # A tap may change the page while a response is in flight; retry next cycle.
            if self.call("qm.results", sequence, total, status) is True:
                self.last_result = current

    def cycle(self):
        state = self.service.snapshot()
        if state["error"]:
            headline = str(state['error'])[:68]
        elif state["stopping"]:
            headline = "Stopping survey"
        elif state["busy"]:
            headline = "Running: " + state["busy"]
        elif state["mission"]:
            headline = "Survey recording"
        else:
            headline = f"Ready / WiFi {len(state['wifi'])} / BLE {len(state['ble'])}"
        accepted = self.call("qm.update", min(len(state["wifi"]),9999),
                             min(len(state["ble"]),9999), min(len(state["sessions"]),9999),
                             bool(state["gps"]), headline)
        if accepted is not True:
            raise ConnectionError("Display rejected its view model")
        self.handle_action(self.call("qm.action"))
        if self.controls:
            prompt = state.get('pairing') or {}
            current = (prompt.get('id',''), prompt.get('kind',''), str(prompt.get('code','')), bool(prompt.get('answered')))
            if current != self.pair_prompt:
                if self.call('qm.pairPrompt', *current) is True: self.pair_prompt = current
        if self.sync_orientation():
            self.sync_theme()
            self.sync_calibration()
            self.sync_results(state)
        self.status(connected=True, error=None)

    def run(self):
        linked = False
        previous_uptime = None
        while not self.stop.is_set():
            try:
                if not linked:
                    protocol = self.call("qm.protocol")
                    if not isinstance(protocol, str) or not protocol.startswith(("qm-display/7;", "qm-display/8;", "qm-display/9;", "qm-display/10;")):
                        raise ConnectionError("Compatible portrait display firmware is required")
                    self.controls = protocol.startswith(('qm-display/8;', 'qm-display/9;', 'qm-display/10;'))
                    self.pair_prompt = None
                    details = self.call("qm.diagnostics")
                    match = re.search(r"uptime_ms=(\d+)", details)
                    uptime = int(match[1]) if match else 0
                    if previous_uptime is not None and uptime < previous_uptime:
                        self.handled = None
                    previous_uptime = uptime
                    self.restore_attempted = False
                    self.orientation_restore_attempted = False
                    self.last_result = None
                    self.status(protocol=protocol, details=details)
                    linked = True
                self.cycle()
            except (OSError, ValueError, TypeError, subprocess.SubprocessError) as exc:
                self.status(connected=False, error=str(exc)[:150])
                linked = False
            self.stop.wait(2)

    def close(self):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=25)
