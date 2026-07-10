from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any


def write_dataclass_evidence_atomic(path: Path, evidence: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(
        json.dumps(asdict(evidence), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
