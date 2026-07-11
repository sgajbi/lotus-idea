from __future__ import annotations

from app.domain.capacity_posture import (
    NonessentialWorkloadCapacityDecision,
    PostgresCapacityPosture,
    decide_nonessential_workload_capacity,
    evaluate_postgres_capacity_posture,
)
from app.ports.capacity_posture import PostgresCapacityPostureRepository


def read_postgres_capacity_posture(repository: object) -> PostgresCapacityPosture:
    if not bool(getattr(repository, "durable_storage_backed", False)):
        return evaluate_postgres_capacity_posture(0.0)
    if not isinstance(repository, PostgresCapacityPostureRepository):
        return evaluate_postgres_capacity_posture(None)
    try:
        return repository.postgres_capacity_posture()
    except Exception:
        return evaluate_postgres_capacity_posture(None)


def evaluate_nonessential_workload_capacity(
    repository: object,
) -> NonessentialWorkloadCapacityDecision:
    return decide_nonessential_workload_capacity(read_postgres_capacity_posture(repository))
