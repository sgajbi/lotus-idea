from __future__ import annotations

from decimal import Decimal
import hashlib
import json

from app.domain.drawdown_review_evaluation import evaluate_drawdown_review_signal
from app.domain.high_volatility_evaluation import evaluate_high_volatility_signal
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
    ConcentrationRiskSignalInput,
    ConcentrationRiskSignalPolicy,
    DrawdownReviewSignalInput,
    DrawdownReviewSignalPolicy,
    HighCashSignalInput,
    HighCashSignalPolicy,
    HighVolatilitySignalInput,
    HighVolatilitySignalPolicy,
    MandateHealthSignalInput,
    MandateHealthSignalPolicy,
    SignalEvaluationOutcome,
    SignalEvaluationResult,
    UnderperformanceSignalInput,
    UnderperformanceSignalPolicy,
)


def evaluate_high_cash_signal(
    source_input: HighCashSignalInput,
    policy: HighCashSignalPolicy,
) -> SignalEvaluationResult:
    validate_timezone_aware_evaluation_time(source_input.evaluated_at_utc)
    source_refs = _available_source_refs(source_input)

    if source_block := _high_cash_source_block(source_input, source_refs):
        return source_block
    if materiality_result := _high_cash_materiality_result(source_input, policy):
        return materiality_result

    return _high_cash_candidate_created_result(source_input, policy, source_refs)


def _high_cash_source_block(
    source_input: HighCashSignalInput,
    source_refs: tuple[SourceRef, ...],
) -> SignalEvaluationResult | None:
    if not source_input.entitlement_allowed:
        return blocked_signal_result(
            family=OpportunityFamily.HIGH_CASH,
            reason_codes=(ReasonCode.REVIEW_REQUIRED,),
            unsupported_reasons=(UnsupportedEvidenceReason.ENTITLEMENT_DENIED,),
        )
    missing_reasons = _missing_required_sources(source_input)
    if missing_reasons:
        return blocked_signal_result(
            family=OpportunityFamily.HIGH_CASH,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=missing_reasons,
        )
    temporal_block = temporal_blocked_signal_result(
        family=OpportunityFamily.HIGH_CASH,
        as_of_date=source_input.as_of_date,
        evaluated_at_utc=source_input.evaluated_at_utc,
        source_refs=source_refs,
    )
    if temporal_block is not None:
        return temporal_block
    stale_sources = [
        source_ref
        for source_ref in source_refs
        if source_ref.freshness is not EvidenceFreshness.CURRENT
    ]
    if stale_sources:
        return blocked_signal_result(
            family=OpportunityFamily.HIGH_CASH,
            reason_codes=(ReasonCode.SOURCE_STALE,),
            unsupported_reasons=(UnsupportedEvidenceReason.STALE_SOURCE,),
        )
    return None


def _high_cash_materiality_result(
    source_input: HighCashSignalInput,
    policy: HighCashSignalPolicy,
) -> SignalEvaluationResult | None:
    if source_input.duplicate_of_candidate_id is not None:
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.SUPPRESSED,
            family=OpportunityFamily.HIGH_CASH,
            reason_codes=(ReasonCode.DUPLICATE_SUPPRESSED,),
        )
    if source_input.source_reported_cash_weight is None:
        return blocked_signal_result(
            family=OpportunityFamily.HIGH_CASH,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )
    source_reported_cash_weight = _bounded_optional_weight(
        source_input.source_reported_cash_weight,
        "source_reported_cash_weight",
    )
    if source_reported_cash_weight is None:
        return blocked_signal_result(
            family=OpportunityFamily.HIGH_CASH,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )
    if source_reported_cash_weight < policy.cash_weight_threshold:
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.NOT_ELIGIBLE,
            family=OpportunityFamily.HIGH_CASH,
            reason_codes=(ReasonCode.BELOW_MATERIALITY,),
        )
    return None


