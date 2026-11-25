#!/usr/bin/env python3
"""Log the ACE-Step candidates downloaded from Kaggle into outputs/music/.

The notebook writes music_301.wav, music_302.wav, music_303.wav and
latencies.json. This stage measures each file and logs the Kaggle latency.
"""

import json
import sys
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


def main() -> int:
    board = ensure_storyboard()
    if not LATENCIES.is_file():
        print(f"missing {_rel(LATENCIES)} (download it with the wavs)", file=sys.stderr)
        return 1
    try:
        latencies, gpu_minutes = load_latencies(LATENCIES)
        payload, records = build(MUSIC_DIR, latencies, gpu_minutes, board["music"])
    except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError) as err:
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
    print("self-check ok")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-check":
        _self_check()
    else:
        sys.exit(main())
