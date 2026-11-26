#!/usr/bin/env python3
"""Validate the storyboard before any other pipeline stage runs."""

import json
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schema" / "storyboard.schema.json"


def storyboard_path() -> Path:
    # ponytail: root is the contract. schema/storyboard.json remains a fallback
    # so an older checkout still validates. Root wins when it is non-empty.
    root = ROOT / "storyboard.json"
    nested = ROOT / "schema" / "storyboard.json"
    if root.is_file() and root.stat().st_size > 0:
        return root
    return nested


def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, f"{_rel(path)}: file not found"
    except json.JSONDecodeError as err:
        return None, f"{_rel(path)}: {err}"


def _schema_line(err: jsonschema.ValidationError) -> str:
    path = err.json_path
    if err.validator == "required" and "'" in err.message:
        name = err.message.split("'", 2)[1]
        path = f"{path}.{name}"
    return f"{path}: {err.message}"


def shot_invariants(data) -> list[str]:
    """Film length is the sum of shot duration_s, not music-cue duration_s.

    ponytail: cues also use duration_s (generated track length, capped at 60s
    each). Counting them would reject a valid 60–90s film. Upgrade path: add
    any new runtime field to this sum by name.
    """
    if not isinstance(data, dict) or not isinstance(data.get("shots"), list):
        return ["$.shots: expected an array of shots"]
    errors = []
    seen: dict[str, str] = {}
    total = 0
    for index, shot in enumerate(data["shots"]):
        path = f"$.shots[{index}]"
        if not isinstance(shot, dict):
            errors.append(f"{path}: expected an object")
            continue
        sid = shot.get("id")
        if isinstance(sid, str):
            if sid in seen:
                errors.append(f"{path}.id: duplicate shot id {sid!r} (also at {seen[sid]})")
            else:
                seen[sid] = f"{path}.id"
        duration = shot.get("duration_s")
        if isinstance(duration, (int, float)) and not isinstance(duration, bool):
            total += duration
    if not 60 <= total <= 90:
        errors.append(f"$.shots: total duration_s is {total:g}, must be between 60 and 90")
    return errors


def collect_errors() -> tuple[object, list[str]]:
    schema, schema_err = _load(SCHEMA_PATH)
    data, data_err = _load(storyboard_path())
    errors = [line for line in (schema_err, data_err) if line]
    if schema_err or data_err:
        return data, errors
    try:
        validator_cls = jsonschema.validators.validator_for(schema)
        validator_cls.check_schema(schema)
        validator = validator_cls(schema)
    except jsonschema.exceptions.SchemaError as err:
        return data, [f"{_rel(SCHEMA_PATH)}: {err.message}"]
    schema_errors = sorted(validator.iter_errors(data), key=lambda err: list(err.absolute_path))
    errors.extend(_schema_line(err) for err in schema_errors)
    errors.extend(shot_invariants(data))
    return data, errors


def ensure_storyboard():
    """Load a valid storyboard or exit 1. Every pipeline stage calls this first."""
    data, errors = collect_errors()
    if errors:
        for line in errors:
            print(line, file=sys.stderr)
        raise SystemExit(1)
    return data


def main() -> int:
    _data, errors = collect_errors()
    if errors:
        for line in errors:
            print(line, file=sys.stderr)
        return 1
    print("ok")
    return 0


def _self_check() -> None:
    short = {"shots": [{"id": "s01", "duration_s": 30}, {"id": "s01", "duration_s": 20}]}
    errs = shot_invariants(short)
    assert any("duplicate" in err for err in errs)
    assert any("total duration_s is 50" in err for err in errs)
    ok = {"shots": [{"id": f"s{i:02d}", "duration_s": 8} for i in range(1, 10)]}
    ok["shots"].append({"id": "s10", "duration_s": 6})
    assert shot_invariants(ok) == []
    assert shot_invariants({"shots": [{"id": "s01", "duration_s": 60}]}) == []
    assert shot_invariants({"shots": [{"id": "s01", "duration_s": 90}]}) == []
    assert any("91" in err for err in shot_invariants({"shots": [{"id": "s01", "duration_s": 91}]}))
    print("self-check ok")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-check":
        _self_check()
    else:
        sys.exit(main())
