from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
import json

import pytest

from tests.support.score_fixture import score_fixture
from tests.support.opportunity_effectiveness_fixture import (
    conversion_intent_fixture as _conversion_intent,
    conversion_outcome_fixture as _conversion_outcome,
)

from app.application.opportunity_effectiveness import (
    EffectivenessDimensionCount,
    OpportunityEffectivenessBoundExceeded,
    OpportunityEffectivenessDataError,
    OpportunityEffectivenessScopeError,
    OpportunityEffectivenessSnapshot,
    PresentationMeasurementStatus,
    build_opportunity_effectiveness_snapshot,
)
from app.domain import (
    SourceCutPosture,
    CandidateChangeReason,
    CandidatePresentationReceipt,
    CandidateVersionHistoryEntry,
    ConversionOutcomeStatus,
    DownstreamSubmissionPosture,
    EvidenceFreshness,
    EvidenceSupportability,
    FEEDBACK_TAXONOMY_VERSION,
    FeedbackCommand,
    FeedbackOutcome,
    FeedbackReason,
    GovernedFeedbackEvent,
    GovernedReviewDecision,
    IdeaCandidate,
    IdeaEvidencePacket,
    IdeaLifecycleStatus,
    IdeaRepositorySnapshot,
    LineageRef,
    OpportunityFamily,
    ReasonCode,
    ReviewAccessScope,
    ReviewAction,
    ReviewActorContext,
    ReviewActorRole,
    ReviewChannel,
    ReviewPosture,
    SourceRef,
    SourceSystem,
    SuppressionReason,
    UnsupportedEvidenceReason,
    record_feedback,
)
from app.domain.persistence_models import CandidatePersistenceRecord
from tests.support.candidate_identity import initial_candidate_identity
from tests.unit.downstream_submission_helpers import build_downstream_submission_record


WINDOW_START = datetime(2026, 6, 21, 8, 0, tzinfo=UTC)
WINDOW_END = datetime(2026, 6, 21, 12, 0, tzinfo=UTC)
EVALUATED_AT = datetime(2026, 6, 22, 8, 0, tzinfo=UTC)


def test_effectiveness_snapshot_produces_reproducible_source_safe_funnel_math() -> None:
    approved = _record(
        _candidate(
            "idea-approved-001",
            family=OpportunityFamily.HIGH_CASH,
            score=Decimal("91"),
            created_at=WINDOW_START + timedelta(hours=1),
            lifecycle_status=IdeaLifecycleStatus.APPROVED,
            review_posture=ReviewPosture.APPROVED_FOR_CONVERSION,
            recurrent=True,
        ),
        review=_review(
            "idea-approved-001",
            action=ReviewAction.APPROVE_FOR_CONVERSION,
            decided_at=WINDOW_START + timedelta(hours=2),
        ),
        feedback_reason=FeedbackReason.RELEVANT,
        feedback_outcome=FeedbackOutcome.USEFUL,
        conversion=True,
    )
    rejected = _record(
        _candidate(
            "idea-rejected-001",
            family=OpportunityFamily.UNDERPERFORMANCE,
            score=Decimal("74"),
            created_at=WINDOW_START + timedelta(hours=1),
            lifecycle_status=IdeaLifecycleStatus.REJECTED,
            review_posture=ReviewPosture.REJECTED,
        ),
        review=_review(
            "idea-rejected-001",
            action=ReviewAction.REJECT,
            decided_at=WINDOW_START + timedelta(hours=5),
        ),
        feedback_reason=FeedbackReason.WRONG_TIMING,
    )
    suppressed = _record(
        _candidate(
            "idea-suppressed-001",
            family=OpportunityFamily.CONCENTRATION,
            score=None,
            created_at=WINDOW_START + timedelta(hours=2),
            lifecycle_status=IdeaLifecycleStatus.READY_FOR_REVIEW,
            review_posture=ReviewPosture.SUPPRESSED,
            supportability=EvidenceSupportability.PARTIAL,
            freshness=EvidenceFreshness.STALE,
            suppression_reason=SuppressionReason.DUPLICATE,
        ),
        review=_review(
            "idea-suppressed-001",
            action=ReviewAction.SUPPRESS,
            decided_at=WINDOW_START + timedelta(hours=3),
            suppression_reason=SuppressionReason.DUPLICATE,
        ),
    )
    other_tenant = _record(
        _candidate(
            "idea-other-tenant-001",
            family=OpportunityFamily.HIGH_CASH,
            score=Decimal("99"),
            created_at=WINDOW_START + timedelta(hours=1),
            tenant_id="tenant-b",
        )
    )
    end_boundary = _record(
        _candidate(
            "idea-end-boundary-001",
            family=OpportunityFamily.HIGH_CASH,
            score=Decimal("82"),
            created_at=WINDOW_END,
        )
    )
    repository_snapshot = _snapshot(
        approved,
        rejected,
        suppressed,
        other_tenant,
        end_boundary,
    )

    first = build_opportunity_effectiveness_snapshot(
        repository_snapshot,
        tenant_id="tenant-a",
        window_start_utc=WINDOW_START,
        window_end_utc=WINDOW_END,
        evaluated_at_utc=EVALUATED_AT,
    )
    second = build_opportunity_effectiveness_snapshot(
        repository_snapshot,
        tenant_id="tenant-a",
        window_start_utc=WINDOW_START,
        window_end_utc=WINDOW_END,
        evaluated_at_utc=EVALUATED_AT,
    )

    assert first == second
    assert first.generated_opportunity_count == 3
    assert first.reviewed_opportunity_count == 3
    assert first.feedback_opportunity_count == 2
    assert first.conversion_opportunity_count == 1
    assert first.conversion_intent_count == 1
    assert first.stale_evidence_opportunity_count == 1
    assert first.unavailable_evidence_opportunity_count == 0
    assert first.unsupported_evidence_opportunity_count == 1
    assert first.suppressed_opportunity_count == 1
    assert first.duplicate_suppressed_opportunity_count == 1
    assert first.recurrent_opportunity_count == 1
    assert first.recurrent_detection_count == 1
    assert _counts(first.family_counts) == {
        OpportunityFamily.HIGH_CASH.value: 1,
        OpportunityFamily.UNDERPERFORMANCE.value: 1,
        OpportunityFamily.CONCENTRATION.value: 1,
    }
    _assert_family_effectiveness(first)
    assert _counts(first.score_band_counts) == {"critical": 1, "high": 1, "unranked": 1}
    assert _counts(first.latest_review_action_counts) == {
        ReviewAction.APPROVE_FOR_CONVERSION.value: 1,
        ReviewAction.REJECT.value: 1,
        ReviewAction.SUPPRESS.value: 1,
    }
    assert _counts(first.feedback_reason_counts) == {
        FeedbackReason.RELEVANT.value: 1,
        FeedbackReason.WRONG_TIMING.value: 1,
    }
    assert _counts(first.current_downstream_outcome_counts) == {
        ConversionOutcomeStatus.ACCEPTED.value: 1
    }
    assert first.review_rate.value == Decimal("1.000000")
    assert first.approval_rate.value == Decimal("0.333333")
    assert first.rejection_rate.value == Decimal("0.333333")
    assert first.suppression_rate.value == Decimal("0.333333")
    assert first.feedback_rate.value == Decimal("0.666667")
    assert first.conversion_rate.value == Decimal("1.000000")
    assert first.downstream_accepted_rate.value == Decimal("1.000000")
    assert first.downstream_rejected_rate.value == Decimal("0.000000")
    assert first.downstream_uncertain_rate.value == Decimal("0.000000")
    assert first.detection_to_review.observation_count == 3
    assert first.detection_to_review.minimum_seconds == Decimal("3600")
    assert first.detection_to_review.p50_seconds == Decimal("3600")
    assert first.detection_to_review.p95_seconds == Decimal("14400")
    assert first.approval_to_conversion.p50_seconds == Decimal("3600")
    assert first.presentation_measurement_status is (
        PresentationMeasurementStatus.UNAVAILABLE_CONSUMER_CERTIFICATION_PENDING
    )
    assert first.presented_opportunity_count is None
    assert first.top_ranked_presented_opportunity_count is None
    assert first.top_ranked_accepted_opportunity_count is None
    assert first.presentation_rate is None
    assert first.top_ranked_acceptance_rate is None

    encoded = json.dumps(first.to_payload(), sort_keys=True)
    for forbidden_value in (
        "tenant-a",
        "tenant-b",
        "client-001",
        "portfolio-001",
        "idea-approved-001",
        "advisor-sensitive-subject",
        "downstream-sensitive-reference",
    ):
        assert forbidden_value not in encoded


