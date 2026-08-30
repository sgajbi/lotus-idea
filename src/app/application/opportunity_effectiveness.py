from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_EVEN
from enum import StrEnum
import hashlib
import json
from typing import Any, Iterable, Mapping

from app.domain.conversion_governance import GovernedConversionIntent, current_conversion_outcome
from app.domain.downstream_submission import (
    DownstreamSubmissionAuditAction,
    DownstreamSubmissionPosture,
)
from app.domain.feedback_taxonomy import FeedbackReason
from app.domain.ideas import (
    CandidateChangeReason,
    ConversionOutcomeStatus,
    EvidenceFreshness,
    EvidenceSupportability,
    OpportunityFamily,
    SuppressionReason,
)
from app.domain.persistence_models import CandidatePersistenceRecord, IdeaRepositorySnapshot
from app.domain.review_governance import (
    GovernedFeedbackEvent,
    GovernedReviewDecision,
    ReviewAction,
)
from app.domain.review_queue import priority_bucket_for_score
from app.ports.idea_repository import OpportunityEffectivenessRepositorySummary


OPPORTUNITY_EFFECTIVENESS_POLICY_VERSION = "idea-opportunity-effectiveness-v1"
OPPORTUNITY_EFFECTIVENESS_SCHEMA_VERSION = "lotus-idea.opportunity-effectiveness.v1"
MAX_EFFECTIVENESS_OPPORTUNITIES = 10_000
RATE_QUANTUM = Decimal("0.000001")


class OpportunityEffectivenessScopeError(ValueError):
    pass


class OpportunityEffectivenessBoundExceeded(ValueError):
    pass


class OpportunityEffectivenessDataError(ValueError):
    pass


class PresentationMeasurementStatus(StrEnum):
    UNAVAILABLE_NO_GOVERNED_PRESENTATION_RECEIPTS = "unavailable_no_governed_presentation_receipts"


class DownstreamOutcomePosture(StrEnum):
    NOT_REPORTED = "not_reported"
    REQUESTED = "requested"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    FAILED = "failed"
    COMPLETED = "completed"


@dataclass(frozen=True)
class EffectivenessRate:
    numerator: int
    denominator: int
    value: Decimal | None

    def to_payload(self) -> dict[str, Any]:
        return {
            "numerator": self.numerator,
            "denominator": self.denominator,
            "value": str(self.value) if self.value is not None else None,
            "zeroDenominatorBehavior": "null",
        }


@dataclass(frozen=True)
class EffectivenessDuration:
    observation_count: int
    minimum_seconds: Decimal | None
    p50_seconds: Decimal | None
    p95_seconds: Decimal | None
    maximum_seconds: Decimal | None

    def to_payload(self) -> dict[str, Any]:
        return {
            "observationCount": self.observation_count,
            "minimumSeconds": _decimal_payload(self.minimum_seconds),
            "p50Seconds": _decimal_payload(self.p50_seconds),
            "p95Seconds": _decimal_payload(self.p95_seconds),
            "maximumSeconds": _decimal_payload(self.maximum_seconds),
        }


@dataclass(frozen=True)
class EffectivenessDimensionCount:
    value: str
    count: int

    def to_payload(self) -> dict[str, Any]:
        return {"value": self.value, "count": self.count}


