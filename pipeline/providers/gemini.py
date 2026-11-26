"""Gemini API calls only. No logging and no output filenames."""

import base64
import io
import json
import re
import urllib.error
import urllib.request
import wave

API = "https://generativelanguage.googleapis.com/v1beta"
VOICE = "Kore"  # prebuilt voice, "Firm", used in the speech-generation samples

# ponytail: "newest" is the highest number tuple in the model id (a date suffix
# counts). lite/preview lose ties. Upgrade path: sort on the API version field
# once it is a real release date rather than a second copy of the name.


class HttpError(RuntimeError):
    def __init__(self, code: int, detail: str):
        self.code = code
        super().__init__(f"HTTP {code}: {detail}")


def redact(text: str, key: str) -> str:
    if key:
        text = text.replace(key, "[redacted]")
    return re.sub(r"(key=)[^&\s\"']+", r"\1[redacted]", text)


def _request(url: str, key: str, payload: dict | None = None, timeout: int = 120) -> dict:
    body = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=body,
        method="POST" if payload is not None else "GET",
    )
    req.add_header("x-goog-api-key", key)
    if payload is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as err:
        detail = redact(err.read().decode("utf-8", "replace"), key)[:500]
        raise HttpError(err.code, detail) from None
    except (urllib.error.URLError, TimeoutError, OSError) as err:
        reason = getattr(err, "reason", err)
        raise RuntimeError(redact(str(reason), key)) from None


def list_models(key: str) -> list[dict]:
    models: list[dict] = []
    page = ""
    for _ in range(20):
        url = f"{API}/models?pageSize=1000"
        if page:
            url += "&pageToken=" + urllib.request.quote(page)
        data = _request(url, key, timeout=60)
        models.extend(data.get("models") or [])
        page = data.get("nextPageToken") or ""
        if not page:
            return models
    return models


def model_id(model: dict | str) -> str:
    name = model["name"] if isinstance(model, dict) else model
    return name.rsplit("/", 1)[-1]


def version_key(mid: str) -> tuple:
    nums = tuple(int(n) for n in re.findall(r"\d+", mid))
    return (nums, "lite" not in mid, "preview" not in mid)


def _supports_generate(model: dict) -> bool:
    actions = model.get("supportedGenerationMethods") or model.get("supportedActions") or []
    if not actions:
        return True
    return any(str(action).lower() == "generatecontent" for action in actions)


def pick_newest(models: list[dict], kind: str) -> str | None:
    chosen = []
    for model in models:
        mid = model_id(model)
        low = mid.lower()
        if kind == "tts":
            if "tts" not in low:
                continue
        elif "flash" not in low or any(
            token in low for token in ("tts", "image", "live", "embed", "audio", "veo")
        ):
            continue
        if not _supports_generate(model):
            continue
        chosen.append(mid)
    if not chosen:
        return None
    return max(chosen, key=version_key)


def pick_flash_lite(models: list[dict]) -> str | None:
    chosen = []
    for model in models:
        mid = model_id(model)
        low = mid.lower()
        if "flash" not in low or "lite" not in low:
            continue
        if any(token in low for token in ("tts", "image", "live", "embed", "audio", "veo")):
            continue
        if not _supports_generate(model):
            continue
        chosen.append(mid)
    if not chosen:
        return None
    return max(chosen, key=version_key)


def flash_names(models: list[dict]) -> list[str]:
    return sorted(
        model.get("name", "")
        for model in models
        if re.search(r"tts|flash", model.get("name", ""), re.I)
    )


def _generate(key: str, model: str, payload: dict, timeout: int = 120) -> dict:
    return _request(f"{API}/models/{model}:generateContent", key, payload, timeout)


def _parts(data: dict) -> list[dict]:
    candidates = data.get("candidates") or []
    if not candidates:
        prompt_block = (data.get("promptFeedback") or {}).get("blockReason")
        raise RuntimeError(prompt_block or "response had no candidates")
    content = candidates[0].get("content") or {}
    return content.get("parts") or []


IMAGE_MODEL = "gemini-3.1-flash-image"


def image_payload(prompt: str, reference: bytes | None = None) -> dict:
    parts: list[dict] = []
    if reference:
        parts.append(
            {
                "inlineData": {
                    "mimeType": "image/jpeg",
                    "data": base64.b64encode(reference).decode(),
                }
            }
        )
    parts.append({"text": prompt})
    return {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "imageConfig": {"aspectRatio": "9:16"},
        },
    }


def generate_image(key: str, model: str, prompt: str, reference: bytes | None = None) -> bytes:
    data = _generate(key, model, image_payload(prompt, reference), timeout=180)
    for part in _parts(data):
        inline = part.get("inlineData") or part.get("inline_data")
        if inline and inline.get("data"):
            raw = base64.b64decode(inline["data"])
            if raw:
                return raw
    raise RuntimeError("response had no image")


def generate_text(key: str, model: str, prompt: str) -> str:
    data = _generate(
        key,
        model,
        {"contents": [{"parts": [{"text": prompt}]}]},
        timeout=60,
    )
    chunks = []
    for part in _parts(data):
        if part.get("thought"):
            continue
        if part.get("text"):
            chunks.append(part["text"])
    text = "".join(chunks).strip()
    if not text:
        raise RuntimeError("response had no text")
    return text


def _mime_int(mime: str, key: str, default: int) -> int:
    match = re.search(rf"{key}\s*=\s*(\d+)", mime, re.I)
    return int(match.group(1)) if match else default


def _pcm_to_wav(pcm: bytes, rate: int = 24000, channels: int = 1) -> bytes:
    if channels < 1 or len(pcm) == 0 or len(pcm) % (channels * 2):
        raise RuntimeError(f"PCM is not 16-bit x {channels} channels ({len(pcm)} bytes)")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(pcm)
    return buf.getvalue()


def _to_wav(data: bytes, mime: str) -> bytes:
    """3.8 unary audio is already a WAV. Earlier TTS is headerless 24 kHz PCM."""
    kind = mime.split(";", 1)[0].strip().lower()
    if data.startswith(b"RIFF") or kind in {"audio/wav", "audio/x-wav", "audio/wave"}:
        if not data.startswith(b"RIFF"):
            raise RuntimeError(f"{kind or 'audio'} response is not a RIFF wav")
        return data
    return _pcm_to_wav(data, _mime_int(mime, "rate", 24000), _mime_int(mime, "channels", 1))


def synthesize(key: str, model: str, text: str, voice: str = VOICE, style: str | None = None) -> bytes:
    # The transcript stays in text. Style is metadata so 3.8 TTS does not read it aloud.
    part: dict = {"text": text}
    if style:
        part["speechMetadata"] = {"style": style}
    data = _generate(
        key,
        model,
        {
            "contents": [{"parts": [part]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}},
            },
        },
    )
    raw = mime = None
    for part in _parts(data):
        inline = part.get("inlineData") or part.get("inline_data")
        if inline and inline.get("data"):
            mime = inline.get("mimeType") or inline.get("mime_type") or ""
            raw = base64.b64decode(inline["data"])
            break
    if raw is None:
        raise RuntimeError("response had no audio")
    wav = _to_wav(raw, mime or "")
    with wave.open(io.BytesIO(wav), "rb") as handle:
        if handle.getnframes() <= 0:
            raise RuntimeError("wav has no frames")
    return wav
