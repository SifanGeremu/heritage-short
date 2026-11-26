#!/usr/bin/env python3
"""Radio cut: black 9:16 frame, padded narration, rain bed, English captions.

Lines are never trimmed. Each shot keeps its storyboard length. A longer
line is sped to fit. The 3s AI end card is part of the runtime.
"""

import ctypes
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ROOT, audio_seconds
from validate import ensure_storyboard

TIMING_PATH = ROOT / "outputs" / "narration" / "timing.json"
OUT_PATH = ROOT / "outputs" / "radio_cut.mp4"
SRT_PATH = ROOT / "outputs" / "radio_cut.srt"
FRAME = "1080x1920"
FONT = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_SIZE = 68
MARGIN_X = 80
MARGIN_V = 280
OUTLINE = 3
# ponytail: width is the sum of glyph advances, kerning ignored. If a line
# ever touches the frame edge, measure with harfbuzz instead.
MAX_TEXT_W = 1080 - MARGIN_X * 2 - OUTLINE * 2 - 8
PAD_LEAD_S = 0.250
PAD_TAIL_S = 0.350
FADE_S = 0.015
HOLD_S = 0.8
MAX_LINE_CHARS = 40
# A3. ponytail: Karplus-Strong, not a recorded guitar. A real sample at
# outputs/audio/guitar_a3.wav replaces the synth if it is ever added.
PLUCK_HZ = 220.0
# 3.3s is the gap after "Just one old string..." in s08_53ff8529.wav. 1.5s sat under the words.
PLUCK_AT_S = 3.3
PLUCK_S = 2.5
PLUCK_GAIN = 2.0


def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _load_timing(path: Path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, f"{_rel(path)}: file not found"
    except json.JSONDecodeError as err:
        return None, f"{_rel(path)}: {err}"
    shots = data.get("shots") if isinstance(data, dict) else data
    if not isinstance(shots, list):
        return None, f"{_rel(path)}: expected a shots array"
    return shots, None


def _clip(entry: dict) -> str | None:
    for key in ("file", "path", "narration"):
        if key not in entry:
            continue
        value = entry[key]
        if value is None or value == "":
            return None
        if isinstance(value, str):
            return value
    return None


def probe_audio(path: Path) -> tuple[float, list[str]]:
    """ffprobe duration in seconds (3 d.p.) and container names."""
    out = subprocess.check_output(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration,format_name",
            "-of", "json",
            str(path),
        ],
        text=True,
    )
    fmt = json.loads(out)["format"]
    names = [name for name in str(fmt.get("format_name", "")).split(",") if name]
    return round(float(fmt["duration"]), 3), names


def slot_for(shot_s: float, line_s: float | None) -> tuple[float, bool]:
    """Storyboard length. A longer line is sped up in the mix, not given extra time."""
    return shot_s, line_s is not None and line_s > shot_s + 1e-9


def playback_rate(wav_s: float | None, shot_s: float) -> float:
    if wav_s is None or wav_s <= shot_s:
        return 1.0
    return wav_s / shot_s


def atempo_chain(rate: float) -> str:
    if rate <= 1.01:
        return ""
    parts = []
    remaining = rate
    while remaining > 2:
        parts.append("atempo=2")
        remaining /= 2
    parts.append(f"atempo={remaining:.4f}")
    return ",".join(parts) + ","


def runtime_warning(total: float) -> str | None:
    if 60 <= total <= 90:
        return None
    return f"total runtime {total:.3f}s including end card is outside 60–90s"


_ft_face = None
_advance_cache: dict[str, float] = {}


