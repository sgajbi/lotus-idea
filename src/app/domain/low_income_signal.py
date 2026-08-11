from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
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
from app.domain.signal_evaluation_common import (
    blocked_signal_result,
    temporal_blocked_signal_result,
    validate_timezone_aware_evaluation_time,
)
from app.domain.signal_evaluation_models import (
    SignalEvaluationOutcome,
    SignalEvaluationResult,
)


@dataclass(frozen=True)
class LowIncomeSignalPolicy:
    policy_version: str
    projected_cumulative_cashflow_threshold: Decimal
    candidate_score: Decimal

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise ValueError("policy_version is required")
        if self.projected_cumulative_cashflow_threshold > Decimal("0"):
            raise ValueError("projected_cumulative_cashflow_threshold must be zero or negative")
        if self.candidate_score < Decimal("0") or self.candidate_score > Decimal("100"):
            raise ValueError("candidate_score must be between 0 and 100")


@dataclass(frozen=True)
class LowIncomeSignalInput:
    as_of_date: date
    source_reported_min_projected_cumulative_cashflow: Decimal | None
    cash_movement_count: int | None
    cash_movement_ref: SourceRef | None
    cashflow_projection_ref: SourceRef | None
    evaluated_at_utc: datetime
    entitlement_allowed: bool = True
    access_scope: ReviewAccessScope | None = None
    duplicate_of_candidate_id: str | None = None


@dataclass(frozen=True)
class _LowIncomeCandidateInputs:
    source_input: LowIncomeSignalInput
    policy: LowIncomeSignalPolicy
    source_refs: tuple[SourceRef, ...]
    identity: str


def evaluate_low_income_signal(
    source_input: LowIncomeSignalInput,
    policy: LowIncomeSignalPolicy,
) -> SignalEvaluationResult:
    validate_timezone_aware_evaluation_time(source_input.evaluated_at_utc)
    source_refs = _available_low_income_source_refs(source_input)
    blocking_result = _evaluate_blocking_posture(source_input, source_refs)
    if blocking_result is not None:
        return blocking_result

    materiality_result = _source_cashflow_materiality_result(source_input, policy)
    if materiality_result is not None:
        return materiality_result

    return _candidate_result(
        _LowIncomeCandidateInputs(
            source_input=source_input,
            policy=policy,
            source_refs=source_refs,
            identity=_stable_low_income_identity(source_input, policy, source_refs),
        )
    )


def _evaluate_blocking_posture(
    source_input: LowIncomeSignalInput,
    source_refs: tuple[SourceRef, ...],
) -> SignalEvaluationResult | None:
    if temporal_block := temporal_blocked_signal_result(
        family=OpportunityFamily.LOW_INCOME,
        as_of_date=source_input.as_of_date,
        evaluated_at_utc=source_input.evaluated_at_utc,
        source_refs=source_refs,
    ):
        return temporal_block
    if not source_input.entitlement_allowed:
        return _blocked_low_income_result(
            reason_codes=(ReasonCode.REVIEW_REQUIRED,),
            unsupported_reasons=(UnsupportedEvidenceReason.ENTITLEMENT_DENIED,),
        )
    if missing_source_count := _missing_required_source_count(source_refs):
        return _blocked_low_income_result(
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,) * missing_source_count,
        )
    if any(source_ref.freshness is not EvidenceFreshness.CURRENT for source_ref in source_refs):
        return _blocked_low_income_result(
            reason_codes=(ReasonCode.SOURCE_STALE,),
            unsupported_reasons=(UnsupportedEvidenceReason.STALE_SOURCE,),
        )
    return None


def _source_cashflow_materiality_result(
    source_input: LowIncomeSignalInput,
    policy: LowIncomeSignalPolicy,
) -> SignalEvaluationResult | None:
    if source_input.duplicate_of_candidate_id is not None:
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.SUPPRESSED,
            family=OpportunityFamily.LOW_INCOME,
            reason_codes=(ReasonCode.DUPLICATE_SUPPRESSED,),
        )
    if source_input.cash_movement_count is None:
        return _missing_source_value_result()
    if source_input.cash_movement_count < 0:
        raise ValueError("cash_movement_count must be non-negative")
    if source_input.source_reported_min_projected_cumulative_cashflow is None:
        return _missing_source_value_result()
    if (
        source_input.source_reported_min_projected_cumulative_cashflow
        > policy.projected_cumulative_cashflow_threshold
    ):
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.NOT_ELIGIBLE,
            family=OpportunityFamily.LOW_INCOME,
            reason_codes=(ReasonCode.BELOW_MATERIALITY,),
        )
    return None


