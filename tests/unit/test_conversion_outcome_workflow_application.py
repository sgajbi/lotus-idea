from __future__ import annotations

from datetime import timedelta

import pytest

from app.application.conversion_workflow import (
    ConversionOutcomeWorkflowResult,
    RecordConversionOutcomeToRepositoryCommand,
    record_conversion_outcome_to_repository,
)
from app.domain import (
    CandidatePersistenceDecision,
    ConversionOutcomeCommand,
    ConversionOutcomeStatus,
    ConversionPersistenceDecision,
    InMemoryIdeaRepository,
    InvalidConversionOutcome,
    SourceSystem,
    current_conversion_outcome,
    request_conversion_intent,
)
from tests.unit.test_conversion_governance import (
    OUTCOME_AT,
    REQUESTED_AT,
    candidate,
    intent_command,
)


def repository_with_conversion_intent() -> tuple[InMemoryIdeaRepository, str]:
    repository = InMemoryIdeaRepository()
    source_candidate = candidate()
    persisted = repository.persist_candidate(
        source_candidate,
        idempotency_key="candidate:conversion-outcome-workflow",
        payload={"candidateId": source_candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=REQUESTED_AT,
    )
    assert persisted.decision is CandidatePersistenceDecision.ACCEPTED
    command = intent_command()
    intent_result = request_conversion_intent(source_candidate, command)
    repository.record_conversion_intent(
        intent_result,
        idempotency_key=command.idempotency_key,
        payload={"candidateId": source_candidate.candidate_id, "target": command.target.value},
    )
    return repository, command.conversion_intent_id


def outcome_command(
    status: ConversionOutcomeStatus,
    *,
    outcome_id: str,
    version: int,
    minute: int = 0,
    supersedes: str | None = None,
    correction_reason: str | None = None,
) -> ConversionOutcomeCommand:
    return ConversionOutcomeCommand(
        conversion_outcome_id=outcome_id,
        status=status,
        source_system=SourceSystem.LOTUS_REPORT,
        source_event_version=version,
        downstream_reference=(
            "report-evidence-pack-001"
            if status in {ConversionOutcomeStatus.ACCEPTED, ConversionOutcomeStatus.COMPLETED}
            else None
        ),
        recorded_at_utc=OUTCOME_AT + timedelta(minutes=minute),
        actor_subject="lotus-report-worker",
        supersedes_conversion_outcome_id=supersedes,
        correction_reason=correction_reason,
    )


def record_outcome(
    repository: InMemoryIdeaRepository,
    conversion_intent_id: str,
    outcome: ConversionOutcomeCommand,
    *,
    idempotency_key: str,
) -> ConversionOutcomeWorkflowResult:
    return record_conversion_outcome_to_repository(
        RecordConversionOutcomeToRepositoryCommand(
            conversion_intent_id=conversion_intent_id,
            outcome=outcome,
            idempotency_key=idempotency_key,
        ),
        repository=repository,
    )


def test_conversion_outcome_identity_replays_across_transport_keys_without_side_effects() -> None:
    repository, intent_id = repository_with_conversion_intent()
    outcome = outcome_command(
        ConversionOutcomeStatus.ACCEPTED,
        outcome_id="outcome-identity-replay",
        version=1,
    )
    first = record_outcome(repository, intent_id, outcome, idempotency_key="outcome:first")
    before_replay = repository.snapshot()

    replayed = record_outcome(repository, intent_id, outcome, idempotency_key="outcome:retry")
    after_replay = repository.snapshot()

    assert first.persistence.decision is ConversionPersistenceDecision.ACCEPTED
    assert replayed.outcome_result is None
    assert replayed.persistence.decision is ConversionPersistenceDecision.REPLAYED
    assert after_replay.candidate_records == before_replay.candidate_records
    assert after_replay.outbox_events == before_replay.outbox_events
    assert "outcome:retry" in after_replay.idempotency_records


def test_conversion_outcome_identity_conflicts_on_changed_source_fact() -> None:
    repository, intent_id = repository_with_conversion_intent()
    outcome_id = "outcome-identity-conflict"
    accepted = outcome_command(
        ConversionOutcomeStatus.ACCEPTED,
        outcome_id=outcome_id,
        version=1,
    )
    record_outcome(repository, intent_id, accepted, idempotency_key="outcome:accepted")
    before_conflict = repository.snapshot()

    conflict = record_outcome(
        repository,
        intent_id,
        outcome_command(
            ConversionOutcomeStatus.REJECTED,
            outcome_id=outcome_id,
            version=1,
        ),
        idempotency_key="outcome:changed",
    )

    assert conflict.outcome_result is None
    assert conflict.persistence.decision is ConversionPersistenceDecision.OUTCOME_CONFLICT
    assert repository.snapshot() == before_conflict


def test_conversion_outcome_workflow_records_legal_progression_and_current_posture() -> None:
    repository, intent_id = repository_with_conversion_intent()
    requested = outcome_command(
        ConversionOutcomeStatus.REQUESTED,
        outcome_id="outcome-requested",
        version=1,
    )
    accepted = outcome_command(
        ConversionOutcomeStatus.ACCEPTED,
        outcome_id="outcome-accepted",
        version=2,
        minute=1,
    )
    completed = outcome_command(
        ConversionOutcomeStatus.COMPLETED,
        outcome_id="outcome-completed",
        version=3,
        minute=2,
    )

    for key, outcome in (
        ("outcome:requested", requested),
        ("outcome:accepted", accepted),
        ("outcome:completed", completed),
    ):
        result = record_outcome(repository, intent_id, outcome, idempotency_key=key)
        assert result.persistence.decision is ConversionPersistenceDecision.ACCEPTED

    outcomes = repository.conversion_outcomes_for_intent(intent_id)
    current = current_conversion_outcome(outcomes)
    assert current is not None
    assert current.outcome.status is ConversionOutcomeStatus.COMPLETED
    assert [outcome.source_event_version for outcome in outcomes] == [1, 2, 3]


def test_terminal_outcome_requires_explicit_append_only_correction() -> None:
    repository, intent_id = repository_with_conversion_intent()
    rejected = outcome_command(
        ConversionOutcomeStatus.REJECTED,
        outcome_id="outcome-rejected",
        version=1,
    )
    record_outcome(repository, intent_id, rejected, idempotency_key="outcome:rejected")

    with pytest.raises(InvalidConversionOutcome, match="invalid_transition"):
        record_outcome(
            repository,
            intent_id,
            outcome_command(
                ConversionOutcomeStatus.ACCEPTED,
                outcome_id="outcome-contradictory",
                version=2,
                minute=1,
            ),
            idempotency_key="outcome:contradictory",
        )

    corrected = record_outcome(
        repository,
        intent_id,
        outcome_command(
            ConversionOutcomeStatus.ACCEPTED,
            outcome_id="outcome-corrected",
            version=2,
            minute=1,
            supersedes=rejected.conversion_outcome_id,
            correction_reason="Source corrected an erroneous rejection",
        ),
        idempotency_key="outcome:corrected",
    )

    assert corrected.persistence.decision is ConversionPersistenceDecision.ACCEPTED
    outcomes = repository.conversion_outcomes_for_intent(intent_id)
    assert len(outcomes) == 2
    assert current_conversion_outcome(outcomes) == outcomes[-1]
