from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
import hashlib
import json

from app.domain.access_scope import ReviewAccessScope
from app.domain.ideas import (
    EvidenceFreshness,
    EvidenceSupportability,
    IdeaCandidate,
    IdeaEvidencePacket,
    IdeaLifecycleStatus,
    IdeaScore,
    LineageRef,
    OpportunityFamily,
    OpportunitySignal,
    ReasonCode,
    ReviewPosture,
    SourceRef,
    UnsupportedEvidenceReason,
)
from app.domain.signal_evaluation import (
    SignalEvaluationOutcome,
    SignalEvaluationResult,
    temporal_blocked_signal_result,
)


@dataclass(frozen=True)
class BondMaturitySignalPolicy:
    policy_version: str
    maturity_window_days: int
    candidate_score: Decimal

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise ValueError("policy_version is required")
        if self.maturity_window_days < 1 or self.maturity_window_days > 366:
            raise ValueError("maturity_window_days must be between 1 and 366")
        if self.candidate_score < Decimal("0") or self.candidate_score > Decimal("100"):
            raise ValueError("candidate_score must be between 0 and 100")


@dataclass(frozen=True)
class BondMaturitySignalInput:
    as_of_date: date
    source_reported_next_maturity_date: date | None
    source_reported_maturing_position_count: int | None
    holdings_ref: SourceRef | None
    maturity_fact_ref: SourceRef | None
    evaluated_at_utc: datetime
    entitlement_allowed: bool = True
    access_scope: ReviewAccessScope | None = None
    duplicate_of_candidate_id: str | None = None


def evaluate_bond_maturity_signal(
    source_input: BondMaturitySignalInput,
    policy: BondMaturitySignalPolicy,
) -> SignalEvaluationResult:
    if (
        source_input.evaluated_at_utc.tzinfo is None
        or source_input.evaluated_at_utc.utcoffset() is None
    ):
        raise ValueError("evaluated_at_utc must be timezone-aware")

    source_refs = _available_bond_maturity_source_refs(source_input)
    missing_count = 2 - len(source_refs)
    temporal_block = temporal_blocked_signal_result(
        family=OpportunityFamily.BOND_MATURITY,
        as_of_date=source_input.as_of_date,
        evaluated_at_utc=source_input.evaluated_at_utc,
        source_refs=source_refs,
    )
    if temporal_block is not None:
        return temporal_block
    if not source_input.entitlement_allowed:
        return _blocked(
            reason_codes=(ReasonCode.REVIEW_REQUIRED,),
            unsupported_reasons=(UnsupportedEvidenceReason.ENTITLEMENT_DENIED,),
        )
    if missing_count:
        return _blocked(
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,) * missing_count,
        )
    if any(source_ref.freshness is not EvidenceFreshness.CURRENT for source_ref in source_refs):
        return _blocked(
            reason_codes=(ReasonCode.SOURCE_STALE,),
            unsupported_reasons=(UnsupportedEvidenceReason.STALE_SOURCE,),
        )
    if source_input.duplicate_of_candidate_id is not None:
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.SUPPRESSED,
            family=OpportunityFamily.BOND_MATURITY,
            reason_codes=(ReasonCode.DUPLICATE_SUPPRESSED,),
        )
    if source_input.source_reported_maturing_position_count is None:
        return _blocked(
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )
    if source_input.source_reported_maturing_position_count < 0:
        raise ValueError("source_reported_maturing_position_count must be non-negative")
    if source_input.source_reported_next_maturity_date is None:
        return _blocked(
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )
    if source_input.source_reported_maturing_position_count == 0 or not _within_maturity_window(
        as_of_date=source_input.as_of_date,
        maturity_date=source_input.source_reported_next_maturity_date,
        window_days=policy.maturity_window_days,
    ):
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.NOT_ELIGIBLE,
            family=OpportunityFamily.BOND_MATURITY,
            reason_codes=(ReasonCode.BELOW_MATERIALITY,),
        )

    identity = _stable_bond_maturity_identity(source_input, policy, source_refs)
    signal = OpportunitySignal(
        signal_id=f"signal_bond_maturity_{identity}",
        family=OpportunityFamily.BOND_MATURITY,
        source_refs=source_refs,
        reason_codes=(ReasonCode.MATURITY_WINDOW,),
        detected_at_utc=source_input.evaluated_at_utc,
    )
    lineage = LineageRef(
        lineage_id=f"lineage:lotus-idea:bond-maturity:{identity}",
        source_refs=source_refs,
        content_hash=f"sha256:{identity}",
    )
    evidence_packet = IdeaEvidencePacket(
        evidence_packet_id=f"iep_bond_maturity_{identity}",
        supportability=EvidenceSupportability.READY,
        source_refs=source_refs,
        lineage_ref=lineage,
        reason_codes=(ReasonCode.MATURITY_WINDOW, ReasonCode.REVIEW_REQUIRED),
        created_at_utc=source_input.evaluated_at_utc,
    )
    candidate = IdeaCandidate(
        candidate_id=f"idea_bond_maturity_{identity}",
        family=OpportunityFamily.BOND_MATURITY,
        lifecycle_status=IdeaLifecycleStatus.GENERATED,
        review_posture=ReviewPosture.ADVISOR_REVIEW_REQUIRED,
        evidence_packet=evidence_packet,
        source_signal_ids=(signal.signal_id,),
        score=IdeaScore(
            policy_version=policy.policy_version,
            score=policy.candidate_score,
            reason_codes=(ReasonCode.MATURITY_WINDOW, ReasonCode.REVIEW_REQUIRED),
        ),
        access_scope=source_input.access_scope,
        created_at_utc=source_input.evaluated_at_utc,
        updated_at_utc=source_input.evaluated_at_utc,
    )
    return SignalEvaluationResult(
        outcome=SignalEvaluationOutcome.CANDIDATE_CREATED,
        family=OpportunityFamily.BOND_MATURITY,
        reason_codes=evidence_packet.reason_codes,
        signal=signal,
        candidate=candidate,
    )


