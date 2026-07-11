from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class ProcessResourceSnapshot:
    observed_at_utc: datetime
    cpu_seconds_total: float
    resident_memory_bytes: int
    virtual_memory_bytes: int | None = None
    open_file_descriptors: int | None = None
    max_file_descriptors: int | None = None

    def __post_init__(self) -> None:
        if self.observed_at_utc.tzinfo is None or self.observed_at_utc.utcoffset() is None:
            raise ValueError("observed_at_utc must be timezone-aware")
        if self.cpu_seconds_total < 0:
            raise ValueError("cpu_seconds_total must not be negative")
        if self.resident_memory_bytes < 0:
            raise ValueError("resident_memory_bytes must not be negative")
        if self.virtual_memory_bytes is not None and self.virtual_memory_bytes < 0:
            raise ValueError("virtual_memory_bytes must not be negative")
        if (self.open_file_descriptors is None) != (self.max_file_descriptors is None):
            raise ValueError("file descriptor measurements must be present together")
        if self.open_file_descriptors is not None:
            if self.open_file_descriptors < 0:
                raise ValueError("open_file_descriptors must not be negative")
            if self.max_file_descriptors is None or self.max_file_descriptors <= 0:
                raise ValueError("max_file_descriptors must be positive")
            if self.open_file_descriptors > self.max_file_descriptors:
                raise ValueError("open_file_descriptors must not exceed max_file_descriptors")


class ResourceProbeError(RuntimeError):
    pass


class ProcessResourceProbePort(Protocol):
    def execute(self) -> ProcessResourceSnapshot: ...

    def close(self) -> None: ...
