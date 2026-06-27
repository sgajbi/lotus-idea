from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class ImplementationProofCapabilityReadiness:
    capability_id: str
    name: str
    readiness_status: str
    supportability_status: str
    evidence_refs: tuple[str, ...]
    blockers: tuple[str, ...]
    supported_feature_promoted: bool

    @property
    def certification_ready(self) -> bool:
        return not self.blockers

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))
        object.__setattr__(self, "blockers", tuple(self.blockers))


@dataclass(frozen=True)
class ImplementationProofReadinessSnapshot:
    repository: str
    evaluated_at_utc: datetime
    readiness_status: str
    supportability_status: str
    certification_ready: bool
    capability_count: int
    certification_ready_capability_count: int
    blocked_capability_count: int
    supported_feature_count: int
    supported_features_promoted: bool
    overall_blockers: tuple[str, ...]
    source_of_truth: Mapping[str, str]
    capabilities: tuple[ImplementationProofCapabilityReadiness, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "overall_blockers", tuple(self.overall_blockers))
        object.__setattr__(
            self,
            "source_of_truth",
            MappingProxyType(dict(self.source_of_truth)),
        )
        object.__setattr__(self, "capabilities", tuple(self.capabilities))
