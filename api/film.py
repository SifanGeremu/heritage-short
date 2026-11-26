"""Vercel entry. One dry film, then the bytes come back on the same request.

The project root on Vercel may be this directory or the repository root.
The laptop server still paints in the background and is polled. This host has
no shared disk between calls, so the preview finishes before the response.
"""

import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent


def _page() -> Path:
    for path in (
        HERE / "page.html",
        HERE.parent / "family" / "static" / "index.html",
    ):
        if path.is_file():
            return path
    raise FileNotFoundError("page.html")


def _family_root() -> Path | None:
    for root in (HERE.parent, HERE):
        if (root / "family" / "render.py").is_file() and (root / "family" / "board.py").is_file():
            return root
    return None


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


def _ff(args: list[str]) -> None:
    proc = subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "ffmpeg failed").strip()
        raise RuntimeError(detail[-500:])


def _need(answers: dict, key: str, limit: int) -> str:
    value = answers.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{key} is required")
    value = " ".join(value.split())
    if not value:
        raise ValueError(f"{key} is required")
    if len(value) > limit:
        raise ValueError(f"{key} is too long")
    return value


def _fallback_film(answers: dict, dest: Path) -> None:
    """Flat preview when family/ is outside this deploy. No API calls."""
    _need(answers, "name", 60)
    _need(answers, "who_om", 280)
    _need(answers, "object", 80)
    _need(answers, "memory_om", 280)
    _need(answers, "last_om", 280)
    lines = (
        _need(answers, "who_en", 280),
        _need(answers, "memory_en", 280),
        _need(answers, "last_en", 280),
    )
    dest.mkdir(parents=True, exist_ok=True)
    colors = ("0x3E4A57", "0x6B4A32", "0xC4A882")
    font = HERE / "DejaVuSans-Bold.ttf"
    clips: list[Path] = []
    for index, (line, color) in enumerate(zip(lines, colors), start=1):
        clip = dest / f"s{index}.mp4"
        text = line.replace("\\", " ").replace(":", " ").replace("'", "")[:80]
        vf = "scale=720:1280"
        if font.is_file():
            vf = (
                "drawtext=fontfile='"
                + font.as_posix()
                + f"':text='{text}':fontsize=36:fontcolor=white:"
                "x=(w-text_w)/2:y=h-180"
            )
        _ff(
            [
                "-f", "lavfi", "-i", f"color=c={color}:s=720x1280:d=6:r=24",
                "-f", "lavfi", "-i", "sine=frequency=196:sample_rate=44100:duration=6",
                "-vf", vf,
                "-shortest",
                "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-movflags", "+faststart",
                str(clip),
            ]
        )
        clips.append(clip)
    card = dest / "card.mp4"
    _ff(
        [
            "-f", "lavfi", "-i", "color=c=black:s=720x1280:d=3:r=24",
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-shortest",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            str(card),
        ]
    )
    clips.append(card)
    args: list[str] = []
    for clip in clips:
        args += ["-i", str(clip)]
    ins = "".join(f"[{i}:v][{i}:a]" for i in range(len(clips)))
    film = dest / "film.mp4"
    _ff(
        args
        + [
            "-filter_complex",
            f"{ins}concat=n={len(clips)}:v=1:a=1[v][a]",
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-movflags", "+faststart",
            str(film),
        ]
    )


def _paint(answers: dict, dest: Path) -> bytes:
    root = _family_root()
    _ffmpeg()
    if root is None:
        _fallback_film(answers, dest)
    else:
        sys.path.insert(0, str(root / "family"))
        from board import build
        from render import render

        render(build(answers), dest, dry=True)
    film = dest / "film.mp4"
    if not film.is_file():
        raise RuntimeError("the film was not written")
    return film.read_bytes()


class handler(BaseHTTPRequestHandler):
    def _json(self, code: int, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        if urlparse(self.path).path not in ("/", "/index.html"):
            self.send_error(404)
            return
        data = _page().read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
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
            with tempfile.TemporaryDirectory() as tmp:
                film = _paint(answers, Path(tmp) / "film")
        except (json.JSONDecodeError, ValueError, RuntimeError) as err:
            self._json(400, {"error": str(err)[:500]})
            return
        except Exception as err:
            self._json(500, {"error": str(err)[:500]})
            return
        encoded = base64.b64encode(film).decode("ascii")
        self._json(200, {"status": "ready", "film": "data:video/mp4;base64," + encoded})