@dataclass(frozen=True)
class OpportunityEffectivenessSnapshot:
    window_start_utc: datetime
    window_end_utc: datetime
    evaluated_at_utc: datetime
    generated_opportunity_count: int
    reviewed_opportunity_count: int
    feedback_opportunity_count: int
    conversion_opportunity_count: int
    conversion_intent_count: int
    stale_evidence_opportunity_count: int
    unavailable_evidence_opportunity_count: int
    unsupported_evidence_opportunity_count: int
    suppressed_opportunity_count: int
    duplicate_suppressed_opportunity_count: int
    recurrent_opportunity_count: int
    recurrent_detection_count: int
    reconciled_submission_count: int
    presentation_measurement_status: PresentationMeasurementStatus
    presented_opportunity_count: int | None
    top_ranked_accepted_opportunity_count: int | None
    family_counts: tuple[EffectivenessDimensionCount, ...]
    score_band_counts: tuple[EffectivenessDimensionCount, ...]
    latest_review_action_counts: tuple[EffectivenessDimensionCount, ...]
    feedback_reason_counts: tuple[EffectivenessDimensionCount, ...]
    current_downstream_outcome_counts: tuple[EffectivenessDimensionCount, ...]
    downstream_submission_posture_counts: tuple[EffectivenessDimensionCount, ...]
    review_rate: EffectivenessRate
    approval_rate: EffectivenessRate
    rejection_rate: EffectivenessRate
    suppression_rate: EffectivenessRate
    feedback_rate: EffectivenessRate
    conversion_rate: EffectivenessRate
    downstream_accepted_rate: EffectivenessRate
    downstream_rejected_rate: EffectivenessRate
    downstream_uncertain_rate: EffectivenessRate
    detection_to_review: EffectivenessDuration
    approval_to_conversion: EffectivenessDuration
    snapshot_digest: str

    def to_payload(self) -> dict[str, Any]:
        return {
            **_snapshot_payload_without_digest(self),
            "snapshotDigest": self.snapshot_digest,
        }


@dataclass(frozen=True)
class _EffectivenessMeasures:
    latest_review_action_counts: Counter[str]
    feedback_reason_counts: Counter[str]
    current_downstream_outcome_counts: Counter[str]
    reviewed_opportunity_count: int
    feedback_opportunity_count: int
    conversion_opportunity_count: int
    conversion_intent_count: int
    suppressed_opportunity_count: int
    duplicate_suppressed_opportunity_count: int
    recurrent_opportunity_count: int
    recurrent_detection_count: int
    detection_to_review_seconds: tuple[Decimal, ...]
    approval_to_conversion_seconds: tuple[Decimal, ...]
    cohort_intent_ids: frozenset[str]


def build_opportunity_effectiveness_snapshot(
    snapshot: IdeaRepositorySnapshot,
    *,
    tenant_id: str,
    window_start_utc: datetime,
    window_end_utc: datetime,
    evaluated_at_utc: datetime,
    max_opportunities: int = MAX_EFFECTIVENESS_OPPORTUNITIES,
) -> OpportunityEffectivenessSnapshot:
    _validate_scope(
        tenant_id=tenant_id,
        window_start_utc=window_start_utc,
        window_end_utc=window_end_utc,
        evaluated_at_utc=evaluated_at_utc,
        max_opportunities=max_opportunities,
    )
    records = _cohort_records(
        snapshot,
        tenant_id=tenant_id,
        window_start_utc=window_start_utc,
        window_end_utc=window_end_utc,
        max_opportunities=max_opportunities,
    )
    summary = _in_memory_repository_summary(
        snapshot,
        records=records,
        evaluated_at_utc=evaluated_at_utc,
    )
    return build_opportunity_effectiveness_snapshot_from_summary(
        summary,
        tenant_id=tenant_id,
        window_start_utc=window_start_utc,
        window_end_utc=window_end_utc,
        evaluated_at_utc=evaluated_at_utc,
        max_opportunities=max_opportunities,
    )


