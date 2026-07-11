from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any


def write_dataclass_evidence_atomic(path: Path, evidence: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(
        json.dumps(asdict(evidence), default=_json_evidence_value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _json_evidence_value(value: object) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("evidence datetime must be timezone-aware UTC")
        return value.isoformat()
    raise TypeError(f"unsupported evidence value: {type(value).__name__}")