def _text_width(text: str) -> float:
    """Pixel width of caption text at FONT_SIZE. Falls back to a wide estimate."""
    global _ft_face
    try:
        if _ft_face is None:
            ft = ctypes.CDLL("libfreetype.so.6")
            ft.FT_Init_FreeType.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
            ft.FT_Init_FreeType.restype = ctypes.c_int
            ft.FT_New_Face.argtypes = [
                ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.POINTER(ctypes.c_void_p),
            ]
            ft.FT_New_Face.restype = ctypes.c_int
            ft.FT_Set_Pixel_Sizes.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint]
            ft.FT_Set_Pixel_Sizes.restype = ctypes.c_int
            ft.FT_Get_Char_Index.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
            ft.FT_Get_Char_Index.restype = ctypes.c_uint
            ft.FT_Get_Advance.argtypes = [
                ctypes.c_void_p, ctypes.c_uint, ctypes.c_int32, ctypes.POINTER(ctypes.c_long),
            ]
            ft.FT_Get_Advance.restype = ctypes.c_int
            library = ctypes.c_void_p()
            face = ctypes.c_void_p()
            if ft.FT_Init_FreeType(ctypes.byref(library)) != 0:
                raise OSError("freetype init failed")
            if ft.FT_New_Face(library, FONT.encode(), 0, ctypes.byref(face)) != 0:
                raise OSError(f"font not found: {FONT}")
            if ft.FT_Set_Pixel_Sizes(face, 0, FONT_SIZE) != 0:
                raise OSError("font size failed")
            _ft_face = (ft, face)
        ft, face = _ft_face
        total = 0.0
        for ch in text:
            adv = _advance_cache.get(ch)
            if adv is None:
                slot = ctypes.c_long()
                ft.FT_Get_Advance(face, ft.FT_Get_Char_Index(face, ord(ch)), 0, ctypes.byref(slot))
                adv = slot.value / 65536
                _advance_cache[ch] = adv
            total += adv
        return total
    except (OSError, AttributeError):
        return len(text) * FONT_SIZE * 0.62


def _fits(line: str) -> bool:
    return len(line) <= MAX_LINE_CHARS and _text_width(line) <= MAX_TEXT_W + 0.5