def build_opportunity_effectiveness_snapshot_from_summary(
    summary: OpportunityEffectivenessRepositorySummary,
    *,
    tenant_id: str,
    window_start_utc: datetime,
    window_end_utc: datetime,
    evaluated_at_utc: datetime,
    max_opportunities: int = MAX_EFFECTIVENESS_OPPORTUNITIES,
) -> OpportunityEffectivenessSnapshot:
    """Apply the versioned methodology to privacy-safe repository aggregate facts."""

    _validate_scope(
        tenant_id=tenant_id,
        window_start_utc=window_start_utc,
        window_end_utc=window_end_utc,
        evaluated_at_utc=evaluated_at_utc,
        max_opportunities=max_opportunities,
    )
    _validate_repository_summary(summary, max_opportunities=max_opportunities)
    approved_count = _count(
        summary.latest_review_action_counts,
        ReviewAction.APPROVE_FOR_CONVERSION.value,
    )
    rejected_count = _count(summary.latest_review_action_counts, ReviewAction.REJECT.value)
    accepted_outcome_count = sum(
        _count(summary.current_downstream_outcome_counts, status.value)
        for status in (ConversionOutcomeStatus.ACCEPTED, ConversionOutcomeStatus.COMPLETED)
    )
    rejected_outcome_count = _count(
        summary.current_downstream_outcome_counts,
        ConversionOutcomeStatus.REJECTED.value,
    )
    uncertain_outcome_count = sum(
        _count(summary.current_downstream_outcome_counts, value)
        for value in (
            DownstreamOutcomePosture.NOT_REPORTED.value,
            ConversionOutcomeStatus.REQUESTED.value,
        )
    )
    provisional = OpportunityEffectivenessSnapshot(
        window_start_utc=window_start_utc,
        window_end_utc=window_end_utc,
        evaluated_at_utc=evaluated_at_utc,
        generated_opportunity_count=summary.generated_opportunity_count,
        reviewed_opportunity_count=summary.reviewed_opportunity_count,
        feedback_opportunity_count=summary.feedback_opportunity_count,
        conversion_opportunity_count=summary.conversion_opportunity_count,
        conversion_intent_count=summary.conversion_intent_count,
        stale_evidence_opportunity_count=summary.stale_evidence_opportunity_count,
        unavailable_evidence_opportunity_count=summary.unavailable_evidence_opportunity_count,
        unsupported_evidence_opportunity_count=summary.unsupported_evidence_opportunity_count,
        suppressed_opportunity_count=summary.suppressed_opportunity_count,
        duplicate_suppressed_opportunity_count=summary.duplicate_suppressed_opportunity_count,
        recurrent_opportunity_count=summary.recurrent_opportunity_count,
        recurrent_detection_count=summary.recurrent_detection_count,
        reconciled_submission_count=summary.reconciled_submission_count,
        presentation_measurement_status=(
            PresentationMeasurementStatus.UNAVAILABLE_NO_GOVERNED_PRESENTATION_RECEIPTS
        ),
        presented_opportunity_count=None,
        top_ranked_accepted_opportunity_count=None,
        family_counts=_dimension_counts(
            Counter(summary.family_counts),
            (family.value for family in OpportunityFamily),
        ),
        score_band_counts=_dimension_counts(
            Counter(summary.score_band_counts),
            (*("critical", "high", "standard", "watchlist"), "unranked"),
        ),
        latest_review_action_counts=_dimension_counts(
            Counter(summary.latest_review_action_counts),
            (action.value for action in ReviewAction),
        ),
        feedback_reason_counts=_dimension_counts(
            Counter(summary.feedback_reason_counts),
            (reason.value for reason in FeedbackReason),
        ),
        current_downstream_outcome_counts=_dimension_counts(
            Counter(summary.current_downstream_outcome_counts),
            (posture.value for posture in DownstreamOutcomePosture),
        ),
        downstream_submission_posture_counts=_dimension_counts(
            Counter(summary.downstream_submission_posture_counts),
            (posture.value for posture in DownstreamSubmissionPosture),
        ),
        review_rate=_rate(summary.reviewed_opportunity_count, summary.generated_opportunity_count),
        approval_rate=_rate(approved_count, summary.reviewed_opportunity_count),
        rejection_rate=_rate(rejected_count, summary.reviewed_opportunity_count),
        suppression_rate=_rate(
            summary.suppressed_opportunity_count,
            summary.reviewed_opportunity_count,
        ),
        feedback_rate=_rate(
            summary.feedback_opportunity_count,
            summary.reviewed_opportunity_count,
        ),
        conversion_rate=_rate(summary.conversion_opportunity_count, approved_count),
        downstream_accepted_rate=_rate(
            accepted_outcome_count,
            summary.conversion_intent_count,
        ),
        downstream_rejected_rate=_rate(
            rejected_outcome_count,
            summary.conversion_intent_count,
        ),
        downstream_uncertain_rate=_rate(
            uncertain_outcome_count,
            summary.conversion_intent_count,
        ),
        detection_to_review=_duration(summary.detection_to_review_seconds),
        approval_to_conversion=_duration(summary.approval_to_conversion_seconds),
        snapshot_digest="",
    )
    payload = _snapshot_payload_without_digest(provisional)
    digest = (
        "sha256:"
        + hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
    )
    return replace(provisional, snapshot_digest=digest)


