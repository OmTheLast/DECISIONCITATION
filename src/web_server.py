from __future__ import annotations

import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from .answer import explain_call
from .settings import CHUNKS_PATH, ROOT


WEB_ROOT = ROOT / "web"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_ROOT), **kwargs)

    def log_message(self, format: str, *args) -> None:
        print(f"[web] {self.address_string()} - {format % args}")

    def do_GET(self) -> None:
        if self.path == "/" or self.path.startswith("/?"):
            self.path = "/index.html"
        if self.path == "/api/health":
            self.write_json(
                {
                    "ok": True,
                    "index_ready": CHUNKS_PATH.exists(),
                    "chunks_path": str(CHUNKS_PATH),
                }
            )
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path != "/api/explain":
            self.send_error(HTTPStatus.NOT_FOUND, "Unknown endpoint")
            return

        try:
            payload = self.read_json()
            incident = str(payload.get("incident", "")).strip()
            call = str(payload.get("call", "")).strip()
            model = str(payload.get("model", "")).strip() or None
            if not incident or not call:
                self.write_json(
                    {"error": "Both incident and call are required."},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            result = explain_call(incident, call, model=model)
            self.write_json(result)
        except Exception as exc:
            self.write_json({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw or "{}")

    def write_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run(host: str = "127.0.0.1", port: int = 8765) -> None:
    if not WEB_ROOT.exists():
        raise FileNotFoundError(f"Web root not found: {WEB_ROOT}")

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Decision Citation UI running at http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    server.serve_forever()
