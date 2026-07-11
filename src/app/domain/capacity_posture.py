from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

POSTGRES_CONNECTION_UTILIZATION_WARN_FRACTION = 0.7
POSTGRES_CONNECTION_UTILIZATION_SHED_FRACTION = 0.9


class CapacityPosture(StrEnum):
    NORMAL = "normal"
    WARNING = "warning"
    SHED = "shed"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class PostgresCapacityPosture:
    posture: CapacityPosture
    connection_utilization_fraction: float | None
    collection_succeeded: bool

    def __post_init__(self) -> None:
        utilization = self.connection_utilization_fraction
        if utilization is not None and not 0 <= utilization <= 1:
            raise ValueError("connection_utilization_fraction must be between zero and one")
        if self.collection_succeeded != (utilization is not None):
            raise ValueError("collection_succeeded must match utilization availability")


@dataclass(frozen=True)
class NonessentialWorkloadCapacityDecision:
    allowed: bool
    posture: CapacityPosture
    blocker: str | None


def evaluate_postgres_capacity_posture(
    connection_utilization_fraction: float | None,
) -> PostgresCapacityPosture:
    if connection_utilization_fraction is None:
        return PostgresCapacityPosture(
            posture=CapacityPosture.UNAVAILABLE,
            connection_utilization_fraction=None,
            collection_succeeded=False,
        )
    if connection_utilization_fraction >= POSTGRES_CONNECTION_UTILIZATION_SHED_FRACTION:
        posture = CapacityPosture.SHED
    elif connection_utilization_fraction >= POSTGRES_CONNECTION_UTILIZATION_WARN_FRACTION:
        posture = CapacityPosture.WARNING
    else:
        posture = CapacityPosture.NORMAL
    return PostgresCapacityPosture(
        posture=posture,
        connection_utilization_fraction=connection_utilization_fraction,
        collection_succeeded=True,
    )


def decide_nonessential_workload_capacity(
    posture: PostgresCapacityPosture,
) -> NonessentialWorkloadCapacityDecision:
    if posture.posture is CapacityPosture.SHED:
        return NonessentialWorkloadCapacityDecision(
            allowed=False,
            posture=posture.posture,
            blocker="postgres_capacity_shed_active",
        )
    if posture.posture is CapacityPosture.UNAVAILABLE:
        return NonessentialWorkloadCapacityDecision(
            allowed=False,
            posture=posture.posture,
            blocker="postgres_capacity_posture_unavailable",
        )
    return NonessentialWorkloadCapacityDecision(
        allowed=True,
        posture=posture.posture,
        blocker=None,
    )