def _blocked(
    *,
    reason_codes: tuple[ReasonCode, ...],
    unsupported_reasons: tuple[UnsupportedEvidenceReason, ...],
) -> SignalEvaluationResult:
    return SignalEvaluationResult(
        outcome=SignalEvaluationOutcome.BLOCKED,
        family=OpportunityFamily.BOND_MATURITY,
        reason_codes=reason_codes,
        unsupported_reasons=unsupported_reasons,
    )


def _available_bond_maturity_source_refs(
    source_input: BondMaturitySignalInput,
) -> tuple[SourceRef, ...]:
    return tuple(
        source_ref
        for source_ref in (
            source_input.holdings_ref,
            source_input.maturity_fact_ref,
        )
        if source_ref is not None
    )


def _within_maturity_window(
    *,
    as_of_date: date,
    maturity_date: date,
    window_days: int,
) -> bool:
    return as_of_date <= maturity_date <= as_of_date + timedelta(days=window_days)


def _stable_bond_maturity_identity(
    source_input: BondMaturitySignalInput,
    policy: BondMaturitySignalPolicy,
    source_refs: tuple[SourceRef, ...],
) -> str:
    identity_payload = {
        "as_of_date": source_input.as_of_date.isoformat(),
        "family": OpportunityFamily.BOND_MATURITY.value,
        "maturity_window_days": policy.maturity_window_days,
        "policy_version": policy.policy_version,
        "source_reported_maturing_position_count": (
            source_input.source_reported_maturing_position_count
        ),
        "source_reported_next_maturity_date": (
            source_input.source_reported_next_maturity_date.isoformat()
            if source_input.source_reported_next_maturity_date is not None
            else None
        ),
        "access_scope": (
            {
                "tenant_id": source_input.access_scope.tenant_id,
                "book_id": source_input.access_scope.book_id,
                "portfolio_id": source_input.access_scope.portfolio_id,
                "client_id": source_input.access_scope.client_id,
            }
            if source_input.access_scope is not None
            else None
        ),
        "source_hashes": [source_ref.content_hash for source_ref in source_refs],
    }
    canonical = json.dumps(identity_payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
