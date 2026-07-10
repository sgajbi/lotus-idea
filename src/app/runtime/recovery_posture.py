from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Mapping

from app.domain.recovery_posture import (
    RecoveryReadinessDecision,
    ServiceRecoveryPosture,
    evaluate_recovery_readiness,
)

RECOVERY_POSTURE_ENV = "LOTUS_IDEA_RECOVERY_POSTURE"


@dataclass(frozen=True)
class RecoveryRuntimeState:
    posture: ServiceRecoveryPosture
    configuration_valid: bool

    @property
    def decision(self) -> RecoveryReadinessDecision:
        return evaluate_recovery_readiness(
            self.posture,
            configuration_valid=self.configuration_valid,
        )


def load_recovery_runtime_state(
    environment: Mapping[str, str] | None = None,
) -> RecoveryRuntimeState:
    values = environment if environment is not None else os.environ
    configured = values.get(RECOVERY_POSTURE_ENV, ServiceRecoveryPosture.NORMAL.value)
    try:
        posture = ServiceRecoveryPosture(configured.strip().lower())
    except ValueError:
        return RecoveryRuntimeState(
            posture=ServiceRecoveryPosture.DEGRADED,
            configuration_valid=False,
        )
    return RecoveryRuntimeState(posture=posture, configuration_valid=True)
