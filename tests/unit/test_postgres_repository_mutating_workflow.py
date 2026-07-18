from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import timedelta

from app.domain import (
    EvidenceReplayStatus,
    GovernedConversionIntent,
    IdeaCandidate,
    IdeaLifecycleStatus,
    ReviewPosture,
    apply_review_action,
    record_conversion_outcome,
    record_feedback,
    request_conversion_intent,
    request_report_evidence_pack,
)
from app.domain.persistence import (
    CandidatePersistenceRecord,
    ConversionPersistenceDecision,
    ConversionPersistenceResult,
    EvidencePackPersistenceDecision,
    EvidencePackPersistenceResult,
    EvidenceReplayResult,
    IdeaRepositorySnapshot,
    LifecyclePersistenceDecision,
    LifecyclePersistenceResult,
    ReviewPersistenceDecision,
    ReviewPersistenceResult,
)
from app.infrastructure.postgres_repository import PostgresIdeaRepository
from tests.unit.postgres_repository_fake import FakePostgresConnection
from tests.unit.postgres_repository_query_assertions import assert_no_whole_store_snapshot
from tests.unit.test_postgres_repository import (
    EVALUATED_AT,
    _append_orphan_detail_rows,
    access_scope,
    conversion_command,
    conversion_outcome_command,
    feedback_command,
    high_cash_candidate,
    report_pack_command,
    review_command,
)


@dataclass(frozen=True)
class MutatingWorkflowSeedCandidates:
    review_ready: IdeaCandidate
    approved: IdeaCandidate


@dataclass(frozen=True)
class MutatingWorkflowPersistenceProof:
    lifecycle: LifecyclePersistenceResult
    review: ReviewPersistenceResult
    feedback: ReviewPersistenceResult
    conversion: ConversionPersistenceResult
    outcome: ConversionPersistenceResult
    pack: EvidencePackPersistenceResult


@dataclass(frozen=True)
class MutatingWorkflowReplayProof:
    replay: EvidenceReplayResult
    review_precheck: ReviewPersistenceResult | None
    conversion_precheck: ConversionPersistenceResult | None
    evidence_pack_precheck: EvidencePackPersistenceResult | None


@dataclass(frozen=True)
class MutatingWorkflowLookupProof:
    loaded_intent: GovernedConversionIntent | None
    loaded_conversion_record: CandidatePersistenceRecord | None


@dataclass(frozen=True)
class MutatingWorkflowRoundTripProof:
    persistence: MutatingWorkflowPersistenceProof
    replay: MutatingWorkflowReplayProof
    lookup: MutatingWorkflowLookupProof


def test_postgres_repository_round_trips_mutating_workflow_details() -> None:
    connection = FakePostgresConnection()
    repository = PostgresIdeaRepository(connection)
    candidates = _persist_mutating_workflow_seed_candidates(repository)
    proof = _record_mutating_workflow_details(repository, candidates)
    bounded_workflow_sql = tuple(connection.executed_sql)
    _append_orphan_detail_rows(connection)

    recovered = PostgresIdeaRepository(connection).snapshot()

    _assert_mutating_workflow_persistence(proof.persistence, bounded_workflow_sql)
    _assert_mutating_workflow_replay(proof.replay)
    _assert_mutating_workflow_lookup(proof.lookup, candidates.approved)
    _assert_mutating_workflow_snapshot(recovered, candidates)
    _assert_replacement_snapshot_round_trip(recovered)


