"""Process lock prevents two workers from writing the same session database."""
from contextlib import contextmanager
from pathlib import Path
import os


@contextmanager
def instance_lock(data_dir):
    root = Path(data_dir)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (root / "instance.lock").open("a+b") as file:
        file.seek(0, 2)
        if file.tell() == 0:
            file.write(b"0")
            file.flush()
        file.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError("Another Q-Marauder process is using this data directory") from exc
        try:
            yield
        finally:
            file.seek(0)
            if os.name == "nt":
                msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(file.fileno(), fcntl.LOCK_UN)
