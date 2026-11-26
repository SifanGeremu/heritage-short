#!/usr/bin/env python3
"""Addis AI narration for every shot, then outputs/narration/timing.json.

The voice is tts.voice_name and the language is project.narration_language.
Nothing here replaces a voice that does not start with om-. Each wav gets
250ms of lead, 350ms of tail, and a 15ms fade at both ends. Nothing is
trimmed. A cached file is reused when the text, voice, language, and pad match.
"""

import hashlib
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ROOT, fail, read_key, unique_path, with_retry
from providers.addis import LANGUAGE, cost_etb, synthesize
from stage_assemble import FADE_S, PAD_LEAD_S, PAD_TAIL_S, _run, probe_audio
from validate import ensure_storyboard

NARRATION_DIR = ROOT / "outputs" / "narration"
CACHE_PATH = NARRATION_DIR / "cache.json"
TIMING_PATH = NARRATION_DIR / "timing.json"


def cache_key(text: str, voice: str, language: str) -> str:
    payload = json.dumps(
        {
            "provider": "addis",
            "voice": voice,
            "language": language,
            "format": "wav_44100",
            "text": text,
            "lead_s": PAD_LEAD_S,
            "tail_s": PAD_TAIL_S,
            "fade_s": FADE_S,
        },
        ensure_ascii=False,
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
    NARRATION_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2) + "\n", encoding="utf-8")


def with_real_extension(path: Path) -> Path:
    _measured, formats = probe_audio(path)
    ext = path.suffix.lower().lstrip(".")
    known = {name.lower() for name in formats}
    if ext in known or not formats:
        return path
    dest = unique_path(path.with_suffix("." + formats[0].lower()))
    path.rename(dest)
    return dest


def pad_wav(src: Path, dest: Path) -> None:
    """250ms lead, 350ms tail, 15ms fades. No silenceremove and no hard trim."""
    measured, _formats = probe_audio(src)
    fade_at = measured + PAD_LEAD_S + PAD_TAIL_S - FADE_S
    effect = (
        f"adelay={int(round(PAD_LEAD_S * 1000))}:all=1,"
        f"apad=pad_dur={PAD_TAIL_S:.3f},"
        f"afade=t=in:st=0:d={FADE_S:.3f},"
        f"afade=t=out:st={fade_at:.3f}:d={FADE_S:.3f}"
    )
    err = _run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(src), "-af", effect, str(dest),
    ])
    if err:
        raise RuntimeError(err)


def timing_row(sid: str, path: Path | None) -> dict:
    if path is None:
        return {"id": sid, "file": None}
    measured, _formats = probe_audio(path)
    return {"id": sid, "file": _rel(path), "duration_s": measured}


def speak(key: str, sid: str, text: str, dest: Path, voice: str, language: str) -> Path | None:
    holder: dict[str, Path] = {}

    def once():
        record = {
            "stage": "narration",
            "provider": "addis",
            "model": voice,
            "parameters": {
                "text": text,
                "voice": voice,
                "language": language,
                "shot": sid,
                "lead_s": PAD_LEAD_S,
                "tail_s": PAD_TAIL_S,
            },
            "seed": None,
            "cost": 0,
        }
        try:
            audio = synthesize(key, text, voice, language)
            dest.parent.mkdir(parents=True, exist_ok=True)
            raw = dest.with_name(dest.stem + ".raw.wav")
            raw.write_bytes(audio)
            raw_seconds, _formats = probe_audio(raw)
            pad_wav(raw, dest)
            raw.unlink(missing_ok=True)
            path = with_real_extension(dest)
            seconds, _formats = probe_audio(path)
        except Exception as err:
            fail(err, record, key)
        holder["path"] = path
        record["output_path"] = _rel(path)
        record["audio_seconds"] = seconds
        record["cost"] = cost_etb(raw_seconds)
        record["detail"] = f"{sid}: {record['output_path']} ({seconds:.3f}s)"
        return record

    if not with_retry(once):
        return None
    return holder["path"]


def main() -> int:
    board = ensure_storyboard()
    key = read_key("ADDIS-AI-API-KEY")
    if not key:
        print("ADDIS-AI-API-KEY is missing from .env", file=sys.stderr)
        return 1
    tts = board.get("tts") or {}
    voice = str(tts.get("voice_name") or "").strip()
    if not voice:
        print("tts.voice_name is missing from the storyboard", file=sys.stderr)
        return 1
    lang = str(board.get("project", {}).get("narration_language") or LANGUAGE)
    cache = load_cache()
    rows = []
    for shot in board.get("shots", []):
        sid = shot["id"]
        text = str(shot.get("narration", {}).get(lang) or "").strip()
        if not text:
            print(f"{sid}: silence")
            rows.append(timing_row(sid, None))
            continue
        digest = cache_key(text, voice, lang)
        cached = cache.get(digest)
        if isinstance(cached, str) and (ROOT / cached).is_file():
            path = ROOT / cached
            print(f"{sid}: cached {_rel(path)}")
        else:
            dest = unique_path(NARRATION_DIR / f"{sid}_{digest[:8]}.wav")
            path = speak(key, sid, text, dest, voice, lang)
            if path is None:
                return 1
            cache[digest] = _rel(path)
            save_cache(cache)
        row = timing_row(sid, path)
        rows.append(row)
        print(f"{sid}: wav {row['duration_s']:.3f}s")
    NARRATION_DIR.mkdir(parents=True, exist_ok=True)
    TIMING_PATH.write_text(
        json.dumps({"shots": rows}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(_rel(TIMING_PATH))
    print(f"shots {len(rows)}/{len(board.get('shots', []))}, voice {voice}")
    return 0


def _self_check() -> None:
    assert cache_key("a", "om-ayyaantuu", "om") == cache_key("a", "om-ayyaantuu", "om")
    assert cache_key("a", "om-ayyaantuu", "om") != cache_key("a", "om-leensaa", "om")
    assert cache_key("a", "am-meron", "am") != cache_key("a", "am-meron", "om")
    assert timing_row("s03", None) == {"id": "s03", "file": None}
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        raw = folder / "raw.wav"
        padded = folder / "padded.wav"
        err = _run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=0.40",
            str(raw),
        ])
        assert err is None, err
        pad_wav(raw, padded)
        measured, _formats = probe_audio(padded)
        expect = 0.40 + PAD_LEAD_S + PAD_TAIL_S
        assert abs(measured - expect) <= 0.05, measured
    print("self-check ok")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-check":
        _self_check()
    else:
        sys.exit(main())