def test_effectiveness_snapshot_uses_null_rates_and_timings_for_empty_population() -> None:
    projection = build_opportunity_effectiveness_snapshot(
        _snapshot(),
        tenant_id="tenant-a",
        window_start_utc=WINDOW_START,
        window_end_utc=WINDOW_END,
        evaluated_at_utc=EVALUATED_AT,
    )

    assert projection.generated_opportunity_count == 0
    assert projection.review_rate.denominator == 0
    assert projection.review_rate.value is None
    assert projection.approval_rate.value is None
    assert projection.conversion_rate.value is None
    assert projection.downstream_accepted_rate.value is None
    assert projection.detection_to_review.to_payload() == {
        "observationCount": 0,
        "minimumSeconds": None,
        "p50Seconds": None,
        "p95Seconds": None,
        "maximumSeconds": None,
    }


def test_effectiveness_snapshot_measures_version_matched_presentations_and_rank_one_acceptance() -> (
    None
):
    candidate = _candidate(
        "idea-presented-001",
        family=OpportunityFamily.HIGH_CASH,
        score=Decimal("91"),
        created_at=WINDOW_START + timedelta(hours=1),
        lifecycle_status=IdeaLifecycleStatus.APPROVED,
        review_posture=ReviewPosture.APPROVED_FOR_CONVERSION,
    )
    record = _record(
        candidate,
        review=_review(
            candidate.candidate_id,
            action=ReviewAction.APPROVE_FOR_CONVERSION,
            decided_at=WINDOW_START + timedelta(hours=3),
        ),
    )
    first_receipt = _receipt(
        candidate,
        receipt_id="receipt-presented-001-a",
        rank=1,
        presented_at=WINDOW_START + timedelta(hours=2),
    )
    replay_from_later_queue = _receipt(
        candidate,
        receipt_id="receipt-presented-001-b",
        rank=2,
        presented_at=WINDOW_START + timedelta(hours=2, minutes=30),
        snapshot_digest_character="8",
    )

    projection = build_opportunity_effectiveness_snapshot(
        _snapshot(record, receipts=(first_receipt, replay_from_later_queue)),
        tenant_id="tenant-a",
        window_start_utc=WINDOW_START,
        window_end_utc=WINDOW_END,
        evaluated_at_utc=EVALUATED_AT,
    )

    assert projection.presentation_measurement_status is (
        PresentationMeasurementStatus.STORED_CONSUMER_CERTIFICATION_PENDING
    )
    assert projection.presented_opportunity_count == 1
    assert projection.top_ranked_presented_opportunity_count == 1
    assert projection.top_ranked_accepted_opportunity_count == 1
    assert projection.presentation_rate is not None
    assert projection.presentation_rate.to_payload() == {
        "numerator": 1,
        "denominator": 1,
        "value": "1.000000",
        "zeroDenominatorBehavior": "null",
    }
    assert len(projection.family_effectiveness) == 1
    family_effectiveness = projection.family_effectiveness[0]
    assert family_effectiveness.family is OpportunityFamily.HIGH_CASH
    assert family_effectiveness.presented_opportunity_count == 1
    assert family_effectiveness.presentation_rate is not None
    assert family_effectiveness.presentation_rate.to_payload() == {
        "numerator": 1,
        "denominator": 1,
        "value": "1.000000",
        "zeroDenominatorBehavior": "null",
    }
    assert projection.top_ranked_acceptance_rate is not None
    assert projection.top_ranked_acceptance_rate.to_payload() == {
        "numerator": 1,
        "denominator": 1,
        "value": "1.000000",
        "zeroDenominatorBehavior": "null",
    }


