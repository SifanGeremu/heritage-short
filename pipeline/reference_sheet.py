#!/usr/bin/env python3
"""Four candidate portraits of the mother. Seeds 201, 202, 203, 204."""

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ROOT, fail, read_key, unique_path, with_retry
from providers.cloudflare import HEIGHT, KLEIN, WIDTH, generate, image_ext
from validate import ensure_storyboard

PROVIDER = "cloudflare"
SEEDS = (201, 202, 203, 204)
OUT_DIR = ROOT / "outputs" / "reference"
GOLDEN = OUT_DIR / "golden.jpg"
SMALL = OUT_DIR / "golden_480.jpg"


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


def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def image_size(path: Path) -> tuple[int, int]:
    out = subprocess.check_output(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "csv=p=0", str(path),
        ],
        text=True,
    )
    width, height = out.strip().split(",")
    return int(width), int(height)


def sheet_ready(path: Path = SMALL) -> bool:
    if not path.is_file():
        return False
    width, height = image_size(path)
    return width < 512 and height < 512


def scale_under_512(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_suffix(".part.jpg")
    proc = subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(src),
            "-vf", "scale=480:480:force_original_aspect_ratio=decrease",
            str(partial),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        partial.unlink(missing_ok=True)
        raise RuntimeError((proc.stderr or "ffmpeg failed").strip()[-500:])
    partial.replace(dest)


def portrait_for(seed: int, out_dir: Path = OUT_DIR) -> Path | None:
    found = [
        path for path in out_dir.glob(f"*_{seed}_*.jpg")
        if path.name not in (GOLDEN.name, SMALL.name)
    ]
    if not found:
        return None
    return max(found, key=lambda path: path.stat().st_mtime)


def generate_seed(board: dict, seed: int) -> Path:
    account = read_key("CLOUDFLARE_ACCOUNT_ID")
    token = read_key("CLOUDFLARE_API_TOKEN")
    if not account or not token:
        raise RuntimeError("CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN are required in .env")
    prompt = mother_prompt(board)
    written: dict[str, Path] = {}

    def once(seed=seed):
        record = {
            "stage": "reference",
            "provider": PROVIDER,
            "model": KLEIN,
            "parameters": {
                "prompt": prompt,
                "width": WIDTH,
                "height": HEIGHT,
                "seed": seed,
                "reference_seed": seed,
            },
            "seed": seed,
            "cost": 0,
        }
        try:
            image = generate(account, token, KLEIN, prompt, width=WIDTH, height=HEIGHT, seed=seed)
            path = dest_for(prompt, seed, image_ext(image))
            path.write_bytes(image)
            written["path"] = path
        except Exception as err:
            fail(err, record, token)
        record["output_path"] = path.relative_to(ROOT).as_posix()
        record["detail"] = path.name
        return record

    if not with_retry(once):
        raise RuntimeError(f"reference seed {seed} failed")
    return written["path"]


def ensure_sheet(board: dict) -> int:
    """The face keyframes condition on. Skip when golden_480.jpg is already small enough.

    A clean tree with no portrait generates character.reference_seed once, then scales it.
    """
    if sheet_ready():
        print(f"reference cached {_rel(SMALL)}")
        return 0
    seed = board.get("character", {}).get("reference_seed")
    if isinstance(seed, bool) or not isinstance(seed, int):
        print("character.reference_seed must be an integer", file=sys.stderr)
        return 1
    src = portrait_for(seed)
    if src is None:
        try:
            src = generate_seed(board, seed)
        except (RuntimeError, OSError) as err:
            print(err, file=sys.stderr)
            return 1
    shutil.copyfile(src, GOLDEN)
    try:
        scale_under_512(GOLDEN, SMALL)
    except RuntimeError as err:
        print(err, file=sys.stderr)
        return 1
    width, height = image_size(SMALL)
    print(f"reference {_rel(SMALL)} {width}x{height} from seed {seed}")
    return 0


def main() -> int:
    board = ensure_storyboard()
    return ensure_sheet(board)


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
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        src = folder / "big.jpg"
        made = subprocess.run(
            [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-f", "lavfi", "-i", "color=c=0x224466:s=800x1200",
                "-frames:v", "1", str(src),
            ],
            capture_output=True, text=True,
        )
        assert made.returncode == 0, made.stderr
        dest = folder / "small.jpg"
        scale_under_512(src, dest)
        width, height = image_size(dest)
        assert width < 512 and height < 512
        assert sheet_ready(dest)
        assert sheet_ready(src) is False
    print("self-check ok")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-check":
        _self_check()
    else:
        sys.exit(main())