def _validate_scope(
    *,
    tenant_id: str,
    window_start_utc: datetime,
    window_end_utc: datetime,
    evaluated_at_utc: datetime,
    max_opportunities: int,
) -> None:
    if not tenant_id.strip():
        raise OpportunityEffectivenessScopeError("tenant_id is required")
    for field_name, value in (
        ("window_start_utc", window_start_utc),
        ("window_end_utc", window_end_utc),
        ("evaluated_at_utc", evaluated_at_utc),
    ):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{field_name} must be timezone-aware")
    if window_start_utc >= window_end_utc:
        raise ValueError("window_start_utc must precede window_end_utc")
    if window_end_utc > evaluated_at_utc:
        raise ValueError("window_end_utc must not be after evaluated_at_utc")
    if max_opportunities < 1 or max_opportunities > MAX_EFFECTIVENESS_OPPORTUNITIES:
        raise ValueError(
            f"max_opportunities must be between 1 and {MAX_EFFECTIVENESS_OPPORTUNITIES}"
        )


def _cohort_records(
    snapshot: IdeaRepositorySnapshot,
    *,
    tenant_id: str,
    window_start_utc: datetime,
    window_end_utc: datetime,
    max_opportunities: int,
) -> tuple[CandidatePersistenceRecord, ...]:
    records: list[CandidatePersistenceRecord] = []
    business_identity_ids: set[str] = set()
    for record in sorted(
        snapshot.candidate_records.values(),
        key=lambda item: item.candidate.candidate_id,
    ):
        candidate = record.candidate
        if not window_start_utc <= candidate.created_at_utc < window_end_utc:
            continue
        if candidate.access_scope is None:
            raise OpportunityEffectivenessScopeError(
                "opportunity effectiveness requires access scope on every cohort candidate"
            )
        if candidate.access_scope.tenant_id != tenant_id:
            continue
        if candidate.identity.business_identity_id in business_identity_ids:
            raise OpportunityEffectivenessDataError(
                "opportunity effectiveness requires one record per business identity"
            )
        business_identity_ids.add(candidate.identity.business_identity_id)
        records.append(record)
        if len(records) > max_opportunities:
            raise OpportunityEffectivenessBoundExceeded(
                f"opportunity effectiveness exceeds the {max_opportunities} opportunity bound"
            )
    return tuple(records)


def _in_memory_repository_summary(
    snapshot: IdeaRepositorySnapshot,
    *,
    records: tuple[CandidatePersistenceRecord, ...],
    evaluated_at_utc: datetime,
) -> OpportunityEffectivenessRepositorySummary:
    measures = _effectiveness_measures(records, evaluated_at_utc=evaluated_at_utc)
    downstream_postures, reconciled_count = _downstream_submission_measures(
        snapshot,
        cohort_intent_ids=measures.cohort_intent_ids,
        evaluated_at_utc=evaluated_at_utc,
    )
    return OpportunityEffectivenessRepositorySummary(
        generated_opportunity_count=len(records),
        reviewed_opportunity_count=measures.reviewed_opportunity_count,
        feedback_opportunity_count=measures.feedback_opportunity_count,
        conversion_opportunity_count=measures.conversion_opportunity_count,
        conversion_intent_count=measures.conversion_intent_count,
        stale_evidence_opportunity_count=sum(_has_stale_evidence(record) for record in records),
        unavailable_evidence_opportunity_count=sum(
            _has_unavailable_evidence(record) for record in records
        ),
        unsupported_evidence_opportunity_count=sum(
            record.candidate.evidence_packet.supportability is not EvidenceSupportability.READY
            for record in records
        ),
        suppressed_opportunity_count=measures.suppressed_opportunity_count,
        duplicate_suppressed_opportunity_count=measures.duplicate_suppressed_opportunity_count,
        recurrent_opportunity_count=measures.recurrent_opportunity_count,
        recurrent_detection_count=measures.recurrent_detection_count,
        reconciled_submission_count=reconciled_count,
        family_counts=Counter(record.candidate.family.value for record in records),
        score_band_counts=Counter(_score_band(record) for record in records),
        latest_review_action_counts=measures.latest_review_action_counts,
        feedback_reason_counts=measures.feedback_reason_counts,
        current_downstream_outcome_counts=measures.current_downstream_outcome_counts,
        downstream_submission_posture_counts=downstream_postures,
        detection_to_review_seconds=measures.detection_to_review_seconds,
        approval_to_conversion_seconds=measures.approval_to_conversion_seconds,
    )


