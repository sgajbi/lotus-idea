from __future__ import annotations

from datetime import UTC, datetime


class SystemUtcClock:
    """Production clock for server acceptance and control decisions."""

    def now_utc(self) -> datetime:
        return datetime.now(UTC)


__all__ = ["SystemUtcClock"]
