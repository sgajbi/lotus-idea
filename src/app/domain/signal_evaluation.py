from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
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
from app.domain.source_temporal import source_temporal_violation


def blocked_signal_result(
    *,
    family: OpportunityFamily,
    reason_codes: tuple[ReasonCode, ...],
    unsupported_reasons: tuple[UnsupportedEvidenceReason, ...],
) -> SignalEvaluationResult:
    return SignalEvaluationResult(
        outcome=SignalEvaluationOutcome.BLOCKED,
        family=family,
        reason_codes=reason_codes,
        unsupported_reasons=unsupported_reasons,
    )


def temporal_blocked_signal_result(
    *,
    family: OpportunityFamily,
    as_of_date: date,
    evaluated_at_utc: datetime,
    source_refs: tuple[SourceRef, ...],
) -> SignalEvaluationResult | None:
    violation = source_temporal_violation(
        requested_as_of_date=as_of_date,
        evaluated_at_utc=evaluated_at_utc,
        source_refs=source_refs,
    )
    if violation is None:
        return None
    reason_code, unsupported_reason = violation
    return blocked_signal_result(
        family=family,
        reason_codes=(reason_code,),
        unsupported_reasons=(unsupported_reason,),
    )


def evaluate_high_cash_signal(
    source_input: HighCashSignalInput,
    policy: HighCashSignalPolicy,
) -> SignalEvaluationResult:
    if source_input.evaluated_at_utc.tzinfo is None:
        raise ValueError("evaluated_at_utc must be timezone-aware")

    source_refs = _available_source_refs(source_input)
    missing_reasons = _missing_required_sources(source_input)
    if not source_input.entitlement_allowed:
        return blocked_signal_result(
            family=OpportunityFamily.HIGH_CASH,
            reason_codes=(ReasonCode.REVIEW_REQUIRED,),
            unsupported_reasons=(UnsupportedEvidenceReason.ENTITLEMENT_DENIED,),
        )
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
        access_scope=source_input.access_scope,
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


