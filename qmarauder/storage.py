"""Local append-only observations, with session isolation and CSV escaping."""
import csv
import datetime as dt
import io
import json
import sqlite3
import uuid
import re
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
            return [{**dict(row),'pcap':(self.root/(row['id']+'.pcap')).is_file()} for row in db.execute("""SELECT s.*, count(o.id) AS observations,
                count(o.lat) AS geotagged FROM sessions s LEFT JOIN observations o ON s.id=o.session
                GROUP BY s.id ORDER BY s.started DESC LIMIT 100""")]

    def save_capture(self, identity, payload):
        if not re.fullmatch(r'[0-9a-f]{32}',identity) or not 24 <= len(payload) <= 524288:
            raise ValueError('Invalid capture')
        path = self.root/(identity+'.pcap')
        with path.open('xb') as output: output.write(payload)
        path.chmod(0o600)

    def latest_lab(self):
        with self.connect() as db:
            row = db.execute("""SELECT s.mode, o.payload FROM sessions s
                LEFT JOIN observations o ON o.session=s.id
                WHERE s.mode IN ('lab-recon', 'lab-injection', 'lab-deauth', 'wifi-capture')
                ORDER BY s.started DESC, o.id DESC LIMIT 1""").fetchone()
        if row is None:
            return None
        if row["payload"]:
            return json.loads(row["payload"])
        return {"state": "error", "action": row["mode"],
                "error": "Previous radio job was interrupted; outcome unknown. It was not restarted."}

    def latest_scan(self, kind):
        if kind not in ('wifi','ble'): raise ValueError('Unknown scan type')
        with self.connect() as db:
            session = db.execute('SELECT id,started FROM sessions WHERE mode=? AND ended IS NOT NULL ORDER BY started DESC LIMIT 1',(kind,)).fetchone()
            if not session: return [], None
            rows = [json.loads(row['payload']) for row in db.execute('SELECT payload FROM observations WHERE session=? ORDER BY id LIMIT 1000',(session['id'],))]
            return rows, session['started']

    def latest_packet(self):
        with self.connect() as db:
            row = db.execute("""SELECT o.payload FROM sessions s LEFT JOIN observations o ON o.session=s.id
                WHERE s.mode IN ('flock-wifi','flock-ble','sky-wifi','sky-ble','ble-sniff','packet-detector','axon-wifi')
                ORDER BY s.started DESC, o.id DESC LIMIT 1""").fetchone()
        if row is None: return None
        return json.loads(row['payload']) if row['payload'] else dict(state='error', error='Previous capture was interrupted; it was not restarted.')

    def export(self, identity, fmt):
        with self.connect() as db:
            if not db.execute("SELECT 1 FROM sessions WHERE id=?", (identity,)).fetchone():
                raise KeyError("Unknown session")
            if fmt == 'pcap':
                if not re.fullmatch(r'[0-9a-f]{32}',identity): raise KeyError('Unknown capture')
                try: return (self.root/(identity+'.pcap')).read_bytes()
                except FileNotFoundError: raise KeyError('Session has no packet capture') from None
            rows = [{**json.loads(row["payload"]), "time": row["time"], "lat": row["lat"], "lon": row["lon"]}
                    for row in db.execute("SELECT * FROM observations WHERE session=? ORDER BY id", (identity,))]
        if fmt == "json":
            return json.dumps(rows, ensure_ascii=False).encode()
        output = io.StringIO(newline="")
        fields = ["time", "kind", "address", "name", "channel", "frequency", "signal", "rssi", "security", "lat", "lon",
                  "action", "state", "interface", "bssid", "monitor_frequency", "received", "decoded", "frames",
                  "beacons", "deauth_seen", "stations", "sent", "probe_responses", "capture_observed", "injection_observed", "note", "error"]
        writer = csv.DictWriter(output, fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: csv_cell(value) for key, value in row.items()})
        return output.getvalue().encode("utf-8")