def _candidate_result(inputs: _LowIncomeCandidateInputs) -> SignalEvaluationResult:
    signal = _opportunity_signal(inputs)
    evidence_packet = _evidence_packet(inputs)
    candidate = _idea_candidate(inputs, signal, evidence_packet)
    return SignalEvaluationResult(
        outcome=SignalEvaluationOutcome.CANDIDATE_CREATED,
        family=OpportunityFamily.LOW_INCOME,
        reason_codes=evidence_packet.reason_codes,
        signal=signal,
        candidate=candidate,
    )


def _opportunity_signal(inputs: _LowIncomeCandidateInputs) -> OpportunitySignal:
    return OpportunitySignal(
        signal_id=f"signal_low_income_{inputs.identity}",
        family=OpportunityFamily.LOW_INCOME,
        source_refs=inputs.source_refs,
        reason_codes=(ReasonCode.INCOME_ATTENTION,),
        detected_at_utc=inputs.source_input.evaluated_at_utc,
    )


def _evidence_packet(inputs: _LowIncomeCandidateInputs) -> IdeaEvidencePacket:
    lineage = LineageRef(
        lineage_id=f"lineage:lotus-idea:low-income:{inputs.identity}",
        source_refs=inputs.source_refs,
        content_hash=f"sha256:{inputs.identity}",
    )
    return IdeaEvidencePacket(
        evidence_packet_id=f"iep_low_income_{inputs.identity}",
        supportability=EvidenceSupportability.READY,
        source_refs=inputs.source_refs,
        lineage_ref=lineage,
        reason_codes=(ReasonCode.INCOME_ATTENTION, ReasonCode.REVIEW_REQUIRED),
        created_at_utc=inputs.source_input.evaluated_at_utc,
    )


def _idea_candidate(
    inputs: _LowIncomeCandidateInputs,
    signal: OpportunitySignal,
    evidence_packet: IdeaEvidencePacket,
) -> IdeaCandidate:
    return IdeaCandidate(
        candidate_id=f"idea_low_income_{inputs.identity}",
        family=OpportunityFamily.LOW_INCOME,
        lifecycle_status=IdeaLifecycleStatus.GENERATED,
        review_posture=ReviewPosture.ADVISOR_REVIEW_REQUIRED,
        evidence_packet=evidence_packet,
        source_signal_ids=(signal.signal_id,),
        score=IdeaScore(
            policy_version=inputs.policy.policy_version,
            score=inputs.policy.candidate_score,
            reason_codes=(ReasonCode.INCOME_ATTENTION, ReasonCode.REVIEW_REQUIRED),
        ),
        access_scope=inputs.source_input.access_scope,
        created_at_utc=inputs.source_input.evaluated_at_utc,
        updated_at_utc=inputs.source_input.evaluated_at_utc,
    )


def _blocked_low_income_result(
    *,
    reason_codes: tuple[ReasonCode, ...],
    unsupported_reasons: tuple[UnsupportedEvidenceReason, ...],
) -> SignalEvaluationResult:
    return blocked_signal_result(
        family=OpportunityFamily.LOW_INCOME,
        reason_codes=reason_codes,
        unsupported_reasons=unsupported_reasons,
    )


def _available_low_income_source_refs(source_input: LowIncomeSignalInput) -> tuple[SourceRef, ...]:
    return tuple(
        source_ref
        for source_ref in (
            source_input.cash_movement_ref,
            source_input.cashflow_projection_ref,
        )
        if source_ref is not None
    )


def _missing_required_source_count(source_refs: tuple[SourceRef, ...]) -> int:
    return 2 - len(source_refs)


def _missing_source_value_result() -> SignalEvaluationResult:
    return _blocked_low_income_result(
        reason_codes=(ReasonCode.SOURCE_PARTIAL,),
        unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
    )


def _stable_low_income_identity(
    source_input: LowIncomeSignalInput,
    policy: LowIncomeSignalPolicy,
    source_refs: tuple[SourceRef, ...],
) -> str:
    identity_payload = {
        "as_of_date": source_input.as_of_date.isoformat(),
        "cash_movement_count": source_input.cash_movement_count,
        "family": OpportunityFamily.LOW_INCOME.value,
        "policy_version": policy.policy_version,
        "source_reported_min_projected_cumulative_cashflow": str(
            source_input.source_reported_min_projected_cumulative_cashflow
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
