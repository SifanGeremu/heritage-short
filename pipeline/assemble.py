#!/usr/bin/env python3
"""Cut the film from storyboard shots, narration, and the chosen score.

The voice is one telling: each line starts when the previous line ends, so
the breaths stay even and two lines never speak at once. The picture holds
with that line. The score is trimmed to the film, faded out, and ducked
under the voice. Two-pass loudnorm lands the mix at -14 LUFS. English lines
are burned into each export, and a drawn end card closes the picture.

The 16:9 export fits the whole 9:16 frame in the centre. The sides are a
blurred copy of the same picture, so heads and feet are not cropped away.
"""

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ROOT, audio_seconds, log_run
from stage_assemble import (
    FONT,
    FONT_SIZE,
    MARGIN_V,
    MARGIN_X,
    OUTLINE,
    PAD_LEAD_S,
    PAD_TAIL_S,
    _filter_path,
    _hold_short_cues,
    assert_subtitle_coverage,
    chunk_cues,
    cue_windows,
    write_ass,
    write_pluck,
)
from validate import ensure_storyboard

SHOT_DIR = ROOT / "outputs" / "shots"
MUSIC_DIR = ROOT / "outputs" / "music"
TIMING_PATH = ROOT / "outputs" / "narration" / "timing.json"
WORK = ROOT / "outputs" / "assemble"
PORTRAIT = ROOT / "outputs" / "film_9x16.mp4"
LANDSCAPE = ROOT / "outputs" / "film_16x9.mp4"

WIDTH = 1080
HEIGHT = 1920
FPS = 24
FADE_S = 0.4
MUSIC_FADE_S = 2.0
# ponytail: fixed bed gain, voice left at unity, then the sidechain pulls the
# bed down. Upgrade path: set the bed from a measured voice LUFS instead.
MUSIC_GAIN = 0.32
# Slower than the raw take so the lines feel told, not announced. Pitch stays.
STORY_TEMPO = 0.88
# Quiet after the last line, before the end card. The pads inside each wav
# are already the breath between sentences.
HOLD_S = 0.8
END_TEXT = "Made with AI"


def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def timeline(durations: list[float], fade: float) -> tuple[list[float], float]:
    """Shot start times after overlaps, and the picture length before the end card."""
    if not durations:
        raise ValueError("no shots")
    if len(durations) > 1 and any(d <= fade for d in durations):
        raise ValueError("a shot is shorter than the crossfade")
    starts = []
    cursor = 0.0
    for index, duration in enumerate(durations):
        starts.append(round(cursor, 3))
        overlap = fade if index < len(durations) - 1 else 0.0
        cursor += duration - overlap
    return starts, round(cursor, 3)


def played_seconds(wav_s: float, tempo: float = STORY_TEMPO) -> float:
    return wav_s / tempo


def picture_slots(wavs: list[float], fade: float, hold: float, tempo: float = STORY_TEMPO) -> list[float]:
    """Each shot stays up for its line. The crossfade sits in the breath before the next line."""
    if not wavs:
        raise ValueError("no narration")
    slots = []
    last = len(wavs) - 1
    for index, wav_s in enumerate(wavs):
        extra = fade if index < last else hold
        slots.append(played_seconds(wav_s, tempo) + extra)
    return slots


def speech_window(start: float, wav_s: float) -> tuple[float, float]:
    played = played_seconds(wav_s)
    lead = PAD_LEAD_S / STORY_TEMPO
    tail = PAD_TAIL_S / STORY_TEMPO
    speech_start = start + lead
    speech_end = start + max(0.0, played - tail)
    if speech_end <= speech_start + 0.05:
        return start, start + played
    return speech_start, speech_end


def caption_cues(placed: list[dict]) -> list[tuple[float, float, str, str]]:
    cues = []
    for shot in placed:
        text = (shot.get("en") or "").strip()
        if not text:
            continue
        start, end = speech_window(shot["start"], shot["wav_s"])
        for window in _hold_short_cues(cue_windows(chunk_cues(text), start, end)):
            cues.append((*window, shot.get("id") or ""))
    return cues


