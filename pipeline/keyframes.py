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
from providers.gemini import IMAGE_MODEL, generate_image, image_payload
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


def reference_seed_of(board: dict) -> int:
    seed = (board.get("character") or {}).get("reference_seed")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise RuntimeError("character.reference_seed must be an integer")
    return seed


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
    try:
        ref_seed = reference_seed_of(board)
    except RuntimeError as err:
        print(err, file=sys.stderr)
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

    gemini_key = read_key("GEMINI_API_KEY")
    cache = load_cache()
    done: list[str] = []
    pending = [str(shot.get("id")) for shot in shots]
    # ponytail: Cloudflare first, then Gemini image, then Pollinations when both free quotas are closed.
    image_via = "cloudflare"
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

        if image_via == "pollinations":
            if not _pollinations_shot(sid, seed, prompt, digest, dest, cache):
                _report(done, pending)
                return 1
            done.append(sid)
            pending.remove(sid)
            continue
        if image_via == "gemini":
            if not _gemini_shot(
                gemini_key, sid, seed, prompt, referenced, digest, dest,
                reference if referenced else None, cache,
            ):
                print(f"{sid}: Gemini image quota closed, using Pollinations flux", file=sys.stderr)
                image_via = "pollinations"
                if not _pollinations_shot(sid, seed, prompt, digest, dest, cache):
                    _report(done, pending)
                    return 1
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
                    "reference_seed": ref_seed if referenced else None,
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
            if err is None or not _daily_limit(str(err)):
                return 1
            # Cloudflare's free day is spent. Gemini Flash Image is the same key's fallback.
            print(f"{sid}: Cloudflare daily limit, using {IMAGE_MODEL}", file=sys.stderr)
            image_via = "gemini"
            if not _gemini_shot(
                gemini_key, sid, seed, prompt, referenced, digest, dest,
                reference if referenced else None, cache,
            ):
                print(f"{sid}: Gemini image quota closed, using Pollinations flux", file=sys.stderr)
                image_via = "pollinations"
                if not _pollinations_shot(sid, seed, prompt, digest, dest, cache):
                    _report(done, pending)
                    return 1
        done.append(sid)
        pending.remove(sid)
    print(f"shots {len(done)}/{len(shots)}")
    return 0


def _for_pollinations(prompt: str) -> str:
    """The shot text has to lead. A mother description first makes the boy disappear."""
    body = prompt.replace(". The woman from image 0", "")
    try:
        style, who, image = body.split(". ", 2)
    except ValueError:
        return prompt
    return (
        f"{image}. Show every person the shot names, the mother and the child together when both are named. "
        f"{style}. If the mother is in the shot she is: {who}. No watermark and no readable text."
    )


def _pollinations_shot(sid: str, seed: int, prompt: str, digest: str, dest: Path, cache: dict) -> bool:
    import urllib.error
    import urllib.parse
    import urllib.request

    spoken = _for_pollinations(prompt)
    query = urllib.parse.urlencode(
        {"width": 768, "height": 1344, "seed": seed, "nologo": "true", "model": "flux"}
    )
    url = "https://image.pollinations.ai/prompt/" + urllib.parse.quote(spoken) + "?" + query

    def once():
        record = {
            "stage": "keyframes",
            "provider": "pollinations",
            "model": "flux",
            "parameters": {"prompt": spoken, "width": 768, "height": 1344, "seed": seed},
            "seed": seed,
            "cost": 0,
        }
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "heritage-short"})
            try:
                with urllib.request.urlopen(req, timeout=180) as resp:
                    image = resp.read()
            except urllib.error.HTTPError as err:
                if err.code >= 500:
                    wrapped = RuntimeError(f"HTTP {err.code}: pollinations")
                    wrapped.code = 503
                    raise wrapped from None
                raise
            if not image.startswith(b"\xff\xd8\xff"):
                raise RuntimeError("pollinations did not return a jpeg")
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                raise RuntimeError(f"{_rel(dest)} already exists")
            dest.write_bytes(image)
        except Exception as err:
            fail(err, record, "")
        record["output_path"] = _rel(dest)
        record["detail"] = f"{sid}: {dest.name}"
        cache[digest] = record["output_path"]
        save_cache(cache)
        return record

    if with_retry(once):
        print(f"{sid}: pollinations flux")
        return True
    return False


def _gemini_shot(
    key: str,
    sid: str,
    seed: int,
    prompt: str,
    referenced: bool,
    digest: str,
    dest: Path,
    reference: bytes | None,
    cache: dict,
) -> bool:
    if not key:
        print("GEMINI_API_KEY is missing from .env", file=sys.stderr)
        return False
    held: dict[str, BaseException] = {}

    def once():
        record = {
            "stage": "keyframes",
            "provider": "gemini",
            "model": IMAGE_MODEL,
            "parameters": {
                "prompt": prompt,
                "aspect": "9:16",
                "seed": seed,
                "reference": _rel(REFERENCE) if referenced else None,
            },
            "seed": seed,
            "cost": 0,
        }
        try:
            image = generate_image(key, IMAGE_MODEL, prompt, reference)
            ext = image_ext(image)
            path = dest if ext == "jpg" else dest.with_suffix("." + ext)
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists():
                raise RuntimeError(f"{_rel(path)} already exists")
            path.write_bytes(image)
        except Exception as err:
            held["error"] = err
            fail(err, record, key)
        record["output_path"] = _rel(path)
        record["detail"] = f"{sid}: {path.name}"
        cache[digest] = record["output_path"]
        save_cache(cache)
        return record

    if with_retry(once):
        print(f"{sid}: {IMAGE_MODEL}")
        return True
    err = held.get("error")
    print(f"{sid}: {err}", file=sys.stderr)
    return False


def _self_check() -> None:
    style = "oil paint look, centered, no text anywhere"
    who = "elderly Oromo woman in her late sixties, silver hair"
    plain = {"id": "s01", "image_prompt": "an empty stool in a dim room", "has_character": False}
    woman = {"id": "s02", "image_prompt": "the mother seated beside a guitar", "has_character": True}
    bare = shot_prompt(style, who, plain, False)
    used = shot_prompt(style, who, woman, True)
    assert "image 0" not in bare and used.endswith("The woman from image 0")
    led = _for_pollinations(used)
    assert led.startswith("the mother seated beside a guitar")
    assert "image 0" not in led
    ref = b"golden-bytes"
    assert cache_key(used, 102, ref) == cache_key(used, 102, ref)
    assert cache_key(used, 102, ref) != cache_key(used, 103, ref)
    assert cache_key(used, 102, ref) != cache_key(bare, 102, ref)
    assert cache_key(used, 102, ref) != cache_key(used, 102, b"other")
    assert cache_key(bare, 101, None) != cache_key(bare, 101, ref)
    payload = image_payload("the mother and a painted child", b"jpeg-bytes")
    assert payload["generationConfig"]["responseModalities"] == ["IMAGE"]
    assert payload["generationConfig"]["imageConfig"]["aspectRatio"] == "9:16"
    assert payload["contents"][0]["parts"][0]["inlineData"]["mimeType"] == "image/jpeg"
    assert _daily_limit("HTTP 429: daily limit reached")
    assert not _daily_limit("HTTP 429: rate limited")
    assert reference_seed_of({"character": {"reference_seed": 201}}) == 201
    print("self-check ok")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-check":
        _self_check()
    else:
        sys.exit(main())