def _clauses(text: str) -> list[str]:
    """Split on sentence and clause marks. An ellipsis is one mark, not three stops."""
    parts: list[str] = []
    buf: list[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "." and i + 1 < len(text) and text[i + 1] == ".":
            while i < len(text) and text[i] == ".":
                buf.append(text[i])
                i += 1
            piece = "".join(buf).strip()
            buf = []
            if piece:
                parts.append(piece)
            continue
        buf.append(ch)
        i += 1
        if ch in ".?!—:,":
            piece = "".join(buf).strip()
            buf = []
            if piece:
                parts.append(piece)
    tail = "".join(buf).strip()
    if tail:
        parts.append(tail)
    def _join(left: str, right: str) -> str:
        right = right.lstrip()
        if left.endswith("—"):
            return f"{left}{right}"
        return f"{left} {right}"

    glued: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if not part.strip(" \"'") and glued:
            glued[-1] = glued[-1] + part.strip()
            index += 1
            continue
        if len(part.split()) <= 2 and index + 1 < len(parts):
            parts[index + 1] = _join(part, parts[index + 1])
            index += 1
            continue
        if len(part.split()) <= 2 and glued:
            glued[-1] = _join(glued[-1], part)
        else:
            glued.append(part)
        index += 1
    return glued


def _wrap_clause(clause: str) -> list[str]:
    words = clause.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        trial = " ".join(current + [word])
        if current and not _fits(trial):
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    index = 1
    while index < len(lines):
        if len(lines[index].split()) > 2 or len(lines[index - 1].split()) <= 3:
            index += 1
            continue
        prev = lines[index - 1].split()
        nxt = lines[index].split()
        moved = False
        while len(nxt) < 3 and len(prev) > 3:
            trial_prev = " ".join(prev[:-1])
            trial_next = " ".join([prev[-1], *nxt])
            if not _fits(trial_prev) or not _fits(trial_next):
                break
            nxt.insert(0, prev.pop())
            moved = True
        lines[index - 1] = " ".join(prev)
        lines[index] = " ".join(nxt)
        if not moved:
            index += 1
    return lines


def chunk_cues(text: str) -> list[str]:
    """Clause breaks first. Two lines, 40 characters, no 1–2 word tail cue."""
    lines: list[str] = []
    for clause in _clauses(text):
        lines.extend(_wrap_clause(clause))
    merged: list[str] = []
    for line in lines:
        if merged and _fits(f"{merged[-1]} {line}"):
            merged[-1] = f"{merged[-1]} {line}"
        else:
            merged.append(line)
    lines = merged
    cues: list[str] = []
    index = 0
    while index < len(lines):
        take = lines[index:index + 2]
        words = " ".join(take).split()
        if len(words) <= 2 and cues:
            prev = cues[-1].split("\n")
            orphan = " ".join(take)
            if len(prev) == 1 and _fits(f"{prev[0]} {orphan}"):
                cues[-1] = f"{prev[0]} {orphan}"
            elif len(prev) == 1 and _fits(orphan):
                cues[-1] = f"{prev[0]}\n{orphan}"
            else:
                cues.append("\n".join(take))
            index += len(take)
            continue
        cues.append("\n".join(take))
        index += len(take)
    return cues


def cue_windows(cues: list[str], start: float, end: float) -> list[tuple[float, float, str]]:
    if not cues or end <= start:
        return []
    weights = [max(1, len(cue.replace("\n", ""))) for cue in cues]
    span = end - start
    total = sum(weights)
    cursor = start
    windows = []
    for cue, weight in zip(cues, weights):
        dur = span * weight / total
        windows.append((cursor, cursor + dur, cue))
        cursor += dur
    return windows


def _srt_time(seconds: float) -> str:
    ms = max(0, int(round(seconds * 1000)))
    hours, ms = divmod(ms, 3_600_000)
    minutes, ms = divmod(ms, 60_000)
    secs, ms = divmod(ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def _ass_time(seconds: float) -> str:
    cs = max(0, int(round(seconds * 100)))
    hours, cs = divmod(cs, 360_000)
    minutes, cs = divmod(cs, 6_000)
    secs, cs = divmod(cs, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{cs:02d}"


def _cue(item) -> tuple[float, float, str, str]:
    if len(item) == 4:
        return item
    start, end, text = item
    return start, end, text, ""


def write_ass(
    cues: list,
    dest: Path,
    *,
    play_x: int = 1080,
    play_y: int = 1920,
    font_size: int = FONT_SIZE,
    margin_x: int = MARGIN_X,
    margin_v: int = MARGIN_V,
    outline: int = OUTLINE,
) -> None:
    """Bottom safe area. The Name field is the shot id, so a missing shot is visible."""
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {play_x}",
        f"PlayResY: {play_y}",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,Liberation Sans,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,"
        f"-1,0,0,0,100,100,0,0,1,{outline},1,2,{margin_x},{margin_x},{margin_v},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for item in cues:
        start, end, text, sid = _cue(item)
        body = text.replace("\\", "").replace("{", "").replace("}", "").replace("\n", r"\N")
        lines.append(
            f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Default,{sid},0,0,0,,{body}"
        )
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_srt(cues: list, dest: Path) -> None:
    blocks = []
    for index, item in enumerate(cues, start=1):
        start, end, text, _sid = _cue(item)
        blocks.append(f"{index}\n{_srt_time(start)} --> {_srt_time(end)}\n{text}\n")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(blocks), encoding="utf-8")


def _ass_seconds(stamp: str) -> float:
    clock, cs = stamp.strip().split(".")
    hours, minutes, seconds = clock.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(cs) / 100.0


def assert_subtitle_coverage(path: Path, placed: list[dict], end_card_at: float) -> None:
    """One subtitle block per non-empty English line, and s10 ends before the end card."""
    spoken = [shot["id"] for shot in placed if (shot.get("en") or "").strip()]
    full = {shot["id"]: (shot.get("en") or "").strip() for shot in placed}
    blocks: list[str] = []
    s10_end = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("Dialogue:"):
            continue
        parts = line.split(":", 1)[1].split(",", 9)
        sid = parts[4].strip()
        end = _ass_seconds(parts[2])
        body = parts[9].replace(r"\N", "\n")
        rows = body.split("\n")
        if len(rows) > 2 or any(len(row) > MAX_LINE_CHARS for row in rows):
            raise SystemExit(f"{_rel(path)}: cue exceeds 2 lines or {MAX_LINE_CHARS} chars: {body!r}")
        if len(body.replace("\n", " ").split()) <= 2 and len(full.get(sid, "").split()) > 2:
            raise SystemExit(f"{_rel(path)}: orphan cue {body!r}")
        if not blocks or blocks[-1] != sid:
            blocks.append(sid)
        if sid == "s10":
            s10_end = end
    if blocks != spoken:
        raise SystemExit(f"{_rel(path)}: subtitle blocks {blocks} != narration shots {spoken}")
    if "s10" in spoken and (s10_end is None or s10_end > end_card_at + 0.05):
        raise SystemExit(
            f"{_rel(path)}: s10 ends at {s10_end}s, end card starts at {end_card_at:.3f}s"
        )


def _measured(sid: str, entry: dict, path: Path) -> tuple[float | None, list[str]]:
    ext = path.suffix.lower().lstrip(".")
    if not ext:
        return None, [f"{sid}: {path.name} must use its actual extension"]
    try:
        measured, formats = probe_audio(path)
    except (subprocess.CalledProcessError, KeyError, ValueError, json.JSONDecodeError) as err:
        return None, [f"{sid}: ffprobe failed: {err}"]
    known = {name.lower() for name in formats}
    if ext not in known:
        found = ",".join(formats) or "unknown"
        return None, [f"{sid}: .{ext} is not the ffprobe format ({found})"]
    recorded = entry.get("duration_s")
    if isinstance(recorded, bool) or not isinstance(recorded, (int, float)):
        return None, [f"{sid}: duration_s must be the ffprobe duration {measured:.3f}s"]
    if abs(float(recorded) - measured) > 0.001:
        return None, [f"{sid}: duration_s is {float(recorded):.3f}s, ffprobe measured {measured:.3f}s"]
    return measured, []


def plan(board: dict, entries: list) -> tuple[list[dict], list[str], list[str], float]:
    """Lay shots end to end. timing.json holds measured padded-wav lengths."""
    by_id: dict[str, dict] = {}
    errors = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
            errors.append(f"$.shots[{index}]: expected an object with an id")
            continue
        sid = entry["id"]
        if sid in by_id:
            errors.append(f"$.shots[{index}].id: duplicate shot id {sid!r}")
            continue
        by_id[sid] = entry

    lang = board.get("project", {}).get("narration_language", "om")
    sub_lang = board.get("project", {}).get("subtitle_language", "en")
    placed = []
    warnings = []
    cursor = 0.0
    board_ids = []
    for shot in board.get("shots", []):
        sid = shot.get("id")
        board_ids.append(sid)
        entry = by_id.get(sid)
        if entry is None:
            errors.append(f"$.shots: timing.json missing shot {sid!r}")
            continue
        shot_s = shot.get("duration_s")
        if isinstance(shot_s, bool) or not isinstance(shot_s, (int, float)) or shot_s <= 0:
            errors.append(f"$.shots[{sid}].duration_s: expected a positive number")
            continue
        narration = shot.get("narration") if isinstance(shot.get("narration"), dict) else {}
        text = str(narration.get(lang) or "").strip()
        clip = None if not text else _clip(entry)
        if text and clip is None:
            errors.append(f"$.shots[{sid}].file: narration line has no audio file")
            continue
        line_s = None
        if clip:
            path = Path(clip)
            if not path.is_absolute():
                path = ROOT / path
            if not path.is_file():
                errors.append(f"{sid}: {_rel(path)}: file not found")
                continue
            line_s, measured_errors = _measured(sid, entry, path)
            errors.extend(measured_errors)
            if measured_errors:
                continue
            clip = str(path)
        slot, overrun = slot_for(float(shot_s), line_s)
        rate = playback_rate(line_s, float(shot_s))
        if overrun and line_s is not None:
            warnings.append(
                f"{sid}: line {line_s:.3f}s, shot {float(shot_s):.3f}s, sped {rate:.2f}x to fit"
            )
        placed.append(
            {
                "id": sid,
                "start_s": cursor,
                "duration_s": slot,
                "shot_s": float(shot_s),
                "wav_s": line_s,
                "rate": rate,
                "file": clip,
                "en": str(narration.get(sub_lang) or "").strip(),
            }
        )
        cursor += slot

    for sid in by_id:
        if sid not in board_ids:
            errors.append(f"$.shots[{sid}]: unknown shot id")
    end_card = board.get("project", {}).get("end_card_duration_s") or 0
    if isinstance(end_card, bool) or not isinstance(end_card, (int, float)) or end_card < 0:
        end_card = 0
    runtime = cursor + float(end_card)
    window = runtime_warning(runtime)
    if window:
        warnings.append(window)
    return placed, errors, warnings, runtime


def spoken_window(shot: dict) -> tuple[float, float]:
    start = shot["start_s"]
    wav = shot.get("wav_s")
    slot = shot["duration_s"]
    if not wav:
        return start, start
    rate = shot.get("rate") or playback_rate(wav, slot)
    speech_start = start + PAD_LEAD_S / rate
    speech_end = min(start + slot, start + (wav - PAD_TAIL_S) / rate)
    if speech_end <= speech_start:
        speech_end = start + min(slot, wav / rate)
        speech_start = start
    return speech_start, speech_end


def _hold_short_cues(
    cues: list[tuple[float, float, str]], minimum: float = 1.0
) -> list[tuple[float, float, str]]:
    """A tail like 'weep.' must stay on screen long enough to read."""
    held = [list(cue) for cue in cues]
    for index in range(1, len(held)):
        start, end, _text = held[index]
        short = end - start
        if short >= minimum - 1e-3:
            continue
        prev_start, prev_end, _prev = held[index - 1]
        if abs(start - prev_end) > 0.05:
            continue
        give = min(minimum - short, max(0.0, (prev_end - prev_start) - minimum))
        if give <= 0:
            continue
        held[index - 1][1] -= give
        held[index][0] -= give
    return [tuple(cue) for cue in held]


def build_cues(placed: list[dict]) -> list[tuple[float, float, str, str]]:
    cues = []
    for shot in placed:
        text = (shot.get("en") or "").strip()
        if not text:
            continue
        start, end = spoken_window(shot)
        for window in _hold_short_cues(cue_windows(chunk_cues(text), start, end)):
            cues.append((*window, shot["id"]))
    return cues


def _run(cmd: list[str]) -> str | None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "ffmpeg failed").strip()
        return detail[-2000:]
    return None


def _filter_path(path: Path) -> str:
    return path.as_posix().replace("\\", "\\\\").replace(":", "\\:").replace("'", r"\'")


def _write_wav(path: Path, samples: list[float], sr: int = 48000) -> None:
    import struct
    import wave

    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sr)
        frames = b"".join(
            struct.pack("<h", int(max(-1.0, min(1.0, sample)) * 32767))
            for sample in samples
        )
        handle.writeframes(frames)


