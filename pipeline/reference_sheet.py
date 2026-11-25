#!/usr/bin/env python3
"""Four candidate portraits of the mother. Seeds 201, 202, 203, 204."""

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ROOT, fail, read_key, unique_path, with_retry
from providers.cloudflare import HEIGHT, KLEIN, WIDTH, generate, image_ext
from validate import ensure_storyboard

PROVIDER = "cloudflare"
SEEDS = (201, 202, 203, 204)
OUT_DIR = ROOT / "outputs" / "reference"


def mother_prompt(board: dict) -> str:
    """character description plus style_block. The schema field is character, not character_block."""
    style = str(board.get("style_block") or "").strip()
    character = board.get("character") or {}
    who = str(board.get("character_block") or character.get("description") or "").strip()
    if not style or not who:
        raise RuntimeError("portrait prompt needs style_block and the character description")
    return f"{who}. {style}"


def dest_for(prompt: str, seed: int, ext: str) -> Path:
    digest = hashlib.sha256(f"{KLEIN}\n{seed}\n{prompt}".encode()).hexdigest()[:8]
    safe = KLEIN.replace("/", "_")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    return unique_path(OUT_DIR / f"{PROVIDER}_{safe}_{seed}_{digest}.{ext}")


def main() -> int:
    board = ensure_storyboard()
    account = read_key("CLOUDFLARE_ACCOUNT_ID")
    token = read_key("CLOUDFLARE_API_TOKEN")
    if not account or not token:
        print("CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN are required in .env", file=sys.stderr)
        return 1
    try:
        prompt = mother_prompt(board)
    except RuntimeError as err:
        print(err, file=sys.stderr)
        return 1

    for seed in SEEDS:
        def once(seed=seed):
            record = {
                "stage": "reference",
                "provider": PROVIDER,
                "model": KLEIN,
                "parameters": {"prompt": prompt, "width": WIDTH, "height": HEIGHT, "seed": seed},
                "seed": seed,
                "cost": 0,
            }
            try:
                image = generate(account, token, KLEIN, prompt, width=WIDTH, height=HEIGHT, seed=seed)
                path = dest_for(prompt, seed, image_ext(image))
                path.write_bytes(image)
            except Exception as err:
                fail(err, record, token)
            record["output_path"] = path.relative_to(ROOT).as_posix()
            record["detail"] = path.name
            return record

        if not with_retry(once):
            return 1
    return 0


def _self_check() -> None:
    text = mother_prompt(
        {
            "style_block": "oil paint look, centered, no text anywhere",
            "character": {"description": "elderly Oromo woman in her late sixties, silver hair"},
        }
    )
    assert text.startswith("elderly Oromo woman")
    assert text.endswith("no text anywhere")
    assert SEEDS == (201, 202, 203, 204)
    print("self-check ok")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-check":
        _self_check()
    else:
        sys.exit(main())
