#!/usr/bin/env python3
"""Speak four storyboard fragments on Gemini TTS and on Addis, then count tokens.

The fragments are slices of the current board: three Afaan Oromo lines that
listeners already failed, and one Amharic line that had never been spoken.
Addis Scribe writes the transcript. The word-error count is that transcript
against the source, not a person's ear. Scribe is an Addis model, so it is
the same company judging both speakers. make film does not call this.
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ROOT, audio_seconds, fail, log_run, read_key, redact, with_retry
from providers.addis import cost_etb, synthesize as addis_synthesize
from providers.gemini import VOICE as GEMINI_VOICE
from providers.gemini import synthesize as gemini_synthesize
from validate import ensure_storyboard

OUT = ROOT / "outputs" / "benchmark"
GEMINI_MODEL = "gemini-3.8-flash-tts"
ADDIS_OM = "om-ayyaantuu"
ADDIS_AM = "am-meron"
SCRIBE_MODEL = "scribe-turbo"

# Exact slices of storyboard.json. The script refuses to run if a slice drifts.
PROBES = (
    {
        "id": "om-guitar",
        "shot": "s02",
        "language": "om",
        "text": "Eebbisaa, gitaarri kee ammallee keenyanitti hirkatee jira.",
    },
    {
        "id": "om-qubee",
        "shot": "s03",
        "language": "om",
        "text": "Ijoollee ollaa qubee—afaan keenyaan barreessuu—barsiistee, maqaa isaanii akka baratan goote.",
    },
    {
        "id": "om-ink",
        "shot": "s05",
        "language": "om",
        "text": "Qalamni cuquliisni kee ammallee dabtara kana guutee jira.",
    },
    {
        "id": "am-guitar",
        "shot": "s02",
        "language": "am",
        "text": "ኤቢሳ፣ ጊታርህ አሁንም ግድግዳው ላይ ተደግፎ አለ።",
    },
)


def tokens(text: str) -> list[str]:
    text = text.replace("—", " ").replace("–", " ").replace("'", " ").replace("’", " ")
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return text.split()


def word_errors(reference: str, heard: str) -> int:
    ref = tokens(reference)
    hyp = tokens(heard)
    prev = list(range(len(hyp) + 1))
    for i, left in enumerate(ref, 1):
        cur = [i]
        for j, right in enumerate(hyp, 1):
            cur.append(
                min(
                    prev[j] + 1,
                    cur[j - 1] + 1,
                    prev[j - 1] + (left != right),
                )
            )
        prev = cur
    return prev[-1]


def transcript_of(result: dict) -> str:
    for key in ("text", "transcription", "transcript"):
        value = result.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict):
            for inner in ("clean", "text", "raw"):
                heard = value.get(inner)
                if isinstance(heard, str) and heard.strip():
                    return heard.strip()
    return ""


def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def check_slices(board: dict) -> None:
    by_id = {shot["id"]: shot for shot in board["shots"]}
    for probe in PROBES:
        full = str(by_id[probe["shot"]]["narration"][probe["language"]])
        if probe["text"] not in full:
            raise SystemExit(f"{probe['id']} is not a slice of {probe['shot']} {probe['language']}")


def addis_voice(language: str) -> str:
    if language == "om":
        return ADDIS_OM
    if language == "am":
        return ADDIS_AM
    raise SystemExit(f"no Addis voice chosen for {language}")


def scribe(key: str, path: Path, language: str) -> dict:
    from addisai import AddisAI

    client = AddisAI(api_key=key, max_retries=0)
    # A path string is not audio. The SDK uploads bytes, or a file object, as wav.
    return client.scribe.transcribe(audio=path.read_bytes(), language=language, backend="turbo")


def log_scribe(probe: dict, provider: str, path: Path, heard: str, started_cost: float) -> None:
    errors = word_errors(probe["text"], heard) if heard else None
    count = len(tokens(probe["text"]))
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stage": "benchmark-scribe",
        "provider": "addis",
        "model": SCRIBE_MODEL,
        "parameters": {
            "probe": probe["id"],
            "shot": probe["shot"],
            "language": probe["language"],
            "source_provider": provider,
            "text": probe["text"],
            "transcript": heard,
            "word_errors": errors,
            "source_tokens": count,
        },
        "seed": None,
        "cost": started_cost,
        "status": "ok" if heard else "error",
        "output_path": _rel(path),
        "audio_seconds": audio_seconds(path),
    }
    if not heard:
        record["error"] = "scribe returned no transcript"
    log_run(record)


def main() -> int:
    board = ensure_storyboard()
    check_slices(board)
    gemini_key = read_key("GEMINI_API_KEY")
    addis_key = read_key("ADDIS-AI-API-KEY")
    if not gemini_key or not addis_key:
        print("GEMINI_API_KEY and ADDIS-AI-API-KEY are both required", file=sys.stderr)
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for probe in PROBES:
        for provider in ("gemini", "addis"):
            dest = OUT / f"{probe['id']}_{provider}.wav"
            if dest.is_file() and dest.stat().st_size > 44:
                print(f"{probe['id']} {provider} wav exists, not resynthesized")
                spoken = True
            elif provider == "gemini":
                voice = GEMINI_VOICE
                model = GEMINI_MODEL

                def once(probe=probe, dest=dest, voice=voice, model=model):
                    record = {
                        "stage": "benchmark-tts",
                        "provider": "gemini",
                        "model": model,
                        "parameters": {
                            "probe": probe["id"],
                            "shot": probe["shot"],
                            "language": probe["language"],
                            "text": probe["text"],
                            "voice": voice,
                            "language_code_sent": None,
                        },
                        "seed": None,
                        "cost": 0,
                    }
                    try:
                        wav = gemini_synthesize(gemini_key, model, probe["text"], voice)
                        dest.write_bytes(wav)
                        seconds = audio_seconds(dest)
                    except Exception as err:
                        fail(err, record, gemini_key)
                    record["output_path"] = _rel(dest)
                    record["audio_seconds"] = seconds
                    record["detail"] = f"{probe['id']} gemini {seconds:.3f}s"
                    return record

                spoken = with_retry(once)
            else:
                voice = addis_voice(probe["language"])

                def once(probe=probe, dest=dest, voice=voice):
                    record = {
                        "stage": "benchmark-tts",
                        "provider": "addis",
                        "model": voice,
                        "parameters": {
                            "probe": probe["id"],
                            "shot": probe["shot"],
                            "language": probe["language"],
                            "text": probe["text"],
                            "voice": voice,
                            "language_code_sent": probe["language"],
                        },
                        "seed": None,
                        "cost": 0,
                    }
                    try:
                        wav = addis_synthesize(addis_key, probe["text"], voice, probe["language"])
                        dest.write_bytes(wav)
                        seconds = audio_seconds(dest)
                    except Exception as err:
                        fail(err, record, addis_key)
                    record["output_path"] = _rel(dest)
                    record["audio_seconds"] = seconds
                    record["cost"] = cost_etb(seconds)
                    record["detail"] = f"{probe['id']} addis {voice} {seconds:.3f}s"
                    return record

                spoken = with_retry(once)
            heard = ""
            errors = None
            if spoken and dest.is_file():
                try:
                    heard = transcript_of(scribe(addis_key, dest, probe["language"]))
                except Exception as err:
                    log_run(
                        {
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "stage": "benchmark-scribe",
                            "provider": "addis",
                            "model": SCRIBE_MODEL,
                            "parameters": {
                                "probe": probe["id"],
                                "source_provider": provider,
                                "text": probe["text"],
                                "language": probe["language"],
                            },
                            "seed": None,
                            "latency": None,
                            "cost": 0,
                            "status": "error",
                            "output_path": _rel(dest),
                            "error": redact(str(err), addis_key)[:500],
                        }
                    )
                    print(f"{probe['id']} {provider} scribe failed: {err}", file=sys.stderr)
                else:
                    log_scribe(probe, provider, dest, heard, 0)
                    if heard:
                        errors = word_errors(probe["text"], heard)
                        print(f"{probe['id']} {provider} errors {errors} :: {heard}")
            rows.append(
                {
                    "probe": probe["id"],
                    "provider": provider,
                    "language": probe["language"],
                    "shot": probe["shot"],
                    "text": probe["text"],
                    "spoken": bool(spoken and dest.is_file()),
                    "transcript": heard,
                    "word_errors": errors,
                    "source_tokens": len(tokens(probe["text"])),
                }
            )
    summary = OUT / "summary.json"
    summary.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(_rel(summary))
    return 0 if any(row["spoken"] for row in rows) else 1


def _self_check() -> None:
    assert word_errors("gitaarri kee", "gitaarri kee") == 0
    assert word_errors("gitaarri kee", "gitaari kee") == 1
    assert word_errors("a b", "") == 2
    assert tokens("Qubee—afaan") == ["qubee", "afaan"]
    print("self-check ok")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-check":
        _self_check()
    else:
        sys.exit(main())
