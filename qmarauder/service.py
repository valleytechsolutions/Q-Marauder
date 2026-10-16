"""Single radio worker, bounded jobs, and durable survey sessions."""
import copy
import base64
import json
import queue
import threading
import time
from pathlib import Path
from . import __version__, gps, radio, lab, ble, settings, pairing
from .ble_data import detections, decode
from .detectors import evaluate, MODES
from . import vendors, capture, linux_tools
from .storage import Store, utcnow


class Service:
    def __init__(self, data_dir):
        self.store = Store(data_dir)
        self.lock = threading.RLock()
        self.jobs = queue.Queue(maxsize=1)
        self.shutdown_event = threading.Event()
        self.advertising_stop = threading.Event()
        self.state = dict(version=__version__, wifi=[], ble=[], gps=None, busy=None,
                          error=None, updated=None, mission=None, stopping=False, lab=self.store.latest_lab(),
                          scan_status={"wifi": {"state": "idle"}, "ble": {"state": "idle"}},
                          display=dict(connected=False, touch="uncalibrated", error=None),
                          capabilities=radio.diagnostics())
        self.state.update(settings=settings.load(data_dir), pending_theme=None, ble_lab=None, detections=[])
        self.state['pending_theme'] = self.state['settings']['theme']
        self.state['pairing'] = None
        self.state['detector_modes'] = MODES
        self.state['packet_lab'] = self.store.latest_packet()
        self.state['linux_tools'] = linux_tools.TOOLS
        self.state['linux_report'] = self.store.latest_linux()
        report_times = [(self.state[key] or {}).get('updated') for key in ('packet_lab', 'linux_report')]
        self.state['updated'] = max((when for when in report_times if when), default=None)
        self.state['vendor_database'] = vendors.status()
        for kind in ('wifi','ble'):
            rows, when = self.store.latest_scan(kind)
            if when:
                for index,row in enumerate(rows):
                    if kind == 'ble': rows[index] = decode(row)
                    else: row['oui_vendor'] = vendors.lookup(row.get('address'))
                self.state[kind] = rows
                self.state['scan_status'][kind] = dict(state='cached', updated=when)
                self.state['updated'] = max(self.state['updated'] or when, when)
        self.pairing = pairing.PairingBroker(self.lock, self.state)
        self.features = json.loads((Path(__file__).with_name("features.json")).read_text(encoding="utf-8"))
        self.worker = threading.Thread(target=self._work, name="radio-worker", daemon=True)
        self.worker.start()

    def snapshot(self):
        with self.lock:
            state = copy.deepcopy(self.state)
        if state["gps"] and not gps.validate_fix({"class":"TPV", **state["gps"]}):
            state["gps"] = None
        state["sessions"] = self.store.sessions()
        state['linux_history'] = self.store.linux_history()
        state["features"] = self.features
        return state

    def set_settings(self, values):
        values = settings.validate(values)
        with self.lock:
            if self.state['busy'] and set(values) - {'theme'}:
                raise RuntimeError('Wait for the current radio job before changing its settings')
            updated = {**self.state['settings'], **values}
            settings.save(self.store.root, updated)
            self.state['settings'] = updated
            if 'theme' in values: self.state['pending_theme'] = values['theme']

    def submit(self, action, parameters=None):
        if action not in ("wifi", "ble", "diagnostics", "mission-start", "mission-stop", 'ble-advert-stop', 'linux-open', *lab.ACTIONS, *ble.ACTIONS, *capture.ACTIONS, *linux_tools.ACTIONS):
            raise ValueError("Unknown action")
        with self.lock:
            if action == 'ble-advert-stop':
                if self.state['busy'] == 'ble-advertise': self.advertising_stop.set()
                return
            if action == "mission-stop":
                if self.state["mission"]:
                    self.state["stopping"] = True
                return
            if self.state["busy"] or self.state["mission"]:
                raise RuntimeError("A radio task is already running. Stop the survey before starting another task.")
            if action == 'linux-open':
                if not isinstance(parameters, dict) or set(parameters) != {'session'}: raise ValueError('Select a saved Linux report')
                self.state['linux_report'] = self.store.linux_report(parameters['session'])
                return
            request = ble.request_for(action, self.state['settings'], parameters) if action in ble.ACTIONS else None
            if parameters and action not in ble.ACTIONS: raise ValueError('This action accepts no parameters')
            self.state.update(busy=action, error=None)
            self.advertising_stop.clear()
            if action in ("wifi", "ble"):
                self.state["scan_status"][action] = {"state": "running"}
            if action in lab.ACTIONS:
                self.state["lab"] = {"action": action, "state": "running"}
            if action in ble.ACTIONS:
                self.state['ble_lab'] = dict(action=action, state='running')
            if action in capture.ACTIONS:
                self.state['packet_lab'] = dict(action=action, state='running')
            if action in linux_tools.ACTIONS:
                self.state['linux_report'] = dict(action=action, state='running')
            self.jobs.put_nowait((action, request))

    def pairing_reply(self, answer):
        self.pairing.respond(answer)

    def cancel_pairing(self):
        self.pairing.cancel()

    def _scan(self, kind, session=None):
        if kind == 'wifi':
            rows = radio.wifi_scan()
            for row in rows: row['oui_vendor'] = vendors.lookup(row.get('address'))
        else:
            rows = ble.call(ble.request_for('ble', self.state['settings']))['rows']
        fix = gps.read_fix()
        if session:
            self.store.append(session, rows, fix)
        with self.lock:
            self.state.update({kind: rows, "gps": fix, "updated": utcnow()})
            self.state["scan_status"][kind] = {"state": "done", "updated": utcnow()}

    def _work(self):
        next_scan = 0.0
        while not self.shutdown_event.is_set():
            with self.lock:
                mission, stopping = self.state["mission"], self.state["stopping"]
            if mission and stopping:
                self.store.stop(mission)
                with self.lock:
                    self.state.update(mission=None, stopping=False, busy=None)
                continue
            if mission and time.monotonic() >= next_scan:
                with self.lock:
                    self.state.update(busy="survey", error=None)
                try:
                    self._scan("wifi", mission)
                except Exception as exc:
                    with self.lock:
                        self.state["error"] = str(exc)[:500]
                finally:
                    with self.lock:
                        self.state["busy"] = None
                next_scan = time.monotonic() + 10
                continue
            try:
                action, request = self.jobs.get(timeout=0.2)
            except queue.Empty:
                continue
            session = None
            try:
                if action == "mission-start":
                    mission = self.store.start("wifi-survey")
                    with self.lock:
                        self.state.update(mission=mission, stopping=False)
                    next_scan = 0
                elif action == "diagnostics":
                    capabilities = radio.diagnostics()
                    with self.lock:
                        self.state["capabilities"] = capabilities
                elif action in linux_tools.ACTIONS:
                    session = self.store.start(action)
                    if action == 'wifi-changes':
                        report = linux_tools.run(action, self.state['settings'], self.store.latest_wifi_report())
                    else: report = linux_tools.run(action, self.state['settings'])
                    report.update(updated=utcnow(), session=session)
                    self.store.append(session, [report])
                    with self.lock:
                        self.state['linux_report'] = report
                        self.state['updated'] = report['updated']
                elif action in capture.ACTIONS:
                    session = self.store.start(action)
                    report, raw = capture.run(action, self.state['settings'])
                    self.store.save_capture(session, raw)
                    report.update(capture_session=session, kind='packet-lab', state='done', updated=utcnow())
                    self.store.append(session, [report])
                    with self.lock:
                        self.state['packet_lab'] = report
                        self.state['updated'] = report['updated']
                elif action in lab.ACTIONS:
                    session = self.store.start(action)
                    report = lab.call(lab.ACTIONS[action])
                    if action == 'wifi-capture':
                        raw = base64.b64decode(report.pop('pcap'), validate=True)
                        self.store.save_capture(session, raw)
                        report['capture_session'] = session
                    report = {**report, "kind": "lab", "state": "done", "updated": utcnow()}
                    self.store.append(session, [report])
                    with self.lock:
                        self.state["lab"] = report
                elif action in ble.ACTIONS:
                    session = self.store.start(action)
                    report = pairing.call(request, self.pairing) if action == 'ble-pair' else ble.call(request, self.advertising_stop) if action == 'ble-advertise' else ble.call(request)
                    report['updated'] = utcnow()
                    if action == 'ble-detect':
                        report['detections'] = detections(report['rows'], self.state['settings']['rules'])
                        report['note'] = 'Configured watchlist matches only; no verified surveillance identities. BlueZ discovery may send scan requests.'
                    elif action in ('ble-axon','ble-detector'):
                        report['detections'] = evaluate(report['rows'], action, self.state['settings']['rules'])
                        report['note'] = 'Candidate identifier matches; not verified identities. BlueZ discovery may transmit scan requests.'
                    self.store.append(session, [report])
                    with self.lock:
                        self.state['ble_lab'] = report
                        self.state['updated'] = report['updated']
                        if 'rows' in report and action != 'ble-foxhunt':
                            self.state['ble'] = report['rows']
                            self.state['scan_status']['ble'] = dict(state='done', updated=utcnow())
                        if 'detections' in report: self.state['detections'] = report['detections']
                else:
                    session = self.store.start(action)
                    self._scan(action, session)
            except Exception as exc:
                with self.lock:
                    self.state["error"] = str(exc)[:500]
                    if action in linux_tools.ACTIONS:
                        report = dict(kind='linux-tool', action=action, state='error', error=str(exc)[:300], updated=utcnow())
                        self.state['linux_report'] = report
                        if session:
                            try: self.store.append(session, [report])
                            except Exception: report['error'] += ' (Report could not be saved.)'
                    if action in capture.ACTIONS:
                        self.state['packet_lab'] = dict(action=action, state='error', error=str(exc)[:300])
                        if session:
                            try: self.store.append(session, [self.state['packet_lab']])
                            except Exception: self.state['packet_lab']['error'] += ' (Report could not be saved.)'
                    if action in ("wifi", "ble"):
                        self.state["scan_status"][action] = {"state": "error", "error": str(exc)[:300]}
                    if action in lab.ACTIONS:
                        self.state["lab"] = {"kind": "lab", "state": "error", "action": lab.ACTIONS[action], "error": str(exc)[:300], "updated": utcnow()}
                        if session:
                            try:
                                self.store.append(session, [self.state["lab"]])
                            except Exception:
                                self.state["lab"]["error"] += " (Report could not be saved.)"
                    if action in ble.ACTIONS:
                        self.state['ble_lab'] = dict(kind='ble-lab', action=action, state='error', error=str(exc)[:300], updated=utcnow())
                        if session:
                            try: self.store.append(session, [self.state['ble_lab']])
                            except Exception: self.state['ble_lab']['error'] += ' (Report could not be saved.)'
            finally:
                if session:
                    self.store.stop(session)
                with self.lock:
                    self.state["busy"] = None
                self.jobs.task_done()
        with self.lock:
            mission = self.state["mission"]
        if mission:
            self.store.stop(mission)

    def close(self):
        self.shutdown_event.set()
        if self.pairing.active:
            try: self.pairing.cancel()
            except RuntimeError: pass
        self.worker.join(timeout=65)