def video_filter(n: int, durations: list[float], sources: list[float], fade: float, font: str) -> str:
    parts = []
    for i in range(n):
        slot = durations[i]
        pad = max(0.0, slot - sources[i])
        hold = f",tpad=stop_mode=clone:stop_duration={pad:.3f}" if pad >= 0.02 else ""
        parts.append(
            f"[{i}:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{HEIGHT},fps={FPS},setpts=PTS-STARTPTS{hold},"
            f"trim=duration={slot:.3f},setpts=PTS-STARTPTS,format=yuv420p[v{i}]"
        )
    label = "v0"
    elapsed = durations[0]
    for i in range(1, n):
        offset = elapsed - fade
        out = f"x{i}"
        parts.append(
            f"[{label}][v{i}]xfade=transition=fade:duration={fade:.3f}:offset={offset:.3f}[{out}]"
        )
        label = out
        elapsed += durations[i] - fade
    font_esc = _filter_path(Path(font))
    parts.append(f"[{label}]fps={FPS},settb=AVTB,format=yuv420p,setsar=1[picture]")
    parts.append(
        f"[{n}:v]fps={FPS},settb=AVTB,format=yuv420p,setsar=1,"
        f"drawtext=fontfile='{font_esc}':text='{END_TEXT}':fontsize=64:"
        f"fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2[card]"
    )
    parts.append("[picture][card]concat=n=2:v=1:a=0[vout]")
    return ";".join(parts)


def audio_filter(starts: list[float], film: float, pluck_at: float | None = None) -> str:
    """Music is input n, after one narration input per shot.

    sidechaincompress attack and release are milliseconds.
    A pluck, when present, is input n+1 and is not ducked.
    """
    parts = []
    labels = []
    for i, start in enumerate(starts):
        ms = max(0, int(round(start * 1000)))
        parts.append(
            f"[{i}:a]atempo={STORY_TEMPO},"
            f"aformat=sample_rates=48000:channel_layouts=stereo,"
            f"adelay={ms}:all=1,apad=whole_dur={film:.3f}[n{i}]"
        )
        labels.append(f"[n{i}]")
    n = len(starts)
    parts.append(
        "".join(labels)
        + f"amix=inputs={n}:duration=longest:normalize=0:dropout_transition=0[voice]"
    )
    parts.append("[voice]asplit=2[voice_mix][voice_sc]")
    fade_at = max(0.0, film - MUSIC_FADE_S)
    fade_d = min(MUSIC_FADE_S, film)
    parts.append(
        f"[{n}:a]aformat=sample_rates=48000:channel_layouts=stereo,"
        f"volume={MUSIC_GAIN},atrim=0:{film:.3f},asetpts=PTS-STARTPTS,"
        f"afade=t=out:st={fade_at:.3f}:d={fade_d:.3f},apad=whole_dur={film:.3f}[bed]"
    )
    parts.append(
        "[bed][voice_sc]sidechaincompress="
        "threshold=0.02:ratio=6:attack=300:release=1500[ducked]"
    )
    tail = "[voice_mix][ducked]"
    inputs = 2
    if pluck_at is not None:
        ms = max(0, int(round(pluck_at * 1000)))
        parts.append(
            f"[{n + 1}:a]aformat=sample_rates=48000:channel_layouts=stereo,"
            f"volume=2.0,adelay={ms}:all=1,apad=whole_dur={film:.3f}[pluck]"
        )
        tail += "[pluck]"
        inputs = 3
    parts.append(
        f"{tail}amix=inputs={inputs}:duration=longest:normalize=0:dropout_transition=0,"
        f"atrim=0:{film:.3f},asetpts=PTS-STARTPTS[aout]"
    )
    return ";".join(parts)