def _high_cash_candidate_created_result(
    source_input: HighCashSignalInput,
    policy: HighCashSignalPolicy,
    source_refs: tuple[SourceRef, ...],
) -> SignalEvaluationResult:
    identity = _stable_identity(source_input, policy, source_refs)
    signal = _high_cash_signal(identity, source_input, source_refs)
    lineage = _high_cash_lineage(identity, source_refs)
    evidence_packet = _high_cash_evidence_packet(identity, source_input, source_refs, lineage)
    candidate = _high_cash_candidate(identity, source_input, policy, signal, evidence_packet)
    return SignalEvaluationResult(
        outcome=SignalEvaluationOutcome.CANDIDATE_CREATED,
        family=OpportunityFamily.HIGH_CASH,
        reason_codes=evidence_packet.reason_codes,
        signal=signal,
        candidate=candidate,
    )


def _high_cash_signal(
    identity: OpportunityIdentity,
    source_input: HighCashSignalInput,
    source_refs: tuple[SourceRef, ...],
) -> OpportunitySignal:
    return OpportunitySignal(
        signal_id=identity.signal_id,
        family=OpportunityFamily.HIGH_CASH,
        source_refs=source_refs,
        reason_codes=(ReasonCode.HIGH_CASH_RATIO, ReasonCode.CASH_SOURCE_READY),
        detected_at_utc=source_input.evaluated_at_utc,
    )


def _high_cash_lineage(
    identity: OpportunityIdentity,
    source_refs: tuple[SourceRef, ...],
) -> LineageRef:
    return LineageRef(
        lineage_id=identity.lineage_id,
        source_refs=source_refs,
        content_hash=identity.evidence_fingerprint,
    )


def _high_cash_evidence_packet(
    identity: OpportunityIdentity,
    source_input: HighCashSignalInput,
    source_refs: tuple[SourceRef, ...],
    lineage: LineageRef,
) -> IdeaEvidencePacket:
    return IdeaEvidencePacket(
        evidence_packet_id=identity.evidence_packet_id,
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


def _high_cash_candidate(
    identity: OpportunityIdentity,
    source_input: HighCashSignalInput,
    policy: HighCashSignalPolicy,
    signal: OpportunitySignal,
    evidence_packet: IdeaEvidencePacket,
) -> IdeaCandidate:
    return IdeaCandidate(
        candidate_id=identity.candidate_id,
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
        access_scope=source_input.access_scope,
        created_at_utc=source_input.evaluated_at_utc,
        updated_at_utc=source_input.evaluated_at_utc,
    )


def evaluate_concentration_risk_signal(
    source_input: ConcentrationRiskSignalInput,
    policy: ConcentrationRiskSignalPolicy,
) -> SignalEvaluationResult:
    _validate_concentration_risk_evaluation_time(source_input)
    if pre_source_block := _concentration_risk_pre_source_block(source_input):
        return pre_source_block

    source_refs = _concentration_risk_source_refs(source_input)
    if source_block := _concentration_risk_source_block(source_input, source_refs):
        return source_block
    if materiality_result := _concentration_risk_materiality_result(
        source_input,
        policy,
    ):
        return materiality_result

    return _concentration_risk_candidate_created_result(source_input, policy, source_refs)


def _validate_concentration_risk_evaluation_time(
    source_input: ConcentrationRiskSignalInput,
) -> None:
    if source_input.evaluated_at_utc.tzinfo is None:
        raise ValueError("evaluated_at_utc must be timezone-aware")


def _concentration_risk_pre_source_block(
    source_input: ConcentrationRiskSignalInput,
) -> SignalEvaluationResult | None:
    if not source_input.entitlement_allowed:
        return blocked_signal_result(
            family=OpportunityFamily.CONCENTRATION,
            reason_codes=(ReasonCode.REVIEW_REQUIRED,),
            unsupported_reasons=(UnsupportedEvidenceReason.ENTITLEMENT_DENIED,),
        )
    if source_input.concentration_ref is None:
        return blocked_signal_result(
            family=OpportunityFamily.CONCENTRATION,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )
    return None


def _concentration_risk_source_block(
    source_input: ConcentrationRiskSignalInput,
    source_refs: tuple[SourceRef, ...],
) -> SignalEvaluationResult | None:
    temporal_block = temporal_blocked_signal_result(
        family=OpportunityFamily.CONCENTRATION,
        as_of_date=source_input.as_of_date,
        evaluated_at_utc=source_input.evaluated_at_utc,
        source_refs=source_refs,
    )
    if temporal_block is not None:
        return temporal_block
    if any(source_ref.freshness is not EvidenceFreshness.CURRENT for source_ref in source_refs):
        return blocked_signal_result(
            family=OpportunityFamily.CONCENTRATION,
            reason_codes=(ReasonCode.SOURCE_STALE,),
            unsupported_reasons=(UnsupportedEvidenceReason.STALE_SOURCE,),
        )
    if source_input.issuer_coverage_status is None:
        return blocked_signal_result(
            family=OpportunityFamily.CONCENTRATION,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )
    if source_input.issuer_coverage_status.lower() != "complete":
        return blocked_signal_result(
            family=OpportunityFamily.CONCENTRATION,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.SOURCE_UNCERTIFIED,),
        )
    return None