def _validate_repository_summary(
    summary: OpportunityEffectivenessRepositorySummary,
    *,
    max_opportunities: int,
) -> None:
    if summary.generated_opportunity_count > max_opportunities:
        raise OpportunityEffectivenessBoundExceeded(
            f"opportunity effectiveness exceeds the {max_opportunities} opportunity bound"
        )
    scalar_counts = (
        summary.generated_opportunity_count,
        summary.reviewed_opportunity_count,
        summary.feedback_opportunity_count,
        summary.conversion_opportunity_count,
        summary.conversion_intent_count,
        summary.stale_evidence_opportunity_count,
        summary.unavailable_evidence_opportunity_count,
        summary.unsupported_evidence_opportunity_count,
        summary.suppressed_opportunity_count,
        summary.duplicate_suppressed_opportunity_count,
        summary.recurrent_opportunity_count,
        summary.recurrent_detection_count,
        summary.reconciled_submission_count,
    )
    dimension_counts = (
        *summary.family_counts.values(),
        *summary.score_band_counts.values(),
        *summary.latest_review_action_counts.values(),
        *summary.feedback_reason_counts.values(),
        *summary.current_downstream_outcome_counts.values(),
        *summary.downstream_submission_posture_counts.values(),
    )
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in (*scalar_counts, *dimension_counts)
    ):
        raise OpportunityEffectivenessDataError(
            "opportunity effectiveness repository summary contains an invalid count"
        )
    if any(
        value < 0
        for value in (*summary.detection_to_review_seconds, *summary.approval_to_conversion_seconds)
    ):
        raise OpportunityEffectivenessDataError(
            "opportunity effectiveness repository summary contains a negative duration"
        )


def _count(counts: Mapping[str, int], value: str) -> int:
    return counts.get(value, 0)


def _effectiveness_measures(
    records: tuple[CandidatePersistenceRecord, ...],
    *,
    evaluated_at_utc: datetime,
) -> _EffectivenessMeasures:
    review_actions: Counter[str] = Counter()
    feedback_reasons: Counter[str] = Counter()
    downstream_outcomes: Counter[str] = Counter()
    reviewed_count = 0
    feedback_count = 0
    conversion_count = 0
    conversion_intent_count = 0
    suppressed_count = 0
    duplicate_suppressed_count = 0
    recurrent_count = 0
    recurrent_detection_count = 0
    detection_to_review: list[Decimal] = []
    approval_to_conversion: list[Decimal] = []
    cohort_intent_ids: set[str] = set()

    for record in records:
        reviews = tuple(
            decision
            for decision in record.review_decisions
            if decision.decided_at_utc <= evaluated_at_utc
        )
        feedback = tuple(
            event
            for event in record.feedback_events
            if event.feedback.recorded_at_utc <= evaluated_at_utc
        )
        intents = tuple(
            intent
            for intent in record.conversion_intents
            if intent.intent.requested_at_utc <= evaluated_at_utc
        )
        _validate_event_times(record, reviews=reviews, feedback=feedback, intents=intents)
        latest_review = _latest_review(reviews)
        if latest_review is not None:
            reviewed_count += 1
            review_actions[latest_review.action.value] += 1
            detection_to_review.append(
                _seconds(latest_review.decided_at_utc - record.candidate.created_at_utc)
            )
            if latest_review.action is ReviewAction.SUPPRESS:
                suppressed_count += 1
                if latest_review.suppression_reason is SuppressionReason.DUPLICATE:
                    duplicate_suppressed_count += 1
        elif record.candidate.suppression_reason is not None:
            suppressed_count += 1
            if record.candidate.suppression_reason is SuppressionReason.DUPLICATE:
                duplicate_suppressed_count += 1
        if feedback:
            feedback_count += 1
            feedback_reasons.update(event.feedback.reason.value for event in feedback)
        if intents:
            conversion_count += 1
            conversion_intent_count += len(intents)
            cohort_intent_ids.update(intent.intent.conversion_intent_id for intent in intents)
            approval = _first_approval(reviews)
            if approval is not None:
                first_intent = min(intents, key=lambda item: item.intent.requested_at_utc)
                if first_intent.intent.requested_at_utc < approval.decided_at_utc:
                    raise OpportunityEffectivenessDataError(
                        "conversion intent precedes its governed approval"
                    )
                approval_to_conversion.append(
                    _seconds(first_intent.intent.requested_at_utc - approval.decided_at_utc)
                )
        _measure_current_outcomes(
            record,
            intents=intents,
            evaluated_at_utc=evaluated_at_utc,
            counts=downstream_outcomes,
        )
        recurrent_events = sum(
            entry.change_reason is CandidateChangeReason.RECURRENT_CONDITION
            and entry.recorded_at_utc <= evaluated_at_utc
            for entry in record.version_history
        )
        if recurrent_events:
            recurrent_count += 1
            recurrent_detection_count += recurrent_events

    return _EffectivenessMeasures(
        latest_review_action_counts=review_actions,
        feedback_reason_counts=feedback_reasons,
        current_downstream_outcome_counts=downstream_outcomes,
        reviewed_opportunity_count=reviewed_count,
        feedback_opportunity_count=feedback_count,
        conversion_opportunity_count=conversion_count,
        conversion_intent_count=conversion_intent_count,
        suppressed_opportunity_count=suppressed_count,
        duplicate_suppressed_opportunity_count=duplicate_suppressed_count,
        recurrent_opportunity_count=recurrent_count,
        recurrent_detection_count=recurrent_detection_count,
        detection_to_review_seconds=tuple(detection_to_review),
        approval_to_conversion_seconds=tuple(approval_to_conversion),
        cohort_intent_ids=frozenset(cohort_intent_ids),
    )


