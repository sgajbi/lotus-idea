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
from app.domain.signal_evaluation import (
    SignalEvaluationOutcome,
    SignalEvaluationResult,
    temporal_blocked_signal_result,
)
from app.domain.signal_evaluation_common import validate_timezone_aware_evaluation_time


@dataclass(frozen=True)
class MissingBenchmarkSignalPolicy:
    policy_version: str
    candidate_score: Decimal

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise ValueError("policy_version is required")
        if self.candidate_score < Decimal("0") or self.candidate_score > Decimal("100"):
            raise ValueError("candidate_score must be between 0 and 100")


@dataclass(frozen=True)
class MissingBenchmarkSignalInput:
    as_of_date: date
    benchmark_assignment_ref: SourceRef | None
    benchmark_identity_resolved: bool
    assignment_effective_for_as_of_date: bool
    assignment_status: str | None
    assignment_version_present: bool
    evaluated_at_utc: datetime
    entitlement_allowed: bool = True
    access_scope: ReviewAccessScope | None = None
    duplicate_of_candidate_id: str | None = None


def evaluate_missing_benchmark_signal(
    source_input: MissingBenchmarkSignalInput,
    policy: MissingBenchmarkSignalPolicy,
) -> SignalEvaluationResult:
    _validate_missing_benchmark_evaluation_time(source_input)
    non_candidate_result = _missing_benchmark_non_candidate_result(source_input)
    if non_candidate_result is not None:
        return non_candidate_result

    source_refs = _current_benchmark_assignment_refs(source_input)
    identity = _stable_missing_benchmark_identity(source_input, policy, source_refs)
    signal = _missing_benchmark_source_signal(source_input, source_refs, identity)
    evidence_packet = _missing_benchmark_evidence_packet(source_input, source_refs, identity)
    candidate = _missing_benchmark_candidate(
        source_input,
        policy,
        signal,
        evidence_packet,
        identity,
    )
    return SignalEvaluationResult(
        outcome=SignalEvaluationOutcome.CANDIDATE_CREATED,
        family=OpportunityFamily.MISSING_BENCHMARK,
        reason_codes=evidence_packet.reason_codes,
        signal=signal,
        candidate=candidate,
    )


def _validate_missing_benchmark_evaluation_time(
    source_input: MissingBenchmarkSignalInput,
) -> None:
    validate_timezone_aware_evaluation_time(source_input.evaluated_at_utc)


def _missing_benchmark_non_candidate_result(
    source_input: MissingBenchmarkSignalInput,
) -> SignalEvaluationResult | None:
    if not source_input.entitlement_allowed:
        return _blocked(
            reason_codes=(ReasonCode.REVIEW_REQUIRED,),
            unsupported_reasons=(UnsupportedEvidenceReason.ENTITLEMENT_DENIED,),
        )
    benchmark_assignment_ref = source_input.benchmark_assignment_ref
    if benchmark_assignment_ref is None:
        return _blocked(
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )
    temporal_block = temporal_blocked_signal_result(
        family=OpportunityFamily.MISSING_BENCHMARK,
        as_of_date=source_input.as_of_date,
        evaluated_at_utc=source_input.evaluated_at_utc,
        source_refs=(benchmark_assignment_ref,),
    )
    if temporal_block is not None:
        return temporal_block
    if benchmark_assignment_ref.freshness is not EvidenceFreshness.CURRENT:
        return _blocked(
            reason_codes=(ReasonCode.SOURCE_STALE,),
            unsupported_reasons=(UnsupportedEvidenceReason.STALE_SOURCE,),
        )
    if source_input.duplicate_of_candidate_id is not None:
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.SUPPRESSED,
            family=OpportunityFamily.MISSING_BENCHMARK,
            reason_codes=(ReasonCode.DUPLICATE_SUPPRESSED,),
        )
    if _benchmark_assignment_is_ready(source_input):
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.NOT_ELIGIBLE,
            family=OpportunityFamily.MISSING_BENCHMARK,
            reason_codes=(ReasonCode.BELOW_MATERIALITY,),
        )
    return None


def _current_benchmark_assignment_refs(
    source_input: MissingBenchmarkSignalInput,
) -> tuple[SourceRef, ...]:
    if source_input.benchmark_assignment_ref is None:
        raise ValueError("benchmark_assignment_ref is required after blocker classification")
    return (source_input.benchmark_assignment_ref,)


def _missing_benchmark_source_signal(
    source_input: MissingBenchmarkSignalInput,
    source_refs: tuple[SourceRef, ...],
    identity: OpportunityIdentity,
) -> OpportunitySignal:
    return OpportunitySignal(
        signal_id=identity.signal_id,
        family=OpportunityFamily.MISSING_BENCHMARK,
        source_refs=source_refs,
        reason_codes=(ReasonCode.MISSING_BENCHMARK,),
        detected_at_utc=source_input.evaluated_at_utc,
    )