def test_effectiveness_snapshot_measures_full_ranked_queue_from_governed_outcomes() -> None:
    candidates = tuple(
        _candidate(
            f"idea-ranked-{index}",
            family=OpportunityFamily.HIGH_CASH,
            score=Decimal(95 - index),
            created_at=WINDOW_START + timedelta(hours=1),
            lifecycle_status=(
                IdeaLifecycleStatus.APPROVED if index == 1 else IdeaLifecycleStatus.GENERATED
            ),
            review_posture=(
                ReviewPosture.APPROVED_FOR_CONVERSION
                if index == 1
                else ReviewPosture.ADVISOR_REVIEW_REQUIRED
            ),
        )
        for index in range(1, 4)
    )
    records = (
        _record(
            candidates[0],
            review=_review(
                candidates[0].candidate_id,
                action=ReviewAction.APPROVE_FOR_CONVERSION,
                decided_at=WINDOW_START + timedelta(hours=2, minutes=30),
            ),
            conversion=True,
        ),
        _record(
            candidates[1],
            feedback_reason=FeedbackReason.RELEVANT,
            feedback_outcome=FeedbackOutcome.USEFUL,
        ),
        _record(
            candidates[2],
            feedback_reason=FeedbackReason.NOT_RELEVANT,
        ),
    )
    presented_at = WINDOW_START + timedelta(hours=2)
    receipts = tuple(
        _receipt(
            candidate,
            receipt_id=f"receipt-ranked-{rank}",
            rank=rank,
            presented_at=presented_at,
        )
        for rank, candidate in enumerate(candidates, start=1)
    )

    projection = _build(_snapshot(*records, receipts=receipts))

    cutoff_three = next(item for item in projection.ranking_quality if item.cutoff == 3)
    assert cutoff_three.ready_snapshot_count == 1
    assert cutoff_three.judgment_coverage == Decimal("1.000000")
    assert cutoff_three.mean_precision_at_k == Decimal("0.666667")
    assert cutoff_three.mean_ndcg_at_k == Decimal("1.000000")
    assert cutoff_three.support_status.value == "insufficient_support"


def test_effectiveness_snapshot_does_not_apply_later_version_feedback_to_old_rank() -> None:
    original = _candidate(
        "idea-ranking-version-fence-001",
        family=OpportunityFamily.HIGH_CASH,
        score=Decimal("91"),
        created_at=WINDOW_START + timedelta(hours=1),
    )
    refreshed = replace(
        original,
        identity=replace(original.identity, evidence_version=2),
        updated_at_utc=WINDOW_START + timedelta(hours=3),
    )
    old_version = CandidateVersionHistoryEntry(
        candidate_id=original.candidate_id,
        business_identity_id=original.identity.business_identity_id,
        material_fingerprint=original.identity.material_fingerprint,
        material_version=1,
        evidence_version=1,
        change_reason=CandidateChangeReason.INITIAL_DETECTION,
        source_lifecycle_status=None,
        resulting_lifecycle_status=IdeaLifecycleStatus.GENERATED,
        supersedes_material_version=None,
        evidence_hash=original.evidence_packet.lineage_ref.content_hash,
        recorded_at_utc=original.created_at_utc,
    )
    record = replace(
        _record(
            refreshed,
            feedback_reason=FeedbackReason.RELEVANT,
            feedback_outcome=FeedbackOutcome.USEFUL,
        ),
        version_history=(old_version,),
    )
    receipt = replace(
        _receipt(
            refreshed,
            receipt_id="receipt-ranking-version-fence-001",
            rank=1,
            presented_at=WINDOW_START + timedelta(hours=2),
        ),
        visible_candidate_count=1,
        candidate_evidence_version=1,
    )

    projection = _build(_snapshot(record, receipts=(receipt,)))

    cutoff_one = next(item for item in projection.ranking_quality if item.cutoff == 1)
    assert cutoff_one.ready_snapshot_count == 0
    assert cutoff_one.incomplete_judgment_snapshot_count == 1
    assert cutoff_one.judgment_coverage == Decimal("0.000000")
    assert cutoff_one.mean_precision_at_k is None


