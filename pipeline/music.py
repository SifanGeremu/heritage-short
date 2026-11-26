#!/usr/bin/env python3
"""Log the ACE-Step candidates downloaded from Kaggle into outputs/music/.

The notebook writes music_301.wav, music_302.wav, music_303.wav and
latencies.json. This stage measures each file and logs the Kaggle latency.
If those files are missing, it writes a sine bed and logs that instead.
"""

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ROOT, audio_seconds, log_run
from validate import ensure_storyboard

SEEDS = (301, 302, 303)
MUSIC_DIR = ROOT / "outputs" / "music"
CANDIDATES = MUSIC_DIR / "candidates.json"
LATENCIES = MUSIC_DIR / "latencies.json"
MODEL = "ace-step-1.5"


def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_latencies(path: Path) -> tuple[dict[int, float], float]:
    data = json.loads(path.read_text(encoding="utf-8"))
    tracks = data.get("tracks") or []
    by_seed = {}
    for row in tracks:
        by_seed[int(row["seed"])] = float(row["latency_s"])
    return by_seed, float(data.get("gpu_minutes") or 0)


def build(music_dir: Path, latencies: dict[int, float], gpu_minutes: float, music: dict) -> tuple[dict, list[dict]]:
    cues = [
        {"id": cue["id"], "duration_s": cue["duration_s"], "caption": cue["caption"]}
        for cue in music.get("cues") or []
    ]
    candidates = []
    records = []
    missing = []
    for seed in SEEDS:
        path = music_dir / f"music_{seed}.wav"
        if not path.is_file():
            missing.append(path.name)
            continue
        if seed not in latencies:
            missing.append(f"latency for seed {seed}")
            continue
        duration = audio_seconds(path)
        rel = _rel(path)
        candidates.append({"seed": seed, "file": rel, "duration_s": duration, "latency_s": latencies[seed]})
        records.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "stage": "music",
                "provider": "ace-step",
                "model": MODEL,
                "parameters": {
                    "bpm": music.get("bpm"),
                    "key": music.get("key"),
                    "instrumental": music.get("instrumental"),
                    "cues": cues,
                    "gpu_minutes": gpu_minutes,
                },
                "seed": seed,
                "latency": latencies[seed],
                "cost": 0,
                "status": "ok",
                "output_path": rel,
            }
        )
    if missing:
        raise FileNotFoundError("missing " + ", ".join(missing))
    payload = {
        "model": MODEL,
        "gpu_minutes": gpu_minutes,
        "candidates": candidates,
    }
    return payload, records


def beds_ready(music_dir: Path, latencies: Path) -> bool:
    return latencies.is_file() and all((music_dir / f"music_{seed}.wav").is_file() for seed in SEEDS)


def write_bed(path: Path, seconds: float, freq: int) -> float:
    path.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    proc = subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", f"sine=frequency={freq}:duration={seconds}",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or "ffmpeg failed").strip()[-500:])
    return round(time.perf_counter() - started, 3)