def write_pluck(path: Path, freq: float = PLUCK_HZ, seconds: float = PLUCK_S, sr: int = 48000) -> None:
    """One warm A3. Decay is a 2.5s ring, not a physical string."""
    import math
    import random

    n = max(2, int(round(sr / freq)))
    rng = random.Random(int(freq))
    buf = [rng.uniform(-1.0, 1.0) for _ in range(n)]
    buf = [0.5 * (buf[i] + buf[(i + 1) % n]) for i in range(n)]
    total = int(sr * seconds)
    samples = []
    idx = 0
    for i in range(total):
        sample = buf[idx]
        buf[idx] = 0.5 * (buf[idx] + buf[(idx + 1) % n])
        idx = (idx + 1) % n
        attack = min(1.0, i / (0.004 * sr))
        env = math.exp(-3.0 * i / total)
        samples.append(sample * attack * env)
    peak = max(abs(sample) for sample in samples) or 1.0
    _write_wav(path, [sample / peak * 0.8 for sample in samples], sr)


def write_hum(path: Path, seconds: float, sr: int = 48000) -> None:
    """A-minor chord, the stand-in for cue_part2_hope when the score is not the bed."""
    import math

    freqs = (110.0, 130.81, 164.81)
    total = max(1, int(sr * seconds))
    samples = []
    for i in range(total):
        t = i / sr
        tone = sum(math.sin(2 * math.pi * freq * t) for freq in freqs) / len(freqs)
        attack = min(1.0, t / 0.35)
        samples.append(tone * attack)
    _write_wav(path, samples, sr)


