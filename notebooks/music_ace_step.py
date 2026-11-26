#!/usr/bin/env python3
"""Kaggle notebook script: three ACE-Step 1.5 instrumentals.

Install and call match the ACE-Step 1.5 README (uv sync, then the Python API
in docs/en/INFERENCE.md). Caption stays in `caption`. Tempo and key stay in
`bpm` and `keyscale`, which is what the model expects.

Kaggle's T4 is 16GB, so this uses the README's 8–16GB pair: DiT
`acestep-v15-turbo` and LM `acestep-5Hz-lm-0.6B` on the PyTorch backend,
with CPU offload. vLLM is the faster backend on a larger card.

Run on a GPU notebook from a copy of this repo:

    python notebooks/music_ace_step.py

Download the music/ folder into outputs/music/ and run `make music`.
`--plan` only prints the storyboard fields. It does not load the model.
"""

import os

os.environ["MPLBACKEND"] = "Agg"

import json
import subprocess
import sys
import time
from pathlib import Path

SEEDS = (301, 302, 303)
DIT = "acestep-v15-turbo"
LM = "acestep-5Hz-lm-0.6B"
REPO = "https://github.com/ACE-Step/ACE-Step-1.5.git"


def find_storyboard() -> Path:
    env = os.environ.get("STORYBOARD")
    names = [Path(env)] if env else []
    names += [
        Path("storyboard.json"),
        Path("schema/storyboard.json"),
        Path("/kaggle/working/storyboard.json"),
        Path("/kaggle/working/heritage-short/storyboard.json"),
        Path("/kaggle/working/schema/storyboard.json"),
        Path("/kaggle/working/heritage-short/schema/storyboard.json"),
    ]
    for path in names:
        if path.is_file() and path.stat().st_size > 0:
            return path
    raise SystemExit("storyboard.json not found. Set STORYBOARD= or upload the repo.")


def read_music(board: dict) -> dict:
    """Caption from the cues. bpm, key, and duration stay in their own fields."""
    music = board["music"]
    cues = music["cues"]
    caption = ". ".join(str(cue["caption"]).strip().rstrip(".") for cue in cues) + "."
    if len(caption) > 512:
        raise SystemExit(f"caption is {len(caption)} characters; ACE-Step allows 512")
    return {
        "caption": caption,
        "bpm": int(music["bpm"]),
        "keyscale": str(music["key"]),
        "duration": float(sum(int(cue["duration_s"]) for cue in cues)),
        "instrumental": bool(music["instrumental"]),
        "cue_ids": [cue["id"] for cue in cues],
    }


def output_dir() -> Path:
    if Path("/kaggle/working").is_dir():
        dest = Path("/kaggle/working/music")
    else:
        dest = Path("outputs/music")
    dest.mkdir(parents=True, exist_ok=True)
    return dest


def _env_with_uv() -> dict:
    env = os.environ.copy()
    home_bin = str(Path.home() / ".local" / "bin")
    env["PATH"] = home_bin + os.pathsep + env.get("PATH", "")
    return env


def install() -> Path:
    """README quick start: install uv, clone ACE-Step 1.5, uv sync."""
    root = Path("/kaggle/working/ACE-Step-1.5") if Path("/kaggle/working").is_dir() else Path("ACE-Step-1.5")
    if not (root / "pyproject.toml").is_file():
        subprocess.check_call(["git", "clone", "--depth", "1", REPO, str(root)])
    env = _env_with_uv()
    if subprocess.call(["uv", "--version"], env=env) != 0:
        subprocess.check_call(["bash", "-lc", "curl -LsSf https://astral.sh/uv/install.sh | sh"], env=env)
    subprocess.check_call(["uv", "sync"], cwd=root, env=env)
    return root


def _inside_uv() -> bool:
    try:
        import acestep  # noqa: F401
        return True
    except ImportError:
        return False


def ensure_runtime() -> Path | None:
    if _inside_uv():
        return Path(os.environ.get("ACE_STEP_ROOT", "ACE-Step-1.5"))
    root = install()
    env = _env_with_uv()
    env["ACE_STEP_ROOT"] = str(root.resolve())
    os.execvpe(
        "uv",
        ["uv", "run", "--directory", str(root), "python", str(Path(__file__).resolve()), *sys.argv[1:]],
        env,
    )
    return root


def _call_with(fn, preferred: dict):
    import inspect
    allowed = inspect.signature(fn).parameters
    return fn(**{key: value for key, value in preferred.items() if key in allowed})


def load_handlers(root: Path):
    from acestep.handler import AceStepHandler
    from acestep.llm_inference import LLMHandler

    dit = AceStepHandler()
    llm = LLMHandler()
    _call_with(
        dit.initialize_service,
        {
            "project_root": str(root),
            "config_path": DIT,
            "device": "cuda",
            "offload_to_cpu": True,
        },
    )
    _call_with(
        llm.initialize,
        {
            "checkpoint_dir": str(root / "checkpoints"),
            "lm_model_path": LM,
            "backend": "pt",
            "device": "cuda",
            "offload_to_cpu": True,
        },
    )
    return dit, llm


def write_wav(audio: dict, dest: Path) -> None:
    import soundfile as sf

    tensor = audio["tensor"].detach().cpu().float().numpy()
    channels = tensor.T if tensor.ndim == 2 else tensor
    sf.write(str(dest), channels, int(audio.get("sample_rate") or 48000))


def generate(root: Path, spec: dict, dest: Path) -> list[dict]:
    from acestep.inference import GenerationConfig, GenerationParams, generate_music

    dit, llm = load_handlers(root)
    rows = []
    for seed in SEEDS:
        params = GenerationParams(
            task_type="text2music",
            caption=spec["caption"],
            lyrics="[Instrumental]",
            instrumental=spec["instrumental"],
            bpm=spec["bpm"],
            keyscale=spec["keyscale"],
            duration=spec["duration"],
            seed=seed,
            inference_steps=8,
            shift=3.0,
            thinking=False,
            use_cot_metas=False,
            use_cot_caption=False,
        )
        config = GenerationConfig(
            batch_size=1,
            use_random_seed=False,
            seeds=[seed],
            audio_format="wav",
        )
        started = time.perf_counter()
        result = generate_music(dit, llm, params, config, save_dir=str(dest))
        latency = round(time.perf_counter() - started, 3)
        if not result.success or not result.audios:
            raise SystemExit(f"seed {seed} failed: {result.error or result.status_message}")
        path = dest / f"music_{seed}.wav"
        write_wav(result.audios[0], path)
        print(f"music_{seed}.wav: latency {latency:.3f}s")
        rows.append({"seed": seed, "file": path.name, "latency_s": latency})
    return rows


def print_plan() -> None:
    spec = read_music(json.loads(find_storyboard().read_text(encoding="utf-8")))
    print(json.dumps({"seeds": SEEDS, **spec, "caption_chars": len(spec["caption"])}, indent=2))


def main() -> int:
    if "--plan" in sys.argv:
        print_plan()
        return 0
    root = ensure_runtime()
    spec = read_music(json.loads(find_storyboard().read_text(encoding="utf-8")))
    dest = output_dir()
    clock = time.perf_counter()
    rows = generate(root, spec, dest)
    gpu_minutes = round((time.perf_counter() - clock) / 60, 3)
    payload = {"gpu_minutes": gpu_minutes, "tracks": rows}
    (dest / "latencies.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"GPU minutes: {gpu_minutes:.3f}")
    print(f"download {dest} into outputs/music/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
