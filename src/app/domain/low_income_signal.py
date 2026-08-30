from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

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
from app.domain.opportunity_identity import OpportunityIdentity, build_opportunity_identity
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
    identity: OpportunityIdentity


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
        signal_id=inputs.identity.signal_id,
        family=OpportunityFamily.LOW_INCOME,
        source_refs=inputs.source_refs,
        reason_codes=(ReasonCode.INCOME_ATTENTION,),
        detected_at_utc=inputs.source_input.evaluated_at_utc,
    )


def _evidence_packet(inputs: _LowIncomeCandidateInputs) -> IdeaEvidencePacket:
    lineage = LineageRef(
        lineage_id=inputs.identity.lineage_id,
        source_refs=inputs.source_refs,
        content_hash=inputs.identity.evidence_fingerprint,
    )
    return IdeaEvidencePacket(
        evidence_packet_id=inputs.identity.evidence_packet_id,
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
        candidate_id=inputs.identity.candidate_id,
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
) -> OpportunityIdentity:
    return build_opportunity_identity(
        family=OpportunityFamily.LOW_INCOME,
        opportunity_kind="low_income",
        as_of_date=source_input.as_of_date,
        access_scope=source_input.access_scope,
        material_facts={
            "as_of_date": source_input.as_of_date.isoformat(),
            "cash_movement_count": source_input.cash_movement_count,
            "policy_version": policy.policy_version,
            "source_reported_min_projected_cumulative_cashflow": str(
                source_input.source_reported_min_projected_cumulative_cashflow
            ),
        },
        source_refs=source_refs,
    )
