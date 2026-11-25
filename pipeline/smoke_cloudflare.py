#!/usr/bin/env python3
"""One Workers AI image: FLUX.2 klein, or FLUX.1 schnell if klein is absent."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ROOT, fail, http_status, output_path, read_key, with_retry
from providers.cloudflare import HEIGHT, KLEIN, SCHNELL, WIDTH, generate, image_ext, model_missing
from validate import ensure_storyboard

PROVIDER = "cloudflare"


def shot_prompt(board: dict) -> tuple[str, int | None]:
    """style_block + character description + s02 image_prompt. The schema names it character, not character_block."""
    style = str(board.get("style_block") or "").strip()
    character = board.get("character") or {}
    who = str(board.get("character_block") or character.get("description") or "").strip()
    shot = next((item for item in board.get("shots") or [] if item.get("id") == "s02"), None)
    if shot is None:
        raise RuntimeError("storyboard has no shot s02")
    image = str(shot.get("image_prompt") or "").strip()
    if not style or not who or not image:
        raise RuntimeError("s02 prompt needs style_block, the character description, and image_prompt")
    seed = shot.get("seed")
    return f"{style}. {who}. {image}", seed if isinstance(seed, int) else None


def main() -> int:
    board = ensure_storyboard()
    account = read_key("CLOUDFLARE_ACCOUNT_ID")
    token = read_key("CLOUDFLARE_API_TOKEN")
    if not account or not token:
        print("CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN are required in .env", file=sys.stderr)
        return 1
    try:
        prompt, seed = shot_prompt(board)
    except RuntimeError as err:
        print(err, file=sys.stderr)
        return 1

    def do_image(model: str, *, sized: bool):
        held: dict[str, BaseException] = {}

        def once():
            record = {
                "stage": "image",
                "provider": PROVIDER,
                "model": model,
                "parameters": {"prompt": prompt, "width": WIDTH, "height": HEIGHT} if sized else {"prompt": prompt},
                "seed": seed if sized else None,
                "cost": 0,
            }
            try:
                image = generate(
                    account,
                    token,
                    model,
                    prompt,
                    width=WIDTH if sized else None,
                    height=HEIGHT if sized else None,
                    seed=seed if sized else None,
                )
                path = output_path(PROVIDER, model, prompt, image_ext(image))
                path.write_bytes(image)
            except Exception as err:
                held["error"] = err
                fail(err, record, token)
            record["output_path"] = path.relative_to(ROOT).as_posix()
            record["detail"] = f"{model}: {record['output_path']} ({path.stat().st_size} bytes)"
            return record

        return once, held

    klein, klein_err = do_image(KLEIN, sized=True)
    if with_retry(klein):
        return 0
    err = klein_err.get("error")
    if err is None or not model_missing(err):
        return 1
    print(f"{KLEIN} is not available (HTTP {http_status(err)}); trying {SCHNELL}", file=sys.stderr)
    schnell, _schnell_err = do_image(SCHNELL, sized=False)
    return 0 if with_retry(schnell) else 1


if __name__ == "__main__":
    sys.exit(main())