def evaluate_concentration_risk_signal(
    source_input: ConcentrationRiskSignalInput,
    policy: ConcentrationRiskSignalPolicy,
) -> SignalEvaluationResult:
    if source_input.evaluated_at_utc.tzinfo is None:
        raise ValueError("evaluated_at_utc must be timezone-aware")

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
    temporal_block = temporal_blocked_signal_result(
        family=OpportunityFamily.CONCENTRATION,
        as_of_date=source_input.as_of_date,
        evaluated_at_utc=source_input.evaluated_at_utc,
        source_refs=(source_input.concentration_ref,),
    )
    if temporal_block is not None:
        return temporal_block
    if source_input.concentration_ref.freshness is not EvidenceFreshness.CURRENT:
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
    if (
        top_position_weight is None or top_position_weight < policy.top_position_weight_threshold
    ) and (top_issuer_weight is None or top_issuer_weight < policy.top_issuer_weight_threshold):
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.NOT_ELIGIBLE,
            family=OpportunityFamily.CONCENTRATION,
            reason_codes=(ReasonCode.BELOW_MATERIALITY,),
        )

    source_refs = (source_input.concentration_ref,)
    identity = _stable_concentration_identity(source_input, policy, source_refs)
    signal = OpportunitySignal(
        signal_id=f"signal_concentration_{identity}",
        family=OpportunityFamily.CONCENTRATION,
        source_refs=source_refs,
        reason_codes=(ReasonCode.CONCENTRATION_ATTENTION,),
        detected_at_utc=source_input.evaluated_at_utc,
    )
    lineage = LineageRef(
        lineage_id=f"lineage:lotus-idea:concentration:{identity}",
        source_refs=source_refs,
        content_hash=f"sha256:{identity}",
    )
    evidence_packet = IdeaEvidencePacket(
        evidence_packet_id=f"iep_concentration_{identity}",
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
        candidate_id=f"idea_concentration_{identity}",
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


def evaluate_underperformance_signal(
    source_input: UnderperformanceSignalInput,
    policy: UnderperformanceSignalPolicy,
) -> SignalEvaluationResult:
    if source_input.evaluated_at_utc.tzinfo is None:
        raise ValueError("evaluated_at_utc must be timezone-aware")

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
    temporal_block = temporal_blocked_signal_result(
        family=OpportunityFamily.UNDERPERFORMANCE,
        as_of_date=source_input.as_of_date,
        evaluated_at_utc=source_input.evaluated_at_utc,
        source_refs=(source_input.performance_ref,),
    )
    if temporal_block is not None:
        return temporal_block
    if source_input.performance_ref.freshness is not EvidenceFreshness.CURRENT:
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
    if source_input.source_reported_active_return < Decimal(
        "-1"
    ) or source_input.source_reported_active_return > Decimal("1"):
        raise ValueError("source_reported_active_return must be between -1 and 1")
    if source_input.source_reported_active_return > policy.active_return_threshold:
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.NOT_ELIGIBLE,
            family=OpportunityFamily.UNDERPERFORMANCE,
            reason_codes=(ReasonCode.BELOW_MATERIALITY,),
        )

    source_refs = (source_input.performance_ref,)
    identity = _stable_underperformance_identity(source_input, policy, source_refs)
    signal = OpportunitySignal(
        signal_id=f"signal_underperformance_{identity}",
        family=OpportunityFamily.UNDERPERFORMANCE,
        source_refs=source_refs,
        reason_codes=(ReasonCode.UNDERPERFORMANCE_ATTENTION,),
        detected_at_utc=source_input.evaluated_at_utc,
    )
    lineage = LineageRef(
        lineage_id=f"lineage:lotus-idea:underperformance:{identity}",
        source_refs=source_refs,
        content_hash=f"sha256:{identity}",
    )
    evidence_packet = IdeaEvidencePacket(
        evidence_packet_id=f"iep_underperformance_{identity}",
        supportability=EvidenceSupportability.READY,
        source_refs=source_refs,
        lineage_ref=lineage,
        reason_codes=(
            ReasonCode.UNDERPERFORMANCE_ATTENTION,
            ReasonCode.REVIEW_REQUIRED,
        ),
        created_at_utc=source_input.evaluated_at_utc,
    )
    candidate = IdeaCandidate(
        candidate_id=f"idea_underperformance_{identity}",
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
    return SignalEvaluationResult(
        outcome=SignalEvaluationOutcome.CANDIDATE_CREATED,
        family=OpportunityFamily.UNDERPERFORMANCE,
        reason_codes=evidence_packet.reason_codes,
        signal=signal,
        candidate=candidate,
    )


def evaluate_mandate_health_signal(
    source_input: MandateHealthSignalInput,
    policy: MandateHealthSignalPolicy,
) -> SignalEvaluationResult:
    if (
        source_input.evaluated_at_utc.tzinfo is None
        or source_input.evaluated_at_utc.utcoffset() is None
    ):
        raise ValueError("evaluated_at_utc must be timezone-aware")
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
    temporal_block = _mandate_health_temporal_block(source_input)
    if temporal_block is not None:
        return temporal_block
    if source_input.action_register_ref.freshness is not EvidenceFreshness.CURRENT:
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

    source_refs = tuple(
        source_ref
        for source_ref in (
            source_input.action_register_ref,
            source_input.mandate_performance_health_ref,
            source_input.mandate_risk_health_ref,
        )
        if source_ref is not None
    )
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


def _mandate_health_temporal_block(
    source_input: MandateHealthSignalInput,
) -> SignalEvaluationResult | None:
    if source_input.action_register_ref is None:
        return None
    return temporal_blocked_signal_result(
        family=OpportunityFamily.ALLOCATION_DRIFT,
        as_of_date=source_input.as_of_date,
        evaluated_at_utc=source_input.evaluated_at_utc,
        source_refs=(source_input.action_register_ref,),
    )


def evaluate_high_volatility_signal(
    source_input: HighVolatilitySignalInput,
    policy: HighVolatilitySignalPolicy,
) -> SignalEvaluationResult:
    if (
        source_input.evaluated_at_utc.tzinfo is None
        or source_input.evaluated_at_utc.utcoffset() is None
    ):
        raise ValueError("evaluated_at_utc must be timezone-aware")

    if not source_input.entitlement_allowed:
        return blocked_signal_result(
            family=OpportunityFamily.HIGH_VOLATILITY,
            reason_codes=(ReasonCode.REVIEW_REQUIRED,),
            unsupported_reasons=(UnsupportedEvidenceReason.ENTITLEMENT_DENIED,),
        )
    if source_input.risk_ref is None:
        return blocked_signal_result(
            family=OpportunityFamily.HIGH_VOLATILITY,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )
    temporal_block = temporal_blocked_signal_result(
        family=OpportunityFamily.HIGH_VOLATILITY,
        as_of_date=source_input.as_of_date,
        evaluated_at_utc=source_input.evaluated_at_utc,
        source_refs=(source_input.risk_ref,),
    )
    if temporal_block is not None:
        return temporal_block
    if source_input.risk_ref.freshness is not EvidenceFreshness.CURRENT:
        return blocked_signal_result(
            family=OpportunityFamily.HIGH_VOLATILITY,
            reason_codes=(ReasonCode.SOURCE_STALE,),
            unsupported_reasons=(UnsupportedEvidenceReason.STALE_SOURCE,),
        )
    if source_input.risk_supportability_state is None:
        return blocked_signal_result(
            family=OpportunityFamily.HIGH_VOLATILITY,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )
    if source_input.risk_supportability_state.lower() != "ready":
        return blocked_signal_result(
            family=OpportunityFamily.HIGH_VOLATILITY,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.SOURCE_UNCERTIFIED,),
        )
    if source_input.duplicate_of_candidate_id is not None:
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.SUPPRESSED,
            family=OpportunityFamily.HIGH_VOLATILITY,
            reason_codes=(ReasonCode.DUPLICATE_SUPPRESSED,),
        )
    if source_input.source_reported_volatility is None:
        return blocked_signal_result(
            family=OpportunityFamily.HIGH_VOLATILITY,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )
    if source_input.source_reported_volatility < Decimal("0"):
        raise ValueError("source_reported_volatility must be non-negative")
    if source_input.source_reported_volatility < policy.volatility_threshold:
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.NOT_ELIGIBLE,
            family=OpportunityFamily.HIGH_VOLATILITY,
            reason_codes=(ReasonCode.BELOW_MATERIALITY,),
        )

    source_refs = (source_input.risk_ref,)
    identity = _stable_high_volatility_identity(source_input, policy, source_refs)
    signal = OpportunitySignal(
        signal_id=f"signal_high_volatility_{identity}",
        family=OpportunityFamily.HIGH_VOLATILITY,
        source_refs=source_refs,
        reason_codes=(ReasonCode.VOLATILITY_ATTENTION,),
        detected_at_utc=source_input.evaluated_at_utc,
    )
    lineage = LineageRef(
        lineage_id=f"lineage:lotus-idea:high-volatility:{identity}",
        source_refs=source_refs,
        content_hash=f"sha256:{identity}",
    )
    evidence_packet = IdeaEvidencePacket(
        evidence_packet_id=f"iep_high_volatility_{identity}",
        supportability=EvidenceSupportability.READY,
        source_refs=source_refs,
        lineage_ref=lineage,
        reason_codes=(
            ReasonCode.VOLATILITY_ATTENTION,
            ReasonCode.REVIEW_REQUIRED,
        ),
        created_at_utc=source_input.evaluated_at_utc,
    )
    candidate = IdeaCandidate(
        candidate_id=f"idea_high_volatility_{identity}",
        family=OpportunityFamily.HIGH_VOLATILITY,
        lifecycle_status=IdeaLifecycleStatus.GENERATED,
        review_posture=ReviewPosture.ADVISOR_REVIEW_REQUIRED,
        evidence_packet=evidence_packet,
        source_signal_ids=(signal.signal_id,),
        score=IdeaScore(
            policy_version=policy.policy_version,
            score=policy.candidate_score,
            reason_codes=(ReasonCode.VOLATILITY_ATTENTION, ReasonCode.REVIEW_REQUIRED),
        ),
        access_scope=source_input.access_scope,
        created_at_utc=source_input.evaluated_at_utc,
        updated_at_utc=source_input.evaluated_at_utc,
    )
    return SignalEvaluationResult(
        outcome=SignalEvaluationOutcome.CANDIDATE_CREATED,
        family=OpportunityFamily.HIGH_VOLATILITY,
        reason_codes=evidence_packet.reason_codes,
        signal=signal,
        candidate=candidate,
    )