def test_effectiveness_snapshot_does_not_credit_old_rank_to_a_later_evidence_approval() -> None:
    candidate = _candidate(
        "idea-version-fenced-001",
        family=OpportunityFamily.HIGH_CASH,
        score=Decimal("91"),
        created_at=WINDOW_START + timedelta(hours=1),
        lifecycle_status=IdeaLifecycleStatus.APPROVED,
        review_posture=ReviewPosture.APPROVED_FOR_CONVERSION,
    )
    old_version = CandidateVersionHistoryEntry(
        candidate_id=candidate.candidate_id,
        business_identity_id=candidate.identity.business_identity_id,
        material_fingerprint=candidate.identity.material_fingerprint,
        material_version=1,
        evidence_version=1,
        change_reason=CandidateChangeReason.INITIAL_DETECTION,
        source_lifecycle_status=None,
        resulting_lifecycle_status=IdeaLifecycleStatus.GENERATED,
        supersedes_material_version=None,
        evidence_hash=f"sha256:{'1' * 64}",
        recorded_at_utc=WINDOW_START + timedelta(hours=1),
    )
    approval = replace(
        _review(
            candidate.candidate_id,
            action=ReviewAction.APPROVE_FOR_CONVERSION,
            decided_at=WINDOW_START + timedelta(hours=3),
        ),
        evidence_content_hash=f"sha256:{'2' * 64}",
        source_revision_vector_digest="legacy:unknown",
        source_cut_posture=SourceCutPosture.UNKNOWN,
        candidate_material_version=1,
        candidate_evidence_version=1,
        review_channel=ReviewChannel.LEGACY_UNVERIFIED,
        presentation_receipt_id=None,
        queue_snapshot_digest=None,
        review_policy_version="legacy-unverified",
    )
    record = replace(_record(candidate, review=approval), version_history=(old_version,))

    projection = build_opportunity_effectiveness_snapshot(
        _snapshot(
            record,
            receipts=(
                _receipt(
                    candidate,
                    receipt_id="receipt-version-fenced-001",
                    rank=1,
                    presented_at=WINDOW_START + timedelta(hours=2),
                ),
            ),
        ),
        tenant_id="tenant-a",
        window_start_utc=WINDOW_START,
        window_end_utc=WINDOW_END,
        evaluated_at_utc=EVALUATED_AT,
    )

    assert projection.presented_opportunity_count == 1
    assert projection.top_ranked_presented_opportunity_count == 1
    assert projection.top_ranked_accepted_opportunity_count == 0
    assert projection.top_ranked_acceptance_rate is not None
    assert projection.top_ranked_acceptance_rate.value == Decimal("0.000000")


def test_effectiveness_snapshot_distinguishes_no_rank_one_presentation_from_rejection() -> None:
    candidate = _candidate(
        "idea-presented-rank-two-001",
        family=OpportunityFamily.HIGH_CASH,
        score=Decimal("81"),
        created_at=WINDOW_START + timedelta(hours=1),
    )

    projection = build_opportunity_effectiveness_snapshot(
        _snapshot(
            _record(candidate),
            receipts=(
                _receipt(
                    candidate,
                    receipt_id="receipt-presented-rank-two-001",
                    rank=2,
                    presented_at=WINDOW_START + timedelta(hours=2),
                ),
            ),
        ),
        tenant_id="tenant-a",
        window_start_utc=WINDOW_START,
        window_end_utc=WINDOW_END,
        evaluated_at_utc=EVALUATED_AT,
    )

    assert projection.presented_opportunity_count == 1
    assert projection.top_ranked_presented_opportunity_count == 0
    assert projection.top_ranked_accepted_opportunity_count == 0
    assert projection.presentation_rate is not None
    assert projection.presentation_rate.value == Decimal("1.000000")
    assert projection.top_ranked_acceptance_rate is not None
    assert projection.top_ranked_acceptance_rate.to_payload() == {
        "numerator": 0,
        "denominator": 0,
        "value": None,
        "zeroDenominatorBehavior": "null",
    }


@pytest.mark.parametrize(
    "approval_time",
    (
        WINDOW_START + timedelta(hours=1, minutes=30),
        EVALUATED_AT + timedelta(seconds=1),
    ),
)
def test_effectiveness_snapshot_does_not_credit_approval_outside_presentation_chronology(
    approval_time: datetime,
) -> None:
    candidate = _candidate(
        "idea-presentation-chronology-001",
        family=OpportunityFamily.HIGH_CASH,
        score=Decimal("91"),
        created_at=WINDOW_START + timedelta(hours=1),
        lifecycle_status=IdeaLifecycleStatus.APPROVED,
        review_posture=ReviewPosture.APPROVED_FOR_CONVERSION,
    )
    record = _record(
        candidate,
        review=_review(
            candidate.candidate_id,
            action=ReviewAction.APPROVE_FOR_CONVERSION,
            decided_at=approval_time,
        ),
    )

    projection = build_opportunity_effectiveness_snapshot(
        _snapshot(
            record,
            receipts=(
                _receipt(
                    candidate,
                    receipt_id="receipt-presentation-chronology-001",
                    rank=1,
                    presented_at=WINDOW_START + timedelta(hours=2),
                ),
            ),
        ),
        tenant_id="tenant-a",
        window_start_utc=WINDOW_START,
        window_end_utc=WINDOW_END,
        evaluated_at_utc=EVALUATED_AT,
    )

    assert projection.presented_opportunity_count == 1
    assert projection.top_ranked_presented_opportunity_count == 1
    assert projection.top_ranked_accepted_opportunity_count == 0


