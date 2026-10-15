import argparse
import json
import os
import signal
from pathlib import Path
from . import radio


def main():
    parser = argparse.ArgumentParser(description="Q-Marauder UNO Q field console")
    parser.add_argument("command", choices=("serve", "doctor"), nargs="?", default="serve")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--data-dir", type=Path,
                        default=Path.home() / ".local/share/q-marauder")
    args = parser.parse_args()
    if args.command == "doctor":
        print(json.dumps(radio.diagnostics(), indent=2))
        return
    os.umask(0o077)
    from .service import Service
    from .server import serve
    from .locking import instance_lock
    def stop(_signum, _frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    try:
        with instance_lock(args.data_dir):
            serve(Service(args.data_dir), args.port)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
