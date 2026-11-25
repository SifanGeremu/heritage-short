#!/usr/bin/env python3
"""One FLUX.2 klein 9B keyframe per shot. Cached by prompt, seed, and reference.

Character shots send outputs/reference/golden_480.jpg as input_image_0.
A daily quota stop leaves finished shots on disk; the next run continues.
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ROOT, _daily_limit, fail, read_key, with_retry
from providers.cloudflare import HEIGHT, KLEIN, WIDTH, generate, image_ext
from validate import ensure_storyboard

PROVIDER = "cloudflare"
OUT_DIR = ROOT / "outputs" / "keyframes"
CACHE_PATH = OUT_DIR / "cache.json"
REFERENCE = ROOT / "outputs" / "reference" / "golden_480.jpg"


def mother_text(board: dict) -> str:
    """The schema field is character.description. character_block is accepted if present."""
    character = board.get("character") or {}
    who = str(board.get("character_block") or character.get("description") or "").strip()
    if not who:
        raise RuntimeError("storyboard needs a character description")
    return who


def shot_prompt(style: str, who: str, shot: dict, referenced: bool) -> str:
    image = str(shot.get("image_prompt") or "").strip()
    if not image:
        raise RuntimeError(f"{shot.get('id')}: image_prompt is empty")
    text = f"{style}. {who}. {image}"
    if referenced:
        text += ". The woman from image 0"
    return text


def cache_key(prompt: str, seed: int, reference: bytes | None) -> str:
    ref = hashlib.sha256(reference).hexdigest() if reference else ""
    payload = json.dumps(
        {"prompt": prompt, "seed": seed, "reference": ref},
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
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2) + "\n", encoding="utf-8")


def _size(path: Path) -> tuple[int, int]:
    out = subprocess.check_output(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "csv=p=0",
            str(path),
        ],
        text=True,
    )
    width, height = out.strip().split(",")
    return int(width), int(height)


def _report(done: list[str], pending: list[str]) -> None:
    print("daily limit reached")
    print("done:", " ".join(done) if done else "(none)")
    print("remaining:", " ".join(pending) if pending else "(none)")


def main() -> int:
    board = ensure_storyboard()
    account = read_key("CLOUDFLARE_ACCOUNT_ID")
    token = read_key("CLOUDFLARE_API_TOKEN")
    if not account or not token:
        print("CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN are required in .env", file=sys.stderr)
        return 1
    style = str(board.get("style_block") or "").strip()
    try:
        who = mother_text(board)
    except RuntimeError as err:
        print(err, file=sys.stderr)
        return 1
    if not style:
        print("storyboard style_block is empty", file=sys.stderr)
        return 1
    shots = board.get("shots") or []
    needs_reference = any(shot.get("has_character") for shot in shots)
    reference = REFERENCE.read_bytes() if needs_reference and REFERENCE.is_file() else None
    if needs_reference and reference is None:
        print(f"missing reference image: {_rel(REFERENCE)}", file=sys.stderr)
        return 1
    if reference is not None:
        width, height = _size(REFERENCE)
        if width >= 512 or height >= 512:
            print(
                f"{_rel(REFERENCE)} is {width}x{height}; klein reference images must be smaller than 512x512",
                file=sys.stderr,
            )
            return 1

    cache = load_cache()
    done: list[str] = []
    pending = [str(shot.get("id")) for shot in shots]
    for shot in shots:
        sid = str(shot.get("id"))
        seed = shot.get("seed")
        if isinstance(seed, bool) or not isinstance(seed, int):
            print(f"{sid}: seed must be an integer", file=sys.stderr)
            return 1
        referenced = bool(shot.get("has_character"))
        try:
            prompt = shot_prompt(style, who, shot, referenced)
        except RuntimeError as err:
            print(err, file=sys.stderr)
            return 1
        digest = cache_key(prompt, seed, reference if referenced else None)
        cached = cache.get(digest)
        cached_path = ROOT / cached if isinstance(cached, str) else None
        if cached_path is not None and cached_path.is_file():
            print(f"{sid}: cached {cached_path.name}")
            done.append(sid)
            pending.remove(sid)
            continue
        dest = OUT_DIR / f"{sid}_{digest[:8]}.jpg"
        if dest.is_file():
            cache[digest] = _rel(dest)
            save_cache(cache)
            print(f"{sid}: cached {dest.name}")
            done.append(sid)
            pending.remove(sid)
            continue

        held: dict[str, BaseException] = {}

        def once(sid=sid, seed=seed, prompt=prompt, referenced=referenced, digest=digest, dest=dest):
            record = {
                "stage": "keyframes",
                "provider": PROVIDER,
                "model": KLEIN,
                "parameters": {
                    "prompt": prompt,
                    "width": WIDTH,
                    "height": HEIGHT,
                    "seed": seed,
                    "reference": _rel(REFERENCE) if referenced else None,
                },
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
                    images={"input_image_0": reference} if referenced else None,
                )
                ext = image_ext(image)
                path = dest if ext == "jpg" else dest.with_suffix("." + ext)
                path.parent.mkdir(parents=True, exist_ok=True)
                if path.exists():
                    raise RuntimeError(f"{_rel(path)} already exists")
                path.write_bytes(image)
            except Exception as err:
                held["error"] = err
                fail(err, record, token)
            record["output_path"] = _rel(path)
            record["detail"] = f"{sid}: {path.name}"
            cache[digest] = record["output_path"]
            save_cache(cache)
            return record

        if not with_retry(once):
            err = held.get("error")
            if err is not None and _daily_limit(str(err)):
                _report(done, pending)
                return 0
            return 1
        done.append(sid)
        pending.remove(sid)
    print(f"shots {len(done)}/{len(shots)}")
    return 0


def _self_check() -> None:
    style = "oil paint look, centered, no text anywhere"
    who = "elderly Oromo woman in her late sixties, silver hair"
    plain = {"id": "s01", "image_prompt": "an empty stool in a dim room", "has_character": False}
    woman = {"id": "s02", "image_prompt": "the mother seated beside a guitar", "has_character": True}
    bare = shot_prompt(style, who, plain, False)
    used = shot_prompt(style, who, woman, True)
    assert "image 0" not in bare and used.endswith("The woman from image 0")
    ref = b"golden-bytes"
    assert cache_key(used, 102, ref) == cache_key(used, 102, ref)
    assert cache_key(used, 102, ref) != cache_key(used, 103, ref)
    assert cache_key(used, 102, ref) != cache_key(bare, 102, ref)
    assert cache_key(used, 102, ref) != cache_key(used, 102, b"other")
    assert cache_key(bare, 101, None) != cache_key(bare, 101, ref)
    assert _daily_limit("HTTP 429: daily limit reached")
    assert not _daily_limit("HTTP 429: rate limited")
    print("self-check ok")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-check":
        _self_check()
    else:
        sys.exit(main())
