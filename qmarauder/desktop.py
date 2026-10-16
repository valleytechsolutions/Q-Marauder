"""XFCE application entry point. Reuse the local service; launch it on demand."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen


def available(port):
    try:
        with urlopen(f'http://127.0.0.1:{port}/api/state', timeout=2) as response:
            state = json.loads(response.read(2_000_000))
            return isinstance(state, dict) and {'features','display','version','scan_status'} <= state.keys()
    except (OSError, ValueError, URLError): return False


def launch(data_dir, port=8787, engine='auto'):
    if sys.platform != 'linux' or not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
        raise RuntimeError('Open Q-Marauder Lab from the UNO Q desktop after connecting a display and signing in.')
    from . import native_app
    native = engine != 'chromium' and native_app.available()
    if engine == 'native' and not native:
        raise RuntimeError('Native app needs python3-gi, gir1.2-gtk-3.0 and gir1.2-webkit2-4.1.')
    browser = shutil.which('chromium') or shutil.which('chromium-browser')
    if not native and not browser: raise RuntimeError('Install the native app dependencies or Debian chromium.')
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not available(port):
        log = data_dir/'desktop-service.log'
        if log.exists() and log.stat().st_size > 1_000_000: log.replace(log.with_suffix('.previous.log'))
        with log.open('ab') as output:
            process = subprocess.Popen([sys.executable, '-m', 'qmarauder', 'serve', '--port', str(port),
                                        '--data-dir', str(data_dir)], cwd=Path(__file__).resolve().parent.parent,
                                       stdin=subprocess.DEVNULL, stdout=output, stderr=output, start_new_session=True)
        for _ in range(30):
            if available(port): break
            if process.poll() is not None: raise RuntimeError('The local service could not start. See desktop-service.log in the data folder.')
            time.sleep(.5)
        else: raise RuntimeError('The local service is still starting. Open Q-Marauder Lab again shortly.')
    if native:
        native_app.launch(f'http://127.0.0.1:{port}/?desktop=1', data_dir)
        return
    subprocess.Popen([browser, '--app='+f'http://127.0.0.1:{port}/?desktop=1', '--start-maximized'],
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)