def evaluate_drawdown_review_signal(
    source_input: DrawdownReviewSignalInput,
    policy: DrawdownReviewSignalPolicy,
) -> SignalEvaluationResult:
    if (
        source_input.evaluated_at_utc.tzinfo is None
        or source_input.evaluated_at_utc.utcoffset() is None
    ):
        raise ValueError("evaluated_at_utc must be timezone-aware")

    if not source_input.entitlement_allowed:
        return blocked_signal_result(
            family=OpportunityFamily.HIGH_VOLATILITY,
            reason_codes=(ReasonCode.REVIEW_REQUIRED,),
            unsupported_reasons=(UnsupportedEvidenceReason.ENTITLEMENT_DENIED,),
        )
    if source_input.risk_ref is None:
        return blocked_signal_result(
            family=OpportunityFamily.HIGH_VOLATILITY,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )
    temporal_block = temporal_blocked_signal_result(
        family=OpportunityFamily.HIGH_VOLATILITY,
        as_of_date=source_input.as_of_date,
        evaluated_at_utc=source_input.evaluated_at_utc,
        source_refs=(source_input.risk_ref,),
    )
    if temporal_block is not None:
        return temporal_block
    if source_input.risk_ref.freshness is not EvidenceFreshness.CURRENT:
        return blocked_signal_result(
            family=OpportunityFamily.HIGH_VOLATILITY,
            reason_codes=(ReasonCode.SOURCE_STALE,),
            unsupported_reasons=(UnsupportedEvidenceReason.STALE_SOURCE,),
        )
    if source_input.risk_supportability_state is None:
        return blocked_signal_result(
            family=OpportunityFamily.HIGH_VOLATILITY,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )
    if source_input.risk_supportability_state.lower() != "ready":
        return blocked_signal_result(
            family=OpportunityFamily.HIGH_VOLATILITY,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.SOURCE_UNCERTIFIED,),
        )
    if source_input.duplicate_of_candidate_id is not None:
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.SUPPRESSED,
            family=OpportunityFamily.HIGH_VOLATILITY,
            reason_codes=(ReasonCode.DUPLICATE_SUPPRESSED,),
        )
    if source_input.source_reported_max_drawdown is None:
        return blocked_signal_result(
            family=OpportunityFamily.HIGH_VOLATILITY,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )
    if source_input.source_reported_max_drawdown > Decimal("0"):
        raise ValueError("source_reported_max_drawdown must be zero or negative")
    if source_input.source_reported_max_drawdown > policy.max_drawdown_threshold:
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.NOT_ELIGIBLE,
            family=OpportunityFamily.HIGH_VOLATILITY,
            reason_codes=(ReasonCode.BELOW_MATERIALITY,),
        )

    source_refs = (source_input.risk_ref,)
    identity = _stable_drawdown_review_identity(source_input, policy, source_refs)
    signal = OpportunitySignal(
        signal_id=f"signal_drawdown_review_{identity}",
        family=OpportunityFamily.HIGH_VOLATILITY,
        source_refs=source_refs,
        reason_codes=(ReasonCode.DRAWDOWN_ATTENTION,),
        detected_at_utc=source_input.evaluated_at_utc,
    )
    lineage = LineageRef(
        lineage_id=f"lineage:lotus-idea:drawdown-review:{identity}",
        source_refs=source_refs,
        content_hash=f"sha256:{identity}",
    )
    evidence_packet = IdeaEvidencePacket(
        evidence_packet_id=f"iep_drawdown_review_{identity}",
        supportability=EvidenceSupportability.READY,
        source_refs=source_refs,
        lineage_ref=lineage,
        reason_codes=(
            ReasonCode.DRAWDOWN_ATTENTION,
            ReasonCode.REVIEW_REQUIRED,
        ),
        created_at_utc=source_input.evaluated_at_utc,
    )
    candidate = IdeaCandidate(
        candidate_id=f"idea_drawdown_review_{identity}",
        family=OpportunityFamily.HIGH_VOLATILITY,
        lifecycle_status=IdeaLifecycleStatus.GENERATED,
        review_posture=ReviewPosture.ADVISOR_REVIEW_REQUIRED,
        evidence_packet=evidence_packet,
        source_signal_ids=(signal.signal_id,),
        score=IdeaScore(
            policy_version=policy.policy_version,
            score=policy.candidate_score,
            reason_codes=(ReasonCode.DRAWDOWN_ATTENTION, ReasonCode.REVIEW_REQUIRED),
        ),
        access_scope=source_input.access_scope,
        created_at_utc=source_input.evaluated_at_utc,
        updated_at_utc=source_input.evaluated_at_utc,
    )
    return SignalEvaluationResult(
        outcome=SignalEvaluationOutcome.CANDIDATE_CREATED,
        family=OpportunityFamily.HIGH_VOLATILITY,
        reason_codes=evidence_packet.reason_codes,
        signal=signal,
        candidate=candidate,
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
) -> str:
    identity_payload = {
        "as_of_date": source_input.as_of_date.isoformat(),
        "family": OpportunityFamily.CONCENTRATION.value,
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


def _stable_underperformance_identity(
    source_input: UnderperformanceSignalInput,
    policy: UnderperformanceSignalPolicy,
    source_refs: tuple[SourceRef, ...],
) -> str:
    identity_payload = {
        "active_return": str(source_input.source_reported_active_return),
        "as_of_date": source_input.as_of_date.isoformat(),
        "benchmark_context_available": source_input.benchmark_context_available,
        "family": OpportunityFamily.UNDERPERFORMANCE.value,
        "policy_version": policy.policy_version,
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


def _stable_high_volatility_identity(
    source_input: HighVolatilitySignalInput,
    policy: HighVolatilitySignalPolicy,
    source_refs: tuple[SourceRef, ...],
) -> str:
    identity_payload = {
        "as_of_date": source_input.as_of_date.isoformat(),
        "family": OpportunityFamily.HIGH_VOLATILITY.value,
        "policy_version": policy.policy_version,
        "risk_supportability_state": source_input.risk_supportability_state,
        "source_reported_volatility": str(source_input.source_reported_volatility),
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


def _stable_drawdown_review_identity(
    source_input: DrawdownReviewSignalInput,
    policy: DrawdownReviewSignalPolicy,
    source_refs: tuple[SourceRef, ...],
) -> str:
    identity_payload = {
        "as_of_date": source_input.as_of_date.isoformat(),
        "family": OpportunityFamily.HIGH_VOLATILITY.value,
        "policy_version": policy.policy_version,
        "risk_supportability_state": source_input.risk_supportability_state,
        "source_reported_max_drawdown": str(source_input.source_reported_max_drawdown),
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
]