def _concentration_risk_materiality_result(
    source_input: ConcentrationRiskSignalInput,
    policy: ConcentrationRiskSignalPolicy,
) -> SignalEvaluationResult | None:
    if source_input.duplicate_of_candidate_id is not None:
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.SUPPRESSED,
            family=OpportunityFamily.CONCENTRATION,
            reason_codes=(ReasonCode.DUPLICATE_SUPPRESSED,),
        )

    top_position_weight = _bounded_optional_weight(
        source_input.top_position_weight_current,
        "top_position_weight_current",
    )
    top_issuer_weight = _bounded_optional_weight(
        source_input.top_issuer_weight_current,
        "top_issuer_weight_current",
    )
    if top_position_weight is None and top_issuer_weight is None:
        return blocked_signal_result(
            family=OpportunityFamily.CONCENTRATION,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )
    if _concentration_risk_below_materiality(
        top_position_weight=top_position_weight,
        top_issuer_weight=top_issuer_weight,
        policy=policy,
    ):
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.NOT_ELIGIBLE,
            family=OpportunityFamily.CONCENTRATION,
            reason_codes=(ReasonCode.BELOW_MATERIALITY,),
        )
    return None


def _concentration_risk_below_materiality(
    *,
    top_position_weight: Decimal | None,
    top_issuer_weight: Decimal | None,
    policy: ConcentrationRiskSignalPolicy,
) -> bool:
    position_below = (
        top_position_weight is None or top_position_weight < policy.top_position_weight_threshold
    )
    issuer_below = (
        top_issuer_weight is None or top_issuer_weight < policy.top_issuer_weight_threshold
    )
    return position_below and issuer_below