def _missing_benchmark_evidence_packet(
    source_input: MissingBenchmarkSignalInput,
    source_refs: tuple[SourceRef, ...],
    identity: OpportunityIdentity,
) -> IdeaEvidencePacket:
    lineage = LineageRef(
        lineage_id=identity.lineage_id,
        source_refs=source_refs,
        content_hash=identity.evidence_fingerprint,
    )
    return IdeaEvidencePacket(
        evidence_packet_id=identity.evidence_packet_id,
        supportability=EvidenceSupportability.READY,
        source_refs=source_refs,
        lineage_ref=lineage,
        reason_codes=(ReasonCode.MISSING_BENCHMARK, ReasonCode.REVIEW_REQUIRED),
        created_at_utc=source_input.evaluated_at_utc,
    )


def _missing_benchmark_candidate(
    source_input: MissingBenchmarkSignalInput,
    policy: MissingBenchmarkSignalPolicy,
    signal: OpportunitySignal,
    evidence_packet: IdeaEvidencePacket,
    identity: OpportunityIdentity,
) -> IdeaCandidate:
    return IdeaCandidate(
        candidate_id=identity.candidate_id,
        identity=identity.initial_candidate_identity(),
        family=OpportunityFamily.MISSING_BENCHMARK,
        lifecycle_status=IdeaLifecycleStatus.GENERATED,
        review_posture=ReviewPosture.ADVISOR_REVIEW_REQUIRED,
        evidence_packet=evidence_packet,
        source_signal_ids=(signal.signal_id,),
        score=IdeaScore(
            policy_version=policy.policy_version,
            score=policy.candidate_score,
            reason_codes=(ReasonCode.MISSING_BENCHMARK, ReasonCode.REVIEW_REQUIRED),
        ),
        access_scope=source_input.access_scope,
        created_at_utc=source_input.evaluated_at_utc,
        updated_at_utc=source_input.evaluated_at_utc,
    )


def _blocked(
    *,
    reason_codes: tuple[ReasonCode, ...],
    unsupported_reasons: tuple[UnsupportedEvidenceReason, ...],
) -> SignalEvaluationResult:
    return SignalEvaluationResult(
        outcome=SignalEvaluationOutcome.BLOCKED,
        family=OpportunityFamily.MISSING_BENCHMARK,
        reason_codes=reason_codes,
        unsupported_reasons=unsupported_reasons,
    )


def _benchmark_assignment_is_ready(source_input: MissingBenchmarkSignalInput) -> bool:
    return (
        benchmark_assignment_diagnostic(
            benchmark_identity_resolved=source_input.benchmark_identity_resolved,
            assignment_effective_for_as_of_date=source_input.assignment_effective_for_as_of_date,
            assignment_status=source_input.assignment_status,
            assignment_version_present=source_input.assignment_version_present,
        )
        == "core_benchmark_assignment_ready"
    )


def benchmark_assignment_diagnostic(
    *,
    benchmark_identity_resolved: bool,
    assignment_effective_for_as_of_date: bool,
    assignment_status: str | None,
    assignment_version_present: bool,
) -> str:
    if not benchmark_identity_resolved:
        return "core_benchmark_assignment_benchmark_identity_missing"
    if not assignment_effective_for_as_of_date:
        return "core_benchmark_assignment_not_effective_for_as_of_date"
    normalized_status = (assignment_status or "").strip().lower()
    if not normalized_status:
        return "core_benchmark_assignment_status_missing"
    if normalized_status != "active":
        return f"core_benchmark_assignment_{normalized_status}"
    if not assignment_version_present:
        return "core_benchmark_assignment_version_missing"
    return "core_benchmark_assignment_ready"


def _stable_missing_benchmark_identity(
    source_input: MissingBenchmarkSignalInput,
    policy: MissingBenchmarkSignalPolicy,
    source_refs: tuple[SourceRef, ...],
) -> OpportunityIdentity:
    return build_opportunity_identity(
        family=OpportunityFamily.MISSING_BENCHMARK,
        opportunity_kind="missing_benchmark",
        as_of_date=source_input.as_of_date,
        access_scope=source_input.access_scope,
        material_facts={
            "as_of_date": source_input.as_of_date.isoformat(),
            "benchmark_identity_resolved": source_input.benchmark_identity_resolved,
            "assignment_effective_for_as_of_date": (
                source_input.assignment_effective_for_as_of_date
            ),
            "assignment_status": source_input.assignment_status,
            "assignment_version_present": source_input.assignment_version_present,
            "policy_version": policy.policy_version,
        },
        source_refs=source_refs,
    )
