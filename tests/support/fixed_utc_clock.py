from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class FixedUtcClock:
    value: datetime

    def __post_init__(self) -> None:
        if self.value.tzinfo is None or self.value.utcoffset() is None:
            raise ValueError("value must be timezone-aware")
        if self.value.utcoffset() != timedelta(0):
            raise ValueError("value must use UTC offset +00:00")

    def now_utc(self) -> datetime:
        return self.value


__all__ = ["FixedUtcClock"]
