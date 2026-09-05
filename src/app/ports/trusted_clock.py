from __future__ import annotations

from datetime import datetime
from typing import Protocol


class TrustedClock(Protocol):
    """Server-owned time source for admission and lifecycle controls."""

    def now_utc(self) -> datetime:
        """Return the current timezone-aware UTC instant."""
        ...


__all__ = ["TrustedClock"]
