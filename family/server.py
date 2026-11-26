#!/usr/bin/env python3
"""One local page. A relative tells three things and gets a short film back."""

import json
import os
import re
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from board import build  # noqa: E402
from render import render  # noqa: E402

STATIC = Path(__file__).resolve().parent / "static" / "index.html"
FAMILY = ROOT / "outputs" / "family"
HOST = "127.0.0.1"
PORT = 8765
MEDIA = {"ref.jpg", "s01.jpg", "s02.jpg", "s03.jpg", "film.mp4"}
ID = re.compile(r"^[a-f0-9]{8}$")


def _dry() -> bool:
    return os.environ.get("FAMILY_DRY", "").strip().lower() in ("1", "true", "yes")


PREVIEW = (
    "This hosted page paints a flat preview. It does not spend a voice key or an image key. "
    "On this machine, make family uses her voice."
)
REAL = "A real film uses her voice. A few minutes, a few birr. Two films fill the free day."


def _page() -> bytes:
    html = STATIC.read_text(encoding="utf-8")
    if not _dry():
        html = html.replace(PREVIEW, REAL, 1)
    return html.encode()


def _film_dir(film_id: str) -> Path:
    if not ID.fullmatch(film_id):
        raise ValueError("bad id")
    path = (FAMILY / film_id).resolve()
    if path.parent != FAMILY.resolve():
        raise ValueError("bad id")
    return path


def _publish(dest: Path, state: dict) -> None:
    film_id = state["id"]
    frames = [f"/media/{film_id}/{name}" for name in state.get("frames") or []]
    film = state.get("film")
    body = {
        "status": state.get("status") or "working",
        "step": state.get("step") or "",
        "frames": frames,
        "film": f"/media/{film_id}/{film}" if film else None,
        "error": state.get("error"),
    }
    tmp = dest / "status.tmp"
    tmp.write_text(json.dumps(body), encoding="utf-8")
    tmp.replace(dest / "status.json")


def _redact(text: str) -> str:
    sys.path.insert(0, str(ROOT / "pipeline"))
    from common import read_key, redact

    for name in ("CLOUDFLARE_API_TOKEN", "ADDIS-AI-API-KEY", "CLOUDFLARE_ACCOUNT_ID"):
        text = redact(text, read_key(name))
    return text[:500]


def _start(board: dict, dest: Path, film_id: str) -> None:
    state = {
        "id": film_id,
        "status": "working",
        "step": "Writing her voice",
        "frames": [],
        "film": None,
        "error": None,
    }
    lock = threading.Lock()

    def update(payload: dict) -> None:
        with lock:
            state.update(payload)
            _publish(dest, state)

    def run() -> None:
        try:
            render(board, dest, dry=_dry(), on_status=update)
        except Exception as err:
            update({"status": "error", "step": "It stopped.", "error": _redact(str(err))})

    update({})
    threading.Thread(target=run, daemon=True).start()


class FamilyHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        print(f"{self.address_string()} {fmt % args}")

    def _json(self, code: int, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _bytes(self, code: int, data: bytes, content_type: str, extra: dict | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-store")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)

    def _file(self, path: Path, content_type: str) -> None:
        if not path.is_file():
            self.send_error(404)
            return
        data = path.read_bytes()
        if content_type == "video/mp4":
            header = self.headers.get("Range")
            if header and header.startswith("bytes="):
                start_s, _, end_s = header[6:].partition("-")
                start = int(start_s) if start_s else 0
                end = int(end_s) if end_s else len(data) - 1
                end = min(end, len(data) - 1)
                if start > end or start < 0:
                    self.send_error(416)
                    return
                chunk = data[start:end + 1]
                self._bytes(
                    206,
                    chunk,
                    content_type,
                    {"Content-Range": f"bytes {start}-{end}/{len(data)}"},
                )
                return
        self._bytes(200, data, content_type)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._bytes(200, _page(), "text/html; charset=utf-8")
            return
        if path.startswith("/api/film/"):
            film_id = path.removeprefix("/api/film/")
            try:
                dest = _film_dir(film_id)
            except ValueError:
                self.send_error(404)
                return
            status = dest / "status.json"
            if not status.is_file():
                self.send_error(404)
                return
            self._file(status, "application/json; charset=utf-8")
            return
        if path.startswith("/media/"):
            parts = path.removeprefix("/media/").split("/")
            if len(parts) != 2 or parts[1] not in MEDIA:
                self.send_error(404)
                return
            try:
                dest = _film_dir(parts[0])
            except ValueError:
                self.send_error(404)
                return
            kind = "video/mp4" if parts[1].endswith(".mp4") else "image/jpeg"
            self._file(dest / parts[1], kind)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/film":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length") or "0")
        if length <= 0 or length > 20_000:
            self._json(400, {"error": "the letter is empty"})
            return
        try:
            answers = json.loads(self.rfile.read(length))
            if not isinstance(answers, dict):
                raise ValueError("expected a letter")
            board = build(answers)
        except (json.JSONDecodeError, ValueError) as err:
            self._json(400, {"error": str(err)})
            return
        film_id = uuid.uuid4().hex[:8]
        dest = FAMILY / film_id
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "board.json").write_text(json.dumps(board, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        _start(board, dest, film_id)
        self._json(200, {"id": film_id})


def main() -> None:
    FAMILY.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((HOST, PORT), FamilyHandler)
    print(f"http://{HOST}:{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