def _concentration_risk_candidate_created_result(
    source_input: ConcentrationRiskSignalInput,
    policy: ConcentrationRiskSignalPolicy,
    source_refs: tuple[SourceRef, ...],
) -> SignalEvaluationResult:
    identity = _stable_concentration_identity(source_input, policy, source_refs)
    signal = OpportunitySignal(
        signal_id=identity.signal_id,
        family=OpportunityFamily.CONCENTRATION,
        source_refs=source_refs,
        reason_codes=(ReasonCode.CONCENTRATION_ATTENTION,),
        detected_at_utc=source_input.evaluated_at_utc,
    )
    lineage = LineageRef(
        lineage_id=identity.lineage_id,
        source_refs=source_refs,
        content_hash=identity.evidence_fingerprint,
    )
    evidence_packet = IdeaEvidencePacket(
        evidence_packet_id=identity.evidence_packet_id,
        supportability=EvidenceSupportability.READY,
        source_refs=source_refs,
        lineage_ref=lineage,
        reason_codes=(
            ReasonCode.CONCENTRATION_ATTENTION,
            ReasonCode.REVIEW_REQUIRED,
        ),
        created_at_utc=source_input.evaluated_at_utc,
    )
    candidate = IdeaCandidate(
        candidate_id=identity.candidate_id,
        family=OpportunityFamily.CONCENTRATION,
        lifecycle_status=IdeaLifecycleStatus.GENERATED,
        review_posture=ReviewPosture.ADVISOR_REVIEW_REQUIRED,
        evidence_packet=evidence_packet,
        source_signal_ids=(signal.signal_id,),
        score=IdeaScore(
            policy_version=policy.policy_version,
            score=policy.candidate_score,
            reason_codes=(ReasonCode.CONCENTRATION_ATTENTION, ReasonCode.REVIEW_REQUIRED),
        ),
        access_scope=source_input.access_scope,
        created_at_utc=source_input.evaluated_at_utc,
        updated_at_utc=source_input.evaluated_at_utc,
    )
    return SignalEvaluationResult(
        outcome=SignalEvaluationOutcome.CANDIDATE_CREATED,
        family=OpportunityFamily.CONCENTRATION,
        reason_codes=evidence_packet.reason_codes,
        signal=signal,
        candidate=candidate,
    )


def _concentration_risk_source_refs(
    source_input: ConcentrationRiskSignalInput,
) -> tuple[SourceRef, ...]:
    return () if source_input.concentration_ref is None else (source_input.concentration_ref,)


def evaluate_underperformance_signal(
    source_input: UnderperformanceSignalInput,
    policy: UnderperformanceSignalPolicy,
) -> SignalEvaluationResult:
    _validate_underperformance_evaluation_time(source_input)
    if pre_source_block := _underperformance_pre_source_block(source_input):
        return pre_source_block

    source_refs = _underperformance_source_refs(source_input)
    if source_block := _underperformance_source_block(source_input, source_refs):
        return source_block
    if materiality_result := _underperformance_materiality_result(source_input, policy):
        return materiality_result

    return _underperformance_candidate_created_result(source_input, policy, source_refs)


def _validate_underperformance_evaluation_time(
    source_input: UnderperformanceSignalInput,
) -> None:
    validate_timezone_aware_evaluation_time(source_input.evaluated_at_utc)


def _underperformance_pre_source_block(
    source_input: UnderperformanceSignalInput,
) -> SignalEvaluationResult | None:
    if not source_input.entitlement_allowed:
        return blocked_signal_result(
            family=OpportunityFamily.UNDERPERFORMANCE,
            reason_codes=(ReasonCode.REVIEW_REQUIRED,),
            unsupported_reasons=(UnsupportedEvidenceReason.ENTITLEMENT_DENIED,),
        )
    if source_input.performance_ref is None:
        return blocked_signal_result(
            family=OpportunityFamily.UNDERPERFORMANCE,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )
    return None


def _underperformance_source_block(
    source_input: UnderperformanceSignalInput,
    source_refs: tuple[SourceRef, ...],
) -> SignalEvaluationResult | None:
    if not source_refs:
        return blocked_signal_result(
            family=OpportunityFamily.UNDERPERFORMANCE,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )
    temporal_block = temporal_blocked_signal_result(
        family=OpportunityFamily.UNDERPERFORMANCE,
        as_of_date=source_input.as_of_date,
        evaluated_at_utc=source_input.evaluated_at_utc,
        source_refs=source_refs,
    )
    if temporal_block is not None:
        return temporal_block
    if any(source_ref.freshness is not EvidenceFreshness.CURRENT for source_ref in source_refs):
        return blocked_signal_result(
            family=OpportunityFamily.UNDERPERFORMANCE,
            reason_codes=(ReasonCode.SOURCE_STALE,),
            unsupported_reasons=(UnsupportedEvidenceReason.STALE_SOURCE,),
        )
    if not source_input.benchmark_context_available:
        return blocked_signal_result(
            family=OpportunityFamily.UNDERPERFORMANCE,
            reason_codes=(ReasonCode.MISSING_BENCHMARK,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )
    return None


def _underperformance_materiality_result(
    source_input: UnderperformanceSignalInput,
    policy: UnderperformanceSignalPolicy,
) -> SignalEvaluationResult | None:
    if source_input.duplicate_of_candidate_id is not None:
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.SUPPRESSED,
            family=OpportunityFamily.UNDERPERFORMANCE,
            reason_codes=(ReasonCode.DUPLICATE_SUPPRESSED,),
        )
    if source_input.source_reported_active_return is None:
        return blocked_signal_result(
            family=OpportunityFamily.UNDERPERFORMANCE,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )
    active_return = _bounded_underperformance_active_return(
        source_input.source_reported_active_return,
    )
    if active_return > policy.active_return_threshold:
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.NOT_ELIGIBLE,
            family=OpportunityFamily.UNDERPERFORMANCE,
            reason_codes=(ReasonCode.BELOW_MATERIALITY,),
        )
    return None


