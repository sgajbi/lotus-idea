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
from app.domain.signal_evaluation import SignalEvaluationOutcome, SignalEvaluationResult


@dataclass(frozen=True)
class MissingSuitabilityContextSignalPolicy:
    policy_version: str
    minimum_open_requirement_count: int
    candidate_score: Decimal

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise ValueError("policy_version is required")
        if self.minimum_open_requirement_count < 0:
            raise ValueError("minimum_open_requirement_count must be non-negative")
        if self.candidate_score < Decimal("0") or self.candidate_score > Decimal("100"):
            raise ValueError("candidate_score must be between 0 and 100")


@dataclass(frozen=True)
class MissingSuitabilityContextSignalInput:
    as_of_date: date
    evaluation_status: str | None
    open_requirement_count: int | None
    blocked_requirement_count: int | None
    sign_off_status: str | None
    sign_off_blocker_count: int | None
    client_ready_publication: str | None
    policy_ref: SourceRef | None
    evaluated_at_utc: datetime
    entitlement_allowed: bool = True
    access_scope: ReviewAccessScope | None = None
    duplicate_of_candidate_id: str | None = None


def evaluate_missing_suitability_context_signal(
    source_input: MissingSuitabilityContextSignalInput,
    policy: MissingSuitabilityContextSignalPolicy,
) -> SignalEvaluationResult:
    _validate_evaluated_at(source_input.evaluated_at_utc)
    blocked = _blocking_result(source_input)
    if blocked is not None:
        return blocked
    _validate_counts(source_input)
    if source_input.duplicate_of_candidate_id is not None:
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.SUPPRESSED,
            family=OpportunityFamily.MISSING_SUITABILITY_CONTEXT,
            reason_codes=(ReasonCode.DUPLICATE_SUPPRESSED,),
        )
    if not _review_required(source_input, policy):
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.NOT_ELIGIBLE,
            family=OpportunityFamily.MISSING_SUITABILITY_CONTEXT,
            reason_codes=(ReasonCode.BELOW_MATERIALITY,),
        )

    return _candidate_result(source_input, policy)


def _validate_evaluated_at(evaluated_at_utc: datetime) -> None:
    if evaluated_at_utc.tzinfo is None or evaluated_at_utc.utcoffset() is None:
        raise ValueError("evaluated_at_utc must be timezone-aware")


def _blocking_result(
    source_input: MissingSuitabilityContextSignalInput,
) -> SignalEvaluationResult | None:
    family = OpportunityFamily.MISSING_SUITABILITY_CONTEXT
    if not source_input.entitlement_allowed:
        return _blocked(
            family=family,
            reason_codes=(ReasonCode.REVIEW_REQUIRED,),
            unsupported_reasons=(UnsupportedEvidenceReason.ENTITLEMENT_DENIED,),
        )
    if source_input.policy_ref is None:
        return _blocked(
            family=family,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )
    if source_input.policy_ref.freshness is not EvidenceFreshness.CURRENT:
        return _blocked(
            family=family,
            reason_codes=(ReasonCode.SOURCE_STALE,),
            unsupported_reasons=(UnsupportedEvidenceReason.STALE_SOURCE,),
        )
    if source_input.client_ready_publication is None:
        return _blocked(
            family=family,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )
    if source_input.client_ready_publication.upper() != "BLOCKED":
        return _blocked(
            family=family,
            reason_codes=(ReasonCode.REVIEW_REQUIRED,),
            unsupported_reasons=(UnsupportedEvidenceReason.SOURCE_UNCERTIFIED,),
        )
    if source_input.evaluation_status is None or source_input.sign_off_status is None:
        return _blocked(
            family=family,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )
    if (
        source_input.open_requirement_count is None
        or source_input.blocked_requirement_count is None
        or source_input.sign_off_blocker_count is None
    ):
        return _blocked(
            family=family,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )
    return None


def _validate_counts(source_input: MissingSuitabilityContextSignalInput) -> None:
    for field_name, value in (
        ("open_requirement_count", source_input.open_requirement_count),
        ("blocked_requirement_count", source_input.blocked_requirement_count),
        ("sign_off_blocker_count", source_input.sign_off_blocker_count),
    ):
        if value is None:
            raise ValueError(f"{field_name} must be available after blocking validation")
        if value < 0:
            raise ValueError(f"{field_name} must be non-negative")


