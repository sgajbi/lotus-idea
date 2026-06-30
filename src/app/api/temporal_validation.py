from __future__ import annotations

from datetime import UTC, datetime


def is_timezone_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


def is_utc_datetime(value: datetime) -> bool:
    return is_timezone_aware(value) and value.utcoffset() == UTC.utcoffset(value)


def require_timezone_aware(
    value: datetime,
    *,
    field_name: str,
    message: str | None = None,
) -> datetime:
    if not is_timezone_aware(value):
        raise ValueError(message or f"{field_name} must be timezone-aware")
    return value


def require_utc_datetime(
    value: datetime,
    *,
    field_name: str,
    message: str | None = None,
) -> datetime:
    if not is_utc_datetime(value):
        raise ValueError(message or f"{field_name} must be UTC")
    return value
