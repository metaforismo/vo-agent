"""Read-only, loopback-only research viewer and portable offline export."""
from __future__ import annotations

import re
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import cast
from urllib.parse import urlsplit

from quaestio.research import ResearchError, ResearchStore, StudySnapshot, serialize_json


def render_html(snapshot: StudySnapshot, *, live: bool = False) -> str:
    payload = serialize_json(snapshot).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    template = Path(__file__).with_name("research_view.html").read_text(encoding="utf-8")
    return template.replace("__LIVE__", "true" if live else "false").replace("__SNAPSHOT__", payload)


def handler_for(path: str | Path) -> type[BaseHTTPRequestHandler]:
    database = Path(path).resolve()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args: object) -> None:
            pass

        def _send(self, status: int, body: bytes, content_type: str, *, attachment: bool = False) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'unsafe-inline'; "
                             "style-src 'unsafe-inline'; connect-src 'self'; img-src data:; "
                             "frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
            if attachment:
                self.send_header("Content-Disposition", 'attachment; filename="research-evidence.bin"')
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            # Reject foreign Host headers so DNS rebinding cannot expose local studies.
            host = self.headers.get("Host", "")
            port = cast(ThreadingHTTPServer, self.server).server_port
            if host not in {f"127.0.0.1:{port}", f"localhost:{port}"}:
                self._send(403, b"Local host required", "text/plain; charset=utf-8")
                return
            route = urlsplit(self.path).path
            try:
                with ResearchStore(database) as store:
                    if route == "/":
                        self._send(200, render_html(store.snapshot(), live=True).encode(), "text/html; charset=utf-8")
                    elif route == "/api/graph":
                        self._send(200, serialize_json(store.snapshot()).encode(), "application/json; charset=utf-8")
                    elif re.fullmatch(r"/api/artifacts/[0-9a-f]{32}", route):
                        self._send(200, store.artifact_bytes(route.rsplit("/", 1)[1]),
                                   "application/octet-stream", attachment=True)
                    else:
                        self._send(404, b"Not found", "text/plain; charset=utf-8")
            except ResearchError:
                self._send(404, b"Record unavailable", "text/plain; charset=utf-8")
            except (OSError, sqlite3.Error):
                self._send(500, b"Study could not be read", "text/plain; charset=utf-8")

    return Handler


def serve(path: str | Path, port: int) -> None:
    if type(port) is not int or not 1 <= port <= 65535:
        raise ResearchError("port must be an integer between 1 and 65535")
    with ResearchStore(path) as store:
        store.snapshot()
    with ThreadingHTTPServer(("127.0.0.1", port), handler_for(path)) as server:
        print(f"Read-only research view: http://127.0.0.1:{port}/", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
