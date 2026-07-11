from __future__ import annotations

import json
from pathlib import Path


def write_json_atomic(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def read_optional_json_object(path: Path | None, *, name: str) -> dict[str, object] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{name} must be a JSON object")
    return payload


def read_optional_capacity_proof(path: Path | None) -> dict[str, object] | None:
    return read_optional_json_object(path, name="capacity proof")


def read_optional_resource_baseline(path: Path | None) -> dict[str, object] | None:
    return read_optional_json_object(path, name="resource baseline")
