"""Single radio worker, bounded jobs, and durable survey sessions."""
import copy
import json
import queue
import threading
import time
from pathlib import Path
from . import __version__, gps, radio
from .storage import Store, utcnow


class Service:
    def __init__(self, data_dir):
        self.store = Store(data_dir)
        self.lock = threading.RLock()
        self.jobs = queue.Queue(maxsize=1)
        self.shutdown_event = threading.Event()
        self.state = dict(version=__version__, wifi=[], ble=[], gps=None, busy=None,
                          error=None, updated=None, mission=None, stopping=False,
                          display=dict(connected=False, touch="uncalibrated", error=None),
                          capabilities=radio.diagnostics())
        self.features = json.loads((Path(__file__).with_name("features.json")).read_text(encoding="utf-8"))
        self.worker = threading.Thread(target=self._work, name="radio-worker", daemon=True)
        self.worker.start()

    def snapshot(self):
        with self.lock:
            state = copy.deepcopy(self.state)
        if state["gps"] and not gps.validate_fix({"class":"TPV", **state["gps"]}):
            state["gps"] = None
        state["sessions"] = self.store.sessions()
        state["features"] = self.features
        return state

    def submit(self, action):
        if action not in ("wifi", "ble", "diagnostics", "mission-start", "mission-stop"):
            raise ValueError("Unknown action")
        with self.lock:
            if action == "mission-stop":
                if self.state["mission"]:
                    self.state["stopping"] = True
                return
            if self.state["busy"] or self.state["mission"]:
                raise RuntimeError("A radio task is already running. Stop the survey before starting another task.")
            self.state.update(busy=action, error=None)
            self.jobs.put_nowait(action)

    def _scan(self, kind, session=None):
        rows = radio.wifi_scan() if kind == "wifi" else radio.ble_scan()
        fix = gps.read_fix()
        if session:
            self.store.append(session, rows, fix)
        with self.lock:
            self.state.update({kind: rows, "gps": fix, "updated": utcnow()})

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
                action = self.jobs.get(timeout=0.2)
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
                else:
                    session = self.store.start(action)
                    self._scan(action, session)
            except Exception as exc:
                with self.lock:
                    self.state["error"] = str(exc)[:500]
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
        self.worker.join(timeout=35)