def _by_id(placed: list[dict], sid: str) -> dict | None:
    for shot in placed:
        if shot["id"] == sid:
            return shot
    return None


def render(placed: list[dict], fps: int, dest: Path, runtime: float, srt: Path | None = None) -> str | None:
    if not placed:
        return "radio cut: no shots"
    end_card = runtime - max(shot["start_s"] + shot["duration_s"] for shot in placed)
    cues = build_cues(placed)
    ass = None
    if srt is not None and cues:
        write_srt(cues, srt)
        ass = srt.with_suffix(".ass")
        write_ass(cues, ass)
        assert_subtitle_coverage(ass, placed, runtime - end_card)
        if dest.resolve() == OUT_PATH.resolve():
            work = ROOT / "outputs" / "assemble"
            subs_9 = work / "subs_9x16.ass"
            subs_16 = work / "subs_16x9.ass"
            write_ass(cues, subs_9)
            write_ass(
                cues, subs_16,
                play_x=1920, play_y=1080, font_size=48, margin_x=160, margin_v=64, outline=2,
            )
            assert_subtitle_coverage(subs_9, placed, runtime - end_card)
            assert_subtitle_coverage(subs_16, placed, runtime - end_card)
    missing = []
    voices = []
    for shot in placed:
        if not shot["file"]:
            continue
        path = Path(shot["file"])
        if not path.is_file():
            missing.append(f"{shot['id']}: {_rel(path)}: file not found")
            continue
        voices.append((shot, path))
    if missing:
        return "\n".join(missing)

    s08 = _by_id(placed, "s08")
    s09 = _by_id(placed, "s09")
    pluck_path = dest.with_name(dest.stem + ".pluck.wav") if s08 is not None else None
    hum_path = dest.with_name(dest.stem + ".hum.wav") if s09 is not None else None
    if pluck_path is not None:
        write_pluck(pluck_path)
    if hum_path is not None:
        write_hum(hum_path, max(0.5, runtime - s09["start_s"]))

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", f"color=c=black:s={FRAME}:r={fps}:d={runtime:.3f}",
        "-f", "lavfi", "-t", f"{runtime:.3f}", "-i",
        f"anoisesrc=color=pink:sample_rate=48000:amplitude=1",
    ]
    for _shot, path in voices:
        cmd += ["-i", str(path)]
    if pluck_path is not None:
        cmd += ["-i", str(pluck_path)]
    if hum_path is not None:
        cmd += ["-i", str(hum_path)]

    fade_out = max(0.0, runtime - FADE_S)
    filters = [
        f"[1:a]lowpass=f=1200,volume=-26dB,afade=t=in:st=0:d={FADE_S:.3f},"
        f"afade=t=out:st={fade_out:.3f}:d={FADE_S:.3f}[rain]"
    ]
    labels = []
    for index, (shot, _path) in enumerate(voices):
        label = f"v{index}"
        ms = int(round(shot["start_s"] * 1000))
        tempo = atempo_chain(float(shot.get("rate") or 1))
        # No atrim and no silenceremove. A long line is sped up to the shot.
        filters.append(
            f"[{index + 2}:a]aformat=sample_rates=48000:channel_layouts=mono,"
            f"{tempo}asetpts=PTS-STARTPTS,adelay=delays={ms}:all=1,volume=0.9[{label}]"
        )
        labels.append(f"[{label}]")
    if pluck_path is None and hum_path is None:
        bed = "[rain]"
        if labels:
            n = 1 + len(labels)
            filters.append(
                f"{bed}{''.join(labels)}amix=inputs={n}:normalize=0:duration=first:dropout_transition=0[mix]"
            )
            audio = "[mix]"
        else:
            audio = bed
    else:
        if labels:
            filters.append(
                f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0:"
                "duration=longest:dropout_transition=0[voice]"
            )
        else:
            filters.append("anullsrc=r=48000:cl=mono,atrim=0:0.1[voice]")
        filters.append("[voice]asplit=2[voice_mix][voice_sc_raw]")
        filters.append(
            f"[voice_sc_raw]apad=whole_dur={runtime:.3f},atrim=0:{runtime:.3f}[voice_sc]"
        )
        bed_parts = ["[rain]"]
        next_index = 2 + len(voices)
        if pluck_path is not None:
            ms = int(round((s08["start_s"] + PLUCK_AT_S) * 1000))
            filters.append(
                f"[{next_index}:a]aformat=sample_rates=48000:channel_layouts=mono,"
                f"volume={PLUCK_GAIN},adelay=delays={ms}:all=1[pluck]"
            )
            next_index += 1
        if hum_path is not None:
            ms = int(round(s09["start_s"] * 1000))
            span = max(0.5, runtime - s09["start_s"])
            filters.append(
                f"[{next_index}:a]aformat=sample_rates=48000:channel_layouts=mono,"
                f"volume='0.28+0.45*min(1\\,t/{span:.3f})':eval=frame,"
                f"adelay=delays={ms}:all=1[hum]"
            )
            bed_parts.append("[hum]")
        if len(bed_parts) == 1:
            bed = "[rain]"
        else:
            filters.append(
                f"{''.join(bed_parts)}amix=inputs={len(bed_parts)}:normalize=0:"
                "duration=longest:dropout_transition=0[bed]"
            )
            bed = "[bed]"
        filters.append(
            f"{bed}[voice_sc]sidechaincompress="
            "threshold=0.02:ratio=6:attack=300:release=1500[ducked]"
        )
        tail = "[voice_mix][ducked]" + ("[pluck]" if pluck_path is not None else "")
        n = 2 + (1 if pluck_path is not None else 0)
        filters.append(
            f"{tail}amix=inputs={n}:normalize=0:duration=longest:dropout_transition=0,"
            f"apad=whole_dur={runtime:.3f},atrim=0:{runtime:.3f}[mix]"
        )
        audio = "[mix]"

    video = "[0:v]"
    if ass is not None and ass.is_file():
        filters.append(
            f"[0:v]subtitles=filename='{_filter_path(ass)}':original_size=1080x1920[v]"
        )
        video = "[v]"
    if end_card >= 1 and Path(FONT).is_file():
        start = runtime - end_card
        src = video if video != "[0:v]" else "[0:v]"
        label = "[vend]"
        filters.append(
            f"{src}drawtext=fontfile='{_filter_path(Path(FONT))}':text='Made with AI':"
            f"fontsize=60:fontcolor=white:borderw=3:bordercolor=black:"
            f"x=(w-text_w)/2:y=(h-text_h)/2:"
            f"enable='gte(t,{start:.3f})'{label}"
        )
        video = label

    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd += [
        "-filter_complex", ";".join(filters),
        "-map", video, "-map", audio,
        "-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart",
        "-t", f"{runtime:.3f}",
        str(dest),
    ]
    return _run(cmd)