def _underperformance_candidate_created_result(
    source_input: UnderperformanceSignalInput,
    policy: UnderperformanceSignalPolicy,
    source_refs: tuple[SourceRef, ...],
) -> SignalEvaluationResult:
    identity = _stable_underperformance_identity(source_input, policy, source_refs)
    signal = _underperformance_signal(identity, source_input, source_refs)
    lineage = _underperformance_lineage(identity, source_refs)
    evidence_packet = _underperformance_evidence_packet(
        identity,
        source_input,
        source_refs,
        lineage,
    )
    candidate = _underperformance_candidate(
        identity,
        source_input,
        policy,
        signal,
        evidence_packet,
    )
    return SignalEvaluationResult(
        outcome=SignalEvaluationOutcome.CANDIDATE_CREATED,
        family=OpportunityFamily.UNDERPERFORMANCE,
        reason_codes=evidence_packet.reason_codes,
        signal=signal,
        candidate=candidate,
    )


def _bounded_underperformance_active_return(active_return: Decimal) -> Decimal:
    if active_return < Decimal("-1") or active_return > Decimal("1"):
        raise ValueError("source_reported_active_return must be between -1 and 1")
    return active_return


def _underperformance_signal(
    identity: OpportunityIdentity,
    source_input: UnderperformanceSignalInput,
    source_refs: tuple[SourceRef, ...],
) -> OpportunitySignal:
    return OpportunitySignal(
        signal_id=identity.signal_id,
        family=OpportunityFamily.UNDERPERFORMANCE,
        source_refs=source_refs,
        reason_codes=(ReasonCode.UNDERPERFORMANCE_ATTENTION,),
        detected_at_utc=source_input.evaluated_at_utc,
    )


def _underperformance_lineage(
    identity: OpportunityIdentity,
    source_refs: tuple[SourceRef, ...],
) -> LineageRef:
    return LineageRef(
        lineage_id=identity.lineage_id,
        source_refs=source_refs,
        content_hash=identity.evidence_fingerprint,
    )


def _underperformance_evidence_packet(
    identity: OpportunityIdentity,
    source_input: UnderperformanceSignalInput,
    source_refs: tuple[SourceRef, ...],
    lineage: LineageRef,
) -> IdeaEvidencePacket:
    return IdeaEvidencePacket(
        evidence_packet_id=identity.evidence_packet_id,
        supportability=EvidenceSupportability.READY,
        source_refs=source_refs,
        lineage_ref=lineage,
        reason_codes=(
            ReasonCode.UNDERPERFORMANCE_ATTENTION,
            ReasonCode.REVIEW_REQUIRED,
        ),
        created_at_utc=source_input.evaluated_at_utc,
    )