def test_effectiveness_snapshot_ignores_future_presentations() -> None:
    candidate = _candidate(
        "idea-future-presentation-001",
        family=OpportunityFamily.HIGH_CASH,
        score=Decimal("91"),
        created_at=WINDOW_START + timedelta(hours=1),
    )
    projection = build_opportunity_effectiveness_snapshot(
        _snapshot(
            _record(candidate),
            receipts=(
                replace(
                    _receipt(
                        candidate,
                        receipt_id="receipt-future-presentation-001",
                        rank=1,
                        presented_at=WINDOW_START + timedelta(hours=2),
                    ),
                    accepted_at_utc=EVALUATED_AT + timedelta(seconds=1),
                ),
            ),
        ),
        tenant_id="tenant-a",
        window_start_utc=WINDOW_START,
        window_end_utc=WINDOW_END,
        evaluated_at_utc=EVALUATED_AT,
    )

    assert projection.presentation_measurement_status is (
        PresentationMeasurementStatus.UNAVAILABLE_CONSUMER_CERTIFICATION_PENDING
    )
    assert projection.presented_opportunity_count is None
    assert projection.top_ranked_presented_opportunity_count is None
    assert projection.top_ranked_accepted_opportunity_count is None
    assert projection.presentation_rate is None
    assert projection.top_ranked_acceptance_rate is None


def test_effectiveness_snapshot_fails_closed_on_cross_tenant_presentation_receipt() -> None:
    candidate = _candidate(
        "idea-cross-tenant-presentation-001",
        family=OpportunityFamily.HIGH_CASH,
        score=Decimal("91"),
        created_at=WINDOW_START + timedelta(hours=1),
    )
    receipt = replace(
        _receipt(
            candidate,
            receipt_id="receipt-cross-tenant-presentation-001",
            rank=1,
            presented_at=WINDOW_START + timedelta(hours=2),
        ),
        tenant_id="tenant-b",
    )

    with pytest.raises(OpportunityEffectivenessDataError, match="tenant does not match"):
        build_opportunity_effectiveness_snapshot(
            _snapshot(_record(candidate), receipts=(receipt,)),
            tenant_id="tenant-a",
            window_start_utc=WINDOW_START,
            window_end_utc=WINDOW_END,
            evaluated_at_utc=EVALUATED_AT,
        )


def test_effectiveness_snapshot_observes_only_facts_available_at_evaluation_time() -> None:
    candidate = _candidate(
        "idea-temporal-001",
        family=OpportunityFamily.HIGH_CASH,
        score=Decimal("82"),
        created_at=WINDOW_START + timedelta(hours=1),
        lifecycle_status=IdeaLifecycleStatus.APPROVED,
        review_posture=ReviewPosture.APPROVED_FOR_CONVERSION,
    )
    future_review = replace(
        _review(
            candidate.candidate_id,
            action=ReviewAction.REJECT,
            decided_at=EVALUATED_AT + timedelta(seconds=1),
        ),
        decided_at_utc=WINDOW_START + timedelta(hours=2),
    )
    intent = _conversion_intent(candidate, requested_at=WINDOW_START + timedelta(hours=3))
    requested = _conversion_outcome(
        intent,
        status=ConversionOutcomeStatus.REQUESTED,
        version=1,
        recorded_at=WINDOW_START + timedelta(hours=4),
    )
    future_accepted = _conversion_outcome(
        intent,
        status=ConversionOutcomeStatus.ACCEPTED,
        version=2,
        recorded_at=EVALUATED_AT + timedelta(seconds=1),
    )
    future_accepted = replace(
        future_accepted,
        outcome=replace(
            future_accepted.outcome,
            recorded_at_utc=WINDOW_START + timedelta(hours=5),
        ),
    )
    record = _record(candidate, conversion=False)
    record = replace(
        record,
        review_decisions=(future_review,),
        conversion_intents=(intent,),
        conversion_outcomes=(requested, future_accepted),
    )

    projection = build_opportunity_effectiveness_snapshot(
        _snapshot(record),
        tenant_id="tenant-a",
        window_start_utc=WINDOW_START,
        window_end_utc=WINDOW_END,
        evaluated_at_utc=EVALUATED_AT,
    )

    assert projection.reviewed_opportunity_count == 0
    assert projection.conversion_intent_count == 1
    assert _counts(projection.current_downstream_outcome_counts) == {
        ConversionOutcomeStatus.REQUESTED.value: 1
    }
    assert projection.downstream_accepted_rate.value == Decimal("0.000000")
    assert projection.downstream_failed_rate.value == Decimal("0.000000")
    assert projection.downstream_uncertain_rate.value == Decimal("1.000000")


def test_effectiveness_snapshot_counts_candidate_level_suppression_without_review() -> None:
    candidate = _candidate(
        "idea-policy-suppressed-001",
        family=OpportunityFamily.CONCENTRATION,
        score=None,
        created_at=WINDOW_START + timedelta(hours=1),
        lifecycle_status=IdeaLifecycleStatus.READY_FOR_REVIEW,
        review_posture=ReviewPosture.SUPPRESSED,
        suppression_reason=SuppressionReason.DUPLICATE,
    )

    projection = _build(_snapshot(_record(candidate)))

    assert projection.reviewed_opportunity_count == 0
    assert projection.suppressed_opportunity_count == 1
    assert projection.duplicate_suppressed_opportunity_count == 1