def _report(placed: list[dict], runtime: float) -> None:
    clipped = 0
    for shot in placed:
        wav = shot.get("wav_s")
        wav_text = "silence" if wav is None else f"{wav:.3f}s"
        print(
            f"{shot['id']}: wav {wav_text}, storyboard {shot['shot_s']:.3f}s, "
            f"effective {shot['duration_s']:.3f}s"
        )
        if wav is not None and shot["duration_s"] + 1e-6 < wav:
            clipped += 1
    print(f"shots {len(placed)}/{len(placed)}, clipping {clipped}")
    print(f"total {runtime:.3f}s")


def main() -> int:
    board = ensure_storyboard()
    entries, err = _load_timing(TIMING_PATH)
    if err:
        print(err, file=sys.stderr)
        return 1
    placed, errors, warnings, runtime = plan(board, entries)
    if errors:
        for line in errors:
            print(line, file=sys.stderr)
        return 1
    for line in warnings:
        print(f"warning: {line}", file=sys.stderr)
    fps = int(board.get("project", {}).get("fps") or 24)
    err = render(placed, fps, OUT_PATH, runtime, SRT_PATH)
    if err:
        print(err, file=sys.stderr)
        return 1
    measured = audio_seconds(OUT_PATH)
    print(_rel(OUT_PATH))
    _report(placed, measured)
    return 0


