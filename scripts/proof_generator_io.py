from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def timeout_seconds_from_args(args: object) -> float:
    try:
        timeout = float(getattr(args, "timeout_seconds"))
    except ValueError as exc:
        raise ValueError("timeout seconds must be numeric") from exc
    if timeout <= 0:
        raise ValueError("timeout seconds must be positive")
    return timeout


def write_json_payload(payload: dict[str, Any], *, output: str | None) -> None:
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(f"{rendered}\n", encoding="utf-8")
        return
    print(rendered)
