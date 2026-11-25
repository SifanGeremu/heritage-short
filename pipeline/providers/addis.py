"""Addis AI calls only. No logging and no output filenames.

The SDK retries on its own unless max_retries is 0. Leave it at 0 so the
smoke script's with_retry is the only retry layer and each attempt is logged.
"""

from addisai import AddisAI

VOICE = "om-bikila"
LANGUAGE = "om"
# Voices 2 list price. Smoke uses measured duration, not the estimate.
COST_PER_MINUTE_ETB = 5


def synthesize(api_key: str, text: str, voice: str = VOICE, language: str = LANGUAGE) -> bytes:
    client = AddisAI(api_key=api_key, max_retries=0)
    clip = client.voice.generate(
        voice_id=voice,
        text=text,
        language=language,
        output_format="wav_44100",
    )
    data = clip.content()
    if not data:
        raise RuntimeError("response had no audio")
    return data


def cost_etb(seconds: float) -> float:
    return round(COST_PER_MINUTE_ETB * seconds / 60, 4)
