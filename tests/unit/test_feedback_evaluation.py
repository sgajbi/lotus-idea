from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
import json

import pytest

from app.application.feedback_evaluation import (
    FeedbackEvaluationBoundExceeded,
    FeedbackEvaluationScopeError,
    build_offline_feedback_evaluation,
)
from app.domain import (
    ConversionBoundary,
    ConversionOutcomeStatus,
    ConversionTarget,
    EvidenceFreshness,
    EvidenceSupportability,
    FEEDBACK_TAXONOMY_VERSION,
    FeedbackCommand,
    FeedbackOutcome,
    FeedbackReason,
    GovernedConversionOutcome,
    GovernedReviewDecision,
    IdeaCandidate,
    IdeaConversionOutcome,
    IdeaEvidencePacket,
    IdeaLifecycleStatus,
    IdeaRepositorySnapshot,
    IdeaScore,
    LineageRef,
    OpportunityFamily,
    ReasonCode,
    ReviewAccessScope,
    ReviewAction,
    ReviewActorContext,
    ReviewActorRole,
    ReviewPosture,
    SourceRef,
    SourceSystem,
    record_feedback,
)
from app.domain.persistence_models import CandidatePersistenceRecord
from tests.support.candidate_identity import initial_candidate_identity


EVALUATED_AT = datetime(2026, 6, 21, 11, 0, tzinfo=UTC)
GOVERNED_REASON_SCENARIOS = (
    (FeedbackOutcome.USEFUL, FeedbackReason.RELEVANT, OpportunityFamily.HIGH_CASH),
    (
        FeedbackOutcome.NOT_USEFUL,
        FeedbackReason.NOT_RELEVANT,
        OpportunityFamily.UNDERPERFORMANCE,
    ),
    (
        FeedbackOutcome.NOT_USEFUL,
        FeedbackReason.ALREADY_KNOWN,
        OpportunityFamily.HIGH_CASH,
    ),
    (
        FeedbackOutcome.NOT_USEFUL,
        FeedbackReason.WRONG_TIMING,
        OpportunityFamily.UNDERPERFORMANCE,
    ),
    (
        FeedbackOutcome.NOT_USEFUL,
        FeedbackReason.INSUFFICIENT_EVIDENCE,
        OpportunityFamily.HIGH_CASH,
    ),
    (
        FeedbackOutcome.NOT_USEFUL,
        FeedbackReason.WRONG_PRIORITY,
        OpportunityFamily.UNDERPERFORMANCE,
    ),
    (
        FeedbackOutcome.NOT_USEFUL,
        FeedbackReason.DUPLICATE,
        OpportunityFamily.HIGH_CASH,
    ),
    (
        FeedbackOutcome.NOT_USEFUL,
        FeedbackReason.CLIENT_SPECIFIC_CONSTRAINT,
        OpportunityFamily.UNDERPERFORMANCE,
    ),
)


