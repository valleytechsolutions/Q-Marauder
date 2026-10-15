"""Optional native TFT bridge via Arduino's locally installed router CLI."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import threading

ACTIONS = {1: "wifi", 2: "ble", 3: "mission-start", 4: "mission-stop"}


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
    if not isinstance(value, str) or not re.fullmatch(r"[01],\d{1,4},\d{1,4}", value):
        raise ValueError("Invalid touch calibration")
    axis, top, bottom = map(int, value.split(","))
    if not (0 <= top <= 1023 and 0 <= bottom <= 1023 and abs(top-bottom) >= 250):
        raise ValueError("Invalid touch span")
    return axis, top, bottom


class DisplayLink:
    def __init__(self, service, data_dir, call=rpc):
        self.service, self.call = service, call
        self.path = Path(data_dir) / "touch-calibration.json"
        self.stop = threading.Event()
        self.thread = None
        self.handled = None
        self.reply = ""
        self.restore_attempted = False
        self.saved = None

    def start(self):
        if not shutil.which("arduino-router-cli") or not Path("/var/run/arduino-router.sock").exists():
            return
        self.thread = threading.Thread(target=self.run, name="tft-bridge", daemon=True)
        self.thread.start()

    def status(self, **values):
        with self.service.lock:
            self.service.state["display"].update(values)

    def handle_action(self, value):
        if not isinstance(value, str) or not re.fullmatch(r"\d{1,10},\d{1,2}", value):
            raise ValueError("Invalid display action")
        sequence, action = map(int, value.split(","))
        if action == 0:
            self.handled = None
            return
        if self.handled != (sequence, action):
            if action not in ACTIONS:
                self.reply = "This action is not supported."
            else:
                try:
                    self.service.submit(ACTIONS[action])
                    self.reply = "Task accepted. Results and exports are available in the USB console."
                except (RuntimeError, ValueError) as exc:
                    self.reply = str(exc)[:120]
            # Keep the result until acknowledged, even across a transient RPC error.
            self.handled = (sequence, action)
        if self.call("qm.ack", sequence, self.reply) is not True:
            raise ConnectionError("Display action acknowledgement failed")

    def sync_calibration(self):
        value = self.call("qm.calibration")
        if value == "uncalibrated":
            self.status(touch="uncalibrated")
            if not self.restore_attempted:
                self.restore_attempted = True
                try:
                    saved = json.loads(self.path.read_text(encoding="utf-8"))
                    values = calibration_values(saved)
                except (OSError, ValueError, TypeError):
                    return
                self.call("qm.restoreCalibration", *values)
            return
        calibration_values(value)
        if value != self.saved:
            self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(json.dumps(value), encoding="utf-8")
            temporary.replace(self.path)
            self.saved = value
        self.status(touch="calibrated")

    def cycle(self):
        state = self.service.snapshot()
        if state["error"]:
            headline = "Task failed - check USB console"
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
        self.sync_calibration()
        self.status(connected=True, error=None)

    def run(self):
        linked = False
        previous_uptime = None
        while not self.stop.is_set():
            try:
                if not linked:
                    protocol = self.call("qm.protocol")
                    if not isinstance(protocol, str) or not protocol.startswith("qm-display/2;"):
                        raise ConnectionError("Compatible portrait display firmware is required")
                    details = self.call("qm.diagnostics")
                    match = re.search(r"uptime_ms=(\d+)", details)
                    uptime = int(match[1]) if match else 0
                    if previous_uptime is not None and uptime < previous_uptime:
                        self.handled = None
                    previous_uptime = uptime
                    self.restore_attempted = False
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
