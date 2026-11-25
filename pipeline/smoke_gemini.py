#!/usr/bin/env python3
"""One Gemini smoke pass: list models, one Flash text call, one TTS wav."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ROOT, audio_seconds, fail, output_path, read_key, with_retry
from validate import ensure_storyboard
from providers.gemini import (
    VOICE,
    flash_names,
    generate_text,
    list_models,
    pick_flash_lite,
    pick_newest,
    synthesize,
)

PROVIDER = "gemini"
TEXT_PROMPT = "In one word, what is 2+2?"
SENTENCE = (
    "akkam jirtu an sifan jedhama.software engineer ta'uudhaan system fi "
    "application gara garaa maamiltoota biyya alaa wajjin hojjechuu irrattan "
    "argama.Galatoomaa"
)


def main() -> int:
    ensure_storyboard()
    key = read_key("GEMINI_API_KEY")
    if not key:
        print("GEMINI_API_KEY is missing from .env", file=sys.stderr)
        return 1

    ok = True
    models: list[dict] = []

    def do_list():
        nonlocal models
        record = {
            "stage": "list",
            "provider": PROVIDER,
            "model": None,
            "parameters": {"page_size": 1000},
            "seed": None,
            "cost": 0,
        }
        try:
            models = list_models(key)
        except Exception as err:
            fail(err, record, key)
        names = flash_names(models)
        record["detail"] = "\n".join(names) if names else "(no model name contains tts or flash)"
        record["output_path"] = None
        return record

    if not with_retry(do_list):
        return 1

    flash = pick_newest(models, "flash")

    def do_text(model: str | None):
        def once():
            record = {
                "stage": "text",
                "provider": PROVIDER,
                "model": model,
                "parameters": {"contents": TEXT_PROMPT},
                "seed": None,
                "cost": 0,
            }
            try:
                if not model:
                    raise RuntimeError("no Flash model that supports generateContent")
                reply = generate_text(key, model, TEXT_PROMPT)
            except Exception as err:
                fail(err, record, key)
            record["detail"] = f"{model}: {reply}"
            record["output_path"] = None
            return record

        return once

    text_ok = with_retry(do_text(flash))
    if not text_ok and flash == "gemini-3.8-flash":
        lite = pick_flash_lite(models)
        if lite:
            print(f"gemini-3.8-flash failed; falling back to {lite}", file=sys.stderr)
            text_ok = with_retry(do_text(lite))
        else:
            print("gemini-3.8-flash failed and the list has no Flash-Lite text model", file=sys.stderr)
    ok = text_ok and ok

    tts = pick_newest(models, "tts")

    def do_tts():
        record = {
            "stage": "tts",
            "provider": PROVIDER,
            "model": tts,
            "parameters": {
                "text": SENTENCE,
                "voice": VOICE,
                "response_modalities": ["AUDIO"],
            },
            "seed": None,
            "cost": 0,
        }
        try:
            if not tts:
                raise RuntimeError("no TTS model that supports generateContent")
            wav = synthesize(key, tts, SENTENCE, VOICE)
            path = output_path(PROVIDER, tts, SENTENCE, "wav")
            path.write_bytes(wav)
            seconds = audio_seconds(path)
        except Exception as err:
            fail(err, record, key)
        record["output_path"] = path.relative_to(ROOT).as_posix()
        record["audio_seconds"] = seconds
        record["detail"] = f"{tts}: {record['output_path']} ({path.stat().st_size} bytes)"
        return record

    ok = with_retry(do_tts) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
