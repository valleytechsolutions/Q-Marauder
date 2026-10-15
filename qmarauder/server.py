"""Loopback-only console; no command execution or arbitrary file API."""
import json
import mimetypes
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

WEB = Path(__file__).with_name("web")


def local_authority(value):
    try:
        parsed = urlsplit("http://" + value)
        return (parsed.hostname in ("127.0.0.1", "localhost", "::1") and
                parsed.username is None and parsed.password is None and
                parsed.path == "" and not parsed.query and not parsed.fragment)
    except ValueError:
        return False


def handler_for(service):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def reply(self, code, payload, kind="application/json", filename=None):
            if kind == "application/json" and not isinstance(payload, bytes):
                payload = json.dumps(payload, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
            if filename:
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(payload)

        def valid_host(self):
            if not local_authority(self.headers.get("Host", "")):
                self.reply(403, {"error": "Loopback access only"})
                return False
            return True

        def do_GET(self):
            if not self.valid_host():
                return
            path = urlsplit(self.path).path
            if path == "/api/state":
                self.reply(200, service.snapshot())
                return
            match = re.fullmatch(r"/api/export/([0-9a-f]{32})\.(csv|json)", path)
            if match:
                identity, fmt = match.groups()
                try:
                    data = service.store.export(identity, fmt)
                    self.reply(200, data, "text/csv; charset=utf-8" if fmt == "csv" else "application/json",
                               f"q-marauder-{identity}.{fmt}")
                except KeyError:
                    self.reply(404, {"error": "Unknown session"})
                return
            # Only fixed static paths; no filesystem paths accepted from clients.
            files = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css",
                     "/assets/bwm.png": "assets/bwm.png", "/assets/marauder.webp": "assets/marauder.webp"}
            if path not in files or not (WEB / files[path]).is_file():
                self.reply(404, {"error": "Not found"})
                return
            file = WEB / files[path]
            self.reply(200, file.read_bytes(), mimetypes.guess_type(file.name)[0] or "application/octet-stream")

        def do_POST(self):
            if not self.valid_host():
                return
            origin = self.headers.get("Origin")
            expected = "http://" + self.headers.get("Host", "")
            if (origin is not None and origin != expected) or self.headers.get("X-QM-Request") != "1":
                self.reply(403, {"error": "Same-origin request required"})
                return
            if self.headers.get_content_type() != "application/json":
                self.reply(415, {"error": "JSON required"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 1024:
                    raise ValueError("Invalid request length")
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict) or not isinstance(body.get("action"), str):
                    raise ValueError("Expected an action")
                if self.path != "/api/action":
                    self.reply(404, {"error": "Not found"})
                    return
                service.submit(body["action"])
                self.reply(202, {"accepted": True})
            except (ValueError, UnicodeError) as exc:
                self.reply(400, {"error": str(exc)})
            except RuntimeError as exc:
                self.reply(409, {"error": str(exc)})

    return Handler


def serve(service, port=8787):
    server = ThreadingHTTPServer(("127.0.0.1", port), handler_for(service))
    try:
        print(f"Q-Marauder listening on http://127.0.0.1:{port}", flush=True)
        server.serve_forever()
    finally:
        server.server_close()
        service.close()