def loudnorm_second(measured: dict) -> str:
    return (
        "loudnorm=I=-14:TP=-1:LRA=11:"
        f"measured_I={measured['input_i']}:measured_TP={measured['input_tp']}:"
        f"measured_LRA={measured['input_lra']}:measured_thresh={measured['input_thresh']}:"
        f"offset={measured['target_offset']}:linear=true"
    )


def parse_loudnorm(stderr: str) -> dict:
    start = stderr.rfind("{")
    end = stderr.rfind("}")
    if start < 0 or end < start:
        raise SystemExit("loudnorm did not print measurements")
    data = json.loads(stderr[start:end + 1])
    missing = [key for key in ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset") if key not in data]
    if missing:
        raise SystemExit(f"loudnorm missing {', '.join(missing)}")
    return data


def subtitles_filter(path: Path, size: str) -> str:
    return f"subtitles=filename='{_filter_path(path)}':original_size={size}"


def ffmpeg(step: str, cmd: list[str], parameters: dict, output: Path | None, *, log: bool = True):
    started = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    latency = round(time.perf_counter() - started, 3)
    if log:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stage": "assemble",
            "provider": "ffmpeg",
            "model": step,
            "parameters": parameters,
            "seed": None,
            "latency": latency,
            "cost": 0,
            "status": "ok" if proc.returncode == 0 else "error",
            "output_path": _rel(output) if output else None,
        }
        if proc.returncode != 0:
            record["error"] = (proc.stderr or proc.stdout or "ffmpeg failed")[-500:]
        log_run(record)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "ffmpeg failed").strip()
        raise SystemExit(f"assemble {step} failed:\n{detail[-1500:]}")
    return proc


def shot_clip(sid: str) -> Path | None:
    found = [
        path for path in SHOT_DIR.glob(f"{sid}_*.mp4")
        if ".part." not in path.name
    ]
    if not found:
        return None
    return max(found, key=lambda path: path.stat().st_mtime)


def load_timing() -> dict[str, dict]:
    data = json.loads(TIMING_PATH.read_text(encoding="utf-8"))
    return {row["id"]: row for row in data.get("shots") or []}


def collect_inputs(board: dict) -> tuple[list[dict], Path, float]:
    """Resolve clips, narration, and the score. Every miss is reported together."""
    timing = load_timing() if TIMING_PATH.is_file() else {}
    problems = []
    placed = []
    for shot in board["shots"]:
        sid = shot["id"]
        clip = shot_clip(sid)
        row = timing.get(sid)
        if clip is None:
            problems.append(f"missing shot clip: outputs/shots/{sid}_*.mp4")
        wav = None
        wav_s = None
        if row is None:
            problems.append(f"missing timing for {sid}")
        else:
            wav = ROOT / row["file"]
            wav_s = float(row["duration_s"])
            if not wav.is_file():
                problems.append(f"missing narration: {row['file']}")
                wav = None
        placed.append(
            {
                "id": sid,
                "clip": clip,
                "duration_s": float(shot["duration_s"]),
                "wav": wav,
                "wav_s": wav_s,
                "en": (shot.get("narration") or {}).get("en") or "",
            }
        )
    seed = board["music"]["selected_seed"]
    music = MUSIC_DIR / f"music_{seed}.wav"
    if not music.is_file():
        on_disk = sorted(path.name for path in MUSIC_DIR.glob("music_*.wav"))
        found = ", ".join(on_disk) if on_disk else "none"
        problems.append(
            f"chosen music: music.selected_seed is {seed}, but {_rel(music)} is missing "
            f"(on disk: {found})"
        )
    if problems:
        raise SystemExit("assemble stopped:\n" + "\n".join(problems))
    end_s = float(board["project"]["end_card_duration_s"])
    return placed, music, end_s


def probe(path: Path) -> dict:
    out = subprocess.check_output(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-show_entries", "stream=codec_type,codec_name,width,height,avg_frame_rate",
            "-of", "json",
            str(path),
        ],
        text=True,
    )
    return json.loads(out)


