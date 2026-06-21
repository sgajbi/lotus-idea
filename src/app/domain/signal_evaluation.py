from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
import hashlib
import json

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


class SignalEvaluationOutcome(StrEnum):
    CANDIDATE_CREATED = "candidate_created"
    NOT_ELIGIBLE = "not_eligible"
    BLOCKED = "blocked"
    SUPPRESSED = "suppressed"


@dataclass(frozen=True)
class HighCashSignalPolicy:
    policy_version: str
    cash_weight_threshold: Decimal
    candidate_score: Decimal

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise ValueError("policy_version is required")
        if self.cash_weight_threshold < Decimal("0") or self.cash_weight_threshold > Decimal("1"):
            raise ValueError("cash_weight_threshold must be between 0 and 1")
        if self.candidate_score < Decimal("0") or self.candidate_score > Decimal("100"):
            raise ValueError("candidate_score must be between 0 and 100")


@dataclass(frozen=True)
class HighCashSignalInput:
    as_of_date: date
    source_reported_cash_weight: Decimal | None
    portfolio_state_ref: SourceRef | None
    holdings_ref: SourceRef | None
    cash_movement_ref: SourceRef | None
    cashflow_projection_ref: SourceRef | None
    evaluated_at_utc: datetime
    entitlement_allowed: bool = True
    duplicate_of_candidate_id: str | None = None


@dataclass(frozen=True)
class SignalEvaluationResult:
    outcome: SignalEvaluationOutcome
    family: OpportunityFamily
    reason_codes: tuple[ReasonCode, ...]
    unsupported_reasons: tuple[UnsupportedEvidenceReason, ...] = ()
    signal: OpportunitySignal | None = None
    candidate: IdeaCandidate | None = None


def evaluate_high_cash_signal(
    source_input: HighCashSignalInput,
    policy: HighCashSignalPolicy,
) -> SignalEvaluationResult:
    if source_input.evaluated_at_utc.tzinfo is None:
        raise ValueError("evaluated_at_utc must be timezone-aware")

    source_refs = _available_source_refs(source_input)
    missing_reasons = _missing_required_sources(source_input)
    if not source_input.entitlement_allowed:
        return _blocked(
            reason_codes=(ReasonCode.REVIEW_REQUIRED,),
            unsupported_reasons=(UnsupportedEvidenceReason.ENTITLEMENT_DENIED,),
        )
    if missing_reasons:
        return _blocked(
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=missing_reasons,
        )
    stale_sources = [
        source_ref
        for source_ref in source_refs
        if source_ref.freshness is not EvidenceFreshness.CURRENT
    ]
    if stale_sources:
        return _blocked(
            reason_codes=(ReasonCode.SOURCE_STALE,),
            unsupported_reasons=(UnsupportedEvidenceReason.STALE_SOURCE,),
        )
    if source_input.duplicate_of_candidate_id is not None:
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.SUPPRESSED,
            family=OpportunityFamily.HIGH_CASH,
            reason_codes=(ReasonCode.DUPLICATE_SUPPRESSED,),
        )
    if source_input.source_reported_cash_weight is None:
        return _blocked(
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )
    if source_input.source_reported_cash_weight < Decimal(
        "0"
    ) or source_input.source_reported_cash_weight > Decimal("1"):
        raise ValueError("source_reported_cash_weight must be between 0 and 1")
    if source_input.source_reported_cash_weight < policy.cash_weight_threshold:
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.NOT_ELIGIBLE,
            family=OpportunityFamily.HIGH_CASH,
            reason_codes=(ReasonCode.BELOW_MATERIALITY,),
        )

    identity = _stable_identity(source_input, policy, source_refs)
    signal = OpportunitySignal(
        signal_id=f"signal_high_cash_{identity}",
        family=OpportunityFamily.HIGH_CASH,
        source_refs=source_refs,
        reason_codes=(ReasonCode.HIGH_CASH_RATIO, ReasonCode.CASH_SOURCE_READY),
        detected_at_utc=source_input.evaluated_at_utc,
    )
    lineage = LineageRef(
        lineage_id=f"lineage:lotus-idea:high-cash:{identity}",
        source_refs=source_refs,
        content_hash=f"sha256:{identity}",
    )
    evidence_packet = IdeaEvidencePacket(
        evidence_packet_id=f"iep_high_cash_{identity}",
        supportability=EvidenceSupportability.READY,
        source_refs=source_refs,
        lineage_ref=lineage,
        reason_codes=(
            ReasonCode.HIGH_CASH_RATIO,
            ReasonCode.CASH_SOURCE_READY,
            ReasonCode.REVIEW_REQUIRED,
        ),
        created_at_utc=source_input.evaluated_at_utc,
    )
    candidate = IdeaCandidate(
        candidate_id=f"idea_high_cash_{identity}",
        family=OpportunityFamily.HIGH_CASH,
        lifecycle_status=IdeaLifecycleStatus.GENERATED,
        review_posture=ReviewPosture.ADVISOR_REVIEW_REQUIRED,
        evidence_packet=evidence_packet,
        source_signal_ids=(signal.signal_id,),
        score=IdeaScore(
            policy_version=policy.policy_version,
            score=policy.candidate_score,
            reason_codes=(ReasonCode.HIGH_CASH_RATIO, ReasonCode.REVIEW_REQUIRED),
        ),
        created_at_utc=source_input.evaluated_at_utc,
        updated_at_utc=source_input.evaluated_at_utc,
    )
    return SignalEvaluationResult(
        outcome=SignalEvaluationOutcome.CANDIDATE_CREATED,
        family=OpportunityFamily.HIGH_CASH,
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
        family=OpportunityFamily.HIGH_CASH,
        reason_codes=reason_codes,
        unsupported_reasons=unsupported_reasons,
    )


def _available_source_refs(source_input: HighCashSignalInput) -> tuple[SourceRef, ...]:
    return tuple(
        source_ref
        for source_ref in (
            source_input.portfolio_state_ref,
            source_input.holdings_ref,
            source_input.cash_movement_ref,
            source_input.cashflow_projection_ref,
        )
        if source_ref is not None
    )


def _missing_required_sources(
    source_input: HighCashSignalInput,
) -> tuple[UnsupportedEvidenceReason, ...]:
    missing_count = 4 - len(_available_source_refs(source_input))
    return (UnsupportedEvidenceReason.MISSING_SOURCE,) * missing_count


def _stable_identity(
    source_input: HighCashSignalInput,
    policy: HighCashSignalPolicy,
    source_refs: tuple[SourceRef, ...],
) -> str:
    identity_payload = {
        "as_of_date": source_input.as_of_date.isoformat(),
        "cash_weight": str(source_input.source_reported_cash_weight),
        "family": OpportunityFamily.HIGH_CASH.value,
        "policy_version": policy.policy_version,
        "source_hashes": [source_ref.content_hash for source_ref in source_refs],
    }
    canonical = json.dumps(identity_payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