def _validate_event_times(
    record: CandidatePersistenceRecord,
    *,
    reviews: tuple[GovernedReviewDecision, ...],
    feedback: tuple[GovernedFeedbackEvent, ...],
    intents: tuple[GovernedConversionIntent, ...],
) -> None:
    created_at = record.candidate.created_at_utc
    event_times = (
        *(decision.decided_at_utc for decision in reviews),
        *(event.feedback.recorded_at_utc for event in feedback),
        *(intent.intent.requested_at_utc for intent in intents),
        *(entry.recorded_at_utc for entry in record.version_history),
    )
    if any(event_time < created_at for event_time in event_times):
        raise OpportunityEffectivenessDataError(
            "opportunity effectiveness event precedes candidate creation"
        )


def _measure_current_outcomes(
    record: CandidatePersistenceRecord,
    *,
    intents: tuple[GovernedConversionIntent, ...],
    evaluated_at_utc: datetime,
    counts: Counter[str],
) -> None:
    for intent in intents:
        intent_id = intent.intent.conversion_intent_id
        outcomes = tuple(
            outcome
            for outcome in record.conversion_outcomes
            if outcome.conversion_intent_id == intent_id
            and outcome.outcome.recorded_at_utc <= evaluated_at_utc
        )
        if any(
            outcome.outcome.recorded_at_utc < intent.intent.requested_at_utc for outcome in outcomes
        ):
            raise OpportunityEffectivenessDataError(
                "conversion outcome precedes its conversion intent"
            )
        current = current_conversion_outcome(outcomes)
        if outcomes and current is None:
            raise OpportunityEffectivenessDataError(
                "opportunity effectiveness requires a policy-valid conversion outcome history"
            )
        counts[
            DownstreamOutcomePosture.NOT_REPORTED.value
            if current is None
            else current.outcome.status.value
        ] += 1