def landscape_filter(ass: Path) -> str:
    """Fit the full portrait frame. Blurred sides fill 16:9. The photo is not cropped.

    ponytail: the side fill is a blurred cover of the same frame. Upgrade path:
    design a real 16:9 frame per shot.
    """
    subs = subtitles_filter(ass, "1920x1080")
    return (
        "[0:v]split[sharp][wide];"
        "[wide]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,boxblur=24:2[bg];"
        "[sharp]scale=1920:1080:force_original_aspect_ratio=decrease:flags=lanczos,setsar=1[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2,{subs}[vout]"
    )


def write_master(
    clips: list[Path],
    durations: list[float],
    sources: list[float],
    end_s: float,
    dest: Path,
    *,
    log: bool,
) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    for clip in clips:
        cmd += ["-i", str(clip)]
    cmd += [
        "-f", "lavfi", "-i", f"color=c=black:s={WIDTH}x{HEIGHT}:r={FPS}:d={end_s}",
        "-filter_complex", video_filter(len(clips), durations, sources, FADE_S, FONT),
        "-map", "[vout]", "-an",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        str(dest),
    ]
    ffmpeg(
        "picture",
        cmd,
        {"fade_s": FADE_S, "end_card_s": end_s, "shots": len(clips), "end_card": END_TEXT},
        dest,
        log=log,
    )


def write_mix(
    wavs: list[Path],
    starts: list[float],
    music: Path,
    film: float,
    dest: Path,
    *,
    log: bool,
    pluck: Path | None = None,
    pluck_at: float | None = None,
) -> None:
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    for wav in wavs:
        cmd += ["-i", str(wav)]
    cmd += ["-i", str(music)]
    if pluck is not None and pluck_at is not None:
        cmd += ["-i", str(pluck)]
    else:
        pluck_at = None
    cmd += [
        "-filter_complex", audio_filter(starts, film, pluck_at),
        "-map", "[aout]",
        "-c:a", "pcm_s16le", "-ar", "48000",
        str(dest),
    ]
    ffmpeg(
        "mix",
        cmd,
        {
            "film_s": film,
            "music_fade_s": MUSIC_FADE_S,
            "music_gain": MUSIC_GAIN,
            "sidechain": "threshold=0.02:ratio=6:attack=300:release=1500",
        },
        dest,
        log=log,
    )


def measure_loudnorm(mix: Path, *, log: bool) -> dict:
    proc = ffmpeg(
        "loudnorm-measure",
        [
            "ffmpeg", "-hide_banner", "-i", str(mix),
            "-af", "loudnorm=I=-14:TP=-1:LRA=11:print_format=json",
            "-f", "null", "-",
        ],
        {"I": -14, "TP": -1, "pass": 1},
        None,
        log=log,
    )
    return parse_loudnorm(proc.stderr)


def apply_loudnorm(mix: Path, measured: dict, dest: Path, *, log: bool) -> None:
    ffmpeg(
        "loudnorm-apply",
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(mix),
            "-af", loudnorm_second(measured),
            "-c:a", "pcm_s16le", "-ar", "48000",
            str(dest),
        ],
        {"I": -14, "TP": -1, "pass": 2, "measured_I": measured["input_i"]},
        dest,
        log=log,
    )