def test_effectiveness_snapshot_counts_only_cohort_downstream_submissions() -> None:
    candidate = _candidate(
        "idea-submitted-001",
        family=OpportunityFamily.HIGH_CASH,
        score=Decimal("91"),
        created_at=WINDOW_START + timedelta(hours=1),
        lifecycle_status=IdeaLifecycleStatus.APPROVED,
        review_posture=ReviewPosture.APPROVED_FOR_CONVERSION,
    )
    record = _record(
        candidate,
        review=_review(
            candidate.candidate_id,
            action=ReviewAction.APPROVE_FOR_CONVERSION,
            decided_at=WINDOW_START + timedelta(hours=2),
        ),
        conversion=True,
    )
    submission = build_downstream_submission_record(
        idempotency_key="submission-idea-submitted-001",
        request_fingerprint=f"sha256:{'8' * 64}",
        resource_id="intent-idea-submitted-001",
        submitted_at_utc=WINDOW_START + timedelta(hours=4),
        status=DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM,
    )
    snapshot = replace(
        _snapshot(record),
        downstream_submission_records={submission.idempotency_key: submission},
    )

    projection = _build(snapshot)

    assert _counts(projection.downstream_submission_posture_counts) == {
        DownstreamSubmissionPosture.ACCEPTED_BY_DOWNSTREAM.value: 1
    }
    assert projection.reconciled_submission_count == 0


def test_effectiveness_snapshot_fails_closed_on_scope_identity_and_event_corruption() -> None:
    unscoped = replace(
        _candidate(
            "idea-unscoped-001",
            family=OpportunityFamily.HIGH_CASH,
            score=Decimal("82"),
            created_at=WINDOW_START + timedelta(hours=1),
        ),
        access_scope=None,
    )
    with pytest.raises(OpportunityEffectivenessScopeError, match="requires access scope"):
        _build(_snapshot(_record(unscoped)))

    first = _candidate(
        "idea-identity-001",
        family=OpportunityFamily.HIGH_CASH,
        score=Decimal("82"),
        created_at=WINDOW_START + timedelta(hours=1),
    )
    second = replace(
        _candidate(
            "idea-identity-002",
            family=OpportunityFamily.UNDERPERFORMANCE,
            score=Decimal("74"),
            created_at=WINDOW_START + timedelta(hours=1),
        ),
        identity=first.identity,
    )
    with pytest.raises(OpportunityEffectivenessDataError, match="one record per business identity"):
        _build(_snapshot(_record(first), _record(second)))

    invalid_review = _review(
        first.candidate_id,
        action=ReviewAction.REJECT,
        decided_at=first.created_at_utc - timedelta(seconds=1),
    )
    with pytest.raises(OpportunityEffectivenessDataError, match="precedes candidate creation"):
        _build(_snapshot(_record(first, review=invalid_review)))

    intent = _conversion_intent(first, requested_at=WINDOW_START + timedelta(hours=3))
    invalid_outcome = _conversion_outcome(
        intent,
        status=ConversionOutcomeStatus.REQUESTED,
        version=1,
        recorded_at=intent.intent.requested_at_utc - timedelta(seconds=1),
    )
    invalid_outcome_record = replace(
        _record(first),
        conversion_intents=(intent,),
        conversion_outcomes=(invalid_outcome,),
    )
    with pytest.raises(OpportunityEffectivenessDataError, match="precedes its conversion intent"):
        _build(_snapshot(invalid_outcome_record))

    invalid_history_record = replace(
        _record(first),
        version_history=(
            CandidateVersionHistoryEntry(
                candidate_id=first.candidate_id,
                business_identity_id=first.identity.business_identity_id,
                material_fingerprint=first.identity.material_fingerprint,
                material_version=2,
                evidence_version=1,
                change_reason=CandidateChangeReason.RECURRENT_CONDITION,
                source_lifecycle_status=IdeaLifecycleStatus.CLOSED,
                resulting_lifecycle_status=IdeaLifecycleStatus.GENERATED,
                supersedes_material_version=1,
                evidence_hash=f"sha256:{'3' * 64}",
                recorded_at_utc=first.created_at_utc - timedelta(seconds=1),
            ),
        ),
    )
    with pytest.raises(OpportunityEffectivenessDataError, match="precedes candidate creation"):
        _build(_snapshot(invalid_history_record))


def test_effectiveness_snapshot_rejects_invalid_window_and_bounds() -> None:
    with pytest.raises(OpportunityEffectivenessScopeError, match="tenant_id is required"):
        _build(_snapshot(), tenant_id=" ")
    with pytest.raises(ValueError, match="window_start_utc must be timezone-aware"):
        _build(_snapshot(), window_start_utc=WINDOW_START.replace(tzinfo=None))
    with pytest.raises(ValueError, match="must precede"):
        _build(_snapshot(), window_start_utc=WINDOW_END)
    with pytest.raises(ValueError, match="must not be after"):
        _build(_snapshot(), evaluated_at_utc=WINDOW_END - timedelta(seconds=1))
    for invalid_bound in (0, 10_001):
        with pytest.raises(ValueError, match="max_opportunities must be between 1 and 10000"):
            _build(_snapshot(), max_opportunities=invalid_bound)

    records = tuple(
        _record(
            _candidate(
                f"idea-bound-{index}",
                family=OpportunityFamily.HIGH_CASH,
                score=Decimal("82"),
                created_at=WINDOW_START + timedelta(hours=1),
            )
        )
        for index in range(2)
    )
    with pytest.raises(OpportunityEffectivenessBoundExceeded, match="1 opportunity bound"):
        _build(_snapshot(*records), max_opportunities=1)


def _build(
    snapshot: IdeaRepositorySnapshot,
    *,
    tenant_id: str = "tenant-a",
    window_start_utc: datetime = WINDOW_START,
    window_end_utc: datetime = WINDOW_END,
    evaluated_at_utc: datetime = EVALUATED_AT,
    max_opportunities: int = 10_000,
) -> OpportunityEffectivenessSnapshot:
    return build_opportunity_effectiveness_snapshot(
        snapshot,
        tenant_id=tenant_id,
        window_start_utc=window_start_utc,
        window_end_utc=window_end_utc,
        evaluated_at_utc=evaluated_at_utc,
        max_opportunities=max_opportunities,
    )


