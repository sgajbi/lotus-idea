from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from app.application.candidate_lifecycle import (
    ApplyCandidateLifecycleTransitionCommand,
    CandidateLifecycleTransitionWorkflowResult,
    apply_candidate_lifecycle_transition_to_repository,
)
from app.application.persisted_action_evidence import PersistedActionEvidenceUnavailable
from app.domain import (
    CandidatePersistenceDecision,
    IdeaLifecycleStatus,
    InMemoryIdeaRepository,
    LifecyclePersistenceDecision,
    LifecyclePersistenceResult,
    OpportunityFamily,
)
from tests.support.opportunity_effectiveness_fixture import candidate_fixture


CHANGED_AT = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)


def lifecycle_command(**overrides: object) -> ApplyCandidateLifecycleTransitionCommand:
    values: dict[str, Any] = {
        "candidate_id": "idea-candidate-001",
        "transition_id": "transition-001",
        "target_status": IdeaLifecycleStatus.READY_FOR_REVIEW,
        "changed_at_utc": CHANGED_AT,
        "reason_codes": ("review_required",),
        "actor_subject": "advisor-001",
        "idempotency_key": "lifecycle-transition-001",
    }
    values.update(overrides)
    return ApplyCandidateLifecycleTransitionCommand(**values)


@pytest.mark.parametrize(
    ("field_name", "bad_value", "message"),
    [
        ("candidate_id", " ", "candidate_id is required"),
        ("transition_id", " ", "transition_id is required"),
        ("actor_subject", " ", "actor_subject is required"),
        ("idempotency_key", " ", "idempotency_key is required"),
        ("reason_codes", (), "reason_codes is required"),
        ("reason_codes", ("review_required", " "), "reason_codes cannot contain blank values"),
        (
            "changed_at_utc",
            datetime(2026, 6, 21, 10, 10),
            "changed_at_utc must be timezone-aware",
        ),
    ],
)
def test_candidate_lifecycle_transition_command_rejects_invalid_inputs(
    field_name: str,
    bad_value: object,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        lifecycle_command(**{field_name: bad_value})


@pytest.mark.parametrize(
    "target_status",
    [IdeaLifecycleStatus.ACCEPTED, IdeaLifecycleStatus.EXECUTED],
)
def test_candidate_lifecycle_transition_command_rejects_downstream_authority_targets(
    target_status: IdeaLifecycleStatus,
) -> None:
    with pytest.raises(ValueError, match="reserved for downstream source-authority outcomes"):
        lifecycle_command(target_status=target_status)


def test_lifecycle_transition_returns_same_exact_persisted_evidence_on_replay() -> None:
    repository = _repository_with_candidate()
    command = lifecycle_command(target_status=IdeaLifecycleStatus.ENRICHED)

    accepted = apply_candidate_lifecycle_transition_to_repository(
        command,
        repository=repository,
    )
    before_replay = repository.snapshot()
    replayed = apply_candidate_lifecycle_transition_to_repository(
        command,
        repository=repository,
    )

    assert accepted.persistence.decision is LifecyclePersistenceDecision.ACCEPTED
    assert replayed.persistence.decision is LifecyclePersistenceDecision.REPLAYED
    assert replayed.require_transition() == accepted.require_transition()
    assert replayed.require_transition().candidate_id == command.candidate_id
    assert replayed.require_transition().transition_id == command.transition_id
    assert replayed.require_transition().lifecycle_status is IdeaLifecycleStatus.ENRICHED
    assert replayed.require_transition().changed_at_utc == command.changed_at_utc
    assert replayed.require_transition().reason_codes == command.reason_codes
    assert repository.snapshot() == before_replay


def test_unsuccessful_lifecycle_results_do_not_claim_persisted_transition_evidence() -> None:
    missing = apply_candidate_lifecycle_transition_to_repository(
        lifecycle_command(target_status=IdeaLifecycleStatus.ENRICHED),
        repository=InMemoryIdeaRepository(),
    )
    repository = _repository_with_candidate()
    command = lifecycle_command(target_status=IdeaLifecycleStatus.ENRICHED)
    apply_candidate_lifecycle_transition_to_repository(command, repository=repository)
    conflict = apply_candidate_lifecycle_transition_to_repository(
        lifecycle_command(
            transition_id="transition-002",
            target_status=IdeaLifecycleStatus.SCORED,
        ),
        repository=repository,
    )

    assert missing.persistence.decision is LifecyclePersistenceDecision.NOT_FOUND
    assert missing.transition is None
    assert conflict.persistence.decision is LifecyclePersistenceDecision.CONFLICT
    assert conflict.transition is None


@pytest.mark.parametrize(
    "evidence_posture",
    ["missing", "ambiguous", "malformed", "contradictory"],
)
def test_successful_lifecycle_transition_fails_closed_without_one_valid_persisted_event(
    evidence_posture: str,
) -> None:
    repository = _repository_with_candidate()
    command = lifecycle_command(target_status=IdeaLifecycleStatus.ENRICHED)
    accepted = apply_candidate_lifecycle_transition_to_repository(command, repository=repository)
    record = accepted.persistence.record
    assert record is not None
    lifecycle_event = record.audit_events[-1]
    if evidence_posture == "missing":
        audit_events = tuple(event for event in record.audit_events if event is not lifecycle_event)
    elif evidence_posture == "ambiguous":
        audit_events = (*record.audit_events, lifecycle_event)
    elif evidence_posture == "malformed":
        audit_events = (
            *record.audit_events[:-1],
            replace(lifecycle_event, attributes={"transition_id": command.transition_id}),
        )
    else:
        audit_events = (
            *record.audit_events[:-1],
            replace(
                lifecycle_event,
                attributes={
                    **lifecycle_event.attributes,
                    "target_status": IdeaLifecycleStatus.SCORED.value,
                },
            ),
        )
    persistence = LifecyclePersistenceResult(
        decision=LifecyclePersistenceDecision.REPLAYED,
        record=replace(record, audit_events=audit_events),
    )

    with pytest.raises(PersistedActionEvidenceUnavailable):
        apply_candidate_lifecycle_transition_to_repository(
            command,
            repository=_StaticLifecycleRepository(persistence),
        )


def test_successful_lifecycle_transition_requires_matching_candidate_record() -> None:
    repository = _repository_with_candidate()
    command = lifecycle_command(target_status=IdeaLifecycleStatus.ENRICHED)
    accepted = apply_candidate_lifecycle_transition_to_repository(command, repository=repository)
    record = accepted.persistence.record
    assert record is not None
    mismatched_candidate = candidate_fixture(
        "different-candidate",
        family=OpportunityFamily.HIGH_CASH,
        score=Decimal("80"),
        created_at=CHANGED_AT,
    )

    with pytest.raises(
        PersistedActionEvidenceUnavailable,
        match="no matching candidate record",
    ):
        apply_candidate_lifecycle_transition_to_repository(
            command,
            repository=_StaticLifecycleRepository(
                LifecyclePersistenceResult(
                    decision=LifecyclePersistenceDecision.REPLAYED,
                    record=replace(record, candidate=mismatched_candidate),
                )
            ),
        )


def test_lifecycle_workflow_result_guard_rejects_missing_success_evidence() -> None:
    with pytest.raises(
        PersistedActionEvidenceUnavailable,
        match="no persisted transition",
    ):
        CandidateLifecycleTransitionWorkflowResult(
            transition=None,
            persistence=LifecyclePersistenceResult(
                decision=LifecyclePersistenceDecision.REPLAYED,
                record=None,
            ),
        ).require_transition()


def _repository_with_candidate() -> InMemoryIdeaRepository:
    repository = InMemoryIdeaRepository()
    candidate = candidate_fixture(
        "idea-candidate-001",
        family=OpportunityFamily.HIGH_CASH,
        score=Decimal("80"),
        created_at=CHANGED_AT,
    )
    result = repository.persist_candidate(
        candidate,
        idempotency_key="seed:lifecycle:001",
        payload={"candidate_id": candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=CHANGED_AT,
    )
    assert result.decision is CandidatePersistenceDecision.ACCEPTED
    return repository


class _StaticLifecycleRepository:
    def __init__(self, persistence: LifecyclePersistenceResult) -> None:
        self._persistence = persistence

    def record_lifecycle_transition(self, *args: Any, **kwargs: Any) -> LifecyclePersistenceResult:
        return self._persistence
