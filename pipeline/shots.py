#!/usr/bin/env python3
"""Still keyframes to short clips. FFmpeg zoompan, centred, 1080x1920 at 24 fps.

Movement comes from the shot's motion_prompt: push-in, pull-back, or drift.
A locked camera gets a smaller drift so it is not a frozen frame. Shots with
no keyframe are skipped. A clip is reused when the keyframe and the move match.
"""

import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ROOT, log_run
from validate import ensure_storyboard

OUT_DIR = ROOT / "outputs" / "shots"
KEY_DIR = ROOT / "outputs" / "keyframes"
CACHE_PATH = OUT_DIR / "cache.json"
FPS = 24
WIDTH = 1080
HEIGHT = 1920


def move_kind(prompt: str) -> str:
    text = prompt.lower()
    if "pull-back" in text or "pull back" in text:
        return "pull-back"
    if "push-in" in text or "push in" in text:
        return "push-in"
    if "drift" in text:
        return "drift"
    return "hold"


def zoompan(kind: str, frames: int) -> str:
    """Slow move. Zoom stays at or above 1 so the frame never shows past the photo.

    x and y stay on the centre. Drift is a few percent of the portrait frame.
    """
    n = max(frames - 1, 1)
    cx = "iw/2-(iw/zoom/2)"
    cy = "ih/2-(ih/zoom/2)"
    if kind == "push-in":
        z, x, y = f"1+0.06*on/{n}", cx, cy
    elif kind == "pull-back":
        z, x, y = f"1.08-0.08*on/{n}", cx, cy
    elif kind == "drift":
        z = "1.04"
        x = f"{cx}+(on/{n}-0.5)*iw*0.03"
        y = cy
    else:
        z = "1.02"
        x = cx
        y = f"{cy}+(on/{n}-0.5)*ih*0.012"
    return f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS}"


def cache_key(keyframe: bytes, params: dict) -> str:
    payload = json.dumps(
        {"keyframe": hashlib.sha256(keyframe).hexdigest(), "params": params},
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_cache() -> dict:
    if not CACHE_PATH.is_file():
        return {}
    try:
        data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def save_cache(cache: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2) + "\n", encoding="utf-8")


def keyframe_for(sid: str) -> Path | None:
    found = []
    for ext in ("jpg", "jpeg", "png", "webp"):
        found.extend(KEY_DIR.glob(f"{sid}_*.{ext}"))
    if not found:
        return None
    return max(found, key=lambda path: path.stat().st_mtime)


def render(image: Path, dest: Path, kind: str, frames: int) -> str | None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_suffix(".part.mp4")
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(image),
        "-vf", zoompan(kind, frames),
        "-frames:v", str(frames),
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(partial),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        partial.unlink(missing_ok=True)
        detail = (proc.stderr or proc.stdout or "ffmpeg failed").strip()
        return detail[-2000:]
    partial.replace(dest)
    return None


def _log(record: dict, started: float, status: str, error: str | None = None) -> None:
    record = dict(record)
    record.update(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "latency": round(time.perf_counter() - started, 3),
            "cost": 0,
            "status": status,
            "seed": None,
        }
    )
    if error:
        record["error"] = error[:500]
    log_run(record)


def main() -> int:
    board = ensure_storyboard()
    fps = int(board.get("project", {}).get("fps") or FPS)
    if fps != FPS:
        print(f"storyboard fps is {fps}; clips are {FPS}", file=sys.stderr)
        return 1
    cache = load_cache()
    made = 0
    skipped = []
    shots = board.get("shots") or []
    for shot in shots:
        sid = str(shot.get("id"))
        image = keyframe_for(sid)
        if image is None:
            print(f"{sid}: no keyframe, skipped")
            skipped.append(sid)
            continue
        duration = shot.get("duration_s")
        if isinstance(duration, bool) or not isinstance(duration, int) or duration < 1:
            print(f"{sid}: duration_s must be a positive integer", file=sys.stderr)
            return 1
        kind = move_kind(str(shot.get("motion_prompt") or ""))
        frames = duration * FPS
        params = {
            "motion": kind,
            "duration_s": duration,
            "fps": FPS,
            "width": WIDTH,
            "height": HEIGHT,
            "frames": frames,
        }
        digest = cache_key(image.read_bytes(), params)
        dest = OUT_DIR / f"{sid}_{digest[:8]}.mp4"
        cached = cache.get(digest)
        cached_path = ROOT / cached if isinstance(cached, str) else None
        if (cached_path is not None and cached_path.is_file()) or dest.is_file():
            path = cached_path if cached_path is not None and cached_path.is_file() else dest
            cache[digest] = _rel(path)
            print(f"{sid}: cached {path.name}")
            made += 1
            continue
        record = {
            "stage": "shots",
            "provider": "ffmpeg",
            "model": "zoompan",
            "parameters": {**params, "keyframe": _rel(image)},
            "output_path": _rel(dest),
        }
        started = time.perf_counter()
        err = render(image, dest, kind, frames)
        if err:
            _log(record, started, "error", err)
            print(f"{sid}: {err}", file=sys.stderr)
            return 1
        cache[digest] = _rel(dest)
        save_cache(cache)
        _log(record, started, "ok")
        print(f"{sid}: {dest.name} ({kind}, {duration}s)")
        made += 1
    save_cache(cache)
    print(f"shots {made}/{len(shots)}" + (f", skipped {' '.join(skipped)}" if skipped else ""))
    return 0


def _self_check() -> None:
    assert move_kind("slow gentle camera push-in") == "push-in"
    assert move_kind("slow pull-back deeper into the room") == "pull-back"
    assert move_kind("very slow horizontal drift across the strings") == "drift"
    assert move_kind("locked static camera, subtle breathing") == "hold"
    assert "iw/2-(iw/zoom/2)" in zoompan("push-in", 48)
    assert cache_key(b"a", {"motion": "hold"}) != cache_key(b"b", {"motion": "hold"})
    assert cache_key(b"a", {"motion": "hold"}) != cache_key(b"a", {"motion": "drift"})

    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        still = folder / "still.png"
        made = subprocess.run(
            [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-f", "lavfi", "-i", "color=c=0x224466:s=320x568",
                "-frames:v", "1", str(still),
            ],
            capture_output=True, text=True,
        )
        assert made.returncode == 0, made.stderr
        clip = folder / "clip.mp4"
        err = render(still, clip, "push-in", 8)
        assert err is None, err
        probe = subprocess.check_output(
            [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=width,height,nb_frames,r_frame_rate",
                "-of", "json", str(clip),
            ],
            text=True,
        )
        stream = json.loads(probe)["streams"][0]
        assert stream["width"] == WIDTH and stream["height"] == HEIGHT
        assert int(stream["nb_frames"]) == 8
        assert stream["r_frame_rate"] == "24/1"
    print("self-check ok")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-check":
        _self_check()
    else:
        sys.exit(main())