def _mean_db(path: Path, start: float, length: float) -> float:
    proc = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-ss", str(start), "-t", str(length),
            "-i", str(path), "-af", "volumedetect", "-f", "null", "-",
        ],
        capture_output=True, text=True,
    )
    for line in proc.stderr.splitlines():
        if "mean_volume:" in line:
            return float(line.rsplit("mean_volume:", 1)[1].replace("dB", "").strip())
    raise AssertionError("volumedetect produced no mean_volume")


def _self_check() -> None:
    assert slot_for(8, None) == (8, False)
    assert slot_for(8, 3) == (8, False)
    assert slot_for(8, 9.25) == (8, True)
    assert abs(playback_rate(9.25, 8) - 9.25 / 8) < 0.001
    assert runtime_warning(81) is None
    assert runtime_warning(50) is not None
    cues = chunk_cues(
        "August again. The Dembi Dollo rain hasn't changed—but your voice, "
        "the one that warmed this house, is gone."
    )
    assert cues
    assert all(cue.count("\n") <= 1 for cue in cues)
    assert all(len(line) <= MAX_LINE_CHARS for cue in cues for line in cue.split("\n"))
    assert all(len(cue.replace("\n", " ").split()) > 2 for cue in cues)
    assert all(_text_width(line) <= MAX_TEXT_W + 0.5 for cue in cues for line in cue.split("\n"))
    closing = chunk_cues(
        "Hear them? Through the Dambi Doolloo rain, they are singing your songs "
        "right back to you. Tonight, my son... I will not cry."
    )
    assert closing
    assert all(len(line) <= MAX_LINE_CHARS and cue.count("\n") <= 1 for cue in closing for line in cue.split("\n"))
    assert all(len(cue.replace("\n", " ").split()) > 2 for cue in closing)
    assert not any(cue.strip() in {"one note.", "weep.", "in silence."} for cue in closing)
    held = _hold_short_cues([(0.0, 2.0, "long line"), (2.0, 2.3, "weep.")])
    assert abs((held[1][1] - held[1][0]) - 1.0) < 0.01
    assert abs(held[0][1] - held[1][0]) < 0.01

    board = {
        "project": {"narration_language": "om", "fps": 24, "subtitle_language": "en"},
        "shots": [
            {"id": "s01", "duration_s": 1, "narration": {"om": "hello", "en": "Hello there friend"}},
            {"id": "s02", "duration_s": 1, "narration": {"om": "", "en": ""}},
        ],
    }
    _placed, miss_err, _warnings, _runtime = plan(
        board, [{"id": "s01", "duration_s": 1, "file": "missing.wav"}]
    )
    assert any("s02" in line for line in miss_err)
    assert any("no audio file" in line or "file not found" in line for line in miss_err)

    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        tone = folder / "voice.wav"
        err = _run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=1.5",
            str(tone),
        ])
        assert err is None, err
        measured, formats = probe_audio(tone)
        assert "wav" in formats and measured >= 1.4
        placed, errors, warnings, runtime = plan(board, [
            {"id": "s01", "duration_s": measured, "file": str(tone)},
            {"id": "s02", "file": "ignored.wav"},
        ])
        assert errors == [], errors
        assert placed[1]["file"] is None
        assert abs(placed[1]["start_s"] - 1) < 0.001
        assert any(line.startswith("s01:") and f"{measured:.3f}" in line and "1.000" in line for line in warnings)
        assert abs(runtime - 2) < 0.001

        _bad, bad_err, _bad_warn, _bad_run = plan(board, [
            {"id": "s01", "duration_s": measured + 1, "file": str(tone)},
            {"id": "s02"},
        ])
        assert any("ffprobe measured" in line for line in bad_err)

        cut = folder / "radio.mp4"
        err = render(placed, 24, cut, runtime, folder / "cues.srt")
        assert err is None, err
        assert abs(audio_seconds(cut) - runtime) <= 0.05
        during_line = _mean_db(cut, 0.15, 0.25)
        after_line = _mean_db(cut, 1.25, 0.2)
        assert during_line > after_line + 6, (during_line, after_line)

        short = folder / "short.wav"
        err = _run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=0.45",
            str(short),
        ])
        assert err is None, err
        short_s, _formats = probe_audio(short)
        diegetic_placed = [
            {
                "id": "s08", "start_s": 0.0, "duration_s": 4.0, "shot_s": 4.0,
                "wav_s": short_s, "rate": 1.0, "file": str(short),
                "en": "Just one old string. Never the song.",
            },
            {
                "id": "s09", "start_s": 4.0, "duration_s": 4.0, "shot_s": 4.0,
                "wav_s": short_s, "rate": 1.0, "file": str(short),
                "en": "Listen, my son. They are singing.",
            },
        ]
        diegetic = folder / "diegetic.mp4"
        err = render(diegetic_placed, 24, diegetic, 8.0, folder / "diegetic.srt")
        assert err is None, err
        rain = _mean_db(diegetic, 0.7, 0.4)
        plucked = _mean_db(diegetic, PLUCK_AT_S + 0.2, 0.4)
        early_hum = _mean_db(diegetic, 4.7, 0.4)
        bloom = _mean_db(diegetic, 6.8, 0.6)
        assert plucked > rain + 6, (plucked, rain)
        assert bloom > early_hum + 1.5, (bloom, early_hum)
    print("self-check ok")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-check":
        _self_check()
    else:
        sys.exit(main())
