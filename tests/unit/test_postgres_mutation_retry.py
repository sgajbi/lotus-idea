from __future__ import annotations

import pytest

import app.infrastructure.postgres_mutation_retry as mutation_retry
from app.domain import IdeaRepositorySnapshot
from app.infrastructure.postgres_candidate_writes import ConcurrentIdempotencyMutationError


def test_postgres_mutation_retry_uses_fresh_snapshot_after_idempotency_race(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observations: list[dict[str, object]] = []
    monkeypatch.setattr(
        mutation_retry,
        "observe_postgres_operation",
        lambda **values: observations.append(values),
    )
    connection = RecordingConnection()
    snapshots = {
        "base": IdeaRepositorySnapshot(
            candidate_records={},
            idempotency_records={},
            idempotency_candidates={},
        ),
        "fresh": IdeaRepositorySnapshot(
            candidate_records={},
            idempotency_records={},
            idempotency_candidates={},
        ),
    }
    apply_attempts = 0

    def apply_delta(*args: object, **kwargs: object) -> None:
        nonlocal apply_attempts
        del args, kwargs
        apply_attempts += 1
        if apply_attempts == 1:
            raise ConcurrentIdempotencyMutationError("duplicate key")

    monkeypatch.setattr(mutation_retry, "apply_postgres_snapshot_delta", apply_delta)

    result = mutation_retry.execute_postgres_mutation(
        object(),
        connection,
        lambda: snapshots["base"],
        lambda: snapshots["fresh"],
        lambda repository: repository.snapshot(),
    )

    assert result == snapshots["fresh"]
    assert apply_attempts == 2
    assert connection.rollback_count == 1
    assert connection.commit_count == 1
    assert len(observations) == 1
    assert observations[0]["operation"] == "mutation"
    assert observations[0]["outcome"] == "accepted"


def test_postgres_mutation_retry_raises_after_second_idempotency_race(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observations: list[dict[str, object]] = []
    monkeypatch.setattr(
        mutation_retry,
        "observe_postgres_operation",
        lambda **values: observations.append(values),
    )
    connection = RecordingConnection()
    snapshot = IdeaRepositorySnapshot(
        candidate_records={},
        idempotency_records={},
        idempotency_candidates={},
    )

    def apply_delta(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise ConcurrentIdempotencyMutationError("duplicate key")

    monkeypatch.setattr(mutation_retry, "apply_postgres_snapshot_delta", apply_delta)

    with pytest.raises(ConcurrentIdempotencyMutationError):
        mutation_retry.execute_postgres_mutation(
            object(),
            connection,
            lambda: snapshot,
            lambda: snapshot,
            lambda repository: repository.snapshot(),
        )

    assert connection.rollback_count == 2
    assert connection.commit_count == 0
    assert len(observations) == 1
    assert observations[0]["outcome"] == "conflict"


class RecordingConnection:
    def __init__(self) -> None:
        self.commit_count = 0
        self.rollback_count = 0

    def cursor(self) -> "RecordingCursor":
        return RecordingCursor()

    def commit(self) -> None:
        self.commit_count += 1

    def rollback(self) -> None:
        self.rollback_count += 1


class RecordingCursor:
    def __enter__(self) -> "RecordingCursor":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None
