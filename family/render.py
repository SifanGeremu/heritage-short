#!/usr/bin/env python3
"""Paint and cut one family film under outputs/family/. Never the graded film."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

from shots import FPS, HEIGHT, WIDTH, zoompan  # noqa: E402

from board import REFERENCE_SEED, SHOT_S, VOICE, build  # noqa: E402

FAMILY = ROOT / "outputs" / "family"
SLOW = 0.88
END_CARD_S = 3
DRY_COLORS = {
    "ref.jpg": "0x141210",
    "s01.jpg": "0x3E4A57",
    "s02.jpg": "0x6B4A32",
    "s03.jpg": "0xC4A882",
}


def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def ffmpeg(args: list[str]) -> None:
    proc = subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "ffmpeg failed").strip()
        raise RuntimeError(detail[-500:])


def filter_path(path: Path) -> str:
    return path.as_posix().replace("\\", "\\\\").replace(":", "\\:").replace("'", r"\'")


def font_file() -> Path:
    for path in (
        ROOT / "family" / "fonts" / "DejaVuSans-Bold.ttf",
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"),
    ):
        if path.is_file():
            return path
    raise RuntimeError("no font for the Made with AI card")


def family_log(record: dict, dest: Path) -> None:
    """Append one line under outputs/family/. A temp self-check does not."""
    from common import read_key

    if FAMILY.resolve() not in dest.resolve().parents:
        return
    text = json.dumps(record, ensure_ascii=False)
    for name in ("CLOUDFLARE_API_TOKEN", "ADDIS-AI-API-KEY", "CLOUDFLARE_ACCOUNT_ID"):
        key = read_key(name)
        if key:
            text = text.replace(key, "[redacted]")
    FAMILY.mkdir(parents=True, exist_ok=True)
    with (FAMILY / "runs.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(text + "\n")


def _flat(path: Path, color: str) -> None:
    ffmpeg(
        [
            "-f", "lavfi", "-i", f"color=c={color}:s={WIDTH}x{HEIGHT}:d=0.1",
            "-frames:v", "1", str(path),
        ]
    )


def _silent(path: Path, seconds: float = 3) -> None:
    ffmpeg(["-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{seconds:.3f}", str(path)])


def _tone(path: Path, seconds: float) -> None:
    ffmpeg(
        [
            "-f", "lavfi",
            "-i", f"sine=frequency=196:sample_rate=44100:duration={seconds:.3f}",
            "-af", "volume=0.04",
            str(path),
        ]
    )


def find_bed() -> Path | None:
    music = ROOT / "outputs" / "music"
    if not music.is_dir():
        return None
    found = sorted(music.glob("*303*.wav"))
    return found[0] if found else None


def to_jpg(data: bytes, dest: Path) -> None:
    from providers.cloudflare import image_ext

    dest.parent.mkdir(parents=True, exist_ok=True)
    ext = image_ext(data)
    if ext in ("jpg", "jpeg"):
        dest.write_bytes(data)
        return
    raw = dest.with_suffix("." + ext)
    raw.write_bytes(data)
    ffmpeg(["-i", str(raw), "-frames:v", "1", str(dest)])


def _paint(prompt: str, seed: int, dest: Path, reference: bytes | None, stage: str) -> None:
    from common import fail, read_key, with_retry, _daily_limit
    from providers.cloudflare import KLEIN, generate

    account = read_key("CLOUDFLARE_ACCOUNT_ID")
    token = read_key("CLOUDFLARE_API_TOKEN")
    held: dict = {}

    def once():
        record = {
            "stage": stage,
            "provider": "cloudflare",
            "model": KLEIN,
            "parameters": {"prompt": prompt, "seed": seed, "width": WIDTH, "height": HEIGHT},
            "seed": seed,
            "cost": 0,
        }
        try:
            image = generate(
                account,
                token,
                KLEIN,
                prompt,
                width=WIDTH,
                height=HEIGHT,
                seed=seed,
                images={"input_image_0": reference} if reference else None,
            )
            to_jpg(image, dest)
        except Exception as err:
            held["error"] = err
            fail(err, record, token)
        record["output_path"] = _rel(dest)
        return record

    if not with_retry(once, log=lambda record: family_log(record, dest.parent)):
        err = held.get("error")
        if err is not None and _daily_limit(str(err)):
            _other_picture(prompt, seed, dest, reference)
            family_log(
                {
                    "stage": stage,
                    "provider": "pollinations",
                    "model": "flux",
                    "parameters": {"prompt": prompt, "seed": seed},
                    "seed": seed,
                    "latency": 0,
                    "cost": 0,
                    "status": "ok",
                    "output_path": _rel(dest),
                },
                dest.parent,
            )
            return
        raise RuntimeError("A picture did not come back.")


def _kept(path: Path) -> bool:
    """A flat dry frame is about 12KB. A real voice is not a silent file."""
    if not path.is_file() or path.stat().st_size < 20000:
        return False
    if path.suffix == ".wav":
        import wave

        with wave.open(str(path)) as handle:
            chunk = handle.readframes(4000)
        return any(chunk)
    return True


def _other_picture(prompt: str, seed: int, dest: Path, reference: bytes | None) -> None:
    from common import read_key
    from providers.gemini import IMAGE_MODEL, generate_image

    key = read_key("GEMINI_API_KEY")
    if key:
        try:
            image = generate_image(key, IMAGE_MODEL, prompt, reference)
            to_jpg(image, dest)
            return
        except Exception:
            pass
    _pollinations(prompt, seed, dest)


def _pollinations(prompt: str, seed: int, dest: Path) -> None:
    """Cloudflare's free day is one account. This is the same backup the film uses."""
    import urllib.parse
    import urllib.request

    text = prompt.replace(". The person from image 0", "")
    low = text.lower()
    for needle in ("wide shot", "medium shot", "character portrait", "the painted"):
        at = low.rfind(needle)
        if at > 0:
            text = text[at:]
            break
    if len(text) > 700:
        text = text[:700]
    query = urllib.parse.urlencode(
        {"width": 768, "height": 1344, "seed": seed, "nologo": "true", "model": "flux"}
    )
    url = "https://image.pollinations.ai/prompt/" + urllib.parse.quote(text) + "?" + query
    req = urllib.request.Request(url, headers={"User-Agent": "heritage-short"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        image = resp.read()
    if not (image.startswith(b"\xff\xd8\xff") or image.startswith(b"\x89PNG")):
        raise RuntimeError("A picture did not come back.")
    to_jpg(image, dest)


def _speak(text: str, dest: Path) -> None:
    from common import audio_seconds, fail, read_key, with_retry
    from providers.addis import cost_etb, synthesize

    key = read_key("ADDIS-AI-API-KEY")
    held: dict = {}

    def once():
        record = {
            "stage": "family-narration",
            "provider": "addis",
            "model": VOICE,
            "parameters": {"voice": VOICE, "language": "om", "text": text},
            "seed": None,
            "cost": 0,
        }
        try:
            dest.write_bytes(synthesize(key, text, voice=VOICE, language="om"))
            record["cost"] = cost_etb(audio_seconds(dest))
            record["audio_seconds"] = audio_seconds(dest)
        except Exception as err:
            held["error"] = err
            fail(err, record, key)
        record["output_path"] = _rel(dest)
        return record

    if not with_retry(once, log=lambda record: family_log(record, dest.parent)):
        raise RuntimeError("The voice did not answer.")


def _clip(image: Path, dest: Path, kind: str, frames: int) -> None:
    partial = dest.with_suffix(".part.mp4")
    ffmpeg(
        [
            "-i", str(image),
            "-vf", zoompan(kind, frames),
            "-frames:v", str(frames),
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(partial),
        ]
    )
    partial.replace(dest)


def _concat(clips: list[Path], dest: Path) -> None:
    args: list[str] = []
    for clip in clips:
        args += ["-i", str(clip)]
    ins = "".join(f"[{i}:v]" for i in range(len(clips)))
    ffmpeg(
        args
        + [
            "-filter_complex", f"{ins}concat=n={len(clips)}:v=1:a=0[v]",
            "-map", "[v]",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(dest),
        ]
    )


def _wrap(text: str, width: int = 36) -> str:
    lines: list[str] = []
    current = ""
    for word in text.split():
        trial = (current + " " + word).strip()
        if len(trial) > width and current:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return "\n".join(lines[:4])


def _srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    hours, ms = divmod(ms, 3_600_000)
    minutes, ms = divmod(ms, 60_000)
    secs, ms = divmod(ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def _write_srt(path: Path, cues: list[tuple[float, float, str]]) -> None:
    blocks = []
    for index, (start, end, text) in enumerate(cues, start=1):
        blocks.append(f"{index}\n{_srt_time(start)} --> {_srt_time(end)}\n{_wrap(text)}\n")
    path.write_text("\n".join(blocks), encoding="utf-8")


def _audio_filter(slots: list[float], film: float) -> str:
    parts = []
    labels = []
    cursor = 0.0
    for index, _slot in enumerate(slots):
        ms = max(0, int(round(cursor * 1000)))
        parts.append(
            f"[{index}:a]atempo={SLOW},"
            f"aformat=sample_rates=48000:channel_layouts=stereo,"
            f"adelay={ms}:all=1,apad=whole_dur={film:.3f}[n{index}]"
        )
        labels.append(f"[n{index}]")
        cursor += _slot
    count = len(slots)
    parts.append(
        "".join(labels)
        + f"amix=inputs={count}:duration=longest:normalize=0:dropout_transition=0[voice]"
    )
    parts.append("[voice]asplit=2[voice_mix][voice_sc]")
    fade_at = max(0.0, film - 2.0)
    parts.append(
        f"[{count}:a]aformat=sample_rates=48000:channel_layouts=stereo,"
        f"volume=0.32,atrim=0:{film:.3f},asetpts=PTS-STARTPTS,"
        f"afade=t=out:st={fade_at:.3f}:d=2,apad=whole_dur={film:.3f}[bed]"
    )
    parts.append(
        "[bed][voice_sc]sidechaincompress="
        "threshold=0.02:ratio=6:attack=300:release=1500[ducked]"
    )
    parts.append(
        "[voice_mix][ducked]amix=inputs=2:duration=longest:normalize=0:dropout_transition=0,"
        f"atrim=0:{film:.3f},asetpts=PTS-STARTPTS[aout]"
    )
    return ";".join(parts)


def _notify(on_status, **payload) -> None:
    if on_status:
        on_status(payload)


def render(board: dict, dest: Path, *, dry: bool, on_status=None) -> Path:
    """Write dest/film.mp4. dry paints flat frames and silence, and calls no API."""
    from common import audio_seconds, read_key

    if board.get("character", {}).get("is_real_person") is not False:
        raise RuntimeError("a family film cannot use a real person")
    dest.mkdir(parents=True, exist_ok=True)
    shots = board["shots"]
    if len(shots) != 3:
        raise RuntimeError("a family film is three shots")
    if not dry:
        if not read_key("ADDIS-AI-API-KEY"):
            raise RuntimeError("ADDIS-AI-API-KEY is missing from .env")
        if not read_key("CLOUDFLARE_ACCOUNT_ID") or not read_key("CLOUDFLARE_API_TOKEN"):
            raise RuntimeError("CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN are required in .env")

    frames: list[str] = []
    _notify(on_status, status="working", step="Writing her voice", frames=frames)
    wavs: list[Path] = []
    for shot in shots:
        wav = dest / f"{shot['id']}.wav"
        if dry:
            _silent(wav)
        elif not _kept(wav):
            _speak(shot["narration"]["om"], wav)
        wavs.append(wav)

    _notify(on_status, status="working", step="Painting her face", frames=list(frames))
    ref = dest / "ref.jpg"
    if dry:
        _flat(ref, DRY_COLORS["ref.jpg"])
    elif _kept(ref):
        pass
    else:
        who = board["character"]["description"]
        _paint(
            (
                f"{who}. character portrait, front view, neutral tender expression, "
                "soft warm side light, neutral mud-wall background. "
                f"{board['style_block']}. Painted character, not a portrait of any real person, "
                "no readable text"
            ),
            int(board["character"]["reference_seed"]),
            ref,
            None,
            "family-reference",
        )
    small = dest / "ref_480.jpg"
    ffmpeg(
        [
            "-i", str(ref),
            "-vf", "scale=480:480:force_original_aspect_ratio=decrease",
            str(small),
        ]
    )
    reference = small.read_bytes() if not dry else b""
    frames.append(ref.name)

    labels = ("Painting the room", "Painting the memory", "Painting the doorway")
    stills: list[Path] = []
    for shot, label in zip(shots, labels):
        _notify(on_status, status="working", step=label, frames=list(frames))
        still = dest / f"{shot['id']}.jpg"
        if dry:
            _flat(still, DRY_COLORS[still.name])
        elif _kept(still):
            pass
        else:
            _paint(
                shot["image_prompt"] + ". The person from image 0",
                int(shot["seed"]),
                still,
                reference,
                "family-keyframe",
            )
        frames.append(still.name)
        stills.append(still)
        _notify(on_status, status="working", step=label, frames=list(frames))

    _notify(on_status, status="working", step="Cutting the film", frames=list(frames))
    slots = [max(float(SHOT_S), round(audio_seconds(wav) / SLOW + 0.35, 3)) for wav in wavs]
    clips = []
    for shot, still, slot in zip(shots, stills, slots):
        clip = dest / f"{shot['id']}.mp4"
        _clip(still, clip, str(shot["motion"]), max(1, int(round(slot * FPS))))
        clips.append(clip)

    picture = dest / "picture.mp4"
    _concat(clips, picture)
    cues = []
    cursor = 0.0
    for shot, slot in zip(shots, slots):
        cues.append((cursor, cursor + slot, shot["narration"]["en"]))
        cursor += slot
    srt = dest / "subs.srt"
    _write_srt(srt, cues)
    burned = dest / "burned.mp4"
    ffmpeg(
        [
            "-i", str(picture),
            "-vf", f"subtitles=filename='{filter_path(srt)}':original_size={WIDTH}x{HEIGHT}",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(burned),
        ]
    )
    card = dest / "card.mp4"
    font = filter_path(font_file())
    ffmpeg(
        [
            "-f", "lavfi", "-i", f"color=c=black:s={WIDTH}x{HEIGHT}:d={END_CARD_S}:r={FPS}",
            "-vf",
            (
                f"drawtext=fontfile='{font}':text='Made with AI':fontsize=64:"
                "fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2"
            ),
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            str(card),
        ]
    )
    silent = dest / "silent.mp4"
    _concat([burned, card], silent)
    film_s = cursor + END_CARD_S
    bed = find_bed()
    if bed is None or dry:
        bed = dest / "bed.wav"
        _tone(bed, film_s)
    mix = dest / "mix.wav"
    audio_args: list[str] = []
    for wav in wavs:
        audio_args += ["-i", str(wav)]
    audio_args += ["-i", str(bed)]
    ffmpeg(
        audio_args
        + [
            "-filter_complex", _audio_filter(slots, film_s),
            "-map", "[aout]",
            str(mix),
        ]
    )
    film = dest / "film.mp4"
    ffmpeg(
        [
            "-i", str(silent), "-i", str(mix),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-shortest",
            "-movflags", "+faststart",
            str(film),
        ]
    )
    family_log(
        {
            "stage": "family-assemble",
            "provider": "ffmpeg",
            "model": "dry" if dry else "zoompan",
            "parameters": {"shots": [shot["id"] for shot in shots], "dry": dry},
            "seed": REFERENCE_SEED,
            "latency": 0,
            "cost": 0,
            "status": "ok",
            "output_path": _rel(film),
        },
        dest,
    )
    _notify(
        on_status,
        status="ready",
        step="The film is ready.",
        frames=list(frames),
        film=film.name,
    )
    return film


def _sample():
    return build(
        {
            "name": "Eebbisaa",
            "who_om": "Eebbisaa koo, roobni ammallee rukkuta.",
            "who_en": "My Eebbisaa, the rain still taps this roof.",
            "object": "blue pen",
            "memory_om": "Qalama cuquliisaa keetiin barreessite.",
            "memory_en": "You wrote with a blue pen.",
            "last_om": "Har'a, ilma koo, ani hin boo'u.",
            "last_en": "Tonight, my son, I will not cry.",
        }
    )


def _self_check() -> None:
    from common import audio_seconds

    story = (ROOT / "storyboard.json").read_bytes()
    graded = ROOT / "outputs" / "film_9x16.mp4"
    graded_mtime = graded.stat().st_mtime if graded.is_file() else None
    runs = ROOT / "runs.jsonl"
    runs_size = runs.stat().st_size if runs.is_file() else 0
    with tempfile.TemporaryDirectory() as tmp:
        film = render(_sample(), Path(tmp) / "one", dry=True)
        assert film.is_file() and film.stat().st_size > 1000
        assert audio_seconds(film) > 20
        assert film.resolve() != graded.resolve()
    assert (ROOT / "storyboard.json").read_bytes() == story
    assert (graded.stat().st_mtime if graded.is_file() else None) == graded_mtime
    assert (runs.stat().st_size if runs.is_file() else 0) == runs_size
    print("self-check ok")


if __name__ == "__main__":
    if "--self-check" in sys.argv:
        _self_check()
    else:
        print("usage: python family/render.py --self-check", file=sys.stderr)
        sys.exit(2)