def write_exports(master: Path, audio: Path, cues: list, work: Path, portrait: Path, landscape: Path, *, log: bool) -> None:
    # Same cues, different safe area. The 16:9 line sits under the full photo,
    # not under a centre crop.
    ass_9 = work / "subs_9x16.ass"
    ass_16 = work / "subs_16x9.ass"
    write_ass(
        cues, ass_9,
        play_x=WIDTH, play_y=HEIGHT, font_size=FONT_SIZE,
        margin_x=MARGIN_X, margin_v=MARGIN_V, outline=OUTLINE,
    )
    write_ass(cues, ass_16, play_x=1920, play_y=1080, font_size=48, margin_x=160, margin_v=64, outline=2)
    video = ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS)]
    audio_args = ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]
    ffmpeg(
        "export-9x16",
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(master), "-i", str(audio),
            "-vf", subtitles_filter(ass_9, f"{WIDTH}x{HEIGHT}"),
            "-map", "0:v", "-map", "1:a",
            *video, *audio_args, "-movflags", "+faststart",
            str(portrait),
        ],
        {"size": f"{WIDTH}x{HEIGHT}", "fps": FPS, "subtitles": _rel(ass_9)},
        portrait,
        log=log,
    )
    ffmpeg(
        "export-16x9",
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(master), "-i", str(audio),
            "-filter_complex", landscape_filter(ass_16),
            "-map", "[vout]", "-map", "1:a",
            *video, *audio_args, "-movflags", "+faststart",
            str(landscape),
        ],
        {"size": "1920x1080", "fit": "full portrait, blurred sides", "fps": FPS},
        landscape,
        log=log,
    )


def build(
    placed: list[dict],
    music: Path,
    end_s: float,
    *,
    log: bool = True,
    work: Path = WORK,
    portrait: Path = PORTRAIT,
    landscape: Path = LANDSCAPE,
) -> tuple[Path, Path]:
    sources = []
    for shot in placed:
        probed = audio_seconds(shot["clip"])
        sources.append(probed)
        shot["clip_s"] = probed
    durations = picture_slots([shot["wav_s"] for shot in placed], FADE_S, HOLD_S, STORY_TEMPO)
    starts, picture = timeline(durations, FADE_S)
    for shot, start in zip(placed, starts):
        shot["start"] = start
    if not Path(FONT).is_file():
        raise SystemExit(f"caption font missing: {FONT}")
    work.mkdir(parents=True, exist_ok=True)
    master = work / "master.mp4"
    mix = work / "mix.wav"
    loud = work / "loud.wav"
    for shot in placed:
        end = shot["start"] + played_seconds(shot["wav_s"])
        print(f"{shot['id']}: voice {shot['start']:.2f}s–{end:.2f}s")
    write_master([shot["clip"] for shot in placed], durations, sources, end_s, master, log=log)
    film = audio_seconds(master)
    if abs(film - (picture + end_s)) > 0.15:
        print(f"picture length {film:.3f}s, expected {picture + end_s:.3f}s", file=sys.stderr)
    pluck_at = None
    pluck_path = None
    for shot in placed:
        if shot["id"] == "s08":
            # Source-wav gap, stretched by the same tempo as the voice.
            pluck_at = shot["start"] + 3.3 / STORY_TEMPO
            pluck_path = work / "pluck.wav"
            write_pluck(pluck_path)
            break
    write_mix(
        [shot["wav"] for shot in placed], starts, music, film, mix,
        log=log, pluck=pluck_path, pluck_at=pluck_at,
    )
    measured = measure_loudnorm(mix, log=log)
    print(f"loudnorm in: {measured['input_i']} LUFS, true peak {measured['input_tp']} dB")
    apply_loudnorm(mix, measured, loud, log=log)
    cues = caption_cues(placed)
    write_exports(master, loud, cues, work, portrait, landscape, log=log)
    end_card_at = film - end_s
    assert_subtitle_coverage(work / "subs_16x9.ass", placed, end_card_at)
    assert_subtitle_coverage(work / "subs_9x16.ass", placed, end_card_at)
    for path in (mix, loud, master):
        path.unlink(missing_ok=True)
    return portrait, landscape


def report(path: Path) -> None:
    data = probe(path)
    video = next(stream for stream in data["streams"] if stream.get("codec_type") == "video")
    audio = next(stream for stream in data["streams"] if stream.get("codec_type") == "audio")
    print(
        f"{_rel(path)} {video['width']}x{video['height']} {video['avg_frame_rate']} "
        f"{video['codec_name']}/{audio['codec_name']} {float(data['format']['duration']):.3f}s"
    )