def _review_required(
    source_input: MissingSuitabilityContextSignalInput,
    policy: MissingSuitabilityContextSignalPolicy,
) -> bool:
    assert source_input.evaluation_status is not None
    assert source_input.sign_off_status is not None
    assert source_input.open_requirement_count is not None
    assert source_input.blocked_requirement_count is not None
    assert source_input.sign_off_blocker_count is not None
    return (
        source_input.evaluation_status.upper() in {"PENDING_REVIEW", "BLOCKED"}
        or source_input.sign_off_status.upper() in {"PENDING_REVIEW", "BLOCKED"}
        or source_input.open_requirement_count >= policy.minimum_open_requirement_count
        or source_input.blocked_requirement_count > 0
        or source_input.sign_off_blocker_count > 0
    )


def _candidate_result(
    source_input: MissingSuitabilityContextSignalInput,
    policy: MissingSuitabilityContextSignalPolicy,
) -> SignalEvaluationResult:
    assert source_input.policy_ref is not None
    source_refs = (source_input.policy_ref,)
    identity = _stable_identity(source_input, policy, source_refs)
    signal = OpportunitySignal(
        signal_id=f"signal_missing_suitability_context_{identity}",
        family=OpportunityFamily.MISSING_SUITABILITY_CONTEXT,
        source_refs=source_refs,
        reason_codes=(ReasonCode.SUITABILITY_CONTEXT_MISSING,),
        detected_at_utc=source_input.evaluated_at_utc,
    )
    lineage = LineageRef(
        lineage_id=f"lineage:lotus-idea:missing-suitability-context:{identity}",
        source_refs=source_refs,
        content_hash=f"sha256:{identity}",
    )
    evidence_packet = IdeaEvidencePacket(
        evidence_packet_id=f"iep_missing_suitability_context_{identity}",
        supportability=EvidenceSupportability.READY,
        source_refs=source_refs,
        lineage_ref=lineage,
        reason_codes=(
            ReasonCode.SUITABILITY_CONTEXT_MISSING,
            ReasonCode.REVIEW_REQUIRED,
        ),
        created_at_utc=source_input.evaluated_at_utc,
    )
    candidate = IdeaCandidate(
        candidate_id=f"idea_missing_suitability_context_{identity}",
        family=OpportunityFamily.MISSING_SUITABILITY_CONTEXT,
        lifecycle_status=IdeaLifecycleStatus.GENERATED,
        review_posture=ReviewPosture.COMPLIANCE_REVIEW_REQUIRED,
        evidence_packet=evidence_packet,
        source_signal_ids=(signal.signal_id,),
        score=IdeaScore(
            policy_version=policy.policy_version,
            score=policy.candidate_score,
            reason_codes=(ReasonCode.SUITABILITY_CONTEXT_MISSING, ReasonCode.REVIEW_REQUIRED),
        ),
        access_scope=source_input.access_scope,
        created_at_utc=source_input.evaluated_at_utc,
        updated_at_utc=source_input.evaluated_at_utc,
    )
    return SignalEvaluationResult(
        outcome=SignalEvaluationOutcome.CANDIDATE_CREATED,
        family=OpportunityFamily.MISSING_SUITABILITY_CONTEXT,
        reason_codes=evidence_packet.reason_codes,
        signal=signal,
        candidate=candidate,
    )


def _blocked(
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


def _stable_identity(
    source_input: MissingSuitabilityContextSignalInput,
    policy: MissingSuitabilityContextSignalPolicy,
    source_refs: tuple[SourceRef, ...],
) -> str:
    identity_payload = {
        "as_of_date": source_input.as_of_date.isoformat(),
        "blocked_requirement_count": source_input.blocked_requirement_count,
        "client_ready_publication": source_input.client_ready_publication,
        "evaluation_status": source_input.evaluation_status,
        "family": OpportunityFamily.MISSING_SUITABILITY_CONTEXT.value,
        "open_requirement_count": source_input.open_requirement_count,
        "policy_version": policy.policy_version,
        "sign_off_blocker_count": source_input.sign_off_blocker_count,
        "sign_off_status": source_input.sign_off_status,
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