def _downstream_submission_measures(
    snapshot: IdeaRepositorySnapshot,
    *,
    cohort_intent_ids: frozenset[str],
    evaluated_at_utc: datetime,
) -> tuple[Counter[str], int]:
    counts: Counter[str] = Counter()
    reconciled_count = 0
    for record in snapshot.downstream_submission_records.values():
        if (
            record.resource_id not in cohort_intent_ids
            or record.submitted_at_utc > evaluated_at_utc
        ):
            continue
        counts[record.status.value] += 1
        if any(
            entry.action is DownstreamSubmissionAuditAction.RECONCILED
            and entry.occurred_at_utc <= evaluated_at_utc
            for entry in record.audit_history
        ):
            reconciled_count += 1
    return counts, reconciled_count


def _latest_review(
    reviews: tuple[GovernedReviewDecision, ...],
) -> GovernedReviewDecision | None:
    if not reviews:
        return None
    return max(reviews, key=lambda item: (item.decided_at_utc, item.review_id))


def _first_approval(
    reviews: tuple[GovernedReviewDecision, ...],
) -> GovernedReviewDecision | None:
    approvals = tuple(
        decision for decision in reviews if decision.action is ReviewAction.APPROVE_FOR_CONVERSION
    )
    if not approvals:
        return None
    return min(approvals, key=lambda item: (item.decided_at_utc, item.review_id))


def _has_stale_evidence(record: CandidatePersistenceRecord) -> bool:
    return any(
        source.freshness in {EvidenceFreshness.STALE, EvidenceFreshness.EXPIRED}
        for source in record.candidate.evidence_packet.source_refs
    )


def _has_unavailable_evidence(record: CandidatePersistenceRecord) -> bool:
    return any(
        source.freshness is EvidenceFreshness.UNAVAILABLE
        for source in record.candidate.evidence_packet.source_refs
    )


def _score_band(record: CandidatePersistenceRecord) -> str:
    score = record.candidate.score
    return "unranked" if score is None else priority_bucket_for_score(score.score).value


def _dimension_counts(
    counts: Counter[str],
    allowed_values: Iterable[str],
) -> tuple[EffectivenessDimensionCount, ...]:
    return tuple(
        EffectivenessDimensionCount(value=value, count=counts[value]) for value in allowed_values
    )


def _rate(numerator: int, denominator: int) -> EffectivenessRate:
    value = (
        None
        if denominator == 0
        else (Decimal(numerator) / Decimal(denominator)).quantize(
            RATE_QUANTUM,
            rounding=ROUND_HALF_EVEN,
        )
    )
    return EffectivenessRate(numerator=numerator, denominator=denominator, value=value)


def _duration(values: tuple[Decimal, ...]) -> EffectivenessDuration:
    if not values:
        return EffectivenessDuration(
            observation_count=0,
            minimum_seconds=None,
            p50_seconds=None,
            p95_seconds=None,
            maximum_seconds=None,
        )
    ordered = tuple(sorted(values))
    return EffectivenessDuration(
        observation_count=len(ordered),
        minimum_seconds=ordered[0],
        p50_seconds=_nearest_rank(ordered, percentile=50),
        p95_seconds=_nearest_rank(ordered, percentile=95),
        maximum_seconds=ordered[-1],
    )