def self_check() -> int:
    starts, picture = timeline([8, 8, 7, 8], FADE_S)
    assert starts == [0.0, 7.6, 15.2, 21.8], starts
    assert picture == 29.8
    slots = picture_slots([6.0, 5.0, 4.0], FADE_S, HOLD_S, 1.0)
    voice_starts, _picture = timeline(slots, FADE_S)
    assert voice_starts == [0.0, 6.0, 11.0], voice_starts
    wide = landscape_filter(ROOT / "outputs" / "assemble" / "subs_16x9.ass")
    assert "force_original_aspect_ratio=decrease" in wide
    assert "1080:608" not in wide
    sample = {
        "input_i": "-18.10",
        "input_tp": "-2.40",
        "input_lra": "6.20",
        "input_thresh": "-28.50",
        "target_offset": "0.10",
    }
    second = loudnorm_second(sample)
    assert "measured_I=-18.10" in second and "linear=true" in second
    assert parse_loudnorm('noise {"input_i":"-18.10","input_tp":"-2.40","input_lra":"6.20","input_thresh":"-28.50","target_offset":"0.10"}')["input_i"] == "-18.10"
    cues = caption_cues(
        [{"en": "August again. The Dembi Dollo rain hasn't changed, but your voice is gone.", "start": 0.0, "wav_s": 6.0}]
    )
    assert cues and all(cue.count("\n") <= 1 for _, _, cue, _sid in cues)
    assert all(len(line) <= 40 for _, _, cue, _sid in cues for line in cue.split("\n"))

    work = WORK / "_check"
    work.mkdir(parents=True, exist_ok=True)
    clips = []
    for index, color in enumerate(("0x203040", "0x402010")):
        path = work / f"c{index}.mp4"
        subprocess.check_call(
            [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-f", "lavfi", "-i", f"color=c={color}:s={WIDTH}x{HEIGHT}:r={FPS}:d=1",
                "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                str(path),
            ]
        )
        clips.append(path)
    voice = work / "voice.wav"
    score = work / "score.wav"
    subprocess.check_call(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=0.8",
            "-c:a", "pcm_s16le", str(voice),
        ]
    )
    subprocess.check_call(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "sine=frequency=220:duration=4",
            "-c:a", "pcm_s16le", str(score),
        ]
    )
    placed = [
        {"id": "a", "clip": clips[0], "wav": voice, "wav_s": 0.8, "en": "August again."},
        {"id": "b", "clip": clips[1], "wav": voice, "wav_s": 0.8, "en": "The rain hasn't changed."},
    ]
    portrait = work / "out9.mp4"
    landscape = work / "out16.mp4"
    try:
        build(placed, score, 0.5, log=False, work=work, portrait=portrait, landscape=landscape)
        wide = probe(landscape)
        tall = probe(portrait)
        video_w = next(stream for stream in wide["streams"] if stream["codec_type"] == "video")
        video_t = next(stream for stream in tall["streams"] if stream["codec_type"] == "video")
        assert (video_t["width"], video_t["height"]) == (1080, 1920)
        assert (video_w["width"], video_w["height"]) == (1920, 1080)
        assert video_t["codec_name"] == "h264"
        assert abs(float(tall["format"]["duration"]) - float(wide["format"]["duration"])) < 0.05
    finally:
        for path in work.glob("*"):
            if path.is_file():
                path.unlink()
        work.rmdir()
    print("self-check ok")
    return 0


def main() -> int:
    if "--check" in sys.argv:
        return self_check()
    board = ensure_storyboard()
    placed, music, end_s = collect_inputs(board)
    portrait, landscape = build(placed, music, end_s)
    report(portrait)
    report(landscape)
    return 0


if __name__ == "__main__":
    sys.exit(main())