def _underperformance_candidate(
    identity: OpportunityIdentity,
    source_input: UnderperformanceSignalInput,
    policy: UnderperformanceSignalPolicy,
    signal: OpportunitySignal,
    evidence_packet: IdeaEvidencePacket,
) -> IdeaCandidate:
    return IdeaCandidate(
        candidate_id=identity.candidate_id,
        family=OpportunityFamily.UNDERPERFORMANCE,
        lifecycle_status=IdeaLifecycleStatus.GENERATED,
        review_posture=ReviewPosture.ADVISOR_REVIEW_REQUIRED,
        evidence_packet=evidence_packet,
        source_signal_ids=(signal.signal_id,),
        score=IdeaScore(
            policy_version=policy.policy_version,
            score=policy.candidate_score,
            reason_codes=(ReasonCode.UNDERPERFORMANCE_ATTENTION, ReasonCode.REVIEW_REQUIRED),
        ),
        access_scope=source_input.access_scope,
        created_at_utc=source_input.evaluated_at_utc,
        updated_at_utc=source_input.evaluated_at_utc,
    )


def _underperformance_source_refs(
    source_input: UnderperformanceSignalInput,
) -> tuple[SourceRef, ...]:
    return () if source_input.performance_ref is None else (source_input.performance_ref,)


def evaluate_mandate_health_signal(
    source_input: MandateHealthSignalInput,
    policy: MandateHealthSignalPolicy,
) -> SignalEvaluationResult:
    _validate_mandate_health_evaluation_time(source_input)
    if pre_source_block := _mandate_health_pre_source_block(source_input):
        return pre_source_block

    source_refs = _mandate_health_source_refs(source_input)
    if source_block := _mandate_health_source_block(source_input, source_refs):
        return source_block
    if materiality_result := _mandate_health_materiality_result(source_input, policy):
        return materiality_result

    return _mandate_health_candidate_created_result(source_input, policy, source_refs)


def _validate_mandate_health_evaluation_time(
    source_input: MandateHealthSignalInput,
) -> None:
    validate_timezone_aware_evaluation_time(source_input.evaluated_at_utc)


def _mandate_health_pre_source_block(
    source_input: MandateHealthSignalInput,
) -> SignalEvaluationResult | None:
    if not source_input.entitlement_allowed:
        return blocked_signal_result(
            family=OpportunityFamily.ALLOCATION_DRIFT,
            reason_codes=(ReasonCode.REVIEW_REQUIRED,),
            unsupported_reasons=(UnsupportedEvidenceReason.ENTITLEMENT_DENIED,),
        )
    if source_input.action_register_ref is None:
        return blocked_signal_result(
            family=OpportunityFamily.ALLOCATION_DRIFT,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )
    return None


def _mandate_health_source_block(
    source_input: MandateHealthSignalInput,
    source_refs: tuple[SourceRef, ...],
) -> SignalEvaluationResult | None:
    temporal_block = temporal_blocked_signal_result(
        family=OpportunityFamily.ALLOCATION_DRIFT,
        as_of_date=source_input.as_of_date,
        evaluated_at_utc=source_input.evaluated_at_utc,
        source_refs=source_refs,
    )
    if temporal_block is not None:
        return temporal_block
    if any(source_ref.freshness is not EvidenceFreshness.CURRENT for source_ref in source_refs):
        return blocked_signal_result(
            family=OpportunityFamily.ALLOCATION_DRIFT,
            reason_codes=(ReasonCode.SOURCE_STALE,),
            unsupported_reasons=(UnsupportedEvidenceReason.STALE_SOURCE,),
        )
    if not source_input.portfolio_scope_confirmed:
        return blocked_signal_result(
            family=OpportunityFamily.ALLOCATION_DRIFT,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )
    if source_input.manage_supportability_state is None:
        return blocked_signal_result(
            family=OpportunityFamily.ALLOCATION_DRIFT,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )
    if source_input.manage_supportability_state.lower() != "ready":
        return blocked_signal_result(
            family=OpportunityFamily.ALLOCATION_DRIFT,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.SOURCE_UNCERTIFIED,),
        )
    return None


