from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_optional_json_object(
    path: Path | None,
    *,
    artifact_name: str,
) -> dict[str, Any] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{artifact_name} must be a JSON object")
    return payload
