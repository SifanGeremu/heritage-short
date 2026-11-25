"""Cloudflare Workers AI image calls only. No logging and no output filenames.

FLUX.2 [klein] 9B is the current Workers AI model (docs, 2026-01-28):
https://developers.cloudflare.com/workers-ai/models/flux-2-klein-9b/
Model ID @cf/black-forest-labs/flux-2-klein-9b. REST is multipart form data
even for a prompt-only call. The image comes back as result.image base64.

FLUX.1 [schnell] is the fallback when klein is not on the account:
https://developers.cloudflare.com/workers-ai/models/flux-1-schnell/
Model ID @cf/black-forest-labs/flux-1-schnell. REST is a JSON body.
"""

import base64
import json
import re
import urllib.error
import urllib.request
import uuid

API = "https://api.cloudflare.com/client/v4"
KLEIN = "@cf/black-forest-labs/flux-2-klein-9b"
SCHNELL = "@cf/black-forest-labs/flux-1-schnell"
# 9:16 film frame. Klein accepts 256–1920; both sides are multiples of 8.
WIDTH = 1080
HEIGHT = 1920


class HttpError(RuntimeError):
    def __init__(self, code: int, detail: str):
        self.code = code
        super().__init__(f"HTTP {code}: {detail}")


def redact(text: str, token: str) -> str:
    if token:
        text = text.replace(token, "[redacted]")
    return re.sub(r"(Bearer\s+)\S+", r"\1[redacted]", text)


def model_missing(err: BaseException) -> bool:
    """True when this account does not serve the model. A 429 is not this."""
    status = getattr(err, "code", None) or getattr(err, "status", None)
    text = str(err).lower()
    if status == 404:
        return True
    return any(phrase in text for phrase in ("not found", "unknown model", "does not exist", "no route"))


def _part_type(data: bytes) -> str:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WEBP":
        return "image/webp"
    return "application/octet-stream"


def _multipart(fields: dict[str, str], files: dict[str, bytes] | None = None) -> tuple[bytes, str]:
    boundary = "----heritage" + uuid.uuid4().hex
    lines: list[bytes] = []
    for name, value in fields.items():
        lines.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode()
        )
    for name, data in (files or {}).items():
        header = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"; filename="{name}.img"\r\n'
            f"Content-Type: {_part_type(data)}\r\n\r\n"
        )
        lines.append(header.encode() + data + b"\r\n")
    lines.append(f"--{boundary}--\r\n".encode())
    return b"".join(lines), f"multipart/form-data; boundary={boundary}"


def _image_bytes(body: bytes, content_type: str) -> bytes:
    kind = content_type.split(";", 1)[0].strip().lower()
    if kind.startswith("image/"):
        raw = body
    else:
        try:
            data = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as err:
            raise RuntimeError("response was not an image") from err
        result = data.get("result") if isinstance(data, dict) else None
        image = result.get("image") if isinstance(result, dict) else None
        if not isinstance(image, str) or not image:
            raise RuntimeError("response had no image")
        if image.startswith("data:"):
            image = image.split(",", 1)[-1]
        try:
            raw = base64.b64decode(image, validate=False)
        except (ValueError, TypeError) as err:
            raise RuntimeError("response image was not base64") from err
    if not raw:
        raise RuntimeError("response had no image")
    return raw


def image_ext(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "webp"
    raise RuntimeError("response was not a png, jpeg, or webp")


def _raise_for_body(status: int, body: bytes, token: str) -> None:
    raw = body.decode("utf-8", "replace")
    detail = redact(raw, token)[:500]
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = None
    if isinstance(data, dict) and data.get("success") is False:
        errors = data.get("errors") or []
        message = "; ".join(str(item.get("message") or item) for item in errors if isinstance(item, dict)) or detail
        code = status if status >= 400 else 400
        message = redact(message, token)[:500]
        if model_missing(HttpError(code, message)):
            code = 404
        raise HttpError(code, message)
    if status >= 400:
        raise HttpError(status, detail)


def generate(
    account_id: str,
    token: str,
    model: str,
    prompt: str,
    *,
    width: int | None = None,
    height: int | None = None,
    seed: int | None = None,
    steps: int | None = None,
    images: dict[str, bytes] | None = None,
) -> bytes:
    """One Workers AI image. flux-2 models are multipart; schnell is JSON."""
    url = f"{API}/accounts/{account_id}/ai/run/{model}"
    fields = {"prompt": prompt}
    if width is not None:
        fields["width"] = str(width)
    if height is not None:
        fields["height"] = str(height)
    if seed is not None:
        fields["seed"] = str(seed)
    if steps is not None:
        fields["steps"] = str(steps)
    if images and "flux-2" not in model:
        raise RuntimeError(f"{model} does not accept a reference image")
    if "flux-2" in model:
        body, content_type = _multipart(fields, images)
    else:
        body = json.dumps({key: (int(value) if key != "prompt" else value) for key, value in fields.items()}).encode()
        content_type = "application/json"
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", content_type)
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            payload = resp.read()
            status = resp.status
            content_type = resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as err:
        _raise_for_body(err.code, err.read(), token)
        raise AssertionError("unreachable") from None
    except (urllib.error.URLError, TimeoutError, OSError) as err:
        reason = getattr(err, "reason", err)
        raise RuntimeError(redact(str(reason), token)) from None
    _raise_for_body(status, payload, token)
    image = _image_bytes(payload, content_type)
    image_ext(image)
    return image


def _self_check() -> None:
    png = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
    raw = _image_bytes(json.dumps({"result": {"image": png}}).encode(), "application/json")
    assert image_ext(raw) == "png"
    assert model_missing(HttpError(404, "HTTP 404: no route"))
    assert not model_missing(HttpError(429, "HTTP 429: rate limited"))
    assert not model_missing(HttpError(400, "HTTP 400: prompt is required"))
    body, content_type = _multipart({"prompt": "a stool", "width": "1080"})
    assert "Bearer" not in body.decode()
    assert content_type.startswith("multipart/form-data; boundary=")
    jpeg = b"\xff\xd8\xff\xd9"
    body, _kind = _multipart({"prompt": "a stool"}, {"input_image_0": jpeg})
    assert b'name="input_image_0"' in body and jpeg in body and b"image/jpeg" in body
    print("self-check ok")


if __name__ == "__main__":
    _self_check()