def test_offline_feedback_projection_is_tenant_scoped_reproducible_and_source_safe() -> None:
    high_cash = _record(
        _candidate("idea-high-cash-001", OpportunityFamily.HIGH_CASH, "tenant-a", Decimal("82")),
        feedback_reason=FeedbackReason.ALREADY_KNOWN,
        review_action=ReviewAction.NO_ACTION,
        include_downstream_outcome=True,
    )
    underperformance = _record(
        _candidate(
            "idea-underperformance-001",
            OpportunityFamily.UNDERPERFORMANCE,
            "tenant-a",
            Decimal("74"),
        ),
        feedback_reason=FeedbackReason.WRONG_TIMING,
    )
    other_tenant = _record(
        _candidate("idea-other-tenant-001", OpportunityFamily.HIGH_CASH, "tenant-b", Decimal("90")),
        feedback_reason=FeedbackReason.WRONG_PRIORITY,
    )
    repository_snapshot = _snapshot(high_cash, underperformance, other_tenant)

    first = build_offline_feedback_evaluation(
        repository_snapshot,
        tenant_id="tenant-a",
        evaluated_at_utc=EVALUATED_AT,
    )
    second = build_offline_feedback_evaluation(
        repository_snapshot,
        tenant_id="tenant-a",
        evaluated_at_utc=EVALUATED_AT,
    )

    assert first == second
    assert first.source_observation_count == 2
    assert [cohort.feedback_reason for cohort in first.cohorts] == [
        FeedbackReason.ALREADY_KNOWN,
        FeedbackReason.WRONG_TIMING,
    ]
    high_cash_cohort = first.cohorts[0]
    assert high_cash_cohort.review_action is ReviewAction.NO_ACTION
    assert high_cash_cohort.score == Decimal("82")
    assert high_cash_cohort.rank_context.value == "high"
    assert high_cash_cohort.downstream_target == "report_evidence"
    assert high_cash_cohort.downstream_status == "completed"
    assert high_cash_cohort.downstream_source_system == "lotus-report"

    encoded = json.dumps(first.to_payload(), sort_keys=True)
    for forbidden_value in (
        "tenant-a",
        "tenant-b",
        "client-001",
        "portfolio-001",
        "advisor-sensitive-subject",
        "idea-high-cash-001",
        "feedback-idea-high-cash-001",
        "downstream-sensitive-reference",
    ):
        assert forbidden_value not in encoded
    assert first.to_payload()["productionMutationAuthority"] == ("none_read_only_offline_evidence")
    assert first.to_payload()["cohorts"][0]["score"] == "82"
    assert repository_snapshot == _snapshot(high_cash, underperformance, other_tenant)


def test_offline_feedback_projection_fails_closed_without_tenant_scope() -> None:
    unscoped = _candidate(
        "idea-unscoped-001",
        OpportunityFamily.HIGH_CASH,
        "tenant-a",
        Decimal("82"),
    )
    record = _record(unscoped, feedback_reason=FeedbackReason.NOT_RELEVANT)
    record = replace(record, candidate=replace(record.candidate, access_scope=None))

    with pytest.raises(FeedbackEvaluationScopeError, match="requires access scope"):
        build_offline_feedback_evaluation(
            _snapshot(record),
            tenant_id="tenant-a",
            evaluated_at_utc=EVALUATED_AT,
        )


def test_offline_feedback_projection_distinguishes_every_governed_reason_across_families() -> None:
    records = tuple(
        _record(
            _candidate(
                f"idea-evaluation-{index}",
                family,
                "tenant-a",
                Decimal("82"),
            ),
            feedback_outcome=outcome,
            feedback_reason=reason,
        )
        for index, (outcome, reason, family) in enumerate(GOVERNED_REASON_SCENARIOS)
    )

    projection = build_offline_feedback_evaluation(
        _snapshot(*records),
        tenant_id="tenant-a",
        evaluated_at_utc=EVALUATED_AT,
    )

    assert projection.source_observation_count == len(GOVERNED_REASON_SCENARIOS)
    assert {
        (cohort.feedback_outcome, cohort.feedback_reason, cohort.opportunity_family)
        for cohort in projection.cohorts
    } == set(GOVERNED_REASON_SCENARIOS)


def test_offline_feedback_projection_enforces_the_requested_bound() -> None:
    records = tuple(
        _record(
            _candidate(
                f"idea-bounded-{index}",
                OpportunityFamily.HIGH_CASH,
                "tenant-a",
                Decimal("82"),
            ),
            feedback_reason=FeedbackReason.DUPLICATE,
        )
        for index in range(2)
    )

    with pytest.raises(FeedbackEvaluationBoundExceeded, match="1 observation bound"):
        build_offline_feedback_evaluation(
            _snapshot(*records),
            tenant_id="tenant-a",
            evaluated_at_utc=EVALUATED_AT,
            max_observations=1,
        )


