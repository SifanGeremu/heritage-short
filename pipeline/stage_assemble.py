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


def wrap_lines(text: str) -> list[str]:
    words = text.replace("\n", " ").split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = word if not current else f"{current} {word}"
        if current and _text_width(trial) > MAX_TEXT_W:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines


def _balance(lines: list[str]) -> list[str]:
    """Pull words down until the two lines are closer, still inside the frame."""
    if len(lines) != 2:
        return lines
    top = lines[0].split()
    bottom = lines[1].split()
    while len(top) > 1:
        trial_bottom = " ".join([top[-1], *bottom])
        if _text_width(trial_bottom) > MAX_TEXT_W:
            break
        trial_top = " ".join(top[:-1])
        before = abs(_text_width(" ".join(top)) - _text_width(" ".join(bottom)))
        after = abs(_text_width(trial_top) - _text_width(trial_bottom))
        if after + 8 >= before:
            break
        bottom.insert(0, top.pop())
    return [" ".join(top), " ".join(bottom)]


def chunk_cues(text: str) -> list[str]:
    """At most two lines, each narrow enough for the 68px caption face."""
    lines = wrap_lines(text)
    cues = []
    for index in range(0, len(lines), 2):
        cues.append("\n".join(_balance(lines[index:index + 2])))
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


def write_ass(cues: list[tuple[float, float, str]], dest: Path) -> None:
    """Bottom safe area on a 1080x1920 frame. PlayRes stops libass scaling cues to the top."""
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,Liberation Sans,{FONT_SIZE},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,"
        f"-1,0,0,0,100,100,0,0,1,{OUTLINE},1,2,{MARGIN_X},{MARGIN_X},{MARGIN_V},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for start, end, text in cues:
        body = text.replace("\\", "").replace("{", "").replace("}", "").replace("\n", r"\N")
        lines.append(
            f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Default,,0,0,0,,{body}"
        )
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_srt(cues: list[tuple[float, float, str]], dest: Path) -> None:
    blocks = []
    for index, (start, end, text) in enumerate(cues, start=1):
        blocks.append(f"{index}\n{_srt_time(start)} --> {_srt_time(end)}\n{text}\n")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(blocks), encoding="utf-8")


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


def build_cues(placed: list[dict]) -> list[tuple[float, float, str]]:
    cues = []
    for shot in placed:
        if not shot.get("en"):
            continue
        start, end = spoken_window(shot)
        cues.extend(_hold_short_cues(cue_windows(chunk_cues(shot["en"]), start, end)))
    return cues


def _run(cmd: list[str]) -> str | None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "ffmpeg failed").strip()
        return detail[-2000:]
    return None


def _filter_path(path: Path) -> str:
    return path.as_posix().replace("\\", "\\\\").replace(":", "\\:").replace("'", r"\'")


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

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", f"color=c=black:s={FRAME}:r={fps}:d={runtime:.3f}",
        "-f", "lavfi", "-t", f"{runtime:.3f}", "-i",
        f"anoisesrc=color=pink:sample_rate=48000:amplitude=1",
    ]
    for _shot, path in voices:
        cmd += ["-i", str(path)]

    fade_out = max(0.0, runtime - FADE_S)
    filters = [
        f"[1:a]lowpass=f=1200,volume=-26dB,afade=t=in:st=0:d={FADE_S:.3f},"
        f"afade=t=out:st={fade_out:.3f}:d={FADE_S:.3f}[pad]"
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
    if labels:
        n = 1 + len(labels)
        filters.append(
            f"[pad]{''.join(labels)}amix=inputs={n}:normalize=0:duration=first:dropout_transition=0[mix]"
        )
        audio = "[mix]"
    else:
        audio = "[pad]"

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
    assert all(_text_width(line) <= MAX_TEXT_W + 0.5 for cue in cues for line in cue.split("\n"))
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
    print("self-check ok")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-check":
        _self_check()
    else:
        sys.exit(main())
