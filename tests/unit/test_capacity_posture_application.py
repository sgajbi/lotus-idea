from __future__ import annotations

from app.application.capacity_posture import (
    evaluate_nonessential_workload_capacity,
    read_postgres_capacity_posture,
)
from app.domain.capacity_posture import (
    CapacityPosture,
    PostgresCapacityPosture,
    evaluate_postgres_capacity_posture,
)


class StubCapacityRepository:
    durable_storage_backed = True

    def __init__(self, utilization: float | None = 0.5, error: Exception | None = None) -> None:
        self.utilization = utilization
        self.error = error

    def postgres_capacity_posture(self) -> PostgresCapacityPosture:
        if self.error is not None:
            raise self.error
        return evaluate_postgres_capacity_posture(self.utilization)


def test_application_reads_repository_capacity_and_applies_shed_policy() -> None:
    posture = read_postgres_capacity_posture(StubCapacityRepository(0.95))
    decision = evaluate_nonessential_workload_capacity(StubCapacityRepository(0.95))

    assert posture.posture is CapacityPosture.SHED
    assert decision.allowed is False
    assert decision.blocker == "postgres_capacity_shed_active"


def test_missing_or_failed_capacity_adapter_fails_closed_without_raw_error() -> None:
    class DurableRepositoryWithoutCapacityPort:
        durable_storage_backed = True

    for repository in (
        DurableRepositoryWithoutCapacityPort(),
        StubCapacityRepository(error=RuntimeError("database detail")),
    ):
        posture = read_postgres_capacity_posture(repository)
        decision = evaluate_nonessential_workload_capacity(repository)

        assert posture.posture is CapacityPosture.UNAVAILABLE
        assert decision.allowed is False
        assert decision.blocker == "postgres_capacity_posture_unavailable"


def test_non_durable_repository_remains_owned_by_existing_storage_guard() -> None:
    decision = evaluate_nonessential_workload_capacity(object())

    assert decision.allowed is True
    assert decision.posture is CapacityPosture.NORMAL
