#!/usr/bin/env python3
"""One Addis AI smoke pass: Afaan Oromo speech with voice om-bikila."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ROOT, audio_seconds, fail, output_path, read_key, with_retry
from validate import ensure_storyboard
from providers.addis import LANGUAGE, VOICE, cost_etb, synthesize

PROVIDER = "addis"
SENTENCE = (
    "akkam jirtu an sifan jedhama.software engineer ta'uudhaan system fi "
    "application gara garaa maamiltoota biyya alaa wajjin hojjechuu irrattan "
    "argama.Galatoomaa"
)


def main() -> int:
    ensure_storyboard()
    key = read_key("ADDIS-AI-API-KEY")
    if not key:
        print("ADDIS-AI-API-KEY is missing from .env", file=sys.stderr)
        return 1

    def do_tts():
        record = {
            "stage": "tts",
            "provider": PROVIDER,
            "model": VOICE,
            "parameters": {"text": SENTENCE, "voice": VOICE, "language": LANGUAGE},
            "seed": None,
            "cost": 0,
        }
        try:
            audio = synthesize(key, SENTENCE)
            path = output_path(PROVIDER, VOICE, SENTENCE, "wav")
            path.write_bytes(audio)
            seconds = audio_seconds(path)
        except Exception as err:
            fail(err, record, key)
        record["output_path"] = path.relative_to(ROOT).as_posix()
        record["audio_seconds"] = seconds
        record["cost"] = cost_etb(seconds)
        record["detail"] = f"{VOICE}: {record['output_path']} ({path.stat().st_size} bytes)"
        return record

    return 0 if with_retry(do_tts) else 1


if __name__ == "__main__":
    sys.exit(main())