def _nearest_rank(values: tuple[Decimal, ...], *, percentile: int) -> Decimal:
    index = ((percentile * len(values) + 99) // 100) - 1
    return values[index]


def _seconds(value: timedelta) -> Decimal:
    return Decimal(value.days * 86_400 + value.seconds) + Decimal(value.microseconds) / Decimal(
        1_000_000
    )


def _snapshot_payload_without_digest(
    snapshot: OpportunityEffectivenessSnapshot,
) -> dict[str, Any]:
    return {
        "schemaVersion": OPPORTUNITY_EFFECTIVENESS_SCHEMA_VERSION,
        "methodologyPolicyVersion": OPPORTUNITY_EFFECTIVENESS_POLICY_VERSION,
        "window": {
            "startUtcInclusive": snapshot.window_start_utc.isoformat(),
            "endUtcExclusive": snapshot.window_end_utc.isoformat(),
            "evaluatedAtUtc": snapshot.evaluated_at_utc.isoformat(),
            "population": "economic_opportunities_first_generated_in_window",
            "outcomeObservation": "latest_governed_fact_at_or_before_evaluated_at",
        },
        "counts": {
            "generatedOpportunityCount": snapshot.generated_opportunity_count,
            "reviewedOpportunityCount": snapshot.reviewed_opportunity_count,
            "feedbackOpportunityCount": snapshot.feedback_opportunity_count,
            "conversionOpportunityCount": snapshot.conversion_opportunity_count,
            "conversionIntentCount": snapshot.conversion_intent_count,
            "staleEvidenceOpportunityCount": snapshot.stale_evidence_opportunity_count,
            "unavailableEvidenceOpportunityCount": (
                snapshot.unavailable_evidence_opportunity_count
            ),
            "unsupportedEvidenceOpportunityCount": (
                snapshot.unsupported_evidence_opportunity_count
            ),
            "suppressedOpportunityCount": snapshot.suppressed_opportunity_count,
            "duplicateSuppressedOpportunityCount": (
                snapshot.duplicate_suppressed_opportunity_count
            ),
            "recurrentOpportunityCount": snapshot.recurrent_opportunity_count,
            "recurrentDetectionCount": snapshot.recurrent_detection_count,
            "reconciledSubmissionCount": snapshot.reconciled_submission_count,
        },
        "presentation": {
            "measurementStatus": snapshot.presentation_measurement_status.value,
            "presentedOpportunityCount": snapshot.presented_opportunity_count,
            "topRankedAcceptedOpportunityCount": (snapshot.top_ranked_accepted_opportunity_count),
        },
        "dimensions": {
            "opportunityFamily": [item.to_payload() for item in snapshot.family_counts],
            "currentScoreBand": [item.to_payload() for item in snapshot.score_band_counts],
            "latestReviewAction": [
                item.to_payload() for item in snapshot.latest_review_action_counts
            ],
            "feedbackReason": [item.to_payload() for item in snapshot.feedback_reason_counts],
            "currentDownstreamOutcome": [
                item.to_payload() for item in snapshot.current_downstream_outcome_counts
            ],
            "downstreamSubmissionPosture": [
                item.to_payload() for item in snapshot.downstream_submission_posture_counts
            ],
        },
        "rates": {
            "review": snapshot.review_rate.to_payload(),
            "approval": snapshot.approval_rate.to_payload(),
            "rejection": snapshot.rejection_rate.to_payload(),
            "suppression": snapshot.suppression_rate.to_payload(),
            "feedback": snapshot.feedback_rate.to_payload(),
            "conversion": snapshot.conversion_rate.to_payload(),
            "downstreamAccepted": snapshot.downstream_accepted_rate.to_payload(),
            "downstreamRejected": snapshot.downstream_rejected_rate.to_payload(),
            "downstreamUncertain": snapshot.downstream_uncertain_rate.to_payload(),
        },
        "timings": {
            "detectionToReview": snapshot.detection_to_review.to_payload(),
            "approvalToConversion": snapshot.approval_to_conversion.to_payload(),
        },
        "privacyBoundary": {
            "scope": "single_tenant",
            "containsRawTenantIdentifier": False,
            "containsRawClientIdentifier": False,
            "containsRawPortfolioIdentifier": False,
            "containsRawCandidateIdentifier": False,
            "containsBusinessIdentityIdentifier": False,
            "containsActorSubject": False,
            "containsCorrelationOrTraceIdentifier": False,
            "containsFreeText": False,
        },
        "productionMutationAuthority": "none_read_only_effectiveness_evidence",
    }


def _decimal_payload(value: Decimal | None) -> str | None:
    return format(value.normalize(), "f") if value is not None else None


__all__ = [
    "MAX_EFFECTIVENESS_OPPORTUNITIES",
    "OPPORTUNITY_EFFECTIVENESS_POLICY_VERSION",
    "OPPORTUNITY_EFFECTIVENESS_SCHEMA_VERSION",
    "DownstreamOutcomePosture",
    "EffectivenessDimensionCount",
    "EffectivenessDuration",
    "EffectivenessRate",
    "OpportunityEffectivenessBoundExceeded",
    "OpportunityEffectivenessDataError",
    "OpportunityEffectivenessScopeError",
    "OpportunityEffectivenessSnapshot",
    "PresentationMeasurementStatus",
    "build_opportunity_effectiveness_snapshot",
    "build_opportunity_effectiveness_snapshot_from_summary",
]