def _candidate(
    candidate_id: str,
    *,
    family: OpportunityFamily,
    score: Decimal | None,
    created_at: datetime,
    tenant_id: str = "tenant-a",
    lifecycle_status: IdeaLifecycleStatus = IdeaLifecycleStatus.GENERATED,
    review_posture: ReviewPosture = ReviewPosture.ADVISOR_REVIEW_REQUIRED,
    supportability: EvidenceSupportability = EvidenceSupportability.READY,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    suppression_reason: SuppressionReason | None = None,
    recurrent: bool = False,
) -> IdeaCandidate:
    source = SourceRef(
        product_id="lotus-core:PortfolioStateSnapshot:v1",
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route="/integration/portfolios/{portfolio_id}/core-snapshot",
        as_of_date=date(2026, 6, 21),
        generated_at_utc=created_at - timedelta(minutes=5),
        content_hash=f"sha256:{'1' * 64}",
        data_quality_status="complete",
        freshness=freshness,
    )
    unsupported_reasons = (
        (UnsupportedEvidenceReason.STALE_SOURCE,)
        if supportability is not EvidenceSupportability.READY
        else ()
    )
    evidence = IdeaEvidencePacket(
        evidence_packet_id=f"evidence-{candidate_id}",
        supportability=supportability,
        source_refs=(source,),
        lineage_ref=LineageRef(
            lineage_id=f"lineage-{candidate_id}",
            source_refs=(source,),
            content_hash=f"sha256:{'2' * 64}",
        ),
        reason_codes=(ReasonCode.REVIEW_REQUIRED,),
        unsupported_reasons=unsupported_reasons,
        created_at_utc=created_at,
    )
    identity = initial_candidate_identity(candidate_id)
    if recurrent:
        identity = replace(
            identity,
            material_fingerprint=f"sha256:{'4' * 64}",
            material_version=2,
            change_reason=CandidateChangeReason.RECURRENT_CONDITION,
            supersedes_material_version=1,
        )
    return IdeaCandidate(
        candidate_id=candidate_id,
        identity=identity,
        family=family,
        lifecycle_status=lifecycle_status,
        review_posture=review_posture,
        evidence_packet=evidence,
        source_signal_ids=(f"signal-{candidate_id}",),
        score=(
            score_fixture(
                policy_version="idle-liquidity-v2",
                score=score,
                reason_codes=(ReasonCode.QUEUE_PRIORITY,),
            )
            if score is not None
            else None
        ),
        access_scope=ReviewAccessScope(
            tenant_id=tenant_id,
            book_id="book-001",
            portfolio_id="portfolio-001",
            client_id="client-001",
        ),
        suppression_reason=suppression_reason,
        created_at_utc=created_at,
        updated_at_utc=created_at,
    )


def _review(
    candidate_id: str,
    *,
    action: ReviewAction,
    decided_at: datetime,
    suppression_reason: SuppressionReason | None = None,
) -> GovernedReviewDecision:
    resulting_posture = {
        ReviewAction.APPROVE_FOR_CONVERSION: ReviewPosture.APPROVED_FOR_CONVERSION,
        ReviewAction.REJECT: ReviewPosture.REJECTED,
        ReviewAction.SUPPRESS: ReviewPosture.SUPPRESSED,
    }[action]
    return GovernedReviewDecision(
        review_id=f"review-{candidate_id}-{action.value}",
        candidate_id=candidate_id,
        evidence_packet_id=f"evidence-{candidate_id}",
        evidence_content_hash=f"sha256:{'2' * 64}",
        source_revision_vector_digest="legacy:unknown",
        source_cut_posture=SourceCutPosture.UNKNOWN,
        candidate_material_version=1,
        candidate_evidence_version=1,
        review_channel=ReviewChannel.LEGACY_UNVERIFIED,
        presentation_receipt_id=None,
        queue_snapshot_digest=None,
        review_policy_version="legacy-unverified",
        action=action,
        resulting_posture=resulting_posture,
        actor_subject="advisor-sensitive-subject",
        actor_role=ReviewActorRole.ADVISOR,
        reason_codes=(ReasonCode.REVIEW_REQUIRED,),
        decided_at_utc=decided_at,
        accepted_at_utc=decided_at,
        suppression_reason=suppression_reason,
    )


