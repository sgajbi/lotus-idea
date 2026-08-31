from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from app.application.candidate_expiry import (
    CandidateExpiryDecision,
    ExpireCandidateCommand,
    expire_candidate,
    expire_candidate_if_due,
)
from app.domain import (
    CandidatePersistenceDecision,
    CandidatePersistenceRecord,
    IdeaLifecycleStatus,
    IdeaRepositorySnapshot,
    InMemoryIdeaRepository,
    InvalidLifecycleTransition,
    LifecyclePersistenceDecision,
    LifecyclePersistenceResult,
    OpportunityFamily,
    ReasonCode,
)
from tests.support.opportunity_effectiveness_fixture import candidate_fixture


EVALUATED_AT = datetime(2026, 6, 21, 11, 0, tzinfo=UTC)


def expiry_command(**overrides: object) -> ExpireCandidateCommand:
    values: dict[str, Any] = {
        "candidate_id": "idea-candidate-expiry-001",
        "actor_subject": "signal-ingestion-worker",
        "evaluated_at_utc": EVALUATED_AT,
        "reason_codes": (ReasonCode.OPPORTUNITY_NO_LONGER_ELIGIBLE,),
    }
    values.update(overrides)
    return ExpireCandidateCommand(**values)


@pytest.mark.parametrize(
    ("field_name", "bad_value", "message"),
    [
        ("candidate_id", " ", "candidate_id is required"),
        ("actor_subject", " ", "actor_subject is required"),
        ("evaluated_at_utc", datetime(2026, 6, 21, 11, 0), "must be timezone-aware"),
        ("reason_codes", (), "reason_codes is required"),
    ],
)
def test_expiry_command_rejects_incomplete_or_ambiguous_evidence(
    field_name: str,
    bad_value: object,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        expiry_command(**{field_name: bad_value})


def test_expiry_classifies_repository_replay_without_duplicate_transition() -> None:
    record = _candidate_record()
    expired_record = _candidate_record(IdeaLifecycleStatus.EXPIRED)
    repository = _ControlledExpiryRepository(
        records=(record,),
        persistence=LifecyclePersistenceResult(
            decision=LifecyclePersistenceDecision.REPLAYED,
            record=expired_record,
        ),
    )

    result = expire_candidate(expiry_command(), repository=repository)

    assert result.decision is CandidateExpiryDecision.ALREADY_EXPIRED
    assert result.persistence is repository.persistence


@pytest.mark.parametrize(
    ("current_record", "expected_decision"),
    [
        (None, CandidateExpiryDecision.NOT_FOUND),
        (IdeaLifecycleStatus.EXPIRED, CandidateExpiryDecision.ALREADY_EXPIRED),
        (IdeaLifecycleStatus.CLOSED, CandidateExpiryDecision.TERMINAL_STATE_PRESERVED),
    ],
)
def test_expiry_is_non_mutating_when_candidate_is_absent_or_already_terminal(
    current_record: IdeaLifecycleStatus | None,
    expected_decision: CandidateExpiryDecision,
) -> None:
    record = None if current_record is None else _candidate_record(current_record)
    repository = _ControlledExpiryRepository(records=(record,))

    result = expire_candidate(expiry_command(), repository=repository)

    assert result.decision is expected_decision
    assert result.persistence is None


@pytest.mark.parametrize(
    ("concurrent_record", "expected_decision"),
    [
        (None, CandidateExpiryDecision.NOT_FOUND),
        (IdeaLifecycleStatus.EXPIRED, CandidateExpiryDecision.ALREADY_EXPIRED),
        (IdeaLifecycleStatus.CLOSED, CandidateExpiryDecision.TERMINAL_STATE_PRESERVED),
        (IdeaLifecycleStatus.GENERATED, CandidateExpiryDecision.EXPIRED),
    ],
)
def test_expiry_reclassifies_state_after_concurrent_transition_rejection(
    concurrent_record: IdeaLifecycleStatus | None,
    expected_decision: CandidateExpiryDecision,
) -> None:
    initial = _candidate_record()
    current = None if concurrent_record is None else _candidate_record(concurrent_record)
    repository = _ControlledExpiryRepository(
        records=(initial, current),
        error=InvalidLifecycleTransition(
            IdeaLifecycleStatus.GENERATED,
            IdeaLifecycleStatus.EXPIRED,
        ),
    )

    result = expire_candidate(expiry_command(), repository=repository)

    assert result.decision is expected_decision
    assert result.persistence is None


def test_expiry_fails_closed_on_idempotency_conflict_while_candidate_remains_active() -> None:
    record = _candidate_record()
    repository = _ControlledExpiryRepository(
        records=(record, record),
        persistence=LifecyclePersistenceResult(
            decision=LifecyclePersistenceDecision.CONFLICT,
            record=None,
        ),
    )

    with pytest.raises(RuntimeError, match="candidate expiry idempotency conflict"):
        expire_candidate(expiry_command(), repository=repository)


@pytest.mark.parametrize(
    ("evaluated_at_utc", "expected_decision"),
    [
        (
            datetime(2026, 6, 21, 11, 59, 59, tzinfo=UTC),
            CandidateExpiryDecision.NOT_DUE,
        ),
        (datetime(2026, 6, 21, 12, 0, tzinfo=UTC), CandidateExpiryDecision.EXPIRED),
        (datetime(2026, 6, 21, 12, 0, 1, tzinfo=UTC), CandidateExpiryDecision.EXPIRED),
    ],
)
def test_due_expiry_uses_persisted_exact_boundary(
    evaluated_at_utc: datetime,
    expected_decision: CandidateExpiryDecision,
) -> None:
    record = _candidate_record(
        applicability_expires_at_utc=datetime(2026, 6, 21, 12, 0, tzinfo=UTC)
    )
    persistence = LifecyclePersistenceResult(
        decision=LifecyclePersistenceDecision.ACCEPTED,
        record=_candidate_record(IdeaLifecycleStatus.EXPIRED),
    )
    repository = _ControlledExpiryRepository(
        records=(record,),
        persistence=persistence,
    )

    result = expire_candidate_if_due(
        expiry_command(evaluated_at_utc=evaluated_at_utc),
        repository=repository,
    )

    assert result.decision is expected_decision
    assert result.persistence is (
        persistence if expected_decision is CandidateExpiryDecision.EXPIRED else None
    )


def _candidate_record(
    status: IdeaLifecycleStatus = IdeaLifecycleStatus.GENERATED,
    applicability_expires_at_utc: datetime | None = None,
) -> CandidatePersistenceRecord:
    repository = InMemoryIdeaRepository()
    candidate = candidate_fixture(
        "idea-candidate-expiry-001",
        family=OpportunityFamily.HIGH_CASH,
        score=Decimal("80"),
        created_at=EVALUATED_AT,
    )
    candidate = replace(
        candidate,
        evidence_packet=replace(
            candidate.evidence_packet,
            applicability_expires_at_utc=applicability_expires_at_utc,
        ),
    )
    persisted = repository.persist_candidate(
        candidate,
        idempotency_key="seed:candidate-expiry:001",
        payload={"candidate_id": candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    assert persisted.decision is CandidatePersistenceDecision.ACCEPTED
    assert persisted.record is not None
    if status is IdeaLifecycleStatus.GENERATED:
        return persisted.record
    transitioned = repository.record_lifecycle_transition(
        candidate.candidate_id,
        status,
        idempotency_key=f"seed:candidate-expiry:status:{status.value}",
        payload={"candidate_id": candidate.candidate_id, "target_status": status.value},
        actor_subject="candidate-expiry-test",
        occurred_at_utc=EVALUATED_AT,
        reason_codes=("test_state_setup",),
    )
    assert transitioned.decision is LifecyclePersistenceDecision.ACCEPTED
    assert transitioned.record is not None
    return transitioned.record


class _ControlledExpiryRepository:
    def __init__(
        self,
        *,
        records: tuple[CandidatePersistenceRecord | None, ...],
        persistence: LifecyclePersistenceResult | None = None,
        error: InvalidLifecycleTransition | None = None,
    ) -> None:
        self._records = list(records)
        self.persistence = persistence
        self._error = error

    def candidate_record_by_id(self, candidate_id: str) -> CandidatePersistenceRecord | None:
        assert candidate_id == "idea-candidate-expiry-001"
        return self._records.pop(0)

    def snapshot(self) -> IdeaRepositorySnapshot:
        raise AssertionError("candidate detail projection should be used")

    def record_lifecycle_transition(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> LifecyclePersistenceResult:
        if self._error is not None:
            raise self._error
        assert self.persistence is not None
        return self.persistence
