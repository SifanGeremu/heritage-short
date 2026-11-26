#!/usr/bin/env python3
"""Three answers become a three-shot board. No picture calls."""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORYBOARD = ROOT / "storyboard.json"

FATHER = (
    "elderly Oromo man in his late sixties, deep-lined weathered face, "
    "short silver-gray hair, worn dark-brown coat, thin weathered hands"
)
VOICE = "om-ayyaantuu"
SHOT_S = 8
SEEDS = (511, 512, 513)
REFERENCE_SEED = 501
MOTIONS = ("push-in", "drift", "pull-back")


def _line(answers: dict, key: str, limit: int) -> str:
    value = answers.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{key} is required")
    value = " ".join(value.split())
    if not value:
        raise ValueError(f"{key} is required")
    if len(value) > limit:
        raise ValueError(f"{key} is too long")
    return value


def relation_of(*parts: str) -> str:
    text = " ".join(parts).casefold()
    if re.search(r"\b(father|dad|abbaa|abba)\b", text):
        return "father"
    return "mother"


def film_look() -> tuple[str, str]:
    data = json.loads(STORYBOARD.read_text(encoding="utf-8"))
    style = str(data.get("style_block") or "").strip()
    mother = str((data.get("character") or {}).get("description") or "").strip()
    if len(style) < 20 or len(mother) < 20:
        raise ValueError("storyboard.json is missing the style or the mother")
    return style, mother


def build(answers: dict) -> dict:
    """Shot 1 says the name. Shot 2 paints the object. Shot 3 speaks the last line."""
    name = _line(answers, "name", 60)
    who_om = _line(answers, "who_om", 280)
    who_en = _line(answers, "who_en", 280)
    thing = _line(answers, "object", 80)
    memory_om = _line(answers, "memory_om", 280)
    memory_en = _line(answers, "memory_en", 280)
    last_om = _line(answers, "last_om", 280)
    last_en = _line(answers, "last_en", 280)

    style, mother = film_look()
    relation = relation_of(name, who_om, who_en)
    description = FATHER if relation == "father" else mother
    who = "man" if relation == "father" else "woman"

    scenes = (
        (
            "wide shot of a dim mud-walled highland room in August rain, "
            f"the painted {who} seated near a rain-streaked window, "
            "low wooden stool, bright open doorway"
        ),
        (
            f"medium shot of the painted {who} holding {thing}, "
            f"{thing} clearly in frame, warm doorway light"
        ),
        (
            f"the painted {who} standing in a bright doorway, "
            "August rain outside, quiet pride, dry eyes"
        ),
    )
    reasons = (
        f"She says the name {name}.",
        f"The private memory is {thing}.",
        "The last line is spoken in full.",
    )
    lines = ((who_om, who_en), (memory_om, memory_en), (last_om, last_en))
    shots = []
    for index, scene in enumerate(scenes):
        om, en = lines[index]
        shots.append(
            {
                "id": f"s{index + 1:02d}",
                "duration_s": SHOT_S,
                "motion": MOTIONS[index],
                "seed": SEEDS[index],
                "reason": reasons[index],
                "image_prompt": (
                    f"{style}. {description}. {scene}. "
                    "Painted character, not a portrait of any real person, no readable text"
                ),
                "narration": {"om": om, "en": en},
            }
        )
    if shots[2]["narration"]["om"] != last_om:
        raise ValueError("the last line was not kept")
    return {
        "character": {
            "is_real_person": False,
            "relation": relation,
            "description": description,
            "reference_seed": REFERENCE_SEED,
        },
        "style_block": style,
        "voice": VOICE,
        "shots": shots,
    }


def _self_check() -> None:
    board = build(
        {
            "name": "Eebbisaa",
            "who_om": "Eebbisaa koo, roobni ammallee rukkuta.",
            "who_en": "My Eebbisaa, the rain still taps this roof.",
            "object": "blue pen",
            "memory_om": "Qalama cuquliisaa keetiin barreessite.",
            "memory_en": "You wrote with a blue pen.",
            "last_om": "Har'a, ilma koo, ani hin boo'u.",
            "last_en": "Tonight, my son, I will not cry.",
        }
    )
    assert board["character"]["is_real_person"] is False
    assert "Eebbisaa" in board["shots"][0]["narration"]["om"]
    assert "blue pen" in board["shots"][1]["image_prompt"]
    assert board["shots"][2]["narration"]["om"] == "Har'a, ilma koo, ani hin boo'u."
    assert all(shot["duration_s"] == 8 for shot in board["shots"])
    father = build(
        {
            "name": "Eebbisaa",
            "who_om": "Eebbisaa koo.",
            "who_en": "My father, the rain still falls.",
            "object": "guitar",
            "memory_om": "Gitaarri kee as jira.",
            "memory_en": "Your guitar is still here.",
            "last_om": "Ani hin boo'u.",
            "last_en": "I will not cry.",
        }
    )
    assert father["character"]["relation"] == "father"
    assert "man" in father["character"]["description"]
    assert father["character"]["is_real_person"] is False
    free = build(
        {
            "name": "Eebbisaa",
            "who_om": "Roobni ammallee rukkuta.",
            "who_en": "The rain still taps.",
            "object": "cup",
            "memory_om": "Shaayiin kee na eeggata.",
            "memory_en": "Your tea is waiting.",
            "last_om": "Ani hin boo'u.",
            "last_en": "I will not cry.",
        }
    )
    assert free["shots"][0]["narration"]["om"] == "Roobni ammallee rukkuta."
    print("self-check ok")


if __name__ == "__main__":
    if "--self-check" in sys.argv:
        _self_check()
    else:
        print("usage: python family/board.py --self-check", file=sys.stderr)
        sys.exit(2)
