from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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
from app.domain.opportunity_family_compatibility import DRAWDOWN_REVIEW_FAMILY_COMPATIBILITY
from app.domain.signal_evaluation_common import (
    blocked_signal_result,
    temporal_blocked_signal_result,
)
from app.domain.signal_evaluation_models import (
    DrawdownReviewSignalInput,
    DrawdownReviewSignalPolicy,
    SignalEvaluationOutcome,
    SignalEvaluationResult,
)


@dataclass(frozen=True)
class _DrawdownReviewCandidateInputs:
    source_refs: tuple[SourceRef, ...]
    source_reported_max_drawdown: Decimal


def evaluate_drawdown_review_signal(
    source_input: DrawdownReviewSignalInput,
    policy: DrawdownReviewSignalPolicy,
) -> SignalEvaluationResult:
    family = DRAWDOWN_REVIEW_FAMILY_COMPATIBILITY.family
    _ensure_evaluated_at_utc_timezone_aware(source_input.evaluated_at_utc)
    candidate_inputs = _drawdown_review_candidate_inputs(source_input, policy, family)
    if isinstance(candidate_inputs, SignalEvaluationResult):
        return candidate_inputs
    return _drawdown_review_candidate_result(source_input, policy, family, candidate_inputs)


def _ensure_evaluated_at_utc_timezone_aware(evaluated_at_utc: datetime) -> None:
    if evaluated_at_utc.tzinfo is None or evaluated_at_utc.utcoffset() is None:
        raise ValueError("evaluated_at_utc must be timezone-aware")


def _drawdown_review_candidate_inputs(
    source_input: DrawdownReviewSignalInput,
    policy: DrawdownReviewSignalPolicy,
    family: OpportunityFamily,
) -> _DrawdownReviewCandidateInputs | SignalEvaluationResult:
    source_refs = _drawdown_review_source_refs_or_block(source_input, family)
    if isinstance(source_refs, SignalEvaluationResult):
        return source_refs
    materiality = _drawdown_review_materiality_or_block(source_input, policy, family)
    if isinstance(materiality, SignalEvaluationResult):
        return materiality
    return _DrawdownReviewCandidateInputs(
        source_refs=source_refs,
        source_reported_max_drawdown=materiality,
    )


def _drawdown_review_source_refs_or_block(
    source_input: DrawdownReviewSignalInput,
    family: OpportunityFamily,
) -> tuple[SourceRef, ...] | SignalEvaluationResult:
    if not source_input.entitlement_allowed:
        return blocked_signal_result(
            family=family,
            reason_codes=(ReasonCode.REVIEW_REQUIRED,),
            unsupported_reasons=(UnsupportedEvidenceReason.ENTITLEMENT_DENIED,),
        )
    if source_input.risk_ref is None:
        return _missing_drawdown_review_source(family)
    source_refs = (source_input.risk_ref,)
    temporal_block = temporal_blocked_signal_result(
        family=family,
        as_of_date=source_input.as_of_date,
        evaluated_at_utc=source_input.evaluated_at_utc,
        source_refs=source_refs,
    )
    if temporal_block is not None:
        return temporal_block
    return _drawdown_review_ready_source_refs_or_block(source_input, family, source_refs)


def _drawdown_review_ready_source_refs_or_block(
    source_input: DrawdownReviewSignalInput,
    family: OpportunityFamily,
    source_refs: tuple[SourceRef, ...],
) -> tuple[SourceRef, ...] | SignalEvaluationResult:
    risk_ref = source_refs[0]
    if risk_ref.freshness is not EvidenceFreshness.CURRENT:
        return blocked_signal_result(
            family=family,
            reason_codes=(ReasonCode.SOURCE_STALE,),
            unsupported_reasons=(UnsupportedEvidenceReason.STALE_SOURCE,),
        )
    if source_input.risk_supportability_state is None:
        return _missing_drawdown_review_source(family)
    if source_input.risk_supportability_state.lower() != "ready":
        return blocked_signal_result(
            family=family,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.SOURCE_UNCERTIFIED,),
        )
    return source_refs


def _drawdown_review_materiality_or_block(
    source_input: DrawdownReviewSignalInput,
    policy: DrawdownReviewSignalPolicy,
    family: OpportunityFamily,
) -> Decimal | SignalEvaluationResult:
    if source_input.duplicate_of_candidate_id is not None:
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.SUPPRESSED,
            family=family,
            reason_codes=(ReasonCode.DUPLICATE_SUPPRESSED,),
        )
    source_reported_max_drawdown = source_input.source_reported_max_drawdown
    if source_reported_max_drawdown is None:
        return _missing_drawdown_review_source(family)
    if source_reported_max_drawdown > Decimal("0"):
        raise ValueError("source_reported_max_drawdown must be zero or negative")
    if source_reported_max_drawdown > policy.max_drawdown_threshold:
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.NOT_ELIGIBLE,
            family=family,
            reason_codes=(ReasonCode.BELOW_MATERIALITY,),
        )
    return source_reported_max_drawdown


def _missing_drawdown_review_source(family: OpportunityFamily) -> SignalEvaluationResult:
    return blocked_signal_result(
        family=family,
        reason_codes=(ReasonCode.SOURCE_PARTIAL,),
        unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
    )


def _drawdown_review_candidate_result(
    source_input: DrawdownReviewSignalInput,
    policy: DrawdownReviewSignalPolicy,
    family: OpportunityFamily,
    candidate_inputs: _DrawdownReviewCandidateInputs,
) -> SignalEvaluationResult:
    source_refs = candidate_inputs.source_refs
    identity = _stable_drawdown_review_identity(
        source_input,
        policy,
        source_refs,
        source_reported_max_drawdown=candidate_inputs.source_reported_max_drawdown,
    )
    signal = OpportunitySignal(
        signal_id=f"signal_drawdown_review_{identity}",
        family=family,
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
        family=family,
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
        family=family,
        reason_codes=evidence_packet.reason_codes,
        signal=signal,
        candidate=candidate,
    )


def _stable_drawdown_review_identity(
    source_input: DrawdownReviewSignalInput,
    policy: DrawdownReviewSignalPolicy,
    source_refs: tuple[SourceRef, ...],
    *,
    source_reported_max_drawdown: Decimal,
) -> str:
    identity_payload = {
        "as_of_date": source_input.as_of_date.isoformat(),
        "family": DRAWDOWN_REVIEW_FAMILY_COMPATIBILITY.family.value,
        "policy_version": policy.policy_version,
        "risk_supportability_state": source_input.risk_supportability_state,
        "source_reported_max_drawdown": str(source_reported_max_drawdown),
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
    "evaluate_drawdown_review_signal",
]