def test_offline_feedback_projection_rejects_invalid_execution_boundaries() -> None:
    snapshot = _snapshot()

    with pytest.raises(FeedbackEvaluationScopeError, match="tenant_id is required"):
        build_offline_feedback_evaluation(
            snapshot,
            tenant_id="  ",
            evaluated_at_utc=EVALUATED_AT,
        )

    with pytest.raises(ValueError, match="evaluated_at_utc must be timezone-aware"):
        build_offline_feedback_evaluation(
            snapshot,
            tenant_id="tenant-a",
            evaluated_at_utc=EVALUATED_AT.replace(tzinfo=None),
        )

    for invalid_bound in (0, 10_001):
        with pytest.raises(ValueError, match="max_observations must be between 1 and 10000"):
            build_offline_feedback_evaluation(
                snapshot,
                tenant_id="tenant-a",
                evaluated_at_utc=EVALUATED_AT,
                max_observations=invalid_bound,
            )


def test_offline_feedback_projection_excludes_future_and_feedback_free_records() -> None:
    feedback_record = _record(
        _candidate("idea-future-001", OpportunityFamily.HIGH_CASH, "tenant-a", Decimal("82")),
        feedback_reason=FeedbackReason.WRONG_TIMING,
    )
    feedback_event = feedback_record.feedback_events[0]
    future_feedback_event = replace(
        feedback_event,
        feedback=replace(
            feedback_event.feedback,
            recorded_at_utc=EVALUATED_AT + timedelta(minutes=1),
        ),
    )
    future_record = replace(feedback_record, feedback_events=(future_feedback_event,))
    feedback_free_record = replace(
        _record(
            _candidate(
                "idea-feedback-free-001",
                OpportunityFamily.UNDERPERFORMANCE,
                "tenant-a",
                Decimal("74"),
            ),
            feedback_reason=FeedbackReason.NOT_RELEVANT,
        ),
        feedback_events=(),
    )

    projection = build_offline_feedback_evaluation(
        _snapshot(future_record, feedback_free_record),
        tenant_id="tenant-a",
        evaluated_at_utc=EVALUATED_AT,
    )

    assert projection.source_observation_count == 0
    assert projection.cohorts == ()


def test_offline_feedback_projection_preserves_unscored_unranked_context() -> None:
    candidate = replace(
        _candidate(
            "idea-unranked-001",
            OpportunityFamily.HIGH_CASH,
            "tenant-a",
            Decimal("82"),
        ),
        score=None,
    )
    record = _record(candidate, feedback_reason=FeedbackReason.INSUFFICIENT_EVIDENCE)

    projection = build_offline_feedback_evaluation(
        _snapshot(record),
        tenant_id="tenant-a",
        evaluated_at_utc=EVALUATED_AT,
    )

    assert projection.source_observation_count == 1
    assert projection.cohorts[0].score_policy_version is None
    assert projection.cohorts[0].score is None
    assert projection.cohorts[0].rank_context.value == "unranked"


