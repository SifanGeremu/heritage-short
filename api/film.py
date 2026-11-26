"""Vercel entry. One dry film, then the bytes come back on the same request.

The laptop server still paints in the background and is polled. This host has
no shared disk between calls, so the preview finishes before the response.
"""

import base64
import json
import os
import shutil
import sys
import tempfile
from http.server import BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "family"))

from board import build  # noqa: E402
from render import render  # noqa: E402


def _ffmpeg() -> None:
    if shutil.which("ffmpeg"):
        return
    import imageio_ffmpeg

    exe = Path(imageio_ffmpeg.get_ffmpeg_exe())
    folder = Path("/tmp/ffmpeg-bin")
    folder.mkdir(exist_ok=True)
    link = folder / "ffmpeg"
    if not link.exists():
        link.symlink_to(exe)
    os.environ["PATH"] = str(folder) + os.pathsep + os.environ.get("PATH", "")


class handler(BaseHTTPRequestHandler):
    def _json(self, code: int, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or "0")
        if length <= 0 or length > 20_000:
            self._json(400, {"error": "the letter is empty"})
            return
        try:
            answers = json.loads(self.rfile.read(length))
            if not isinstance(answers, dict):
                raise ValueError("expected a letter")
            board = build(answers)
            _ffmpeg()
            with tempfile.TemporaryDirectory() as tmp:
                dest = Path(tmp) / "film"
                render(board, dest, dry=True)
                film = (dest / "film.mp4").read_bytes()
        except (json.JSONDecodeError, ValueError, RuntimeError) as err:
            self._json(400, {"error": str(err)[:500]})
            return
        except Exception as err:
            self._json(500, {"error": str(err)[:500]})
            return
        encoded = base64.b64encode(film).decode("ascii")
        self._json(200, {"status": "ready", "film": "data:video/mp4;base64," + encoded})
