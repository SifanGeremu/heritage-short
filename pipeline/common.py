"""Shared smoke helpers. No provider calls."""

import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
RUNS = ROOT / "runs.jsonl"
SMOKE_DIR = ROOT / "outputs" / "smoke"

ATTEMPTS = 3
RETRY_STATUS = (429, 503)

# ponytail: 3 tries, sleeps of 1s then 2s, only for 429/503. Ignores Retry-After.
# Upgrade path: honor that header when the service sends one.

_LOG_FIELDS = (
    "timestamp",
    "stage",
    "provider",
    "model",
    "parameters",
    "seed",
    "latency",
    "cost",
    "status",
    "output_path",
    "audio_seconds",
    "error",
)


def read_key(name: str) -> str:
    """Return one value from .env. Never prints it."""
    if not ENV_PATH.is_file():
        return ""
    for raw in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() != name:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        return value.strip()
    return ""


def redact(text: str, key: str) -> str:
    if key:
        text = text.replace(key, "[redacted]")
    return re.sub(r"(key=)[^&\s\"']+", r"\1[redacted]", text)


def log_run(record: dict) -> None:
    line = {field: record[field] for field in _LOG_FIELDS if field in record}
    with RUNS.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(line, ensure_ascii=False) + "\n")


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    n = 2
    while True:
        candidate = path.with_name(f"{path.stem}-{n}{path.suffix}")
        if not candidate.exists():
            return candidate
        n += 1


def output_path(provider: str, model_or_voice: str, text: str, ext: str) -> Path:
    """outputs/smoke/{provider}_{model_or_voice}_{hash8}.{ext}, never an existing file."""
    digest = hashlib.sha256(text.encode()).hexdigest()[:8]
    safe = str(model_or_voice).replace("/", "_")
    ext = ext.lstrip(".")
    SMOKE_DIR.mkdir(parents=True, exist_ok=True)
    return unique_path(SMOKE_DIR / f"{provider}_{safe}_{digest}.{ext}")


def audio_seconds(path) -> float:
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(path),
        ],
        text=True,
    )
    return round(float(out.strip()), 3)


def _daily_limit(text: str) -> bool:
    """A spent daily allowance is not a transient 429. Do not retry it."""
    low = text.lower()
    return "per day" in low or "daily" in low or "quota" in low


def http_status(err: BaseException) -> int | None:
    status = getattr(err, "status", None)
    if isinstance(status, int) and 100 <= status <= 599:
        return status
    code = getattr(err, "code", None)
    if isinstance(code, int) and 100 <= code <= 599:
        return code
    return None


class CallFailed(Exception):
    def __init__(self, status: int | None, message: str, record: dict):
        super().__init__(message)
        self.status = status
        self.record = record


def fail(err: BaseException, record: dict, key: str = "") -> None:
    raise CallFailed(http_status(err), redact(str(err), key)[:500], record) from None


def with_retry(fn, *, sleep=time.sleep, log=log_run) -> bool:
    """Call fn up to 3 times. Each attempt is one runs.jsonl line. 429/503 back off."""
    for attempt in range(1, ATTEMPTS + 1):
        started = time.perf_counter()
        try:
            record = fn()
        except Exception as err:
            latency = round(time.perf_counter() - started, 3)
            record = dict(getattr(err, "record", {}) or {})
            detail = record.pop("detail", None)
            params = dict(record.get("parameters") or {})
            params["attempt"] = attempt
            record.update(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "parameters": params,
                    "seed": record.get("seed"),
                    "latency": latency,
                    "cost": record.get("cost", 0),
                    "status": "error",
                    "output_path": None,
                    "error": redact(str(err), "")[:500],
                }
            )
            record.pop("audio_seconds", None)
            log(record)
            status = http_status(err)
            daily = _daily_limit(str(record.get("error") or ""))
            if daily or status not in RETRY_STATUS or attempt == ATTEMPTS:
                print(f"{record.get('stage', 'call')} failed: {record['error']}", file=sys.stderr)
                return False
            delay = 2 ** (attempt - 1)
            print(
                f"{record.get('stage')} attempt {attempt} got HTTP {status}; retrying in {delay}s",
                file=sys.stderr,
            )
            sleep(delay)
            continue
        detail = record.pop("detail", None)
        params = dict(record.get("parameters") or {})
        params["attempt"] = attempt
        record.update(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "parameters": params,
                "seed": record.get("seed"),
                "latency": round(time.perf_counter() - started, 3),
                "cost": record.get("cost", 0),
                "status": "ok",
                "output_path": record.get("output_path"),
            }
        )
        log(record)
        if detail:
            print(detail)
        return True
    return False


def _self_check() -> None:
    import tempfile

    from providers.gemini import pick_flash_lite, pick_newest

    models = [
        {"name": "models/gemini-2.5-flash", "supportedActions": ["generateContent"]},
        {"name": "models/gemini-3.8-flash", "supportedActions": ["generateContent"]},
        {"name": "models/gemini-3.5-flash-lite", "supportedActions": ["generateContent"]},
        {"name": "models/gemini-3.8-flash-lite-tts", "supportedActions": ["generateContent"]},
        {"name": "models/gemini-3.8-flash-tts", "supportedActions": ["generateContent"]},
        {"name": "models/gemini-3.8-flash-image", "supportedActions": ["generateContent"]},
    ]
    assert pick_newest(models, "tts") == "gemini-3.8-flash-tts"
    assert pick_newest(models, "flash") == "gemini-3.8-flash"
    assert pick_flash_lite(models) == "gemini-3.5-flash-lite"

    secret = "super-secret-key"
    assert secret not in redact(f"url?key={secret} boom {secret}", secret)

    with tempfile.TemporaryDirectory() as tmp:
        first = Path(tmp) / "addis_om-bikila_abcd1234.wav"
        first.write_bytes(b"x")
        assert unique_path(first) == Path(tmp) / "addis_om-bikila_abcd1234-2.wav"

    logs: list[dict] = []
    sleeps: list[int] = []

    def boom():
        raise CallFailed(503, "busy", {"stage": "text", "provider": "gemini", "model": "m", "parameters": {}})

    assert with_retry(boom, sleep=sleeps.append, log=logs.append) is False
    assert sleeps == [1, 2]
    assert [row["parameters"]["attempt"] for row in logs] == [1, 2, 3]
    assert all(row["status"] == "error" for row in logs)

    logs.clear()
    sleeps.clear()

    def bad():
        raise CallFailed(400, "bad", {"stage": "text", "provider": "addis", "model": "om-bikila", "parameters": {}})

    assert with_retry(bad, sleep=sleeps.append, log=logs.append) is False
    assert sleeps == [] and len(logs) == 1 and logs[0]["provider"] == "addis"
    print("self-check ok")


if __name__ == "__main__":
    _self_check()