def _candidate(
    candidate_id: str,
    family: OpportunityFamily,
    tenant_id: str,
    score: Decimal,
) -> IdeaCandidate:
    source = SourceRef(
        product_id="lotus-core:PortfolioStateSnapshot:v1",
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route="/integration/portfolios/{portfolio_id}/core-snapshot",
        as_of_date=date(2026, 6, 21),
        generated_at_utc=datetime(2026, 6, 21, 9, 0, tzinfo=UTC),
        content_hash=f"sha256:{'1' * 64}",
        data_quality_status="complete",
        freshness=EvidenceFreshness.CURRENT,
    )
    evidence = IdeaEvidencePacket(
        evidence_packet_id=f"evidence-{candidate_id}",
        supportability=EvidenceSupportability.READY,
        source_refs=(source,),
        lineage_ref=LineageRef(
            lineage_id=f"lineage-{candidate_id}",
            source_refs=(source,),
            content_hash=f"sha256:{'2' * 64}",
        ),
        reason_codes=(ReasonCode.REVIEW_REQUIRED,),
        created_at_utc=datetime(2026, 6, 21, 9, 0, tzinfo=UTC),
    )
    score_policy = {
        OpportunityFamily.HIGH_CASH: "idle-liquidity-v1",
        OpportunityFamily.UNDERPERFORMANCE: "underperformance-review-v1",
    }[family]
    return IdeaCandidate(
        candidate_id=candidate_id,
        identity=initial_candidate_identity(candidate_id),
        family=family,
        lifecycle_status=IdeaLifecycleStatus.GENERATED,
        review_posture=ReviewPosture.ADVISOR_REVIEW_REQUIRED,
        evidence_packet=evidence,
        source_signal_ids=(f"signal-{candidate_id}",),
        score=IdeaScore(
            policy_version=score_policy,
            score=score,
            reason_codes=(ReasonCode.QUEUE_PRIORITY,),
        ),
        access_scope=ReviewAccessScope(
            tenant_id=tenant_id,
            book_id="book-001",
            portfolio_id="portfolio-001",
            client_id="client-001",
        ),
        created_at_utc=datetime(2026, 6, 21, 9, 0, tzinfo=UTC),
        updated_at_utc=datetime(2026, 6, 21, 9, 0, tzinfo=UTC),
    )


def _record(
    candidate: IdeaCandidate,
    *,
    feedback_outcome: FeedbackOutcome = FeedbackOutcome.NOT_USEFUL,
    feedback_reason: FeedbackReason,
    review_action: ReviewAction | None = None,
    include_downstream_outcome: bool = False,
) -> CandidatePersistenceRecord:
    feedback_time = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
    scope = candidate.access_scope
    assert scope is not None
    feedback = record_feedback(
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
            recorded_at_utc=feedback_time,
        ),
    ).feedback_event
    reviews = (
        (
            GovernedReviewDecision(
                review_id=f"review-{candidate.candidate_id}",
                candidate_id=candidate.candidate_id,
                evidence_packet_id=candidate.evidence_packet.evidence_packet_id,
                evidence_content_hash=candidate.evidence_packet.lineage_ref.content_hash,
                action=review_action,
                resulting_posture=ReviewPosture.NO_ACTION,
                actor_subject="advisor-sensitive-subject",
                actor_role=ReviewActorRole.ADVISOR,
                reason_codes=(ReasonCode.REVIEW_NO_ACTION,),
                decided_at_utc=datetime(2026, 6, 21, 9, 55, tzinfo=UTC),
            ),
        )
        if review_action is not None
        else ()
    )
    outcomes = (_conversion_outcome(),) if include_downstream_outcome else ()
    return CandidatePersistenceRecord(
        candidate=candidate,
        evidence_hash=f"sha256:{'3' * 64}",
        persisted_at_utc=datetime(2026, 6, 21, 9, 0, tzinfo=UTC),
        review_decisions=reviews,
        feedback_events=(feedback,),
        conversion_outcomes=outcomes,
    )


def _conversion_outcome() -> GovernedConversionOutcome:
    return GovernedConversionOutcome(
        outcome=IdeaConversionOutcome(
            conversion_outcome_id="outcome-sensitive-id",
            conversion_intent_id="intent-sensitive-id",
            status=ConversionOutcomeStatus.COMPLETED,
            downstream_reference="downstream-sensitive-reference",
            recorded_at_utc=datetime(2026, 6, 21, 10, 30, tzinfo=UTC),
        ),
        conversion_intent_id="intent-sensitive-id",
        target=ConversionTarget.REPORT_EVIDENCE,
        source_system=SourceSystem.LOTUS_REPORT,
        boundary=ConversionBoundary.DOWNSTREAM_REALIZATION_REQUIRED,
        source_event_version=1,
        actor_subject="report-sensitive-subject",
    )


def _snapshot(*records: CandidatePersistenceRecord) -> IdeaRepositorySnapshot:
    return IdeaRepositorySnapshot(
        candidate_records={record.candidate.candidate_id: record for record in records},
        idempotency_records={},
        idempotency_candidates={},
    )