def _persist_mutating_workflow_seed_candidates(
    repository: PostgresIdeaRepository,
) -> MutatingWorkflowSeedCandidates:
    review_ready = replace(
        high_cash_candidate(candidate_scope=access_scope()),
        candidate_id="idea_high_cash_review_ready",
        lifecycle_status=IdeaLifecycleStatus.READY_FOR_REVIEW,
    )
    approved = replace(
        high_cash_candidate(candidate_scope=access_scope()),
        candidate_id="idea_high_cash_approved",
        lifecycle_status=IdeaLifecycleStatus.APPROVED,
        review_posture=ReviewPosture.APPROVED_FOR_CONVERSION,
    )

    repository.persist_candidate(
        review_ready,
        idempotency_key="candidate:review-ready",
        payload={"candidateId": review_ready.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    repository.persist_candidate(
        approved,
        idempotency_key="candidate:approved",
        payload={"candidateId": approved.candidate_id, "state": "approved"},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    return MutatingWorkflowSeedCandidates(
        review_ready=review_ready,
        approved=approved,
    )


def _record_mutating_workflow_details(
    repository: PostgresIdeaRepository,
    candidates: MutatingWorkflowSeedCandidates,
) -> MutatingWorkflowRoundTripProof:
    lifecycle = repository.record_lifecycle_transition(
        candidates.review_ready.candidate_id,
        IdeaLifecycleStatus.REVIEWED_BY_ADVISOR,
        idempotency_key="lifecycle:reviewed",
        payload={
            "candidateId": candidates.review_ready.candidate_id,
            "target": "reviewed_by_advisor",
        },
        actor_subject="advisor-001",
        occurred_at_utc=EVALUATED_AT + timedelta(minutes=1),
        transition_id="transition-review-001",
        reason_codes=("review_required",),
    )
    assert lifecycle.record is not None

    review_result = apply_review_action(
        lifecycle.record.candidate,
        review_command(),
    )
    review = repository.record_review_action(
        review_result,
        idempotency_key="review:approve",
        payload={"reviewId": review_result.decision.review_id},
    )
    assert review.record is not None
    feedback_result = record_feedback(
        review.record.candidate,
        feedback_command(),
    )
    feedback = repository.record_feedback_event(
        feedback_result,
        idempotency_key="feedback:useful",
        payload={"feedbackId": feedback_result.feedback_event.feedback.feedback_id},
    )

    conversion_result = request_conversion_intent(
        candidates.approved,
        conversion_command(),
    )
    conversion = repository.record_conversion_intent(
        conversion_result,
        idempotency_key="conversion:intent",
        payload={
            "conversionIntentId": conversion_result.conversion_intent.intent.conversion_intent_id
        },
    )
    assert conversion.record is not None
    outcome_result = record_conversion_outcome(
        conversion_result.conversion_intent,
        conversion_outcome_command(),
    )
    outcome = repository.record_conversion_outcome(
        outcome_result,
        idempotency_key="conversion:outcome",
        payload={
            "conversionOutcomeId": outcome_result.conversion_outcome.outcome.conversion_outcome_id
        },
    )
    pack_result = request_report_evidence_pack(
        conversion.record.candidate,
        conversion_result.conversion_intent,
        report_pack_command(),
    )
    pack = repository.record_report_evidence_pack(
        pack_result,
        idempotency_key="report:evidence-pack",
        payload={"reportEvidencePackId": pack_result.evidence_pack.report_evidence_pack_id},
    )
    replay = repository.replay_evidence(
        candidates.review_ready.candidate_id,
        current_source_refs=candidates.review_ready.evidence_packet.source_refs,
        evaluated_at_utc=EVALUATED_AT + timedelta(minutes=7),
    )
    review_precheck = repository.precheck_review_mutation(
        idempotency_key="review:approve",
        payload={"reviewId": review_result.decision.review_id},
        identity=review_result.decision.mutation_identity,
    )
    conversion_precheck = repository.precheck_conversion_mutation(
        idempotency_key="conversion:intent",
        payload={
            "conversionIntentId": conversion_result.conversion_intent.intent.conversion_intent_id
        },
    )
    evidence_pack_precheck = repository.precheck_evidence_pack_mutation(
        idempotency_key="report:evidence-pack",
        payload={"reportEvidencePackId": pack_result.evidence_pack.report_evidence_pack_id},
    )
    loaded_intent = repository.conversion_intent_by_id("conversion-report-001")
    loaded_conversion_record = repository.candidate_record_for_conversion_intent(
        "conversion-report-001"
    )
    return MutatingWorkflowRoundTripProof(
        persistence=MutatingWorkflowPersistenceProof(
            lifecycle=lifecycle,
            review=review,
            feedback=feedback,
            conversion=conversion,
            outcome=outcome,
            pack=pack,
        ),
        replay=MutatingWorkflowReplayProof(
            replay=replay,
            review_precheck=review_precheck,
            conversion_precheck=conversion_precheck,
            evidence_pack_precheck=evidence_pack_precheck,
        ),
        lookup=MutatingWorkflowLookupProof(
            loaded_intent=loaded_intent,
            loaded_conversion_record=loaded_conversion_record,
        ),
    )


def _assert_mutating_workflow_persistence(
    proof: MutatingWorkflowPersistenceProof,
    bounded_workflow_sql: tuple[str, ...],
) -> None:
    assert proof.lifecycle.decision is LifecyclePersistenceDecision.ACCEPTED
    assert proof.review.decision is ReviewPersistenceDecision.ACCEPTED
    assert proof.feedback.decision is ReviewPersistenceDecision.ACCEPTED
    assert proof.conversion.decision is ConversionPersistenceDecision.ACCEPTED
    assert proof.outcome.decision is ConversionPersistenceDecision.ACCEPTED
    assert proof.pack.decision is EvidencePackPersistenceDecision.ACCEPTED
    assert_no_whole_store_snapshot(bounded_workflow_sql)


def _assert_mutating_workflow_replay(proof: MutatingWorkflowReplayProof) -> None:
    assert proof.replay.status is EvidenceReplayStatus.MATCHED
    assert proof.review_precheck is not None
    assert proof.review_precheck.decision is ReviewPersistenceDecision.REPLAYED
    assert proof.conversion_precheck is not None
    assert proof.conversion_precheck.decision is ConversionPersistenceDecision.REPLAYED
    assert proof.evidence_pack_precheck is not None
    assert proof.evidence_pack_precheck.decision is EvidencePackPersistenceDecision.REPLAYED


def _assert_mutating_workflow_lookup(
    proof: MutatingWorkflowLookupProof,
    approved: IdeaCandidate,
) -> None:
    assert proof.loaded_intent is not None
    assert proof.loaded_intent.intent.conversion_intent_id == "conversion-report-001"
    assert proof.loaded_conversion_record is not None
    assert proof.loaded_conversion_record.candidate.candidate_id == approved.candidate_id


def _assert_mutating_workflow_snapshot(
    recovered: IdeaRepositorySnapshot,
    candidates: MutatingWorkflowSeedCandidates,
) -> None:
    reviewed_record = recovered.candidate_records[candidates.review_ready.candidate_id]
    converted_record = recovered.candidate_records[candidates.approved.candidate_id]

    assert len(reviewed_record.lifecycle_history) == 2
    assert len(reviewed_record.review_decisions) == 1
    assert len(reviewed_record.feedback_events) == 1
    assert len(converted_record.conversion_intents) == 1
    assert len(converted_record.conversion_outcomes) == 1
    assert len(converted_record.report_evidence_packs) == 1
    assert [event.event_type for event in recovered.outbox_events.values()] == [
        "idea.candidate.persisted.v1",
        "idea.candidate.persisted.v1",
        "idea.lifecycle.transitioned.v1",
        "idea.review.decision_recorded.v1",
        "idea.feedback.recorded.v1",
        "idea.conversion.intent_requested.v1",
        "idea.conversion.outcome_recorded.v1",
        "idea.report_evidence_pack.requested.v1",
    ]
    assert (
        recovered.conversion_intent_candidates["conversion-report-001"]
        == candidates.approved.candidate_id
    )
    assert (
        recovered.report_evidence_pack_candidates["report-evidence-pack-001"]
        == candidates.approved.candidate_id
    )


def _assert_replacement_snapshot_round_trip(recovered: IdeaRepositorySnapshot) -> None:
    replacement_connection = FakePostgresConnection()
    PostgresIdeaRepository(replacement_connection).replace_snapshot(recovered)
    replaced = PostgresIdeaRepository(replacement_connection).snapshot()

    assert replacement_connection.commits == 1
    assert replacement_connection.rollbacks == 0
    assert replaced.candidate_records.keys() == recovered.candidate_records.keys()
    assert len(replacement_connection.rows["idea_lifecycle_history"]) == 3
    assert len(replacement_connection.rows["idea_review_decision"]) == 1
    assert len(replacement_connection.rows["idea_feedback_event"]) == 1
    assert len(replacement_connection.rows["idea_conversion_intent"]) == 1
    assert len(replacement_connection.rows["idea_conversion_outcome"]) == 1
    assert len(replacement_connection.rows["idea_report_evidence_pack_request"]) == 1
    assert len(replacement_connection.rows["idea_outbox_event"]) == 8