def _record(
    candidate: IdeaCandidate,
    *,
    review: GovernedReviewDecision | None = None,
    feedback_reason: FeedbackReason | None = None,
    feedback_outcome: FeedbackOutcome = FeedbackOutcome.NOT_USEFUL,
    conversion: bool = False,
) -> CandidatePersistenceRecord:
    feedback: tuple[GovernedFeedbackEvent, ...] = ()
    if feedback_reason is not None:
        scope = candidate.access_scope
        assert scope is not None
        feedback = (
            record_feedback(
                candidate,
                FeedbackCommand(
                    feedback_id=f"feedback-{candidate.candidate_id}",
                    actor=ReviewActorContext(
                        actor_subject="advisor-sensitive-subject",
                        role=ReviewActorRole.ADVISOR,
                        tenant_ids=frozenset({scope.tenant_id}),
                        book_ids=frozenset({scope.book_id}),
                        portfolio_ids=frozenset({scope.portfolio_id}),
                        client_ids=frozenset({scope.client_id}),
                    ),
                    outcome=feedback_outcome,
                    reason=feedback_reason,
                    taxonomy_version=FEEDBACK_TAXONOMY_VERSION,
                    recorded_at_utc=WINDOW_START + timedelta(hours=6),
                ),
                accepted_at_utc=WINDOW_START + timedelta(hours=6),
            ).feedback_event,
        )
    intent = (
        _conversion_intent(candidate, requested_at=WINDOW_START + timedelta(hours=3))
        if conversion
        else None
    )
    outcomes = (
        (
            _conversion_outcome(
                intent,
                status=ConversionOutcomeStatus.REQUESTED,
                version=1,
                recorded_at=WINDOW_START + timedelta(hours=4),
            ),
            _conversion_outcome(
                intent,
                status=ConversionOutcomeStatus.ACCEPTED,
                version=2,
                recorded_at=WINDOW_START + timedelta(hours=5),
            ),
        )
        if intent is not None
        else ()
    )
    version_history = (
        (
            CandidateVersionHistoryEntry(
                candidate_id=candidate.candidate_id,
                business_identity_id=candidate.identity.business_identity_id,
                material_fingerprint=candidate.identity.material_fingerprint,
                material_version=2,
                evidence_version=1,
                change_reason=CandidateChangeReason.RECURRENT_CONDITION,
                source_lifecycle_status=IdeaLifecycleStatus.CLOSED,
                resulting_lifecycle_status=IdeaLifecycleStatus.GENERATED,
                supersedes_material_version=1,
                evidence_hash=f"sha256:{'3' * 64}",
                recorded_at_utc=WINDOW_START + timedelta(minutes=90),
            ),
        )
        if candidate.identity.change_reason is CandidateChangeReason.RECURRENT_CONDITION
        else ()
    )
    return CandidatePersistenceRecord(
        candidate=candidate,
        evidence_hash=f"sha256:{'3' * 64}",
        persisted_at_utc=candidate.created_at_utc,
        version_history=version_history,
        review_decisions=(review,) if review is not None else (),
        feedback_events=feedback,
        conversion_intents=(intent,) if intent is not None else (),
        conversion_outcomes=outcomes,
    )


def _assert_family_effectiveness(snapshot: OpportunityEffectivenessSnapshot) -> None:
    family_effectiveness = {item.family: item for item in snapshot.family_effectiveness}
    high_cash = family_effectiveness[OpportunityFamily.HIGH_CASH]
    assert high_cash.generated_opportunity_count == 1
    assert high_cash.presented_opportunity_count is None
    assert high_cash.presentation_rate is None
    assert high_cash.reviewed_opportunity_count == 1
    assert high_cash.approved_opportunity_count == 1
    assert high_cash.feedback_opportunity_count == 1
    assert high_cash.conversion_opportunity_count == 1
    assert high_cash.downstream_accepted_count == 1
    assert high_cash.downstream_failed_count == 0
    assert high_cash.review_rate.value == Decimal("1.000000")
    assert high_cash.approval_rate.value == Decimal("1.000000")
    assert high_cash.conversion_rate.value == Decimal("1.000000")
    assert high_cash.downstream_accepted_rate.value == Decimal("1.000000")
    assert high_cash.downstream_failed_rate.value == Decimal("0.000000")

    concentration = family_effectiveness[OpportunityFamily.CONCENTRATION]
    assert concentration.suppressed_opportunity_count == 1
    assert concentration.duplicate_suppressed_opportunity_count == 1
    assert concentration.suppression_rate.value == Decimal("1.000000")
    assert concentration.duplicate_suppression_rate.value == Decimal("1.000000")
    assert concentration.approval_rate.value == Decimal("0.000000")
    assert concentration.conversion_rate.value is None

    underperformance = family_effectiveness[OpportunityFamily.UNDERPERFORMANCE]
    assert underperformance.rejected_opportunity_count == 1
    assert underperformance.rejection_rate.value == Decimal("1.000000")
    assert underperformance.feedback_rate.value == Decimal("1.000000")


def _counts(items: tuple[EffectivenessDimensionCount, ...]) -> dict[str, int]:
    return {item.value: item.count for item in items if item.count > 0}


def _receipt(
    candidate: IdeaCandidate,
    *,
    receipt_id: str,
    rank: int,
    presented_at: datetime,
    snapshot_digest_character: str = "9",
) -> CandidatePresentationReceipt:
    scope = candidate.access_scope
    assert scope is not None
    return CandidatePresentationReceipt(
        receipt_id=receipt_id,
        candidate_id=candidate.candidate_id,
        tenant_id=scope.tenant_id,
        presented_at_utc=presented_at,
        rank_at_presentation=rank,
        visible_candidate_count=3,
        queue_snapshot_digest=f"sha256:{snapshot_digest_character * 64}",
        queue_policy_version="idea-queue-v1",
        ranking_policy_version="idea-rank-v1",
        candidate_material_version=candidate.identity.material_version,
        candidate_evidence_version=candidate.identity.evidence_version,
        source_revision_vector_digest=candidate.evidence_packet.source_revision_vector_digest,
        source_cut_posture=candidate.evidence_packet.source_cut_posture,
        accepted_at_utc=presented_at,
    )


def _snapshot(
    *records: CandidatePersistenceRecord,
    receipts: tuple[CandidatePresentationReceipt, ...] = (),
) -> IdeaRepositorySnapshot:
    return IdeaRepositorySnapshot(
        candidate_records={record.candidate.candidate_id: record for record in records},
        idempotency_records={},
        idempotency_candidates={},
        presentation_receipts={receipt.receipt_id: receipt for receipt in receipts},
    )