def _mandate_health_materiality_result(
    source_input: MandateHealthSignalInput,
    policy: MandateHealthSignalPolicy,
) -> SignalEvaluationResult | None:
    if source_input.duplicate_of_candidate_id is not None:
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.SUPPRESSED,
            family=OpportunityFamily.ALLOCATION_DRIFT,
            reason_codes=(ReasonCode.DUPLICATE_SUPPRESSED,),
        )
    if source_input.workflow_decision_count is None or source_input.lineage_edge_count is None:
        return blocked_signal_result(
            family=OpportunityFamily.ALLOCATION_DRIFT,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )
    if source_input.workflow_decision_count < 0:
        raise ValueError("workflow_decision_count must be non-negative")
    if source_input.lineage_edge_count < 0:
        raise ValueError("lineage_edge_count must be non-negative")
    if (
        source_input.workflow_decision_count < policy.minimum_workflow_decision_count
        or source_input.lineage_edge_count < policy.minimum_lineage_edge_count
    ):
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.NOT_ELIGIBLE,
            family=OpportunityFamily.ALLOCATION_DRIFT,
            reason_codes=(ReasonCode.BELOW_MATERIALITY,),
        )
    return None


def _mandate_health_candidate_created_result(
    source_input: MandateHealthSignalInput,
    policy: MandateHealthSignalPolicy,
    source_refs: tuple[SourceRef, ...],
) -> SignalEvaluationResult:
    identity = _stable_mandate_health_identity(source_input, policy, source_refs)
    signal = OpportunitySignal(
        signal_id=f"signal_allocation_drift_{identity}",
        family=OpportunityFamily.ALLOCATION_DRIFT,
        source_refs=source_refs,
        reason_codes=(ReasonCode.ALLOCATION_DRIFT_ATTENTION,),
        detected_at_utc=source_input.evaluated_at_utc,
    )
    lineage = LineageRef(
        lineage_id=f"lineage:lotus-idea:allocation-drift:{identity}",
        source_refs=source_refs,
        content_hash=f"sha256:{identity}",
    )
    evidence_packet = IdeaEvidencePacket(
        evidence_packet_id=f"iep_allocation_drift_{identity}",
        supportability=EvidenceSupportability.READY,
        source_refs=source_refs,
        lineage_ref=lineage,
        reason_codes=(
            ReasonCode.ALLOCATION_DRIFT_ATTENTION,
            ReasonCode.REVIEW_REQUIRED,
        ),
        created_at_utc=source_input.evaluated_at_utc,
    )
    candidate = IdeaCandidate(
        candidate_id=f"idea_allocation_drift_{identity}",
        family=OpportunityFamily.ALLOCATION_DRIFT,
        lifecycle_status=IdeaLifecycleStatus.GENERATED,
        review_posture=ReviewPosture.PM_REVIEW_REQUIRED,
        evidence_packet=evidence_packet,
        source_signal_ids=(signal.signal_id,),
        score=IdeaScore(
            policy_version=policy.policy_version,
            score=policy.candidate_score,
            reason_codes=(ReasonCode.ALLOCATION_DRIFT_ATTENTION, ReasonCode.REVIEW_REQUIRED),
        ),
        access_scope=source_input.access_scope,
        created_at_utc=source_input.evaluated_at_utc,
        updated_at_utc=source_input.evaluated_at_utc,
    )
    return SignalEvaluationResult(
        outcome=SignalEvaluationOutcome.CANDIDATE_CREATED,
        family=OpportunityFamily.ALLOCATION_DRIFT,
        reason_codes=evidence_packet.reason_codes,
        signal=signal,
        candidate=candidate,
    )


def _mandate_health_source_refs(
    source_input: MandateHealthSignalInput,
) -> tuple[SourceRef, ...]:
    return tuple(
        source_ref
        for source_ref in (
            source_input.action_register_ref,
            source_input.mandate_performance_health_ref,
            source_input.mandate_risk_health_ref,
        )
        if source_ref is not None
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
) -> OpportunityIdentity:
    return build_opportunity_identity(
        family=OpportunityFamily.HIGH_CASH,
        opportunity_kind="high_cash",
        as_of_date=source_input.as_of_date,
        access_scope=source_input.access_scope,
        material_facts={
            "as_of_date": source_input.as_of_date.isoformat(),
            "cash_weight": str(source_input.source_reported_cash_weight),
            "policy_version": policy.policy_version,
        },
        source_refs=source_refs,
    )


