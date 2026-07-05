from __future__ import annotations

from typing import Any


def first_reason_code(payload: dict[str, Any]) -> str | None:
    reason_codes = payload.get("reason_codes") or payload.get("reasonCodes")
    if isinstance(reason_codes, list):
        for reason_code in reason_codes:
            if isinstance(reason_code, str) and reason_code.strip():
                return reason_code.strip()
    return None
