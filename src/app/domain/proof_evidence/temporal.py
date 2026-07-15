from __future__ import annotations

from datetime import UTC, datetime


def parse_timezone_aware_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(UTC)


def is_timezone_aware_datetime_text(value: object) -> bool:
    return parse_timezone_aware_datetime(value) is not None
