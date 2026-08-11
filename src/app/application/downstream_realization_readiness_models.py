from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class DownstreamRealizationCapabilityReadiness:
    capability_id: str
    name: str
    source_authority: str
    readiness_status: str
    supportability_status: str
    evidence_refs: tuple[str, ...]
    blockers: tuple[str, ...]
    blocker_issue_refs: Mapping[str, tuple[str, ...]]

    @property
    def certification_ready(self) -> bool:
        return not self.blockers

    def __post_init__(self) -> None:
        _freeze_blocker_readiness(self)


@dataclass(frozen=True)
class DownstreamRealizationContractReadiness:
    contract_id: str
    owner_repository: str
    source_authority: str
    target_route: str
    route_fit_status: str
    adapter_status: str
    evidence_refs: tuple[str, ...]
    blockers: tuple[str, ...]
    blocker_issue_refs: Mapping[str, tuple[str, ...]]

    @property
    def certification_ready(self) -> bool:
        return not self.blockers

    def __post_init__(self) -> None:
        _freeze_blocker_readiness(self)


@dataclass(frozen=True)
class DownstreamRealizationReadinessSnapshot:
    repository: str
    readiness_status: str
    supportability_status: str
    certification_ready: bool
    durable_storage_backed: bool
    conversion_intent_count: int
    conversion_outcome_count: int
    report_evidence_pack_request_count: int
    downstream_submission_count: int
    downstream_reconciliation_required_count: int
    downstream_adapter_foundation_present: bool
    source_of_truth: Mapping[str, str]
    blockers: tuple[str, ...]
    blocker_issue_refs: Mapping[str, tuple[str, ...]]
    capabilities: tuple[DownstreamRealizationCapabilityReadiness, ...]
    downstream_contracts: tuple[DownstreamRealizationContractReadiness, ...]
    supported_feature_promoted: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_of_truth",
            MappingProxyType(dict(self.source_of_truth)),
        )
        object.__setattr__(self, "blockers", tuple(self.blockers))
        object.__setattr__(
            self,
            "blocker_issue_refs",
            immutable_issue_refs(self.blocker_issue_refs),
        )
        object.__setattr__(self, "capabilities", tuple(self.capabilities))
        object.__setattr__(
            self,
            "downstream_contracts",
            tuple(self.downstream_contracts),
        )


DownstreamReadinessComponents = tuple[
    tuple[DownstreamRealizationCapabilityReadiness, ...],
    tuple[DownstreamRealizationContractReadiness, ...],
]


def build_downstream_capability_readiness(
    capability_id: str,
    name: str,
    source_authority: str,
    *,
    evidence_refs: tuple[str, ...],
    blockers: tuple[str, ...],
    blocker_issue_refs: Mapping[str, tuple[str, ...]],
) -> DownstreamRealizationCapabilityReadiness:
    return DownstreamRealizationCapabilityReadiness(
        capability_id=capability_id,
        name=name,
        source_authority=source_authority,
        readiness_status="planned",
        supportability_status="not_certified",
        evidence_refs=evidence_refs,
        blockers=blockers,
        blocker_issue_refs=blocker_issue_refs,
    )


def immutable_issue_refs(
    issue_refs: Mapping[str, tuple[str, ...]],
) -> Mapping[str, tuple[str, ...]]:
    return MappingProxyType(
        {
            str(blocker): tuple(str(issue_ref) for issue_ref in refs)
            for blocker, refs in issue_refs.items()
        }
    )


def _freeze_blocker_readiness(
    readiness: DownstreamRealizationCapabilityReadiness | DownstreamRealizationContractReadiness,
) -> None:
    object.__setattr__(readiness, "evidence_refs", tuple(readiness.evidence_refs))
    object.__setattr__(readiness, "blockers", tuple(readiness.blockers))
    object.__setattr__(
        readiness,
        "blocker_issue_refs",
        immutable_issue_refs(readiness.blocker_issue_refs),
    )
