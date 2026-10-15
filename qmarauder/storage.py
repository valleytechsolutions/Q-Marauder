"""Local append-only observations, with session isolation and CSV escaping."""
import csv
import datetime as dt
import io
import json
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path


def utcnow():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def csv_cell(value):
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = self.root / "observations.sqlite3"
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY, started TEXT NOT NULL, ended TEXT, mode TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS observations (
                    id INTEGER PRIMARY KEY, session TEXT NOT NULL REFERENCES sessions(id),
                    time TEXT NOT NULL, payload TEXT NOT NULL, lat REAL, lon REAL);
                CREATE INDEX IF NOT EXISTS obs_session ON observations(session);
            """)
            # A process restart closes incomplete missions instead of silently resuming RF work.
            db.execute("UPDATE sessions SET ended=? WHERE ended IS NULL", (utcnow(),))
        self.path.chmod(0o600)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.execute("PRAGMA foreign_keys=ON")
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def start(self, mode):
        identity = uuid.uuid4().hex
        with self.connect() as db:
            db.execute("INSERT INTO sessions VALUES (?, ?, NULL, ?)", (identity, utcnow(), mode))
        return identity

    def stop(self, identity):
        with self.connect() as db:
            db.execute("UPDATE sessions SET ended=? WHERE id=?", (utcnow(), identity))

    def append(self, identity, rows, fix=None):
        when = utcnow()
        with self.connect() as db:
            db.executemany("INSERT INTO observations(session,time,payload,lat,lon) VALUES (?,?,?,?,?)",
                           [(identity, when, json.dumps(row, ensure_ascii=False),
                             fix["lat"] if fix else None, fix["lon"] if fix else None) for row in rows])

    def sessions(self):
        with self.connect() as db:
            return [dict(row) for row in db.execute("""SELECT s.*, count(o.id) AS observations,
                count(o.lat) AS geotagged FROM sessions s LEFT JOIN observations o ON s.id=o.session
                GROUP BY s.id ORDER BY s.started DESC LIMIT 100""")]

    def export(self, identity, fmt):
        with self.connect() as db:
            if not db.execute("SELECT 1 FROM sessions WHERE id=?", (identity,)).fetchone():
                raise KeyError("Unknown session")
            rows = [{**json.loads(row["payload"]), "time": row["time"], "lat": row["lat"], "lon": row["lon"]}
                    for row in db.execute("SELECT * FROM observations WHERE session=? ORDER BY id", (identity,))]
        if fmt == "json":
            return json.dumps(rows, ensure_ascii=False).encode()
        output = io.StringIO(newline="")
        fields = ["time", "kind", "address", "name", "channel", "frequency", "signal", "rssi", "security", "lat", "lon"]
        writer = csv.DictWriter(output, fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: csv_cell(value) for key, value in row.items()})
        return output.getvalue().encode("utf-8")
