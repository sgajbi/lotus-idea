from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol


@dataclass(frozen=True)
class CapacityProbeRequest:
    method: str
    path: str
    headers: Mapping[str, str]
    expected_status_codes: frozenset[int]


@dataclass(frozen=True)
class CapacityProbeResult:
    duration_seconds: float
    status_code: int | None
    transport_outcome: str
    response_summary: Mapping[str, object]


class CapacityProbePort(Protocol):
    def execute(self, request: CapacityProbeRequest) -> CapacityProbeResult: ...

    def close(self) -> None: ...