def _bounded_optional_weight(value: Decimal | None, field_name: str) -> Decimal | None:
    if value is None:
        return None
    if value < Decimal("0") or value > Decimal("1"):
        raise ValueError(f"{field_name} must be between 0 and 1")
    return value


def _stable_concentration_identity(
    source_input: ConcentrationRiskSignalInput,
    policy: ConcentrationRiskSignalPolicy,
    source_refs: tuple[SourceRef, ...],
) -> OpportunityIdentity:
    return build_opportunity_identity(
        family=OpportunityFamily.CONCENTRATION,
        opportunity_kind="concentration",
        as_of_date=source_input.as_of_date,
        access_scope=source_input.access_scope,
        material_facts={
            "as_of_date": source_input.as_of_date.isoformat(),
            "issuer_coverage_status": source_input.issuer_coverage_status,
            "policy_version": policy.policy_version,
            "top_issuer_weight_current": (
                str(source_input.top_issuer_weight_current)
                if source_input.top_issuer_weight_current is not None
                else None
            ),
            "top_position_weight_current": (
                str(source_input.top_position_weight_current)
                if source_input.top_position_weight_current is not None
                else None
            ),
        },
        source_refs=source_refs,
    )


def _stable_underperformance_identity(
    source_input: UnderperformanceSignalInput,
    policy: UnderperformanceSignalPolicy,
    source_refs: tuple[SourceRef, ...],
) -> OpportunityIdentity:
    return build_opportunity_identity(
        family=OpportunityFamily.UNDERPERFORMANCE,
        opportunity_kind="underperformance",
        as_of_date=source_input.as_of_date,
        access_scope=source_input.access_scope,
        material_facts={
            "active_return": str(source_input.source_reported_active_return),
            "as_of_date": source_input.as_of_date.isoformat(),
            "benchmark_context_available": source_input.benchmark_context_available,
            "policy_version": policy.policy_version,
        },
        source_refs=source_refs,
    )


def _stable_mandate_health_identity(
    source_input: MandateHealthSignalInput,
    policy: MandateHealthSignalPolicy,
    source_refs: tuple[SourceRef, ...],
) -> str:
    identity_payload = {
        "as_of_date": source_input.as_of_date.isoformat(),
        "family": OpportunityFamily.ALLOCATION_DRIFT.value,
        "lineage_edge_count": source_input.lineage_edge_count,
        "manage_supportability_state": source_input.manage_supportability_state,
        "policy_version": policy.policy_version,
        "portfolio_scope_confirmed": source_input.portfolio_scope_confirmed,
        "workflow_decision_count": source_input.workflow_decision_count,
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


__all__ = [
    "ConcentrationRiskSignalInput",
    "ConcentrationRiskSignalPolicy",
    "DrawdownReviewSignalInput",
    "DrawdownReviewSignalPolicy",
    "HighCashSignalInput",
    "HighCashSignalPolicy",
    "HighVolatilitySignalInput",
    "HighVolatilitySignalPolicy",
    "MandateHealthSignalInput",
    "MandateHealthSignalPolicy",
    "SignalEvaluationOutcome",
    "SignalEvaluationResult",
    "UnderperformanceSignalInput",
    "UnderperformanceSignalPolicy",
    "blocked_signal_result",
    "evaluate_concentration_risk_signal",
    "evaluate_drawdown_review_signal",
    "evaluate_high_cash_signal",
    "evaluate_high_volatility_signal",
    "evaluate_mandate_health_signal",
    "evaluate_underperformance_signal",
    "temporal_blocked_signal_result",
]
