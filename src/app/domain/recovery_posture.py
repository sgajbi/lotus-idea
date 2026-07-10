from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ServiceRecoveryPosture(StrEnum):
    NORMAL = "normal"
    RESTORING = "restoring"
    DEGRADED = "degraded"
    DRAINING = "draining"


@dataclass(frozen=True)
class RecoveryReadinessDecision:
    posture: ServiceRecoveryPosture
    write_ready: bool
    readiness_status: str
    blocker: str | None


def evaluate_recovery_readiness(
    posture: ServiceRecoveryPosture,
    *,
    configuration_valid: bool = True,
) -> RecoveryReadinessDecision:
    if not configuration_valid:
        return RecoveryReadinessDecision(
            posture=ServiceRecoveryPosture.DEGRADED,
            write_ready=False,
            readiness_status="degraded",
            blocker="recovery_posture_invalid",
        )
    if posture is ServiceRecoveryPosture.NORMAL:
        return RecoveryReadinessDecision(
            posture=posture,
            write_ready=True,
            readiness_status="ready",
            blocker=None,
        )
    return RecoveryReadinessDecision(
        posture=posture,
        write_ready=False,
        readiness_status=posture.value,
        blocker=f"service_recovery_{posture.value}",
    )