def write_fallback(music_dir: Path, music: dict, *, seconds: float | None = None) -> tuple[dict, list[dict]]:
    """Sine beds for a clean clone. Existing wavs are left where they are.

    ponytail: one sine per seed, not a score. Upgrade path is the Kaggle notebook.
    """
    cues = [
        {"id": cue["id"], "duration_s": cue["duration_s"], "caption": cue["caption"]}
        for cue in music.get("cues") or []
    ]
    span = seconds if seconds is not None else float(sum(cue["duration_s"] for cue in cues) or 84)
    candidates = []
    records = []
    tracks = []
    for index, seed in enumerate(SEEDS):
        path = music_dir / f"music_{seed}.wav"
        if path.is_file():
            latency = 0.0
        else:
            latency = write_bed(path, span, 196 + index * 24)
        duration = audio_seconds(path)
        rel = _rel(path)
        candidates.append({"seed": seed, "file": rel, "duration_s": duration, "latency_s": latency})
        tracks.append({"seed": seed, "file": path.name, "latency_s": latency})
        records.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "stage": "music",
                "provider": "ffmpeg",
                "model": "sine",
                "parameters": {
                    "bpm": music.get("bpm"),
                    "key": music.get("key"),
                    "instrumental": True,
                    "cues": cues,
                    "gpu_minutes": 0,
                    "fallback": "ace-step wav or latencies missing",
                },
                "seed": seed,
                "latency": latency,
                "cost": 0,
                "status": "ok",
                "output_path": rel,
            }
        )
    latencies_path = music_dir / "latencies.json"
    if not latencies_path.is_file():
        latencies_path.write_text(
            json.dumps({"gpu_minutes": 0, "source": "ffmpeg", "tracks": tracks}, indent=2) + "\n",
            encoding="utf-8",
        )
    payload = {"model": "ffmpeg-sine", "gpu_minutes": 0, "source": "ffmpeg", "candidates": candidates}
    return payload, records


def main() -> int:
    board = ensure_storyboard()
    try:
        if beds_ready(MUSIC_DIR, LATENCIES):
            latencies, gpu_minutes = load_latencies(LATENCIES)
            payload, records = build(MUSIC_DIR, latencies, gpu_minutes, board["music"])
        else:
            payload, records = write_fallback(MUSIC_DIR, board["music"])
    except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError, RuntimeError) as err:
        print(err, file=sys.stderr)
        return 1
    for record in records:
        log_run(record)
    for row in payload["candidates"]:
        print(f"music_{row['seed']}.wav: duration {row['duration_s']:.3f}s, latency {row['latency_s']:.3f}s")
    CANDIDATES.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(_rel(CANDIDATES))
    return 0


def _self_check() -> None:
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        for seed, seconds in ((301, 0.4), (302, 0.5), (303, 0.6)):
            err = subprocess.run(
                [
                    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
                    str(folder / f"music_{seed}.wav"),
                ],
                capture_output=True, text=True,
            )
            assert err.returncode == 0, err.stderr
        latencies = {301: 1.5, 302: 1.6, 303: 1.7}
        payload, records = build(
            folder,
            latencies,
            0.25,
            {"bpm": 68, "key": "A minor", "instrumental": True, "cues": [{"id": "cue", "duration_s": 42, "caption": "guitar"}]},
        )
        assert [row["seed"] for row in payload["candidates"]] == [301, 302, 303]
        assert records[0]["provider"] == "ace-step" and records[0]["model"] == "ace-step-1.5"
        assert records[0]["cost"] == 0 and records[0]["latency"] == 1.5
        assert records[0]["seed"] == 301
        assert abs(payload["candidates"][1]["duration_s"] - 0.5) < 0.05

        empty = folder / "empty"
        empty.mkdir()
        music = {"bpm": 68, "key": "A minor", "instrumental": True, "cues": [{"id": "cue", "duration_s": 42, "caption": "guitar"}]}
        assert beds_ready(empty, empty / "latencies.json") is False
        fallback, rows = write_fallback(empty, music, seconds=0.2)
        assert [row["seed"] for row in fallback["candidates"]] == [301, 302, 303]
        assert rows[0]["provider"] == "ffmpeg" and rows[0]["model"] == "sine"
        assert rows[0]["latency"] >= 0 and rows[0]["cost"] == 0
        written = json.loads((empty / "latencies.json").read_text(encoding="utf-8"))
        assert written["source"] == "ffmpeg" and written["gpu_minutes"] == 0
        assert beds_ready(empty, empty / "latencies.json")
        kept = (empty / "music_303.wav").read_bytes()
        again, _rows = write_fallback(empty, music, seconds=0.2)
        assert (empty / "music_303.wav").read_bytes() == kept
        assert again["source"] == "ffmpeg"
    print("self-check ok")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-check":
        _self_check()
    else:
        sys.exit(main())
